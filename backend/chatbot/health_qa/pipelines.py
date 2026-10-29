"""
pipelines.py - the three independent inference pipelines shared by Chat and Comparison.

    RuleBasedPipeline   rule_engine.py (emergency rules, spelling repair, keyword rules)  no training
    SvmPipeline         TF-IDF + linear SVM                (models/svm/)
    DistilBertPipeline  fine-tuned distilbert-base-uncased (models/distilbert_medical/)

Each pipeline predicts its OWN intent. The reply text is then produced by responder.py from the
curated knowledge base, with the same emergency override for all three (safety.assess looks at
the question only, never at a model's output).

Public API of every pipeline (same for all three):
    predict(question, context=None) -> dict   full result used by the UI
    predict_intent(text)            -> intent id or None
    predict_with_confidence(text)   -> (intent or None, confidence or None)
    predict_top_k(text, k=3)        -> [(intent, confidence), ...]
    model_info()                    -> dict (availability, artifact, metadata)
`context` = {"topic": <last intent id>} lets follow-up questions ("explain simpler") refer to the
previous topic. A pipeline that cannot run returns status "unavailable" with the real reason and
never borrows another model's answer.
"""
import json
import math
import os
import pickle
import time

from chatbot.health_qa import chat_reply, language, localized, safety
from chatbot.health_qa.dataset import normalise
from chatbot.health_qa.responder import category_info

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "models")
SVM_DIR = os.path.join(MODEL_DIR, "svm")
DISTILBERT_DIR = os.path.join(MODEL_DIR, "distilbert_medical")

RESULT_KEYS = ("status", "response", "intent", "confidence", "confidence_kind", "inference_ms",
               "error", "category", "categories", "safety_override", "top_k",
               "language", "canonical_text", "symptoms", "question_kind", "reply_topic", "handled_by")


def _result(status, response="", intent=None, confidence=None, kind="", ms=None, error=None,
            override=False, top_k=None, analysis=None, reply_topic=None, handled_by="model"):
    cat = category_info(intent) if intent else {"category": None, "categories": []}
    an = analysis or {}
    return {"status": status, "response": response, "intent": intent,
            "confidence": None if confidence is None else round(float(confidence), 4),
            "confidence_kind": kind, "inference_ms": None if ms is None else round(ms, 3),
            "error": error, "category": cat["category"], "categories": cat["categories"],
            "safety_override": override, "top_k": top_k or [],
            "language": {"lang": an.get("lang", "en"), "script": an.get("script"), "confidence": an.get("lang_confidence")},
            "canonical_text": an.get("canonical"), "symptoms": an.get("symptoms", []),
            "question_kind": an.get("question_kind"), "reply_topic": reply_topic, "handled_by": handled_by}


def _softmax(scores):
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


class _Base:
    """Shared public methods. Subclasses implement _rank(text) -> (ranking, accepted_intent_or_None)."""
    key = name = kind = style = ""

    def available(self):
        return True

    def predict_top_k(self, text, k=3):
        if not self.available():
            return []
        ranking, _ = self._rank(text)
        return [(i, round(float(c), 4)) for i, c in ranking[:k]]

    def predict_with_confidence(self, text):
        if not self.available():
            return None, None
        ranking, accepted = self._rank(text)
        conf = ranking[0][1] if ranking else None
        return accepted, (None if conf is None else round(float(conf), 4))

    def predict_intent(self, text):
        return self.predict_with_confidence(text)[0]

    def model_info(self):
        return self.info()

    def predict(self, question, context=None):
        if not self.available():
            return _result("unavailable", "", error=self.error, kind=self.kind)
        start = time.perf_counter()
        analysis = language.analyse(question)              # same preprocessing for all three models
        safe = safety.assess(question)                     # question only; never a model output
        if analysis["small_talk"] and not safe["emergency"]:
            # Greetings / thanks / bye are answered by the shared front-end, NOT by the model.
            text = localized.small_talk_reply(analysis["small_talk"], analysis["lang"],
                                              seed=len(str(question)))
            ms = (time.perf_counter() - start) * 1000.0
            return _result("small_talk", text, None, None, "", ms, analysis=analysis,
                           handled_by="language front-end (small talk, no model used)")
        model_text = analysis["canonical"] or str(question)
        ranking, accepted = self._rank(model_text)
        ctx_topic = (context or {}).get("topic")
        reply_topic = None
        if analysis["followup"] and ctx_topic and accepted in (None, "out_of_scope", "follow_up_simplify", "follow_up_next_steps"):
            reply_topic = ctx_topic if accepted in (None, "out_of_scope") else None
        text, override = chat_reply.compose(self.style, accepted, safe, analysis, ctx_topic,
                                            reply_topic=reply_topic)
        ms = (time.perf_counter() - start) * 1000.0
        top_k = [(i, round(float(c), 4)) for i, c in ranking[:3]]
        conf = ranking[0][1] if ranking else 0.0
        kw = dict(override=override, top_k=top_k, analysis=analysis, reply_topic=reply_topic)
        if accepted is None:
            return _result("no_match", text, None, conf, self.kind, ms, **kw)
        if accepted == "out_of_scope":      # recognised as "not a health question": unsupported, intent kept
            return _result("no_match", text, accepted, conf, self.kind, ms, **kw)
        return _result("ok", text, accepted, conf, self.kind, ms, **kw)


