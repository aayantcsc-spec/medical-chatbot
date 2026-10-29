"""
train_svm.py - trains the TF-IDF + linear-SVM pipeline.

  * TF-IDF and SVM are fitted on the TRAIN split only.
  * C and the n-gram range are chosen on the VALIDATION split.
  * The TEST split is not touched here (evaluate.py is the only user).
  * min_margin (reject threshold) is chosen on validation data.

Run:  python -m chatbot.health_qa.train_svm
"""
import itertools
import json
import os
import pickle
import time
from datetime import datetime, timezone

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.svm import LinearSVC

from chatbot.health_qa.knowledge import TOPICS
from chatbot.health_qa.dataset import load_split, normalise, SEED, build
from chatbot.health_qa.pipelines import SVM_DIR

GRID = {"C": [0.1, 0.3, 1.0, 3.0, 10.0], "ngram_range": [(1, 1), (1, 2)], "char": [False, True]}


def _make(C, ngram, char=False):
    word = TfidfVectorizer(ngram_range=ngram, sublinear_tf=True, stop_words="english")
    # optional character n-grams make the model more tolerant of spelling mistakes (TF-IDF still fitted on train only)
    vec = FeatureUnion([("w", word), ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))]) if char else word
    return Pipeline([
        ("tfidf", vec),
        ("svm", LinearSVC(C=C, random_state=SEED, max_iter=10000)),
    ])


def train():
    build(write=True)
    tr, va = load_split("train"), load_split("val")
    xtr, ytr = [normalise(r["text"]) for r in tr], [r["label"] for r in tr]
    # extra TRAIN-ONLY rows: the project's labelled keyword phrases (never added to val/test)
    kw_rows = [(normalise(k), t["id"]) for t in TOPICS for k in t["keywords"]]
    xtr += [k for k, _ in kw_rows]
    ytr += [l for _, l in kw_rows]
    xva, yva = [normalise(r["text"]) for r in va], [r["label"] for r in va]

    start = time.perf_counter()
    trials = []
    for C, ngram, char in itertools.product(GRID["C"], GRID["ngram_range"], GRID["char"]):
        m = _make(C, ngram, char).fit(xtr, ytr)
        acc = float(np.mean(np.array(m.predict(xva)) == np.array(yva)))
        trials.append({"C": C, "ngram_range": list(ngram), "char_ngrams": char, "val_accuracy": round(acc, 4)})
    best = max(trials, key=lambda t: (t["val_accuracy"], -t["C"]))
    model = _make(best["C"], tuple(best["ngram_range"]), best["char_ngrams"]).fit(xtr, ytr)    # train split only

    # reject threshold from VALIDATION margins: smallest margin that gives >=90% selective accuracy
    scores = model.decision_function(xva)
    pred = model.named_steps["svm"].classes_[scores.argmax(1)]
    top = scores.max(1)
    correct = pred == np.array(yva)
    min_margin = 0.0
    for thr in sorted(set(np.round(top, 4))):
        keep = top >= thr
        if keep.sum() >= 10 and correct[keep].mean() >= 0.90:
            min_margin = float(thr)
            break
    # temperature scaling fitted on VALIDATION data (minimise log-loss)
    idx = {c: i for i, c in enumerate(model.named_steps["svm"].classes_)}
    yi = np.array([idx[y] for y in yva])
    best_t, best_nll = 1.0, float("inf")
    for T in [1, 2, 3, 5, 8, 12, 20, 30, 50]:
        z = scores * T
        z = z - z.max(1, keepdims=True)
        logp = z - np.log(np.exp(z).sum(1, keepdims=True))
        nll = -logp[np.arange(len(yi)), yi].mean()
        if nll < best_nll:
            best_t, best_nll = T, float(nll)
    seconds = time.perf_counter() - start

    os.makedirs(SVM_DIR, exist_ok=True)
    with open(os.path.join(SVM_DIR, "svm_pipeline.pkl"), "wb") as f:
        pickle.dump(model, f)
    run_id = "svm-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {"run_id": run_id, "trained_at": datetime.now(timezone.utc).isoformat(),
            "architecture": "TfidfVectorizer (word" + (" + char" if best["char_ngrams"] else "") + ") + LinearSVC", "seed": SEED,
            "sklearn_version": sklearn.__version__, "dataset": "datasets/intent_splits/{train,val}.csv",
            "train_examples": len(xtr), "train_question_rows": len(tr), "train_keyword_rows": len(kw_rows), "val_examples": len(va), "classes": len(set(ytr)),
            "hyperparameters": {"C": best["C"], "ngram_range": best["ngram_range"],
                                "char_ngrams": best["char_ngrams"], "stop_words": "english", "sublinear_tf": True},
            "tuning_trials_on_validation": trials, "min_margin": min_margin, "temperature": best_t, "val_log_loss": round(best_nll, 4),
            "min_margin_note": "chosen on validation split only; 0.0 means no rejection threshold met",
            "training_seconds": round(seconds, 3), "artifact": "models/svm/svm_pipeline.pkl",
            "known_limitations": ["Small author-written dataset (~7 train questions per class, plus keyword phrases).",
                                  "Temperature fitted on only ~150 validation examples; treat the score as a rough indicator."]}
    with open(os.path.join(SVM_DIR, "svm_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


if __name__ == "__main__":
    m = train()
    print(json.dumps({k: m[k] for k in ("run_id", "train_examples", "val_examples", "classes",
                                        "hyperparameters", "min_margin", "training_seconds")}, indent=2))
