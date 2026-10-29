"""
train_lr_mlp.py - the specification's Health Q&A ML and DL bots, retrained on the CURRENT data.

    ML  = TF-IDF (word n-grams) + LogisticRegression      -> models/health_lr/
    DL  = TF-IDF (character n-grams) + MLPClassifier       -> models/health_mlp/
          (a conventional scikit-learn feed-forward network - NOT a transformer)

Same protocol as train_svm.py so all five Health Q&A models are comparable:
  * fitted on datasets/intent_splits/train.csv (+ the topics' keyword phrases, train only)
  * hyperparameters and the abstain threshold chosen on val.csv
  * test.csv is never read here (evaluation_service.py is its only user)
The existing splits are reused as-is (dataset.build() is NOT re-run), so the held-out test set is
identical to the one the SVM and DistilBERT were evaluated on.

Run:  python -m chatbot.health_qa.train_lr_mlp
"""
import json
import os
import pickle
import time
from datetime import datetime, timezone

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from chatbot.health_qa.knowledge import TOPICS
from chatbot.health_qa.dataset import load_split, normalise, SEED

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LR_DIR = os.path.join(BASE_DIR, "models", "health_lr")
MLP_DIR = os.path.join(BASE_DIR, "models", "health_mlp")

SPECS = {
    "lr": {"dir": LR_DIR, "grid": [{"C": c} for c in (1.0, 3.0, 10.0, 30.0)],
           "architecture": "TfidfVectorizer (word 1-2 grams) + LogisticRegression"},
    "mlp": {"dir": MLP_DIR, "grid": [{"hidden": h, "alpha": a} for h in ((128,), (256,), (128, 64)) for a in (1e-4, 1e-3)],
            "architecture": "TfidfVectorizer (char_wb 2-4 grams) + MLPClassifier (scikit-learn feed-forward network)"},
}


def _make(kind, hp):
    if kind == "lr":
        return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")),
                         ("clf", LogisticRegression(C=hp["C"], max_iter=4000, random_state=SEED))])
    return Pipeline([("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
                     ("clf", MLPClassifier(hidden_layer_sizes=hp["hidden"], alpha=hp["alpha"], max_iter=500,
                                           early_stopping=False, random_state=SEED))])


def _data():
    tr, va = load_split("train"), load_split("val")
    xtr, ytr = [normalise(r["text"]) for r in tr], [r["label"] for r in tr]
    kw = [(normalise(k), t["id"]) for t in TOPICS for k in t["keywords"]]
    xtr += [k for k, _ in kw]
    ytr += [l for _, l in kw]
    return xtr, ytr, [normalise(r["text"]) for r in va], [r["label"] for r in va], len(tr), len(kw)


def train(kind):
    spec = SPECS[kind]
    xtr, ytr, xva, yva, n_q, n_kw = _data()
    start = time.perf_counter()
    trials = []
    for hp in spec["grid"]:
        m = _make(kind, hp).fit(xtr, ytr)
        acc = float(np.mean(m.predict(xva) == np.array(yva)))
        trials.append({**{k: list(v) if isinstance(v, tuple) else v for k, v in hp.items()}, "val_accuracy": round(acc, 4)})
    best_i = max(range(len(trials)), key=lambda i: trials[i]["val_accuracy"])
    model = _make(kind, spec["grid"][best_i]).fit(xtr, ytr)

    proba = model.predict_proba(xva)
    top = proba.max(1)
    correct = model.classes_[proba.argmax(1)] == np.array(yva)
    min_conf = 0.0
    for thr in sorted(set(np.round(top, 3))):
        keep = top >= thr
        if keep.sum() >= 10 and correct[keep].mean() >= 0.90:
            min_conf = float(thr)
            break
    os.makedirs(spec["dir"], exist_ok=True)
    with open(os.path.join(spec["dir"], "pipeline.pkl"), "wb") as f:
        pickle.dump(model, f)
    now = datetime.now(timezone.utc)
    meta = {"run_id": f"{kind}-" + now.strftime("%Y%m%dT%H%M%SZ"), "trained_at": now.isoformat(timespec="seconds"),
            "architecture": spec["architecture"], "seed": SEED, "sklearn_version": sklearn.__version__,
            "dataset": "datasets/intent_splits/{train,val}.csv", "train_examples": len(xtr), "train_question_rows": n_q,
            "train_keyword_rows": n_kw, "val_examples": len(xva), "classes": len(set(ytr)),
            "hyperparameters": trials[best_i], "tuning_trials_on_validation": trials, "min_confidence": min_conf,
            "min_confidence_note": "chosen on validation split only; below it the bot declines to answer",
            "training_seconds": round(time.perf_counter() - start, 3),
            "artifact": f"models/{os.path.basename(spec['dir'])}/pipeline.pkl"}
    with open(os.path.join(spec["dir"], "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


if __name__ == "__main__":
    for k in ("lr", "mlp"):
        m = train(k)
        print(k, json.dumps({x: m[x] for x in ("run_id", "hyperparameters", "min_confidence", "training_seconds")}))
