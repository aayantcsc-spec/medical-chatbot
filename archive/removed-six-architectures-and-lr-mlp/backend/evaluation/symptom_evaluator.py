"""
symptom_evaluator.py - reproducible evaluation of the six symptom architectures.

Dataset: datasets/symptom_splits/test.csv - the HELD-OUT 15% of Symptom2Disease.csv that the
classifier never saw (made by chatbot/classification/train.py). Using the full file would leak the
classifier's training rows into its score; that is refused unless `legacy_full_dataset=True`, in
which case every result is labelled "in-sample (methodologically limited)".

Every selected architecture receives the SAME sampled inputs (stratified by label, fixed seed) and
runs through the same safety layer (chatbot.symptom.registry.run). Measured per architecture:

  task metrics (separate, never blended)
    label_metrics       accuracy + macro precision/recall/F1 of the predicted label. Only for
                        architectures that predict a label (Classification, Retrieval). An abstention
                        counts as the prediction NO_MATCH (wrong). Averaging: macro over true classes.
    legacy_mention      the ORIGINAL project metric: is the true disease named anywhere in the reply?
                        Kept for reproducibility. Rule/NLP/Generation are designed NOT to name diseases,
                        so a low value for them reflects design, not a defect.
  coverage              share of inputs answered (status ok) vs no_match vs failed
  safety                share of replies that passed the response gate; rejected count
  response time         per-request wall time in ms: mean, median, p90, p95 (time.perf_counter around
                        registry.run, single process, sequential requests, warm caches after 1 warm-up call)
  cpu / memory          process CPU time used during that architecture's requests divided by wall time
                        (percent of ONE core), and resident-memory change across its requests (psutil).
                        These depend on hardware, OS and other load; compare only within one run.

Results are saved three ways: models/evaluation/symptom_runs/<run_id>.json (full detail),
results/comparison_results.csv (append-only history, one row per architecture per run) and the
experiments / performance_results tables in SQLite (for dashboards).

CLI (spec-compatible):  python -m evaluation.evaluator --sample-size 30 --seed 42
"""
import csv
import hashlib
import json
import os
import random
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.join(BASE_DIR, "models", "evaluation", "symptom_runs")
RESULTS_CSV = os.path.join(BASE_DIR, "results", "comparison_results.csv")
SPLIT_FILE = os.path.join(BASE_DIR, "datasets", "symptom_splits", "test.csv")
FULL_FILE = os.path.join(BASE_DIR, "datasets", "Symptom2Disease.csv")
NO_MATCH = "NO_MATCH"
DEFAULT_SEED = 42
SMALL_SAMPLE = 50

CSV_COLUMNS = ["run_id", "timestamp", "suite", "dataset", "dataset_version", "split", "sample_size", "seed", "architecture",
               "accuracy", "precision_macro", "recall_macro", "f1_macro", "legacy_mention_accuracy", "coverage",
               "safety_pass_rate", "mean_response_time_ms", "median_response_time_ms", "cpu_percent_one_core",
               "memory_delta_mb", "successful_requests", "failed_requests", "evaluation_method"]

_lock = threading.Lock()
_active = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12] if os.path.isfile(path) else None


