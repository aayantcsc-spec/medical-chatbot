import os
import sys

from sklearn.metrics import accuracy_score


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
# CALCULATE ACCURACY
# ==========================================

def calculate_accuracy(
    actual_values,
    predicted_values
):
    """
    Calculate classification accuracy.

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

    accuracy = accuracy_score(
        actual_values,
        predicted_values
    )

    return accuracy


# ==========================================
# ACCURACY IN PERCENTAGE
# ==========================================

def accuracy_percentage(
    actual_values,
    predicted_values
):

    accuracy = calculate_accuracy(
        actual_values,
        predicted_values
    )

    return accuracy * 100


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("Testing accuracy module...")

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

    accuracy = calculate_accuracy(
        actual,
        predicted
    )

    percentage = accuracy_percentage(
        actual,
        predicted
    )

    print()
    print("Actual values   :", actual)
    print("Predicted values:", predicted)
    print()
    print(
        "Accuracy:",
        round(accuracy, 4)
    )

    print(
        "Accuracy:",
        round(percentage, 2),
        "%"
    )

    print()
    print("Accuracy module working!")