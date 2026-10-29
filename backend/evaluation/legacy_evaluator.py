"""
evaluation/evaluator.py

Legacy / standalone comparative evaluator.

Evaluates the three chatbot architectures:

    1. Rule-Based
    2. Machine Learning
    3. Deep Learning

using a shared sample from:

    datasets/Symptom2Disease.csv

Calculates:

    Accuracy
    Precision
    Recall
    F1 Score
    Response Time
    Memory Usage
    CPU Usage

Results are saved through evaluation.compare.save_comparison()
to:

    results/comparison_results.csv

IMPORTANT
---------
The main 300-question comparative evaluation used by the current
Analysis page is handled by:

    evaluation/evaluation_runner.py

and stored in SQLite:

    evaluation_runs
    evaluation_results

This file is retained as a standalone/legacy evaluator for the
older CSV-based comparison workflow.

Usage:

    python -m evaluation.evaluator

or:

    python -m evaluation.evaluator --sample-size 30
"""

import argparse
import os
import sys
import time


# ============================================================
# PROJECT PATH
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# THIRD-PARTY IMPORTS
# ============================================================

import pandas as pd


# ============================================================
# EVALUATION IMPORTS
# ============================================================

from evaluation.accuracy import accuracy_percentage
from evaluation.precision import precision_percentage
from evaluation.recall import recall_percentage
from evaluation.f1_score import f1_percentage

from evaluation.memory_usage import get_memory_usage
from evaluation.cpu_usage import get_cpu_usage

from evaluation.compare import (
    save_comparison,
    RESULTS_DIR,
)

from chatbot.orchestrator.bot_registry import (
    get_bot_response,
)


# ============================================================
# CHATBOT ARCHITECTURES
# ============================================================

ARCHITECTURES = {
    "rule": "Rule-Based",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
}


# ============================================================
# TEST DATA
# ============================================================

TEST_DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "Symptom2Disease.csv",
)


# ============================================================
# DATA LOADING
# ============================================================

