"""
comparison_service.py - ONE question -> THREE independent pipelines.

    Rule-Based        chatbot/health_qa/pipelines.py :: RuleBasedPipeline
    TF-IDF + SVM      chatbot/health_qa/pipelines.py :: SvmPipeline
    DistilBERT        chatbot/health_qa/pipelines.py :: DistilBertPipeline

Each pipeline gets the same original question, runs on its own, and returns its own
result. If one fails or is unavailable its card shows that real state; another model's
answer is never substituted. rank_responses() adds a transparent, single-question
"Best Overall Response" (safety-gated, heuristic). It is NOT a ranking of the architectures:
the held-out results in models/evaluation/comparison_eval.json remain the evidence for that.
"""
import re
import threading

from chatbot.health_qa import language as _language
from chatbot.health_qa import safety
from chatbot.health_qa.knowledge import PRESET_QUESTIONS, TOPIC_BY_ID
from chatbot.health_qa.pipelines import RuleBasedPipeline, SvmPipeline, DistilBertPipeline

ORDER = ("rule", "ml", "dl")
PIPELINE_CLASSES = {"rule": RuleBasedPipeline, "ml": SvmPipeline, "dl": DistilBertPipeline}
BOT_NAMES = {"rule": "Rule-Based", "ml": "ML - TF-IDF + SVM", "dl": "DL - DistilBERT"}
MAX_QUESTION_CHARS = 1000

_pipelines, _lock = {}, threading.Lock()


def get_pipeline(key):
    """Load once per process. Pipelines are stateless at inference time, so sharing them
    between requests does not mix users' data."""
    with _lock:
        if key not in _pipelines:
            _pipelines[key] = PIPELINE_CLASSES[key]()
        return _pipelines[key]


def reset_pipelines():
    with _lock:
        _pipelines.clear()


def warm_up():
    def work():
        for key in ORDER:
            try:
                get_pipeline(key)
            except Exception as exc:
                print("[COMPARISON] could not load", key, exc)
    threading.Thread(target=work, daemon=True).start()


def get_examples():
    """Clickable suggestions only - the question box accepts any text."""
    return [{"emoji": e, "category": c, "question": q} for e, c, q, _ in PRESET_QUESTIONS]


def model_versions():
    out = {}
    for key in ORDER:
        try:
            out[key] = get_pipeline(key).info().get("version")
        except Exception:
            out[key] = None
    return out


def clean_question(question):
    return re.sub(r"\s+", " ", str(question or "")).strip()


def run_one(key, question, context=None):
    base = {"key": key, "name": BOT_NAMES[key]}
    try:
        pipe = get_pipeline(key)
        info = pipe.info()
        out = pipe.predict(question, context=context) if context else pipe.predict(question)
    except Exception as exc:                            # inference failure stays inside this card
        return {**base, "status": "error", "response": "", "intent": None, "confidence": None,
                "confidence_kind": "", "inference_ms": None, "architecture": None,
                "error": f"{type(exc).__name__}: {exc}", "intent_title": None,
                "language": None, "canonical_text": None, "symptoms": [], "question_kind": None,
                "reply_topic": None, "handled_by": "model", "top_k": [], "category": None, "categories": [],
                "safety_override": False}
    topic = TOPIC_BY_ID.get(out["intent"]) if out["intent"] else None
    return {**base, **out, "architecture": info.get("architecture"), "version": info.get("version"),
            "artifact": info.get("artifact"),
            "intent_title": topic["id"].replace("_", " ").title() if topic else None}


def structure_of(result):
    """Objective, automatic structure facts about ONE reply. These are NOT quality or correctness scores."""
    text = result.get("response") or ""
    return {
        "characters": len(text),
        "sections": len(re.findall(r"^### ", text, flags=re.M)),
        "has_when_to_seek_help": bool(re.search(r"^### (When to seek|Warning signs|Doctor to consult|Doctor ko kab|Khatre|Kaun sa doctor|डॉक्टर को कब|खतरे|कौन से डॉक्टर)",
                                                text, flags=re.M)),
        "has_self_care_steps": bool(re.search(r"^### (What you can do|Aap kya kar|आप क्या कर)", text, flags=re.M)),
        "asks_follow_up_question": "?" in text.split("###")[-1] if text else False,
        "mentions_emergency_number": "112" in text,
    }


