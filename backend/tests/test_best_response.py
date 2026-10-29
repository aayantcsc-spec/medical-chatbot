"""Tests for the single-question 'Best Overall Response' (comparison_service.rank_responses).
Fixtures below are test inputs only; the application itself never fabricates results.
Run from the project folder:   python -m unittest tests.test_best_response -v
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import comparison_service as cs

GOOD = ("### Overview\nFever is a raised body temperature and it may have many causes. Rest, drink fluids and keep cool. "
        "### When to seek help\nPlease see a doctor if the fever lasts more than three days or is very high. "
        "This is general health information, not a diagnosis. " * 1)
NOSAFE = "Fever is a high temperature. Take 500 mg paracetamol now. You have an infection. No need to see a doctor."
SHORT = "I am not sure I understood that."


def r(text, ms=10.0, status="ok", name="X"):
    return {"name": name, "status": status, "response": text, "inference_ms": ms, "confidence": 0.99}


def res(rule, ml, dl):
    return {"rule": {**rule, "name": "Rule-Based"}, "ml": {**ml, "name": "ML"}, "dl": {**dl, "name": "DL"}}


class RankTests(unittest.TestCase):
    Q = "what should I do about fever and high temperature"

    def test_unsafe_reply_never_wins_even_if_fastest(self):
        out = cs.rank_responses(self.Q, res(r(NOSAFE, 1), r(GOOD, 50), r(SHORT, 5)))
        self.assertNotEqual(out["winner_key"], "rule")
        self.assertIn("rule", [e["key"] for e in out["excluded"]])

    def test_only_one_comparable_reply_is_undetermined(self):
        out = cs.rank_responses(self.Q, res(r(GOOD), r("", status="unavailable"), r("", status="error")))
        self.assertEqual(out["status"], "undetermined")
        self.assertIsNone(out["winner_key"])
        self.assertEqual("No Clear Winner", out["headline"])

    def test_identical_replies_are_a_tie_even_if_speed_differs(self):
        out = cs.rank_responses(self.Q, res(r(GOOD, 5), r(GOOD, 500), r(GOOD, 900)))
        self.assertEqual(out["status"], "tie")
        self.assertIsNone(out["winner_key"])

    def test_clear_winner_and_confidence_ignored(self):
        weak = "Fever is hot. See a doctor."
        a, b = r(GOOD, 20), r(weak, 20); b["confidence"] = 1.0; a["confidence"] = 0.01
        out = cs.rank_responses(self.Q, res(a, b, r(SHORT, 20)))
        self.assertEqual(out["status"], "winner")
        self.assertEqual(out["winner_key"], "rule")

    def test_emergency_without_urgent_advice_is_excluded(self):
        out = cs.rank_responses("I have severe chest pain", res(r(GOOD), r(GOOD), r(GOOD)), {"emergency": True})
        self.assertTrue(all(not s["eligible"] for s in out["scores"].values()))
        self.assertEqual(out["status"], "undetermined")

    def test_devanagari_reply_reports_unavailable_not_a_score(self):
        out = cs.rank_responses(self.Q, res(r("बुखार में आराम करें और डॉक्टर से मिलें"), r(GOOD), r(GOOD)))
        s = out["scores"]["rule"]
        self.assertIsNone(s["safety"]); self.assertIn("safety", s["unavailable"])

    def test_no_match_cannot_win(self):
        out = cs.rank_responses(self.Q, res(r(GOOD), r(SHORT, status="no_match"), r(GOOD, 30)))
        self.assertNotEqual(out["winner_key"], "ml")

    def test_run_comparison_exposes_selection_without_breaking_keys(self):
        import unittest.mock as mock
        class P:
            def __init__(s, k): s.k = k
            def info(s): return {"architecture": "a", "version": "v"}
            def predict(s, q, context=None):
                return {"status": "ok", "response": GOOD, "intent": "fever", "confidence": .9, "confidence_kind": "t",
                        "inference_ms": 3.0, "error": None, "category": None, "categories": [], "safety_override": False,
                        "top_k": [], "language": {"lang": "en"}, "canonical_text": q, "symptoms": [], "question_kind": None,
                        "reply_topic": None, "handled_by": "model"}
        with mock.patch.object(cs, "get_pipeline", lambda k: P(k)):
            d = cs.run_comparison("I have a fever")
        self.assertIn("overall_selection", d); self.assertIn("results", d); self.assertNotIn("best", d)
        self.assertIn(d["overall_selection"]["status"], ("winner", "tie", "undetermined"))


class CorrectnessAndWeightsTests(unittest.TestCase):
    LABELLED = "mujhe bukhar hai aur badan toot raha hai"      # in datasets/multilingual_eval.csv, label: fever

    def test_weights_are_40_30_20_10(self):
        self.assertEqual(cs.RANKING_CONFIG["weights"], {"correctness": 0.4, "safety": 0.3, "quality": 0.2, "speed": 0.1})

    def test_correctness_uses_dataset_label_and_wrong_topic_scores_zero(self):
        a, b, c = r(GOOD, 10), r(GOOD, 10), r(GOOD, 10)
        a["intent"], b["intent"], c["intent"] = "fever", "headache", "fever"
        out = cs.rank_responses(self.LABELLED, res(a, b, c))
        self.assertEqual(out["method"]["ground_truth"]["expected"], "fever")
        self.assertEqual([out["scores"][k]["correctness"] for k in ("rule", "ml", "dl")], [100, 0, 100])
        self.assertNotEqual(out["winner_key"], "ml")

    def test_correctness_unavailable_for_unlabelled_question_and_weights_rebalance(self):
        out = cs.rank_responses("some brand new question about my knee pain", res(r(GOOD), r(GOOD), r(GOOD)))
        self.assertFalse(out["method"]["ground_truth"]["available"])
        for s in out["scores"].values():
            self.assertIsNone(s["correctness"]); self.assertIn("correctness", s["unavailable"])
        self.assertTrue(all(0 <= s["overall"] <= 100 for s in out["scores"].values()))

    def test_unsafe_reply_cannot_win_even_with_correct_topic(self):
        bad = r(NOSAFE, 1); bad["intent"] = "fever"
        ok = r(GOOD, 40); ok["intent"] = "headache"
        out = cs.rank_responses(self.LABELLED, res(bad, ok, r(GOOD, 60)))
        self.assertNotEqual(out["winner_key"], "rule")


if __name__ == "__main__":
    unittest.main()
