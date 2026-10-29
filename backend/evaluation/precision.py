import os
import sys

from sklearn.metrics import precision_score


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
# CALCULATE PRECISION
# ==========================================

def calculate_precision(
    actual_values,
    predicted_values
):
    """
    Calculate weighted precision.

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

    precision = precision_score(
        actual_values,
        predicted_values,
        average="weighted",
        zero_division=0
    )

    return precision


# ==========================================
# PRECISION PERCENTAGE
# ==========================================

def precision_percentage(
    actual_values,
    predicted_values
):

    precision = calculate_precision(
        actual_values,
        predicted_values
    )

    return precision * 100


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("Testing precision module...")

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

    precision = calculate_precision(
        actual,
        predicted
    )

    percentage = precision_percentage(
        actual,
        predicted
    )

    print()
    print("Actual values   :", actual)
    print("Predicted values:", predicted)
    print()
    print(
        "Precision:",
        round(precision, 4)
    )

    print(
        "Precision:",
        round(percentage, 2),
        "%"
    )

    print()
    print("Precision module working!")