def summarise_differences(results):
    """Plain-language differences between the replies. No winner is chosen, and nothing here
    says which reply is medically correct (that needs human review - see the User Study)."""
    notes, ok = [], {k: r for k, r in results.items() if r["status"] in ("ok", "no_match", "small_talk")}
    for k, r in results.items():
        if r["status"] in ("unavailable", "error"):
            notes.append(f"{r['name']} could not run: {r['error']}")
    if not ok:
        return notes
    intents = {k: r["intent"] for k, r in ok.items()}
    if any(r["status"] == "small_talk" for r in ok.values()):
        notes.append("This was greeting or small talk, handled by a shared front-end before any model ran, so all replies are identical by design.")
        return notes
    distinct = {i for i in intents.values() if i}
    if len(distinct) > 1:
        pretty = ", ".join(f"{results[k]['name']}: {i or 'no confident match'}" for k, i in intents.items())
        notes.append("The models predicted different topics (" + pretty + "), so their replies cover different information.")
    elif len(ok) > 1 and distinct:
        notes.append("The models that answered predicted the same topic; differences are in how much detail each reply includes.")
    unmatched = [results[k]["name"] for k, r in ok.items() if r["status"] == "no_match"]
    if unmatched:
        notes.append(", ".join(unmatched) + " did not find a confident health topic and asked for clarification or declined to guess.")
    lens = {k: structure_of(r) for k, r in ok.items()}
    longest = max(lens, key=lambda k: lens[k]["characters"])
    shortest = min(lens, key=lambda k: lens[k]["characters"])
    if longest != shortest and lens[longest]["characters"] > 1.4 * max(1, lens[shortest]["characters"]):
        notes.append(f"{results[longest]['name']} gave the longest reply and {results[shortest]['name']} the shortest "
                     "(length alone does not indicate quality).")
    missing = [results[k]["name"] for k, l in lens.items() if not l["has_when_to_seek_help"] and ok[k]["status"] == "ok"]
    if missing:
        notes.append("No explicit 'when to seek help' section in: " + ", ".join(missing) + ".")
    return notes


# ---------------------------------------------------------------------------------------------
# BEST OVERALL RESPONSE (single question). Reuses chatbot/health_qa/evaluator.py unchanged.
# ---------------------------------------------------------------------------------------------
import re as _re
from chatbot.health_qa import evaluator as _ev

SCORING_VERSION = "2"             # bump when a scoring rule changes (shown in the UI, stored nowhere)
RANKING_CONFIG = {
    "weights": {"correctness": 0.4, "safety": 0.3, "quality": 0.2, "speed": 0.1},   # renormalised over available parts
    "tie_margin": 2.0,            # points; closer than this is reported as a tie
    "min_candidates": 2,          # a "best" needs at least two comparable replies
}
_DEVANAGARI = _re.compile(r"[\u0900-\u097F]")


_GT = {"index": None}
_GT_LOCK = threading.Lock()
_GT_ORDER = ("held_out_test", "multilingual", "question_bank")     # exact-label sets first


def _ground_truth_index():
    """Index of the project's own labelled questions (datasets/*.csv, via evaluation_service.load_dataset).
    Rows whose label itself is invalid/ambiguous are skipped; rows merely excluded from the AGGREGATE
    evaluation for training overlap/duplicates still carry a valid label, so they are kept here."""
    with _GT_LOCK:
        if _GT["index"] is None:
            import evaluation_service as es
            idx = {}
            for name in _GT_ORDER:
                try:
                    data = es.load_dataset(name)
                    lmap = es.load_label_map() if data["spec"]["kind"] == "mapped" else {}
                except Exception:
                    continue
                for item in data["rows"]:
                    why = item.get("skip_reason") or ""
                    if why and not (why.startswith("overlaps") or why.startswith("duplicate")):
                        continue
                    idx.setdefault(es._norm(item["question"]), (name, data["spec"]["kind"], item, lmap))
            _GT["index"] = idx
        return _GT["index"]


def find_ground_truth(question):
    """Expected label for this EXACT question if it is in the project's labelled datasets, else None."""
    try:
        import evaluation_service as es
        return _ground_truth_index().get(es._norm(question))
    except Exception:
        return None


def _correctness(gt, r):
    """Same rule as evaluation_service._score_classification: predicted topic is the expected one
    (lenient for the 19-category question bank). 100 = correct, 0 = wrong. None if no ground truth."""
    if not gt:
        return None
    name, kind, item, lmap = gt
    intent = r.get("intent")
    if kind == "exact":
        ok = intent == item["expected"]
    else:
        ok = bool(intent) and item["expected"] in (lmap.get(intent) or [])
    return 100 if ok else 0


