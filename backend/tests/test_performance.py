"""Tests for the Evaluation-page performance overview, best-architecture rules and the new read-only routes.
Fixtures are test inputs only; the application never fabricates results.
Run:  python -m unittest tests.test_performance -v
"""
import os, sys, tempfile, types, unittest, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import authlib  # noqa: F401
except ImportError:
    pkg = types.ModuleType("authlib"); integ = types.ModuleType("authlib.integrations"); fc = types.ModuleType("authlib.integrations.flask_client")
    class _OAuth:
        def __init__(self, *a, **k): pass
        def register(self, *a, **k): return types.SimpleNamespace()
    fc.OAuth = _OAuth
    sys.modules.update({"authlib": pkg, "authlib.integrations": integ, "authlib.integrations.flask_client": fc})

import comparison_service as cs
import evaluation_service as ev
import performance_service as ps

GOOD = ("### Overview\nFever is a raised body temperature and it may have many causes. Rest, drink fluids and keep cool. "
        "### When to seek help\nPlease see a doctor if the fever lasts more than three days. This is general health information, not a diagnosis.")


def reply(ms=10.0, text=GOOD, status="ok", lang="en", intent="fever"):
    return {"status": status, "response": text, "inference_ms": ms, "intent": intent, "language": {"lang": lang}}


def res(rule, ml, dl):
    return {"rule": {**rule, "name": "Rule-Based"}, "ml": {**ml, "name": "ML"}, "dl": {**dl, "name": "DL"}}


def model(key, overall, safety=100, correctness=80, quality=80, n=100, content=None, median=10, level=None):
    return {"key": key, "name": ps.NAMES[key], "available": True, "unavailable_reason": None, "questions": n, "overall": overall,
            "content": content if content is not None else overall, "correctness": {"value": correctness, "n": n},
            "safety": {"value": safety, "n": n, "level": level or ps._level(safety)}, "quality": {"value": quality, "n": n},
            "speed": {"value": 50, "median_ms": median, "p95_ms": median * 2, "n": n}}


class LanguageScopeTests(unittest.TestCase):
    Q = "what should I do about a fever"

    def test_hinglish_reply_is_not_scored_with_english_rules(self):
        out = cs.rank_responses(self.Q, res(reply(lang="hinglish"), reply(), reply()))
        s = out["scores"]["rule"]
        self.assertIsNone(s["safety"]); self.assertIsNone(s["quality"]); self.assertFalse(s["eligible"])
        self.assertIn("Hinglish", s["excluded_reason"])

    def test_all_hinglish_means_no_winner(self):
        out = cs.rank_responses(self.Q, res(reply(lang="hinglish"), reply(lang="hinglish"), reply(lang="hinglish")))
        self.assertEqual(out["status"], "undetermined"); self.assertIsNone(out["winner_key"])

    def test_tie_reports_fastest_without_crowning_it(self):
        out = cs.rank_responses(self.Q, res(reply(5), reply(500), reply(900)))
        self.assertEqual(out["status"], "tie"); self.assertIsNone(out["winner_key"]); self.assertEqual(out["fastest_key"], "rule")
        self.assertIn("fastest", out["reason"])

    def test_scoring_info_matches_ranking_config(self):
        self.assertEqual(cs.scoring_info()["weights"], cs.RANKING_CONFIG["weights"])
        self.assertAlmostEqual(sum(cs.scoring_info()["weights"].values()), 1.0)


class PickBestTests(unittest.TestCase):
    def test_clear_winner(self):
        out = ps.pick_best({"rule": model("rule", 70), "ml": model("ml", 85), "dl": model("dl", 78)})
        self.assertEqual((out["status"], out["winner_key"]), ("winner", "ml"))
        self.assertIn("85", out["explanation"])

    def test_lead_under_margin_is_tie(self):
        out = ps.pick_best({"rule": model("rule", 80), "ml": model("ml", 81), "dl": model("dl", 60)})
        self.assertEqual(out["status"], "tie"); self.assertEqual(set(out["tied_keys"]), {"rule", "ml"}); self.assertIsNone(out["winner_key"])

    def test_lead_from_speed_alone_is_tie(self):
        out = ps.pick_best({"rule": model("rule", 90, content=80), "ml": model("ml", 70, content=80), "dl": model("dl", 60, content=60)})
        self.assertEqual(out["status"], "tie"); self.assertIn("response time alone", out["explanation"])

    def test_unsafe_model_excluded_even_if_best_overall(self):
        out = ps.pick_best({"rule": model("rule", 95, safety=40, level="Unsafe"), "ml": model("ml", 70), "dl": model("dl", 60)})
        self.assertNotEqual(out["winner_key"], "rule"); self.assertTrue(any(e["key"] == "rule" for e in out["excluded"]))

    def test_too_little_data_is_insufficient(self):
        out = ps.pick_best({"rule": model("rule", 90, n=3), "ml": model("ml", 70, n=3), "dl": model("dl", 60, n=3)})
        self.assertEqual(out["status"], "insufficient"); self.assertIsNone(out["winner_key"])

    def test_unavailable_model_is_listed_not_zeroed(self):
        dl = ps._empty_model("dl"); dl["unavailable_reason"] = "not trained"
        out = ps.pick_best({"rule": model("rule", 90), "ml": model("ml", 70), "dl": dl})
        self.assertEqual(out["winner_key"], "rule"); self.assertTrue(any(e["key"] == "dl" and "not trained" in e["reason"] for e in out["excluded"]))