def load_rows(legacy_full_dataset=False):
    """[(row_id, text, canonical_label)] + metadata. Validates columns and labels."""
    from chatbot.symptom.knowledge import load_symptom2disease
    if legacy_full_dataset:
        rows = [(str(i), t, l) for i, (t, l, _) in enumerate(load_symptom2disease())]
        return rows, {"file": "datasets/Symptom2Disease.csv", "split": "full dataset (IN-SAMPLE for the classifier)",
                      "version": _sha(FULL_FILE), "in_sample": True}
    if not os.path.isfile(SPLIT_FILE):
        raise FileNotFoundError("Held-out split missing: run  python -m chatbot.classification.train")
    with open(SPLIT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = {"row_id", "text", "label"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"datasets/symptom_splits/test.csv is missing columns: {sorted(missing)}")
        rows = [(r["row_id"], r["text"].strip(), r["label"].strip()) for r in reader if r["text"].strip() and r["label"].strip()]
    return rows, {"file": "datasets/symptom_splits/test.csv", "split": "held-out test (15%, stratified, seed 42)",
                  "version": _sha(SPLIT_FILE), "in_sample": False}


def sample(rows, size, seed):
    """Stratified round-robin over labels; deterministic for (rows, size, seed)."""
    if not size or size >= len(rows):
        return list(rows)
    rng = random.Random(seed)
    buckets = {}
    for r in rows:
        buckets.setdefault(r[2], []).append(r)
    for b in buckets.values():
        rng.shuffle(b)
    order = sorted(buckets)
    rng.shuffle(order)
    out = []
    while len(out) < size:
        for lab in order:
            if buckets[lab] and len(out) < size:
                out.append(buckets[lab].pop())
        if not any(buckets.values()):
            break
    return out


def _latency(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {"n": 0, "mean_ms": None, "median_ms": None, "p90_ms": None, "p95_ms": None}

    def pct(p):
        k = (len(vals) - 1) * p / 100
        lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
        return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 3)
    return {"n": len(vals), "mean_ms": round(statistics.fmean(vals), 3), "median_ms": round(statistics.median(vals), 3),
            "p90_ms": pct(90), "p95_ms": pct(95)}


def _evaluate_architecture(key, items, rows_meta):
    import psutil
    from chatbot.symptom import registry
    from chatbot.symptom.knowledge import mentioned_diseases
    from evaluation_service import classification_metrics

    arch = registry.get(key)
    info = arch.info()
    proc = psutil.Process()
    if info["available"]:
        registry.run(key, "warm up headache")                 # load models/indexes outside the timed window
    mem0, cpu0, wall0 = proc.memory_info().rss, proc.cpu_times(), time.perf_counter()
    records = []
    for row_id, text, label in items:
        t0 = time.perf_counter()
        try:
            r = registry.run(key, text)
        except Exception as exc:
            r = {"status": "error", "error": f"{type(exc).__name__}: {exc}", "response": "", "prediction": None, "safety": {}}
        wall = round((time.perf_counter() - t0) * 1000, 3)
        p = r.get("prediction") or {}
        # an answer naming a disease outside the 41 canonical ones is a WRONG label, not an abstention
        pred = (p.get("label") or ("other:" + str(p.get("label_name") or "unknown").lower())) if r.get("status") == "ok" and p else None
        mentioned = mentioned_diseases(r.get("withheld_response") or r.get("response") or "")
        top3 = [e.get("record_id") or e.get("label") for e in (r.get("evidence") or [])[:3]]
        records.append({"row_id": row_id, "input": text, "expected": label, "status": r.get("status"),
                        "predicted": pred or NO_MATCH, "mentions_expected": label in mentioned, "top3_hit": label in top3,
                        "safety_status": (r.get("safety") or {}).get("status"), "response_time_ms": wall,
                        "error": r.get("error"), "response": (r.get("response") or "")[:600]})
    wall_s = time.perf_counter() - wall0
    cpu1, mem1 = proc.cpu_times(), proc.memory_info().rss
    cpu_s = (cpu1.user - cpu0.user) + (cpu1.system - cpu0.system)

    n = len(records)
    failed = [r for r in records if r["status"] in ("error", "unavailable")]
    valid = [r for r in records if r not in failed]
    out = {"architecture": key, "name": info["name"], "method": info["method"], "version": info["version"],
           "available": info["available"], "unavailable_reason": info["unavailable_reason"],
           "predicts_label": info["predicts_label"], "requests": n, "successful_requests": len(valid),
           "failed_requests": len(failed),
           "coverage": {"answered": sum(r["status"] == "ok" for r in records), "no_match": sum(r["status"] == "no_match" for r in records),
                        "failed": len(failed), "answered_rate": round(sum(r["status"] == "ok" for r in records) / n, 4) if n else None},
           "safety": {"passed": sum(r["safety_status"] == "passed" for r in valid),
                      "rejected": sum(r["safety_status"] == "rejected" for r in valid),
                      "emergency_override": sum(r["safety_status"] == "emergency_override" for r in valid),
                      "pass_rate": round(sum(r["safety_status"] in ("passed", "emergency_override") for r in valid) / len(valid), 4) if valid else None},
           "latency": _latency([r["response_time_ms"] for r in valid]),
           "resources": {"cpu_percent_one_core": round(100 * cpu_s / wall_s, 1) if wall_s > 0 else None,
                         "memory_rss_mb_after": round(mem1 / 2 ** 20, 1), "memory_delta_mb": round((mem1 - mem0) / 2 ** 20, 2),
                         "method": "psutil process CPU time / wall time over this architecture's requests; RSS before vs after"},
           "legacy_mention": {"accuracy": round(sum(r["mentions_expected"] for r in valid) / len(valid), 4) if valid else None,
                              "label": "LEGACY METRIC - correct if the reply names the true disease anywhere",
                              "applicable": info["predicts_label"] or key == "rag_based",
                              "note": None if info["predicts_label"] else
                              "This architecture is designed not to name diseases; a low score reflects that design choice."},
           "label_metrics": None, "records": records}
    if info["predicts_label"] and valid:
        y_true = [r["expected"] for r in valid]
        y_pred = [r["predicted"] for r in valid]
        labels = sorted(set(y_true)) + ([NO_MATCH] if NO_MATCH in y_pred else []) + sorted(set(y_pred) - set(y_true) - {NO_MATCH})
        m = classification_metrics(y_true, y_pred, labels)
        out["label_metrics"] = {"accuracy": m["accuracy"], "precision_macro": m["macro"]["precision"],
                                "recall_macro": m["macro"]["recall"], "f1_macro": m["macro"]["f1"],
                                "averaging": "macro over classes present in the true labels; abstentions count as wrong",
                                "per_class": m["per_class"], "labels": m["labels"], "confusion_matrix": m["confusion_matrix"],
                                "no_match": sum(1 for p in y_pred if p == NO_MATCH),
                                "top3_hit_rate": round(sum(r["top3_hit"] for r in valid) / len(valid), 4),
                                "top3_note": "share of inputs whose true label is among the 3 highest-ranked classes/records"}
    if key == "classification":
        meta = arch.meta() if hasattr(arch, "meta") else {}
        out["classifier_reference"] = {"in_sample_train_accuracy": meta.get("in_sample_train_accuracy"),
                                       "validation_accuracy": meta.get("validation_accuracy"),
                                       "note": meta.get("in_sample_note"), "split": meta.get("split")}
        if rows_meta["in_sample"]:
            out["warning"] = "IN-SAMPLE: this dataset includes the classifier's training rows; its score is not a generalisation estimate."
    return out


def _warnings(rows_meta, n, keys, available=None):
    w = []
    if rows_meta["in_sample"]:
        w.append("Legacy full-dataset mode: the Classification-Based model was trained on most of these rows, so its "
                 "scores are in-sample and NOT comparable with the other architectures or with held-out results.")
    if n < SMALL_SAMPLE:
        w.append(f"Small sample ({n} inputs): differences of a few percentage points are within noise. "
                 f"Use a larger sample (the dataset has {available} usable rows) before drawing conclusions.")
    w.append("Symptom2Disease.csv contains author-style descriptions, not real patient conversations; scores do not "
             "describe real-world clinical performance.")
    if any(k in keys for k in ("rule_based", "nlp_based", "generation_based")):
        w.append("Rule-, NLP- and Generation-Based give general guidance by design and are not scored on disease labels; "
                 "compare them on coverage, safety and response time instead.")
    w.append("Retrieval-Based searches profiles of 677 diseases from a different dataset; 4 of the 24 test labels "
             "(Typhoid, Dengue, Peptic ulcer, Diabetes) exist there only as descriptions, which limits its label accuracy.")
    return w


def _append_csv(state):
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    new = not os.path.isfile(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if new:
            w.writeheader()
        for a in state["architectures"].values():
            lm = a.get("label_metrics") or {}
            w.writerow({"run_id": state["run_id"], "timestamp": state["finished_at"], "suite": "symptom",
                        "dataset": state["dataset"]["file"], "dataset_version": state["dataset"]["version"],
                        "split": state["dataset"]["split"], "sample_size": state["config"]["sample_size_used"],
                        "seed": state["config"]["seed"], "architecture": a["architecture"], "accuracy": lm.get("accuracy"),
                        "precision_macro": lm.get("precision_macro"), "recall_macro": lm.get("recall_macro"),
                        "f1_macro": lm.get("f1_macro"), "legacy_mention_accuracy": a["legacy_mention"]["accuracy"],
                        "coverage": a["coverage"]["answered_rate"], "safety_pass_rate": a["safety"]["pass_rate"],
                        "mean_response_time_ms": a["latency"]["mean_ms"], "median_response_time_ms": a["latency"]["median_ms"],
                        "cpu_percent_one_core": a["resources"]["cpu_percent_one_core"],
                        "memory_delta_mb": a["resources"]["memory_delta_mb"], "successful_requests": a["successful_requests"],
                        "failed_requests": a["failed_requests"], "evaluation_method": state["method"]})


def _persist(state):
    os.makedirs(RUN_DIR, exist_ok=True)
    path = os.path.join(RUN_DIR, state["run_id"] + ".json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def _execute(state, items, rows_meta, keys, on_finish):
    try:
        state["status"], state["started_at"] = "running", _now()
        _persist(state)
        for key in keys:
            state["progress"]["current"] = key
            state["architectures"][key] = _evaluate_architecture(key, items, rows_meta)
            state["progress"]["completed"] += 1
            _persist(state)
        state["status"] = "completed"
    except Exception as exc:
        state["status"], state["error"] = "failed", f"{type(exc).__name__}: {exc}"
    finally:
        state["finished_at"] = _now()
        state["progress"]["current"] = None
        _persist(state)
        if state["status"] == "completed":
            _append_csv(state)
        if on_finish:
            try:
                on_finish(state)
            except Exception as exc:                  # storage hooks must never turn a run into a failure
                state.setdefault("storage_warnings", []).append(f"{type(exc).__name__}: {exc}")
                _persist(state)
        with _lock:
            _active.pop(state["run_id"], None)


def start(sample_size=30, seed=DEFAULT_SEED, architectures=None, legacy_full_dataset=False, user_id=None,
          name=None, wait=False, on_finish=None):
    from chatbot.symptom.registry import ORDER
    keys = [k for k in (architectures or ORDER)]
    bad = [k for k in keys if k not in ORDER]
    if bad:
        raise ValueError(f"Unknown architecture(s): {bad}")
    if not keys:
        raise ValueError("Select at least one architecture.")
    seed = int(seed if seed is not None else DEFAULT_SEED)
    rows, rows_meta = load_rows(legacy_full_dataset)
    if not rows:
        raise ValueError("The evaluation dataset has no usable rows.")
    size = int(sample_size) if sample_size else None
    if size is not None and size < 1:
        raise ValueError("Sample size must be at least 1.")
    items = sample(rows, size, seed)
    with _lock:
        if _active:
            raise RuntimeError("A symptom evaluation is already running. Wait for it to finish.")
        run_id = "sym-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        state = {"run_id": run_id, "suite": "symptom", "name": name or f"Six-architecture evaluation ({len(items)} inputs)",
                 "status": "pending", "created_at": _now(), "started_at": None, "finished_at": None, "user_id": user_id,
                 "error": None, "dataset": {**rows_meta, "rows_available": len(rows), "labels": len({r[2] for r in rows})},
                 "config": {"sample_size_requested": size, "sample_size_used": len(items), "seed": seed,
                            "architectures": keys, "legacy_full_dataset": bool(legacy_full_dataset),
                            "input_ids": [r[0] for r in items]},
                 "method": ("held-out" if not rows_meta["in_sample"] else "legacy in-sample") +
                           " | same inputs for every architecture | stratified sample | sequential, single process",
                 "progress": {"completed": 0, "total": len(keys), "current": None, "unit": "architectures"},
                 "architectures": {}, "warnings": _warnings(rows_meta, len(items), keys, len(rows))}
        _active[run_id] = state
    _persist(state)
    th = threading.Thread(target=_execute, args=(state, items, rows_meta, keys, on_finish), daemon=True, name=run_id)
    th.start()
    if wait:
        th.join()
    return state


def get(run_id):
    with _lock:
        if run_id in _active:
            return _active[run_id]
    if not run_id or not all(c.isalnum() or c == "-" for c in run_id):
        return None
    path = os.path.join(RUN_DIR, run_id + ".json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        st = json.load(f)
    if st["status"] in ("pending", "running"):
        st["status"], st["error"] = "failed", "Run was interrupted (server restarted before it finished)."
    return st


def list_runs(limit=100):
    out = []
    if os.path.isdir(RUN_DIR):
        for fn in sorted(os.listdir(RUN_DIR), reverse=True)[:limit]:
            if fn.endswith(".json"):
                st = get(fn[:-5])
                if st:
                    out.append(summary(st))
    return out


def summary(st):
    """Compact per-run view (no per-record detail) for lists and charts."""
    archs = {}
    for k, a in (st.get("architectures") or {}).items():
        lm = a.get("label_metrics") or {}
        archs[k] = {"name": a["name"], "accuracy": lm.get("accuracy"), "f1_macro": lm.get("f1_macro"),
                    "top3_hit_rate": lm.get("top3_hit_rate"),
                    "precision_macro": lm.get("precision_macro"), "recall_macro": lm.get("recall_macro"),
                    "legacy_mention_accuracy": a["legacy_mention"]["accuracy"], "coverage": a["coverage"]["answered_rate"],
                    "safety_pass_rate": a["safety"]["pass_rate"], "mean_ms": a["latency"]["mean_ms"],
                    "median_ms": a["latency"]["median_ms"], "cpu_percent": a["resources"]["cpu_percent_one_core"],
                    "memory_delta_mb": a["resources"]["memory_delta_mb"], "failed": a["failed_requests"],
                    "successful": a["successful_requests"], "predicts_label": a["predicts_label"]}
    return {"run_id": st["run_id"], "suite": "symptom", "name": st["name"], "status": st["status"], "created_at": st["created_at"],
            "finished_at": st["finished_at"], "dataset": st["dataset"]["file"], "split": st["dataset"]["split"],
            "dataset_version": st["dataset"]["version"], "in_sample": st["dataset"]["in_sample"],
            "sample_size": st["config"]["sample_size_used"], "seed": st["config"]["seed"],
            "progress": st["progress"], "error": st["error"], "architectures": archs, "warnings": st.get("warnings", [])}


def export_csv(run_id):
    st = get(run_id)
    if not st:
        return None
    import io
    buf = io.StringIO()
    cols = ["run_id", "architecture", "row_id", "input", "expected", "status", "predicted", "mentions_expected",
            "safety_status", "response_time_ms", "error"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for k, a in st["architectures"].items():
        for r in a["records"]:
            w.writerow({"run_id": st["run_id"], "architecture": k, **r})
    return buf.getvalue()
