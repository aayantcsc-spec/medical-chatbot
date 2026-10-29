# -*- coding: utf-8 -*-
"""
evaluation_service.py - real, dataset-based evaluation of the three pipelines.

Every number is computed here from the pipelines' actual outputs on a dataset file. Nothing is
hardcoded or defaulted to a "success" value. A pipeline that is unavailable or raises an error
is recorded as such and excluded from classification metrics (counted in failure/availability).

Datasets (all in datasets/):
    question_bank   evaluation_questions.csv  300 author-written questions, 19 COARSE categories.
                    Models predict 91 fine-grained intents, so predictions are mapped to categories
                    with datasets/evaluation_label_map.json (an explicit author-made assumption).
                    Scored two ways: strict (intent's primary category) and lenient (any acceptable one).
    held_out_test   intent_splits/test.csv    held-out split of the 91-intent dataset (exact labels)
    multilingual    multilingual_eval.csv     Hinglish + Hindi questions with exact 91-intent labels;
                    never used for training
    safety          safety_oos_eval.csv + safety_multilingual_eval.csv
                    emergency detection (model-independent) and out-of-scope handling

A run is stored as models/evaluation/runs/<run_id>.json (atomic write), so a page refresh
retrieves the saved result instead of resetting. Only one run executes at a time; it runs in a
background thread so Chat requests are not blocked.
"""
import csv
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "datasets")
RUN_DIR = os.path.join(BASE_DIR, "models", "evaluation", "runs")
LABEL_MAP_FILE = os.path.join(DATA_DIR, "evaluation_label_map.json")
MODELS = ("rule", "ml", "dl")                       # the three MediChat architectures
NO_MATCH = "NO_MATCH"
QUICK_SIZE = 30
SEED = 42

DATASETS = {
    "question_bank": {"title": "Question bank (300 questions, 19 categories)", "files": ["evaluation_questions.csv"],
                      "kind": "mapped", "text": "question", "id": "question_id", "label": "expected_intent"},
    "held_out_test": {"title": "Held-out test split (91 intents)", "files": ["intent_splits/test.csv"],
                      "kind": "exact", "text": "text", "id": None, "label": "label"},
    "multilingual": {"title": "Hinglish + Hindi questions (91 intents)", "files": ["multilingual_eval.csv"],
                     "kind": "exact", "text": "question", "id": None, "label": "label"},
    "safety": {"title": "Safety + out-of-scope probes (English, Hinglish, Hindi)",
               "files": ["safety_oos_eval.csv", "safety_multilingual_eval.csv"], "kind": "safety",
               "text": "question", "id": None, "label": "expected_emergency"},
}

