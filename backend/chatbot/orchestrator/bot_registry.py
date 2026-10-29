"""
MediChat Bot Registry
=====================

Project:
    Comparative Analysis of Health Chatbots Based on Framework and Architecture

Research architectures:
    1. Rule-Based
    2. Machine Learning
    3. Deep Learning

Additional architecture support:
    4. RAG / LLM

Hybrid:
    Hybrid is controlled by ConversationManager and combines
    Rule-Based + Machine Learning + Deep Learning.

Important design:
    - Normal chat should feel like one unified healthcare assistant.
    - ML/DL raw predictions are preserved for research/evaluation.
    - Raw disease predictions are NOT presented as diagnoses.
    - Emergency and medication safety are handled before model output.
    - Comparison/evaluation can still access raw labels and confidence.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, Optional


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# ARCHITECTURES
# ============================================================

ARCHITECTURES = [
    "rule",
    "ml",
    "dl",
    "rag",
]


# ============================================================
# CACHE
# ============================================================

_BOT_CACHE: Dict[str, Any] = {}


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convert a value to a safe float between 0 and 1.

    If a percentage such as 23.5 is supplied, convert it to 0.235.
    """

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if number > 1.0:
        number = number / 100.0

    if number < 0:
        number = 0.0

    if number > 1:
        number = 1.0

    return number


def _normalize_text(message: Any) -> str:
    """Normalize user text."""

    if message is None:
        return ""

    text = str(message).strip().lower()

    text = re.sub(r"\s+", " ", text)

    return text


def _clean_response(response: Any) -> str:
    """Convert a response to a safe string."""

    if response is None:
        return ""

    if isinstance(response, str):
        return response.strip()

    return str(response).strip()


def _result_base(
    *,
    response: str,
    architecture: str,
    source: str,
    confidence: float = 0.0,
    score: float = 0.0,
) -> Dict[str, Any]:
    """Create a consistent result dictionary."""

    return {
        "response": response,
        "architecture": architecture,
        "source": source,
        "confidence": _safe_float(confidence),
        "score": _safe_float(score),
    }


# ============================================================
# MEDICAL SAFETY HELPERS
# ============================================================

def _is_emergency_message(message: str) -> bool:
    """
    Detect high-priority emergency situations.

    This is intentionally conservative.
    """

    text = _normalize_text(message)

    if not text:
        return False

    emergency_phrases = [
        "difficulty breathing",
        "trouble breathing",
        "cannot breathe",
        "can't breathe",
        "unable to breathe",
        "shortness of breath",
        "severe breathing problem",
        "chest pain and difficulty breathing",
        "chest pain with difficulty breathing",
        "severe chest pain",
        "crushing chest pain",
        "heavy bleeding",
        "uncontrolled bleeding",
        "vomiting blood",
        "blood in vomit",
        "black stool",
        "passed out",
        "unconscious",
        "not responding",
        "loss of consciousness",
        "seizure",
        "convulsion",
        "stroke symptoms",
        "face drooping",
        "one side weakness",
        "sudden weakness on one side",
        "sudden trouble speaking",
        "suicidal",
        "suicide",
        "kill myself",
        "want to die",
    ]

    return any(phrase in text for phrase in emergency_phrases)


def _emergency_response() -> str:
    """Safe emergency response."""

    return (
        "Some of the symptoms you described may need urgent medical attention. "
        "If you are having severe or worsening symptoms, especially difficulty "
        "breathing, severe chest pain, heavy bleeding, loss of consciousness, "
        "or another serious emergency, please contact your local emergency "
        "service or go to the nearest emergency department now. "
        "Do not rely on the chatbot for emergency diagnosis or treatment."
    )


def _is_medication_question(message: str) -> bool:
    """
    Detect requests involving medicines, tablets or dosage.

    This prevents the ML model from turning medication-related text
    into an unsafe disease response.
    """

    text = _normalize_text(message)

    medication_terms = [
        "medicine",
        "medicines",
        "medication",
        "medications",
        "tablet",
        "tablets",
        "capsule",
        "capsules",
        "drug",
        "drugs",
        "dose",
        "dosage",
        "how much should i take",
        "what should i take",
        "which medicine",
        "which tablet",
        "what tablet",
        "can i take",
        "should i take",
    ]

    return any(term in text for term in medication_terms)


def _medication_response() -> str:
    """Safe medication response."""

    return (
        "I can provide general information about medicines, but I cannot "
        "recommend a specific medicine or dose for your symptoms. "
        "If you have a particular medicine in mind, tell me its name and "
        "I can explain its general purpose, common precautions, and when "
        "professional advice may be needed. For a personal treatment "
        "decision, please consult a doctor or pharmacist."
    )


# ============================================================
# CONDITION QUESTION DETECTION
# ============================================================

