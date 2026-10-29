"""Six symptom architectures, the shared safety layer, the ConversationManager and the held-out evaluator."""
import csv
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.symptom import registry                                      # noqa: E402
from chatbot.symptom.base import RESULT_KEYS                              # noqa: E402
from chatbot.medical import safety                                        # noqa: E402
from chatbot.nlp_based.architecture import analyse                        # noqa: E402
from chatbot.orchestrator.conversation_manager import ConversationManager, is_duration_answer  # noqa: E402
from chatbot.classification import train as clf_train                     # noqa: E402
from evaluation import symptom_evaluator as se                            # noqa: E402

FEVER = "I have had a high fever and chills for 3 days with a bad headache"
EMERGENCIES = ["I have crushing chest pain spreading to my left arm",
               "my father cannot breathe and his lips are turning blue",
               "I want to end my life",
               "seene mein dard ho raha hai saans nahi aa rahi",
               "she suddenly has slurred speech and her face is drooping"]


class ArchitectureContract(unittest.TestCase):
    def test_every_architecture_returns_the_shared_shape(self):
        out = registry.compare(FEVER)
        self.assertEqual(set(out["results"]), set(registry.ORDER))
        for key, r in out["results"].items():
            for k in RESULT_KEYS:
                self.assertIn(k, r, f"{key} missing {k}")
            self.assertIn(r["status"], ("ok", "no_match", "unsupported"), f"{key}: {r['error']}")
            self.assertIsNotNone(r["response_time_ms"])
            self.assertIn(r["safety"]["status"], ("passed", "rejected"))

    def test_architectures_are_distinct_modules(self):
        classes = {type(registry.get(k)).__module__ for k in registry.ORDER}
        self.assertEqual(len(classes), 6)

    def test_only_label_architectures_predict_labels(self):
        out = registry.compare(FEVER)
        for k in ("rule_based", "nlp_based", "generation_based", "rag_based"):
            self.assertIsNone(out["results"][k]["prediction"], k)
        self.assertIsNotNone(out["results"]["classification"]["prediction"])

    def test_off_topic_input_is_declined_by_all(self):
        out = registry.compare("what is the weather in paris today")
        self.assertEqual(out["summary"]["answered"], [])

    def test_rule_and_nlp_and_generation_never_name_diseases(self):
        from chatbot.symptom.knowledge import mentioned_diseases
        for text in (FEVER, "I keep sneezing and have watery eyes", "burning when I pee"):
            for k in ("rule_based", "nlp_based", "generation_based"):
                r = registry.run(k, text)
                self.assertEqual(mentioned_diseases(r["response"]), set(), f"{k}: {text}")

    def test_one_failing_architecture_does_not_break_comparison(self):
        arch = registry.get("nlp_based")
        with mock.patch.object(type(arch), "_answer", side_effect=RuntimeError("boom")):
            out = registry.compare(FEVER)
        self.assertEqual(out["results"]["nlp_based"]["status"], "error")
        self.assertIn("boom", out["results"]["nlp_based"]["error"])
        self.assertEqual(out["results"]["rule_based"]["status"], "ok")


class NlpPipeline(unittest.TestCase):
    def test_negation_is_excluded(self):
        a = analyse("I have a cough but no fever and not vomiting")
        ids = [s["id"] for s in a["symptoms"]]
        self.assertIn("cough", ids)
        self.assertNotIn("fever", ids)
        self.assertIn("fever", a["negated"])
        self.assertIn("vomiting", a["negated"])

    def test_entities(self):
        a = analyse("severe headache for two days, temperature 39.8 C")
        self.assertEqual(a["duration"]["value"], 2)
        self.assertEqual(a["temperature"]["value"], 39.8)
        self.assertEqual(a["symptoms"][0]["modifier"] or [s for s in a["symptoms"] if s["modifier"]][0]["modifier"], "severe")


class SafetyLayer(unittest.TestCase):
    def test_emergency_overrides_every_architecture_across_phrasings(self):
        for text in EMERGENCIES:
            out = registry.compare(text)
            self.assertTrue(out["safety"]["emergency"], text)
            for k, r in out["results"].items():
                self.assertEqual(r["safety"]["status"], "emergency_override", f"{k}: {text}")
                self.assertRegex(r["response"], r"112|emergency|Tele-MANAS|14416")

    def test_informational_question_about_emergency_is_not_an_alarm(self):
        self.assertFalse(safety.assess_input("What are the warning signs of a stroke?")["emergency"])

    def test_gate_rejects_rather_than_downscores(self):
        for bad in ("Take 500 mg paracetamol twice a day.", "You have diabetes. Eat less sugar.",
                    "There is no need to see a doctor for this."):
            self.assertEqual(safety.check_response(bad)["status"], "rejected", bad)
        raw = {"status": "ok", "response": "Take 2 tablets of ibuprofen every 4 hours."}
        out = safety.apply("I have a headache", raw)
        self.assertEqual(out["safety"]["status"], "rejected")
        self.assertEqual(out["response"], safety.SAFE_FALLBACK)
        self.assertEqual(out["withheld_response"], raw["response"])

    def test_emergency_reply_without_urgent_advice_is_rejected(self):
        self.assertEqual(safety.check_response("Rest and drink water.", emergency=True)["status"], "rejected")


