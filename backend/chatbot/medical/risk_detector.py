import re


# ============================================================
# RISK PATTERNS
# ============================================================

RISK_PATTERNS = {

    # --------------------------------------------------------
    # HIGH RISK
    # --------------------------------------------------------

    "high": {

        "severe pain": [
            "severe pain",
            "extreme pain",
            "unbearable pain",
            "very severe pain",
        ],

        "persistent symptoms": [
            "symptoms getting worse",
            "symptoms are getting worse",
            "pain getting worse",
            "getting worse",
            "not getting better",
            "not improving",
            "persistent symptoms",
            "symptoms for many days",
        ],

        "high fever": [
            "very high fever",
            "high fever",
            "fever above 103",
            "fever above 104",
            "fever 103",
            "fever 104",
        ],

        "severe vomiting": [
            "vomiting continuously",
            "cannot stop vomiting",
            "can't stop vomiting",
            "severe vomiting",
            "vomiting all day",
        ],

        "severe dehydration": [
            "severe dehydration",
            "unable to keep fluids down",
            "cannot keep fluids down",
            "not urinating",
            "very little urine",
        ],

        "serious infection signs": [
            "confusion with fever",
            "very weak with fever",
            "fever and confusion",
            "fever with confusion",
        ]
    },

    # --------------------------------------------------------
    # MODERATE RISK
    # --------------------------------------------------------

    "moderate": {

        "moderate pain": [
            "moderate pain",
            "persistent headache",
            "persistent cough",
            "persistent fever",
            "persistent stomach pain",
        ],

        "duration": [
            "for several days",
            "for a few days",
            "for one week",
            "for a week",
            "for two weeks",
            "for several weeks",
        ],

        "recurring symptoms": [
            "keeps happening",
            "keeps coming back",
            "happens repeatedly",
            "recurring",
            "recurrent",
        ],

        "medication concern": [
            "medicine is not working",
            "medication is not working",
            "treatment is not working",
            "side effects from medicine",
            "reaction to medicine",
        ]
    }
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
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
# DETECT RISK
# ============================================================

def detect_risk(query):

    normalized_query = normalize_text(
        query
    )

    if not normalized_query:

        return {
            "risk_level": "LOW",
            "categories": [],
            "matched_patterns": []
        }

    high_matches = []
    moderate_matches = []

    # --------------------------------------------------------
    # HIGH RISK
    # --------------------------------------------------------

    for category, patterns in RISK_PATTERNS[
        "high"
    ].items():

        for pattern in patterns:

            normalized_pattern = normalize_text(
                pattern
            )

            if normalized_pattern in normalized_query:

                high_matches.append({
                    "category": category,
                    "pattern": pattern
                })

    # --------------------------------------------------------
    # MODERATE RISK
    # --------------------------------------------------------

    for category, patterns in RISK_PATTERNS[
        "moderate"
    ].items():

        for pattern in patterns:

            normalized_pattern = normalize_text(
                pattern
            )

            if normalized_pattern in normalized_query:

                moderate_matches.append({
                    "category": category,
                    "pattern": pattern
                })

    # --------------------------------------------------------
    # DETERMINE LEVEL
    # --------------------------------------------------------

    if high_matches:

        return {
            "risk_level": "HIGH",
            "categories": list(
                set(
                    item["category"]
                    for item in high_matches
                )
            ),
            "matched_patterns": [
                item["pattern"]
                for item in high_matches
            ]
        }

    if moderate_matches:

        return {
            "risk_level": "MODERATE",
            "categories": list(
                set(
                    item["category"]
                    for item in moderate_matches
                )
            ),
            "matched_patterns": [
                item["pattern"]
                for item in moderate_matches
            ]
        }

    return {
        "risk_level": "LOW",
        "categories": [],
        "matched_patterns": []
    }


# ============================================================
# RISK RESPONSE
# ============================================================

def risk_response(risk_result):

    level = risk_result.get(
        "risk_level",
        "LOW"
    )

    if level == "HIGH":

        return (
            "Some details in your message may "
            "indicate that you should seek medical "
            "evaluation promptly. If symptoms are "
            "severe, rapidly worsening, or you feel "
            "seriously unwell, seek urgent care."
        )

    if level == "MODERATE":

        return (
            "Your symptoms may need monitoring. "
            "If they persist, worsen, or interfere "
            "with normal activities, consider "
            "speaking with a healthcare professional."
        )

    return (
        "Based on the information provided, "
        "no high-risk pattern was detected by "
        "this basic screening system."
    )


# ============================================================
# COMPLETE RISK CHECK
# ============================================================

def check_risk(query):

    result = detect_risk(
        query
    )

    result["response"] = risk_response(
        result
    )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 65)
    print("                RISK DETECTOR TEST")
    print("=" * 65)

    test_queries = [

        "I have a mild headache",

        "I have a persistent cough",

        "My symptoms are getting worse",

        "I have severe pain",

        "I have a fever for several days",

        "I feel fine and want to know about diabetes"

    ]

    for query in test_queries:

        print("\n")
        print("-" * 65)

        print("USER:")
        print(query)

        result = check_risk(
            query
        )

        print("\nRISK LEVEL:")
        print(
            result["risk_level"]
        )

        print("\nCATEGORIES:")

        if result["categories"]:

            for category in result[
                "categories"
            ]:

                print(
                    f"  • {category}"
                )

        else:

            print("  None")

        print("\nMATCHED PATTERNS:")

        if result["matched_patterns"]:

            for pattern in result[
                "matched_patterns"
            ]:

                print(
                    f"  • {pattern}"
                )

        else:

            print("  None")

        print("\nRESPONSE:")
        print(
            result["response"]
        )

    print("\n")
    print("=" * 65)
    print("                 TEST COMPLETE")
    print("=" * 65)