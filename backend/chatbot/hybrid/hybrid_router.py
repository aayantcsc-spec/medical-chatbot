"""
MediChat Hybrid Intelligent Router

Project:
Comparative Analysis of Health Chatbots Based on Framework and Architecture

HYBRID DESIGN
--------------
User Message
    ↓
Emergency / Safety Check
    ↓
Conversation / Intent Detection
    ↓
General Health Guidance
    ↓
Rule + ML + DL Supporting Evidence
    ↓
Relevance / Agreement Check
    ↓
Medical Retrieval / RAG
    ↓
Natural Hybrid Response
    ↓
Safe Fallback

IMPORTANT
---------
Hybrid is NOT a fourth disease classifier.

Rule-Based, ML and DL remain separate architectures for
comparative evaluation.

Inside the normal MediChat conversation, they act as
supporting components of one unified conversational system.

A disease prediction from ML/DL is NEVER returned simply
because it has a high confidence score when the user's
question is asking for general health guidance.
"""

import os
import re
import sys
import time


# ============================================================
# PROJECT PATH
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# PROJECT IMPORTS
# ============================================================

from chatbot import config as chatbot_config
from chatbot.pipeline_logging import get_logger


log = get_logger("medichat.pipeline.hybrid_router")


# ============================================================
# BASIC HELPERS
# ============================================================

def _normalize(text):
    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip().lower()
    )


def _safe_confidence(result):
    if not isinstance(result, dict):
        return 0.0

    value = result.get("score")

    if value is None:
        value = result.get("confidence")

    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _build_result(
    response,
    architecture,
    layer,
    confidence,
    start_time,
    fallback_chain=None,
    extra=None,
):
    result = {
        "response": response,
        "architecture": architecture,
        "layer": layer,
        "confidence": confidence,
        "score": confidence,
        "response_time": round(
            time.perf_counter() - start_time,
            6
        ),
        "fallback_chain": fallback_chain or [],
        "hybrid_mode": True,
    }

    if extra:
        result.update(extra)

    log.info(
        "Hybrid routed -> architecture=%s layer=%s confidence=%s time=%.4fs",
        architecture,
        layer,
        confidence,
        result["response_time"],
    )

    return result


# ============================================================
# SMALL TALK
# ============================================================

_GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "hii",
    "hiya",
    "good morning",
    "good afternoon",
    "good evening",
}

_GOODBYE_WORDS = {
    "bye",
    "goodbye",
    "see you",
    "take care",
    "exit",
    "quit",
}

_THANKS_WORDS = {
    "thanks",
    "thank you",
    "thx",
    "appreciate it",
    "thankyou",
}


def is_greeting(text):
    return _normalize(text) in _GREETING_WORDS


def is_goodbye(text):
    return _normalize(text) in _GOODBYE_WORDS


def is_thanks(text):
    return _normalize(text) in _THANKS_WORDS


# ============================================================
# SYMPTOMS
# ============================================================

_SYMPTOM_HINTS = {
    "fever",
    "temperature",
    "high temperature",
    "cough",
    "headache",
    "pain",
    "nausea",
    "vomit",
    "vomiting",
    "fatigue",
    "tired",
    "rash",
    "itching",
    "dizziness",
    "dizzy",
    "chills",
    "sore throat",
    "cold",
    "diarrhea",
    "breathless",
    "breathing",
    "bleeding",
    "swelling",
    "ache",
    "cramps",
    "weakness",
    "sweating",
    "congestion",
    "runny nose",
    "shortness of breath",
    "chest pain",
    "body ache",
    "body pain",
}


def count_symptom_hints(text):
    text = _normalize(text)

    found = set()

    for symptom in _SYMPTOM_HINTS:
        if symptom in text:
            found.add(symptom)

    return len(found)


# ============================================================
# GENERAL HEALTH GUIDANCE DETECTION
# ============================================================

def _is_general_self_care_question(text):
    """
    Detect whether the user is asking for general care,
    rather than asking the system to identify a disease.
    """

    text = _normalize(text)

    guidance_phrases = [
        "what should i do",
        "what can i do",
        "how can i",
        "how should i",
        "general steps",
        "care for myself",
        "home care",
        "self care",
        "take care",
        "manage",
        "relieve",
        "help with",
        "what helps",
        "what should i take",
        "what should i drink",
        "what can i take",
        "how do i feel better",
        "how to feel better",
        "what can help",
    ]

    return any(
        phrase in text
        for phrase in guidance_phrases
    )