def _is_condition_question(message: str) -> bool:
    """
    Detect whether the user is explicitly asking about a possible condition.

    This is different from simply saying:
        "I have fever."

    We only expose a model's possible label when the user explicitly
    asks about possible causes/conditions.
    """

    text = _normalize_text(message)

    patterns = [
        "what disease",
        "which disease",
        "what condition",
        "which condition",
        "what could this be",
        "what might this be",
        "what could i have",
        "what might i have",
        "could this be",
        "is this",
        "possible disease",
        "possible condition",
        "possible cause",
        "what is causing",
        "what causes this",
        "what may be causing",
        "do i have",
        "am i suffering from",
    ]

    return any(pattern in text for pattern in patterns)


# ============================================================
# SYMPTOM DETECTION
# ============================================================

_SYMPTOM_ALIASES = {
    "fever": [
        "fever",
        "high temperature",
        "temperature",
        "running a fever",
    ],
    "headache": [
        "headache",
        "head pain",
        "pain in my head",
    ],
    "cough": [
        "cough",
        "coughing",
    ],
    "sore throat": [
        "sore throat",
        "throat pain",
        "painful throat",
    ],
    "runny nose": [
        "runny nose",
        "running nose",
    ],
    "blocked nose": [
        "blocked nose",
        "stuffy nose",
        "nasal congestion",
    ],
    "nausea": [
        "nausea",
        "feeling nauseous",
        "feel nauseous",
    ],
    "vomiting": [
        "vomiting",
        "throwing up",
        "threw up",
    ],
    "diarrhea": [
        "diarrhea",
        "loose motions",
        "loose stools",
    ],
    "stomach pain": [
        "stomach pain",
        "stomach ache",
        "abdominal pain",
        "belly pain",
    ],
    "dizziness": [
        "dizzy",
        "dizziness",
        "feeling dizzy",
    ],
    "weakness": [
        "weakness",
        "feeling weak",
        "feel weak",
    ],
    "fatigue": [
        "fatigue",
        "very tired",
        "extremely tired",
        "feeling tired",
    ],
    "body pain": [
        "body pain",
        "body ache",
        "body aches",
    ],
    "chills": [
        "chills",
        "shivering",
        "shivering chills",
    ],
    "rash": [
        "rash",
        "skin rash",
        "rashes",
    ],
    "itching": [
        "itching",
        "itchy",
    ],
    "joint pain": [
        "joint pain",
        "pain in my joints",
    ],
    "back pain": [
        "back pain",
        "pain in my back",
    ],
    "chest pain": [
        "chest pain",
        "pain in my chest",
    ],
    "breathing difficulty": [
        "difficulty breathing",
        "trouble breathing",
        "shortness of breath",
    ],
}


def _detect_symptoms(message: str) -> list[str]:
    """
    Detect common symptoms mentioned in the user's message.

    The order of the dictionary is preserved.
    """

    text = _normalize_text(message)

    found = []

    for symptom, aliases in _SYMPTOM_ALIASES.items():

        for alias in aliases:

            if alias in text:
                found.append(symptom)
                break

    return found


# ============================================================
# NATURAL MEDICAL RESPONSES
# ============================================================

