"""
Tests for the Comparison pipelines, evaluation metrics, safety layer and User Study storage.
Run from the project folder:   python -m unittest discover -s tests -v

Note: if `authlib` is not installed (it is only needed for Google login) a tiny stub is
registered so the Flask app can be imported for these tests. It is not used at runtime.
"""
import json
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import authlib  # noqa: F401
except ImportError:
    pkg = types.ModuleType("authlib"); integ = types.ModuleType("authlib.integrations")
    fc = types.ModuleType("authlib.integrations.flask_client")
    class _OAuth:                                            # minimal stub
        def __init__(self, *a, **k): pass
        def register(self, *a, **k): return types.SimpleNamespace()
    fc.OAuth = _OAuth
    sys.modules.update({"authlib": pkg, "authlib.integrations": integ, "authlib.integrations.flask_client": fc})

from database import database as db
_tmp = tempfile.mkdtemp()
db.DATABASE_PATH = os.path.join(_tmp, "test.db")

from chatbot.health_qa import safety
from chatbot.health_qa.pipelines import RuleBasedPipeline, SvmPipeline, DistilBertPipeline
import comparison_service as cs

Q = "Which doctor should I consult for recurring headaches?"


class PipelineTests(unittest.TestCase):
    def test_each_pipeline_returns_same_schema(self):
        keys = set(__import__("chatbot.health_qa.pipelines", fromlist=["RESULT_KEYS"]).RESULT_KEYS)
        for cls in (RuleBasedPipeline, SvmPipeline, DistilBertPipeline):
            self.assertEqual(set(cls().predict(Q)), keys)

    def test_rule_and_svm_answer_and_time_is_positive(self):
        for cls in (RuleBasedPipeline, SvmPipeline):
            out = cls().predict("What causes headaches?")
            self.assertEqual(out["status"], "ok")
            self.assertGreater(out["inference_ms"], 0)

    def test_out_of_scope_gets_fallback(self):
        out = SvmPipeline().predict("What is the capital of France?")
        self.assertEqual(out["status"], "no_match")
        self.assertIn(out["intent"], (None, "out_of_scope"))

    def test_missing_distilbert_is_reported_not_faked(self):
        p = DistilBertPipeline(model_dir=os.path.join(_tmp, "nope"))
        out = p.predict(Q)
        self.assertEqual(out["status"], "unavailable")
        self.assertEqual(out["response"], "")
        self.assertIn("train_distilbert", out["error"])

    def test_missing_svm_artifact_is_reported(self):
        out = SvmPipeline(model_dir=os.path.join(_tmp, "nope")).predict(Q)
        self.assertEqual(out["status"], "unavailable")


class ComparisonTests(unittest.TestCase):
    def test_one_question_reaches_all_three(self):
        seen = []
        orig = dict(cs.PIPELINE_CLASSES)
        class Spy:
            def __init__(self, inner): self.inner = inner
            def info(self): return self.inner.info()
            def predict(self, q): seen.append(q); return self.inner.predict(q)
        cs.reset_pipelines()
        for k in cs.ORDER:
            cs._pipelines[k] = Spy(orig[k]())
        data = cs.run_comparison(Q)
        cs.reset_pipelines()
        self.assertEqual(seen, [Q, Q, Q])
        self.assertEqual(set(data["results"]), {"rule", "ml", "dl"})

    def test_failure_in_one_model_does_not_replace_others(self):
        cs.reset_pipelines()
        class Boom:
            def info(self): return {"architecture": "x"}
            def predict(self, q): raise RuntimeError("boom")
        cs._pipelines["ml"] = Boom()
        data = cs.run_comparison("What causes headaches?")
        cs.reset_pipelines()
        self.assertEqual(data["results"]["ml"]["status"], "error")
        self.assertEqual(data["results"]["ml"]["response"], "")
        self.assertEqual(data["results"]["rule"]["status"], "ok")

    def test_input_validation(self):
        with self.assertRaises(ValueError): cs.run_comparison("   ")
        with self.assertRaises(ValueError): cs.run_comparison("a" * 1001)

    def test_no_winner_field(self):
        self.assertNotIn("best", cs.run_comparison(Q))


class SafetyTests(unittest.TestCase):
    def test_emergencies_flagged_regardless_of_model(self):
        for q in ["I have severe chest pain", "my father's face is drooping and speech slurred",
                  "I can't breathe", "I want to end my life"]:
            self.assertTrue(safety.assess(q)["emergency"], q)

    def test_ordinary_not_flagged(self):
        self.assertFalse(safety.assess("What are common causes of fever?")["emergency"])

    def test_emergency_notice_present_in_comparison(self):
        data = cs.run_comparison("I have severe chest pain and I can't breathe")
        self.assertTrue(data["safety"]["emergency"])
        self.assertIn("112", data["safety"]["notice"])


