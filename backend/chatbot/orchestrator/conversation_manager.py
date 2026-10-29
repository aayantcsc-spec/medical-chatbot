"""
conversation_manager.py - the ConversationManager used by Chat for all three MediChat chatbots.

(chat_manager.py in this folder is the legacy manager used only by legacy_app.py.)

Bots: rule (Rule-Based), ml (TF-IDF + SVM), dl (DistilBERT). Each one runs its REAL pipeline from
chatbot/health_qa/pipelines.py via comparison_service.run_one.

Order of handling for one message - identical for every bot, so differences come only from the bot:
    1. emergency check on the raw message      -> urgent guidance only (no questions first)
    2. small talk (greeting / thanks / bye ...) -> shared front-end reply, no model
    3. the selected bot, with the previous topic as context so follow-ups ("what should I do now?",
       "explain simpler") refer to the earlier answer
    4. the reply passes the response safety gate (chatbot/medical/safety.py)

State is a tiny JSON-serialisable dict stored per conversation: the last topic and a turn count.
"""
import time

from chatbot.health_qa import language, localized
from chatbot.medical import safety

BOTS = ("rule", "ml", "dl")
MAX_CHARS = 1000


def new_state():
    return {"topic": None, "turns": 0}


def clean(text):
    text = " ".join(str(text or "").split())
    if not text:
        raise ValueError("Please enter a health question.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Please keep the message under {MAX_CHARS} characters.")
    return text


class ConversationManager:
    def __init__(self, bot="rule", state=None):
        if bot not in BOTS:
            raise ValueError(f"Unknown chatbot '{bot}'. Choose from: {', '.join(BOTS)}")
        self.bot = bot
        self.state = {**new_state(), **(state or {})}

    def _reply(self, text, handled_by, start, safety_status="passed", result=None, lang="en"):
        return {"reply": text, "handled_by": handled_by, "bot": self.bot, "safety_status": safety_status,
                "response_time_ms": round((time.perf_counter() - start) * 1000, 3), "result": result,
                "language": lang, "state": dict(self.state)}

    def process(self, message):
        import comparison_service as cs
        start = time.perf_counter()
        text = clean(message)
        self.state["turns"] = int(self.state.get("turns") or 0) + 1
        analysis = language.analyse(text)
        lang = analysis["lang"]
        assessed = safety.assess_input(text)

        # 1. emergencies first - nothing may delay or dilute this
        if assessed["emergency"]:
            return self._reply(safety.emergency_text(assessed, text), "safety layer (emergency)", start,
                               "emergency_override", {"categories": assessed["categories"]}, lang)
        # 2. small talk
        if analysis["small_talk"]:
            return self._reply(localized.small_talk_reply(analysis["small_talk"], lang, seed=len(text)),
                               "language front-end (small talk, no model used)", start, "passed", None, lang)
        # 3. the selected bot, with the previous topic for follow-ups
        res = cs.run_one(self.bot, text, {"topic": self.state.get("topic")} if self.state.get("topic") else None)
        if res["status"] in ("unavailable", "error"):
            return self._reply(f"{res['name']} could not answer: {res.get('error')}", f"{self.bot} (failed)", start,
                               "not_applicable", res, lang)
        if res.get("intent") and res["intent"] not in ("out_of_scope", "follow_up_simplify", "follow_up_next_steps"):
            self.state["topic"] = res.get("reply_topic") or res["intent"]
        reply = res.get("response") or ""
        # 4. response safety gate
        status = "emergency_override" if res.get("safety_override") else "passed"
        if status == "passed":
            gate = safety.check_response(reply)
            if gate["status"] == "rejected":
                res = {**res, "withheld_response": reply, "safety_reasons": gate["reasons"]}
                reply, status = safety.SAFE_FALLBACK, "rejected"
        return self._reply(reply, self.bot, start, status, res, lang)