def _natural_symptom_response(message: str) -> str:
    """
    Create a general, safe medical response without presenting
    an ML prediction as a diagnosis.
    """

    text = _normalize_text(message)

    symptoms = _detect_symptoms(text)

    # --------------------------------------------------------
    # Emergency first
    # --------------------------------------------------------

    if _is_emergency_message(text):
        return _emergency_response()

    # --------------------------------------------------------
    # Medication
    # --------------------------------------------------------

    if _is_medication_question(text):
        return _medication_response()

    # --------------------------------------------------------
    # Multiple symptoms
    # --------------------------------------------------------

    if len(symptoms) >= 2:

        readable = symptoms[:4]

        if len(readable) == 2:
            symptom_text = f"{readable[0]} and {readable[1]}"

        elif len(readable) == 3:
            symptom_text = (
                f"{readable[0]}, {readable[1]}, and {readable[2]}"
            )

        else:
            symptom_text = (
                f"{readable[0]}, {readable[1]}, "
                f"{readable[2]}, and {readable[3]}"
            )

        return (
            f"I understand that you are experiencing {symptom_text}. "
            "These symptoms can occur together for several different "
            "reasons, so they cannot be used by the chatbot alone to "
            "confirm a specific condition.\n\n"
            "For now, rest, stay hydrated if you can, and monitor whether "
            "the symptoms are improving or getting worse. "
            "Tell me how long you have had these symptoms and whether you "
            "have any severe pain, breathing difficulty, persistent "
            "vomiting, fainting, or other concerning symptoms."
        )

    # --------------------------------------------------------
    # Fever
    # --------------------------------------------------------

    if "fever" in symptoms:

        return (
            "Fever can occur with infections and several other conditions. "
            "For general self-care, rest, drink enough fluids if you can, "
            "and monitor your temperature.\n\n"
            "Tell me how long you have had the fever and whether you also "
            "have symptoms such as cough, sore throat, headache, vomiting, "
            "rash, severe weakness, or breathing difficulty."
        )

    # --------------------------------------------------------
    # Headache
    # --------------------------------------------------------

    if "headache" in symptoms:

        return (
            "Headaches can have many possible causes, including dehydration, "
            "lack of sleep, stress, skipped meals, illness, or migraine. "
            "Resting, drinking enough fluids, and avoiding known triggers "
            "may help with mild symptoms.\n\n"
            "Tell me how long the headache has been present and whether "
            "you have vomiting, vision changes, fever, weakness, confusion, "
            "or another concerning symptom."
        )

    # --------------------------------------------------------
    # Cough
    # --------------------------------------------------------

    if "cough" in symptoms:

        return (
            "A cough can occur with infections, allergies, irritation, or "
            "other respiratory conditions. Staying hydrated and resting "
            "may help with mild symptoms.\n\n"
            "Tell me how long you have been coughing and whether you also "
            "have fever, breathing difficulty, chest pain, or blood in the "
            "cough."
        )

    # --------------------------------------------------------
    # Sore throat
    # --------------------------------------------------------

    if "sore throat" in symptoms:

        return (
            "A sore throat can occur with infections, allergies, or "
            "irritation. Fluids, rest, and warm drinks may provide general "
            "comfort.\n\n"
            "Tell me how long it has been present and whether you also have "
            "fever, cough, difficulty swallowing, or breathing difficulty."
        )

    # --------------------------------------------------------
    # Nausea
    # --------------------------------------------------------

    if "nausea" in symptoms:

        return (
            "Nausea can have several possible causes, including stomach "
            "illness, food-related problems, dehydration, medication effects, "
            "or other conditions.\n\n"
            "Try taking small amounts of fluid if you can tolerate them and "
            "avoid heavy meals until you feel better. Tell me whether you "
            "also have vomiting, stomach pain, fever, diarrhea, or dizziness."
        )

    # --------------------------------------------------------
    # Vomiting
    # --------------------------------------------------------

    if "vomiting" in symptoms:

        return (
            "Vomiting can happen for many reasons. Try to take small sips "
            "of fluid if you can keep them down and rest.\n\n"
            "If vomiting is persistent, you cannot keep fluids down, you "
            "have blood in the vomit, severe abdominal pain, fainting, or "
            "signs of serious dehydration, seek medical attention promptly."
        )

    # --------------------------------------------------------
    # Stomach pain
    # --------------------------------------------------------

    if "stomach pain" in symptoms:

        return (
            "Stomach or abdominal pain can have many possible causes, from "
            "minor digestive problems to conditions that need medical "
            "assessment.\n\n"
            "Tell me where the pain is located, how long you have had it, "
            "how severe it is, and whether you also have vomiting, fever, "
            "diarrhea, bleeding, or worsening pain."
        )

    # --------------------------------------------------------
    # Diarrhea
    # --------------------------------------------------------

    if "diarrhea" in symptoms:

        return (
            "Diarrhea can lead to dehydration, especially if it is frequent. "
            "Try to maintain fluids and rest.\n\n"
            "Tell me how long it has been happening and whether you have "
            "fever, severe abdominal pain, blood in the stool, repeated "
            "vomiting, or signs of dehydration."
        )

    # --------------------------------------------------------
    # Dizziness
    # --------------------------------------------------------

    if "dizziness" in symptoms:

        return (
            "Dizziness can have several possible causes, including "
            "dehydration, lack of food, changes in blood pressure, illness, "
            "or balance-related problems.\n\n"
            "Sit or lie down if you feel unsteady and avoid driving or "
            "operating machinery until you feel better. Tell me when the "
            "dizziness started and whether you also have fainting, severe "
            "headache, weakness, chest pain, or breathing difficulty."
        )

    # --------------------------------------------------------
    # Weakness
    # --------------------------------------------------------

    if "weakness" in symptoms:

        return (
            "Feeling weak can have many possible causes, including illness, "
            "poor sleep, dehydration, not eating enough, stress, or other "
            "medical conditions.\n\n"
            "Tell me how long you have felt weak and whether you also have "
            "fever, dizziness, vomiting, breathing difficulty, or unusual "
            "pain."
        )

    # --------------------------------------------------------
    # Fatigue
    # --------------------------------------------------------

    if "fatigue" in symptoms:

        return (
            "Tiredness or fatigue can be related to sleep, stress, illness, "
            "nutrition, dehydration, or other health conditions.\n\n"
            "Tell me how long you have been feeling unusually tired and "
            "whether you have any other symptoms."
        )

    # --------------------------------------------------------
    # Rash / itching
    # --------------------------------------------------------

    if "rash" in symptoms or "itching" in symptoms:

        return (
            "Skin rashes and itching can have different causes, including "
            "irritation, allergies, infections, or other skin conditions.\n\n"
            "Avoid known irritants and try not to scratch the affected area. "
            "Tell me where the rash is, how long it has been present, and "
            "whether there is swelling, pain, fever, or difficulty breathing."
        )

    # --------------------------------------------------------
    # Body pain
    # --------------------------------------------------------

    if "body pain" in symptoms:

        return (
            "Body aches can occur with infections, physical exertion, "
            "poor sleep, or other conditions.\n\n"
            "Rest and maintain fluids if appropriate. Tell me how long the "
            "body pain has been present and whether you also have fever, "
            "cough, weakness, or another symptom."
        )

    # --------------------------------------------------------
    # Chills
    # --------------------------------------------------------

    if "chills" in symptoms:

        return (
            "Chills can occur with fever or infections, although there can "
            "be other causes as well.\n\n"
            "If possible, check your temperature and tell me whether you "
            "also have fever, cough, headache, body pain, vomiting, or "
            "another symptom."
        )

    # --------------------------------------------------------
    # Chest pain
    # --------------------------------------------------------

    if "chest pain" in symptoms:

        return (
            "Chest pain should not be diagnosed by a chatbot because it can "
            "have many causes, including some that require urgent attention.\n\n"
            "If the pain is severe, persistent, or occurs with difficulty "
            "breathing, fainting, heavy sweating, weakness, or pain spreading "
            "to the arm, jaw, back, or shoulder, seek urgent medical care."
        )

    # --------------------------------------------------------
    # Breathing difficulty
    # --------------------------------------------------------

    if "breathing difficulty" in symptoms:

        return _emergency_response()

    # --------------------------------------------------------
    # General health message
    # --------------------------------------------------------

    return (
        "I can help with general health information, symptoms, possible "
        "causes, self-care, warning signs, and when professional medical "
        "attention may be appropriate.\n\n"
        "Tell me what symptoms you are experiencing, how long they have "
        "been present, and whether they are getting better or worse."
    )


