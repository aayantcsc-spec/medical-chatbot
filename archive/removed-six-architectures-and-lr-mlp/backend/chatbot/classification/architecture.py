"""
Architecture 3 - Classification-Based.

TF-IDF + Logistic Regression trained on the TRAIN split of Symptom2Disease.csv (see train.py).
It predicts which of the 24 dataset labels the description is most similar to. The reply says so
plainly: the label is "the closest match in the training data", not a diagnosis, and the
probability is the model's score, not a calibrated medical likelihood.
"""
import json
import os
import pickle
import threading

from chatbot.symptom.base import Architecture, DISCLAIMER, join, bullet
from chatbot.symptom.knowledge import diseases, display_name
from chatbot.classification.train import MODEL_FILE, META_FILE

SCORE_KIND = "logistic-regression class probability (not clinically calibrated; not a likelihood of having the condition)"


class ClassificationArchitecture(Architecture):
    key = "classification"
    name = "Classification-Based"
    method = "TF-IDF + Logistic Regression trained on a held-out split of Symptom2Disease.csv"
    predicts_label = True

    def __init__(self):
        self._model, self._meta, self._error = None, {}, None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is not None or self._error:
                return
            if not os.path.isfile(MODEL_FILE):
                self._error = "Classifier not trained yet. Run:  python -m chatbot.classification.train"
                return
            try:
                with open(MODEL_FILE, "rb") as f:
                    self._model = pickle.load(f)
                with open(META_FILE, encoding="utf-8") as f:
                    self._meta = json.load(f)
            except Exception as exc:
                self._error = f"Classifier could not be loaded ({exc}). Retrain: python -m chatbot.classification.train"

    def available(self):
        self._load()
        return (self._model is not None), self._error

    def version(self):
        self._load()
        return self._meta.get("run_id", "untrained")

    def meta(self):
        self._load()
        return dict(self._meta)

    def predict_proba(self, text):
        probs = self._model.predict_proba([text])[0]
        order = probs.argsort()[::-1]
        return [(str(self._model.classes_[i]), float(probs[i])) for i in order[:3]]

    def _answer(self, text, context):
        top = self.predict_proba(text)
        label, p = top[0]
        evidence = [{"type": "model_score", "label": l, "label_name": display_name(l), "score": round(s, 4)} for l, s in top]
        threshold = self._meta.get("min_probability", 0.0)
        if p < threshold:
            return {"status": "no_match", "evidence": evidence,
                    "prediction": {"label": None, "label_name": None, "score": round(p, 4), "score_kind": SCORE_KIND,
                                   "abstained": True, "threshold": threshold},
                    "response": join("The classifier was not confident enough to match your description to any condition in its "
                                     f"training data (top score {p:.2f}, below the {threshold:.2f} threshold set on validation data).",
                                     "Please describe your symptoms in more detail, or speak to a doctor.", DISCLAIMER)}
        info = diseases().get(label, {})
        name = display_name(label)
        parts = [f"Your description is most similar to examples of **{name}** in the training data "
                 f"(model score {p:.2f}). This is a pattern match, not a diagnosis - many conditions share symptoms."]
        if info.get("description"):
            parts.append(f"About {name}: {info['description']}")
        if info.get("precautions"):
            parts.append("General precautions listed in the dataset:\n" + bullet(p.capitalize() for p in info["precautions"]))
        others = [display_name(l) for l, s in top[1:] if s >= 0.1]
        if others:
            parts.append("Other similar patterns: " + ", ".join(others) + ".")
        parts.append("Please see a doctor to find out what is actually causing your symptoms.")
        parts.append(DISCLAIMER)
        return {"status": "ok", "response": join(*parts), "evidence": evidence,
                "prediction": {"label": label, "label_name": name, "score": round(p, 4), "score_kind": SCORE_KIND,
                               "abstained": False, "threshold": threshold}}