def scoring_info():
    """The scoring rules as data, so templates and the Evaluation page show the SAME numbers the backend uses."""
    return {"version": SCORING_VERSION, "weights": dict(RANKING_CONFIG["weights"]),
            "tie_margin": RANKING_CONFIG["tie_margin"], "min_candidates": RANKING_CONFIG["min_candidates"]}


def reply_language(r, text=""):
    """Language of a reply: the pipeline's own language tag, else Devanagari detection, else English."""
    lang = ((r or {}).get("language") or {}).get("lang") if isinstance((r or {}).get("language"), dict) else None
    if lang in (None, "", "en") and _DEVANAGARI.search(text or ""):
        return "hi"
    return lang or "en"


def score_text(question, canonical, emergency, text, lang="en"):
    """Safety + quality of ONE reply with evaluator.check_safety / check_quality. The single place these
    rules are applied, used by the Comparison tab and by the Evaluation page.

    The rules are English-word regexes (doctor advice, disclaimer wording, relevance by word overlap), so a
    Hindi or Hinglish reply cannot be scored by them reliably: it returns supported=False with the reason,
    never a made-up number.
    """
    if lang != "en":
        label = {"hi": "Hindi", "hinglish": "Hinglish"}.get(lang, "non-English")
        return {"supported": False,
                "reason": f"the reply is in {label} - the English-only safety and quality rules cannot score it reliably"}
    sf = _ev.check_safety(text, emergency)
    ql = _ev.check_quality(canonical or question, text)
    return {"supported": True, "reason": None, "safety": sf, "quality": ql}


def _score_one(key, question, canonical, emergency, r, gt=None):
    """Safety + quality of ONE reply, using evaluator.check_safety / check_quality.
    Returns None for the scores that cannot be calculated reliably (never a guess)."""
    out = {"key": key, "name": r.get("name"), "eligible": False, "excluded_reason": None,
           "correctness": None, "safety": None, "safety_level": None, "safety_notes": [], "quality": None,
           "quality_parts": None, "quality_notes": [], "speed": None,
           "inference_ms": r.get("inference_ms"), "unavailable": [], "overall": None, "content": None}
    text = r.get("response") or ""
    if r.get("status") != "ok" or not text.strip():
        out["excluded_reason"] = {"unavailable": "model unavailable", "error": "model failed",
                                  "no_match": "no confident topic - declined to answer",
                                  "small_talk": "greeting/small talk"}.get(r.get("status"), "no reply")
        return out
    sc = score_text(question, canonical, emergency, text, reply_language(r, text))
    if not sc["supported"]:
        # Topic correctness does not depend on the reply language, so it is still reported when the
        # question is labelled; safety and quality stay unavailable and the reply cannot be crowned.
        out["correctness"] = _correctness(gt, r)
        out["unavailable"] = ["safety", "quality"] + ([] if gt else ["correctness"])
        out["excluded_reason"] = sc["reason"]
        return out
    sf, ql = sc["safety"], sc["quality"]
    out.update(eligible=True, correctness=_correctness(gt, r), safety=sf["score"], safety_level=sf["level"], safety_notes=sf["notes"],
               quality=ql["score"], quality_notes=ql["notes"],
               quality_parts={k: ql[k] for k in ("relevance", "completeness", "clarity")})
    if sf["level"] == "Unsafe":
        out["eligible"] = False
        out["excluded_reason"] = "failed the safety check (" + "; ".join(sf["notes"]) + ")"
    return out


