import re


# ============================================================
# EMERGENCY KEYWORDS / PHRASES
# ============================================================

EMERGENCY_PATTERNS = {

    "chest_pain": [
        "severe chest pain",
        "crushing chest pain",
        "chest pain and sweating",
        "chest pain and nausea",
        "chest pressure",
        "pressure in chest",
        "tightness in chest",
        "heavy chest",
    ],

    "breathing_difficulty": [
        "difficulty breathing",
        "trouble breathing",
        "cannot breathe",
        "can't breathe",
        "unable to breathe",
        "severe shortness of breath",
        "severe breathlessness",
        "gasping for air",
    ],

    "loss_of_consciousness": [
        "lost consciousness",
        "loss of consciousness",
        "passed out",
        "fainted",
        "unconscious",
        "not responding",
        "unresponsive",
    ],

    "stroke_warning": [
        "face drooping",
        "facial drooping",
        "slurred speech",
        "cannot speak",
        "can't speak",
        "sudden weakness",
        "sudden numbness",
        "one sided weakness",
        "one sided numbness",
        "sudden confusion",
    ],

    "severe_bleeding": [
        "severe bleeding",
        "heavy bleeding",
        "uncontrolled bleeding",
        "bleeding won't stop",
        "blood loss",
    ],

    "severe_allergic_reaction": [
        "anaphylaxis",
        "severe allergic reaction",
        "throat swelling",
        "tongue swelling",
        "face swelling and difficulty breathing",
        "cannot swallow and breathing difficulty",
    ],

    "severe_seizure": [
        "seizure lasting",
        "continuous seizure",
        "repeated seizures",
        "severe seizure",
        "convulsions that won't stop",
    ],

    "severe_injury": [
        "severe head injury",
        "serious head injury",
        "major accident",
        "severe injury",
        "serious injury",
    ],

    "self_harm_emergency": [
        "I want to kill myself",
        "I want to die",
        "I am going to kill myself",
        "I might hurt myself",
        "I want to hurt myself",
        "suicide attempt",
    ]
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s']",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# DETECT EMERGENCY
# ============================================================

def detect_emergency(query):

    normalized_query = normalize_text(
        query
    )

    if not normalized_query:
        return {
            "is_emergency": False,
            "category": None,
            "matched_patterns": []
        }

    detected_categories = []

    matched_patterns = []

    for category, patterns in EMERGENCY_PATTERNS.items():

        for pattern in patterns:

            normalized_pattern = normalize_text(
                pattern
            )

            if normalized_pattern in normalized_query:

                if category not in detected_categories:

                    detected_categories.append(
                        category
                    )

                if pattern not in matched_patterns:

                    matched_patterns.append(
                        pattern
                    )

    if detected_categories:

        return {
            "is_emergency": True,
            "category": detected_categories[0],
            "categories": detected_categories,
            "matched_patterns": matched_patterns
        }

    return {
        "is_emergency": False,
        "category": None,
        "categories": [],
        "matched_patterns": []
    }


# ============================================================
# EMERGENCY RESPONSE
# ============================================================

def emergency_response(emergency_result):

    if not emergency_result.get(
        "is_emergency",
        False
    ):

        return None

    category = emergency_result.get(
        "category"
    )

    # --------------------------------------------------------
    # General response
    # --------------------------------------------------------

    response = (
        "Your message contains symptoms or "
        "circumstances that may require urgent "
        "medical attention.\n\n"
    )

    response += (
        "Please seek immediate medical care "
        "or contact your local emergency service. "
        "If possible, have someone stay with you "
        "and do not delay professional evaluation.\n\n"
    )

    # --------------------------------------------------------
    # Additional category-specific guidance
    # --------------------------------------------------------

    if category == "chest_pain":

        response += (
            "Severe or sudden chest pain can have "
            "serious causes and should not be "
            "self-diagnosed."
        )

    elif category == "breathing_difficulty":

        response += (
            "Severe difficulty breathing can be "
            "an emergency. Seek urgent professional "
            "assessment."
        )

    elif category == "stroke_warning":

        response += (
            "Sudden facial weakness, speech problems, "
            "or one-sided weakness can require "
            "emergency assessment."
        )

    elif category == "severe_bleeding":

        response += (
            "Uncontrolled or severe bleeding requires "
            "urgent medical attention."
        )

    elif category == "severe_allergic_reaction":

        response += (
            "Severe allergic reactions involving "
            "breathing or swelling can become "
            "life-threatening quickly."
        )

    elif category == "loss_of_consciousness":

        response += (
            "Loss of consciousness or failure to "
            "respond requires urgent medical "
            "assessment."
        )

    elif category == "self_harm_emergency":

        response += (
            "Please move away from anything you could "
            "use to hurt yourself and stay with a "
            "trusted person while getting immediate "
            "professional help."
        )

    else:

        response += (
            "Because the situation may be serious, "
            "a healthcare professional should assess "
            "you promptly."
        )

    return response


# ============================================================
# MAIN FUNCTION
# ============================================================

def check_emergency(query):

    result = detect_emergency(
        query
    )

    if result["is_emergency"]:

        result["response"] = (
            emergency_response(result)
        )

    else:

        result["response"] = None

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 65)
    print("              EMERGENCY DETECTOR TEST")
    print("=" * 65)

    test_queries = [

        "I have severe chest pain",

        "I am having difficulty breathing",

        "I suddenly have slurred speech",

        "I have a mild headache",

        "I have a fever and cough",

        "I cannot breathe and have chest pressure"

    ]

    for query in test_queries:

        print("\n")
        print("-" * 65)

        print("USER:")
        print(query)

        result = check_emergency(
            query
        )

        print("\nEMERGENCY:")
        print(
            result["is_emergency"]
        )

        print("CATEGORY:")
        print(
            result["category"]
        )

        if result["matched_patterns"]:

            print(
                "MATCHED:"
            )

            for pattern in result[
                "matched_patterns"
            ]:

                print(
                    f"  • {pattern}"
                )

        if result["response"]:

            print("\nRESPONSE:")
            print(
                result["response"]
            )

    print("\n")
    print("=" * 65)
    print("                 TEST COMPLETE")
    print("=" * 65)