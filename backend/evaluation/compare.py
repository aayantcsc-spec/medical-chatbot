import os
import sys
import csv
from datetime import datetime


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
# RESULTS FOLDER
# ==========================================

RESULTS_DIR = os.path.join(
    BASE_DIR,
    "results"
)

os.makedirs(
    RESULTS_DIR,
    exist_ok=True
)


# ==========================================
# COMPARISON FILE
# ==========================================

COMPARISON_FILE = os.path.join(
    RESULTS_DIR,
    "comparison_results.csv"
)


# ==========================================
# SAVE COMPARISON RESULT
# ==========================================

def save_comparison(
    chatbot_type,
    accuracy=0.0,
    precision=0.0,
    recall=0.0,
    f1_score=0.0,
    response_time=0.0,
    cpu_usage=0.0,
    memory_usage=0.0
):

    file_exists = os.path.exists(
        COMPARISON_FILE
    )

    with open(
        COMPARISON_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        # Create header only once
        if not file_exists:

            writer.writerow([
                "Date",
                "Chatbot",
                "Accuracy",
                "Precision",
                "Recall",
                "F1 Score",
                "Response Time",
                "CPU Usage",
                "Memory Usage"
            ])

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            chatbot_type,
            round(accuracy, 4),
            round(precision, 4),
            round(recall, 4),
            round(f1_score, 4),
            round(response_time, 4),
            round(cpu_usage, 2),
            round(memory_usage, 4)
        ])

    print(
        "Comparison result saved successfully!"
    )


# ==========================================
# READ COMPARISON RESULTS
# ==========================================

def get_comparison_results():

    if not os.path.exists(
        COMPARISON_FILE
    ):
        return []

    results = []

    with open(
        COMPARISON_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            results.append(row)

    return results


# ==========================================
# DISPLAY RESULTS
# ==========================================

def display_results():

    results = get_comparison_results()

    if not results:

        print(
            "No comparison results available."
        )

        return

    print()
    print("=" * 80)
    print("CHATBOT COMPARISON")
    print("=" * 80)

    for row in results:

        print()
        print(
            "Chatbot:",
            row["Chatbot"]
        )

        print(
            "Accuracy:",
            row["Accuracy"]
        )

        print(
            "Precision:",
            row["Precision"]
        )

        print(
            "Recall:",
            row["Recall"]
        )

        print(
            "F1 Score:",
            row["F1 Score"]
        )

        print(
            "Response Time:",
            row["Response Time"],
            "seconds"
        )

        print(
            "CPU Usage:",
            row["CPU Usage"],
            "%"
        )

        print(
            "Memory Usage:",
            row["Memory Usage"],
            "MB"
        )

    print()
    print("=" * 80)


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print(
        "Testing comparison module..."
    )

    # Test result
    save_comparison(
        chatbot_type="Classification",
        accuracy=0.95,
        precision=0.94,
        recall=0.93,
        f1_score=0.935,
        response_time=0.25,
        cpu_usage=12.5,
        memory_usage=35.6
    )

    display_results()

    print()
    print(
        "Comparison module working!"
    )