def rank_responses(question, results, assessed=None, canonical=None, config=None):
    """Choose the Best Overall Response for ONE question, or say honestly that none can be chosen.

    Rules (all visible to the user in the returned 'method'):
      1. Only replies with status 'ok' are compared; failed / unavailable / no-match replies cannot win.
      2. A reply rated Unsafe by evaluator.check_safety (e.g. emergency question without urgent
         advice) is excluded, however fast or fluent it is.
      3. overall = weighted correctness 40 + safety 30 + quality 20 + speed 10 (renormalised over what is
         available). Correctness needs a labelled question; otherwise it is "unavailable", never guessed.
         Speed = fastest reply's time / this reply's time. Model confidence is never used.
      4. If the lead is under tie_margin, or the lead comes from speed alone, the result is a tie.
      5. Fewer than min_candidates comparable replies -> 'Unable to determine a reliable winner'.
    Quality is a heuristic proxy (relevance/completeness/clarity); it is not medical correctness.
    """
    cfg = {**RANKING_CONFIG, **(config or {})}
    emergency = bool((assessed or {}).get("emergency")) or _ev.is_emergency(question)
    gt = find_ground_truth(question)
    scores = {k: _score_one(k, question, canonical, emergency, results[k], gt) for k in ORDER if k in results}
    pool = [x for x in scores.values() if x["eligible"]]

    times = [x["inference_ms"] for x in pool if x["inference_ms"] and x["inference_ms"] > 0]
    fastest = min(times) if len(times) >= 2 else None
    w = cfg["weights"]
    for x in pool:
        if fastest and x["inference_ms"] and x["inference_ms"] > 0:
            x["speed"] = round(100.0 * fastest / x["inference_ms"], 1)
        else:
            x["unavailable"].append("speed")
        if x["correctness"] is None:
            x["unavailable"].append("correctness")
        parts = {"correctness": x["correctness"], "safety": x["safety"], "quality": x["quality"], "speed": x["speed"]}
        have = {k: v for k, v in parts.items() if v is not None}
        x["overall"] = round(sum(w[k] * v for k, v in have.items()) / sum(w[k] for k in have), 1)
        c = {k: v for k, v in have.items() if k != "speed"}
        x["content"] = round(sum(w[k] * v for k, v in c.items()) / sum(w[k] for k in c), 1)

    truth = ({"available": True, "dataset": gt[0], "expected": gt[2]["expected"], "id": gt[2]["id"]} if gt
             else {"available": False, "note": "This exact question is not in the labelled evaluation datasets, so "
                   "correctness cannot be scored. The winner uses safety, quality and speed only (weights re-balanced)."})
    method = {"version": SCORING_VERSION, "weights": w, "tie_margin": cfg["tie_margin"], "emergency_question": emergency, "ground_truth": truth,
              "language_scope": "Safety and quality rules are English-only; Hindi and Hinglish replies are reported as unavailable, not scored.",
              "scope": "This question only. It is not the best model across the evaluation dataset - "
                       "see the Model Evaluation results for that.",
              "limits": "Quality is an automatic proxy (word overlap, completeness, length); safety checks "
                        "look for doctor advice, a disclaimer, doses, diagnosis claims and urgent advice. "
                        "Neither proves the reply is medically correct. Model confidence is not used."}
    excluded = [{"key": x["key"], "name": x["name"], "reason": x["excluded_reason"]}
                for x in scores.values() if not x["eligible"]]
    timed = [x for x in pool if x["inference_ms"] and x["inference_ms"] > 0]
    fastest_x = min(timed, key=lambda x: x["inference_ms"]) if len(timed) >= 2 else None
    base = {"scores": scores, "excluded": excluded, "method": method, "winner_key": None,
            "winner_name": None, "winner_score": None, "tied_keys": [],
            "fastest_key": fastest_x["key"] if fastest_x else None,       # informational only - never decides a winner
            "fastest_name": fastest_x["name"] if fastest_x else None}

    if len(pool) < cfg["min_candidates"]:
        why = ("Fewer than two replies could be compared reliably" +
               (": " + "; ".join(f"{e['name']} - {e['reason']}" for e in excluded) if excluded else "") + ".")
        return {**base, "status": "undetermined", "headline": "No Clear Winner",
                "reason": why}

    pool.sort(key=lambda x: (x["overall"], x["safety"], x["quality"]), reverse=True)
    top, nxt = pool[0], pool[1]
    lead, content_lead = top["overall"] - nxt["overall"], top["content"] - nxt["content"]
    if lead < cfg["tie_margin"] or content_lead < cfg["tie_margin"]:
        tied = [x["key"] for x in pool if top["overall"] - x["overall"] < cfg["tie_margin"]
                or top["content"] - x["content"] < cfg["tie_margin"]]
        nm = [scores[k]["name"] for k in tied]
        names = nm[0] if len(nm) == 1 else ", ".join(nm[:-1]) + " and " + nm[-1]
        why = (f"{names} scored within {cfg['tie_margin']:g} points on safety and quality, "
               "so no single reply is declared best." +
               (" Any lead came from speed alone, which is not enough to decide." if lead >= cfg["tie_margin"] else ""))
        if base["fastest_name"] and base["fastest_key"] in tied:
            why += f" {base['fastest_name']} responded fastest."
        return {**base, "status": "tie", "headline": "No Clear Winner", "reason": why,
                "tied_keys": tied}

    parts = ([f"correctness {top['correctness']}/100"] if top["correctness"] is not None else []) + \
            [f"safety {top['safety']}/100", f"quality {top['quality']}/100"]
    if top["speed"] is not None:
        parts.append(f"speed {top['speed']:g}/100")
    why = (f"{top['name']} scored {top['overall']}/100 ({', '.join(parts)}), "
           f"{lead:.1f} points ahead of {nxt['name']} ({nxt['overall']}/100).")
    if excluded:
        why += " Not compared: " + "; ".join(f"{e['name']} ({e['reason']})" for e in excluded) + "."
    return {**base, "status": "winner", "headline": "Best Response for This Question", "reason": why,
            "winner_key": top["key"], "winner_name": top["name"], "winner_score": top["overall"]}



