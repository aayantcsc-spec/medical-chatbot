"""
safety.py - the ONE safety layer shared by the six symptom architectures, the Health Q&A bots and Chat.

Two independent checks:

1. assess_input(text)      - emergency detection on the USER'S message only (delegates to
                             chatbot.health_qa.safety.assess: English, Hindi and Hinglish patterns).
                             Never looks at a model's output or confidence.
2. check_response(text, emergency)
                           - a GATE on a chatbot reply. It REJECTS (does not merely down-score) a reply
                             that gives medicine doses, claims a diagnosis, discourages seeing a doctor,
                             or - for an emergency message - lacks urgent-care advice.

apply(text, result) combines both for one architecture result: an emergency notice always comes
first and replaces ordinary advice; a rejected reply is replaced by a safe fallback, and the
original is kept only in `withheld_response` for research transparency.
"""
from chatbot.health_qa import safety as _qa_safety
from chatbot.health_qa.evaluator import DOSE, DIAGNOSIS, AVOID_DOCTOR, URGENT_ADVICE

SAFE_FALLBACK = ("I can't give a reliable answer to this. Please speak to a doctor or pharmacist about your symptoms. "
                 "If you feel very unwell or your symptoms are getting worse quickly, seek medical care urgently. "
                 "This is general information, not a diagnosis.")


def assess_input(text):
    return _qa_safety.assess(text)


def check_response(text, emergency=False):
    """Return {'status': 'passed'|'rejected', 'reasons': [...]} for one reply."""
    reasons = []
    t = str(text or "")
    if DOSE.search(t):
        reasons.append("gives a medicine dose")
    if DIAGNOSIS.search(t):
        reasons.append("claims a diagnosis")
    if AVOID_DOCTOR.search(t):
        reasons.append("discourages seeing a doctor")
    if emergency and not URGENT_ADVICE.search(t):
        reasons.append("emergency message without urgent-care advice")
    return {"status": "rejected" if reasons else "passed", "reasons": reasons}


def emergency_text(assessed, user_text=""):
    """Emergency reply in the user's language (English, Hindi or Hinglish) - same wording as Health Q&A."""
    try:
        from chatbot.health_qa import chat_reply, language
        return chat_reply.emergency_text(assessed, None, {"lang": language.detect_language(user_text)["lang"]})
    except Exception:                                   # never let localisation hide the emergency notice
        lines = [assessed.get("notice") or _qa_safety.EMERGENCY_NOTICE]
        lines += [g for g in assessed.get("guidance") or [] if g]
        return "\n\n".join(lines)


def apply(user_text, result, assessed=None):
    """Return a copy of an architecture result with safety applied.

    Adds: safety = {'status': 'emergency_override'|'passed'|'rejected'|'not_applicable',
                    'emergency': bool, 'categories': [...], 'reasons': [...]}"""
    assessed = assessed if assessed is not None else assess_input(user_text)
    out = dict(result)
    if assessed.get("emergency"):
        out["withheld_response"] = result.get("response") or None
        out["response"] = emergency_text(assessed, user_text)
        out["safety"] = {"status": "emergency_override", "emergency": True, "categories": assessed["categories"],
                         "reasons": ["urgent-care guidance replaces the ordinary reply"]}
        return out
    if result.get("status") in ("error", "unavailable") or not result.get("response"):
        out["safety"] = {"status": "not_applicable", "emergency": False, "categories": [], "reasons": []}
        return out
    gate = check_response(result["response"])
    if gate["status"] == "rejected":
        out["withheld_response"] = result["response"]
        out["response"] = SAFE_FALLBACK
    out["safety"] = {"status": gate["status"], "emergency": False,
                     "categories": assessed.get("categories") or [], "reasons": gate["reasons"],
                     "informational_emergency_topic": assessed.get("mode") == "informational"}
    return out
