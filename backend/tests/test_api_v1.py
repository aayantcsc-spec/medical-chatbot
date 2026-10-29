"""/api/v1: auth, CSRF, profile, chat (three chatbots) + history ownership, comparison, evaluation, errors, account deletion."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import database as db          # noqa: E402
from database import experiments as exp      # noqa: E402
import evaluation_service as ev              # noqa: E402


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._db = mock.patch.object(db, "DATABASE_PATH", os.path.join(self.tmp.name, "test.db"))
        self._db.start()
        exp._ready = False
        self._runs = mock.patch.object(ev, "RUN_DIR", os.path.join(self.tmp.name, "runs"))
        self._runs.start()
        from app import create_app
        from config import TestConfig
        self.app = create_app(TestConfig)
        self.c = self.app.test_client()

    def tearDown(self):
        self._runs.stop()
        self._db.stop()
        exp._ready = False
        self.tmp.cleanup()

    def token(self, client=None):
        return (client or self.c).get("/api/v1/auth/csrf").get_json()["data"]["csrf_token"]

    def send(self, method, url, json=None, client=None):
        client = client or self.c
        return getattr(client, method)(url, json=json, headers={"X-CSRF-Token": self.token(client)})

    def register(self, email="a@example.com", client=None, onboard=True):
        r = self.send("post", "/api/v1/auth/register", {"name": "Asha", "email": email, "password": "secret123"}, client)
        self.assertEqual(r.status_code, 201, r.get_json())
        if onboard:
            r = self.send("put", "/api/v1/profile", {"age_range": "18-29", "acknowledged": True}, client)
            self.assertEqual(r.status_code, 200, r.get_json())


class AuthTests(ApiTestCase):
    def test_register_login_logout_me(self):
        self.register(onboard=False)
        me = self.c.get("/api/v1/auth/me").get_json()["data"]["user"]
        self.assertEqual(me["email"], "a@example.com")
        self.assertFalse(me["onboarded"])
        self.send("post", "/api/v1/auth/logout")
        self.assertIsNone(self.c.get("/api/v1/auth/me").get_json()["data"]["user"])
        self.assertEqual(self.send("post", "/api/v1/auth/login", {"email": "A@example.com", "password": "secret123"}).status_code, 200)

    def test_password_is_hashed(self):
        self.register()
        with db.get_db() as conn:
            stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
        self.assertNotIn("secret123", stored)

    def test_duplicate_and_validation(self):
        self.register()
        r = self.send("post", "/api/v1/auth/register", {"name": "B", "email": "a@example.com", "password": "secret123"})
        self.assertEqual(r.status_code, 409)
        r = self.send("post", "/api/v1/auth/register", {"name": "B", "email": "b@example.com", "password": "short"})
        self.assertEqual(r.get_json()["error"]["field"], "password")

    def test_wrong_password(self):
        self.register()
        self.assertEqual(self.send("post", "/api/v1/auth/login", {"email": "a@example.com", "password": "wrong1234"}).status_code, 401)

    def test_csrf_required(self):
        r = self.c.post("/api/v1/auth/register", json={"name": "A", "email": "a@example.com", "password": "secret123"})
        self.assertEqual(r.get_json()["error"]["code"], "CSRF_FAILED")

    def test_protected_routes_require_login(self):
        for url in ("/api/v1/profile", "/api/v1/chats", "/api/v1/evaluations", "/api/v1/analytics/summary"):
            self.assertEqual(self.c.get(url).status_code, 401, url)


class ProfileTests(ApiTestCase):
    def test_acknowledgement_then_update_and_delete(self):
        self.register(onboard=False)
        self.assertEqual(self.send("put", "/api/v1/profile", {"age_range": "30-44"}).get_json()["error"]["code"], "ACKNOWLEDGEMENT_REQUIRED")
        r = self.send("put", "/api/v1/profile", {"height": "170 cm", "acknowledged": True})
        self.assertEqual(r.get_json()["data"]["profile"]["height"], "170 cm")
        self.assertTrue(self.send("delete", "/api/v1/profile").get_json()["data"]["deleted"])


class ChatTests(ApiTestCase):
    def test_options_list_exactly_three_chatbots(self):
        bots = self.c.get("/api/v1/chat/options").get_json()["data"]["bots"]
        self.assertEqual([b["key"] for b in bots], ["rule", "ml", "dl"])

    def test_each_chatbot_answers_with_its_own_pipeline(self):
        for bot in ("rule", "ml"):
            d = self.send("post", "/api/v1/chat", {"message": "What can cause fever and headache?", "bot": bot, "save": False}).get_json()["data"]
            self.assertEqual(d["handled_by"], bot)
            self.assertIn("Not a diagnosis", d["reply"])
            self.assertIsNotNone(d["details"]["inference_ms"])

    def test_emergency_first_for_every_bot(self):
        for bot in ("rule", "ml", "dl"):
            d = self.send("post", "/api/v1/chat", {"message": "I have chest pain and difficulty breathing.", "bot": bot, "save": False}).get_json()["data"]
            self.assertEqual(d["safety_status"], "emergency_override")
            self.assertIn("112", d["reply"])

    def test_follow_up_uses_previous_topic(self):
        self.register()
        r1 = self.send("post", "/api/v1/chat", {"message": "I have a headache", "bot": "rule"}).get_json()["data"]
        r2 = self.send("post", "/api/v1/chat", {"message": "explain in simple words", "bot": "rule",
                                                "conversation_id": r1["conversation_id"]}).get_json()["data"]
        self.assertIn("In simple words", r2["reply"])
        detail = self.c.get(f"/api/v1/chats/{r1['conversation_id']}").get_json()["data"]
        self.assertEqual(len(detail["messages"]), 4)

    def test_unsupported_question_is_declined(self):
        d = self.send("post", "/api/v1/chat", {"message": "What is the capital of France?", "bot": "rule", "save": False}).get_json()["data"]
        self.assertEqual(d["details"]["status"], "no_match")

    def test_history_isolated_between_users(self):
        self.register("a@example.com")
        cid = self.send("post", "/api/v1/chat", {"message": "I have a rash", "bot": "rule"}).get_json()["data"]["conversation_id"]
        other = self.app.test_client()
        self.register("b@example.com", other)
        self.assertEqual(other.get(f"/api/v1/chats/{cid}").status_code, 404)
        self.assertEqual(self.send("delete", f"/api/v1/chats/{cid}", client=other).status_code, 404)

    def test_validation(self):
        self.assertEqual(self.send("post", "/api/v1/chat", {"message": ""}).status_code, 400)
        self.assertEqual(self.send("post", "/api/v1/chat", {"message": "x" * 1001}).status_code, 400)
        self.assertEqual(self.send("post", "/api/v1/chat", {"message": "hi", "bot": "rag"}).status_code, 400)


class ComparisonTests(ApiTestCase):
    def test_same_question_to_three_chatbots(self):
        d = self.send("post", "/api/v1/comparison/ask", {"question": "How can I sleep better?"}).get_json()["data"]
        self.assertEqual(set(d["results"]), {"rule", "ml", "dl"})
        for k, r in d["results"].items():
            self.assertEqual(r["key"], k)
            if r["status"] not in ("unavailable", "error"):
                self.assertIsNotNone(r["inference_ms"], k)
        self.assertIn(d["overall_selection"]["headline"], ("Best Response for This Question", "No Clear Winner"))

    def test_empty_question_rejected(self):
        self.assertEqual(self.send("post", "/api/v1/comparison/ask", {"question": "  "}).status_code, 400)

    def test_saved_for_user_study_when_signed_in(self):
        self.register()
        d = self.send("post", "/api/v1/comparison/ask", {"question": "What is a balanced diet?"}).get_json()["data"]
        run = self.c.get(f"/api/v1/study/runs/{d['run_id']}").get_json()["data"]
        self.assertEqual(len(run["responses"]), 3)
        self.assertEqual([r["slot"] for r in run["responses"]], ["A", "B", "C"])


class EvaluationTests(ApiTestCase):
    def test_overview_requires_real_runs_then_reports_them(self):
        self.register()
        o = self.c.get("/api/v1/analytics/overview").get_json()["data"]
        self.assertTrue(o["evaluation_required"])
        self.assertEqual(o["overall"]["status"], "insufficient")
        self.assertIsNone(o["chatbots"][0]["correctness"]["held_out_accuracy"])
        st = ev.start_run("held_out_test", "custom", limit=12, wait=True, on_finish=exp.record_health_qa_run)
        self.assertEqual(ev.get_run(st["run_id"])["status"], "completed")
        o = self.c.get("/api/v1/analytics/overview").get_json()["data"]
        self.assertFalse(o["evaluation_required"])
        self.assertEqual(o["runs"]["held_out_test"]["n"], 12)
        self.assertEqual(o["overall"]["status"], "insufficient")          # safety run still missing -> no winner
        self.assertEqual(len(self.c.get("/api/v1/analytics/history").get_json()["data"]), 3)
        csv_text = self.c.get(f"/api/v1/evaluations/{st['run_id']}/export.csv").data.decode()
        self.assertEqual(len(csv_text.strip().splitlines()), 1 + 12 * 3)

    def test_start_validation(self):
        self.register()
        self.assertEqual(self.send("post", "/api/v1/evaluations", {"dataset": "nope"}).status_code, 400)
        self.assertEqual(self.c.get("/api/v1/evaluations/missing").status_code, 404)


class ErrorAndAccountTests(ApiTestCase):
    def test_errors_are_json_without_tracebacks(self):
        self.assertEqual(self.c.get("/api/v1/nope").status_code, 404)
        with mock.patch("chatbot.orchestrator.conversation_manager.ConversationManager.process", side_effect=KeyError("secret path")):
            r = self.send("post", "/api/v1/chat", {"message": "hello"})
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secret path", r.data.decode())

    def test_account_deletion_removes_personal_data(self):
        self.register()
        self.send("post", "/api/v1/chat", {"message": "I have a cough", "bot": "rule"})
        self.assertEqual(self.send("delete", "/api/v1/auth/account", {"confirm": "DELETE"}).status_code, 200)
        with db.get_db() as conn:
            for table in ("users", "health_profiles", "conversations", "chats"):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0, table)


if __name__ == "__main__":
    unittest.main()