def _is_duration_question(text):
    text = _normalize(text)

    duration_phrases = [
        "how long",
        "how many days",
        "how much time",
        "usually last",
        "last for",
        "duration",
        "when will it go away",
        "when should it improve",
    ]

    return any(
        phrase in text
        for phrase in duration_phrases
    )


def _is_symptom_statement(text):
    text = _normalize(text)

    symptom_words = [
        "fever",
        "temperature",
        "cough",
        "coughing",
        "headache",
        "stomach pain",
        "chest pain",
        "back pain",
        "body pain",
        "body ache",
        "rash",
        "itching",
        "nausea",
        "vomiting",
        "diarrhea",
        "dizziness",
        "dizzy",
        "weakness",
        "fatigue",
        "sore throat",
        "runny nose",
        "blocked nose",
        "chills",
    ]

    return any(
        word in text
        for word in symptom_words
    )


# ============================================================
# FOLLOW-UP DETECTION
# ============================================================

def _looks_like_follow_up(text, context):
    """
    Recognize short conversational follow-ups.

    Examples:
        How long does it last?
        What about food?
        Can I rest?
        What should I drink?
        Is that normal?
    """

    if context.get("is_follow_up"):
        return True

    text = _normalize(text)

    follow_up_phrases = [
        "how long",
        "what about",
        "can i",
        "should i",
        "what should",
        "is it normal",
        "will it",
        "when should",
        "how much",
        "what can i",
    ]

    if any(
        phrase in text
        for phrase in follow_up_phrases
    ):
        return True

    if len(text.split()) <= 7 and "?" in text:
        return True

    return False


# ============================================================
# FEVER / GENERAL HEALTH INTENT
# ============================================================

def _contains_fever(text):
    text = _normalize(text)

    return any(
        phrase in text
        for phrase in [
            "fever",
            "high fever",
            "temperature",
            "high temperature",
            "chills",
            "shivering",
        ]
    )


def _contains_headache(text):
    text = _normalize(text)

    return any(
        phrase in text
        for phrase in [
            "headache",
            "head pain",
            "pain in my head",
        ]
    )


def _contains_cough(text):
    text = _normalize(text)

    return any(
        phrase in text
        for phrase in [
            "cough",
            "coughing",
        ]
    )


def _contains_chills(text):
    text = _normalize(text)

    return any(
        phrase in text
        for phrase in [
            "chills",
            "shivering",
            "shivering chills",
        ]
    )


def _general_health_response(text, context):
    """
    Natural response layer for common health-care questions.

    This layer prevents disease classifiers from producing
    unrelated diagnoses for ordinary care questions.

    Returns:
        response string
        or None
    """

    normalized = _normalize(text)

    # --------------------------------------------------------
    # FEVER + GENERAL CARE
    # --------------------------------------------------------

    if (
        _contains_fever(normalized)
        and (
            _is_general_self_care_question(normalized)
            or _is_symptom_statement(normalized)
        )
    ):

        response = (
            "Fever can happen for many different reasons, including "
            "infections. For general care, rest, drink plenty of "
            "fluids, and monitor your temperature. Avoid strenuous "
            "activity and pay attention to whether your symptoms "
            "are improving or getting worse."
        )

        if _contains_chills(normalized):
            response += (
                " Chills can occur along with a fever, so keep yourself "
                "comfortable and continue monitoring your temperature."
            )

        response += (
            " If the fever is very high or persistent, or you develop "
            "difficulty breathing, confusion, severe weakness, repeated "
            "vomiting, severe dehydration, a seizure, or another serious "
            "symptom, seek medical attention promptly."
        )

        response += (
            " How high is your temperature, and how long have you "
            "had the fever?"
        )

        return response

    # --------------------------------------------------------
    # FEVER DURATION
    # --------------------------------------------------------

    if (
        _contains_fever(normalized)
        and _is_duration_question(normalized)
    ):

        return (
            "The duration of a fever depends on its underlying cause. "
            "Many short-term fevers improve within a few days, but "
            "there is no single duration that applies to every case. "
            "If the fever persists, becomes worse, or is accompanied "
            "by serious symptoms, seek medical advice."
        )

    # --------------------------------------------------------
    # HEADACHE GENERAL CARE
    # --------------------------------------------------------

    if (
        _contains_headache(normalized)
        and (
            _is_general_self_care_question(normalized)
            or _is_symptom_statement(normalized)
        )
    ):

        return (
            "For a mild headache, try resting in a quiet environment, "
            "drinking enough fluids, and getting adequate sleep. "
            "Avoiding obvious triggers such as excessive screen time "
            "or loud surroundings may also help. If the headache is "
            "sudden and extremely severe, follows a significant injury, "
            "or occurs with confusion, weakness, fainting, vision "
            "changes, or other serious symptoms, seek medical care."
        )

    # --------------------------------------------------------
    # COUGH GENERAL CARE
    # --------------------------------------------------------

    if (
        _contains_cough(normalized)
        and _is_general_self_care_question(normalized)
    ):

        return (
            "For a mild cough, rest, stay hydrated, and avoid smoke "
            "or other irritants. Warm fluids may be soothing for some "
            "people. If you have difficulty breathing, chest pain, "
            "coughing up blood, severe weakness, or a persistent or "
            "worsening cough, seek medical advice."
        )

    return None