class EvaluationTests(unittest.TestCase):
    def test_saved_evaluation_matches_recomputation_shape(self):
        from chatbot.health_qa import evaluate
        rep = evaluate.main()
        names = {p["key"]: p for p in rep["pipelines"]}
        self.assertEqual(names["dl"]["status"], "unavailable") if names["dl"]["status"] != "evaluated" else None
        svm = names["ml"]["classification"]
        self.assertEqual(svm["n_test_examples"], rep["evaluation_set"]["n_test"])
        m = svm["confusion_matrix"]["matrix"]
        self.assertEqual(sum(map(sum, m)), svm["n_test_examples"])
        self.assertTrue(0 <= svm["accuracy"] <= 1)

    def test_no_leakage_between_splits(self):
        from chatbot.health_qa.dataset import load_split, normalise
        tr, va, te = (set(normalise(r["text"]) for r in load_split(n)) for n in ("train", "val", "test"))
        self.assertFalse(tr & va); self.assertFalse(tr & te); self.assertFalse(va & te)


class UserStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.create_database()

    def _run(self):
        data = cs.run_comparison("What causes headaches?")
        return db.save_comparison_run(1, data["question"], data["results"], {"rule": None, "ml": "v1", "dl": None}), data

    def _r(self, v):
        return {"correctness": v, "relevance": v, "clarity": v, "completeness": v, "safety": v, "comment": "ok"}

    def test_ratings_stored_against_correct_architecture(self):
        run_id, data = self._run()
        res = db.save_comparison_study("P-test", run_id, {"rule": self._r(2), "ml": self._r(5), "dl": self._r(1)})
        self.assertTrue(res["success"])
        ratable = {k for k, v in data["results"].items() if v["status"] not in ("unavailable", "error")}
        self.assertEqual(res["saved"], len(ratable))            # only models that actually answered can be rated
        rows = {r["architecture"]: r for r in db.get_comparison_study_rows() if r["run_id"] == run_id}
        self.assertEqual(rows["ml"]["correctness"], 5)
        self.assertEqual(rows["rule"]["correctness"], 2)
        self.assertEqual(rows["ml"]["response_shown"], data["results"]["ml"]["response"])
        self.assertEqual("dl" in rows, "dl" in ratable)         # an unavailable DL model is never rated
        s = db.get_comparison_study_summary()
        self.assertGreaterEqual(s["per_architecture"]["ml"]["n"], 1)

    def test_invalid_rating_rejected(self):
        run_id, _ = self._run()
        bad = self._r(3); bad["clarity"] = 9
        self.assertFalse(db.save_comparison_study("P-x", run_id, {"rule": bad})["success"])

    def test_unknown_run_rejected(self):
        self.assertFalse(db.save_comparison_study("P-x", "nope", {"rule": self._r(3)})["success"])


class FlaskRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import legacy_app as appmod
        appmod.app.config["TESTING"] = True
        cls.appmod = appmod
        db.create_database()

    def setUp(self):
        self.client = self.appmod.app.test_client()          # fresh cookie jar per test

    def test_requires_login(self):
        self.assertEqual(self.client.post("/api/comparison/ask", json={"question": Q}).status_code, 401)

    def test_ask_study_summary_export_flow(self):
        with self.client.session_transaction() as s:
            s["user_id"] = 1
        r = self.client.post("/api/comparison/ask", json={"question": "What causes headaches?"})
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(set(body["results"]), {"rule", "ml", "dl"})
        self.assertEqual(self.client.post("/api/comparison/ask", json={"question": ""}).status_code, 400)
        no_consent = self.client.post("/api/comparison/study/submit", json={"run_id": body["run_id"], "ratings": {}})
        self.assertEqual(no_consent.status_code, 400)
        ratings = {a: {c: 4 for c in ("correctness", "relevance", "clarity", "completeness", "safety")}
                   for a in ("rule", "ml", "dl")}
        ok = self.client.post("/api/comparison/study/submit",
                              json={"run_id": body["run_id"], "consent": True, "ratings": ratings})
        self.assertEqual(ok.status_code, 200)
        summ = self.client.get("/api/comparison/study/summary").get_json()["data"]
        self.assertGreaterEqual(summ["completed_ratings"], 2)
        csv_text = self.client.get("/api/comparison/study/export.csv").data.decode()
        self.assertIn("response_shown", csv_text)
        self.assertEqual(self.client.get("/api/comparison/evaluation").status_code, 200)


if __name__ == "__main__":
    unittest.main()
