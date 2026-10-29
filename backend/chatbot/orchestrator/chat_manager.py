"""
MediChat Conversation Manager

Project:
Comparative Analysis of Health Chatbots Based on Framework and Architecture

Architectures:
1. Rule-Based
2. Machine Learning
3. Deep Learning
4. RAG + LLM
5. Hybrid

Normal Chat:
    User -> MediChat -> Hybrid
                    -> Rule + ML + DL
                    -> one final response

Comparison:
    User -> Comparison
          -> Rule
          -> ML
          -> DL
          -> RAG + LLM
          -> Hybrid

Important design rule:

    Comparison architecture requests MUST remain isolated.

Normal Chat:
    Hybrid = Rule + ML + DL

Comparison:
    Rule = Rule only
    ML   = ML only
    DL   = DL only
    RAG  = RAG only
    Hybrid = Rule + ML + DL

RAG is kept as a separate comparison architecture.
"""

import os
import re
import time
import traceback

from chatbot.personalization.onboarding_context import (
    build_context,
    rule_keywords,
    personalised_note,
)


# ============================================================
# PROJECT PATH
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

if PROJECT_ROOT not in os.sys.path:
    os.sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# DATASET IMPORTS
# ============================================================

try:
    from chatbot.data.dataset_loader import (
        search_symptom2disease,
        search_disease_symptoms,
        search_precautions,
        search_medical_qa,
    )
except Exception:
    search_symptom2disease = None
    search_disease_symptoms = None
    search_precautions = None
    search_medical_qa = None


# ============================================================
# MEDICAL ROUTER
# ============================================================

try:
    from chatbot.medical.medical_router import MedicalRouter
except Exception:
    MedicalRouter = None


# ============================================================
# BOT REGISTRY
# ============================================================

try:
    from chatbot.orchestrator.bot_registry import get_bot_response
except Exception:
    get_bot_response = None


# ============================================================
# CONVERSATION MANAGER
# ============================================================