class ConversationFlow(unittest.TestCase):
    def test_duration_answer_detection(self):
        for t in ("two days", "for 3 weeks", "since yesterday", "about a week now"):
            self.assertTrue(is_duration_answer(t), t)
        for t in ("I have a headache", "what is malaria", "two days ago I fell and hurt my knee badly"):
            self.assertFalse(is_duration_answer(t), t)

    def test_follow_up_is_attached_to_previous_symptom(self):
        cm = ConversationManager("symptom", "generation_based")
        r1 = cm.process("I have fever")
        self.assertEqual(r1["state"]["pending"], "duration")
        r2 = ConversationManager("symptom", "generation_based", r1["state"]).process("Two days")
        self.assertIn("two days", r2["reply"].lower())
        self.assertIn("fever", r2["reply"].lower())
        self.assertIsNone(r2["state"]["pending"])
        self.assertEqual(r2["handled_by"], "symptom:generation_based")

    def test_follow_up_works_for_every_architecture_that_asks(self):
        for k in registry.ORDER:
            r1 = ConversationManager("symptom", k).process("I have a cough")
            if r1["state"]["pending"] == "duration":
                r2 = ConversationManager("symptom", k, r1["state"]).process("3 days")
                self.assertTrue(r2["reply"].startswith("Thanks - noted"), k)

    def test_greeting_and_explicit_question_routing(self):
        cm = ConversationManager("symptom", "rule_based")
        self.assertIn("small talk", cm.process("hello")["handled_by"])
        r = cm.process("What is the treatment for malaria?")
        self.assertIn("health_qa", r["handled_by"])

    def test_emergency_beats_pending_follow_up(self):
        r1 = ConversationManager("symptom", "nlp_based").process("I have a headache")
        r2 = ConversationManager("symptom", "nlp_based", r1["state"]).process("now I can't breathe")
        self.assertEqual(r2["safety_status"], "emergency_override")

    def test_invalid_bot_rejected(self):
        with self.assertRaises(ValueError):
            ConversationManager("symptom", "dl")


class HeldOutEvaluation(unittest.TestCase):
    def test_split_has_no_leakage(self):
        tr = {r["text"] for r in clf_train.load_split("train")}
        va = {r["text"] for r in clf_train.load_split("val")}
        te = {r["text"] for r in clf_train.load_split("test")}
        self.assertFalse(tr & te)
        self.assertFalse(va & te)
        self.assertEqual(len({r["label"] for r in clf_train.load_split("test")}), 24)

    def test_split_is_reproducible(self):
        from chatbot.symptom.knowledge import load_symptom2disease
        rows = load_symptom2disease()
        a = clf_train.make_splits(rows, 42, write=False)
        b = clf_train.make_splits(rows, 42, write=False)
        self.assertEqual([r["row_id"] for r in a["test"]], [r["row_id"] for r in b["test"]])
        self.assertGreater(a["_stats"]["exact_duplicates_removed"], 0)       # the file really has duplicates

    def test_sampling_is_deterministic_and_stratified(self):
        rows, _ = se.load_rows()
        s1, s2 = se.sample(rows, 48, 7), se.sample(rows, 48, 7)
        self.assertEqual(s1, s2)
        self.assertEqual(len({r[2] for r in s1}), 24)
        self.assertNotEqual(se.sample(rows, 48, 8), s1)

    def test_run_records_results_and_appends_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(se, "RUN_DIR", tmp), mock.patch.object(se, "RESULTS_CSV", os.path.join(tmp, "r.csv")):
                for _ in range(2):
                    st = se.start(sample_size=24, seed=1, architectures=["classification", "rule_based"], wait=True)
                    self.assertEqual(st["status"], "completed", st["error"])
                with open(os.path.join(tmp, "r.csv"), newline="") as f:
                    rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4)                          # appended, never overwritten
        clf = st["architectures"]["classification"]
        self.assertIsNotNone(clf["label_metrics"]["accuracy"])
        self.assertIsNone(st["architectures"]["rule_based"]["label_metrics"])
        self.assertTrue(any("Small sample" in w for w in st["warnings"]))
        self.assertEqual(clf["requests"], 24)

    def test_legacy_full_dataset_is_labelled_in_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(se, "RUN_DIR", tmp), mock.patch.object(se, "RESULTS_CSV", os.path.join(tmp, "r.csv")):
                st = se.start(sample_size=24, architectures=["classification"], legacy_full_dataset=True, wait=True)
        self.assertTrue(st["dataset"]["in_sample"])
        self.assertIn("IN-SAMPLE", st["architectures"]["classification"]["warning"])
        self.assertTrue(any("in-sample" in w for w in st["warnings"]))

    def test_unknown_architecture_rejected(self):
        with self.assertRaises(ValueError):
            se.start(architectures=["gpt"], wait=True)


if __name__ == "__main__":
    unittest.main()