# --------------------------------------------------------------------- rule-based
class RuleBasedPipeline(_Base):
    key, name, style = "rule", "Rule-Based", "rule"
    kind = "rule match strength (not a probability)"
    error = None

    def info(self):
        return {"key": self.key, "name": self.name, "available": True,
                "architecture": "Emergency rules + spelling repair + keyword/phrase rules over the health topic list",
                "version": "rules-v2 (46-category)"}

    def _rank(self, text):
        from chatbot.health_qa.rule_engine import classify
        out = classify(text)
        self._clarify = out["clarify"]
        return out["ranking"], out["topic"]


# --------------------------------------------------------------------------- SVM
class SvmPipeline(_Base):
    key, name, style = "ml", "ML - TF-IDF + SVM", "ml"
    kind = "temperature-scaled softmax of SVM margins (fitted on validation split; rough, not a clinical probability)"

    def __init__(self, model_dir=SVM_DIR):
        self.model_dir, self.error, self.model, self.meta = model_dir, None, None, {}
        path = os.path.join(model_dir, "svm_pipeline.pkl")
        meta = os.path.join(model_dir, "svm_meta.json")
        if not os.path.isfile(path):
            self.error = "SVM model not trained yet. Run:  python -m chatbot.health_qa.train_svm"
            return
        try:
            with open(path, "rb") as f:
                self.model = pickle.load(f)
            with open(meta, encoding="utf-8") as f:
                self.meta = json.load(f)
        except Exception as exc:                     # corrupt file / sklearn version mismatch
            self.model, self.error = None, f"SVM model could not be loaded: {exc}. Retrain with train_svm."

    def available(self):
        return self.model is not None

    def info(self):
        return {"key": self.key, "name": self.name, "available": self.available(), "error": self.error,
                "architecture": "TF-IDF (word n-grams) + linear SVM",
                "trained_at": self.meta.get("trained_at"), "version": self.meta.get("run_id"),
                "classes": self.meta.get("classes"), "artifact": "models/svm/svm_pipeline.pkl"}

    def _rank(self, text):
        x = self.model.named_steps["tfidf"].transform([normalise(text)])
        if x.nnz == 0:                               # no known word at all
            return [], None
        svm = self.model.named_steps["svm"]
        scores = svm.decision_function(x)[0]
        probs = _softmax([float(v) * self.meta.get("temperature", 1.0) for v in scores])
        order = sorted(range(len(probs)), key=lambda i: -probs[i])
        ranking = [(str(svm.classes_[i]), probs[i]) for i in order[:5]]
        if float(scores[order[0]]) < self.meta.get("min_margin", 0.0):
            return ranking, None
        return ranking, ranking[0][0]


# -------------------------------------------------------------------- DistilBERT
class DistilBertPipeline(_Base):
    key, name, style = "dl", "DL - DistilBERT", "dl"
    kind = "softmax probability (not clinically calibrated)"

    def __init__(self, model_dir=DISTILBERT_DIR):
        self.model_dir, self.error = model_dir, None
        self.model = self.tokenizer = None
        self.labels, self.meta = [], {}
        needed = ("config.json", "label_map.json", "training_config.json")
        if not all(os.path.isfile(os.path.join(model_dir, n)) for n in needed):
            self.error = ("DistilBERT checkpoint not found in models/distilbert_medical/. "
                          "Install torch + transformers (pip install -r requirements.txt) and run:  "
                          "python -m chatbot.health_qa.train_distilbert  (needs internet once, to "
                          "download distilbert-base-uncased).")
            return
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self._torch = torch
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
            with open(os.path.join(model_dir, "label_map.json"), encoding="utf-8") as f:
                self.labels = json.load(f)["id2label_list"]
            with open(os.path.join(model_dir, "training_config.json"), encoding="utf-8") as f:
                self.meta = json.load(f)
        except Exception as exc:
            self.model, self.error = None, f"DistilBERT could not be loaded: {exc}"

    def available(self):
        return self.model is not None

    def info(self):
        return {"key": self.key, "name": self.name, "available": self.available(), "error": self.error,
                "architecture": "Fine-tuned distilbert-base-uncased classifier",
                "trained_at": self.meta.get("trained_at"), "version": self.meta.get("run_id"),
                "classes": len(self.labels) or None, "artifact": "models/distilbert_medical/"}

    def _rank(self, text):
        enc = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=self.meta.get("max_length", 128))
        with self._torch.no_grad():
            probs = self._torch.softmax(self.model(**enc).logits[0], dim=-1)
        conf, idx = self._torch.topk(probs, k=min(5, probs.shape[-1]))
        ranking = [(self.labels[int(i)], float(c)) for c, i in zip(conf, idx)]
        if ranking[0][1] < self.meta.get("min_confidence", 0.0):
            return ranking, None
        return ranking, ranking[0][0]
