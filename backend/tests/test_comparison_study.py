"""Comparison API behaviour and the User Study (storage, validation, duplicates, aggregation, export)."""
import csv
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from database import database as db   # noqa: E402
import comparison_service as cs       # noqa: E402


class FakePipe:
    """Records exactly what each pipeline was given, so tests can prove all three got the same input."""
    seen = []

    def __init__(self, key, fail=False, intent="fever"):
        self.key, self.fail, self.intent = key, fail, intent

    def info(self):
        return {"architecture": f"arch-{self.key}", "version": f"{self.key}-v9", "artifact": f"models/{self.key}"}

    def predict(self, question, context=None):
        FakePipe.seen.append((self.key, question, context))
        if self.fail:
            raise RuntimeError("model exploded")
        return {"status": "ok", "response": f"### Overview\nanswer from {self.key}", "intent": self.intent, "confidence": .5,
                "confidence_kind": "test", "inference_ms": 3.0, "error": None, "category": "x", "categories": [],
                "safety_override": False, "top_k": [], "language": {"lang": "en"}, "canonical_text": "q", "symptoms": [],
                "question_kind": "symptom", "reply_topic": None, "handled_by": "model"}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "study.db")
        db.create_database()
        import legacy_app as A
        cls.A = A
        for i, name in enumerate(("a", "b", "c")):
            db.create_user("U", name, f"{name}@example.com", "Passw0rd!x")
        cls.u = [db.get_user_by_email(f"{n}@example.com")["id"] for n in ("a", "b", "c")]

    def client(self, uid=None):
        c = self.A.app.test_client()
        if uid:
            with c.session_transaction() as s:
                s["user_id"], s["user_name"], s["user_email"] = uid, "T", "t@x.com"
        return c

    def patch_pipes(self, **fails):
        pipes = {k: FakePipe(k, fail=fails.get(k, False)) for k in cs.ORDER}
        FakePipe.seen = []
        return mock.patch.object(cs, "get_pipeline", lambda k: pipes[k])