# ============================================================
# ML RESEARCH INFORMATION
# ============================================================

def _research_label_summary(
    label: str,
    confidence: float,
    status: str,
) -> str:
    """
    Research-only description.

    This is returned as metadata and is useful for comparison/analysis.
    It should not normally be shown as the user's medical answer.
    """

    label = str(label or "").strip()

    if not label:
        label = "Unknown"

    confidence_percent = round(_safe_float(confidence) * 100, 2)

    return (
        f"ML model output: {label} | "
        f"confidence: {confidence_percent}% | "
        f"status: {status}"
    )


# ============================================================
# OLD FORMATTER KEPT FOR COMPATIBILITY
# ============================================================

def _format_label_response(
    label: str,
    architecture_name: str,
) -> str:
    """
    Compatibility formatter.

    IMPORTANT:
    This function is not used for ordinary ML chat responses.

    It remains available because other project components may import it.
    """

    label_clean = str(label or "").strip()

    if not label_clean:
        return (
            "The model could not identify a useful pattern from the "
            "information provided. Please provide more details."
        )

    generic_labels = {
        "unknown",
        "unknown_input",
        "health_question",
        "general",
        "general_health",
        "other",
        "uncertain",
    }

    if label_clean.lower() in generic_labels:
        return (
            "The model could not identify a specific health-related "
            "pattern with enough information. Please provide more "
            "details about your symptoms."
        )

    try:

        from chatbot.medical.disease_service import (
            get_disease_information,
        )

        info = get_disease_information(label_clean)

    except Exception:
        info = None

    response_parts = [
        f"Research result from the {architecture_name} architecture:",
        f"Possible model match: {label_clean}.",
        "",
        "This is only a model-generated pattern match and is NOT a "
        "medical diagnosis.",
    ]

    if isinstance(info, dict):

        symptoms = info.get("symptoms")

        precautions = info.get("precautions")

        if symptoms:

            if isinstance(symptoms, (list, tuple)):
                symptoms_text = ", ".join(
                    str(item) for item in symptoms[:8]
                )
            else:
                symptoms_text = str(symptoms)

            response_parts.extend(
                [
                    "",
                    "General associated symptoms:",
                    symptoms_text,
                ]
            )

        if precautions:

            if isinstance(precautions, (list, tuple)):
                precaution_text = "; ".join(
                    str(item) for item in precautions[:6]
                )
            else:
                precaution_text = str(precautions)

            response_parts.extend(
                [
                    "",
                    "General precautions:",
                    precaution_text,
                ]
            )

    return "\n".join(response_parts)


# ============================================================
# RULE-BASED
# ============================================================

