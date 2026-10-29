"""Evaluation service: metric maths, dataset validation, real runs with failing models, persistence, CSV."""
import csv
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import evaluation_service as E  # noqa: E402


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class MetricTests(unittest.TestCase):
    """Fixture computed by hand.
    y_true = a a b b c      y_pred = a b b b a
    confusion (rows true, cols pred) over [a,b,c]: [[1,1,0],[0,2,0],[1,0,0]]
    a: P=1/2 R=1/2 F1=.5 | b: P=2/3 R=1 F1=.8 | c: P=0 R=0 F1=0
    accuracy 3/5; macro P=.3889 R=.5 F1=.4333; weighted P=.4667"""
    Y_TRUE = list("aabbc")
    Y_PRED = list("abbba")

    def test_known_fixture(self):
        m = E.classification_metrics(self.Y_TRUE, self.Y_PRED, ["a", "b", "c"])
        self.assertEqual(m["n"], 5)
        self.assertAlmostEqual(m["accuracy"], 0.6)
        self.assertEqual(m["confusion_matrix"], [[1, 1, 0], [0, 2, 0], [1, 0, 0]])
        self.assertAlmostEqual(m["per_class"]["a"]["precision"], 0.5)
        self.assertAlmostEqual(m["per_class"]["b"]["precision"], 0.6667, places=3)
        self.assertAlmostEqual(m["per_class"]["b"]["recall"], 1.0)
        self.assertAlmostEqual(m["per_class"]["b"]["f1"], 0.8)
        self.assertEqual(m["per_class"]["c"]["f1"], 0.0)
        self.assertAlmostEqual(m["macro"]["precision"], 0.3889, places=3)
        self.assertAlmostEqual(m["macro"]["recall"], 0.5, places=3)
        self.assertAlmostEqual(m["macro"]["f1"], 0.4333, places=3)
        self.assertAlmostEqual(m["weighted"]["precision"], 0.4667, places=3)

    def test_matches_scikit_learn(self):
        try:
            from sklearn.metrics import precision_recall_fscore_support, accuracy_score
        except ImportError:
            self.skipTest("scikit-learn not installed")
        import random
        rng = random.Random(7)
        labels = list("abcde")
        yt = [rng.choice(labels) for _ in range(200)]
        yp = [t if rng.random() < .6 else rng.choice(labels) for t in yt]
        mine = E.classification_metrics(yt, yp, labels)
        p, r, f, s = precision_recall_fscore_support(yt, yp, labels=labels, zero_division=0)
        self.assertAlmostEqual(mine["accuracy"], accuracy_score(yt, yp), places=3)
        for i, l in enumerate(labels):
            self.assertAlmostEqual(mine["per_class"][l]["precision"], p[i], places=3)
            self.assertAlmostEqual(mine["per_class"][l]["recall"], r[i], places=3)
            self.assertAlmostEqual(mine["per_class"][l]["f1"], f[i], places=3)

    def test_empty_input_has_no_fabricated_accuracy(self):
        m = E.classification_metrics([], [])
        self.assertEqual(m["n"], 0)
        self.assertIsNone(m["accuracy"])

    def test_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            E.classification_metrics(["a"], ["a", "b"])

    def test_latency_percentiles(self):
        s = E.latency_stats([10, 20, 30, 40, 100])
        self.assertEqual(s["median_ms"], 30)
        self.assertEqual(s["mean_ms"], 40)
        self.assertEqual(s["p90_ms"], 76.0)          # linear interpolation: 40 + 0.6*(100-40)
        self.assertEqual(s["max_ms"], 100)
        self.assertIsNone(E.latency_stats([])["median_ms"])
        self.assertEqual(E.latency_stats([None, 5])["n"], 1)