def load_test_questions(
    sample_size=30,
    random_state=42,
):
    """
    Load a reproducible test sample from Symptom2Disease.csv.

    Required columns:

        text
        label

    Returns:

        questions
        labels
        known_labels
    """

    if not os.path.isfile(TEST_DATA_FILE):
        raise FileNotFoundError(
            "Evaluation dataset not found:\n"
            f"{TEST_DATA_FILE}"
        )

    df = pd.read_csv(TEST_DATA_FILE)

    required_columns = {
        "text",
        "label",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Symptom2Disease.csv is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    # Remove incomplete rows.
    df = df.dropna(
        subset=[
            "text",
            "label",
        ]
    )

    if df.empty:
        raise ValueError(
            "Symptom2Disease.csv contains no usable evaluation rows."
        )

    # Make sure sample size is valid.
    try:
        sample_size = int(sample_size)
    except (TypeError, ValueError):
        raise ValueError(
            "sample_size must be an integer."
        )

    if sample_size <= 0:
        raise ValueError(
            "sample_size must be greater than zero."
        )

    sample_size = min(
        sample_size,
        len(df),
    )

    sample = df.sample(
        n=sample_size,
        random_state=random_state,
    )

    questions = (
        sample["text"]
        .astype(str)
        .tolist()
    )

    labels = (
        sample["label"]
        .astype(str)
        .tolist()
    )

    known_labels = sorted(
        df["label"]
        .astype(str)
        .unique()
        .tolist()
    )

    return (
        questions,
        labels,
        known_labels,
    )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text for case-insensitive label matching.
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


# ============================================================
# LABEL ALIASES
# ============================================================

LABEL_ALIASES = {
    "common cold": [
        "cold",
        "common cold",
    ],

    "flu": [
        "flu",
        "influenza",
    ],

    "influenza": [
        "influenza",
        "flu",
    ],

    "heart attack": [
        "heart attack",
        "myocardial infarction",
    ],

    "gastroesophageal reflux disease": [
        "gastroesophageal reflux disease",
        "gerd",
        "acid reflux",
    ],

    "urinary tract infection": [
        "urinary tract infection",
        "uti",
    ],
}


def get_label_variants(label):
    """
    Return the canonical label plus known aliases.
    """

    normalized = normalize_text(label)

    variants = [
        normalized
    ]

    aliases = LABEL_ALIASES.get(
        normalized,
        []
    )

    for alias in aliases:
        alias_normalized = normalize_text(alias)

        if alias_normalized not in variants:
            variants.append(
                alias_normalized
            )

    return variants


# ============================================================
# PREDICTION EXTRACTION
# ============================================================

def extract_predicted_label(
    response_text,
    known_labels,
):
    """
    Extract a disease label from the chatbot's free-text response.

    The method is deliberately simple and explainable:

        - Search for known disease labels.
        - Check documented aliases.
        - Return the first matching label.
        - Otherwise return "no_match".

    This avoids inventing predictions.
    """

    response = normalize_text(
        response_text
    )

    if not response:
        return "no_match"

    # Check longer labels first so that a short label does not
    # accidentally match before its more specific disease name.
    sorted_labels = sorted(
        known_labels,
        key=lambda item: len(
            normalize_text(item)
        ),
        reverse=True,
    )

    for label in sorted_labels:

        variants = get_label_variants(
            label
        )

        for variant in variants:

            if variant and variant in response:
                return label

    return "no_match"


# ============================================================
# SINGLE ARCHITECTURE EVALUATION
# ============================================================

def evaluate_architecture(
    bot_key,
    questions,
    labels,
    known_labels,
):
    """
    Evaluate one chatbot architecture.

    Returns:

        predictions
        average response time
        memory usage
        CPU usage
    """

    predictions = []
    response_times = []

    # --------------------------------------------------------
    # WARM-UP
    # --------------------------------------------------------

    if questions:

        try:
            get_bot_response(
                bot_key,
                questions[0],
            )

        except Exception as error:

            print(
                f"[WARNING] Warm-up failed for "
                f"{bot_key}: {error}"
            )

    # --------------------------------------------------------
    # MEMORY BASELINE
    # --------------------------------------------------------

    memory_before = get_memory_usage()

    # --------------------------------------------------------
    # CPU BASELINE
    # --------------------------------------------------------

    try:
        get_cpu_usage(
            interval=None
        )
    except Exception:
        pass

    # --------------------------------------------------------
    # QUESTIONS
    # --------------------------------------------------------

    for index, question in enumerate(
        questions,
        start=1,
    ):

        print(
            f"    Question {index}/{len(questions)}",
            end="\r",
        )

        call_start = time.perf_counter()

        try:

            result = get_bot_response(
                bot_key,
                question,
            )

        except Exception as error:

            print(
                f"\n[WARNING] {bot_key} "
                f"question {index} failed: "
                f"{error}"
            )

            result = {
                "available": False,
                "response": "",
                "error": str(error),
            }

        elapsed = (
            time.perf_counter()
            - call_start
        )

        # Never allow negative timing values.
        elapsed = max(
            elapsed,
            0.0,
        )

        response_times.append(
            elapsed
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        if not isinstance(result, dict):
            result = {
                "available": False,
                "response": "",
            }

        available = result.get(
            "available",
            True,
        )

        if not available:

            predictions.append(
                "no_match"
            )

            continue

        response_text = result.get(
            "response",
            "",
        )

        predicted = extract_predicted_label(
            response_text,
            known_labels,
        )

        predictions.append(
            predicted
        )

    print()

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    memory_after = get_memory_usage()

    memory_used = max(
        memory_after - memory_before,
        0.0,
    )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    try:

        cpu_usage = get_cpu_usage(
            interval=0.1
        )

    except Exception as error:

        print(
            f"[WARNING] CPU measurement failed "
            f"for {bot_key}: {error}"
        )

        cpu_usage = 0.0

    # --------------------------------------------------------
    # RESPONSE TIME
    # --------------------------------------------------------

    if response_times:

        avg_response_time = (
            sum(response_times)
            / len(response_times)
        )

    else:

        avg_response_time = 0.0

    return {
        "predictions": predictions,
        "avg_response_time": max(
            avg_response_time,
            0.0,
        ),
        "memory_used_mb": max(
            memory_used,
            0.0,
        ),
        "cpu_usage_percent": max(
            float(cpu_usage),
            0.0,
        ),
    }


# ============================================================
# RUN COMPLETE COMPARISON
# ============================================================

def run_evaluation(
    sample_size=30,
    random_state=42,
    verbose=True,
):
    """
    Run the comparison across:

        Rule-Based
        Machine Learning
        Deep Learning

    using exactly the same test questions.

    Returns a dictionary containing the measured metrics.
    """

    questions, labels, known_labels = (
        load_test_questions(
            sample_size=sample_size,
            random_state=random_state,
        )
    )

    if verbose:

        print()
        print("=" * 65)
        print("CHATBOT COMPARATIVE EVALUATION")
        print("=" * 65)

        print(
            f"Dataset       : "
            f"{os.path.basename(TEST_DATA_FILE)}"
        )

        print(
            f"Questions     : "
            f"{len(questions)}"
        )

        print(
            f"Disease labels: "
            f"{len(known_labels)}"
        )

        print(
            "Architectures : "
            + ", ".join(
                ARCHITECTURES.values()
            )
        )

        print("=" * 65)
        print()

    all_results = {}

    # ========================================================
    # EACH ARCHITECTURE
    # ========================================================

    for bot_key, display_name in ARCHITECTURES.items():

        if verbose:

            print(
                f"\n[{display_name}]"
            )

            print(
                "-" * 45
            )

        run = evaluate_architecture(
            bot_key=bot_key,
            questions=questions,
            labels=labels,
            known_labels=known_labels,
        )

        predictions = run[
            "predictions"
        ]

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        try:

            accuracy = accuracy_percentage(
                labels,
                predictions,
            )

        except Exception as error:

            print(
                f"[WARNING] Accuracy calculation "
                f"failed: {error}"
            )

            accuracy = 0.0

        try:

            precision = precision_percentage(
                labels,
                predictions,
            )

        except Exception as error:

            print(
                f"[WARNING] Precision calculation "
                f"failed: {error}"
            )

            precision = 0.0

        try:

            recall = recall_percentage(
                labels,
                predictions,
            )

        except Exception as error:

            print(
                f"[WARNING] Recall calculation "
                f"failed: {error}"
            )

            recall = 0.0

        try:

            f1_score = f1_percentage(
                labels,
                predictions,
            )

        except Exception as error:

            print(
                f"[WARNING] F1 calculation "
                f"failed: {error}"
            )

            f1_score = 0.0

        # ----------------------------------------------------
        # SAVE CSV RESULT
        # ----------------------------------------------------

        save_comparison(
            chatbot_type=display_name,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            response_time=run[
                "avg_response_time"
            ],
            cpu_usage=run[
                "cpu_usage_percent"
            ],
            memory_usage=run[
                "memory_used_mb"
            ],
        )

        # ----------------------------------------------------
        # RESULT OBJECT
        # ----------------------------------------------------

        result_data = {
            "name": display_name,

            "accuracy": round(
                float(accuracy),
                2,
            ),

            "precision": round(
                float(precision),
                2,
            ),

            "recall": round(
                float(recall),
                2,
            ),

            "f1_score": round(
                float(f1_score),
                2,
            ),

            "response_time": round(
                float(
                    run[
                        "avg_response_time"
                    ]
                ),
                4,
            ),

            "memory_usage": round(
                float(
                    run[
                        "memory_used_mb"
                    ]
                ),
                2,
            ),

            "cpu_usage": round(
                float(
                    run[
                        "cpu_usage_percent"
                    ]
                ),
                2,
            ),

            "questions_evaluated": len(
                questions
            ),

            "correct_predictions": sum(
                1
                for expected, predicted
                in zip(
                    labels,
                    predictions,
                )
                if normalize_text(expected)
                == normalize_text(predicted)
            ),

            "failed_predictions": sum(
                1
                for predicted
                in predictions
                if predicted == "no_match"
            ),
        }

        all_results[bot_key] = result_data

        # ----------------------------------------------------
        # TERMINAL OUTPUT
        # ----------------------------------------------------

        if verbose:

            print(
                f"Accuracy       : "
                f"{accuracy:.2f}%"
            )

            print(
                f"Precision      : "
                f"{precision:.2f}%"
            )

            print(
                f"Recall         : "
                f"{recall:.2f}%"
            )

            print(
                f"F1 Score       : "
                f"{f1_score:.2f}%"
            )

            print(
                f"Response Time  : "
                f"{run['avg_response_time']:.4f} sec"
            )

            print(
                f"Memory Usage   : "
                f"{run['memory_used_mb']:.2f} MB"
            )

            print(
                f"CPU Usage      : "
                f"{run['cpu_usage_percent']:.2f}%"
            )

            print()

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    if verbose:

        print("=" * 65)
        print("EVALUATION COMPLETED")
        print("=" * 65)

        print(
            "Results saved to:"
        )

        print(
            os.path.join(
                RESULTS_DIR,
                "comparison_results.csv",
            )
        )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "The main 300-question evaluation used "
            "by the current Analysis page is handled "
            "by evaluation_runner.py and stored in "
            "healthbot.db."
        )

        print()

    return all_results


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare Rule-Based, Machine Learning, "
            "and Deep Learning chatbot architectures."
        )
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help=(
            "Number of test questions to evaluate "
            "(default: 30)."
        ),
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help=(
            "Random seed used to select the shared "
            "test questions (default: 42)."
        ),
    )

    args = parser.parse_args()

    try:

        results = run_evaluation(
            sample_size=args.sample_size,
            random_state=args.random_state,
            verbose=True,
        )

        print(
            "\nFinal metric summary:\n"
        )

        for bot_key, result in results.items():

            print(
                f"{result['name']}: "
                f"Accuracy={result['accuracy']}%, "
                f"Precision={result['precision']}%, "
                f"Recall={result['recall']}%, "
                f"F1={result['f1_score']}%, "
                f"Time={result['response_time']}s, "
                f"Memory={result['memory_usage']}MB, "
                f"CPU={result['cpu_usage']}%"
            )

        return 0

    except FileNotFoundError as error:

        print(
            f"\n[ERROR] {error}"
        )

        return 1

    except ValueError as error:

        print(
            f"\n[ERROR] {error}"
        )

        return 1

    except KeyboardInterrupt:

        print(
            "\n\nEvaluation cancelled by user."
        )

        return 130

    except Exception as error:

        print(
            "\n[ERROR] Evaluation failed:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )