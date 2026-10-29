import os
import sys

from sklearn.metrics import recall_score


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
# CALCULATE RECALL
# ==========================================

def calculate_recall(
    actual_values,
    predicted_values
):
    """
    Calculate weighted recall.

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

    recall = recall_score(
        actual_values,
        predicted_values,
        average="weighted",
        zero_division=0
    )

    return recall


# ==========================================
# RECALL PERCENTAGE
# ==========================================

def recall_percentage(
    actual_values,
    predicted_values
):

    recall = calculate_recall(
        actual_values,
        predicted_values
    )

    return recall * 100


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("Testing recall module...")

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

    recall = calculate_recall(
        actual,
        predicted
    )

    percentage = recall_percentage(
        actual,
        predicted
    )

    print()
    print("Actual values   :", actual)
    print("Predicted values:", predicted)
    print()
    print(
        "Recall:",
        round(recall, 4)
    )

    print(
        "Recall:",
        round(percentage, 2),
        "%"
    )

    print()
    print("Recall module working!")