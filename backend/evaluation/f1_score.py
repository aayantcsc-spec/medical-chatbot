import os
import sys

from sklearn.metrics import f1_score


# ==========================================
# PROJECT ROOT
# ==========================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ==========================================
# CALCULATE F1 SCORE
# ==========================================

def calculate_f1_score(
    actual_values,
    predicted_values
):
    """
    Calculate weighted F1 score.

    actual_values:
        Correct disease labels.

    predicted_values:
        Model predicted disease labels.
    """

    if len(actual_values) == 0:
        return 0.0

    if len(actual_values) != len(predicted_values):
        raise ValueError(
            "Actual and predicted values "
            "must have the same length."
        )

    score = f1_score(
        actual_values,
        predicted_values,
        average="weighted",
        zero_division=0
    )

    return score


# ==========================================
# F1 SCORE PERCENTAGE
# ==========================================

def f1_percentage(
    actual_values,
    predicted_values
):

    score = calculate_f1_score(
        actual_values,
        predicted_values
    )

    return score * 100


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("Testing F1-score module...")

    actual = [
        "Fungal infection",
        "Allergy",
        "Diabetes",
        "Migraine",
        "Malaria"
    ]

    predicted = [
        "Fungal infection",
        "Allergy",
        "Diabetes",
        "Migraine",
        "Malaria"
    ]

    score = calculate_f1_score(
        actual,
        predicted
    )

    percentage = f1_percentage(
        actual,
        predicted
    )

    print()
    print("Actual values   :", actual)
    print("Predicted values:", predicted)
    print()

    print(
        "F1 Score:",
        round(score, 4)
    )

    print(
        "F1 Score:",
        round(percentage, 2),
        "%"
    )

    print()
    print("F1-score module working!")