class ConversationManager:

    VALID_BOT_TYPES = {
        "rule",
        "ml",
        "dl",
        "rag",
        "hybrid",
    }

    BOT_ALIASES = {
        "auto": "hybrid",
        "default": "hybrid",
        "chat": "hybrid",
        "normal": "hybrid",
        "normal_chat": "hybrid",
        "conversation": "hybrid",

        "rule_based": "rule",
        "rule-based": "rule",
        "rule based": "rule",
        "rules": "rule",

        "machine_learning": "ml",
        "machine-learning": "ml",
        "machine learning": "ml",

        "deep_learning": "dl",
        "deep-learning": "dl",
        "deep learning": "dl",

        "rag_llm": "rag",
        "rag+llm": "rag",
        "rag + llm": "rag",
        "rag-based": "rag",
        "rag based": "rag",
    }

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self, user_profile=None):

        self.context = {
            "symptoms": [],
            "duration": None,
            "temperature": None,
            "severity": None,
            "progression": None,
            "other_symptoms": [],
            "active": False,
            "asked_other_symptoms": False,
            "follow_up_turns": 0,
            "last_topic": None,
            "last_intent": None,
            "last_response": None,
        }

        self.conversation_history = []

        self.user_profile = user_profile or {}

        self.onboarding_context = build_context(
            self.user_profile
        )

        self._rule_hint = ""

        self.medical_router = None

        if MedicalRouter is not None:
            try:
                self.medical_router = MedicalRouter()
            except Exception:
                self.medical_router = None

    # ========================================================
    # BASIC HELPERS
    # ========================================================

    def normalize(self, text):

        if text is None:
            return ""

        text = str(text)

        text = text.replace("\n", " ")
        text = text.replace("\r", " ")

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip().lower()

    # --------------------------------------------------------

    def correct_common_typos(self, text):

        if not text:
            return text

        replacements = {
            r"\bfeaver\b": "fever",
            r"\btemprature\b": "temperature",
            r"\bhead ache\b": "headache",
            r"\bheadake\b": "headache",
            r"\bstomack\b": "stomach",
            r"\bvomitting\b": "vomiting",
            r"\bdiarhea\b": "diarrhea",
            r"\bdiarrhoea\b": "diarrhea",
            r"\bcoughh\b": "cough",
            r"\bthroath\b": "throat",
            r"\bnauseus\b": "nauseous",
            r"\bnaseous\b": "nauseous",
            r"\bbreathless\b": "breathlessness",
        }

        result = text

        for pattern, replacement in replacements.items():

            result = re.sub(
                pattern,
                replacement,
                result,
                flags=re.IGNORECASE,
            )

        return result

    # --------------------------------------------------------

    def clean_text(self, text):

        if text is None:
            return ""

        text = str(text).strip()

        if not text:
            return ""

        return self.correct_common_typos(text)

    # ========================================================
    # BOT TYPE NORMALIZATION
    # ========================================================

    def normalize_bot_type(self, bot_type):

        if bot_type is None:
            return "hybrid"

        value = str(bot_type).strip().lower()

        if not value:
            return "hybrid"

        if value in self.VALID_BOT_TYPES:
            return value

        if value in self.BOT_ALIASES:
            return self.BOT_ALIASES[value]

        return "hybrid"

    # ========================================================
    # USER PROFILE
    # ========================================================

    def set_user_profile(self, profile):
        """
        Save the user's onboarding profile for this chat session.

        BUG FIXED: db.get_user_profile() returns a sqlite3.Row, and the
        old code only accepted a dict, so the profile was never stored
        and the chatbot never saw the onboarding answers.
        """

        if profile is None:

            self.user_profile = {}
            self.onboarding_context = build_context(None)
            return

        if isinstance(profile, dict):

            data = profile

        else:

            try:
                data = dict(profile)
            except Exception:
                return

        self.user_profile = data
        self.onboarding_context = build_context(data)

    # --------------------------------------------------------

    def get_profile_value(self, key, default=None):

        if not isinstance(self.user_profile, dict):
            return default

        value = self.user_profile.get(key)

        if value is None:
            return default

        return value

    # --------------------------------------------------------

    def personalization(self):

        age = self.get_profile_value("age")

        if age:
            return (
                f"Considering your provided age information ({age}), "
            )

        return ""

    # ========================================================
    # GREETING / CONVERSATIONAL RESPONSES
    # ========================================================

    def greeting_response(self, message):

        text = self.normalize(message)

        greetings = {
            "hi",
            "hello",
            "hey",
            "hii",
            "hiii",
            "namaste",
            "good morning",
            "good afternoon",
            "good evening",
        }

        if text in greetings:

            return (
                "Hello! I’m MediChat, your AI health assistant. "
                "You can describe a health question or symptom, and "
                "I can provide general information and guidance. "
                "For the project comparison, MediChat can also evaluate "
                "different AI architectures."
            )

        return None

    # --------------------------------------------------------

    def goodbye_response(self, message):

        text = self.normalize(message)

        goodbye_words = {
            "bye",
            "goodbye",
            "see you",
            "see you later",
            "take care",
        }

        if text in goodbye_words:

            return (
                "Take care. If you have another health-related question, "
                "you can come back to MediChat anytime."
            )

        return None

    # --------------------------------------------------------

    def thanks_response(self, message):

        text = self.normalize(message)

        thank_words = {
            "thanks",
            "thank you",
            "thankyou",
            "thx",
            "thanks a lot",
        }

        if text in thank_words:

            return (
                "You're welcome. I'm here to help with general "
                "health information whenever you need it."
            )

        return None

    # ========================================================
    # SYMPTOM DETECTION
    # ========================================================

    def symptom_words(self):

        return [
            "fever",
            "cough",
            "cold",
            "headache",
            "migraine",
            "dizziness",
            "nausea",
            "vomiting",
            "vomit",
            "diarrhea",
            "constipation",
            "stomach pain",
            "abdominal pain",
            "chest pain",
            "back pain",
            "neck pain",
            "joint pain",
            "body pain",
            "sore throat",
            "throat pain",
            "runny nose",
            "blocked nose",
            "fatigue",
            "weakness",
            "tiredness",
            "rash",
            "itching",
            "skin irritation",
            "shortness of breath",
            "breathlessness",
            "burning urination",
            "painful urination",
            "frequent urination",
            "blood in urine",
            "swelling",
            "pain",
            "chills",
        ]

    # --------------------------------------------------------

    def extract_symptoms(self, message):

        text = self.normalize(message)

        found = []

        for symptom in self.symptom_words():

            if symptom in text:
                found.append(symptom)

        result = []

        for symptom in found:

            if symptom not in result:
                result.append(symptom)

        return result

    # --------------------------------------------------------

    def is_symptom_query(self, message):

        return bool(
            self.extract_symptoms(message)
        )

    # ========================================================
    # CONTEXT EXTRACTION
    # ========================================================

    def extract_duration(self, message):

        text = self.normalize(message)

        patterns = [
            r"\bfor\s+(\d+)\s*(day|days|week|weeks|month|months|hour|hours)\b",
            r"\b(\d+)\s*(day|days|week|weeks|month|months|hour|hours)\s*(ago|since)?\b",
            r"\b(a|an|one|two|three|four|five|few)\s+(day|days|week|weeks|month|months)\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
            )

            if match:

                number = match.group(1)
                unit = match.group(2)

                return f"{number} {unit}"

        if "since yesterday" in text:
            return "since yesterday"

        if "since today" in text:
            return "since today"

        if "since last night" in text:
            return "since last night"

        if "since this morning" in text:
            return "since this morning"

        if "from yesterday" in text:
            return "from yesterday"

        if "from today" in text:
            return "from today"

        return None

    # --------------------------------------------------------

    def extract_temperature(self, message):

        text = self.normalize(message)

        patterns = [
            r"(\d+(?:\.\d+)?)\s*°?\s*f\b",
            r"(\d+(?:\.\d+)?)\s*°?\s*c\b",
            r"temperature\s*(?:is|of)?\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
            )

            if match:
                return match.group(1)

        return None

    # --------------------------------------------------------

    def extract_progression(self, message):

        text = self.normalize(message)

        if any(
            phrase in text
            for phrase in [
                "getting worse",
                "worse",
                "increasing",
                "increased",
                "severe now",
            ]
        ):
            return "worsening"

        if any(
            phrase in text
            for phrase in [
                "getting better",
                "better",
                "improving",
                "improved",
            ]
        ):
            return "improving"

        return None

    # --------------------------------------------------------

    def update_context(self, message):

        symptoms = self.extract_symptoms(message)

        if symptoms:

            for symptom in symptoms:

                if symptom not in self.context["symptoms"]:
                    self.context["symptoms"].append(symptom)

            self.context["active"] = True

            # The newest symptom remains the current topic.
            # The complete symptom list is preserved separately.
            self.context["last_topic"] = symptoms[-1]

        duration = self.extract_duration(message)

        if duration:
            self.context["duration"] = duration

        temperature = self.extract_temperature(message)

        if temperature:
            self.context["temperature"] = temperature

        progression = self.extract_progression(message)

        if progression:
            self.context["progression"] = progression

        normalized = self.normalize(message)

        if "severe" in normalized:
            self.context["severity"] = "severe"

        elif "mild" in normalized:
            self.context["severity"] = "mild"

        elif "moderate" in normalized:
            self.context["severity"] = "moderate"

    # ========================================================
    # CURRENT TOPIC
    # ========================================================

    def get_current_topic(self):

        symptoms = self.context.get(
            "symptoms",
            [],
        )

        if not symptoms:
            return None

        last_topic = self.context.get(
            "last_topic"
        )

        if last_topic:
            return last_topic

        return symptoms[-1]

    # --------------------------------------------------------

    def topic_display_name(self, topic):

        names = {
            "stomach pain": "stomach pain",
            "abdominal pain": "abdominal pain",
            "chest pain": "chest pain",
            "back pain": "back pain",
            "neck pain": "neck pain",
            "joint pain": "joint pain",
            "body pain": "body pain",
            "sore throat": "sore throat",
            "throat pain": "throat pain",
            "runny nose": "runny nose",
            "blocked nose": "blocked nose",
            "shortness of breath": "shortness of breath",
            "burning urination": "burning urination",
            "painful urination": "painful urination",
            "frequent urination": "frequent urination",
            "blood in urine": "blood in urine",
        }

        return names.get(
            topic,
            topic or "your symptoms",
        )

    # ========================================================
    # FOLLOW-UP DETECTION
    # ========================================================

    def is_follow_up(self, message):

        text = self.normalize(message)

        if not self.context.get("active"):
            return False

        # ----------------------------------------------------
        # Explicit follow-up phrases
        # ----------------------------------------------------

        follow_up_phrases = [
            "what should i do",
            "what can i do",
            "what do i do",
            "how can i treat",
            "how do i treat",
            "what treatment",
            "what about this",
            "is it serious",
            "should i worry",
            "how long",
            "how long does it last",
            "how long will it last",
            "what causes it",
            "why is this happening",
            "can i take medicine",
            "what medicine",
            "what should i take",
            "can i take",
            "anything i can do",
            "home remedy",
            "home remedies",
            "what next",
            "then what",
            "what should i drink",
            "what can i drink",
            "what should i eat",
            "what can i eat",
            "can i rest",
            "should i rest",
        ]

        if any(
            phrase in text
            for phrase in follow_up_phrases
        ):
            return True

        # ----------------------------------------------------
        # Conversation continuation phrases
        #
        # Examples:
        # "Since yesterday and I also have cough"
        # "I also have headache"
        # "I am also feeling dizzy"
        # ----------------------------------------------------

        continuation_phrases = [
            "also have",
            "also having",
            "i also have",
            "i also feel",
            "i am also having",
            "and i have",
            "and i am having",
            "along with",
            "as well as",
            "since yesterday",
            "since today",
            "since last night",
            "since this morning",
            "for the past",
            "for about",
            "from yesterday",
            "from today",
        ]

        if any(
            phrase in text
            for phrase in continuation_phrases
        ):
            return True

        # ----------------------------------------------------
        # Short duration answers such as "since 2 days",
        # "for 3 days", "2 weeks" after a symptom was described.
        # ----------------------------------------------------

        if (
            len(text.split()) <= 8
            and self.extract_duration(message)
        ):
            return True

        # ----------------------------------------------------
        # If an existing conversation is active and the new
        # message contains a symptom, treat it as a possible
        # continuation instead of starting from zero.
        # ----------------------------------------------------

        current_symptoms = self.extract_symptoms(message)

        if current_symptoms and self.context.get("symptoms"):

            return True

        # ----------------------------------------------------
        # Short contextual follow-ups
        # ----------------------------------------------------

        short_followups = {
            "why",
            "how",
            "what now",
            "and now",
            "then",
            "really",
            "is it serious",
            "should i worry",
        }

        if text in short_followups:
            return True

        # ----------------------------------------------------
        # Pronoun-based contextual questions
        # ----------------------------------------------------

        words = text.split()

        if len(words) <= 5:

            contextual_words = {
                "it",
                "this",
                "that",
                "now",
                "then",
            }

            if any(
                word in words
                for word in contextual_words
            ):
                return True

        return False

    # ========================================================
    # NEW QUESTION DETECTION
    # ========================================================

    def is_new_question(self, message):

        text = self.normalize(message)

        if not text:
            return False

        new_question_patterns = [
            "another question",
            "different question",
            "also tell me",
            "what is diabetes",
            "what is hypertension",
            "what is pcos",
            "what is migraine",
            "what is asthma",
            "what is pneumonia",
        ]

        return any(
            phrase in text
            for phrase in new_question_patterns
        )

    # ========================================================
    # TOPIC-SPECIFIC SELF CARE
    # ========================================================

    def topic_self_care_response(self, topic):

        if not topic:
            return None

        # ----------------------------------------------------
        # Fever
        # ----------------------------------------------------

        if topic == "fever":

            temperature = self.context.get(
                "temperature"
            )

            temperature_text = ""

            if temperature:
                temperature_text = (
                    f" You mentioned a temperature of about "
                    f"{temperature}; continue monitoring it."
                )

            return (
                "For a fever, you can generally rest, drink plenty "
                "of fluids, wear comfortable clothing, and monitor "
                "your temperature. Light foods are fine if you feel "
                "like eating."
                + temperature_text
                + " If the fever is very high, persistent, worsening, "
                "or accompanied by serious symptoms, seek medical care."
            )

        # ----------------------------------------------------
        # Headache
        # ----------------------------------------------------

        if topic == "headache":

            return (
                "For a headache, try resting in a quiet environment, "
                "drinking enough water, getting adequate sleep, and "
                "avoiding anything that clearly makes the headache worse. "
                "If the headache is sudden and extremely severe, follows "
                "an injury, or occurs with serious symptoms such as "
                "weakness, confusion, fainting, or difficulty speaking, "
                "seek urgent medical attention."
            )

        # ----------------------------------------------------
        # Cough
        # ----------------------------------------------------

        if topic == "cough":

            return (
                "For a cough, rest and stay well hydrated. Warm fluids "
                "may help soothe an irritated throat. Avoid smoke and "
                "other irritants. If you have difficulty breathing, "
                "cough up blood, develop severe chest pain, or the cough "
                "persists or worsens, seek medical advice."
            )

        # ----------------------------------------------------
        # Cold
        # ----------------------------------------------------

        if topic == "cold":

            return (
                "For common cold symptoms, rest, drink enough fluids, "
                "and eat normally as tolerated. Warm fluids can be "
                "comforting, and avoiding smoke may help. If symptoms "
                "become severe, last unusually long, or you develop "
                "difficulty breathing, seek medical advice."
            )

        # ----------------------------------------------------
        # Nausea / vomiting
        # ----------------------------------------------------

        if topic in {
            "nausea",
            "vomiting",
            "vomit",
        }:

            return (
                "If you feel nauseous or are vomiting, take small sips "
                "of water or an oral rehydration drink if tolerated. "
                "Try small, light meals once you can keep fluids down. "
                "Seek medical care if vomiting is persistent, you cannot "
                "keep fluids down, you have signs of dehydration, severe "
                "pain, or blood in the vomit."
            )

        # ----------------------------------------------------
        # Diarrhea
        # ----------------------------------------------------

        if topic == "diarrhea":

            return (
                "For diarrhea, focus on replacing fluids and electrolytes. "
                "Drink water or an oral rehydration solution and eat light "
                "foods if tolerated. Seek medical advice if there is blood "
                "in the stool, severe abdominal pain, significant "
                "dehydration, or persistent or worsening symptoms."
            )

        # ----------------------------------------------------
        # Sore throat
        # ----------------------------------------------------

        if topic in {
            "sore throat",
            "throat pain",
        }:

            return (
                "For a sore throat, drink enough fluids, rest, and consider "
                "warm liquids if they feel soothing. Avoid smoking and "
                "other throat irritants. If you have difficulty breathing "
                "or swallowing, severe swelling, or worsening symptoms, "
                "seek medical attention."
            )

        # ----------------------------------------------------
        # Dizziness
        # ----------------------------------------------------

        if topic == "dizziness":

            return (
                "If you feel dizzy, sit or lie down somewhere safe and "
                "avoid driving or climbing until the feeling passes. "
                "Drink fluids if dehydration may be contributing. If the "
                "dizziness is sudden, severe, recurrent, or occurs with "
                "fainting, chest pain, severe headache, weakness, or "
                "difficulty speaking, seek urgent medical care."
            )

        # ----------------------------------------------------
        # Fatigue / weakness
        # ----------------------------------------------------

        if topic in {
            "fatigue",
            "weakness",
            "tiredness",
        }:

            return (
                "For tiredness or weakness, make sure you are getting "
                "enough rest, fluids, and regular nutritious meals. "
                "If the problem is persistent, severe, or accompanied "
                "by other concerning symptoms, consider speaking with "
                "a healthcare professional."
            )

        # ----------------------------------------------------
        # Rash / itching
        # ----------------------------------------------------

        if topic in {
            "rash",
            "itching",
            "skin irritation",
        }:

            return (
                "For a mild rash or itching, avoid known irritants, "
                "keep the skin clean, and try not to scratch the area. "
                "If there is facial or throat swelling, difficulty "
                "breathing, widespread blistering, or rapid worsening, "
                "seek urgent medical attention."
            )

        # ----------------------------------------------------
        # Stomach pain
        # ----------------------------------------------------

        if topic in {
            "stomach pain",
            "abdominal pain",
        }:

            return (
                "For mild stomach discomfort, rest, drink fluids, and "
                "choose light foods if you feel like eating. Avoid foods "
                "that clearly worsen the discomfort. Severe or worsening "
                "pain, repeated vomiting, blood in vomit or stool, fainting, "
                "or a rigid or very swollen abdomen should be assessed "
                "urgently."
            )

        # ----------------------------------------------------
        # Body / joint / back / neck pain
        # ----------------------------------------------------

        if topic in {
            "body pain",
            "joint pain",
            "back pain",
            "neck pain",
        }:

            return (
                f"For {self.topic_display_name(topic)}, gentle rest, "
                "adequate fluids, and avoiding activities that clearly "
                "worsen the pain may help. If the pain is severe, follows "
                "an injury, keeps getting worse, or occurs with other "
                "concerning symptoms, seek medical advice."
            )

        # ----------------------------------------------------
        # Urinary symptoms
        # ----------------------------------------------------

        if topic in {
            "burning urination",
            "painful urination",
            "frequent urination",
            "blood in urine",
        }:

            return (
                "Urinary symptoms can have several causes. Stay hydrated "
                "unless a healthcare professional has told you to limit "
                "fluids, and consider getting medical advice rather than "
                "self-treating with antibiotics. Blood in the urine, fever "
                "with urinary symptoms, severe pain, vomiting, or worsening "
                "symptoms should be medically assessed."
            )

        # ----------------------------------------------------
        # Breathlessness
        # ----------------------------------------------------

        if topic in {
            "shortness of breath",
            "breathlessness",
        }:

            return (
                "Shortness of breath should be taken seriously. Sit upright "
                "and avoid strenuous activity. If breathing difficulty is "
                "severe, sudden, worsening, or occurs with chest pain, "
                "blue lips, fainting, or confusion, seek emergency medical "
                "attention immediately."
            )

        return None

    # ========================================================
    # COMBINED SYMPTOM RESPONSE
    # ========================================================

    def combined_symptom_response(self, message):

        symptoms = self.context.get(
            "symptoms",
            []
        )

        if not symptoms:
            return None

        # Only use combined response when two or more symptoms
        # are active in the current conversation.
        if len(symptoms) < 2:
            return None

        text = self.normalize(message)

        # ----------------------------------------------------
        # Determine whether this is a continuation.
        # ----------------------------------------------------

        continuation_indicators = [
            "also",
            "and i",
            "along with",
            "as well as",
            "since",
            "from",
            "for the past",
            "for about",
            "now",
        ]

        is_continuation = any(
            phrase in text
            for phrase in continuation_indicators
        )

        if not is_continuation:
            return None

        # ----------------------------------------------------
        # Format all symptoms.
        # ----------------------------------------------------

        symptom_names = [
            self.topic_display_name(symptom)
            for symptom in symptoms
        ]

        if len(symptom_names) == 2:

            symptom_text = (
                f"{symptom_names[0]} and "
                f"{symptom_names[1]}"
            )

        else:

            symptom_text = (
                ", ".join(symptom_names[:-1])
                + ", and "
                + symptom_names[-1]
            )

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        duration = self.context.get(
            "duration"
        )

        duration_text = ""

        if duration:

            # Natural wording for different duration values.
            if duration.startswith("since "):
                duration_text = (
                    f" You mentioned that these symptoms "
                    f"started {duration}."
                )
            elif duration.startswith("from "):
                duration_text = (
                    f" You mentioned that these symptoms "
                    f"started {duration}."
                )
            else:
                duration_text = (
                    f" You mentioned that you have had "
                    f"these symptoms for {duration}."
                )

        # ----------------------------------------------------
        # Temperature
        # ----------------------------------------------------

        temperature = self.context.get(
            "temperature"
        )

        temperature_text = ""

        if temperature:

            temperature_text = (
                f" You also mentioned a temperature of "
                f"about {temperature}; continue monitoring it."
            )

        # ----------------------------------------------------
        # Severity / progression
        # ----------------------------------------------------

        severity = self.context.get(
            "severity"
        )

        progression = self.context.get(
            "progression"
        )

        condition_text = ""

        if severity == "severe":

            condition_text += (
                " You described the symptoms as severe, so "
                "medical assessment is especially important."
            )

        if progression == "worsening":

            condition_text += (
                " You also mentioned that the symptoms are "
                "getting worse."
            )

        # ----------------------------------------------------
        # Final combined response
        # ----------------------------------------------------

        return (
            f"I understand. You are experiencing "
            f"{symptom_text}.{duration_text}"
            f"{temperature_text}"
            f"{condition_text}\n\n"

            "These symptoms can occur together for several "
            "different reasons, and the combination alone "
            "does not confirm a particular disease.\n\n"

            "For now, rest, stay hydrated, and monitor your "
            "temperature and how your symptoms change. "

            "If you develop difficulty breathing, severe chest "
            "pain, confusion, fainting, severe weakness, "
            "persistent vomiting, or rapidly worsening symptoms, "
            "seek urgent medical attention.\n\n"

            "If you can, tell me your temperature and whether "
            "you have any other symptoms such as sore throat, "
            "body aches, chills, or breathing difficulty."
        )

    # ========================================================
    # CONTEXTUAL RESPONSE
    # ========================================================

    def contextual_response(self, message):

        symptoms = self.context.get(
            "symptoms",
            [],
        )

        if not symptoms:
            return None

        text = self.normalize(message)

        topic = self.get_current_topic()

        topic_name = self.topic_display_name(topic)

        # ----------------------------------------------------
        # DURATION ANSWER ("since 2 days")
        # ----------------------------------------------------

        duration = self.extract_duration(message)

        if duration and len(text.split()) <= 8:

            match = re.match(
                r"(\d+)\s+(day|days|week|weeks|month|months|hour|hours)",
                duration,
            )

            long_lasting = False

            if match:

                number = int(match.group(1))
                unit = match.group(2)

                if unit.startswith(("week", "month")):
                    long_lasting = True

                elif unit.startswith("day") and number >= 3:
                    long_lasting = True

            if long_lasting:

                advice = (
                    "Since this has lasted several days, it would "
                    "be a good idea to see a doctor soon, "
                    "especially if it is not improving."
                )

            else:

                advice = (
                    "Many mild illnesses improve within a few days. "
                    "Rest, drink plenty of fluids and watch how you "
                    "feel. See a doctor if it lasts more than 3 days "
                    "or keeps getting worse."
                )

            return (
                f"Thank you for telling me. You mentioned "
                f"{topic_name} for {duration}. {advice} Please get "
                "urgent medical help for trouble breathing, chest "
                "pain, confusion, a stiff neck or a severe headache. "
                "This is general information, not a diagnosis."
            )

        # ----------------------------------------------------
        # WHAT CAN / SHOULD I DO?
        # ----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "what should i do",
                "what can i do",
                "what do i do",
                "anything i can do",
                "home remedy",
                "home remedies",
                "what next",
                "then what",
            ]
        ):

            specific = self.topic_self_care_response(
                topic
            )

            if specific:
                return specific

            symptom_text = ", ".join(symptoms)

            return (
                f"For symptoms such as {symptom_text}, general "
                "supportive steps may include resting, drinking "
                "enough fluids, eating light foods if tolerated, "
                "and monitoring how the symptoms change. The "
                "appropriate treatment depends on the underlying "
                "cause. If symptoms are severe, persistent, rapidly "
                "worsening, or concerning, seek medical care."
            )

        # ----------------------------------------------------
        # DRINK
        # ----------------------------------------------------

        if (
            "what should i drink" in text
            or "what can i drink" in text
            or "what to drink" in text
        ):

            if topic == "fever":

                return (
                    "For fever, focus on fluids such as water, "
                    "oral rehydration solution if needed, and "
                    "other non-alcoholic fluids that you tolerate. "
                    "Small, frequent amounts can be useful if you "
                    "do not feel like drinking much at once."
                )

            if topic in {
                "vomiting",
                "vomit",
                "diarrhea",
            }:

                return (
                    "For these symptoms, hydration is especially "
                    "important. Try small, frequent sips of water "
                    "or an oral rehydration solution if tolerated."
                )

            return (
                f"For {topic_name}, water and other suitable "
                "non-alcoholic fluids can generally help maintain "
                "hydration. If you have been advised to restrict "
                "fluids for a medical reason, follow that advice."
            )

        # ----------------------------------------------------
        # FOOD
        # ----------------------------------------------------

        if (
            "what should i eat" in text
            or "what can i eat" in text
            or "what to eat" in text
        ):

            if topic in {
                "fever",
                "cold",
                "cough",
                "sore throat",
                "throat pain",
            }:

                return (
                    "If you have an appetite, choose light, "
                    "easy-to-tolerate meals and continue drinking "
                    "enough fluids. You do not need to force a large "
                    "meal when you are unwell."
                )

            if topic in {
                "vomiting",
                "vomit",
                "nausea",
                "diarrhea",
            }:

                return (
                    "Once you can tolerate food, try small portions "
                    "of simple, light foods. Focus on fluids first "
                    "if you have been vomiting or have diarrhea."
                )

            return (
                f"For {topic_name}, choose balanced foods that "
                "you normally tolerate. If eating makes your "
                "symptoms worse, consider medical advice."
            )

        # ----------------------------------------------------
        # REST
        # ----------------------------------------------------

        if (
            "can i rest" in text
            or "should i rest" in text
            or text == "can i rest"
        ):

            return (
                f"Yes, getting adequate rest can be helpful while "
                f"your body is dealing with {topic_name}. Avoid "
                "activities that make you feel worse and continue "
                "monitoring your symptoms."
            )

        # ----------------------------------------------------
        # SERIOUSNESS
        # ----------------------------------------------------

        if (
            "is it serious" in text
            or "should i worry" in text
        ):

            return (
                f"{topic_name.capitalize()} can have many possible "
                "causes, and seriousness depends on the severity, "
                "duration, and other symptoms. If symptoms are "
                "severe, rapidly worsening, or accompanied by "
                "emergency warning signs, seek urgent medical care."
            )

        # ----------------------------------------------------
        # HOW LONG?
        # ----------------------------------------------------

        if (
            "how long" in text
            or "how long does it last" in text
            or "how long will it last" in text
        ):

            duration = self.context.get(
                "duration"
            )

            if duration:

                return (
                    f"You mentioned that your {topic_name} has "
                    f"been present for {duration}. How long it "
                    "lasts depends on the underlying cause. If "
                    "it is not improving, is getting worse, or "
                    "continues longer than expected, consider "
                    "speaking with a healthcare professional."
                )

            return (
                f"The duration of {topic_name} varies depending "
                "on the underlying cause. If it persists, worsens, "
                "or interferes significantly with normal activities, "
                "consider getting medical advice."
            )

        # ----------------------------------------------------
        # MEDICINE
        # ----------------------------------------------------

        if (
            "what medicine" in text
            or "what should i take" in text
            or "can i take medicine" in text
            or "can i take" in text
        ):

            return (
                f"The appropriate medicine for {topic_name} depends "
                "on the cause of the symptoms, your age, allergies, "
                "other medicines, and medical history. It is safer "
                "not to start prescription medicine based only on "
                "a chatbot response. A pharmacist or healthcare "
                "professional can help you choose an appropriate "
                "treatment."
            )

        # ----------------------------------------------------
        # WHY?
        # ----------------------------------------------------

        if (
            text == "why"
            or "why is this happening" in text
            or "what causes it" in text
        ):

            return (
                f"There can be several possible causes of "
                f"{topic_name}. I would need more information "
                "about your symptoms, duration, severity, and "
                "other symptoms to provide more useful general "
                "information."
            )

        return None

    # ========================================================
    # MEDICAL QUESTION TYPE
    # ========================================================

    def detect_question_type(self, message):

        text = self.normalize(message)

        if any(
            phrase in text
            for phrase in [
                "what is",
                "what are",
                "meaning of",
                "define",
                "definition",
            ]
        ):
            return "definition"

        if any(
            phrase in text
            for phrase in [
                "symptoms of",
                "signs of",
                "how do i know",
            ]
        ):
            return "symptoms"

        if any(
            phrase in text
            for phrase in [
                "cause",
                "causes",
                "why",
            ]
        ):
            return "causes"

        if any(
            phrase in text
            for phrase in [
                "treatment",
                "treat",
                "medicine",
                "medication",
            ]
        ):
            return "treatment"

        if any(
            phrase in text
            for phrase in [
                "prevention",
                "prevent",
                "avoid",
            ]
        ):
            return "prevention"

        if any(
            phrase in text
            for phrase in [
                "diet",
                "food",
                "eat",
            ]
        ):
            return "diet"

        return "general"

    # ========================================================
    # DISEASE DETECTION
    # ========================================================

    def extract_disease(self, message):

        text = self.normalize(message)

        diseases = [
            "diabetes",
            "hypertension",
            "high blood pressure",
            "asthma",
            "migraine",
            "pneumonia",
            "influenza",
            "flu",
            "malaria",
            "dengue",
            "typhoid",
            "covid",
            "covid-19",
            "urinary tract infection",
            "uti",
            "pcos",
            "polycystic ovary syndrome",
            "gastritis",
            "acid reflux",
            "anemia",
            "anaemia",
        ]

        for disease in diseases:

            if disease in text:
                return disease

        return None

    # --------------------------------------------------------

    def is_disease_question(self, message):

        return (
            self.extract_disease(message)
            is not None
        )

    # ========================================================
    # DATASET SEARCH
    # ========================================================

    def search_qa(self, message):

        if search_medical_qa is None:
            return None

        try:
            return search_medical_qa(message)
        except Exception:
            return None

    # --------------------------------------------------------

    def rank_medical_results(self, results, message):

        if not results:
            return []

        if not isinstance(results, list):
            results = [results]

        text = self.normalize(message)

        scored = []

        for item in results:

            if isinstance(item, str):

                score = 0

                for word in text.split():

                    if word in self.normalize(item):
                        score += 1

                scored.append(
                    (score, item)
                )

                continue

            if isinstance(item, dict):

                combined = " ".join(
                    str(value)
                    for value in item.values()
                    if value is not None
                )

                combined_normalized = self.normalize(
                    combined
                )

                score = 0

                for word in text.split():

                    if (
                        len(word) >= 3
                        and word in combined_normalized
                    ):
                        score += 1

                scored.append(
                    (score, item)
                )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            item
            for _, item in scored
        ]

    # --------------------------------------------------------

    def valid_qa_result(self, result):

        if result is None:
            return False

        if isinstance(result, str):
            return bool(result.strip())

        if isinstance(result, dict):

            for key in [
                "answer",
                "response",
                "text",
                "content",
                "Answer",
            ]:

                if result.get(key):
                    return True

        return False

    # --------------------------------------------------------

    def format_qa_response(self, result):

        if result is None:
            return None

        if isinstance(result, str):
            return result.strip()

        if isinstance(result, dict):

            answer = (
                result.get("answer")
                or result.get("response")
                or result.get("text")
                or result.get("content")
                or result.get("Answer")
            )

            if answer:
                return str(answer).strip()

        return None

    # ========================================================
    # SYMPTOM DATASET
    # ========================================================

    def search_symptoms(self, message):

        if search_symptom2disease is None:
            return None

        try:
            return search_symptom2disease(message)
        except Exception:
            return None

    # --------------------------------------------------------

    def symptom_response(self, message):

        result = self.search_symptoms(message)

        if not result:
            return None

        ranked = self.rank_medical_results(
            result,
            message,
        )

        if not ranked:
            return None

        first = ranked[0]

        if isinstance(first, str):
            return first

        if isinstance(first, dict):

            disease = (
                first.get("label")
                or first.get("disease")
                or first.get("Disease")
                or first.get("name")
            )

            if disease:

                return (
                    "Your symptoms may be associated with several "
                    f"possible conditions, including {disease}. "
                    "This is not a diagnosis. Symptoms can overlap "
                    "between different conditions, so a healthcare "
                    "professional should be consulted for diagnosis."
                )

        return None

    # ========================================================
    # DISEASE INFORMATION
    # ========================================================

    def disease_information_response(self, message):

        disease = self.extract_disease(message)

        if not disease:
            return None

        question_type = self.detect_question_type(message)

        if question_type == "prevention":

            if search_precautions is not None:

                try:

                    result = search_precautions(
                        disease
                    )

                    if result:

                        formatted = self.format_qa_response(
                            result
                        )

                        if formatted:
                            return formatted

                        if isinstance(result, list):

                            lines = []

                            for item in result[:8]:

                                if isinstance(item, str):
                                    lines.append(
                                        f"• {item}"
                                    )

                                elif isinstance(item, dict):

                                    value = (
                                        item.get("precaution")
                                        or item.get("Precaution")
                                        or item.get("text")
                                        or item.get("description")
                                    )

                                    if value:
                                        lines.append(
                                            f"• {value}"
                                        )

                            if lines:

                                return (
                                    f"General precautions related to "
                                    f"{disease}:\n"
                                    + "\n".join(lines)
                                )

                except Exception:
                    pass

        if question_type == "symptoms":

            if search_disease_symptoms is not None:

                try:

                    result = search_disease_symptoms(
                        disease
                    )

                    if result:

                        formatted = self.format_qa_response(
                            result
                        )

                        if formatted:
                            return formatted

                        if isinstance(result, list):

                            items = []

                            for item in result[:10]:

                                if isinstance(item, str):
                                    items.append(
                                        f"• {item}"
                                    )

                                elif isinstance(item, dict):

                                    value = (
                                        item.get("symptom")
                                        or item.get("Symptom")
                                        or item.get("name")
                                    )

                                    if value:
                                        items.append(
                                            f"• {value}"
                                        )

                            if items:

                                return (
                                    f"Common symptoms associated with "
                                    f"{disease} may include:\n"
                                    + "\n".join(items)
                                )

                except Exception:
                    pass

        return None

    # ========================================================
    # MEDICAL ROUTER
    # ========================================================

    def medical_module_response(self, message):

        if self.medical_router is None:
            return None

        try:

            if hasattr(
                self.medical_router,
                "process",
            ):

                result = self.medical_router.process(
                    message
                )

            elif hasattr(
                self.medical_router,
                "route",
            ):

                result = self.medical_router.route(
                    message
                )

            elif hasattr(
                self.medical_router,
                "respond",
            ):

                result = self.medical_router.respond(
                    message
                )

            else:
                return None

            return self.format_qa_response(
                result
            )

        except Exception:
            return None

    # ========================================================
    # BOT REGISTRY
    # ========================================================

    # ========================================================
    # HEALTH Q&A BOTS (trained on chatbot/health_qa/knowledge.py)
    # ========================================================

    _health_bots = {}

    def is_full_health_question(self, message):
        """
        True for a complete question such as "What should I do if a
        child has a fever?". These are answered on their own and are
        not treated as a short follow-up to the previous message.
        """

        words = str(message).lower().split()

        if len(words) < 5:
            return False

        return words[0] in {
            "what", "how", "why", "when", "which", "who",
            "can", "could", "should", "is", "are", "do", "does",
        }

    # --------------------------------------------------------

    def health_qa_response(self, bot_type, message):
        """
        Answer general health questions with the Rule / ML / DL bots
        from chatbot/health_qa. Returns None when the bot does not
        recognise the topic, so the older logic can still try.
        """

        try:

            if bot_type not in ConversationManager._health_bots:

                from chatbot.health_qa.bots import (
                    RuleBot,
                    MLBot,
                    DLBot,
                )

                classes = {
                    "rule": RuleBot,
                    "ml": MLBot,
                    "dl": DLBot,
                }

                if bot_type not in classes:
                    return None

                ConversationManager._health_bots[bot_type] = (
                    classes[bot_type]()
                )

            result = ConversationManager._health_bots[
                bot_type
            ].answer(message)

        except Exception as error:

            print(
                "[HEALTH QA] could not answer:",
                error,
            )

            return None

        if not result or not result.get("topic"):
            return None

        return {
            "response": result["response"],
            "source": bot_type,
            "score": result["confidence"],
            "confidence": result["confidence"],
            "label": result["topic"],
            "label_display": result["topic"].replace("_", " ").title(),
            "architecture": bot_type,
        }

    # --------------------------------------------------------

    def _call_bot(self, bot_type, message):

        bot_type = self.normalize_bot_type(
            bot_type
        )

        if bot_type == "hybrid":

            return self.hybrid_architecture_response(
                message
            )

        # Rule-Based only: add the onboarding keyword for vague questions
        if bot_type == "rule" and getattr(self, "_rule_hint", ""):

            message = f"{message} {self._rule_hint}"

        # new trained health bots first, older registry as backup
        health_result = self.health_qa_response(
            bot_type,
            message,
        )

        if health_result:
            return health_result

        if get_bot_response is None:
            return None

        try:

            result = get_bot_response(
                bot_type,
                message,
            )

        except Exception:

            return None

        if not result:
            return None

        if isinstance(result, str):

            response = result.strip()

            if not response:
                return None

            return {
                "response": response,
                "source": bot_type,
                "score": 0,
                "confidence": 0,
                "label": None,
                "label_display": None,
                "architecture": bot_type,
            }

        if isinstance(result, dict):

            response = (
                result.get("response")
                or result.get("answer")
                or result.get("text")
                or result.get("message")
                or result.get("content")
            )

            if response is None:
                return None

            response = str(
                response
            ).strip()

            if not response:
                return None

            source = (
                result.get("source")
                or result.get("chatbot")
                or result.get("chatbot_type")
                or bot_type
            )

            score = (
                result.get("score")
                if result.get("score") is not None
                else result.get(
                    "confidence",
                    0,
                )
            )

            confidence = result.get(
                "confidence",
                score,
            )

            return {
                "response": response,
                "source": source,
                "score": score,
                "confidence": confidence,
                "label": result.get("label"),
                "label_display": result.get(
                    "label_display"
                ),
                "architecture": bot_type,
            }

        return None

    # ========================================================
    # CLEAN ARCHITECTURE RESPONSE
    # ========================================================

    def clean_architecture_response(
        self,
        response,
        bot_type=None,
    ):

        if response is None:
            return None

        response = str(
            response
        ).strip()

        if not response:
            return None

        response = response.replace(
            "\r\n",
            "\n",
        )

        response = re.sub(
            r"\n{3,}",
            "\n\n",
            response,
        )

        return response.strip()

    # ========================================================
    # INDIVIDUAL ARCHITECTURE
    # ========================================================

    def architecture_response(
        self,
        message,
        bot_type,
    ):

        bot_type = self.normalize_bot_type(
            bot_type
        )

        if bot_type == "hybrid":

            return self.hybrid_architecture_response(
                message
            )

        result = self._call_bot(
            bot_type,
            message,
        )

        if not result:
            return None

        response = self.clean_architecture_response(
            result.get("response"),
            bot_type,
        )

        if not response:
            return None

        result["response"] = response
        result["source"] = bot_type
        result["architecture"] = bot_type

        return result

    # ========================================================
    # HYBRID ARCHITECTURE
    # ========================================================

    def hybrid_architecture_response(self, message):

        candidates = []

        for architecture in [
            "rule",
            "ml",
            "dl",
        ]:

            result = self._call_bot(
                architecture,
                message,
            )

            if result:

                result["architecture"] = architecture

                candidates.append(
                    result
                )

        if not candidates:
            return None

        selected = self.select_hybrid_response(
            candidates,
            message,
        )

        if not selected:
            return None

        selected_response = self.clean_architecture_response(
            selected.get("response"),
            selected.get("architecture"),
        )

        if not selected_response:
            return None

        selected_architecture = (
            selected.get("architecture")
            or selected.get("source")
            or "hybrid"
        )

        architecture_details = []

        for candidate in candidates:

            architecture_details.append(
                {
                    "architecture": candidate.get(
                        "architecture",
                        candidate.get("source"),
                    ),
                    "response": candidate.get(
                        "response",
                        "",
                    ),
                    "score": candidate.get(
                        "score",
                        0,
                    ),
                    "confidence": candidate.get(
                        "confidence",
                        candidate.get(
                            "score",
                            0,
                        ),
                    ),
                    "label": candidate.get(
                        "label"
                    ),
                    "label_display": candidate.get(
                        "label_display"
                    ),
                }
            )

        return {
            "response": selected_response,
            "source": "hybrid",
            "score": selected.get(
                "score",
                0,
            ),
            "confidence": selected.get(
                "confidence",
                selected.get(
                    "score",
                    0,
                ),
            ),
            "architecture": "hybrid",
            "selected_architecture": selected_architecture,
            "architectures": architecture_details,
        }

    # ========================================================
    # HYBRID RESPONSE SELECTION
    # ========================================================

    def select_hybrid_response(
        self,
        candidates,
        message,
    ):
        """
        Select the safest and most relevant architecture result.

        Rule, ML and DL are used internally.

        ML/DL disease labels are not treated as diagnoses.
        """

        if not candidates:
            return None

        message = self.normalize(
            message
        )

        def safe_float(value):

            try:
                return float(value)

            except (
                TypeError,
                ValueError,
            ):
                return 0.0

        def get_architecture(candidate):

            return self.normalize_bot_type(
                candidate.get("architecture")
                or candidate.get("source")
                or ""
            )

        def get_response(candidate):

            return str(
                candidate.get("response")
                or candidate.get("answer")
                or candidate.get("text")
                or ""
            ).strip()

        def get_confidence(candidate):

            return safe_float(
                candidate.get(
                    "confidence",
                    candidate.get(
                        "score",
                        0,
                    ),
                )
            )

        def calculate_relevance(candidate):

            response = self.normalize(
                get_response(candidate)
            )

            message_words = set(
                re.findall(
                    r"\b[a-zA-Z]{3,}\b",
                    message,
                )
            )

            response_words = set(
                re.findall(
                    r"\b[a-zA-Z]{3,}\b",
                    response,
                )
            )

            if not message_words or not response_words:
                return 0.0

            common_words = (
                message_words.intersection(
                    response_words
                )
            )

            return min(
                len(common_words)
                / max(
                    len(message_words),
                    1,
                ),
                1.0,
            )

        def contains_unsafe_classification(candidate):

            architecture = get_architecture(
                candidate
            )

            response = self.normalize(
                get_response(candidate)
            )

            if architecture not in {
                "ml",
                "dl",
            }:
                return False

            unsafe_patterns = [
                "you have",
                "you are suffering from",
                "diagnosis",
                "diagnosed with",
                "the disease is",
                "you likely have",
                "you definitely have",
                "classified as",
                "prediction is",
                "predicted disease",
                "disease prediction",
            ]

            return any(
                pattern in response
                for pattern in unsafe_patterns
            )

        priority = {
            "rule": 3,
            "ml": 2,
            "dl": 1,
        }

        scored_candidates = []

        for candidate in candidates:

            if not isinstance(
                candidate,
                dict,
            ):
                continue

            response = get_response(
                candidate
            )

            if not response:
                continue

            architecture = get_architecture(
                candidate
            )

            if architecture not in {
                "rule",
                "ml",
                "dl",
            }:
                continue

            confidence = get_confidence(
                candidate
            )

            relevance = calculate_relevance(
                candidate
            )

            unsafe = contains_unsafe_classification(
                candidate
            )

            final_score = (
                relevance * 0.65
                + confidence * 0.25
            )

            if (
                architecture == "rule"
                and relevance >= 0.30
            ):
                final_score += 0.10

            if unsafe:
                final_score -= 0.50

            final_score = max(
                0.0,
                min(
                    final_score,
                    1.0,
                ),
            )

            scored_candidates.append(
                {
                    **candidate,
                    "architecture": architecture,
                    "_relevance": round(
                        relevance,
                        4,
                    ),
                    "_confidence": round(
                        confidence,
                        4,
                    ),
                    "_unsafe": unsafe,
                    "_hybrid_score": round(
                        final_score,
                        4,
                    ),
                }
            )

        if not scored_candidates:
            return None

        scored_candidates.sort(
            key=lambda item: (
                item.get(
                    "_hybrid_score",
                    0,
                ),
                item.get(
                    "_relevance",
                    0,
                ),
                item.get(
                    "_confidence",
                    0,
                ),
                priority.get(
                    item.get(
                        "architecture",
                        "",
                    ),
                    0,
                ),
            ),
            reverse=True,
        )

        selected = dict(
            scored_candidates[0]
        )

        selected.pop(
            "_relevance",
            None,
        )

        selected.pop(
            "_confidence",
            None,
        )

        selected.pop(
            "_unsafe",
            None,
        )

        selected.pop(
            "_hybrid_score",
            None,
        )

        return selected

    # ========================================================
    # GENERAL DATASET FALLBACK
    # ========================================================

    def general_response(self, message):

        qa_result = self.search_qa(
            message
        )

        if qa_result:

            ranked = self.rank_medical_results(
                qa_result,
                message,
            )

            if ranked:

                formatted = self.format_qa_response(
                    ranked[0]
                )

                if formatted:
                    return formatted

        symptom_result = self.symptom_response(
            message
        )

        if symptom_result:
            return symptom_result

        disease_result = (
            self.disease_information_response(
                message
            )
        )

        if disease_result:
            return disease_result

        return (
            "I can help with general health information. "
            "Please describe your symptoms, health question, "
            "duration, or other relevant details. "
            "I can provide general information, but I cannot "
            "replace a qualified healthcare professional."
        )

    # ========================================================
    # EMERGENCY DETECTION
    # ========================================================

    def check_emergency(self, message):

        text = self.normalize(
            message
        )

        emergency_patterns = [
            "difficulty breathing",
            "cannot breathe",
            "can't breathe",
            "severe chest pain",
            "chest pain and difficulty breathing",
            "unconscious",
            "passed out",
            "loss of consciousness",
            "seizure",
            "heavy bleeding",
            "uncontrolled bleeding",
            "vomiting blood",
            "coughing blood",
            "blood in vomit",
            "stroke symptoms",
            "face drooping",
            "slurred speech",
            "sudden weakness on one side",
            "suicidal",
            "want to die",
            "self harm",
            "severe allergic reaction",
            "anaphylaxis",
        ]

        for pattern in emergency_patterns:

            if pattern in text:

                return {
                    "is_emergency": True,
                    "message": (
                        "The symptoms you described may require urgent "
                        "medical attention. Please contact your local "
                        "emergency service or go to the nearest emergency "
                        "department immediately. Do not rely on a chatbot "
                        "for emergency diagnosis or treatment."
                    ),
                }

        return {
            "is_emergency": False,
            "message": None,
        }

    # ========================================================
    # ARCHITECTURE DETAILS
    # ========================================================

    def get_architecture_details(
        self,
        architecture,
    ):

        architecture = self.normalize_bot_type(
            architecture
        )

        details = {

            "rule": {
                "name": "Rule-Based",
                "short_name": "Rule",
                "description": (
                    "Uses predefined rules, patterns and "
                    "decision logic."
                ),
            },

            "ml": {
                "name": "Machine Learning",
                "short_name": "ML",
                "description": (
                    "Uses a trained machine-learning model "
                    "to classify or interpret input."
                ),
            },

            "dl": {
                "name": "Deep Learning",
                "short_name": "DL",
                "description": (
                    "Uses a trained deep-learning model "
                    "for healthcare language understanding."
                ),
            },

            "rag": {
                "name": "RAG + LLM",
                "short_name": "RAG",
                "description": (
                    "Retrieves relevant information and uses "
                    "an LLM-based response layer."
                ),
            },

            "hybrid": {
                "name": "Hybrid",
                "short_name": "Hybrid",
                "description": (
                    "Combines Rule-Based, Machine Learning and "
                    "Deep Learning responses into one MediChat "
                    "conversation."
                ),
            },
        }

        return details.get(
            architecture,
            details["hybrid"],
        )

    # ========================================================
    # RESULT BUILDER
    # ========================================================

    def _result(
        self,
        response,
        source="hybrid",
        score=0,
        start_time=None,
        architecture=None,
        selected_architecture=None,
        architectures=None,
        emergency=False,
        confidence=None,
    ):

        if start_time is None:
            start_time = time.perf_counter()

        response_time = (
            time.perf_counter()
            - start_time
        )

        try:

            response_time = round(
                float(response_time),
                4,
            )

        except Exception:

            response_time = 0.0

        result = {

            "response": str(
                response
                if response is not None
                else ""
            ).strip(),

            "source": source,

            "score": score,

            "response_time": response_time,

            "architecture": (
                architecture
                or source
            ),

            "emergency": bool(
                emergency
            ),
        }

        if confidence is not None:
            result["confidence"] = confidence

        if selected_architecture:
            result["selected_architecture"] = (
                selected_architecture
            )

        if architectures is not None:
            result["architectures"] = architectures

        return result

    # ========================================================
    # HISTORY
    # ========================================================

    def save_history(
        self,
        message,
        response,
        source="hybrid",
        response_time=0,
    ):

        self.conversation_history.append(
            {
                "user": message,
                "assistant": response,
                "source": source,
                "response_time": response_time,
                "timestamp": time.time(),
            }
        )

        if len(
            self.conversation_history
        ) > 100:

            self.conversation_history = (
                self.conversation_history[-100:]
            )

        self.context["last_response"] = response

    # ========================================================
    # MAIN PROCESS MESSAGE
    # ========================================================

    def process_message(
        self,
        message,
        bot_type="hybrid",
        comparison_mode=False,
    ):
        """
        Normal chat entry point.

        1. The chosen chatbot answers the user's real question with its
           own method (Rule / ML / DL are not changed).
        2. If the question relates to what the user said during
           onboarding, one short personalised note is added after the
           answer. Emergencies, greetings and unrelated questions are
           left alone, and comparison_mode never uses onboarding data.
        """

        context = getattr(self, "onboarding_context", None)

        use_context = bool(
            context
            and context.get("has_context")
            and not comparison_mode
        )

        # Rule-Based only: vague questions such as "How can I feel
        # better?" get the onboarding concern as an extra keyword.
        self._rule_hint = ""

        if use_context:
            self._rule_hint = rule_keywords(
                context,
                str(message),
            )

        try:

            result = self._process_message_core(
                message,
                bot_type=bot_type,
                comparison_mode=comparison_mode,
            )

        finally:

            self._rule_hint = ""

        if not use_context or not isinstance(result, dict):
            return result

        if result.get("emergency"):
            return result

        if result.get("source") not in {
            "rule", "ml", "dl", "hybrid", "medical", "medical_knowledge",
        }:
            return result

        note = personalised_note(
            context,
            str(message),
        )

        if note:

            result["response"] = (
                str(result.get("response", "")).rstrip()
                + "\n\n"
                + note
            )

            result["personalized"] = True

        return result

    # --------------------------------------------------------

    def _process_message_core(
        self,
        message,
        bot_type="hybrid",
        comparison_mode=False,
    ):

        start_time = time.perf_counter()

        original_message = message

        message = self.clean_text(
            message
        )

        if not message:

            return self._result(
                response=(
                    "Please enter a health-related question "
                    "or describe your symptoms."
                ),
                source="hybrid",
                score=0,
                start_time=start_time,
                architecture="hybrid",
            )

        bot_type = self.normalize_bot_type(
            bot_type
        )

        comparison_mode = bool(
            comparison_mode
        )

        # ====================================================
        # CONVERSATIONAL SHORTCUTS
        # ====================================================

        goodbye = self.goodbye_response(
            message
        )

        if goodbye and not comparison_mode:

            self.save_history(
                original_message,
                goodbye,
                "conversation",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=goodbye,
                source="conversation",
                score=1,
                start_time=start_time,
                architecture="conversation",
            )

        greeting = self.greeting_response(
            message
        )

        if greeting and not comparison_mode:

            self.save_history(
                original_message,
                greeting,
                "conversation",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=greeting,
                source="conversation",
                score=1,
                start_time=start_time,
                architecture="conversation",
            )

        thanks = self.thanks_response(
            message
        )

        if thanks and not comparison_mode:

            self.save_history(
                original_message,
                thanks,
                "conversation",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=thanks,
                source="conversation",
                score=1,
                start_time=start_time,
                architecture="conversation",
            )

        # ====================================================
        # EMERGENCY
        # ====================================================

        emergency = self.check_emergency(
            message
        )

        if emergency.get(
            "is_emergency"
        ):

            response = emergency.get(
                "message"
            )

            self.save_history(
                original_message,
                response,
                "safety",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=response,
                source="safety",
                score=1,
                start_time=start_time,
                architecture="safety",
                emergency=True,
            )

        # ====================================================
        # UPDATE CONTEXT
        # ====================================================

        self.update_context(
            message
        )

        # ====================================================
        # CONTEXTUAL FOLLOW-UP
        # ====================================================

        if (
            not comparison_mode
            and bot_type == "hybrid"
            and self.is_follow_up(message)
            and not self.is_new_question(message)
            and not self.is_full_health_question(message)
        ):

            # ------------------------------------------------
            # First handle multiple symptoms carried through
            # the conversation.
            #
            # Example:
            # "I have fever"
            # "Since yesterday and I also have cough"
            # ------------------------------------------------

            contextual = self.combined_symptom_response(
                message
            )

            # ------------------------------------------------
            # If this is not a combined-symptom continuation,
            # use the existing contextual response system.
            # ------------------------------------------------

            if not contextual:

                contextual = self.contextual_response(
                    message
                )

            if contextual:

                self.context["follow_up_turns"] += 1

                self.save_history(
                    original_message,
                    contextual,
                    "context",
                    time.perf_counter()
                    - start_time,
                )

                return self._result(
                    response=contextual,
                    source="context",
                    score=1,
                    start_time=start_time,
                    architecture="hybrid",
                    selected_architecture="context",
                )

        # ====================================================
        # LAST INTENT
        # ====================================================

        self.context["last_intent"] = (
            self.detect_question_type(
                message
            )
        )

        # ====================================================
        # ARCHITECTURE-SPECIFIC MODE
        # ====================================================

        if bot_type in {
            "rule",
            "ml",
            "dl",
            "rag",
        }:

            architecture_result = (
                self.architecture_response(
                    message,
                    bot_type,
                )
            )

            if architecture_result:

                response = architecture_result.get(
                    "response"
                )

                score = architecture_result.get(
                    "score",
                    0,
                )

                confidence = architecture_result.get(
                    "confidence"
                )

                self.save_history(
                    original_message,
                    response,
                    bot_type,
                    time.perf_counter()
                    - start_time,
                )

                return self._result(
                    response=response,
                    source=bot_type,
                    score=score,
                    confidence=confidence,
                    start_time=start_time,
                    architecture=bot_type,
                    selected_architecture=bot_type,
                )

            fallback_messages = {

                "rule": (
                    "The Rule-Based architecture could not "
                    "generate a response for this question."
                ),

                "ml": (
                    "The Machine Learning architecture could "
                    "not generate a response for this question."
                ),

                "dl": (
                    "The Deep Learning architecture could "
                    "not generate a response for this question."
                ),

                "rag": (
                    "The RAG + LLM architecture could not "
                    "generate a response for this question."
                ),
            }

            response = fallback_messages.get(
                bot_type,
                "No architecture response was available.",
            )

            self.save_history(
                original_message,
                response,
                bot_type,
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=response,
                source=bot_type,
                score=0,
                start_time=start_time,
                architecture=bot_type,
                selected_architecture=bot_type,
            )

        # ====================================================
        # NORMAL MEDICHAT / HYBRID
        # ====================================================

        if bot_type == "hybrid":

            hybrid_result = (
                self.hybrid_architecture_response(
                    message
                )
            )

            if hybrid_result:

                response = hybrid_result.get(
                    "response"
                )

                score = hybrid_result.get(
                    "score",
                    0,
                )

                confidence = hybrid_result.get(
                    "confidence"
                )

                selected_architecture = (
                    hybrid_result.get(
                        "selected_architecture"
                    )
                )

                architectures = hybrid_result.get(
                    "architectures",
                    [],
                )

                self.save_history(
                    original_message,
                    response,
                    "hybrid",
                    time.perf_counter()
                    - start_time,
                )

                return self._result(
                    response=response,
                    source="hybrid",
                    score=score,
                    confidence=confidence,
                    start_time=start_time,
                    architecture="hybrid",
                    selected_architecture=(
                        selected_architecture
                    ),
                    architectures=architectures,
                )

        # ====================================================
        # COMPARISON SAFETY
        # ====================================================

        if comparison_mode:

            response = (
                "The requested architecture did not "
                "return a response for this question."
            )

            return self._result(
                response=response,
                source=bot_type,
                score=0,
                start_time=start_time,
                architecture=bot_type,
                selected_architecture=bot_type,
            )

        # ====================================================
        # NORMAL CHAT FALLBACK
        # ====================================================

        medical_response = (
            self.medical_module_response(
                message
            )
        )

        if medical_response:

            self.save_history(
                original_message,
                medical_response,
                "medical",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=medical_response,
                source="medical",
                score=0,
                start_time=start_time,
                architecture="hybrid",
            )

        disease_response = (
            self.disease_information_response(
                message
            )
        )

        if disease_response:

            self.save_history(
                original_message,
                disease_response,
                "medical_knowledge",
                time.perf_counter()
                - start_time,
            )

            return self._result(
                response=disease_response,
                source="medical_knowledge",
                score=0,
                start_time=start_time,
                architecture="hybrid",
            )

        fallback_response = (
            self.general_response(
                message
            )
        )

        self.save_history(
            original_message,
            fallback_response,
            "fallback",
            time.perf_counter()
            - start_time,
        )

        return self._result(
            response=fallback_response,
            source="fallback",
            score=0,
            start_time=start_time,
            architecture="hybrid",
        )

    # ========================================================
    # CLEAR CONTEXT
    # ========================================================

    def clear_context(self):

        self.context = {
            "symptoms": [],
            "duration": None,
            "temperature": None,
            "severity": None,
            "progression": None,
            "other_symptoms": [],
            "active": False,
            "asked_other_symptoms": False,
            "follow_up_turns": 0,
            "last_topic": None,
            "last_intent": None,
            "last_response": None,
        }

        self.conversation_history = []

    # ========================================================
    # GET CONTEXT
    # ========================================================

    def get_context(self):

        return dict(
            self.context
        )

    # ========================================================
    # GET HISTORY
    # ========================================================

    def get_history(self):

        return list(
            self.conversation_history
        )


