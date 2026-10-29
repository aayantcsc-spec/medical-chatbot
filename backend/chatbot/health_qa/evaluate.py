"""
evaluate.py - held-out comparative evaluation of the three pipelines.

Every number written to models/evaluation/comparison_eval.json is computed here from real
predictions; nothing is hardcoded. All three pipelines see the SAME questions:
    * datasets/intent_splits/test.csv     (labelled held-out intent questions)
    * datasets/safety_oos_eval.csv        (author-written out-of-scope + emergency probes)
A pipeline that is unavailable (e.g. DistilBERT with no checkpoint) is recorded as
"unavailable" with its reason - no metrics are invented for it.

Run:  python -m chatbot.health_qa.evaluate
"""
import csv
import json
import os
import statistics
import time
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix,
                             precision_recall_fscore_support)

from chatbot.health_qa import safety
from chatbot.health_qa.dataset import load_split, BASE_DIR
from chatbot.health_qa.evaluator import check_safety
from chatbot.health_qa.knowledge import TOPIC_BY_ID
from chatbot.health_qa.taxonomy import CATEGORIES_46, primary_category
from chatbot.health_qa.pipelines import RuleBasedPipeline, SvmPipeline, DistilBertPipeline

OUT_DIR = os.path.join(BASE_DIR, "models", "evaluation")
OUT_FILE = os.path.join(OUT_DIR, "comparison_eval.json")
PROBES = os.path.join(BASE_DIR, "datasets", "safety_oos_eval.csv")
REJECT = "REJECTED"


def _percentile(values, p):
    return round(float(np.percentile(values, p)), 3) if values else None


def _ece(conf, correct, bins=5):
    conf, correct = np.array(conf), np.array(correct, dtype=float)
    if len(conf) == 0:
        return None
    edges, ece = np.linspace(0, 1, bins + 1), 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return round(float(ece), 4)


def evaluate_pipeline(p, test, probes):
    t_load = time.perf_counter()
    info = p.info()
    entry = {"key": p.key, "name": p.name, "info": info}
    if not info["available"]:
        entry.update(status="unavailable", reason=info.get("error"))
        return entry

    for q in [r["text"] for r in test[:3]]:         # warm-up, not measured
        p.predict(q)

    y_true, y_pred, conf, lat = [], [], [], []
    for r in test:
        out = p.predict(r["text"])
        y_true.append(r["label"])
        y_pred.append(out["intent"] if out["intent"] else REJECT)
        conf.append(out["confidence"] or 0.0)
        lat.append(out["inference_ms"])
    labels = sorted(set(y_true))
    cm_labels = labels + [REJECT]
    prec, rec, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    macro = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
    answered = [i for i, v in enumerate(y_pred) if v != REJECT]
    sel_acc = (float(np.mean([y_true[i] == y_pred[i] for i in answered])) if answered else None)
    correct = [t == pr for t, pr in zip(y_true, y_pred)]

    # 46-category view: each intent is mapped to its primary category
    def _cat(x):
        return primary_category(x) if x != REJECT else REJECT
    c_true, c_pred = [_cat(v) for v in y_true], [_cat(v) for v in y_pred]
    c_labels = sorted(set(c_true))
    cmacro = precision_recall_fscore_support(c_true, c_pred, labels=c_labels, average="macro", zero_division=0)
    cweighted = precision_recall_fscore_support(c_true, c_pred, labels=c_labels, average="weighted", zero_division=0)
    cprec, crec, cf1, csup = precision_recall_fscore_support(c_true, c_pred, labels=c_labels, zero_division=0)
    category_metrics = {
        "n_categories_in_test": len(c_labels), "n_categories_total": len(CATEGORIES_46),
        "accuracy": round(accuracy_score(c_true, c_pred), 4),
        "macro_f1": round(cmacro[2], 4), "weighted_f1": round(cweighted[2], 4),
        "per_category": {l: {"precision": round(float(a), 4), "recall": round(float(b), 4),
                              "f1": round(float(c), 4), "support": int(d)}
                         for l, a, b, c, d in zip(c_labels, cprec, crec, cf1, csup)},
        "note": "an intent counts as correct at category level when its primary category matches; "
                "categories not present in the test split are listed in categories_missing_from_test",
        "categories_missing_from_test": sorted({c["id"] for c in CATEGORIES_46} - set(c_labels)),
    }
    intents_never_correct = sorted({t for t, pr in zip(y_true, y_pred) if t != pr} - {t for t, pr in zip(y_true, y_pred) if t == pr})

    # out-of-scope and emergency probes (same questions for every pipeline)
    oos = [r for r in probes if r["kind"] == "out_of_scope"]
    emg = [r for r in probes if r["kind"] == "emergency"]
    probe_out = {r["question"]: p.predict(r["question"]) for r in probes}
    def _rej(o):
        return o["status"] != "ok" or o["intent"] == "out_of_scope"
    oos_rejected = sum(_rej(probe_out[r["question"]]) for r in oos)
    oos_wrong = [r["question"] for r in oos if not _rej(probe_out[r["question"]])]
    ctl = [r for r in probes if r["kind"] == "non_emergency"]
    false_alarms = [r["question"] for r in ctl if probe_out[r["question"]]["safety_override"]]
    missed = [r["question"] for r in emg if not probe_out[r["question"]]["safety_override"]]
    emg_resp_urgent = sum(check_safety(probe_out[r["question"]]["response"], True)["score"] >= 85 for r in emg)
    lat += [o["inference_ms"] for o in probe_out.values()]

    rubric = [check_safety(o["response"], safety.assess(q)["emergency"])["score"]
              for q, o in probe_out.items() if o["status"] != "unavailable"]
    entry.update(
        status="evaluated",
        classification={
            "n_test_examples": len(test), "n_classes": len(labels),
            "accuracy": round(accuracy_score(y_true, y_pred), 4),
            "accuracy_note": "rejected (low-confidence) questions count as wrong",
            "macro_precision": round(macro[0], 4), "macro_recall": round(macro[1], 4), "macro_f1": round(macro[2], 4),
            "weighted_precision": round(weighted[0], 4), "weighted_recall": round(weighted[1], 4),
            "weighted_f1": round(weighted[2], 4),
            "per_class": {l: {"precision": round(float(a), 4), "recall": round(float(b), 4),
                              "f1": round(float(c), 4), "support": int(d)}
                          for l, a, b, c, d in zip(labels, prec, rec, f1, sup)},
            "intents_with_zero_correct_test_predictions": intents_never_correct,
            "intent_coverage": round(1 - len(intents_never_correct) / len(labels), 4),
            "category_level": category_metrics,
            "confusion_matrix": {"labels": cm_labels,
                                 "matrix": confusion_matrix(y_true, y_pred, labels=cm_labels).tolist()},
        },
        selective={"coverage": round(len(answered) / len(test), 4), "accuracy_on_answered": None if sel_acc is None else round(sel_acc, 4)},
        calibration={"ece_5bin": _ece(conf, correct), "n": len(conf),
                     "note": "small test set - ECE is very noisy; confidence kinds differ between models"},
        probes={"out_of_scope_n": len(oos), "out_of_scope_rejected": oos_rejected,
                "out_of_scope_answered_as_health_topic": oos_wrong,
                "unsupported_rate_on_test": round(1 - len(answered) / len(test), 4),
                "emergency_n": len(emg), "emergency_responses_with_urgent_guidance": emg_resp_urgent,
                "emergency_missed_by_final_response": missed,
                "non_emergency_controls_n": len(ctl), "false_alarms_on_controls": false_alarms,
                "note": "final response = model intent + shared safety override; see safety_layer for the keyword layer alone"},
        latency_ms={"n": len(lat), "mean": round(statistics.mean(lat), 3), "median": round(statistics.median(lat), 3),
                    "p95": _percentile(lat, 95), "model_load_and_init_ms": round((time.perf_counter() - t_load) * 1000, 3)},
        response_rubric={"method": "automated checks from evaluator.check_safety (disclaimer, doctor advice, no dose, "
                                   "no diagnosis claim, urgent advice if emergency)",
                         "n": len(rubric), "mean_score_0_100": round(statistics.mean(rubric), 2),
                         "limitation": "Checks wording only. NOT proof of factual or clinical correctness."},
    )
    return entry


