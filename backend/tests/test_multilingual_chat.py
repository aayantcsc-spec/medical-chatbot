"""
Language layer, multilingual safety and the Chat API.
Run:  python -m unittest discover -s tests -v      (or: python -m pytest tests -q)
These tests use only the rule-based and SVM pipelines (no torch needed).
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from database import database as db                                    # noqa: E402
from chatbot.health_qa import language, safety                         # noqa: E402
from chatbot.health_qa.pipelines import RuleBasedPipeline, SvmPipeline  # noqa: E402
import comparison_service as cs                                        # noqa: E402


class LanguageTests(unittest.TestCase):
    def test_detects_three_languages(self):
        self.assertEqual(language.detect_language("I have a fever and a cough")["lang"], "en")
        self.assertEqual(language.detect_language("Mujhe bukhar aur khansi ho rahi hai")["lang"], "hinglish")
        self.assertEqual(language.detect_language("मुझे बुखार है")["lang"], "hi")
        self.assertEqual(language.detect_language("Mujhe fever ho raha hai")["lang"], "hinglish")

    def test_plain_english_is_not_mistaken_for_hinglish(self):
        for q in ["Please tell me a good diet", "I have a rash and itchy skin", "Sir, I have a fever", "what is the period of validity"]:
            self.assertEqual(language.detect_language(q)["lang"], "en", q)

    def test_canonical_text_preserves_medical_meaning(self):
        cases = {
            "Mujhe bukhar aur khansi ho rahi hai, kya karu?": ["fever", "cough"],
            "Mere sir mein dard hai aur chakkar aa rahe hain.": ["headache", "dizziness"],
            "मेरे सिर में दर्द है और चक्कर आ रहे हैं": ["headache", "dizziness"],
            "pet mein lagatar dard rehta hai": ["persistent", "stomach pain"],
            "seene mein bahut tez dard hai": ["severe", "chest pain"],
            "Saans lene mein dikkat hai": ["difficulty breathing"],
        }
        for text, needles in cases.items():
            canon = language.canonicalise(text)
            for n in needles:
                self.assertIn(n, canon, f"{text!r} -> {canon!r}")

    def test_typos_and_spelling_variants(self):
        self.assertIn("fever", language.canonicalise("bukhaarr hai mujhe"))
        self.assertIn("headache", language.canonicalise("sar dard ho raha hai"))

    def test_multi_symptom_extraction(self):
        self.assertEqual(set(language.analyse("Mujhe bukhar aur khansi hai")["symptoms"]), {"fever", "cough"})
        self.assertEqual(set(language.analyse("I have a headache and feel dizzy")["symptoms"]), {"headache", "dizziness"})

    def test_small_talk_recognised_in_all_languages(self):
        kinds = {"Hi": "greeting", "Hello": "greeting", "Namaste": "greeting", "नमस्ते": "greeting", "How are you?": "how_are_you",
                 "kaise ho": "how_are_you", "Thank you": "thanks", "shukriya": "thanks", "धन्यवाद": "thanks", "Bye": "bye", "alvida": "bye"}
        for text, kind in kinds.items():
            self.assertEqual(language.small_talk(text), kind, text)

    def test_greeting_does_not_hide_a_health_question(self):
        for q in ["Hello, I have a fever", "Namaste mujhe bukhar hai"]:
            a = language.analyse(q)
            self.assertIsNone(a["small_talk"], q)
            self.assertIn("fever", a["canonical"])
            self.assertNotIn("namaste", a["canonical"])
            self.assertNotIn("hello", a["canonical"])

    def test_question_kinds(self):
        self.assertEqual(language.analyse("Which doctor should I consult for persistent stomach pain?")["question_kind"], "doctor")
        self.assertEqual(language.analyse("kis doctor ko dikhana chahiye pet dard ke liye")["question_kind"], "doctor")
        self.assertEqual(language.analyse("What is diabetes?")["question_kind"], "definition")
        self.assertEqual(language.analyse("I have a headache")["question_kind"], "symptom")


class SafetyTests(unittest.TestCase):
    EMERGENCIES = ["I have severe chest pain", "seene mein dard ho raha hai saans nahi aa rahi", "सीने में तेज दर्द और सांस लेने में तकलीफ",
                   "mujhe marne ka mann kar raha hai", "मुझे मरने का मन कर रहा है", "mere papa behosh ho gaye", "khoon nahi ruk raha",
                   "usne zeher kha liya", "bachche ko daura pada hai", "Mujhe saans lene mein dikkat hai", "खून रुक नहीं रहा है"]
    SAFE = ["mujhe bukhar hai", "mere sir mein dard hai", "मुझे बुखार है", "chakkar aa rahe hain", "pet mein dard hai",
            "What are the warning signs of a stroke?", "Which doctor treats thyroid problems?"]

    def test_emergencies_detected_in_english_hindi_hinglish(self):
        for q in self.EMERGENCIES:
            self.assertTrue(safety.assess(q)["emergency"], q)

    def test_ordinary_symptoms_are_not_flagged(self):
        for q in self.SAFE:
            self.assertFalse(safety.assess(q)["emergency"], q)

    def test_emergency_reply_is_localised_and_names_112_in_every_model(self):
        for pipe in (RuleBasedPipeline(), SvmPipeline()):
            for q, marker in (("I have severe chest pain", "112"), ("seene mein dard ho raha hai saans nahi aa rahi", "112"),
                              ("सीने में तेज दर्द और सांस लेने में तकलीफ", "112")):
                out = pipe.predict(q)
                self.assertTrue(out["safety_override"], (pipe.kind, q))
                self.assertIn(marker, out["response"])
        hinglish = RuleBasedPipeline().predict("seene mein dard ho raha hai saans nahi aa rahi")["response"]
        self.assertIn("Khatre ke sanket", hinglish)               # Hinglish heading, not English
        hindi = RuleBasedPipeline().predict("सीने में तेज दर्द और सांस लेने में तकलीफ")["response"]
        self.assertIn("खतरे के संकेत", hindi)

    def test_self_harm_reply_gives_helpline_not_a_routine_appointment(self):
        out = RuleBasedPipeline().predict("mujhe marne ka mann kar raha hai")["response"]
        self.assertIn("14416", out)
        self.assertNotIn("appointment", out.lower())

    def test_emergency_is_never_answered_with_a_routine_doctor_recommendation(self):
        out = RuleBasedPipeline().predict("Which doctor should I see? I have crushing chest pain and cannot breathe")
        self.assertTrue(out["safety_override"])
        self.assertIn("112", out["response"])


class PipelineLanguageTests(unittest.TestCase):
    def setUp(self):
        self.rule, self.svm = RuleBasedPipeline(), SvmPipeline()

    def test_same_meaning_in_three_languages_gives_same_topic_in_rule_model(self):
        topics = {self.rule.predict(q)["intent"] for q in ["I have fever", "Mujhe bukhar hai", "Mujhe fever ho raha hai", "मुझे बुखार है"]}
        self.assertEqual(topics, {"fever"})

    def test_reply_language_follows_question_language(self):
        en = self.rule.predict("I have a headache")["response"]
        hing = self.rule.predict("mere sir mein dard hai")["response"]
        hi = self.rule.predict("मेरे सिर में दर्द है")["response"]
        # concise replies have no section headings; the uncertainty line and footer are localised
        self.assertIn("These symptoms alone cannot identify the cause", en)
        self.assertIn("Sirf in symptoms se karan pata nahi chal sakta", hing)
        self.assertIn("केवल इन लक्षणों से कारण पता नहीं चल सकता", hi)
        self.assertIn("Not a diagnosis", en)

    def test_untranslated_topic_is_labelled_not_silently_english(self):
        out = self.rule.predict("sunn jhunjhuni hoti hai haath mein")
        if out["intent"] == "numbness_tingling":                  # topic has no Hindi/Hinglish text
            self.assertIn("English", out["response"])

    def test_greeting_handled_without_a_model(self):
        for pipe in (self.rule, self.svm):
            out = pipe.predict("Namaste")
            self.assertEqual(out["status"], "small_talk")
            self.assertIn("MediChat", out["response"])
            self.assertIsNone(out["confidence"])
            self.assertIn("no model", out["handled_by"])

    def test_greeting_reply_in_hinglish_matches_requested_style(self):
        self.assertIn("Namaste! Main MediChat hoon", self.rule.predict("Namaste")["response"])

    def test_multi_symptom_reply_mentions_both_and_does_not_diagnose(self):
        out = self.rule.predict("I have a headache and feel dizzy. What could be the reason?")["response"]
        self.assertIn("more than one symptom", out)
        self.assertIn("headache", out.lower()); self.assertIn("dizz", out.lower())
        low = out.lower()
        self.assertIn("cannot say what is behind them", low)          # explicit uncertainty
        for diagnostic in ("you have a ", "you are suffering", "you definitely", "this is caused by", "you have been diagnosed"):
            self.assertNotIn(diagnostic, low)

    def test_doctor_question_gets_specialty_not_a_diagnosis(self):
        out = self.rule.predict("Which doctor should I consult for persistent stomach pain?")["response"]
        self.assertIn("Gastroenterologist", out)
        self.assertIn("General Physician", out)
        self.assertIn("not a diagnosis", out)
        hing = self.rule.predict("kis doctor ko dikhana chahiye pet dard ke liye")["response"]
        self.assertIn("Gastroenterologist", hing)

    def test_out_of_domain_is_declined(self):
        out = self.rule.predict("What is the capital of France?")
        self.assertEqual(out["status"], "no_match")

    def test_unclear_symptom_gets_an_honest_limitation_not_a_question(self):
        out = self.rule.predict("mujhe kuch ajeeb sa lag raha hai")
        self.assertIn(out["status"], ("no_match", "ok"))
        if out["status"] == "no_match":
            self.assertIn("doctor", out["response"].lower())
            self.assertNotIn("?", out["response"])

    def test_qna_replies_never_ask_a_question_back(self):
        for q in ("I have a fever and headache. What should I do?", "I have a cough", "mujhe bukhar hai", "मुझे सिरदर्द है",
                  "Which doctor should I consult for frequent headaches?", "What is a balanced diet?", "I feel unwell"):
            for pipe in (self.rule, self.svm):
                self.assertNotIn("?", pipe.predict(q)["response"], (pipe.key, q))

    def test_followup_uses_context_topic(self):
        out = self.rule.predict("why?", context={"topic": "fever"})
        self.assertIn(out["status"], ("ok", "no_match"))
        self.assertTrue(out["response"])

    def test_result_has_language_metadata(self):
        out = self.rule.predict("Mujhe bukhar aur khansi ho rahi hai")
        self.assertEqual(out["language"]["lang"], "hinglish")
        self.assertIn("fever", out["canonical_text"])
        self.assertEqual(set(out["symptoms"]), {"fever", "cough"})


class ChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "chat.db")
        db.create_database()
        import legacy_app as A
        cls.A = A
        db.create_user("Test", "User", "chat@example.com", "Passw0rd!x")
        db.create_user("Other", "User", "other@example.com", "Passw0rd!x")
        cls.uid = db.get_user_by_email("chat@example.com")["id"]
        cls.other = db.get_user_by_email("other@example.com")["id"]

    def client(self, uid=None):
        c = self.A.app.test_client()
        if uid:
            with c.session_transaction() as s:
                s["user_id"], s["user_name"], s["user_email"] = uid, "T", "t@x.com"
        return c

    def ask(self, c, q, **extra):
        return c.post("/api/health-chat/ask", json={"question": q, **extra})

    def test_requires_login(self):
        r = self.ask(self.client(), "hi")
        self.assertEqual(r.status_code, 401)

    def test_english_hindi_hinglish_and_smalltalk_round_trip(self):
        c = self.client(self.uid)
        for q in ["What is diabetes?", "मुझे बुखार है", "Mujhe bukhar aur khansi ho rahi hai, kya karu?", "Namaste", "Thank you"]:
            r = self.ask(c, q)
            self.assertEqual(r.status_code, 200, q)
            j = r.get_json()
            self.assertTrue(j["success"]); self.assertTrue(j["reply"]); self.assertEqual(j["reply"], j["result"]["response"])

    def test_conversation_is_persisted_and_reopens(self):
        c = self.client(self.uid)
        first = self.ask(c, "I have a headache").get_json()
        cid = first["conversation_id"]
        second = self.ask(c, "Mujhe bukhar hai", conversation_id=cid).get_json()
        self.assertEqual(second["conversation_id"], cid)
        detail = c.get(f"/api/conversations/{cid}").get_json()
        msgs = detail["data"]["messages"]
        self.assertEqual([m["user_message"] for m in msgs], ["I have a headache", "Mujhe bukhar hai"])
        self.assertTrue(all(m["bot_response"] for m in msgs))

    def test_cannot_write_into_someone_elses_conversation(self):
        cid = self.ask(self.client(self.other), "hello there").get_json()["conversation_id"]
        r = self.ask(self.client(self.uid), "I have fever", conversation_id=cid)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.ask(self.client(self.uid), "I have fever", conversation_id="abc").status_code, 400)

    def test_empty_and_too_long_questions_rejected(self):
        c = self.client(self.uid)
        self.assertEqual(self.ask(c, "   ").status_code, 400)
        self.assertEqual(self.ask(c, "x" * 1500).status_code, 400)

    def test_emergency_in_hinglish_via_api(self):
        j = self.ask(self.client(self.uid), "seene mein dard ho raha hai saans nahi aa rahi").get_json()
        self.assertTrue(j["result"]["safety_override"])
        self.assertIn("112", j["reply"])

    def test_context_topic_is_returned_for_followups(self):
        c = self.client(self.uid)
        j = self.ask(c, "I have fever").get_json()
        self.assertEqual(j["next_context_topic"], "fever")
        j2 = self.ask(c, "what should I do next?", conversation_id=j["conversation_id"], context_topic=j["next_context_topic"]).get_json()
        self.assertTrue(j2["success"])

    def test_first_pipeline_unavailable_falls_back_and_is_reported(self):
        real = cs.run_one

        def fake(key, q, ctx=None):
            if key == cs.chat_routing_policy()["order"][0]:
                return {"key": key, "name": cs.BOT_NAMES[key], "status": "unavailable", "error": "model file missing", "response": ""}
            return real(key, q, ctx)

        with mock.patch.object(cs, "run_one", fake):
            j = self.ask(self.client(self.uid), "I have fever").get_json()
        self.assertTrue(j["success"])
        self.assertEqual(len(j["skipped"]), 1)
        self.assertEqual(j["skipped"][0]["reason"], "model file missing")
        self.assertNotEqual(j["answered_by"], j["skipped"][0]["key"])

    def test_all_pipelines_failing_returns_an_error_not_a_fake_answer(self):
        def dead(key, q, ctx=None):
            return {"key": key, "name": key, "status": "error", "error": "boom", "response": ""}
        with mock.patch.object(cs, "run_one", dead):
            r = self.ask(self.client(self.uid), "I have fever")
        self.assertEqual(r.status_code, 500)
        self.assertFalse(r.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