# ============================================================
# CONVERSATIONAL FOLLOW-UP RESPONSE
# ============================================================

def _contextual_follow_up(text, context):
    """
    Handle short follow-up questions using the previous
    conversation context.

    This prevents:
        "How long does it last?"

    from being treated as a completely unrelated disease query.
    """

    normalized = _normalize(text)

    previous_symptoms = context.get(
        "symptoms",
        []
    )

    if isinstance(previous_symptoms, str):
        previous_symptoms = [
            previous_symptoms
        ]

    previous_text = _normalize(
        context.get(
            "last_user_message",
            ""
        )
    )

    fever_context = (
        "fever" in previous_text
        or "temperature" in previous_text
        or "fever" in previous_symptoms
        or "temperature" in previous_symptoms
    )

    # --------------------------------------------------------
    # FEVER FOLLOW-UP
    # --------------------------------------------------------

    if fever_context:

        if _is_duration_question(normalized):

            return (
                "The duration of a fever depends on its cause. "
                "Many short-term fevers improve within a few days, "
                "but this can vary. If your fever persists, becomes "
                "worse, or you develop serious symptoms, seek medical "
                "advice."
            )

        if any(
            phrase in normalized
            for phrase in [
                "what should i drink",
                "what can i drink",
                "drink",
            ]
        ):

            return (
                "Keeping hydrated is important when you have a fever. "
                "Water is a simple choice, and fluids such as soups "
                "or oral rehydration solutions may also be useful, "
                "especially if you are losing fluids."
            )

        if any(
            phrase in normalized
            for phrase in [
                "what should i eat",
                "what can i eat",
                "food",
                "eat",
            ]
        ):

            return (
                "If you have a fever, choose foods that are easy for "
                "you to tolerate and continue drinking enough fluids. "
                "If your appetite is reduced, smaller meals can be "
                "easier than large meals."
            )

        if any(
            phrase in normalized
            for phrase in [
                "can i rest",
                "should i rest",
                "rest",
                "sleep",
            ]
        ):

            return (
                "Yes. Rest and adequate sleep can help your body recover. "
                "Continue monitoring your temperature and how your "
                "symptoms change."
            )

    return None


# ============================================================
# RAG SINGLETON
# ============================================================

_rag_bot_instance = None
_rag_bot_error = None


def _get_rag_bot():

    global _rag_bot_instance
    global _rag_bot_error

    if _rag_bot_instance is not None:
        return _rag_bot_instance, None

    if _rag_bot_error is not None:
        return None, _rag_bot_error

    try:

        from chatbot.rag_based.rag_bot import RAGBot

        _rag_bot_instance = RAGBot()

        return _rag_bot_instance, None

    except Exception as error:

        _rag_bot_error = (
            f"{type(error).__name__}: {error}"
        )

        return None, _rag_bot_error


# ============================================================
# QUERY COMPLEXITY
# ============================================================

