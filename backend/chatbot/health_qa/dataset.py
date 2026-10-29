"""
dataset.py - builds the labelled intent dataset and the 70/15/15 split.

SOURCE: chatbot/health_qa/knowledge.py (the project's own hand-written health
topics; every question is labelled with the topic id it belongs to).

Why this source and not Symptom2Disease.csv / the augmented disease file?
  * Those files map symptom descriptions -> disease names. They are not
    health *questions*, and turning disease names into chatbot answers would
    create answers that nobody has medically validated.
  * medical_qa.csv is generated from knowledge.py (make_qa_csv.py), so using
    it would only duplicate the same rows.
Excluded on purpose: the templated "tell me about <keyword>" rows that
bots.get_training_data() adds (synthetic, not real wording).

Leakage control:
  1. exact duplicates (after normalisation) are removed;
  2. a normalised text that appears under two different labels is dropped
     (conflicting label);
  3. near-duplicates (same label, Jaccard >= 0.6 on content words) are put in
     one GROUP and a group is never split across train / val / test;
  4. every class keeps at least one group in train.

Run:  python -m chatbot.health_qa.dataset
"""
import csv
import json
import os
import random
import re
from collections import defaultdict

from chatbot.health_qa.knowledge import TOPICS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT_DIR = os.path.join(BASE_DIR, "datasets", "intent_splits")
SEED = 42
SPLIT = (0.70, 0.15, 0.15)
NEAR_DUP_JACCARD = 0.6

_STOP = set("a an the is are was were be do does did i my me you your it its of to in on for and or "
            "what how why when which who can could should would may might about".split())


def normalise(text):
    text = re.sub(r"[^a-z0-9\s'-]", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _content_words(text):
    return frozenset(w for w in normalise(text).split() if w not in _STOP)


def load_raw():
    rows = []
    for t in TOPICS:
        for q in t["questions"]:
            rows.append({"text": q, "label": t["id"], "category": t["category"], "category46": t["categories"][0]})
    return rows


def clean_rows(rows):
    """Remove exact duplicates and conflicting labels. Returns (rows, excluded)."""
    by_norm = defaultdict(set)
    for r in rows:
        by_norm[normalise(r["text"])].add(r["label"])
    kept, excluded, seen = [], [], set()
    for r in rows:
        n = normalise(r["text"])
        if not n:
            excluded.append({**r, "reason": "empty after normalisation"})
        elif len(by_norm[n]) > 1:
            excluded.append({**r, "reason": "same text under conflicting labels"})
        elif n in seen:
            excluded.append({**r, "reason": "exact duplicate"})
        else:
            seen.add(n)
            kept.append(r)
    return kept, excluded


def _groups(rows):
    """Union-find over same-label rows whose content words overlap strongly."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    words = [_content_words(r["text"]) for r in rows]
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i]["label"] != rows[j]["label"]:
                continue
            a, b = words[i], words[j]
            if a and b and len(a & b) / len(a | b) >= NEAR_DUP_JACCARD:
                parent[find(i)] = find(j)
    return [find(i) for i in range(len(rows))]


def split_rows(rows, seed=SEED):
    """Group-aware, per-class split into train / val / test."""
    gid = _groups(rows)
    per_label = defaultdict(lambda: defaultdict(list))
    for r, g in zip(rows, gid):
        per_label[r["label"]][g].append(r)
    rng = random.Random(seed)
    out = {"train": [], "val": [], "test": []}
    for label in sorted(per_label):
        groups = list(per_label[label].values())
        rng.shuffle(groups)
        n = len(groups)
        n_test = round(SPLIT[2] * n) if n >= 4 else (1 if n == 3 else 0)
        n_val = round(SPLIT[1] * n) if n >= 4 else (1 if n == 3 else 0)
        n_test, n_val = max(n_test, 1 if n >= 3 else 0), max(n_val, 1 if n >= 3 else 0)
        for k, grp in enumerate(groups):
            part = "test" if k < n_test else ("val" if k < n_test + n_val else "train")
            out[part].extend(grp)
    return out


def build(write=True):
    raw = load_raw()
    rows, excluded = clean_rows(raw)
    parts = split_rows(rows)
    report = {
        "source": "chatbot/health_qa/knowledge.py + knowledge_extra.py (author-written topics; 46-category taxonomy in taxonomy.py)",
        "seed": SEED, "target_split": SPLIT, "near_duplicate_jaccard": NEAR_DUP_JACCARD,
        "raw_examples": len(raw), "usable_examples": len(rows), "excluded": len(excluded),
        "excluded_detail": excluded,
        "classes": len({r["label"] for r in rows}),
        "split_sizes": {k: len(v) for k, v in parts.items()},
        "classes_in_split": {k: len({r["label"] for r in v}) for k, v in parts.items()},
        "limitations": [
            "Examples are hand-written by the project team, so the held-out test set measures "
            "generalisation to new wording of the SAME topics, not to real patient language.",
            "With ~10 questions per topic the validation and test sets contain only 1-2 "
            "groups per class; metrics have wide uncertainty.",
            "Labels are topic ids, not clinically validated diagnoses.",
        ],
    }
    if write:
        os.makedirs(SPLIT_DIR, exist_ok=True)
        for name, items in parts.items():
            with open(os.path.join(SPLIT_DIR, name + ".csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["text", "label", "category", "category46"])
                w.writeheader()
                w.writerows(items)
        with open(os.path.join(SPLIT_DIR, "split_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return parts, report


def load_split(name):
    path = os.path.join(SPLIT_DIR, name + ".csv")
    if not os.path.isfile(path):
        build(write=True)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    _, rep = build()
    print({k: v for k, v in rep.items() if k not in ("excluded_detail", "limitations")})
