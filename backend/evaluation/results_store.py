"""
results_store.py

Reads results/comparison_results.csv (written by
evaluation/compare.py, populated by evaluation/evaluator.py) and
formats the *latest* result for each of the three architectures into
the shape templates/analysis.html's JavaScript expects:

    {
        "chatbots": [
            {"name": ..., "accuracy": ..., "precision": ...,
             "recall": ..., "f1_score": ..., "response_time": ...,
             "memory_usage": ..., "cpu_usage": ...},
            ...
        ],
        "summary": {
            "best_accuracy": "...",
            "best_f1": "...",
            "fastest": "...",
            "lowest_memory": "...",
        },
        "is_demo_data": False
    }

If no evaluation has been run yet, load_latest_results() returns
None so the caller can show "Evaluation required" instead of
inventing numbers -- this file never fabricates a metric.
"""

import os
import csv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPARISON_FILE = os.path.join(
    BASE_DIR, "results", "comparison_results.csv"
)


def _read_all_rows():
    if not os.path.exists(COMPARISON_FILE):
        return []

    with open(COMPARISON_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def load_latest_results():
    """
    Returns the most recent evaluation row per chatbot, or None if
    no evaluation has been run yet.
    """

    rows = _read_all_rows()

    if not rows:
        return None

    # Keep only the latest row per chatbot (rows are appended in
    # chronological order by compare.save_comparison, so the last
    # occurrence of each name is the most recent run).
    latest_by_bot = {}
    for row in rows:
        latest_by_bot[row["Chatbot"]] = row

    chatbots = []
    for name, row in latest_by_bot.items():
        chatbots.append({
            "name": name,
            "accuracy": float(row["Accuracy"]),
            "precision": float(row["Precision"]),
            "recall": float(row["Recall"]),
            "f1_score": float(row["F1 Score"]),
            "response_time": float(row["Response Time"]),
            "memory_usage": float(row["Memory Usage"]),
            "cpu_usage": float(row["CPU Usage"]),
            "date": row["Date"],
        })

    if not chatbots:
        return None

    best_accuracy = max(chatbots, key=lambda b: b["accuracy"])
    best_f1 = max(chatbots, key=lambda b: b["f1_score"])
    fastest = min(chatbots, key=lambda b: b["response_time"])
    lowest_memory = min(chatbots, key=lambda b: b["memory_usage"])

    return {
        "chatbots": chatbots,
        "summary": {
            "best_accuracy": best_accuracy["name"],
            "best_f1": best_f1["name"],
            "fastest": fastest["name"],
            "lowest_memory": lowest_memory["name"],
        },
        "is_demo_data": False,
    }


def load_experiment_history():
    """
    Returns every saved evaluation run, grouped by timestamp, so a
    history/experiments view can show past runs rather than only
    the latest one.
    """

    rows = _read_all_rows()

    history = {}
    for row in rows:
        date = row["Date"]
        history.setdefault(date, []).append(row)

    return history
