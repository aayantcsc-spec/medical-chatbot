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
# IMPORT MEDICAL ROUTER
# ============================================================

from chatbot.medical.medical_router import route_medical_query


# ============================================================
# MEDICAL ANALYZER
# ============================================================

class MedicalAnalyzer:

    def __init__(self):
        print(
            "Medical Analyzer initialized successfully!"
        )

    # ========================================================
    # ANALYZE QUERY
    # ========================================================

    def analyze(self, query):

        # ----------------------------------------------------
        # Validate query
        # ----------------------------------------------------

        if not query or not str(query).strip():

            return {
                "success": False,
                "query": "",
                "route": "general",
                "risk_level": "LOW",
                "response": (
                    "Please enter a health-related "
                    "question."
                ),
                "data": None,
                "risk": None
            }

        query = str(query).strip()

        # ----------------------------------------------------
        # Send query to medical router
        # ----------------------------------------------------

        try:

            result = route_medical_query(query)

        except Exception as error:

            print(
                "\nMedical router error:",
                error
            )

            return {
                "success": False,
                "query": query,
                "route": "general",
                "risk_level": "LOW",
                "response": (
                    "I could not process your health "
                    "question right now. Please try again."
                ),
                "data": None,
                "risk": None
            }

        # ----------------------------------------------------
        # Make sure router returned a dictionary
        # ----------------------------------------------------

        if not isinstance(result, dict):

            return {
                "success": False,
                "query": query,
                "route": "general",
                "risk_level": "LOW",
                "response": (
                    "I could not process the medical "
                    "information correctly."
                ),
                "data": None,
                "risk": None
            }

        # ----------------------------------------------------
        # Extract basic information
        # ----------------------------------------------------

        route = result.get(
            "route",
            "general"
        )

        success = result.get(
            "success",
            False
        )

        risk_level = result.get(
            "risk_level",
            "LOW"
        )

        response = result.get(
            "response"
        )

        # ----------------------------------------------------
        # Fallback response
        # ----------------------------------------------------

        if not response:

            response = (
                "I could not find enough information "
                "to answer that question."
            )

        # ----------------------------------------------------
        # Build standard response structure
        # ----------------------------------------------------

        analysis = {

            "success": success,

            "query": query,

            "route": route,

            "risk_level": risk_level,

            "response": response,

            "data": result.get(
                "data"
            ),

            "risk": result.get(
                "risk"
            )
        }

        return analysis


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_medical_query(query):

    analyzer = MedicalAnalyzer()

    return analyzer.analyze(
        query
    )


# ============================================================
# FORMAT SIMPLE RESULT
# ============================================================

def format_analysis(result):

    if not result:

        return (
            "Unable to process the medical query."
        )

    response = result.get(
        "response"
    )

    if response:

        return response

    return (
        "I could not find enough information "
        "to answer that question."
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("              MEDICAL ANALYZER TEST")
    print("=" * 70)

    analyzer = MedicalAnalyzer()

    test_queries = [

        "Hello",

        "I have fever and headache",

        "What are the symptoms of dengue?",

        "What is diabetes?",

        "What causes dehydration?",

        "I have severe chest pain",

        "My symptoms are getting worse",

        "What are the symptoms of LCM"
    ]

    for query in test_queries:

        print("\n")
        print("-" * 70)

        print("USER:")
        print(query)

        result = analyzer.analyze(
            query
        )

        print("\nROUTE:")
        print(
            result.get(
                "route",
                "general"
            )
        )

        print("\nRISK:")
        print(
            result.get(
                "risk_level",
                "LOW"
            )
        )

        print("\nSUCCESS:")
        print(
            result.get(
                "success",
                False
            )
        )

        print("\nRESPONSE:")

        print(
            format_analysis(
                result
            )
        )

    print("\n")
    print("=" * 70)
    print("                 TEST COMPLETE")
    print("=" * 70)