def run_comparison(question, context=None):
    question = clean_question(question)
    if not question:
        raise ValueError("Please enter a healthcare question.")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"Please keep the question under {MAX_QUESTION_CHARS} characters.")

    assessed = safety.assess(question)                  # independent of every model
    analysis = _language.analyse(question)              # identical preprocessing for all three models
    results = {key: run_one(key, question, context) for key in ORDER}      # same question, same context
    for r in results.values():
        r["structure"] = structure_of(r) if r["status"] in ("ok", "no_match", "small_talk") else None
    return {
        "question": question,
        "language": {"lang": analysis["lang"], "script": analysis["script"], "confidence": analysis["lang_confidence"]},
        "canonical_text": analysis["canonical"],
        "symptoms": analysis["symptoms"],
        "safety": assessed,
        "results": results,
        "overall_selection": rank_responses(question, results, assessed, analysis.get("canonical")),
        "notes": summarise_differences(results),
        "notes_kind": "automatic structural comparison - not a quality score and not a statement of medical correctness",
        "disclaimer": "Research comparison of three chatbot architectures. Not a medical diagnosis. "
                      "Model confidence is not medical certainty.",
    }


# ---------------------------------------------------------------------------------------------
# CHAT ROUTING POLICY (shared pipelines, one answer per question)
# ---------------------------------------------------------------------------------------------
import json as _json
import os as _os

_EVAL_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "models", "evaluation", "comparison_eval.json")
CHAT_DEFAULT_ORDER = ("rule", "ml", "dl")      # used only if no held-out evaluation file exists


def chat_routing_policy():
    """Documented policy: answer with the AVAILABLE pipeline that has the highest accuracy on the
    held-out test set in models/evaluation/comparison_eval.json (ties -> rule, ml, dl order). If no
    evaluation exists, fall back to the fixed order. The reply states which model answered and that
    no comparison was made; use the Comparison page to see all three."""
    scores = {}
    try:
        with open(_EVAL_FILE, encoding="utf-8") as f:
            for e in _json.load(f)["pipelines"]:
                if e.get("status") == "evaluated":
                    scores[e["key"]] = e["classification"]["accuracy"]
    except Exception:
        pass
    order = sorted(ORDER, key=lambda k: (-scores.get(k, -1.0), CHAT_DEFAULT_ORDER.index(k)))
    return {"order": order, "held_out_accuracy": scores,
            "rule": "highest held-out test accuracy among available pipelines"}


def route_chat(question, context=None):
    """Answer one chat message with ONE pipeline chosen by chat_routing_policy().
    Never claims a comparison. Unavailable/failed pipelines are skipped and listed."""
    question = clean_question(question)
    if not question:
        raise ValueError("Please enter a healthcare question.")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"Please keep the question under {MAX_QUESTION_CHARS} characters.")
    policy = chat_routing_policy()
    skipped = []
    for key in policy["order"]:
        res = run_one(key, question, context)
        if res["status"] in ("ok", "no_match", "small_talk"):
            if res["status"] != "small_talk":
                # Full-detail presentation for Chat. The TOPIC is still the chosen model's own prediction.
                from chatbot.health_qa import chat_reply
                analysis = _language.analyse(question)
                text, override = chat_reply.compose("chat", res["intent"], safety.assess(question), analysis,
                                                    (context or {}).get("topic"), reply_topic=res.get("reply_topic"))
                res = {**res, "response": text, "safety_override": override or res.get("safety_override"),
                       "presentation": "chat (full detail)"}
            return {"question": question, "answered_by": key, "answered_by_name": BOT_NAMES[key],
                    "result": res, "safety": safety.assess(question), "skipped": skipped,
                    "language": res.get("language"), "reply": res.get("response", ""),
                    "routing": policy, "compared_models": False,
                    "disclaimer": "General health information only - not a diagnosis or a substitute for a doctor."}
        skipped.append({"key": key, "reason": res.get("error")})
    raise RuntimeError("No chatbot pipeline is available: " + "; ".join(str(s["reason"]) for s in skipped))
