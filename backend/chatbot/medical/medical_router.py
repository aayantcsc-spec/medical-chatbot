"""
medical_router.py

Central medical processing controller.

FIX NOTE (previous version):
The previous file was named `medical_rotuer.py` (typo), which is
why every import of `chatbot.medical.medical_router` failed with:

    No module named 'chatbot.medical.medical_router'

On top of the filename typo, the old MedicalRouter imported
classes that don't exist:

    from chatbot.medical.disease_service import DiseaseService
    from chatbot.medical.risk_detector import RiskDetector
    from chatbot.medical.emergency_detector import EmergencyDetector
    from chatbot.medical.symptom_analyzer import SymptomAnalyzer

disease_service.py, risk_detector.py, emergency_detector.py and
symptom_analyzer.py only define module-level FUNCTIONS (e.g.
`answer_disease_query()`, `check_risk()`, `check_emergency()`,
`analyze_symptoms()`) -- there are no such classes in those files.
So even with the filename fixed, every one of those imports would
have raised ImportError and MedicalRouter would have silently run
with everything disabled.

This version wires the router to the REAL functions that already
exist in those files (left untouched -- they work fine on their
own, as their own __main__ tests show), plus the new MedicalQA
class in medical_qa.py.

Priority order (per project spec):
    1. Emergency detection            (always first)
    2. Risk detection
    3. Disease-specific question       (e.g. "treatment for fever")
    4. Medical Q&A dataset lookup
    5. Symptom analysis
"""

import os
import re
import sys
import time


# ============================================================
# PROJECT ROOT
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# IMPORT MEDICAL MODULES (each optional / fault-tolerant)
# ============================================================

try:
    from chatbot.medical.emergency_detector import check_emergency
except Exception as error:
    print("[MEDICAL ROUTER] emergency_detector import error:", error)
    check_emergency = None

try:
    from chatbot.medical.risk_detector import check_risk
except Exception as error:
    print("[MEDICAL ROUTER] risk_detector import error:", error)
    check_risk = None

try:
    from chatbot.medical.symptom_analyzer import analyze_symptoms
except Exception as error:
    print("[MEDICAL ROUTER] symptom_analyzer import error:", error)
    analyze_symptoms = None

try:
    from chatbot.medical.disease_service import answer_disease_query
except Exception as error:
    print("[MEDICAL ROUTER] disease_service import error:", error)
    answer_disease_query = None

try:
    from chatbot.medical.medical_qa import MedicalQA
except Exception as error:
    print("[MEDICAL ROUTER] medical_qa import error:", error)
    MedicalQA = None


# ============================================================
# QUESTION DETECTION
#
# Bare symptom mentions ("headache", "2 days", "getting worse")
# are intentionally NOT answered here -- those are handled by
# ConversationManager's own follow-up/context engine in
# chat_manager.py. This router focuses on explicit medical
# QUESTIONS ("What is the treatment for fever?", "How can I
# prevent malaria?"), which is exactly the case that was
# previously being swallowed by the follow-up logic.
# ============================================================

QUESTION_MARKERS = [
    "what", "how", "who", "why", "when", "which",
    "can", "is", "are", "does", "do", "should",
    "treatment", "treat", "cure", "medicine", "medication",
    "therapy", "prevent", "prevention", "avoid",
    "risk", "risk factor", "susceptible", "diagnose",
    "diagnosis", "cause", "causes", "symptom", "symptoms",
]

# A generic question word ("can", "how", "is"...) is not enough
# on its own -- "can you help me with something" would otherwise
# be misrouted into the medical dataset search. At least one
# medically-relevant word must also be present.
MEDICAL_TOPIC_WORDS = [
    "fever", "cough", "headache", "pain", "rash", "itching",
    "vomiting", "nausea", "diarrhea", "diarrhoea", "dizziness",
    "fatigue", "weakness", "breathing", "breathlessness",
    "disease", "illness", "condition", "symptom", "symptoms",
    "treatment", "treat", "medicine", "medication", "diagnosis",
    "diagnostic", "test", "prevention", "prevent", "risk",
    "infection", "virus", "bacteria", "doctor", "hospital",
    "health", "medical", "heart", "lung", "brain", "stomach",
    "kidney", "liver", "blood", "chest", "throat",
    "malaria", "dengue", "diabetes", "asthma", "covid",
    "influenza", "flu", "pneumonia", "hypertension", "migraine",
    "cancer", "allergy", "allergic",
]


def _looks_like_question(text):

    normalized = str(text).lower().strip()

    has_medical_word = any(
        re.search(r"\b" + re.escape(word) + r"\b", normalized)
        for word in MEDICAL_TOPIC_WORDS
    )

    if not has_medical_word:
        return False

    if normalized.endswith("?"):
        return True

    for marker in QUESTION_MARKERS:

        pattern = r"\b" + re.escape(marker) + r"\b"

        if re.search(pattern, normalized):
            return True

    return False


# ============================================================
# MEDICAL ROUTER
# ============================================================

class MedicalRouter:

    def __init__(self):

        print()
        print("=" * 70)
        print("INITIALIZING MEDICAL ROUTER")
        print("=" * 70)

        self.emergency_available = check_emergency is not None
        self.risk_available = check_risk is not None
        self.symptom_available = analyze_symptoms is not None
        self.disease_available = answer_disease_query is not None

        self.medical_qa = None

        if MedicalQA is not None:

            try:
                self.medical_qa = MedicalQA()
                print("[OK] Medical QA loaded")
            except Exception as error:
                print("[ERROR] Medical QA:", error)

        print("[OK] Emergency Detector" if self.emergency_available else "[UNAVAILABLE] Emergency Detector")
        print("[OK] Risk Detector" if self.risk_available else "[UNAVAILABLE] Risk Detector")
        print("[OK] Symptom Analyzer" if self.symptom_available else "[UNAVAILABLE] Symptom Analyzer")
        print("[OK] Disease Service" if self.disease_available else "[UNAVAILABLE] Disease Service")

        print("=" * 70)
        print("MEDICAL ROUTER READY")
        print("=" * 70)
        print()

    # ========================================================
    # MAIN ROUTER
    # ========================================================

    def route(self, query):

        start_time = time.time()

        query = str(query or "").strip()

        def finish(response, source, score, extra=None):

            result = {
                "response": response,
                "source": source,
                "score": score,
                "response_time": round(time.time() - start_time, 4),
                "emergency": source == "emergency_detector",
                "risk": extra.get("risk") if extra else None,
            }

            if extra:
                result.update({k: v for k, v in extra.items() if k != "risk"})

            return result

        if not query:

            return finish(
                "Please enter a medical or health-related question.",
                "medical_router",
                0
            )

        # ====================================================
        # 1. EMERGENCY -- ALWAYS CHECKED FIRST
        # ====================================================

        if self.emergency_available:

            try:

                emergency_result = check_emergency(query)

                if emergency_result.get("is_emergency"):

                    return finish(
                        emergency_result.get("response"),
                        "emergency_detector",
                        100,
                        {"risk": emergency_result}
                    )

            except Exception as error:
                print("[MEDICAL ROUTER] [EMERGENCY DETECTOR] error:", error)

        # ====================================================
        # 2. RISK DETECTION (informational, attached to answer)
        # ====================================================

        risk_result = None

        if self.risk_available:

            try:
                risk_result = check_risk(query)
            except Exception as error:
                print("[MEDICAL ROUTER] [RISK DETECTOR] error:", error)

        # Only bare "question" style queries proceed past this
        # point. Plain symptom mentions / short follow-ups are
        # deliberately left to ConversationManager's context
        # engine so we don't fight over the same turn.

        if not _looks_like_question(query):

            return finish(None, "medical_router", 0, {"risk": risk_result})

        # ====================================================
        # 3. DISEASE-SPECIFIC QUESTION
        #    e.g. "treatment for fever", "prevent malaria"
        # ====================================================

        if self.disease_available:

            try:

                disease_result = answer_disease_query(query)

                if disease_result and disease_result.get("found"):

                    response = disease_result.get("response")

                    if risk_result and risk_result.get("risk_level") == "HIGH":

                        response += (
                            "\n\n⚠️ Your message may also indicate a "
                            "higher-risk situation. Consider seeking "
                            "medical evaluation promptly."
                        )

                    return finish(
                        response,
                        "disease_service",
                        80,
                        {"risk": risk_result}
                    )

            except Exception as error:
                print("[MEDICAL ROUTER] [DISEASE SERVICE] error:", error)

        # ====================================================
        # 4. MEDICAL Q&A DATASET
        #    e.g. "What is the treatment for fever?"
        # ====================================================

        if self.medical_qa is not None:

            try:

                qa_result = self.medical_qa.answer(query)

                if qa_result:

                    response = qa_result["response"]

                    if risk_result and risk_result.get("risk_level") == "HIGH":

                        response += (
                            "\n\n⚠️ Your message may also indicate a "
                            "higher-risk situation. Consider seeking "
                            "medical evaluation promptly."
                        )

                    return finish(
                        response,
                        "medical_qa",
                        qa_result["score"],
                        {"risk": risk_result}
                    )

            except Exception as error:
                print("[MEDICAL ROUTER] [MEDICAL QA] error:", error)

        # ====================================================
        # 5. SYMPTOM ANALYSIS (fallback for "symptoms of X")
        # ====================================================

        if self.symptom_available:

            try:

                symptom_result = analyze_symptoms(query)

                conditions = symptom_result.get("possible_conditions") if symptom_result else None

                if conditions:

                    lines = [
                        f"• {c['disease']}"
                        for c in conditions[:5]
                        if isinstance(c, dict) and c.get("disease")
                    ]

                    if lines:

                        response = (
                            "Based on the symptom dataset, conditions "
                            "associated with what you described "
                            "include:\n\n"
                            + "\n".join(lines)
                            + "\n\nThese are dataset-based associations "
                            "only and should not be interpreted as a "
                            "diagnosis."
                        )

                        return finish(
                            response,
                            "symptom_analyzer",
                            70,
                            {"risk": risk_result}
                        )

            except Exception as error:
                print("[MEDICAL ROUTER] [SYMPTOM ANALYZER] error:", error)

        # ====================================================
        # NOTHING CONFIDENT -- let the caller fall back
        # ====================================================

        return finish(None, "medical_router", 0, {"risk": risk_result})

    # ========================================================
    # PROCESS
    #
    # Compatibility method: chat_manager.py calls
    # `self.medical_router.process(message)` and expects either
    # None or a dict with response/source/score.
    # ========================================================

    def process(self, message):

        result = self.route(message)

        if not result or not result.get("response"):
            return None

        return {
            "response": result["response"],
            "source": result["source"],
            "score": result["score"],
        }

    # ========================================================
    # CHAT (simple convenience)
    # ========================================================

    def chat(self, query):

        result = self.route(query)

        return result.get("response")