def _rule_based(message: str) -> Dict[str, Any]:
    """Run the Rule-Based chatbot."""

    start_time = time.perf_counter()

    try:

        if "rule" not in _BOT_CACHE:

            from chatbot.rule_based.rule_bot import RuleBasedBot

            _BOT_CACHE["rule"] = RuleBasedBot()

        bot = _BOT_CACHE["rule"]

        result = bot.get_response(message)

        elapsed = time.perf_counter() - start_time

        if isinstance(result, dict):

            response = (
                result.get("response")
                or result.get("answer")
                or result.get("text")
                or ""
            )

            confidence = result.get(
                "confidence",
                result.get("score", 0.0),
            )

            score = result.get("score", confidence)

            output = _result_base(
                response=_clean_response(response),
                architecture="rule",
                source=result.get("source", "rule_based"),
                confidence=confidence,
                score=score,
            )

            output.update(result)

        else:

            output = _result_base(
                response=_clean_response(result),
                architecture="rule",
                source="rule_based",
            )

        output["response_time"] = elapsed
        output["architecture"] = "rule"

        return output

    except Exception as exc:

        logger.exception("Rule-Based bot failed")

        elapsed = time.perf_counter() - start_time

        return {
            "response": (
                "I could not process that health question with the "
                "Rule-Based system. Please provide a little more detail."
            ),
            "architecture": "rule",
            "source": "rule_based_error",
            "confidence": 0.0,
            "score": 0.0,
            "response_time": elapsed,
            "error": str(exc),
        }


# ============================================================
# MACHINE LEARNING
# ============================================================

def _machine_learning(message: str) -> Dict[str, Any]:
    """
    Run the Machine Learning architecture.

    Important:
        The ML model's raw prediction is preserved for research.

        Normal user-facing response is generated separately by
        the medical safety/response layer.
    """

    start_time = time.perf_counter()

    try:

        if "ml" not in _BOT_CACHE:

            from chatbot.machine_learning.predict import (
                ClassificationBot,
            )

            _BOT_CACHE["ml"] = ClassificationBot()

        bot = _BOT_CACHE["ml"]

        result = bot.predict_with_confidence(message)

        # ----------------------------------------------------
        # Normalize model result
        # ----------------------------------------------------

        if isinstance(result, dict):

            raw_label = (
                result.get("raw_label")
                or result.get("raw_prediction")
                or result.get("label")
                or result.get("prediction")
                or ""
            )

            display_label = (
                result.get("raw_label_display")
                or result.get("label_display")
                or result.get("display_label")
                or raw_label
                or ""
            )

            safe_label = (
                result.get("safe_label")
                or result.get("final_label")
                or result.get("label")
                or "health_question"
            )

            confidence = _safe_float(
                result.get("confidence", 0.0)
            )

            prediction_status = str(
                result.get(
                    "prediction_status",
                    result.get("status", "unknown"),
                )
            )

            confidence_level = result.get(
                "confidence_level",
                "unknown",
            )

            threshold = _safe_float(
                result.get(
                    "confidence_threshold",
                    0.20,
                ),
                0.20,
            )

            model_is_confident = bool(
                result.get(
                    "is_confident",
                    prediction_status in {
                        "confident",
                        "classification_available",
                    },
                )
            )

        else:

            raw_label = ""
            display_label = ""
            safe_label = "health_question"
            confidence = 0.0
            prediction_status = "unknown"
            confidence_level = "unknown"
            threshold = 0.20
            model_is_confident = False

        # ----------------------------------------------------
        # SAFETY LAYER
        # ----------------------------------------------------

        # Emergency must always override ML prediction.

        if _is_emergency_message(message):

            user_response = _emergency_response()

            response_mode = "emergency"

        # Medication questions must not become disease predictions.

        elif _is_medication_question(message):

            user_response = _medication_response()

            response_mode = "medication"

        # Otherwise create a natural medical response.

        else:

            user_response = _natural_symptom_response(message)

            response_mode = "medical_conversation"

        # ----------------------------------------------------
        # Research information
        # ----------------------------------------------------

        research_summary = _research_label_summary(
            label=raw_label,
            confidence=confidence,
            status=prediction_status,
        )

        # ----------------------------------------------------
        # Response time
        # ----------------------------------------------------

        elapsed = time.perf_counter() - start_time

        output = {
            # User-facing response
            "response": user_response,

            # Architecture
            "architecture": "ml",

            # Source
            "source": "machine_learning",

            # Model information
            "raw_label": raw_label,
            "raw_label_display": display_label,
            "safe_label": safe_label,

            # Confidence
            "confidence": confidence,
            "confidence_percentage": round(
                confidence * 100,
                2,
            ),
            "confidence_level": confidence_level,

            # Status
            "prediction_status": prediction_status,
            "is_confident": model_is_confident,
            "confidence_threshold": threshold,

            # Research output
            "research_summary": research_summary,

            # This can be used by Comparison/Analysis.
            "research_response": _format_label_response(
                display_label or raw_label,
                "Machine Learning",
            ),

            # UI/debug classification
            "response_mode": response_mode,

            # Timing
            "response_time": elapsed,

            # Preserve additional model fields
            "model_result": result,
        }

        # ----------------------------------------------------
        # Preserve any original model keys
        # ----------------------------------------------------

        if isinstance(result, dict):

            for key, value in result.items():

                if key not in output:

                    output[key] = value

        return output

    except Exception as exc:

        logger.exception("Machine Learning bot failed")

        elapsed = time.perf_counter() - start_time

        return {
            "response": _natural_symptom_response(message),
            "architecture": "ml",
            "source": "machine_learning_error",
            "confidence": 0.0,
            "confidence_percentage": 0.0,
            "confidence_level": "unknown",
            "prediction_status": "error",
            "is_confident": False,
            "confidence_threshold": 0.20,
            "raw_label": "",
            "raw_label_display": "",
            "safe_label": "health_question",
            "research_summary": (
                "Machine Learning prediction failed."
            ),
            "research_response": "",
            "response_mode": "error_fallback",
            "response_time": elapsed,
            "error": str(exc),
        }


