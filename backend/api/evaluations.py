"""Model Evaluation (dataset-based) + the analytics overview for the three MediChat chatbots.

Runs are executed by evaluation_service.py (same questions for all three chatbots, leakage checks,
stored in models/evaluation/runs/). Nothing here invents a number: every value is read from a
completed run file, and a metric with no run behind it is returned as null.
"""
from flask import Blueprint, Response, request

from api.common import ApiError, body, current_user_id, int_arg, login_required, ok, page_meta
from database import experiments as exp
from database import repository as repo

bp = Blueprint("evaluations", __name__)
MODELS = ("rule", "ml", "dl")
# Overall-best rule (documented in docs/evaluation-methodology.md): a chatbot is named overall best only if,
# on the latest completed runs, it is best or within TIE of the best on EVERY one of: held-out correctness,
# emergency guidance, off-topic declining and reliability. Speed and the automated quality estimate are
# reported but never decide it.
TIE = 0.02


def _ev():
    import evaluation_service as ev
    return ev


def _three(run):
    """Only the three MediChat chatbots (older runs on disk may contain archived models)."""
    if not run:
        return run
    out = dict(run)
    out["metrics"] = {k: v for k, v in (run.get("metrics") or {}).items() if k in MODELS}
    out["models_requested"] = [m for m in run.get("models_requested") or [] if m in MODELS]
    if run.get("safety"):
        out["safety"] = {**run["safety"], "per_model": {k: v for k, v in run["safety"].get("per_model", {}).items() if k in MODELS}}
    if "per_question" in run:
        out["per_question"] = [{**q, "models": {k: v for k, v in q["models"].items() if k in MODELS}} for q in run["per_question"]]
    return out


def _latest(dataset):
    for r in _ev().list_runs(500):
        if r["status"] == "completed" and r["dataset"] == dataset and set(MODELS) <= set(r.get("models_included") or []):
            return _three(_ev().get_run(r["run_id"]))
    return None


@bp.get("/evaluations/datasets")
@login_required
def datasets():
    return ok({"datasets": _ev().list_datasets(), "quick_size": _ev().QUICK_SIZE, "models": list(MODELS)})


@bp.post("/evaluations")
@login_required
def start():
    d = body()
    try:
        limit = d.get("limit")
        limit = int(limit) if limit not in (None, "", 0) else None
        st = _ev().start_run(str(d.get("dataset") or "held_out_test"), str(d.get("mode") or "quick"), limit=limit,
                             models=MODELS, user_id=current_user_id(), category=d.get("category") or None,
                             on_finish=exp.record_health_qa_run)
    except (TypeError, ValueError) as exc:
        raise ApiError("VALIDATION_ERROR", str(exc))
    except RuntimeError as exc:
        raise ApiError("EVALUATION_BUSY", str(exc), 409)
    return ok(st, 202)


@bp.get("/evaluations")
@login_required
def list_runs():
    page, per = int_arg("page", 1, 1, 1000), int_arg("per_page", 20, 1, 100)
    runs = [{**r, "models": {k: v for k, v in (r.get("models") or {}).items() if k in MODELS}} for r in _ev().list_runs(500)]
    return ok(runs[(page - 1) * per: page * per], meta=page_meta(page, per, len(runs)))


@bp.get("/evaluations/<run_id>")
@login_required
def get_run(run_id):
    st = _ev().get_run(run_id)
    if not st:
        raise ApiError("NOT_FOUND", "Evaluation run not found.", 404)
    st = _three(st)
    if request.args.get("records") != "1":
        st = {k: v for k, v in st.items() if k != "per_question"}
    return ok(st)


@bp.get("/evaluations/<run_id>/status")
@login_required
def status(run_id):
    st = _ev().get_status(run_id)
    if not st:
        raise ApiError("NOT_FOUND", "Evaluation run not found.", 404)
    return ok(st)


@bp.get("/evaluations/<run_id>/export.csv")
@login_required
def export(run_id):
    text = _ev().export_csv(run_id)
    if text is None:
        raise ApiError("NOT_FOUND", "Evaluation run not found.", 404)
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(text)))
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(r for r in rows if r.get("model") in MODELS)
    else:
        buf.write(text)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=evaluation_{run_id}.csv"})