class ComparisonApiTests(Base):
    def test_requires_login(self):
        self.assertEqual(self.client().post("/api/comparison/ask", json={"question": "hi"}).status_code, 401)
        self.assertEqual(self.client().get("/comparison").status_code, 302)

    def test_same_original_question_and_context_reach_all_three_models(self):
        with self.patch_pipes():
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "Mujhe bukhar hai", "context_topic": "fever"}).get_json()
        self.assertTrue(j["success"])
        self.assertEqual(len(FakePipe.seen), 3)
        self.assertEqual({q for _, q, _ in FakePipe.seen}, {"Mujhe bukhar hai"})
        self.assertEqual({str(c) for _, _, c in FakePipe.seen}, {str({"topic": "fever"})})

    def test_each_model_has_its_own_answer_version_and_timing(self):
        with self.patch_pipes():
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "I have fever"}).get_json()
        for k in cs.ORDER:
            r = j["results"][k]
            self.assertIn(f"answer from {k}", r["response"])
            self.assertEqual(r["version"], f"{k}-v9")
            self.assertEqual(r["architecture"], f"arch-{k}")
            self.assertGreaterEqual(r["inference_ms"], 0)
            self.assertEqual(r["name"], cs.BOT_NAMES[k])

    def test_partial_failure_stays_inside_its_card(self):
        with self.patch_pipes(ml=True):
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "I have fever"}).get_json()
        self.assertTrue(j["success"])
        self.assertEqual(j["results"]["ml"]["status"], "error")
        self.assertIn("model exploded", j["results"]["ml"]["error"])
        self.assertEqual(j["results"]["ml"]["response"], "")                       # no substituted answer
        self.assertIn("answer from rule", j["results"]["rule"]["response"])
        self.assertIn("answer from dl", j["results"]["dl"]["response"])
        self.assertTrue(any("could not run" in n for n in j["notes"]))
        self.assertIsNone(j["results"]["ml"]["structure"])

    def test_differences_summary_does_not_declare_a_winner(self):
        pipes = {"rule": FakePipe("rule", intent="fever"), "ml": FakePipe("ml", intent="cough"), "dl": FakePipe("dl", intent="fever")}
        with mock.patch.object(cs, "get_pipeline", lambda k: pipes[k]):
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "I have fever"}).get_json()
        text = " ".join(j["notes"]).lower()
        self.assertIn("different topics", text)
        for word in ("winner", "best", "more accurate", "correct answer"):
            self.assertNotIn(word, text)
        self.assertIn("not a quality score", j["notes_kind"])

    def test_history_is_saved_with_exact_responses_and_versions(self):
        with self.patch_pipes():
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "I have fever"}).get_json()
        run = db.get_comparison_run(j["run_id"])
        self.assertEqual(run["user_id"], self.u[0])
        self.assertEqual(run["question"], "I have fever")
        self.assertEqual(run["results"]["rule"]["response"], j["results"]["rule"]["response"])
        self.assertEqual(run["model_versions"]["dl"], "dl-v9")

    def test_validation(self):
        c = self.client(self.u[0])
        self.assertEqual(c.post("/api/comparison/ask", json={"question": ""}).status_code, 400)
        self.assertEqual(c.post("/api/comparison/ask", json={"question": "x" * 1500}).status_code, 400)

    def test_real_pipelines_end_to_end_hinglish(self):
        c = self.client(self.u[0])
        j = c.post("/api/comparison/ask", json={"question": "Mujhe bukhar aur khansi ho rahi hai, kya karu?"}).get_json()
        self.assertEqual(j["language"]["lang"], "hinglish")
        self.assertEqual(set(j["symptoms"]), {"fever", "cough"})
        self.assertIn("fever", j["canonical_text"])
        self.assertEqual(j["results"]["rule"]["status"], "ok")
        self.assertEqual(j["results"]["rule"]["language"]["lang"], "hinglish")

    def test_emergency_is_flagged_independently_of_the_models(self):
        with self.patch_pipes():
            j = self.client(self.u[0]).post("/api/comparison/ask", json={"question": "seene mein dard aur saans nahi aa rahi"}).get_json()
        self.assertTrue(j["safety"]["emergency"])


def make_run(user_id, question="I have fever", dl_status="unavailable"):
    results = {k: {"status": "ok", "response": f"response from {k}", "name": cs.BOT_NAMES[k]} for k in ("rule", "ml")}
    results["dl"] = {"status": dl_status, "response": "" if dl_status != "ok" else "response from dl", "error": "no torch", "name": "DL"}
    return db.save_comparison_run(user_id, question, results, {"rule": "r1", "ml": "m1", "dl": "d1"})


GOOD = {"helpfulness": 4, "relevance": 5, "clarity": 3, "trustworthiness": 4, "safety": 5, "comment": "ok"}