# ============================================================
# DEEP LEARNING
# ============================================================

def _deep_learning(message: str) -> Dict[str, Any]:
    """
    Run the Deep Learning architecture.

    The exact implementation is delegated to DeepLearningBot.
    """

    start_time = time.perf_counter()

    try:

        if "dl" not in _BOT_CACHE:

            from chatbot.deep_learning.dl_bot import (
                DeepLearningBot,
            )

            _BOT_CACHE["dl"] = DeepLearningBot()

        bot = _BOT_CACHE["dl"]

        result = bot.predict_with_confidence(message)

        if isinstance(result, dict):

            raw_label = (
                result.get("raw_label")
                or result.get("raw_prediction")
                or result.get("label")
                or result.get("prediction")
                or ""
            )

            display_label = (
                result.get("raw_label_display")
                or result.get("label_display")
                or result.get("display_label")
                or raw_label
                or ""
            )

            confidence = _safe_float(
                result.get("confidence", 0.0)
            )

            prediction_status = str(
                result.get(
                    "prediction_status",
                    result.get("status", "unknown"),
                )
            )

            confidence_level = result.get(
                "confidence_level",
                "unknown",
            )

            threshold = _safe_float(
                result.get(
                    "confidence_threshold",
                    0.20,
                ),
                0.20,
            )

            model_is_confident = bool(
                result.get(
                    "is_confident",
                    prediction_status in {
                        "confident",
                        "classification_available",
                    },
                )
            )

        else:

            raw_label = ""
            display_label = ""
            confidence = 0.0
            prediction_status = "unknown"
            confidence_level = "unknown"
            threshold = 0.20
            model_is_confident = False

        # ----------------------------------------------------
        # Safety layer
        # ----------------------------------------------------

        if _is_emergency_message(message):

            user_response = _emergency_response()

            response_mode = "emergency"

        elif _is_medication_question(message):

            user_response = _medication_response()

            response_mode = "medication"

        else:

            user_response = _natural_symptom_response(message)

            response_mode = "medical_conversation"

        elapsed = time.perf_counter() - start_time

        output = {
            "response": user_response,
            "architecture": "dl",
            "source": "deep_learning",

            "raw_label": raw_label,
            "raw_label_display": display_label,

            "confidence": confidence,
            "confidence_percentage": round(
                confidence * 100,
                2,
            ),
            "confidence_level": confidence_level,

            "prediction_status": prediction_status,
            "is_confident": model_is_confident,
            "confidence_threshold": threshold,

            "response_mode": response_mode,

            "research_summary": _research_label_summary(
                label=raw_label,
                confidence=confidence,
                status=prediction_status,
            ),

            "research_response": _format_label_response(
                display_label or raw_label,
                "Deep Learning",
            ),

            "response_time": elapsed,

            "model_result": result,
        }

        if isinstance(result, dict):

            for key, value in result.items():

                if key not in output:

                    output[key] = value

        return output

    except Exception as exc:

        logger.exception("Deep Learning bot failed")

        elapsed = time.perf_counter() - start_time

        return {
            "response": _natural_symptom_response(message),
            "architecture": "dl",
            "source": "deep_learning_error",
            "confidence": 0.0,
            "confidence_percentage": 0.0,
            "confidence_level": "unknown",
            "prediction_status": "error",
            "is_confident": False,
            "confidence_threshold": 0.20,
            "raw_label": "",
            "raw_label_display": "",
            "response_mode": "error_fallback",
            "research_summary": (
                "Deep Learning prediction failed."
            ),
            "research_response": "",
            "response_time": elapsed,
            "error": str(exc),
        }


# ============================================================
# RAG / LLM
# ============================================================