class BenchmarkTests(unittest.TestCase):
    def test_correctness_matches_the_saved_runs_own_accuracy(self):
        data = ps.benchmark_performance()
        if not data["available"]:
            self.skipTest("no saved evaluation runs")
        for view in data["views"]:
            if view["id"] != "held_out_test":
                continue
            run = ev.get_run(view["runs"][0]["run_id"])
            for k in ps.ORDER:
                m = view["models"][k]
                if m["available"]:
                    expected = run["metrics"][k]["classification"]["accuracy"] * 100
                    self.assertAlmostEqual(m["correctness"]["value"], expected, delta=0.06)

    def test_scores_are_in_range_and_unmeasured_is_none_not_zero(self):
        data = ps.benchmark_performance()
        if not data["available"]:
            self.skipTest("no saved evaluation runs")
        for view in data["views"]:
            for m in view["models"].values():
                for c in ("correctness", "safety", "quality"):
                    if m[c]:
                        self.assertTrue(0 <= m[c]["value"] <= 100)
                if m["overall"] is not None:
                    self.assertTrue(0 <= m["overall"] <= 100)
            if view["id"] == "multilingual":            # all Hindi/Hinglish: safety + quality cannot be scored
                for m in view["models"].values():
                    self.assertIsNone(m["safety"]); self.assertIsNone(m["quality"]); self.assertIn("safety", m["unavailable"])

    def test_no_runs_means_no_numbers(self):
        old = ev.RUN_DIR
        try:
            ev.RUN_DIR = tempfile.mkdtemp()
            out = ps.benchmark_performance()
            self.assertFalse(out["available"]); self.assertEqual(out["views"], [])
        finally:
            ev.RUN_DIR = old


class LiveHistoryTests(unittest.TestCase):
    def runs(self, n, dl_ok=True):
        dl = reply(40) if dl_ok else reply(0, "", status="unavailable")
        return [{"run_id": str(i), "question": "what should I do about a fever", "created_at": "2026-10-28 08:00:00",
                 "results": res(reply(30), reply(5), dl)} for i in range(n)]

    def test_deterministic_and_counts(self):
        a, b = ps.live_history(self.runs(12)), ps.live_history(self.runs(12))
        self.assertEqual(a["counts"], b["counts"]); self.assertEqual(a["count"], 12)

    def test_identical_content_is_tie_not_winner(self):
        out = ps.live_history(self.runs(12))
        self.assertEqual(out["best"]["status"], "tie"); self.assertEqual(out["counts"]["winner"], 0)

    def test_best_needs_all_three_scored(self):
        out = ps.live_history(self.runs(12, dl_ok=False))
        self.assertEqual(out["best"]["status"], "insufficient"); self.assertEqual(out["paired_count"], 0)

    def test_corrupt_row_does_not_hide_others(self):
        runs = self.runs(3) + [{"run_id": "bad", "question": "x", "results": None, "created_at": ""}]
        self.assertEqual(ps.live_history(runs)["count"], 3)


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import database as db
        cls.db = db
        db.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
        db.create_database()
        import legacy_app as appmod
        appmod.app.config["TESTING"] = True
        cls.app = appmod.app

    def client(self, uid=None):
        c = self.app.test_client()
        if uid:
            with c.session_transaction() as s:
                s["user_id"] = uid
        return c

    def test_login_required(self):
        for url in ("/api/comparison/performance", "/api/comparison/history"):
            self.assertEqual(self.client().get(url).status_code, 401)

    def test_history_returns_only_own_runs(self):
        self.db.save_comparison_run(101, "my own fever question", res(reply(30), reply(5), reply(40)))
        self.db.save_comparison_run(202, "someone elses private question", res(reply(30), reply(5), reply(40)))
        body = self.client(101).get("/api/comparison/history").get_json()
        qs = [i["question"] for i in body["data"]["items"]]
        self.assertEqual(qs, ["my own fever question"])

    def test_performance_route_and_page_scoring(self):
        r = self.client(101).get("/api/comparison/performance")
        self.assertEqual(r.status_code, 200); self.assertIn("scoring", r.get_json()["data"])
        page = self.client(101).get("/comparison").get_data(as_text=True)
        self.assertIn("comparison.css", page); self.assertIn("comparison.js", page)
        self.assertIn(str(round(cs.RANKING_CONFIG["weights"]["correctness"] * 100)) + "%", page)


if __name__ == "__main__":
    unittest.main()
