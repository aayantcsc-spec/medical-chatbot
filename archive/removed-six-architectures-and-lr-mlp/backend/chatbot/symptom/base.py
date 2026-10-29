"""
base.py - the contract every symptom architecture follows.

An architecture implements `_answer(text, context) -> dict` with any of:
    status       "ok" | "no_match" | "unsupported"
    response     reply text (general guidance; never a diagnosis or a dose)
    extracted    what the architecture understood (symptoms, entities, duration ...)
    evidence     records it relied on (rules fired, retrieved rows, model scores ...)
    prediction   {"label", "label_name", "score", "score_kind"} - ONLY for architectures that predict a label

`Architecture.answer()` wraps that with timing, error capture and a uniform result shape.
It does NOT apply safety: registry.run() does that for every architecture in the same way.
"""
import time

RESULT_KEYS = ("architecture", "name", "status", "response", "response_time_ms", "extracted",
               "evidence", "prediction", "error")

DISCLAIMER = "This is general information, not a diagnosis. Please see a doctor about your own situation."


class Architecture:
    key = ""             # stable identifier used in the API and stored results
    name = ""            # display name
    method = ""          # one-line method summary shown on comparison cards
    predicts_label = False

    def available(self):
        return True, None

    def info(self):
        ok, why = self.available()
        return {"key": self.key, "name": self.name, "method": self.method, "available": ok,
                "unavailable_reason": why, "predicts_label": self.predicts_label, "version": self.version()}

    def version(self):
        return "v1"

    def answer(self, text, context=None):
        base = {"architecture": self.key, "name": self.name, "status": "error", "response": "",
                "response_time_ms": None, "extracted": {}, "evidence": [], "prediction": None, "error": None}
        ok, why = self.available()
        if not ok:
            return {**base, "status": "unavailable", "error": why}
        start = time.perf_counter()
        try:
            out = self._answer(str(text or ""), context or {})
        except Exception as exc:                          # one failing module never breaks the others
            return {**base, "response_time_ms": round((time.perf_counter() - start) * 1000, 3),
                    "error": f"{type(exc).__name__}: {exc}"}
        ms = round((time.perf_counter() - start) * 1000, 3)
        return {**base, **{k: v for k, v in out.items() if k in RESULT_KEYS}, "response_time_ms": ms,
                "architecture": self.key, "name": self.name}

    def _answer(self, text, context):
        raise NotImplementedError


def join(*parts):
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def bullet(items):
    return "\n".join(f"- {i}" for i in items if i)