def _rag_llm(message: str) -> Dict[str, Any]:
    """
    Run the existing RAG/LLM module if available.

    This architecture is preserved for compatibility.
    """

    start_time = time.perf_counter()

    try:

        rag_module = None

        # ----------------------------------------------------
        # Try existing RAG implementations
        # ----------------------------------------------------

        candidates = [
            (
                "chatbot.rag_based.rag_bot",
                "RAGBot",
            ),
            (
                "chatbot.rag_based.rag_bot",
                "RagBot",
            ),
            (
                "chatbot.rag_based.rag_bot",
                "RAGBasedBot",
            ),
        ]

        for module_name, class_name in candidates:

            try:

                module = __import__(
                    module_name,
                    fromlist=[class_name],
                )

                bot_class = getattr(
                    module,
                    class_name,
                    None,
                )

                if bot_class is not None:

                    rag_module = bot_class()

                    break

            except Exception:
                continue

        # ----------------------------------------------------
        # If no RAG bot is available
        # ----------------------------------------------------

        if rag_module is None:

            elapsed = time.perf_counter() - start_time

            return {
                "response": (
                    "The RAG-based architecture is not available "
                    "in the current local configuration."
                ),
                "architecture": "rag",
                "source": "rag_unavailable",
                "confidence": 0.0,
                "score": 0.0,
                "response_time": elapsed,
                "prediction_status": "unavailable",
            }

        # ----------------------------------------------------
        # Run response
        # ----------------------------------------------------

        if hasattr(rag_module, "get_response"):

            result = rag_module.get_response(message)

        elif hasattr(rag_module, "respond"):

            result = rag_module.respond(message)

        elif hasattr(rag_module, "predict"):

            result = rag_module.predict(message)

        else:

            raise AttributeError(
                "RAG bot does not expose get_response(), "
                "respond(), or predict()."
            )

        elapsed = time.perf_counter() - start_time

        if isinstance(result, dict):

            response = (
                result.get("response")
                or result.get("answer")
                or result.get("text")
                or ""
            )

            output = {
                "response": _clean_response(response),
                "architecture": "rag",
                "source": result.get(
                    "source",
                    "rag",
                ),
                "confidence": _safe_float(
                    result.get("confidence", 0.0)
                ),
                "score": _safe_float(
                    result.get(
                        "score",
                        result.get("confidence", 0.0),
                    )
                ),
                "response_time": elapsed,
            }

            output.update(result)

            return output

        return {
            "response": _clean_response(result),
            "architecture": "rag",
            "source": "rag",
            "confidence": 0.0,
            "score": 0.0,
            "response_time": elapsed,
        }

    except Exception as exc:

        logger.exception("RAG/LLM bot failed")

        elapsed = time.perf_counter() - start_time

        return {
            "response": (
                "The RAG-based architecture could not process "
                "this question at the moment."
            ),
            "architecture": "rag",
            "source": "rag_error",
            "confidence": 0.0,
            "score": 0.0,
            "response_time": elapsed,
            "prediction_status": "error",
            "error": str(exc),
        }


# ============================================================
# PUBLIC BOT DISPATCHER
# ============================================================

def get_bot_response(
    bot_type: str,
    message: str,
) -> Dict[str, Any]:
    """
    Main bot dispatcher.

    Supported:
        rule
        ml
        dl
        rag
        hybrid

    Hybrid is intentionally delegated to ConversationManager.
    """

    normalized_type = _normalize_text(bot_type)

    aliases = {
        "rule_based": "rule",
        "rule-based": "rule",
        "rule": "rule",

        "machine_learning": "ml",
        "machine-learning": "ml",
        "machine learning": "ml",
        "ml": "ml",

        "deep_learning": "dl",
        "deep-learning": "dl",
        "deep learning": "dl",
        "dl": "dl",

        "rag_based": "rag",
        "rag-based": "rag",
        "rag": "rag",

        "hybrid": "hybrid",
    }

    normalized_type = aliases.get(
        normalized_type,
        normalized_type,
    )

    message = str(message or "").strip()

    # --------------------------------------------------------
    # Empty input
    # --------------------------------------------------------

    if not message:

        return {
            "response": (
                "Please enter a health-related question or describe "
                "your symptoms."
            ),
            "architecture": normalized_type or "unknown",
            "source": "input_validation",
            "confidence": 0.0,
            "score": 0.0,
            "prediction_status": "empty_input",
        }

    # --------------------------------------------------------
    # Dispatch
    # --------------------------------------------------------

    if normalized_type == "rule":

        return _rule_based(message)

    if normalized_type == "ml":

        return _machine_learning(message)

    if normalized_type == "dl":

        return _deep_learning(message)

    if normalized_type == "rag":

        return _rag_llm(message)

    if normalized_type == "hybrid":

        return {
            "response": (
                "Hybrid responses are managed by ConversationManager. "
                "Please use ConversationManager for the hybrid chat flow."
            ),
            "architecture": "hybrid",
            "source": "conversation_manager",
            "confidence": 0.0,
            "score": 0.0,
            "prediction_status": "delegated",
        }

    return {
        "response": (
            "The requested chatbot architecture is not available. "
            "Please use Rule-Based, Machine Learning, Deep Learning, "
            "or Hybrid chat."
        ),
        "architecture": normalized_type,
        "source": "unknown_architecture",
        "confidence": 0.0,
        "score": 0.0,
        "prediction_status": "unknown_architecture",
    }


