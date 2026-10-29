"""
registry.py - the six symptom architectures, loaded once per process, run under identical conditions.

run(key, text, context) -> architecture result + safety (chatbot.medical.safety.apply)
compare(text, keys)     -> the same text through each selected architecture
"""
import threading

from chatbot.medical import safety

ORDER = ("rule_based", "nlp_based", "classification", "retrieval_based", "rag_based", "generation_based")
MAX_CHARS = 1000

_instances, _lock = {}, threading.Lock()


def _make(key):
    if key == "rule_based":
        from chatbot.rule_based.architecture import RuleBasedArchitecture as C
    elif key == "nlp_based":
        from chatbot.nlp_based.architecture import NlpBasedArchitecture as C
    elif key == "classification":
        from chatbot.classification.architecture import ClassificationArchitecture as C
    elif key == "retrieval_based":
        from chatbot.retrieval_based.architecture import RetrievalArchitecture as C
    elif key == "rag_based":
        from chatbot.rag_based.architecture import RagArchitecture as C
    elif key == "generation_based":
        from chatbot.generation_based.architecture import GenerationArchitecture as C
    else:
        raise KeyError(key)
    return C()


def get(key):
    if key not in ORDER:
        raise KeyError(f"Unknown architecture '{key}'. Choose from: {', '.join(ORDER)}")
    with _lock:
        if key not in _instances:
            _instances[key] = _make(key)
        return _instances[key]


def reset():
    with _lock:
        _instances.clear()


def describe():
    return [get(k).info() for k in ORDER]


def clean(text):
    text = " ".join(str(text or "").split())
    if not text:
        raise ValueError("Please enter a symptom description.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Please keep the message under {MAX_CHARS} characters.")
    return text


def run(key, text, context=None, assessed=None):
    raw = get(key).answer(text, context or {})
    return safety.apply(text, raw, assessed)


def compare(text, keys=None, context=None):
    text = clean(text)
    keys = [k for k in (keys or ORDER) if k in ORDER] or list(ORDER)
    assessed = safety.assess_input(text)            # once, shared - identical for every architecture
    results = {k: run(k, text, context, assessed) for k in keys}
    ok = [r for r in results.values() if r["status"] == "ok"]
    times = {k: r["response_time_ms"] for k, r in results.items() if r["response_time_ms"] is not None}
    summary = {
        "answered": [k for k, r in results.items() if r["status"] == "ok"],
        "no_match": [k for k, r in results.items() if r["status"] == "no_match"],
        "failed": [k for k, r in results.items() if r["status"] in ("error", "unavailable")],
        "fastest": min(times, key=times.get) if times else None,
        "slowest": max(times, key=times.get) if times else None,
        "labels": {k: (r.get("prediction") or {}).get("label_name") for k, r in results.items() if r.get("prediction")},
        "note": ("Response time and coverage are shown for comparison only. No architecture is ranked as medically "
                 "better: speed and keyword overlap do not measure correctness."),
    }
    if len({v for v in summary["labels"].values() if v}) > 1:
        summary["label_disagreement"] = True
    return {"input": text, "safety": {"emergency": assessed["emergency"], "mode": assessed["mode"],
                                      "categories": assessed["categories"], "notice": assessed["notice"]},
            "results": results, "summary": summary, "answered_count": len(ok)}
