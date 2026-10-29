"""Comparison: one custom question -> the three MediChat chatbots (Rule-Based, TF-IDF + SVM, DistilBERT).

Live comparison of a user's own question. Dataset-based measurement is in Model Evaluation.
"""
import hashlib

from flask import Blueprint, current_app

from api.chat import bot_list
from api.common import ApiError, body, current_user_id, login_required, ok, text_field
from database import database as db

bp = Blueprint("comparison", __name__)


@bp.get("/comparison/options")
def options():
    import comparison_service as cs
    from chatbot.health_qa.knowledge import TOPICS
    from chatbot.health_qa.taxonomy import CATEGORIES_46
    return ok({"bots": bot_list(), "examples": cs.get_examples(), "topic_count": len(TOPICS),
               "categories": [{"id": c["id"], "name": c["name"]} for c in CATEGORIES_46],
               "scoring": cs.scoring_info()})


@bp.post("/comparison/ask")
def ask():
    """The exact same question goes to all three chatbots; each runs its own pipeline and is timed separately."""
    import comparison_service as cs
    d = body()
    question = text_field(d, "question", max_len=cs.MAX_QUESTION_CHARS)
    try:
        data = cs.run_comparison(question, {"topic": str(d["context_topic"])[:80]} if d.get("context_topic") else None)
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", str(exc))
    uid = current_user_id()
    if uid:                                            # kept so a user-study rating refers to exactly what was shown
        data["run_id"] = db.save_comparison_run(uid, data["question"], data["results"],
                                                {k: r.get("version") for k, r in data["results"].items()})
    return ok(data)


# ------------------------------------------------------------------ user study (blinded)
def _participant():
    raw = f"{current_app.secret_key}|study|{current_user_id()}".encode()
    return "P-" + hashlib.sha256(raw).hexdigest()[:10]


@bp.get("/study/runs")
@login_required
def study_runs():
    runs = db.list_comparison_runs_for_user(current_user_id())
    if runs is None:
        raise ApiError("DATABASE_ERROR", "Your comparison runs could not be loaded.", 503)
    return ok(runs)


@bp.get("/study/runs/<run_id>")
@login_required
def study_run(run_id):
    """Responses are returned under neutral letters in a per-participant shuffled order (blinded)."""
    import random
    run = db.get_comparison_run(run_id)
    if not run or run.get("user_id") != current_user_id():
        raise ApiError("NOT_FOUND", "Comparison run not found.", 404)
    mine = db.get_participant_ratings(_participant(), run_id) or {}
    keys = [k for k in db.STUDY_ARCHITECTURES if k in run["results"]]
    rng = random.Random(f"{_participant()}|{run_id}")
    rng.shuffle(keys)
    responses = []
    for pos, k in enumerate(keys):
        r = run["results"][k]
        responses.append({"slot": chr(65 + pos), "token": k, "position": pos + 1, "response": r.get("response", ""),
                          "ratable": r.get("status") not in (None, "unavailable", "error"),
                          "my_rating": {c: mine[k].get(c) for c in db.STUDY_CRITERIA + ("comment",)} if k in mine else None})
    return ok({"run_id": run_id, "question": run["question"], "responses": responses, "criteria": list(db.STUDY_CRITERIA),
               "scale": "1 (poor) - 5 (excellent); leave blank for not applicable"})


@bp.post("/study/ratings")
@login_required
def study_submit():
    d = body()
    if d.get("consent") is not True:
        raise ApiError("CONSENT_REQUIRED", "Please tick the consent box before submitting.")
    result = db.save_comparison_study(_participant(), str(d.get("run_id", "")), d.get("ratings"), d.get("positions"))
    if not result.get("success"):
        raise ApiError("VALIDATION_ERROR", result.get("error") or "The ratings could not be saved.")
    return ok(result)


@bp.get("/study/summary")
@login_required
def study_summary():
    s = db.get_comparison_study_summary()
    if "error" in s:
        raise ApiError("DATABASE_ERROR", s["error"], 503)
    return ok(s)


@bp.get("/study/export.csv")
@login_required
def study_export():
    import csv
    import io
    from flask import Response
    rows = db.get_comparison_study_rows()
    if rows is None:
        raise ApiError("DATABASE_ERROR", "Study data could not be read.", 503)
    buf = io.StringIO()
    cols = ["study_response_id", "participant_id", "run_id", "question_text", "architecture", "response_shown",
            "display_position", "helpfulness", "relevance", "clarity", "trustworthiness", "safety", "comment",
            "model_version", "created_at", "updated_at"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=user_study.csv"})
