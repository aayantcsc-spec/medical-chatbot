"""
bots.py
-------
Three different health chatbots that all use knowledge.py:

1. RuleBot - keyword rules, no training.
2. MLBot   - TF-IDF (words) + Logistic Regression, trained on the questions.
3. DLBot   - TF-IDF (character n-grams) + neural network (MLPClassifier),
             trained on the same questions.

(DistilBERT needs PyTorch which is not installed, so the DL bot uses a
feed-forward neural network from scikit-learn instead.)

Each bot returns a dict:
    {"topic": id or None, "category": str, "confidence": 0-1, "response": str}
"""

import os
import re
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline

from chatbot.health_qa.knowledge import TOPICS, TOPIC_BY_ID, DISCLAIMER
from chatbot.health_qa.evaluator import is_emergency, _words

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "models")
ML_FILE = os.path.join(MODEL_DIR, "health_ml.pkl")
DL_FILE = os.path.join(MODEL_DIR, "health_dl.pkl")

# below this confidence the ML / DL bots say "I am not sure"
ML_MIN_CONFIDENCE = 0.20
DL_MIN_CONFIDENCE = 0.40

SHORT_DISCLAIMER = "This is general information, not a diagnosis."

FALLBACK = ("I am not sure I understood that health question. I can help with topics like "
            "common symptoms, first aid, medicines safety, nutrition, exercise, sleep, "
            "mental health, child and older adult health. Please try asking in a different "
            "way, and see a doctor for advice about your own situation. " + SHORT_DISCLAIMER)


EMERGENCY_FALLBACK = ("This could be a medical emergency. Please call your local emergency number "
                      "(112 or 108 in India, 911 in the US) or go to the nearest hospital "
                      "immediately. Do not wait for an online answer. " + SHORT_DISCLAIMER)


def no_answer(question):
    """Reply used when a bot cannot match the question to any topic."""
    return EMERGENCY_FALLBACK if is_emergency(question) else FALLBACK


def shares_words(question, topic_id):
    """True if at least one important word of the question appears in the topic text.
    Stops the ML / DL models from confidently answering unrelated questions."""
    t = TOPIC_BY_ID[topic_id]
    topic_text = " ".join(t["questions"] + t["keywords"] + [t["short"], t["details"], t["advice"]]).lower()
    words = _words(question)
    return any(w[:5] in topic_text for w in words)


def clean(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9\s\-']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ----------------------------------------------------------------------
# training data
# ----------------------------------------------------------------------
def get_training_data():
    """Returns (texts, labels). Uses the questions plus a few keyword-based questions."""
    texts, labels = [], []
    for t in TOPICS:
        for q in t["questions"]:
            texts.append(clean(q))
            labels.append(t["id"])
        for kw in t["keywords"][:4]:
            texts.append(clean("tell me about " + kw))
            labels.append(t["id"])
            texts.append(clean("what is " + kw))
            labels.append(t["id"])
    return texts, labels


def build_ml_model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english"),
        LogisticRegression(C=20, max_iter=2000),
    )


def build_dl_model():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True),
        MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=400, random_state=1),
    )


def train_and_save(which="both"):
    """Train the ML and/or DL model on the knowledge base and save to models/."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    texts, labels = get_training_data()
    if which in ("ml", "both"):
        ml = build_ml_model().fit(texts, labels)
        with open(ML_FILE, "wb") as f:
            pickle.dump(ml, f)
    if which in ("dl", "both"):
        dl = build_dl_model().fit(texts, labels)
        with open(DL_FILE, "wb") as f:
            pickle.dump(dl, f)


def _load(path, which):
    """Load a saved model. If it is missing, or was saved with a different
    scikit-learn version and cannot be opened, train it again automatically."""
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as error:
            print("[HEALTH QA] could not load", os.path.basename(path), "-", error)
            print("[HEALTH QA] training it again on this computer...")
    train_and_save(which)
    with open(path, "rb") as f:
        return pickle.load(f)


# ----------------------------------------------------------------------
# response builders - each bot has its own style
# ----------------------------------------------------------------------
def _result(topic_id, confidence, text):
    if topic_id:
        category = TOPIC_BY_ID[topic_id]["category"]
    else:
        category = None
    return {"topic": topic_id, "category": category,
            "confidence": round(float(confidence), 3), "response": text}


def _join(*parts):
    return "\n\n".join(p for p in parts if p)


# extra rules: if the question has a word from BOTH sets, use this topic
CHILD_WORDS = {"child", "children", "kid", "kids", "baby", "babies", "toddler", "infant", "son", "daughter"}
COMBO_RULES = [
    (CHILD_WORDS, {"fever", "temperature", "hot"}, "child_fever"),
    (CHILD_WORDS, {"diarrhea", "diarrhoea", "vomiting", "dehydrated", "dehydration"}, "child_dehydration"),
]


class RuleBot:
    name = "Rule-Based"

    def answer(self, question):
        text = " " + clean(question) + " "
        words = set(text.split())
        for set_a, set_b, topic_id in COMBO_RULES:
            if words & set_a and words & set_b:
                t = TOPIC_BY_ID[topic_id]
                return _result(topic_id, 1.0, _join(t["short"], t["doctor"], SHORT_DISCLAIMER))
        best_id, best_score = None, 0
        for t in TOPICS:
            score = 0
            for kw in t["keywords"]:
                if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", text):
                    score += 2 if " " in kw else 1      # phrases count more
            if score > best_score:
                best_id, best_score = t["id"], score
        if not best_id:
            return _result(None, 0, no_answer(question))
        t = TOPIC_BY_ID[best_id]
        # rule bot gives a short answer: overview + when to see a doctor
        reply = _join(t["short"], t["doctor"], SHORT_DISCLAIMER)
        return _result(best_id, min(1.0, best_score / 3), reply)


class MLBot:
    name = "ML"

    def __init__(self):
        self.model = _load(ML_FILE, "ml")

    def answer(self, question):
        probs = self.model.predict_proba([clean(question)])[0]
        i = probs.argmax()
        topic_id, conf = str(self.model.classes_[i]), probs[i]
        if conf < ML_MIN_CONFIDENCE or not shares_words(question, topic_id):
            return _result(None, conf, no_answer(question))
        t = TOPIC_BY_ID[topic_id]
        # ML bot: overview + key facts (symptoms / causes) + doctor advice
        reply = _join(t["short"], "Key points: " + t["details"], t["doctor"], DISCLAIMER)
        return _result(topic_id, conf, reply)


class DLBot:
    name = "DL"

    def __init__(self):
        self.model = _load(DL_FILE, "dl")

    def answer(self, question):
        probs = self.model.predict_proba([clean(question)])[0]
        i = probs.argmax()
        topic_id, conf = str(self.model.classes_[i]), probs[i]
        if conf < DL_MIN_CONFIDENCE or not shares_words(question, topic_id):
            return _result(None, conf, no_answer(question))
        t = TOPIC_BY_ID[topic_id]
        # DL bot: overview + practical advice + doctor advice
        reply = _join(t["short"], "What you can do: " + t["advice"], t["doctor"], DISCLAIMER)
        return _result(topic_id, conf, reply)