def main(pipelines=None):
    test = load_split("test")
    with open(PROBES, newline="", encoding="utf-8") as f:
        probes = list(csv.DictReader(f))

    results, load_ms = [], {}
    for cls in (RuleBasedPipeline, SvmPipeline, DistilBertPipeline):
        start = time.perf_counter()
        p = cls()
        load_ms[p.key] = round((time.perf_counter() - start) * 1000, 3)   # loading measured separately
        e = evaluate_pipeline(p, test, probes)
        e["load_time_ms"] = load_ms[p.key]
        results.append(e)

    flagged = [r for r in test if safety.assess(r["text"])["emergency"]]
    urgent_total = [r for r in test if TOPIC_BY_ID[r["label"]]["urgent"]]
    layer = {
        "emergency_probes_detected": sum(safety.assess(r["question"])["emergency"] for r in probes if r["kind"] == "emergency"),
        "emergency_probes_n": sum(r["kind"] == "emergency" for r in probes),
        "test_questions_n": len(test),
        "test_questions_flagged": len(flagged),
        "flagged_with_urgent_topic_label": sum(TOPIC_BY_ID[r["label"]]["urgent"] for r in flagged),
        "urgent_topic_test_questions": len(urgent_total),
        "urgent_topic_questions_flagged": sum(safety.assess(r["text"])["emergency"] for r in urgent_total),
        "flagged_but_non_urgent_topic": [r["text"] for r in flagged if not TOPIC_BY_ID[r["label"]]["urgent"]],
        "note": "keyword safety layer, independent of every model; checked against the project's own 'urgent' topic flag",
    }
    report = {"run_at": datetime.now(timezone.utc).isoformat(),
              "evaluation_set": {"test_csv": "datasets/intent_splits/test.csv", "n_test": len(test),
                                 "probe_csv": "datasets/safety_oos_eval.csv", "n_probes": len(probes)},
              "pipelines": results, "safety_layer": layer,
              "limitations": [
                  "Labels come from the project's own topic list; no clinician-reviewed reference answers exist, so "
                  "factual correctness is NOT measured automatically (use the User Study / human rubric).",
                  "Test set is small (see n_test) and author-written, so differences of a few points are within noise.",
                  "Latency was measured on this machine, single-threaded, models already loaded.",
                  "No model is declared the overall winner: accuracy, latency and safety are reported separately."]}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    rep = main()
    for e in rep["pipelines"]:
        if e["status"] != "evaluated":
            print(e["name"], "->", e["status"], "|", e["reason"][:90]); continue
        c = e["classification"]
        print(f'{e["name"]:20s} acc={c["accuracy"]} macroF1={c["macro_f1"]} cat_acc={c["category_level"]["accuracy"]} cov={e["selective"]["coverage"]} '
              f'oos_rej={e["probes"]["out_of_scope_rejected"]}/{e["probes"]["out_of_scope_n"]} '
              f'lat_mean={e["latency_ms"]["mean"]}ms')
    print("safety layer:", rep["safety_layer"])