# --------------------------------------------------------------------- analytics overview
def overview():
    held, multi, safe, bank = (_latest(d) for d in ("held_out_test", "multilingual", "safety", "question_bank"))
    names = {"rule": "Rule-Based", "ml": "ML - TF-IDF + SVM", "dl": "DL - DistilBERT"}
    per = {k: {"key": k, "name": names[k]} for k in MODELS}

    def runinfo(r):
        return None if not r else {"run_id": r["run_id"], "dataset": r["dataset"]["title"], "n": (r.get("selection") or {}).get("selected"),
                                   "finished_at": r.get("finished_at")}
    for k in MODELS:
        p = per[k]
        m = (held or {}).get("metrics", {}).get(k) or {}
        c = m.get("classification") or {}
        p["correctness"] = {"held_out_accuracy": c.get("accuracy"), "held_out_macro_f1": (c.get("macro") or {}).get("f1"),
                            "declined": m.get("no_confident_match"),
                            "multilingual_accuracy": (((multi or {}).get("metrics", {}).get(k) or {}).get("classification") or {}).get("accuracy"),
                            "question_bank_accuracy": (((bank or {}).get("metrics", {}).get(k) or {}).get("classification") or {}).get("accuracy")}
        p["response_time"] = {"median_ms": (m.get("latency") or {}).get("median_ms"), "mean_ms": (m.get("latency") or {}).get("mean_ms"),
                              "p95_ms": (m.get("latency") or {}).get("p95_ms")}
        p["reliability"] = {"answered_without_error": m.get("availability_rate"), "failed": m.get("failed"),
                            "questions": m.get("questions")}
        sm = ((safe or {}).get("safety") or {}).get("per_model", {}).get(k) or {}
        p["safety"] = {"emergency_guidance_rate": sm.get("emergency_recall"), "off_topic_declined_rate": sm.get("oos_decline_rate"),
                       "false_alarms": sm.get("false_alarms")}
        est = ((bank or {}).get("metrics", {}).get(k) or {}).get("response_estimates") or {}
        p["quality"] = {"keyword_coverage": est.get("keyword_coverage_mean"), "n": est.get("n"),
                        "label": "PROVISIONAL automated estimate (keyword coverage) - not human-validated"}

    criteria = {"correctness": lambda p: p["correctness"]["held_out_accuracy"],
                "emergency guidance": lambda p: p["safety"]["emergency_guidance_rate"],
                "off-topic declining": lambda p: p["safety"]["off_topic_declined_rate"],
                "reliability": lambda p: p["reliability"]["answered_without_error"]}
    leaders, missing = {}, []
    for name, f in criteria.items():
        vals = {k: f(per[k]) for k in MODELS}
        if any(v is None for v in vals.values()):
            missing.append(name)
            continue
        best = max(vals.values())
        leaders[name] = [k for k, v in vals.items() if best - v <= TIE]
    speeds = {k: per[k]["response_time"]["median_ms"] for k in MODELS if per[k]["response_time"]["median_ms"] is not None}
    if missing:
        verdict = {"status": "insufficient", "winner": None,
                   "reason": "No reliable overall winner can be determined yet: no completed run measures " + ", ".join(missing) + "."}
    else:
        common = set(MODELS)
        for ks in leaders.values():
            common &= set(ks)
        if len(common) == 1:
            w = common.pop()
            verdict = {"status": "winner", "winner": w,
                       "reason": f"{names[w]} is best (or within {TIE * 100:.0f} points of the best) on every criterion: " + ", ".join(leaders) + "."}
        else:
            verdict = {"status": "none", "winner": None,
                       "reason": "No single chatbot leads on every criterion, so no overall winner is declared. "
                                 + "; ".join(f"{n}: {', '.join(names[k] for k in ks)}" for n, ks in leaders.items()) + "."}
    verdict["method"] = (f"A chatbot is named overall best only if it is best or within {TIE * 100:.0f} percentage points of the best on held-out "
                         "correctness, emergency guidance, off-topic declining and reliability. Response time and the automated quality "
                         "estimate are reported but never decide it; the metrics are not combined into one score.")
    verdict["fastest"] = min(speeds, key=speeds.get) if speeds else None
    return {"chatbots": [per[k] for k in MODELS], "overall": verdict, "leaders": leaders,
            "runs": {"held_out_test": runinfo(held), "multilingual": runinfo(multi), "safety": runinfo(safe), "question_bank": runinfo(bank)},
            "safety_detection": ((safe or {}).get("safety") or {}).get("emergency_detection"),
            "evaluation_required": held is None}


@bp.get("/analytics/overview")
@login_required
def analytics_overview():
    return ok(overview())


@bp.get("/analytics/summary")
@login_required
def summary():
    return ok({"activity": repo.user_activity(current_user_id()), "experiments": exp.counts(), "overview": overview()})


@bp.get("/analytics/history")
@login_required
def history():
    return ok(exp.history(request.args.get("dataset") or "held_out_test"))