class StudyTests(Base):
    def setUp(self):
        with db.get_db() as c:
            c.execute("DELETE FROM comparison_study_ratings")

    def rows(self):
        with db.get_db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM comparison_study_ratings ORDER BY architecture")]

    def test_valid_submission_is_linked_to_the_right_run_model_and_response(self):
        run = make_run(self.u[0])
        r = db.save_comparison_study("P-1", run, {"rule": GOOD, "ml": {**GOOD, "helpfulness": 2}}, {"rule": 2, "ml": 1})
        self.assertTrue(r["success"]); self.assertEqual((r["created"], r["updated"]), (2, 0))
        rows = {x["architecture"]: x for x in self.rows()}
        self.assertEqual(rows["rule"]["response_shown"], "response from rule")      # read from the stored run
        self.assertEqual(rows["ml"]["response_shown"], "response from ml")
        self.assertEqual(rows["ml"]["helpfulness"], 2); self.assertEqual(rows["rule"]["helpfulness"], 4)
        self.assertEqual(rows["rule"]["run_id"], run); self.assertEqual(rows["rule"]["model_version"], "r1")
        self.assertEqual(rows["rule"]["question_text"], "I have fever")
        self.assertEqual(rows["rule"]["display_position"], 2)

    def test_client_cannot_inject_question_or_response_text(self):
        run = make_run(self.u[0])
        db.save_comparison_study("P-1", run, {"rule": {**GOOD, "response_shown": "FORGED", "question_text": "FORGED"}})
        row = self.rows()[0]
        self.assertEqual(row["response_shown"], "response from rule")
        self.assertEqual(row["question_text"], "I have fever")

    def test_invalid_submissions_are_rejected_and_store_nothing(self):
        run = make_run(self.u[0])
        bad = [({"rule": {**GOOD, "clarity": 6}}, "between 1 and 5"), ({"rule": {**GOOD, "clarity": 0}}, "between 1 and 5"),
               ({"rule": {**GOOD, "clarity": "abc"}}, "integer"), ({"rule": {**GOOD, "clarity": 3.5}}, "whole number"),
               ({"rule": {**GOOD, "clarity": True}}, "integer"), ({"gpt4": GOOD}, "Unknown architecture"), ({}, "No ratings"),
               ("nope", "No ratings")]
        for ratings, msg in bad:
            r = db.save_comparison_study("P-1", run, ratings)
            self.assertFalse(r["success"], ratings); self.assertIn(msg, r["error"])
        self.assertFalse(db.save_comparison_study("P-1", "no-such-run", {"rule": GOOD})["success"])
        self.assertFalse(db.save_comparison_study("", run, {"rule": GOOD})["success"])
        self.assertEqual(self.rows(), [])

    def test_unavailable_model_cannot_be_rated(self):
        run = make_run(self.u[0])
        r = db.save_comparison_study("P-1", run, {"rule": GOOD, "dl": GOOD})
        self.assertTrue(r["success"]); self.assertEqual(r["skipped"], 1)
        self.assertEqual([x["architecture"] for x in self.rows()], ["rule"])

    def test_not_applicable_is_stored_as_null_and_excluded_from_means(self):
        run = make_run(self.u[0])
        na = {"helpfulness": "na", "relevance": None, "clarity": 4, "trustworthiness": "", "safety": "N/A"}
        self.assertTrue(db.save_comparison_study("P-1", run, {"rule": na})["success"])
        row = self.rows()[0]
        self.assertIsNone(row["helpfulness"]); self.assertEqual(row["clarity"], 4)
        s = db.get_comparison_study_summary()["per_architecture"]["rule"]
        self.assertEqual(s["n_rated"]["clarity"], 1); self.assertEqual(s["n_rated"]["helpfulness"], 0)
        self.assertIsNone(s["mean"]["helpfulness"]); self.assertEqual(s["not_applicable"]["helpfulness"], 1)

    def test_everything_not_applicable_is_rejected(self):
        run = make_run(self.u[0])
        r = db.save_comparison_study("P-1", run, {"rule": {c: "na" for c in db.STUDY_CRITERIA}})
        self.assertFalse(r["success"]); self.assertEqual(self.rows(), [])

    def test_resubmitting_updates_instead_of_duplicating(self):
        run = make_run(self.u[0])
        first = db.save_comparison_study("P-1", run, {"rule": GOOD, "ml": GOOD})
        again = db.save_comparison_study("P-1", run, {"rule": {**GOOD, "helpfulness": 1}, "ml": GOOD})
        self.assertEqual((first["created"], first["updated"]), (2, 0))
        self.assertEqual((again["created"], again["updated"]), (0, 2))
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual({x["architecture"]: x["helpfulness"] for x in self.rows()}["rule"], 1)
        db.save_comparison_study("P-2", run, {"rule": GOOD})
        self.assertEqual(len(self.rows()), 3)                                       # a second participant is separate

    def test_summary_withholds_averages_until_enough_participants(self):
        run = make_run(self.u[0])
        for i in range(4):
            db.save_comparison_study(f"P-{i}", run, {"rule": {**GOOD, "helpfulness": 5}})
        s = db.get_comparison_study_summary()
        self.assertEqual(s["participants"], 4); self.assertFalse(s["sufficient"])
        db.save_comparison_study("P-4", run, {"rule": {**GOOD, "helpfulness": 1}})
        s = db.get_comparison_study_summary()
        self.assertTrue(s["sufficient"]); self.assertEqual(s["participants"], 5)
        self.assertEqual(s["per_architecture"]["rule"]["mean"]["helpfulness"], 4.2)   # (5*4 + 1)/5, computed not hardcoded
        self.assertEqual(s["per_architecture"]["rule"]["distribution"]["helpfulness"]["5"], 4)
        self.assertIn("not verified medical correctness", s["note"].lower().replace("participant-perceived quality (opinions), ", ""))

    def test_empty_summary_has_no_invented_numbers(self):
        s = db.get_comparison_study_summary()
        self.assertEqual(s["completed_ratings"], 0); self.assertEqual(s["per_architecture"], {})

    def test_legacy_v1_columns_still_accepted(self):
        run = make_run(self.u[0])
        self.assertTrue(db.save_comparison_study("P-1", run, {"rule": {"correctness": 4, "completeness": 3}})["success"])
        self.assertEqual(self.rows()[0]["correctness"], 4)


