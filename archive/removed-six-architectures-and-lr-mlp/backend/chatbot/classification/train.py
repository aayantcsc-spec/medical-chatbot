"""
train.py - TF-IDF + Logistic Regression on Symptom2Disease.csv, with a held-out test split.

The original project trained on ALL 1,200 rows and then "evaluated" on rows it had seen, which
reads as ~100% accuracy. This trainer fixes that:

  * one reproducible stratified split (seed 42): 70% train / 15% validation / 15% test,
    written to datasets/symptom_splits/{train,val,test}.csv
  * TF-IDF + LogisticRegression are fitted on TRAIN only
  * C is chosen on VALIDATION; the abstain threshold is chosen on VALIDATION
  * TEST is never read here - evaluation/symptom_evaluator.py is its only user
  * in-sample (training) accuracy is recorded too, clearly labelled, so the historical
    "near 100%" figure can be reproduced and explained rather than hidden

Run:  python -m chatbot.classification.train
"""
import csv
import hashlib
import json
import os
import pickle
import random
import time
from datetime import datetime, timezone

from chatbot.symptom.knowledge import BASE_DIR, DATA_DIR, load_symptom2disease, display_name

SEED = 42
SPLIT_DIR = os.path.join(DATA_DIR, "symptom_splits")
MODEL_DIR = os.path.join(BASE_DIR, "models", "symptom")
MODEL_FILE = os.path.join(MODEL_DIR, "classifier.pkl")
META_FILE = os.path.join(MODEL_DIR, "classifier_meta.json")
C_GRID = [0.3, 1.0, 3.0, 10.0, 30.0]


def dedupe(rows):
    """Symptom2Disease.csv repeats some descriptions verbatim. Keep the first copy of each normalised text
    (so a test sentence can never also be a training sentence) and drop texts seen under two labels."""
    from chatbot.symptom.knowledge import norm
    labels_by_text, first = {}, {}
    for i, (text, label, raw) in enumerate(rows):
        n = norm(text)
        labels_by_text.setdefault(n, set()).add(label)
        first.setdefault(n, i)
    kept = [(i, r) for i, r in enumerate(rows) if first[norm(r[0])] == i and len(labels_by_text[norm(r[0])]) == 1]
    stats = {"rows_in_file": len(rows), "exact_duplicates_removed": len(rows) - len(first),
             "conflicting_label_texts_removed": sum(1 for v in labels_by_text.values() if len(v) > 1), "rows_used": len(kept)}
    return kept, stats


def make_splits(rows, seed=SEED, write=True):
    """Stratified 70/15/15 split by label over de-duplicated rows. Deterministic for a given seed and input."""
    rng = random.Random(seed)
    by_label = {}
    kept, stats = dedupe(rows)
    for i, (text, label, raw) in kept:
        by_label.setdefault(label, []).append({"row_id": i, "text": text, "label": label, "raw_label": raw})
    splits = {"train": [], "val": [], "test": []}
    for label in sorted(by_label):
        items = by_label[label]
        rng.shuffle(items)
        n = len(items)
        n_test, n_val = max(1, round(n * 0.15)), max(1, round(n * 0.15))
        splits["test"] += items[:n_test]
        splits["val"] += items[n_test:n_test + n_val]
        splits["train"] += items[n_test + n_val:]
    if write:
        os.makedirs(SPLIT_DIR, exist_ok=True)
        for name, items in splits.items():
            with open(os.path.join(SPLIT_DIR, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["row_id", "text", "label", "raw_label"])
                w.writeheader()
                w.writerows(sorted(items, key=lambda r: r["row_id"]))
    splits["_stats"] = stats
    return splits


def load_split(name):
    path = os.path.join(SPLIT_DIR, f"{name}.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Split not found: datasets/symptom_splits/{name}.csv - run python -m chatbot.classification.train")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_model(C):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)),
                     ("clf", LogisticRegression(C=C, max_iter=3000, random_state=SEED))])


def _acc(model, texts, labels):
    pred = model.predict(texts)
    return sum(1 for p, y in zip(pred, labels) if p == y) / len(labels) if labels else None


def train():
    import numpy as np
    import sklearn
    start = time.perf_counter()
    rows = load_symptom2disease()
    splits = make_splits(rows)
    xtr, ytr = [r["text"] for r in splits["train"]], [r["label"] for r in splits["train"]]
    xva, yva = [r["text"] for r in splits["val"]], [r["label"] for r in splits["val"]]

    trials = []
    for C in C_GRID:
        m = build_model(C).fit(xtr, ytr)
        trials.append({"C": C, "val_accuracy": round(_acc(m, xva, yva), 4)})
    best = max(trials, key=lambda t: (t["val_accuracy"], -t["C"]))
    model = build_model(best["C"]).fit(xtr, ytr)

    # abstain threshold on VALIDATION: lowest top-probability that keeps >= 90% selective accuracy
    proba = model.predict_proba(xva)
    top = proba.max(1)
    correct = model.classes_[proba.argmax(1)] == np.array(yva)
    min_prob = 0.0
    for thr in sorted(set(np.round(top, 3))):
        keep = top >= thr
        if keep.sum() >= 10 and correct[keep].mean() >= 0.90:
            min_prob = float(thr)
            break

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)
    sha = hashlib.sha256(open(os.path.join(DATA_DIR, "Symptom2Disease.csv"), "rb").read()).hexdigest()[:12]
    now = datetime.now(timezone.utc)
    meta = {"run_id": "clf-" + now.strftime("%Y%m%dT%H%M%SZ"), "trained_at": now.isoformat(timespec="seconds"),
            "architecture": "TfidfVectorizer (word 1-2 grams) + LogisticRegression", "seed": SEED,
            "sklearn_version": sklearn.__version__, "dataset": "datasets/Symptom2Disease.csv", "dataset_version": sha,
            "split": {"strategy": "stratified by label, 70/15/15, after removing duplicate texts", "train": len(xtr),
                      "val": len(xva), "test": len(splits["test"]), "deduplication": splits["_stats"],
                      "files": "datasets/symptom_splits/{train,val,test}.csv"},
            "classes": sorted(set(ytr)), "class_names": {c: display_name(c) for c in sorted(set(ytr))},
            "hyperparameters": {"C": best["C"]}, "tuning_trials_on_validation": trials,
            "min_probability": min_prob, "min_probability_note": "below this top-class probability the bot abstains (chosen on validation)",
            "in_sample_train_accuracy": round(_acc(model, xtr, ytr), 4),
            "in_sample_note": "Accuracy on the rows the model was trained on. NOT a generalisation estimate - do not compare with held-out results.",
            "validation_accuracy": round(_acc(model, xva, yva), 4),
            "training_seconds": round(time.perf_counter() - start, 3), "artifact": "models/symptom/classifier.pkl"}
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


if __name__ == "__main__":
    m = train()
    print(json.dumps({k: m[k] for k in ("run_id", "split", "hyperparameters", "min_probability",
                                        "in_sample_train_accuracy", "validation_accuracy", "training_seconds")}, indent=2))