# ============================================================
# MODULE-LEVEL CONVENIENCE
#
# medical_analyzer.py expects a `route_medical_query` function.
# ============================================================

_default_router = None


def _get_default_router():

    global _default_router

    if _default_router is None:
        _default_router = MedicalRouter()

    return _default_router


def route_medical_query(query):
    """
    Convenience wrapper used by medical_analyzer.py.
    Returns the same structure as MedicalRouter.route().
    """

    router = _get_default_router()

    result = router.route(query)

    # medical_analyzer.py expects success / route / risk_level / data
    risk = result.get("risk") or {}

    risk_level = "LOW"

    if result.get("emergency"):
        risk_level = "EMERGENCY"
    elif isinstance(risk, dict):
        risk_level = risk.get("risk_level", "LOW")

    return {
        "success": bool(result.get("response")),
        "route": result.get("source", "general"),
        "risk_level": risk_level,
        "response": result.get("response"),
        "data": None,
        "risk": risk,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    router = MedicalRouter()

    test_questions = [
        "What are the symptoms of malaria?",
        "What is the treatment for fever?",
        "How can I prevent malaria?",
        "What are the risk factors for diabetes?",
        "I have chest pain and difficulty breathing",
        "I have fever",
        "2 days",
        "headache",
        "getting worse",
    ]

    for question in test_questions:

        print()
        print("-" * 70)
        print("USER:", question)
        print("-" * 70)

        result = router.route(question)

        print("SOURCE:", result.get("source"))
        print("SCORE:", result.get("score"))
        print("RESPONSE:", result.get("response"))