class StudyApiTests(Base):
    def setUp(self):
        with db.get_db() as c:
            c.execute("DELETE FROM comparison_study_ratings")

    def submit(self, c, run, ratings=None, consent=True, **kw):
        return c.post("/api/comparison/study/submit", json={"run_id": run, "ratings": ratings or {"rule": GOOD}, "consent": consent, **kw})

    def test_login_and_consent_required(self):
        run = make_run(self.u[0])
        self.assertEqual(self.submit(self.client(), run).status_code, 401)
        r = self.submit(self.client(self.u[0]), run, consent=False)
        self.assertEqual(r.status_code, 400); self.assertIn("consent", r.get_json()["error"].lower())

    def test_submit_roundtrip_and_confirmation_payload(self):
        run = make_run(self.u[0]); c = self.client(self.u[0])
        j = self.submit(c, run, {"rule": GOOD, "ml": GOOD}).get_json()
        self.assertTrue(j["success"]); self.assertEqual(j["created"], 2)
        j2 = self.submit(c, run, {"rule": GOOD}).get_json()
        self.assertEqual((j2["created"], j2["updated"]), (0, 1))

    def test_invalid_rating_returns_400_with_message(self):
        run = make_run(self.u[0])
        r = self.submit(self.client(self.u[0]), run, {"rule": {**GOOD, "clarity": 9}})
        self.assertEqual(r.status_code, 400); self.assertIn("between 1 and 5", r.get_json()["error"])

    def test_participants_only_see_their_own_runs(self):
        mine, theirs = make_run(self.u[0], "my question"), make_run(self.u[1], "someone else's private question")
        c = self.client(self.u[0])
        runs = c.get("/api/comparison/study/runs").get_json()["runs"]
        self.assertIn(mine, [r["run_id"] for r in runs]); self.assertNotIn(theirs, [r["run_id"] for r in runs])
        self.assertEqual(c.get(f"/api/comparison/study/run/{theirs}").status_code, 404)
        self.assertEqual(self.client().get(f"/api/comparison/study/run/{mine}").status_code, 401)

    def test_run_detail_shows_actual_responses_and_marks_unavailable_as_not_ratable(self):
        run = make_run(self.u[0]); c = self.client(self.u[0])
        j = c.get(f"/api/comparison/study/run/{run}").get_json()["run"]
        self.assertEqual(j["question"], "I have fever")
        self.assertEqual(j["responses"]["rule"]["response"], "response from rule")
        self.assertTrue(j["responses"]["rule"]["ratable"]); self.assertFalse(j["responses"]["dl"]["ratable"])
        self.submit(c, run, {"rule": GOOD})
        again = c.get(f"/api/comparison/study/run/{run}").get_json()["run"]
        self.assertEqual(again["responses"]["rule"]["my_rating"]["helpfulness"], 4)     # prefill for editing
        self.assertIsNone(again["responses"]["ml"]["my_rating"])

    def test_participant_id_is_pseudonymous(self):
        run = make_run(self.u[0]); self.submit(self.client(self.u[0]), run)
        with db.get_db() as c:
            pid = c.execute("SELECT participant_id FROM comparison_study_ratings").fetchone()[0]
        self.assertTrue(pid.startswith("P-")); self.assertNotIn("a@example.com", pid); self.assertNotEqual(pid, f"P-{self.u[0]}")

    def test_summary_and_csv_export(self):
        run = make_run(self.u[0])
        self.submit(self.client(self.u[0]), run, {"rule": GOOD, "ml": {**GOOD, "helpfulness": "na"}})
        j = self.client(self.u[0]).get("/api/comparison/study/summary").get_json()["data"]
        self.assertEqual(j["completed_ratings"], 2); self.assertFalse(j["sufficient"])
        r = self.client(self.u[0]).get("/api/comparison/study/export.csv")
        self.assertEqual(r.status_code, 200); self.assertIn("text/csv", r.content_type)
        rows = list(csv.DictReader(io.StringIO(r.get_data(as_text=True))))
        self.assertEqual(len(rows), 2)
        self.assertEqual({x["architecture"] for x in rows}, {"rule", "ml"})
        for col in ("helpfulness", "trustworthiness", "safety", "participant_id", "model_version", "response_shown"):
            self.assertIn(col, rows[0])
        self.assertEqual([x for x in rows if x["architecture"] == "ml"][0]["helpfulness"], "")   # N/A exported as blank
        self.assertEqual(self.client().get("/api/comparison/study/export.csv").status_code, 401)