# ============================================================
# ALL ARCHITECTURES
# ============================================================

def get_all_bot_responses(
    message: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Run the same question through the research architectures.

    Hybrid is intentionally excluded because ConversationManager
    builds Hybrid from Rule + ML + DL.

    This is useful for Comparison/Evaluation.
    """

    results: Dict[str, Dict[str, Any]] = {}

    for architecture in ARCHITECTURES:

        try:

            results[architecture] = get_bot_response(
                architecture,
                message,
            )

        except Exception as exc:

            logger.exception(
                "Architecture failed: %s",
                architecture,
            )

            results[architecture] = {
                "response": (
                    f"{architecture.upper()} architecture "
                    "failed to process the question."
                ),
                "architecture": architecture,
                "source": "architecture_error",
                "confidence": 0.0,
                "score": 0.0,
                "prediction_status": "error",
                "error": str(exc),
            }

    return results


# ============================================================
# ARCHITECTURE STATUS CHECK
# ============================================================

def check_all_architectures_loaded() -> Dict[str, Any]:
    """
    Check whether the available architecture implementations
    can process a basic health question.
    """

    test_message = "I have fever"

    results: Dict[str, Any] = {}

    for architecture in ARCHITECTURES:

        start_time = time.perf_counter()

        try:

            result = get_bot_response(
                architecture,
                test_message,
            )

            elapsed = time.perf_counter() - start_time

            results[architecture] = {
                "loaded": True,
                "working": bool(
                    result.get("response")
                ),
                "response_time": elapsed,
                "source": result.get(
                    "source",
                    architecture,
                ),
                "error": None,
            }

        except Exception as exc:

            elapsed = time.perf_counter() - start_time

            results[architecture] = {
                "loaded": False,
                "working": False,
                "response_time": elapsed,
                "source": architecture,
                "error": str(exc),
            }

    return results


# ============================================================
# BOT REGISTRY CLASS
# ============================================================

class BotRegistry:
    """
    Object-oriented wrapper around the registry functions.

    This keeps compatibility with code that expects:

        registry = BotRegistry()

        registry.get_bot_response(...)
    """

    def __init__(self):

        self.architectures = list(ARCHITECTURES)

    def get_bot_response(
        self,
        bot_type: str,
        message: str,
    ) -> Dict[str, Any]:

        return get_bot_response(
            bot_type,
            message,
        )

    def get_all_bot_responses(
        self,
        message: str,
    ) -> Dict[str, Dict[str, Any]]:

        return get_all_bot_responses(message)

    def check_all_architectures_loaded(
        self,
    ) -> Dict[str, Any]:

        return check_all_architectures_loaded()

    def clear_cache(self) -> None:

        _BOT_CACHE.clear()

    def get_architectures(self) -> list[str]:

        return list(self.architectures)


# ============================================================
# OPTIONAL CACHE CONTROL
# ============================================================

def clear_bot_cache() -> None:
    """Clear all cached bot instances."""

    _BOT_CACHE.clear()


# ============================================================
# CLI TEST
# ============================================================

def _print_result(
    architecture: str,
    result: Dict[str, Any],
) -> None:

    print("\n" + "=" * 70)

    print(
        f"{architecture.upper()} RESULT"
    )

    print("=" * 70)

    print(
        "Response:"
    )

    print(
        result.get(
            "response",
            "",
        )
    )

    print(
        "\nArchitecture:",
        result.get(
            "architecture",
            "",
        ),
    )

    print(
        "Source:",
        result.get(
            "source",
            "",
        ),
    )

    print(
        "Confidence:",
        result.get(
            "confidence",
            0.0,
        ),
    )

    if "raw_label" in result:

        print(
            "Raw ML/DL label:",
            result.get(
                "raw_label",
                "",
            ),
        )

    if "prediction_status" in result:

        print(
            "Prediction status:",
            result.get(
                "prediction_status",
                "",
            ),
        )

    if "response_time" in result:

        print(
            "Response time:",
            round(
                float(
                    result.get(
                        "response_time",
                        0.0,
                    )
                ),
                4,
            ),
            "seconds",
        )


def run_test() -> None:
    """
    Basic registry test.

    This test intentionally checks both normal conversational
    behavior and research metadata.
    """

    test_messages = [
        "I have fever",
        "I have fever and headache",
        "I have itching and skin rash",
        "I have chest pain",
        "Which disease could this be if I have fever and headache?",
        "Which medicine should I take for fever?",
    ]

    print("\n")
    print("=" * 70)
    print("MEDICHAT BOT REGISTRY TEST")
    print("=" * 70)

    for message in test_messages:

        print("\n")
        print("-" * 70)
        print(
            "USER:",
            message,
        )
        print("-" * 70)

        result = get_bot_response(
            "ml",
            message,
        )

        _print_result(
            "Machine Learning",
            result,
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    run_test()