_lock = threading.Lock()
_active = {}            # run_id -> live state dict (only while this process is running it)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------------------ metrics (pure)
def classification_metrics(y_true, y_pred, labels=None):
    """Accuracy, per-class precision/recall/F1/support, macro + weighted averages, confusion matrix.
    Implemented directly (no sklearn) so it can be unit-tested against a hand-computed fixture."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    n = len(y_true)
    if n == 0:
        return {"n": 0, "accuracy": None, "per_class": {}, "macro": None, "weighted": None, "labels": [], "confusion_matrix": []}
    labels = list(labels) if labels is not None else sorted(set(y_true) | set(y_pred))
    idx = {l: i for i, l in enumerate(labels)}
    cm = [[0] * len(labels) for _ in labels]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            cm[idx[t]][idx[p]] += 1
    per, correct = {}, sum(1 for t, p in zip(y_true, y_pred) if t == p)
    for l in labels:
        i = idx[l]
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(len(labels))) - tp
        fn = sum(cm[i]) - tp
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[l] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "support": sum(cm[i])}
    present = [l for l in labels if per[l]["support"] > 0]
    total = sum(per[l]["support"] for l in present) or 1
    macro = {k: round(sum(per[l][k] for l in present) / len(present), 4) for k in ("precision", "recall", "f1")} if present else None
    weighted = {k: round(sum(per[l][k] * per[l]["support"] for l in present) / total, 4) for k in ("precision", "recall", "f1")} if present else None
    return {"n": n, "accuracy": round(correct / n, 4), "per_class": per, "macro": macro, "weighted": weighted,
            "labels": labels, "confusion_matrix": cm,
            "notes": "macro/weighted averages are over classes that occur in the true labels (support > 0)"}


def latency_stats(values):
    vals = sorted(float(v) for v in values if v is not None)
    if not vals:
        return {"n": 0, "mean_ms": None, "median_ms": None, "p90_ms": None, "p95_ms": None, "min_ms": None, "max_ms": None}

    def pct(p):
        k = (len(vals) - 1) * p / 100.0
        lo, hi = math.floor(k), math.ceil(k)
        return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 3)

    return {"n": len(vals), "mean_ms": round(statistics.fmean(vals), 3), "median_ms": round(statistics.median(vals), 3),
            "p90_ms": pct(90), "p95_ms": pct(95), "min_ms": round(vals[0], 3), "max_ms": round(vals[-1], 3)}


# --------------------------------------------------------------------------------- datasets
def _norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s\u0900-\u097F']", " ", str(text or "").lower())).strip()


def _read_csv(rel):
    path = os.path.join(DATA_DIR, rel)
    if not os.path.isfile(path):
        return None, f"file not found: datasets/{rel}"
    if os.path.getsize(path) == 0:
        return None, f"file is empty (0 bytes): datasets/{rel}"
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f)), None
    except Exception as exc:
        return None, f"could not read datasets/{rel}: {exc}"


def load_label_map():
    with open(LABEL_MAP_FILE, encoding="utf-8") as f:
        return json.load(f)["map"]


def _training_texts():
    """Normalised text of everything the models were trained or tuned on (train + val splits)."""
    texts = set()
    for part in ("train", "val"):
        rows, _ = _read_csv(f"intent_splits/{part}.csv")
        texts.update(_norm(r["text"]) for r in rows or [])
    return texts


def load_dataset(name, label_map=None):
    """Return {rows, validation}. Rows: dict(id, question, expected, expected_set, lang, extra, skip_reason)."""
    spec = DATASETS.get(name)
    if not spec:
        raise ValueError(f"Unknown dataset '{name}'. Choose one of: {', '.join(DATASETS)}")
    issues, raw = [], []
    for rel in spec["files"]:
        rows, err = _read_csv(rel)
        if err:
            issues.append(err)
        else:
            raw.extend(dict(r, _file=rel) for r in rows)
    val = {"dataset": name, "files": spec["files"], "rows_in_file": len(raw), "issues": issues, "excluded": [], "warnings": []}
    if not raw:
        val.update(valid=False, rows_usable=0)
        if not issues:
            issues.append("dataset is empty")
        return {"rows": [], "validation": val, "spec": spec, "version": None}

    need = {spec["text"], spec["label"]}
    cols = set(raw[0].keys())
    if need - cols:
        issues.append(f"missing required column(s): {sorted(need - cols)}; found {sorted(c for c in cols if not c.startswith('_'))}")
        val.update(valid=False, rows_usable=0)
        return {"rows": [], "validation": val, "spec": spec, "version": None}

    from chatbot.health_qa.knowledge import TOPIC_BY_ID
    label_map = label_map or (load_label_map() if spec["kind"] == "mapped" else {})
    trained = _training_texts() if name != "safety" else set()
    seen, by_text_labels = {}, {}
    for r in raw:
        by_text_labels.setdefault(_norm(r[spec["text"]]), set()).add(str(r[spec["label"]]).strip())

    rows = []
    for i, r in enumerate(raw):
        q = str(r.get(spec["text"], "")).strip()
        lab = str(r.get(spec["label"], "")).strip()
        rid = (r.get(spec["id"]) if spec["id"] else None) or f"{name[:3].upper()}{i + 1:04d}"
        item = {"id": rid, "question": q, "expected": lab, "expected_set": [], "lang": r.get("lang") or None,
                "extra": {k: v for k, v in r.items() if k not in (spec["text"], spec["label"], "_file")}, "skip_reason": None}
        n = _norm(q)
        if not q:
            item["skip_reason"] = "empty question"
        elif not lab:
            item["skip_reason"] = "missing expected label"
        elif spec["kind"] == "exact" and lab not in TOPIC_BY_ID:
            item["skip_reason"] = f"label '{lab}' is not a model intent (dataset/model label mismatch)"
        elif spec["kind"] == "mapped" and not any(lab in v for v in label_map.values()):
            item["skip_reason"] = f"label '{lab}' is not covered by evaluation_label_map.json (label mismatch)"
        elif len(by_text_labels.get(n, ())) > 1:
            item["skip_reason"] = "same question appears with conflicting expected labels (ambiguous ground truth)"
        elif n in seen:
            item["skip_reason"] = f"duplicate of {seen[n]}"
        elif n in trained:
            item["skip_reason"] = "overlaps a training/validation question (possible data leakage)"
        else:
            seen[n] = rid
        if spec["kind"] == "safety" and lab not in ("0", "1"):
            item["skip_reason"] = item["skip_reason"] or "expected_emergency must be 0 or 1"
        if spec["kind"] == "mapped" and not item["skip_reason"]:
            item["expected_set"] = [lab]
        if not item["lang"]:
            from chatbot.health_qa import language
            item["lang"] = language.detect_language(q)["lang"] if q else None
        rows.append(item)

    usable = [r for r in rows if not r["skip_reason"]]
    for r in rows:
        if r["skip_reason"]:
            val["excluded"].append({"id": r["id"], "question": r["question"][:90], "reason": r["skip_reason"]})
    counts = {}
    for r in usable:
        counts[r["expected"]] = counts.get(r["expected"], 0) + 1
    small = sorted(k for k, v in counts.items() if v < 5)
    if small and spec["kind"] != "safety":
        val["warnings"].append(f"{len(small)} class(es) have fewer than 5 questions; their per-class metrics are unstable: {small[:8]}")
    if spec["kind"] == "mapped":
        val["warnings"].append("Question-bank labels are 19 coarse categories; scores depend on datasets/evaluation_label_map.json, an author-made mapping.")
    if name == "safety":
        val["warnings"].append("safety_multilingual_eval.csv was used while the Hindi/Hinglish lexicon was being developed (missed items were fixed "
                               "afterwards), so it is a regression set, not unseen data. The English probes in safety_oos_eval.csv were not used for tuning.")
    if name == "multilingual":
        val["warnings"].append("multilingual_eval.csv was written by the same team that wrote the Hindi/Hinglish lexicon (not by independent annotators) and "
                               "is small; treat the scores as indicative only.")
    if name != "safety":
        val["warnings"].append("Models were trained on author-written questions about the same topics; scores measure generalisation to new "
                               "wording, not performance on real patient language.")
    sha = hashlib.sha256()
    for rel in spec["files"]:
        p = os.path.join(DATA_DIR, rel)
        if os.path.isfile(p):
            sha.update(open(p, "rb").read())
    val.update(valid=bool(usable) and not [i for i in issues if "missing required" in i], rows_usable=len(usable),
               rows_excluded=len(val["excluded"]), class_counts=counts, languages=_count(r["lang"] for r in usable))
    return {"rows": rows, "validation": val, "spec": spec, "version": sha.hexdigest()[:12]}


def _count(it):
    out = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return out


def list_datasets():
    out = []
    for name, spec in DATASETS.items():
        try:
            d = load_dataset(name)
            v = d["validation"]
            out.append({"name": name, "title": spec["title"], "kind": spec["kind"], "files": spec["files"],
                        "rows_in_file": v["rows_in_file"], "rows_usable": v.get("rows_usable", 0), "valid": v["valid"],
                        "issues": v["issues"], "warnings": v["warnings"], "version": d["version"],
                        "rows_excluded": v.get("rows_excluded", 0), "languages": v.get("languages", {}),
                        "categories": [{"value": c, "count": n} for c, n in sorted(category_counts(d["rows"], spec["kind"]).items())],
                        "category_label": "Probe type" if spec["kind"] == "safety" else "Category"})
        except Exception as exc:
            out.append({"name": name, "title": spec["title"], "valid": False, "issues": [str(exc)], "rows_usable": 0})
    return out


# ------------------------------------------------------------------------------- sampling
MODES = ("quick", "full", "custom")


def category_of(item, kind):
    """The 'category' a row belongs to for filtering: the expected label (question-bank category / intent id),
    or the probe kind (emergency / non_emergency / out_of_scope) for the safety dataset."""
    if kind == "safety":
        return str((item.get("extra") or {}).get("kind") or "").strip() or "unspecified"
    return item["expected"]


def category_counts(rows, kind):
    """{category: eligible row count} over rows that passed validation."""
    out = {}
    for r in rows:
        if not r["skip_reason"]:
            c = category_of(r, kind)
            out[c] = out.get(c, 0) + 1
    return out


def select_rows(rows, mode="quick", limit=None, seed=SEED, category=None, kind=None):
    """Choose the questions that will be sent to ALL models. Only eligible rows (no skip_reason) are considered.
    category: restrict to one category first (see category_of). mode: quick = QUICK_SIZE, full = all, custom = limit.
    Backward compatible: limit still overrides quick/full when given."""
    usable = [r for r in rows if not r["skip_reason"]]
    if category:
        usable = [r for r in usable if category_of(r, kind) == category]
    n = len(usable) if mode == "full" else min(QUICK_SIZE, len(usable))
    if limit:
        n = min(int(limit), len(usable))
    if n >= len(usable):
        return usable
    rng = random.Random(seed)
    buckets = {}
    for r in usable:                                            # stratified round-robin over expected labels
        buckets.setdefault(r["expected"], []).append(r)
    for b in buckets.values():
        rng.shuffle(b)
    order = sorted(buckets)
    rng.shuffle(order)
    picked, i = [], 0
    while len(picked) < n:
        progressed = False
        for lab in order:
            if buckets[lab] and len(picked) < n:
                picked.append(buckets[lab].pop())
                progressed = True
        if not progressed:
            break
    return picked


# --------------------------------------------------------------------------------- scoring
def _predicted_categories(intent, label_map):
    return list(label_map.get(intent, [])) if intent else []


def _score_classification(item, rec, spec, label_map):
    """Add predicted/correct fields to one model record for label-based datasets."""
    intent = rec.get("intent")
    if rec["status"] in ("unavailable", "error"):
        rec.update(predicted=None, correct_strict=None, correct_lenient=None)
        return
    if spec["kind"] == "exact":
        pred = intent or NO_MATCH
        ok = pred == item["expected"]
        rec.update(predicted=pred, predicted_lenient=pred, correct_strict=ok, correct_lenient=ok)
    else:
        cats = _predicted_categories(intent, label_map)
        primary = cats[0] if cats else NO_MATCH
        strict = primary == item["expected"]
        lenient = item["expected"] in cats
        rec.update(predicted=primary, predicted_lenient=item["expected"] if lenient else primary,
                   predicted_categories=cats, correct_strict=strict, correct_lenient=lenient)


def _keyword_coverage(response, keywords):
    kws = [k.strip().lower() for k in str(keywords or "").split(",") if k.strip()]
    if not kws:
        return None
    text = (response or "").lower()
    return round(sum(1 for k in kws if k in text) / len(kws), 3)


def _summarise_model(key, records, spec, info, label_names):
    total = len(records)
    failed = [r for r in records if r["status"] in ("unavailable", "error")]
    valid = [r for r in records if r["status"] not in ("unavailable", "error")]
    out = {"key": key, "version": info.get("version"), "architecture": info.get("architecture"),
           "available": info.get("available", True), "error": info.get("error"),
           "questions": total, "valid_predictions": len(valid), "failed": len(failed),
           "availability_rate": round(len(valid) / total, 4) if total else None,
           "failure_rate": round(len(failed) / total, 4) if total else None,
           "latency": latency_stats([r["inference_ms"] for r in valid])}
    if spec["kind"] in ("exact", "mapped") and valid:
        for tag, field, pfield in (("strict", "correct_strict", "predicted"), ("lenient", "correct_lenient", "predicted_lenient")):
            y_true = [r["expected"] for r in valid]
            y_pred = [r[pfield] for r in valid]
            labels = sorted(set(y_true) | set(y_pred) - {NO_MATCH})
            if NO_MATCH in y_pred:
                labels.append(NO_MATCH)
            m = classification_metrics(y_true, y_pred, labels)
            m["correct"] = sum(1 for r in valid if r[field])
            out["classification_" + tag] = m
        out["no_confident_match"] = sum(1 for r in valid if r["predicted"] == NO_MATCH)
        out["classification"] = out["classification_lenient"] if spec["kind"] == "mapped" else out["classification_strict"]
        out["classification_note"] = ("Lenient: a prediction counts as correct if the expected category is any acceptable category of the predicted intent. "
                                      "Strict: only the intent's primary category counts." if spec["kind"] == "mapped"
                                      else "Exact match of the predicted intent id with the expected intent id.")
    elif spec["kind"] in ("exact", "mapped"):
        out["classification"] = None
    covs = [r["keyword_coverage"] for r in valid if r.get("keyword_coverage") is not None]
    if covs:
        out["response_estimates"] = {
            "label": "AUTOMATED ESTIMATE - not human-assessed, not a measure of medical correctness",
            "keyword_coverage_mean": round(statistics.fmean(covs), 4), "n": len(covs),
            "rubric": "share of the question's expected_keywords that appear in the reply text (substring match)"}
    return out


def _safety_summary(rows_done, model_records):
    """Emergency detection (model-independent) + per-model surfacing + out-of-scope handling."""
    emerg = [r for r in rows_done if r["extra"].get("kind") in ("emergency", "non_emergency", "out_of_scope")]
    y_true = [int(r["expected"]) for r in emerg]
    y_pred = [int(r["safety_detected"]) for r in emerg]
    m = classification_metrics(y_true, y_pred, [0, 1])
    pos = m["per_class"].get(1, {"precision": 0, "recall": 0, "f1": 0, "support": 0})
    by_lang = {}
    for r in emerg:
        if r["expected"] == "1":
            d = by_lang.setdefault(r["lang"] or "unknown", {"emergencies": 0, "detected": 0})
            d["emergencies"] += 1
            d["detected"] += int(r["safety_detected"])
    for d in by_lang.values():
        d["recall"] = round(d["detected"] / d["emergencies"], 4) if d["emergencies"] else None
    per_model = {}
    for key, recs in model_records.items():
        pm = {"emergency_surfaced": 0, "emergency_total": 0, "false_alarms": 0, "non_emergency_total": 0,
              "oos_total": 0, "oos_declined": 0, "failed": 0}
        for r, rec in zip(emerg, recs):
            if rec["status"] in ("unavailable", "error"):
                pm["failed"] += 1
            elif r["expected"] == "1":
                pm["emergency_total"] += 1
                pm["emergency_surfaced"] += int(bool(rec.get("safety_override")))
            else:
                pm["non_emergency_total"] += 1
                pm["false_alarms"] += int(bool(rec.get("safety_override")))
                if r["extra"].get("kind") == "out_of_scope":
                    pm["oos_total"] += 1
                    pm["oos_declined"] += int(rec["status"] == "no_match")
        pm["emergency_recall"] = round(pm["emergency_surfaced"] / pm["emergency_total"], 4) if pm["emergency_total"] else None
        pm["oos_decline_rate"] = round(pm["oos_declined"] / pm["oos_total"], 4) if pm["oos_total"] else None
        per_model[key] = pm
    missed = [r["question"] for r in emerg if r["expected"] == "1" and not r["safety_detected"]]
    false_alarms = [r["question"] for r in emerg if r["expected"] == "0" and r["safety_detected"]]
    return {"emergency_detection": {"accuracy": m["accuracy"], "precision": pos["precision"], "recall": pos["recall"], "f1": pos["f1"],
                                    "confusion_matrix": m["confusion_matrix"], "labels": ["not emergency", "emergency"], "n": m["n"]},
            "by_language_recall": by_lang, "per_model": per_model, "missed_emergencies": missed, "false_alarms": false_alarms,
            "note": "Safety is assessed separately from answer relevance. Detection is model-independent (safety.assess on the question)."}


# -------------------------------------------------------------------------------- the run
def _default_runner(key, question):
    import comparison_service as cs
    return cs.run_one(key, question)


def _model_infos(models):
    import comparison_service as cs
    infos = {}
    for k in models:
        try:
            infos[k] = dict(cs.get_pipeline(k).info())
        except Exception as exc:
            infos[k] = {"available": False, "error": f"{type(exc).__name__}: {exc}", "version": None}
    return infos


def _new_state(run_id, dataset, mode, models, user_id, loaded, selected, category=None, requested_limit=None):
    v = loaded["validation"]
    return {"run_id": run_id, "status": "pending", "created_at": _now(), "started_at": None, "finished_at": None, "user_id": user_id,
            "dataset": {"name": dataset, "title": loaded["spec"]["title"], "kind": loaded["spec"]["kind"], "version": loaded["version"],
                        "files": loaded["spec"]["files"], "rows_in_file": v["rows_in_file"], "rows_usable": v.get("rows_usable", 0),
                        "rows_excluded": v.get("rows_excluded", 0), "validation": v},
            "mode": mode, "models_requested": list(models), "sampled": len(selected) < v.get("rows_usable", 0),
            "selection": {"mode": mode, "category": category, "requested_limit": requested_limit,
                          "dataset_rows": v["rows_in_file"], "dataset_eligible": v.get("rows_usable", 0),
                          "dataset_excluded": v.get("rows_excluded", 0),
                          "category_eligible": sum(1 for r in loaded["rows"] if not r["skip_reason"] and (not category or category_of(r, loaded["spec"]["kind"]) == category)),
                          "selected": len(selected), "seed": SEED, "question_ids": [r["id"] for r in selected]},
            "progress": {"completed": 0, "total": len(selected), "errors": 0, "skipped": v.get("rows_excluded", 0), "current": None},
            "error": None, "models": {}, "per_question": [], "metrics": {}, "limitations": [], "label_map_version": None}


def _persist(state):
    os.makedirs(RUN_DIR, exist_ok=True)
    path = os.path.join(RUN_DIR, state["run_id"] + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, path)


def _execute(state, selected, runner, models, loaded, on_finish=None):
    spec, run_id = loaded["spec"], state["run_id"]
    label_map = load_label_map() if spec["kind"] == "mapped" else {}
    try:
        state["status"], state["started_at"] = "running", _now()
        _persist(state)
        infos = _model_infos(models)
        state["models"] = {k: {kk: infos[k].get(kk) for kk in ("version", "architecture", "available", "error", "trained_at", "artifact")} for k in models}
        per_model = {k: [] for k in models}
        records = []
        for i, item in enumerate(selected):
            state["progress"]["current"] = item["id"]
            row = {"id": item["id"], "question": item["question"], "expected": item["expected"], "lang": item["lang"], "extra": item["extra"], "models": {}}
            if spec["kind"] == "safety":
                from chatbot.health_qa import safety
                row["safety_detected"] = bool(safety.assess(item["question"])["emergency"])
            for key in models:
                t0 = time.perf_counter()
                try:
                    res = runner(key, item["question"])
                except Exception as exc:                   # a crashing model must not stop the run
                    res = {"status": "error", "error": f"{type(exc).__name__}: {exc}", "response": "", "intent": None,
                           "confidence": None, "inference_ms": None}
                rec = {"status": res.get("status"), "intent": res.get("intent"), "confidence": res.get("confidence"),
                       "inference_ms": res.get("inference_ms"), "error": res.get("error"), "response": res.get("response", ""),
                       "expected": item["expected"], "safety_override": bool(res.get("safety_override")), "wall_ms": round((time.perf_counter() - t0) * 1000, 3)}
                if rec["status"] in ("unavailable", "error"):
                    state["progress"]["errors"] += 1
                if spec["kind"] in ("exact", "mapped"):
                    _score_classification(item, rec, spec, label_map)
                    rec["keyword_coverage"] = _keyword_coverage(rec["response"], item["extra"].get("expected_keywords"))
                row["models"][key] = rec
                per_model[key].append(rec)
            records.append(row)
            state["per_question"] = records
            state["progress"]["completed"] = i + 1
            if (i + 1) % 10 == 0:
                _persist(state)
            time.sleep(0)                                  # yield so Chat requests are served
        metrics = {k: _summarise_model(k, per_model[k], spec, infos[k], None) for k in models}
        state["metrics"] = metrics
        if spec["kind"] == "safety":
            state["safety"] = _safety_summary(records, per_model)
        state["limitations"] = list(state["dataset"]["validation"]["warnings"])
        sel = state.get("selection") or {}
        if sel.get("category"):
            state["limitations"].append(f"Category filter: only questions in '{sel['category']}' were evaluated ({len(selected)} of "
                                        f"{sel.get('category_eligible')} eligible in that category). Scores describe that category only.")
        if len(selected) < sel.get("category_eligible", state["dataset"]["rows_usable"]):
            state["limitations"].append(f"{'Quick test' if state['mode'] == 'quick' else state['mode'].capitalize() + ' selection'}: only {len(selected)} of {sel.get('category_eligible', state['dataset']['rows_usable'])} eligible questions were evaluated "
                                        f"(stratified sample, seed {SEED}). Run all eligible questions for reportable numbers.")
        state["label_map_version"] = "1" if spec["kind"] == "mapped" else None
        state["status"] = "completed"
    except Exception as exc:                               # never report success for a crashed run
        state["status"], state["error"] = "failed", f"{type(exc).__name__}: {exc}"
    finally:
        state["finished_at"] = _now()
        state["progress"]["current"] = None
        try:
            _persist(state)
            if on_finish and state["status"] == "completed":
                try:
                    on_finish(state)
                except Exception as exc:          # a storage hook must never fail a finished run
                    print("[EVALUATION] on_finish hook failed:", exc)
        finally:
            with _lock:
                _active.pop(run_id, None)


def start_run(dataset="question_bank", mode="quick", limit=None, models=None, user_id=None, runner=None, wait=False, category=None,
              on_finish=None):
    """Validate, then start a run. Returns the initial status dict. Raises ValueError / RuntimeError."""
    if mode not in MODES:
        raise ValueError("mode must be 'quick', 'full' or 'custom'")
    models = tuple(models or MODELS)
    bad = [m for m in models if m not in MODELS]
    if bad:
        raise ValueError(f"Unknown model(s): {bad}")
    loaded = load_dataset(dataset)
    if not loaded["validation"]["valid"] or not loaded["rows"]:
        raise ValueError("Dataset cannot be evaluated: " + "; ".join(loaded["validation"]["issues"] or ["no usable rows"]))
    kind = loaded["spec"]["kind"]
    category = (str(category).strip() if category not in (None, "") else None)
    eligible = category_counts(loaded["rows"], kind)
    if category and category not in eligible:
        raise ValueError(f"Category '{category}' has no eligible questions in this dataset.")
    available = eligible[category] if category else sum(eligible.values())
    if mode == "custom":
        if not limit:
            raise ValueError("Custom mode needs a question count.")
        if int(limit) > available:
            raise ValueError(f"Only {available} eligible question{'s' if available != 1 else ''} available for this selection; "
                             f"{int(limit)} requested.")
    selected = select_rows(loaded["rows"], mode, limit, category=category, kind=kind)
    if not selected:
        raise ValueError("Dataset has no usable questions after validation.")
    with _lock:
        if _active:
            raise RuntimeError("An evaluation is already running (" + next(iter(_active)) + "). Wait for it to finish.")
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        state = _new_state(run_id, dataset, mode, models, user_id, loaded, selected, category, int(limit) if limit else None)
        _active[run_id] = state
    _persist(state)
    th = threading.Thread(target=_execute, args=(state, selected, runner or _default_runner, models, loaded, on_finish),
                          daemon=True, name="eval-" + run_id)
    th.start()
    if wait:
        th.join()
    return status_of(state)


# ---------------------------------------------------------------------------------- queries
def status_of(state):
    p = state["progress"]
    return {"run_id": state["run_id"], "status": state["status"], "dataset": state["dataset"]["name"], "mode": state["mode"],
            "created_at": state["created_at"], "started_at": state["started_at"], "finished_at": state["finished_at"],
            "progress": dict(p), "percent": round(100.0 * p["completed"] / p["total"], 1) if p["total"] else 0.0,
            "error": state["error"], "sampled": state["sampled"]}


def _load_file(run_id):
    if not re.fullmatch(r"[0-9A-Za-z\-]+", str(run_id or "")):
        return None
    path = os.path.join(RUN_DIR, run_id + ".json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_state(run_id):
    with _lock:
        live = _active.get(run_id)
    if live is not None:
        return live
    st = _load_file(run_id)
    if st and st["status"] in ("pending", "running"):       # file says running but no thread owns it
        st["status"], st["error"] = "failed", "Run was interrupted (the server restarted before it finished)."
    return st


def get_status(run_id):
    st = get_state(run_id)
    return status_of(st) if st else None


def get_run(run_id):
    return get_state(run_id)


def list_runs(limit=50):
    out = []
    if os.path.isdir(RUN_DIR):
        for fn in sorted(os.listdir(RUN_DIR), reverse=True):
            if fn.endswith(".json"):
                st = get_state(fn[:-5])
                if st:
                    s = status_of(st)
                    s["models"] = {k: (st["metrics"].get(k, {}).get("classification") or {}).get("accuracy") for k in st.get("metrics", {})}
                    s["dataset_title"] = st["dataset"]["title"]
                    s["dataset_kind"] = st["dataset"].get("kind")
                    s["models_included"] = list(st.get("models_requested") or [])
                    s["category"] = (st.get("selection") or {}).get("category")
                    out.append(s)
    out.sort(key=lambda s: s["created_at"], reverse=True)
    return out[:limit]


def latest_run():
    runs = list_runs(1)
    return get_run(runs[0]["run_id"]) if runs else None


def export_csv(run_id):
    st = get_state(run_id)
    if not st:
        return None
    buf = io.StringIO()
    cols = ["run_id", "dataset", "dataset_version", "question_id", "language", "question", "expected", "model", "model_version", "status",
            "predicted_intent", "predicted_label", "correct_strict", "correct_lenient", "confidence", "inference_ms", "keyword_coverage_estimate", "error"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for row in st.get("per_question", []):
        for key, rec in row["models"].items():
            w.writerow({"run_id": st["run_id"], "dataset": st["dataset"]["name"], "dataset_version": st["dataset"]["version"],
                        "question_id": row["id"], "language": row["lang"], "question": row["question"], "expected": row["expected"],
                        "model": key, "model_version": (st.get("models", {}).get(key) or {}).get("version"), "status": rec["status"],
                        "predicted_intent": rec.get("intent"), "predicted_label": rec.get("predicted"),
                        "correct_strict": rec.get("correct_strict"), "correct_lenient": rec.get("correct_lenient"),
                        "confidence": rec.get("confidence"), "inference_ms": rec.get("inference_ms"),
                        "keyword_coverage_estimate": rec.get("keyword_coverage"), "error": rec.get("error")})
    return buf.getvalue()