class MigrationTests(unittest.TestCase):
    def test_v1_table_is_upgraded_without_losing_rows(self):
        path = os.path.join(tempfile.mkdtemp(), "mig.db")
        con = sqlite3.connect(path)
        con.execute("""CREATE TABLE comparison_study_ratings (study_response_id TEXT PRIMARY KEY, participant_id TEXT NOT NULL, run_id TEXT NOT NULL,
            question_text TEXT NOT NULL, architecture TEXT NOT NULL, response_shown TEXT NOT NULL, display_position INTEGER, correctness INTEGER NOT NULL,
            relevance INTEGER NOT NULL, clarity INTEGER NOT NULL, completeness INTEGER NOT NULL, safety INTEGER NOT NULL, comment TEXT, model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(participant_id, run_id, architecture))""")
        con.execute("INSERT INTO comparison_study_ratings (study_response_id,participant_id,run_id,question_text,architecture,response_shown,correctness,relevance,clarity,completeness,safety,comment) VALUES ('x','P-1','r','q','rule','resp',4,5,3,4,5,'kept')")
        cur = con.cursor()
        db._migrate_study_ratings(cur)
        db._migrate_study_ratings(cur)                       # idempotent
        con.commit()
        cols = [r[1] for r in con.execute("PRAGMA table_info(comparison_study_ratings)")]
        self.assertIn("helpfulness", cols); self.assertIn("trustworthiness", cols)
        row = con.execute("SELECT correctness, relevance, comment, helpfulness FROM comparison_study_ratings").fetchone()
        self.assertEqual(row, (4, 5, "kept", None))
        self.assertIsNone(con.execute("SELECT 1 FROM sqlite_master WHERE name='comparison_study_ratings_v1'").fetchone())
        con.execute("UPDATE comparison_study_ratings SET relevance=NULL")           # nullable now (N/A support)


if __name__ == "__main__":
    unittest.main()