# ============================================================
# OPTIONAL FACTORY
# ============================================================

def create_conversation_manager(
    user_profile=None,
):

    return ConversationManager(
        user_profile=user_profile
    )


# ============================================================
# MODULE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("MediChat Conversation Manager")
    print("Project: Comparative Analysis of Health Chatbots")
    print("=" * 70)

    manager = ConversationManager()

    tests = [
        "hello",
        "I have fever",
        "Since yesterday and I also have cough",
        "what can i do",
        "how long does it last",
        "I also have chills",
        "what should i drink",
        "can i rest",
    ]

    print("\nConversation test:")

    for message in tests:

        print("\nUSER:")
        print(message)

        try:

            result = manager.process_message(
                message,
                bot_type="hybrid",
            )

            print("\nMEDICHAT:")
            print(
                result.get(
                    "response"
                )
            )

            print(
                "\nSource:",
                result.get(
                    "source"
                ),
            )

            print(
                "Topic:",
                manager.get_current_topic(),
            )

            print(
                "Context:",
                manager.get_context(),
            )

        except Exception:

            traceback.print_exc()

    print(
        "\n"
        + "=" * 70
    )

    print("Architecture tests")

    test_message = (
        "I have a fever. What general steps can I take?"
    )

    for architecture in [
        "rule",
        "ml",
        "dl",
        "rag",
        "hybrid",
    ]:

        print(
            "\n"
            + "-" * 50
        )

        print(
            f"Testing architecture: {architecture}"
        )

        try:

            result = manager.process_message(
                test_message,
                bot_type=architecture,
                comparison_mode=True,
            )

            print(
                "Source:",
                result.get(
                    "source"
                ),
            )

            print(
                "Architecture:",
                result.get(
                    "architecture"
                ),
            )

            print(
                "Selected:",
                result.get(
                    "selected_architecture"
                ),
            )

            print(
                "Response:",
                result.get(
                    "response"
                ),
            )

            print(
                "Response time:",
                result.get(
                    "response_time"
                ),
            )

        except Exception:

            traceback.print_exc()
