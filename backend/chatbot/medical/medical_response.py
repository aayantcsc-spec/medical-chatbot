import os
import sys


# ============================================================
# PROJECT ROOT
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# RESPONSE GENERATOR
# ============================================================

class MedicalResponse:

    def __init__(self):

        print(
            "Medical Response initialized successfully!"
        )

    # ========================================================
    # MAIN RESPONSE FUNCTION
    # ========================================================

    def generate(self, analysis):

        if not analysis:

            return (
                "I couldn't process your question. "
                "Please try asking your health question "
                "in a little more detail."
            )

        route = analysis.get(
            "route",
            "general"
        )

        risk_level = analysis.get(
            "risk_level",
            "LOW"
        )

        response = analysis.get(
            "response"
        )

        data = analysis.get(
            "data"
        )

        # ====================================================
        # EMERGENCY
        # ====================================================

        if route == "emergency":

            return self._emergency_response(
                response
            )

        # ====================================================
        # GREETING
        # ====================================================

        if route == "greeting":

            return (
                "Hello! 👋\n\n"
                "I'm your health information assistant. "
                "You can ask me about symptoms, diseases, "
                "medical conditions, precautions, or "
                "general health questions."
            )

        # ====================================================
        # GOODBYE
        # ====================================================

        if route == "goodbye":

            return (
                "Take care! 👋\n\n"
                "If you have another health-related "
                "question, feel free to ask."
            )

        # ====================================================
        # SYMPTOM RESPONSE
        # ====================================================

        if route == "symptom":

            return self._symptom_response(
                data,
                risk_level
            )

        # ====================================================
        # DISEASE RESPONSE
        # ====================================================

        if route == "disease":

            return self._disease_response(
                data,
                risk_level
            )

        # ====================================================
        # MEDICAL Q&A RESPONSE
        # ====================================================

        if route == "medical_qa":

            return self._qa_response(
                data,
                risk_level
            )

        # ====================================================
        # FALLBACK
        # ====================================================

        if response:

            return str(response)

        return (
            "I couldn't find enough information "
            "to answer that question reliably."
        )

    # ========================================================
    # EMERGENCY RESPONSE
    # ========================================================

    def _emergency_response(
        self,
        response
    ):

        result = (
            "⚠️ URGENT MEDICAL ATTENTION\n\n"
        )

        if response:

            result += str(
                response
            )

        else:

            result += (
                "Your message may describe a "
                "potentially serious situation. "
                "Please seek urgent professional "
                "medical care."
            )

        return result

    # ========================================================
    # SYMPTOM RESPONSE
    # ========================================================

    def _symptom_response(
        self,
        data,
        risk_level
    ):

        if not data:

            return (
                "I couldn't identify enough information "
                "from the symptoms you provided."
            )

        symptoms = data.get(
            "symptoms",
            []
        )

        conditions = data.get(
            "possible_conditions",
            []
        )

        response_parts = []

        response_parts.append(
            "🩺 Symptom Analysis"
        )

        # ----------------------------------------------------
        # Symptoms
        # ----------------------------------------------------

        if symptoms:

            response_parts.append(
                "\nSymptoms I identified:"
            )

            for symptom in symptoms:

                response_parts.append(
                    f"• {symptom}"
                )

        # ----------------------------------------------------
        # Possible conditions
        # ----------------------------------------------------

        if conditions:

            response_parts.append(
                "\nPossible matching conditions:"
            )

            for condition in conditions[:5]:

                if isinstance(
                    condition,
                    dict
                ):

                    disease = condition.get(
                        "disease",
                        "Unknown"
                    )

                    score = condition.get(
                        "score"
                    )

                    if score is not None:

                        response_parts.append(
                            f"• {disease}"
                        )

                    else:

                        response_parts.append(
                            f"• {disease}"
                        )

                else:

                    response_parts.append(
                        f"• {condition}"
                    )

        else:

            response_parts.append(
                "\nI couldn't find a strong "
                "matching condition in the "
                "current dataset."
            )

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        if risk_level == "HIGH":

            response_parts.append(
                "\n⚠️ Risk indication:"
            )

            response_parts.append(
                "Some details may require prompt "
                "medical evaluation, especially if "
                "your symptoms are severe or worsening."
            )

        elif risk_level == "MODERATE":

            response_parts.append(
                "\nRisk indication:"
            )

            response_parts.append(
                "Monitor your symptoms. If they "
                "persist or become worse, consider "
                "consulting a healthcare professional."
            )

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        response_parts.append(
            "\n⚠️ Important:"
        )

        response_parts.append(
            "The conditions listed above are "
            "possible matches based on the "
            "information provided. They are not "
            "a confirmed diagnosis."
        )

        return "\n".join(
            response_parts
        )

    # ========================================================
    # DISEASE RESPONSE
    # ========================================================

    def _disease_response(
        self,
        data,
        risk_level
    ):

        if not data:

            return (
                "I couldn't find detailed information "
                "about that condition."
            )

        disease = data.get(
            "disease",
            "the condition"
        )

        symptoms = data.get(
            "symptoms",
            []
        )

        precautions = data.get(
            "precautions",
            []
        )

        response_parts = []

        response_parts.append(
            f"🩺 Information about {disease}"
        )

        # ----------------------------------------------------
        # Symptoms
        # ----------------------------------------------------

        if symptoms:

            response_parts.append(
                "\nCommonly associated symptoms:"
            )

            for symptom in symptoms[:10]:

                response_parts.append(
                    f"• {symptom}"
                )

        # ----------------------------------------------------
        # Precautions
        # ----------------------------------------------------

        if precautions:

            response_parts.append(
                "\nGeneral precautions:"
            )

            for precaution in precautions[:10]:

                response_parts.append(
                    f"• {precaution}"
                )

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        if risk_level == "HIGH":

            response_parts.append(
                "\n⚠️ Because your message may "
                "indicate higher risk, consider "
                "prompt medical evaluation."
            )

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        response_parts.append(
            "\n⚠️ Important:"
        )

        response_parts.append(
            "This information is for general "
            "educational purposes and does not "
            "confirm a diagnosis or replace advice "
            "from a qualified healthcare professional."
        )

        return "\n".join(
            response_parts
        )

    # ========================================================
    # MEDICAL Q&A RESPONSE
    # ========================================================

    def _qa_response(
        self,
        data,
        risk_level
    ):

        if not data:

            return (
                "I couldn't find a sufficiently "
                "relevant answer in the medical "
                "knowledge base."
            )

        answer = data.get(
            "answer"
        )

        question_type = data.get(
            "qtype"
        )

        if not answer:

            return (
                "I found a related medical question "
                "but couldn't retrieve its answer."
            )

        response_parts = []

        response_parts.append(
            "🩺 Medical Information"
        )

        response_parts.append(
            "\n" + str(answer)
        )

        # ----------------------------------------------------
        # Question category
        # ----------------------------------------------------

        if question_type:

            response_parts.append(
                f"\n\nTopic: {question_type}"
            )

        # ----------------------------------------------------
        # Risk information
        # ----------------------------------------------------

        if risk_level == "HIGH":

            response_parts.append(
                "\n\n⚠️ Based on your wording, "
                "consider seeking medical evaluation "
                "promptly if your symptoms are severe "
                "or worsening."
            )

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        response_parts.append(
            "\n\n⚠️ Important:"
        )

        response_parts.append(
            "This information is provided for "
            "general educational purposes and "
            "should not be treated as a personal "
            "diagnosis."
        )

        return "".join(
            response_parts
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def generate_medical_response(
    analysis
):

    responder = MedicalResponse()

    return responder.generate(
        analysis
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("             MEDICAL RESPONSE TEST")
    print("=" * 70)

    responder = MedicalResponse()

    # --------------------------------------------------------
    # Test symptom response
    # --------------------------------------------------------

    symptom_analysis = {

        "route": "symptom",

        "risk_level": "LOW",

        "data": {

            "symptoms": [
                "fever",
                "headache",
                "cough"
            ],

            "possible_conditions": [

                {
                    "disease": "Influenza",
                    "score": 3
                },

                {
                    "disease": "Common Cold",
                    "score": 2
                }
            ]
        }
    }

    print("\n")
    print("-" * 70)
    print("SYMPTOM RESPONSE")
    print("-" * 70)

    print(
        responder.generate(
            symptom_analysis
        )
    )

    # --------------------------------------------------------
    # Test disease response
    # --------------------------------------------------------

    disease_analysis = {

        "route": "disease",

        "risk_level": "LOW",

        "data": {

            "disease": "Dengue",

            "symptoms": [
                "fever",
                "headache",
                "muscle pain"
            ],

            "precautions": [
                "Drink adequate fluids",
                "Rest adequately"
            ]
        }
    }

    print("\n")
    print("-" * 70)
    print("DISEASE RESPONSE")
    print("-" * 70)

    print(
        responder.generate(
            disease_analysis
        )
    )

    # --------------------------------------------------------
    # Test emergency response
    # --------------------------------------------------------

    emergency_analysis = {

        "route": "emergency",

        "risk_level": "EMERGENCY",

        "response": (
            "Your message contains symptoms "
            "that may require urgent medical attention."
        )
    }

    print("\n")
    print("-" * 70)
    print("EMERGENCY RESPONSE")
    print("-" * 70)

    print(
        responder.generate(
            emergency_analysis
        )
    )

    print("\n")
    print("=" * 70)
    print("                 TEST COMPLETE")
    print("=" * 70)