class TempDatasetCase(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.runs = tempfile.mkdtemp()
        self.patches = [mock.patch.object(E, "DATA_DIR", self.data), mock.patch.object(E, "RUN_DIR", self.runs),
                        mock.patch.object(E, "DATASETS", dict(E.DATASETS)),
                        mock.patch.object(E, "_model_infos", lambda models: {k: {"available": True, "version": f"{k}-test", "architecture": k} for k in models})]
        for p in self.patches:
            p.start()
        E.DATASETS["tmp"] = {"title": "tmp", "files": ["tmp.csv"], "kind": "exact", "text": "question", "id": None, "label": "label"}
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        E._active.clear()

    def put(self, header, rows):
        write_csv(os.path.join(self.data, "tmp.csv"), header, rows)


class ValidationTests(TempDatasetCase):
    def test_valid_dataset(self):
        self.put(["question", "label"], [["I have a fever", "fever"], ["I have a headache", "headache"]])
        d = E.load_dataset("tmp")
        self.assertTrue(d["validation"]["valid"])
        self.assertEqual(d["validation"]["rows_usable"], 2)
        self.assertEqual(len(d["version"]), 12)

    def test_zero_byte_file_like_the_shipped_evaluation_expected_csv(self):
        open(os.path.join(self.data, "tmp.csv"), "w").close()
        d = E.load_dataset("tmp")
        self.assertFalse(d["validation"]["valid"])
        self.assertIn("empty", " ".join(d["validation"]["issues"]))
        with self.assertRaises(ValueError):
            E.start_run("tmp")

    def test_header_only_dataset_is_rejected(self):
        self.put(["question", "label"], [])
        with self.assertRaises(ValueError):
            E.start_run("tmp")

    def test_missing_column(self):
        self.put(["question", "wrong_name"], [["I have a fever", "fever"]])
        d = E.load_dataset("tmp")
        self.assertFalse(d["validation"]["valid"])
        self.assertIn("missing required column", d["validation"]["issues"][0])

    def test_missing_file(self):
        self.assertFalse(E.load_dataset("tmp")["validation"]["valid"])

    def test_label_that_is_not_a_model_intent_is_excluded_with_a_reason(self):
        self.put(["question", "label"], [["I have a fever", "fever"], ["what is love", "romance"], ["blank label", ""]])
        d = E.load_dataset("tmp")
        reasons = {x["reason"] for x in d["validation"]["excluded"]}
        self.assertEqual(d["validation"]["rows_usable"], 1)
        self.assertTrue(any("label mismatch" in r for r in reasons))
        self.assertTrue(any("missing expected label" in r for r in reasons))

    def test_all_labels_mismatched_cannot_be_run(self):
        self.put(["question", "label"], [["a b c", "nope"], ["d e f", "nada"]])
        with self.assertRaises(ValueError):
            E.start_run("tmp")

    def test_duplicates_and_conflicting_duplicates(self):
        self.put(["question", "label"], [["I have a fever", "fever"], ["i have a FEVER!", "fever"], ["Is it bad?", "fever"], ["is it bad", "headache"]])
        d = E.load_dataset("tmp")
        reasons = [x["reason"] for x in d["validation"]["excluded"]]
        self.assertEqual(d["validation"]["rows_usable"], 1)
        self.assertTrue(any("duplicate" in r for r in reasons))
        self.assertEqual(sum("conflicting" in r for r in reasons), 2)

    def test_question_overlapping_training_data_is_excluded(self):
        os.makedirs(os.path.join(self.data, "intent_splits"))
        write_csv(os.path.join(self.data, "intent_splits", "train.csv"), ["text", "label"], [["I have a fever", "fever"]])
        self.put(["question", "label"], [["I have a fever!", "fever"], ["My head hurts a lot", "headache"]])
        d = E.load_dataset("tmp")
        self.assertEqual(d["validation"]["rows_usable"], 1)
        self.assertIn("leakage", d["validation"]["excluded"][0]["reason"])

    def test_shipped_question_bank_loads_with_the_label_map(self):
        with mock.patch.object(E, "DATA_DIR", os.path.join(ROOT, "datasets")):
            d = E.load_dataset("question_bank")
        v = d["validation"]
        self.assertTrue(v["valid"])
        self.assertEqual(v["rows_in_file"], 300)
        self.assertGreater(v["rows_usable"], 250)
        self.assertTrue(any("mapping" in w for w in v["warnings"]))


def fake_runner_factory(answers, fail_keys=(), unavailable_keys=()):
    def runner(key, question):
        if key in unavailable_keys:
            return {"status": "unavailable", "error": f"{key} model file missing", "response": "", "intent": None, "confidence": None, "inference_ms": None}
        if key in fail_keys:
            raise RuntimeError("inference exploded")
        return {"status": "ok", "intent": answers.get(question, "fever"), "response": f"reply for {question}", "confidence": .9, "inference_ms": 4.0}
    return runner


class RunTests(TempDatasetCase):
    ROWS = [["I have a fever", "fever"], ["I have a headache", "headache"], ["I feel dizzy", "dizziness"], ["I have a cough", "cough"]]

    def setUp(self):
        super().setUp()
        self.put(["question", "label"], self.ROWS)

    def run_ok(self, **kw):
        runner = fake_runner_factory({"I have a headache": "headache", "I feel dizzy": "headache", "I have a cough": "cough"}, **kw)
        st = E.start_run("tmp", "full", runner=runner, wait=True)
        return E.get_run(st["run_id"])

    def test_metrics_are_computed_from_actual_predictions(self):
        run = self.run_ok()
        self.assertEqual(run["status"], "completed")
        m = run["metrics"]["rule"]
        self.assertEqual(m["valid_predictions"], 4)
        self.assertAlmostEqual(m["classification"]["accuracy"], 0.75)       # dizzy question predicted wrongly
        self.assertEqual(m["classification"]["per_class"]["dizziness"]["recall"], 0.0)
        self.assertEqual(m["latency"]["median_ms"], 4.0)

    def test_crashing_model_does_not_stop_the_run_or_fake_metrics(self):
        run = self.run_ok(fail_keys=("ml",))
        self.assertEqual(run["status"], "completed")
        ml = run["metrics"]["ml"]
        self.assertEqual(ml["valid_predictions"], 0)
        self.assertEqual(ml["failed"], 4)
        self.assertEqual(ml["failure_rate"], 1.0)
        self.assertIsNone(ml.get("classification"))                 # no accuracy invented for a model that never answered
        self.assertEqual(run["progress"]["errors"], 4)
        self.assertEqual(run["metrics"]["rule"]["valid_predictions"], 4)   # other models unaffected
        self.assertIn("inference exploded", run["per_question"][0]["models"]["ml"]["error"])

    def test_unavailable_model_is_recorded_not_hidden(self):
        run = self.run_ok(unavailable_keys=("dl",))
        dl = run["metrics"]["dl"]
        self.assertEqual(dl["availability_rate"], 0.0)
        self.assertEqual(run["per_question"][0]["models"]["dl"]["status"], "unavailable")
        self.assertIsNone(dl.get("classification"))

    def test_progress_counts_and_final_state(self):
        run = self.run_ok()
        self.assertEqual(run["progress"]["completed"], run["progress"]["total"], 4)
        self.assertIsNone(run["progress"]["current"])
        self.assertIsNotNone(run["finished_at"])

    def test_quick_mode_is_flagged_as_a_sample_and_never_claims_full(self):
        write_csv(os.path.join(self.data, "tmp.csv"), ["question", "label"],
                  [[f"question number {i}", "fever" if i % 2 else "headache"] for i in range(80)])
        st = E.start_run("tmp", "quick", runner=fake_runner_factory({}), wait=True)
        run = E.get_run(st["run_id"])
        self.assertEqual(run["progress"]["total"], E.QUICK_SIZE)
        self.assertTrue(run["sampled"])
        self.assertTrue(any("Quick test" in l for l in run["limitations"]))
        full = E.get_run(E.start_run("tmp", "full", runner=fake_runner_factory({}), wait=True)["run_id"])
        self.assertFalse(full["sampled"]); self.assertEqual(full["progress"]["total"], 80)

    def test_quick_sample_is_reproducible(self):
        rows = E.load_dataset("tmp")["rows"]
        a = [r["id"] for r in E.select_rows(rows, "quick", 3)]
        b = [r["id"] for r in E.select_rows(rows, "quick", 3)]
        self.assertEqual(a, b)

    def test_results_persist_and_reload_after_a_restart(self):
        run = self.run_ok()
        E._active.clear()                                           # simulate a new process
        again = E.get_run(run["run_id"])
        self.assertEqual(again["metrics"]["rule"]["classification"]["accuracy"], run["metrics"]["rule"]["classification"]["accuracy"])
        listed = E.list_runs()
        self.assertEqual(listed[0]["run_id"], run["run_id"])
        self.assertEqual(listed[0]["status"], "completed")
        self.assertEqual(E.latest_run()["run_id"], run["run_id"])
        self.assertEqual(again["dataset"]["version"], run["dataset"]["version"])
        self.assertEqual(again["models"]["rule"]["version"], "rule-test")

    def test_run_left_running_by_a_dead_server_is_reported_failed_not_running(self):
        run = self.run_ok()
        path = os.path.join(self.runs, run["run_id"] + ".json")
        st = json.load(open(path)); st["status"] = "running"; json.dump(st, open(path, "w"))
        E._active.clear()
        got = E.get_run(run["run_id"])
        self.assertEqual(got["status"], "failed")
        self.assertIn("interrupted", got["error"])

    def test_only_one_run_at_a_time(self):
        gate = threading.Event()
        def slow(key, q):
            gate.wait(5)
            return {"status": "ok", "intent": "fever", "response": "", "confidence": 1, "inference_ms": 1}
        first = E.start_run("tmp", "full", runner=slow)
        try:
            with self.assertRaises(RuntimeError):
                E.start_run("tmp", "full", runner=slow)
            self.assertIn(E.get_status(first["run_id"])["status"], ("pending", "running"))
        finally:
            gate.set()
        for _ in range(100):
            if E.get_status(first["run_id"])["status"] == "completed":
                break
            threading.Event().wait(.05)
        self.assertEqual(E.get_status(first["run_id"])["status"], "completed")

    def test_unknown_or_malicious_run_id(self):
        self.assertIsNone(E.get_run("../../etc/passwd"))
        self.assertIsNone(E.get_run("does-not-exist"))

    def test_csv_export(self):
        run = self.run_ok(fail_keys=("ml",))
        rows = list(csv.DictReader(io.StringIO(E.export_csv(run["run_id"]))))
        self.assertEqual(len(rows), 4 * 3)                           # 4 questions x 3 models
        self.assertEqual({r["model"] for r in rows}, {"rule", "ml", "dl"})
        ml = [r for r in rows if r["model"] == "ml"][0]
        self.assertEqual(ml["status"], "error")
        self.assertEqual(ml["correct_strict"], "")
        self.assertIn("model_version", rows[0]); self.assertIn("dataset_version", rows[0])
        self.assertIsNone(E.export_csv("nope"))

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            E.start_run("tmp", "medium")
        with self.assertRaises(ValueError):
            E.start_run("tmp", "full", models=["gpt"])
        with self.assertRaises(ValueError):
            E.start_run("not_a_dataset")


class MappedScoringTests(unittest.TestCase):
    def test_strict_vs_lenient_with_multi_category_intent(self):
        lm = {"chest_pain_emergency": ["emergency", "cardiovascular"], "fever": ["fever"], "out_of_scope": []}
        spec = {"kind": "mapped"}
        item = {"expected": "cardiovascular"}
        rec = {"status": "ok", "intent": "chest_pain_emergency"}
        E._score_classification(item, rec, spec, lm)
        self.assertFalse(rec["correct_strict"]); self.assertTrue(rec["correct_lenient"])
        rec2 = {"status": "ok", "intent": "out_of_scope"}
        E._score_classification(item, rec2, spec, lm)
        self.assertFalse(rec2["correct_lenient"]); self.assertEqual(rec2["predicted"], E.NO_MATCH)
        rec3 = {"status": "error", "intent": None}
        E._score_classification(item, rec3, spec, lm)
        self.assertIsNone(rec3["correct_lenient"])

    def test_label_map_covers_every_model_intent(self):
        from chatbot.health_qa.knowledge import TOPIC_BY_ID
        with mock.patch.object(E, "LABEL_MAP_FILE", os.path.join(ROOT, "datasets", "evaluation_label_map.json")):
            lm = E.load_label_map()
        self.assertEqual(set(lm), set(TOPIC_BY_ID))


if __name__ == "__main__":
    unittest.main()
