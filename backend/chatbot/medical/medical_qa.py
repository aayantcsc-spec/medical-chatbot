"""
medical_qa.py

Medical Question & Answer module.

FIX NOTE (previous version):
This file previously contained:

    from chatbot.medical.medical_qa import MedicalQA

i.e. it tried to import MedicalQA from ITSELF, and it defined a
class called `MedicalRouter` instead of `MedicalQA`. That is a
circular self-import and would always raise:

    ImportError: cannot import name 'MedicalQA' from partially
    initialized module 'chatbot.medical.medical_qa'

This rebuilt version defines an actual `MedicalQA` class that
searches datasets/medical_qa.csv (via chatbot.data.dataset_loader)
and returns a consistently-shaped result.
"""

import os
import sys


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
# DATASET LOADER
# ============================================================

try:

    from chatbot.data.dataset_loader import (
        search_medical_qa,
        get_dataset_status,
    )

except Exception as error:

    print(
        "[MEDICAL QA] Could not import dataset_loader:",
        error
    )

    search_medical_qa = None
    get_dataset_status = None


# ============================================================
# MEDICAL QA
# ============================================================

class MedicalQA:
    """
    Thin wrapper around the medical_qa.csv dataset search.

    Public API:
        answer(query) -> dict | None
            {
                "response": str,
                "source": "medical_qa",
                "score": float,
                "qtype": str,
                "question": str
            }
    """

    # Minimum score (see dataset_loader.search_medical_qa scoring)
    # required before we trust a match enough to answer with it.
    MIN_SCORE = 15

    def __init__(self):

        self.available = search_medical_qa is not None

        if self.available and get_dataset_status is not None:

            try:

                status = get_dataset_status()

                qa_count = status.get("medical_qa", 0)

                if qa_count == 0:

                    print(
                        "[MEDICAL QA] WARNING: medical_qa.csv "
                        "loaded 0 rows. Place a valid "
                        "medical_qa.csv in the datasets/ "
                        "folder (columns: qtype, question, "
                        "answer) to enable this feature."
                    )

                else:

                    print(
                        f"[MEDICAL QA] Ready with "
                        f"{qa_count} question/answer rows."
                    )

            except Exception as error:

                print(
                    "[MEDICAL QA] Status check failed:",
                    error
                )

    # ========================================================
    # ANSWER
    # ========================================================

    def answer(self, query):

        if not self.available:
            return None

        query = str(query or "").strip()

        if not query:
            return None

        try:

            results = search_medical_qa(
                query,
                top_k=5
            )

        except Exception as error:

            print(
                "[MEDICAL QA] Search error:",
                error
            )

            return None

        if not results:
            return None

        best = results[0]

        try:
            score = float(best.get("score", 0))
        except (TypeError, ValueError):
            score = 0

        if score < self.MIN_SCORE:
            return None

        answer_text = str(
            best.get("answer", "")
        ).strip()

        if not answer_text:
            return None

        qtype = str(
            best.get("qtype", "")
        ).strip().lower()

        response = self._format(
            answer_text,
            qtype
        )

        return {
            "response": response,
            "source": "medical_qa",
            "score": score,
            "qtype": qtype,
            "question": best.get("question", "")
        }

    # ========================================================
    # FORMAT
    # ========================================================

    def _format(self, answer_text, qtype):

        headings = {
            "symptoms": "Here is general information about the symptoms:",
            "treatment": "Here is general information about treatment:",
            "prevention": "Here are some general prevention measures:",
            "susceptibility": "Here is general information about risk factors:",
            "exams and tests": "Here is general information about diagnosis and testing:",
        }

        heading = headings.get(
            qtype,
            "Here is some relevant medical information:"
        )

        return (
            f"{heading}\n\n{answer_text}\n\n"
            "Important: This information is for educational "
            "purposes only. It does not confirm a diagnosis or "
            "replace advice from a qualified healthcare "
            "professional."
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    qa = MedicalQA()

    for question in [
        "What is the treatment for fever?",
        "How can I prevent malaria?",
        "What are the risk factors for diabetes?",
    ]:

        print("\nUSER:", question)

        result = qa.answer(question)

        print(result)