def is_complex_query(text, is_follow_up=False):

    if is_follow_up:
        return True

    text = _normalize(text)

    word_count = len(
        text.split()
    )

    try:

        min_symptoms = int(
            getattr(
                chatbot_config,
                "COMPLEX_QUERY_MIN_SYMPTOMS",
                2
            )
        )

    except Exception:

        min_symptoms = 2

    try:

        min_words = int(
            getattr(
                chatbot_config,
                "COMPLEX_QUERY_MIN_WORDS",
                18
            )
        )

    except Exception:

        min_words = 18

    if count_symptom_hints(text) >= min_symptoms:
        return True

    if word_count >= min_words:
        return True

    return False


# ============================================================
# MAIN HYBRID ROUTER
# ============================================================

def route(message, context=None):

    start_time = time.perf_counter()

    text = str(
        message or ""
    ).strip()

    context = context or {}

    fallback_chain = []

    # ========================================================
    # EMPTY INPUT
    # ========================================================

    if not text:

        return _build_result(
            "Please describe your health question or symptoms.",
            "rule",
            "empty_input",
            1.0,
            start_time,
        )

    # ========================================================
    # LOAD BOT REGISTRY
    # ========================================================

    try:

        from chatbot.orchestrator.bot_registry import (
            get_bot_response
        )

    except Exception as error:

        log.error(
            "Bot registry unavailable: %s",
            error
        )

        get_bot_response = None

    # ========================================================
    # STEP 1
    # EMERGENCY
    # ========================================================

    try:

        from chatbot.medical.emergency_detector import (
            check_emergency
        )

        emergency = check_emergency(
            text
        )

    except Exception as error:

        log.warning(
            "Emergency detector unavailable: %s",
            error
        )

        emergency = {
            "is_emergency": False
        }

    if (
        isinstance(emergency, dict)
        and emergency.get("is_emergency")
    ):

        return _build_result(
            emergency.get(
                "response",
                "This may require urgent medical attention. "
                "Please seek medical care promptly."
            ),
            "rule",
            "emergency_safety",
            1.0,
            start_time,
            extra={
                "emergency": True
            },
        )

    # ========================================================
    # STEP 2
    # SMALL TALK
    # ========================================================

    if get_bot_response:

        if (
            is_greeting(text)
            or is_goodbye(text)
            or is_thanks(text)
        ):

            try:

                rule_result = get_bot_response(
                    "rule",
                    text
                )

            except Exception as error:

                log.warning(
                    "Rule small-talk failed: %s",
                    error
                )

                rule_result = {}

            if (
                rule_result.get("available")
                and rule_result.get("response")
            ):

                return _build_result(
                    rule_result["response"],
                    "rule",
                    "smalltalk",
                    1.0,
                    start_time,
                )

            # Safe direct responses if rule bot is unavailable.

            if is_greeting(text):

                return _build_result(
                    "Hello! I'm MediChat, your AI health assistant. "
                    "You can tell me about a health question or symptom, "
                    "and I'll provide general information and guidance.",
                    "hybrid",
                    "conversation_greeting",
                    1.0,
                    start_time,
                )

            if is_thanks(text):

                return _build_result(
                    "You're welcome. If you have another health question, "
                    "feel free to ask.",
                    "hybrid",
                    "conversation_thanks",
                    1.0,
                    start_time,
                )

            if is_goodbye(text):

                return _build_result(
                    "Take care. If you need general health information "
                    "later, you can come back and ask MediChat.",
                    "hybrid",
                    "conversation_goodbye",
                    1.0,
                    start_time,
                )

    # ========================================================
    # STEP 3
    # FOLLOW-UP / CONTEXT
    # ========================================================

    is_follow_up = _looks_like_follow_up(
        text,
        context
    )

    contextual_response = _contextual_follow_up(
        text,
        context
    )

    if contextual_response:

        return _build_result(
            contextual_response,
            "hybrid",
            "contextual_follow_up",
            1.0,
            start_time,
            extra={
                "context_used": True,
            },
        )

    # ========================================================
    # STEP 4
    # GENERAL HEALTH GUIDANCE
    #
    # THIS IS THE MOST IMPORTANT CHANGE.
    #
    # Do this BEFORE allowing ML/DL disease classifications
    # to become the final response.
    # ========================================================

    general_response = _general_health_response(
        text,
        context
    )

    if general_response:

        return _build_result(
            general_response,
            "hybrid",
            "general_health_guidance",
            1.0,
            start_time,
            extra={
                "context_used": bool(context),
                "ml_used_as_support": False,
                "dl_used_as_support": False,
            },
        )

    # ========================================================
    # STEP 5
    # QUERY TYPE
    # ========================================================

    general_guidance = _is_general_self_care_question(
        text
    )

    symptom_statement = _is_symptom_statement(
        text
    )

    complex_query = is_complex_query(
        text,
        is_follow_up=is_follow_up
    )

    # ========================================================
    # STEP 6
    # ML + DL SUPPORTING RESULTS
    # ========================================================

    ml_result = {
        "available": False
    }

    dl_result = {
        "available": False
    }

    ml_confidence = 0.0
    dl_confidence = 0.0

    if get_bot_response:

        try:

            ml_result = get_bot_response(
                "ml",
                text
            )

        except Exception as error:

            log.warning(
                "ML architecture failed: %s",
                error
            )

            ml_result = {
                "available": False,
                "error": str(error)
            }

        try:

            dl_result = get_bot_response(
                "dl",
                text
            )

        except Exception as error:

            log.warning(
                "DL architecture failed: %s",
                error
            )

            dl_result = {
                "available": False,
                "error": str(error)
            }

        ml_confidence = _safe_confidence(
            ml_result
        )

        dl_confidence = _safe_confidence(
            dl_result
        )

    # ========================================================
    # STEP 7
    # CLASSIFICATION ONLY WHEN APPROPRIATE
    #
    # General-care questions NEVER enter this section.
    # ========================================================

    if (
        symptom_statement
        and not general_guidance
        and not complex_query
    ):

        ml_available = bool(
            ml_result.get("available")
            and ml_result.get("response")
        )

        dl_available = bool(
            dl_result.get("available")
            and dl_result.get("response")
        )

        try:

            ml_threshold = float(
                getattr(
                    chatbot_config,
                    "ML_CONFIDENCE_HIGH",
                    0.75
                )
            )

        except Exception:

            ml_threshold = 0.75

        try:

            dl_threshold = float(
                getattr(
                    chatbot_config,
                    "DL_CONFIDENCE_HIGH",
                    0.75
                )
            )

        except Exception:

            dl_threshold = 0.75

        ml_high = (
            ml_confidence >= ml_threshold
        )

        dl_high = (
            dl_confidence >= dl_threshold
        )

        ml_label = str(
            ml_result.get(
                "label",
                ml_result.get(
                    "prediction",
                    ""
                )
            )
        ).strip().lower()

        dl_label = str(
            dl_result.get(
                "label",
                dl_result.get(
                    "prediction",
                    ""
                )
            )
        ).strip().lower()

        # ----------------------------------------------------
        # ML + DL AGREEMENT
        # ----------------------------------------------------

        if (
            ml_available
            and dl_available
            and ml_high
            and dl_high
            and ml_label
            and dl_label
            and ml_label == dl_label
        ):

            return _build_result(
                ml_result["response"],
                "hybrid",
                "ml_dl_agreement",
                round(
                    (
                        ml_confidence
                        + dl_confidence
                    ) / 2,
                    4
                ),
                start_time,
                extra={
                    "selected_architecture": "ml+dl",
                    "ml_confidence": ml_confidence,
                    "dl_confidence": dl_confidence,
                    "ml_label": ml_label,
                    "dl_label": dl_label,
                },
            )

        # ----------------------------------------------------
        # DISAGREEMENT
        # ----------------------------------------------------

        if ml_available or dl_available:

            fallback_chain.append(
                "ml_dl_not_agreed"
            )

    # ========================================================
    # STEP 8
    # MEDICAL RETRIEVAL
    # ========================================================

    retrieval = {
        "success": False
    }

    retrieval_confidence = None

    try:

        from chatbot.medical.medical_router import (
            route_medical_query
        )

        retrieval = route_medical_query(
            text
        )

    except Exception as error:

        log.warning(
            "Medical retrieval unavailable: %s",
            error
        )

        fallback_chain.append(
            "retrieval_error"
        )

    if not isinstance(
        retrieval,
        dict
    ):

        retrieval = {
            "success": False
        }

    if (
        isinstance(
            retrieval.get("risk"),
            dict
        )
    ):

        retrieval_confidence = retrieval[
            "risk"
        ].get(
            "score"
        )

    # --------------------------------------------------------
    # RETRIEVAL RESPONSE
    # --------------------------------------------------------

    if (
        retrieval.get("success")
        and retrieval.get("response")
    ):

        return _build_result(
            retrieval["response"],
            "retrieval",
            "medical_dataset",
            retrieval_confidence,
            start_time,
            fallback_chain=fallback_chain,
        )

    # ========================================================
    # STEP 9
    # RAG
    # ========================================================

    rag_bot, rag_error = _get_rag_bot()

    if rag_bot is not None:

        try:

            rag_result = rag_bot.chat(
                text
            )

        except Exception as error:

            log.warning(
                "RAG failed: %s",
                error
            )

            rag_result = None

            fallback_chain.append(
                "rag_error"
            )

        if (
            isinstance(
                rag_result,
                dict
            )
            and rag_result.get("response")
        ):

            try:

                used_llm = (
                    getattr(
                        rag_bot,
                        "llm_backend",
                        "fallback"
                    )
                    == "openai"
                )

            except Exception:

                used_llm = False

            sources = []

            try:

                sources = rag_bot.get_sources(
                    rag_result.get(
                        "retrieved_documents",
                        []
                    )
                )

            except Exception:

                sources = []

            return _build_result(
                rag_result["response"],
                "rag_llm" if used_llm else "retrieval",
                "rag_generation",
                rag_result.get(
                    "confidence"
                ),
                start_time,
                fallback_chain=fallback_chain,
                extra={
                    "used_llm": used_llm,
                    "sources": sources,
                },
            )

    else:

        fallback_chain.append(
            "rag_unavailable"
        )

    # ========================================================
    # STEP 10
    # SAFE NON-CLASSIFICATION FALLBACK
    #
    # IMPORTANT:
    #
    # DO NOT use DL or ML here for general questions.
    #
    # The old code did:
    #
    #     fallback → DL
    #
    # which caused:
    #
    #     fever → psoriasis
    #
    # ========================================================

    fallback_chain.append(
        "safe_hybrid_fallback"
    )

    if (
        general_guidance
        or symptom_statement
        or complex_query
    ):

        return _build_result(
            (
                "I can provide general health information, but I "
                "couldn't find enough relevant information to answer "
                "that safely. Please describe your symptoms, how long "
                "you have had them, and any important associated "
                "symptoms. If the situation is urgent or severe, "
                "please seek medical care."
            ),
            "hybrid",
            "safe_health_fallback",
            0.0,
            start_time,
            fallback_chain=fallback_chain,
        )

    # ========================================================
    # STEP 11
    # RULE FALLBACK
    # ========================================================

    if get_bot_response:

        try:

            rule_result = get_bot_response(
                "rule",
                text
            )

        except Exception as error:

            log.warning(
                "Rule fallback failed: %s",
                error
            )

            rule_result = {}

    else:

        rule_result = {}

    response = (
        rule_result.get(
            "response"
        )
        or
        (
            "I'm not able to fully answer that right now. "
            "Please describe your health question in more detail."
        )
    )

    return _build_result(
        response,
        "rule",
        "fallback_rule",
        rule_result.get(
            "score"
        ),
        start_time,
        fallback_chain=fallback_chain,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("MEDICHAT HYBRID ROUTER TEST")
    print("=" * 70)

    test_messages = [

        "hello",

        "I have a high fever with chills. What should I do?",

        "I have a fever. What general steps can I take to care for myself?",

        "How long does a common fever usually last?",

        "I have a headache. What should I do?",

        "I have itching and skin rash",

        "I have fever and headache",

        "What should I do for a headache?",

        "I have chest pain",

        "Thanks",

        "bye",
    ]

    for message in test_messages:

        print("\n" + "-" * 70)

        print(
            "INPUT:",
            message
        )

        try:

            result = route(
                message
            )

            print(
                "ARCHITECTURE:",
                result.get(
                    "architecture"
                )
            )

            print(
                "LAYER:",
                result.get(
                    "layer"
                )
            )

            print(
                "CONFIDENCE:",
                result.get(
                    "confidence"
                )
            )

            print(
                "RESPONSE TIME:",
                result.get(
                    "response_time"
                )
            )

            print(
                "RESPONSE:",
                result.get(
                    "response"
                )
            )

        except Exception as error:

            print(
                "ERROR:",
                type(error).__name__,
                error
            )