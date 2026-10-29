"""
MediChat Evaluation Runner

Project:
Comparative Analysis of Health Chatbots Based on Framework and Architecture

Evaluation architectures:
1. Rule-Based
2. Machine Learning
3. Deep Learning

Evaluation dataset:
datasets/evaluation_questions.csv

Expected evaluation:
300 questions x 3 architectures = 900 responses

Results are stored in:
    healthbot.db

Tables:
    evaluation_runs
    evaluation_results

Standalone usage:
    python -m evaluation.evaluation_runner
    python -m evaluation.evaluation_runner --force
"""

import argparse
import os
import sys

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
# THIRD-PARTY
# ============================================================

import pandas as pd


# ============================================================
# PROJECT IMPORTS
# ============================================================

from database import database as db

from evaluation.chatbot_adapter import (
    get_response,
    check_chatbots_available,
)

from evaluation.answer_evaluator import evaluate_answer
from evaluation.safety_evaluator import evaluate_safety
from evaluation.metrics import compute_quality_score


# ============================================================
# CONFIGURATION
# ============================================================

QUESTIONS_FILE = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "evaluation_questions.csv",
)


# ============================================================
# ONLY THESE THREE ARCHITECTURES ARE USED
# ============================================================

CHATBOT_NAMES = [
    "Rule-Based",
    "Machine Learning",
    "Deep Learning",
]


# ============================================================
# REQUIRED CSV COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "question_id",
    "category",
    "question",
    "expected_intent",
    "expected_keywords",
    "safety_level",
]


# ============================================================
# REQUIRED DATASETS
# ============================================================
#
# evaluation_questions.csv is the actual evaluation dataset.
#
# Symptom2Disease.csv is retained as the project's main
# disease dataset and is checked during environment validation.
#
# Missing old files such as:
#
#   medical_qa.csv
#   DiseaseAndSymptoms.csv
#
# are NOT required.
# ============================================================

REQUIRED_DATASETS = [
    os.path.join(
        PROJECT_ROOT,
        "datasets",
        "Symptom2Disease.csv",
    ),
]


# ============================================================
# CUSTOM VALIDATION ERROR
# ============================================================

class EvaluationValidationError(Exception):
    """Raised when evaluation pre-flight validation fails."""
    pass


# ============================================================
# LOAD AND VALIDATE QUESTIONS
# ============================================================

def load_and_validate_questions():
    """
    Load and validate evaluation_questions.csv.

    Returns:
        list[dict]
    """

    # --------------------------------------------------------
    # FILE EXISTS
    # --------------------------------------------------------

    if not os.path.exists(QUESTIONS_FILE):

        raise EvaluationValidationError(
            "evaluation_questions.csv not found at:\n"
            f"{QUESTIONS_FILE}"
        )


    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            QUESTIONS_FILE
        )

    except Exception as error:

        raise EvaluationValidationError(
            "Could not read evaluation_questions.csv:\n"
            f"{type(error).__name__}: {error}"
        )


    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        raise EvaluationValidationError(
            "evaluation_questions.csv is missing "
            f"columns: {missing_columns}"
        )


    # --------------------------------------------------------
    # REMOVE ROWS WITHOUT ID OR QUESTION
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "question_id",
            "question",
        ]
    )


    if df.empty:

        raise EvaluationValidationError(
            "evaluation_questions.csv has no valid rows."
        )


    # --------------------------------------------------------
    # QUESTION ID AS STRING
    # --------------------------------------------------------

    df["question_id"] = (
        df["question_id"]
        .astype(str)
        .str.strip()
    )


    # --------------------------------------------------------
    # QUESTION TEXT AS STRING
    # --------------------------------------------------------

    df["question"] = (
        df["question"]
        .astype(str)
        .str.strip()
    )


    # --------------------------------------------------------
    # CHECK EMPTY QUESTION IDS
    # --------------------------------------------------------

    empty_ids = df[
        df["question_id"] == ""
    ]

    if not empty_ids.empty:

        raise EvaluationValidationError(
            "One or more questions have an empty "
            "question_id."
        )


    # --------------------------------------------------------
    # CHECK DUPLICATE IDS
    # --------------------------------------------------------

    duplicate_mask = (
        df["question_id"].duplicated(
            keep=False
        )
    )

    if duplicate_mask.any():

        duplicates = sorted(
            df.loc[
                duplicate_mask,
                "question_id",
            ]
            .unique()
            .tolist()
        )

        raise EvaluationValidationError(
            "evaluation_questions.csv has duplicate "
            f"question_id values: {duplicates}"
        )


    # --------------------------------------------------------
    # CHECK EMPTY QUESTION TEXT
    # --------------------------------------------------------

    empty_questions = df[
        df["question"].str.strip() == ""
    ]

    if not empty_questions.empty:

        ids = (
            empty_questions[
                "question_id"
            ]
            .tolist()
        )

        raise EvaluationValidationError(
            "The following questions have empty "
            f"question text: {ids}"
        )


    # --------------------------------------------------------
    # RETURN DICTIONARY ROWS
    # --------------------------------------------------------

    return df.to_dict(
        orient="records"
    )


# ============================================================
# ENVIRONMENT VALIDATION
# ============================================================

def validate_environment():
    """
    Validate the evaluation dataset, required datasets,
    and availability of the three chatbot architectures.

    Returns:
        dict
    """

    questions = load_and_validate_questions()


    # --------------------------------------------------------
    # DATASET CHECK
    # --------------------------------------------------------

    missing_datasets = [
        path
        for path in REQUIRED_DATASETS
        if not os.path.exists(path)
    ]


    # --------------------------------------------------------
    # CHATBOT AVAILABILITY
    # --------------------------------------------------------

    try:

        availability = check_chatbots_available()

    except Exception as error:

        availability = {}

        availability_error = (
            f"{type(error).__name__}: {error}"
        )

    else:

        availability_error = None


    selected_availability = {}


    for chatbot_name in CHATBOT_NAMES:

        if chatbot_name in availability:

            selected_availability[
                chatbot_name
            ] = availability[
                chatbot_name
            ]

        else:

            selected_availability[
                chatbot_name
            ] = {
                "available": False,
                "error": (
                    f"{chatbot_name} is not registered "
                    "in chatbot_adapter."
                ),
            }


    if availability_error:

        for chatbot_name in CHATBOT_NAMES:

            selected_availability[
                chatbot_name
            ] = {
                "available": False,
                "error": availability_error,
            }


    return {
        "questions_loaded": len(
            questions
        ),

        "missing_datasets": missing_datasets,

        "chatbot_availability":
            selected_availability,

        "all_chatbots_available": all(
            info.get(
                "available",
                False,
            )
            for info in selected_availability.values()
        ),
    }


# ============================================================
# SCORE ONE RESPONSE
# ============================================================

def _score_single_result(
    question_row,
    chatbot_name,
    adapter_result,
):
    """
    Score one chatbot response.

    Returns a dictionary matching the
    evaluation_results database table.
    """

    question_id = str(
        question_row[
            "question_id"
        ]
    ).strip()


    # --------------------------------------------------------
    # RESPONSE TIME
    # --------------------------------------------------------

    response_time = (
        adapter_result.get(
            "response_time_ms"
        )
    )

    if response_time is None:
        response_time = 0.0

    try:
        response_time = float(
            response_time
        )

    except (
        TypeError,
        ValueError,
    ):
        response_time = 0.0


    response_time = max(
        response_time,
        0.0,
    )


    # --------------------------------------------------------
    # BASIC RESULT
    # --------------------------------------------------------

    base = {

        "question_id":
            question_id,

        "category":
            question_row.get(
                "category"
            ),

        "chatbot_name":
            chatbot_name,

        "question":
            question_row.get(
                "question",
                "",
            ),

        "response":
            adapter_result.get(
                "response"
            ) or "",

        "response_time_ms":
            response_time,
    }


    # --------------------------------------------------------
    # CHATBOT ERROR
    # --------------------------------------------------------

    if not adapter_result.get(
        "success",
        False,
    ):

        base.update({

            "correctness_score":
                None,

            "keyword_score":
                None,

            "intent_score":
                None,

            "semantic_score":
                None,

            "safety_score":
                None,

            "safety_level":
                None,

            "overall_quality_score":
                None,

            "is_error":
                True,

            "error_message":
                (
                    adapter_result.get(
                        "error"
                    )
                    or
                    "Unknown chatbot error"
                ),
        })

        return base


    # --------------------------------------------------------
    # ANSWER EVALUATION
    # --------------------------------------------------------

    answer_scores = evaluate_answer(

        base["response"],

        question_row.get(
            "expected_intent"
        ),

        question_row.get(
            "expected_keywords"
        ),
    )


    # --------------------------------------------------------
    # SAFETY EVALUATION
    # --------------------------------------------------------

    safety_scores = evaluate_safety(

        base["response"],

        question_row.get(
            "safety_level",
            "normal",
        ),
    )


    # --------------------------------------------------------
    # OVERALL QUALITY
    # --------------------------------------------------------

    quality_score = compute_quality_score(

        answer_scores[
            "correctness_score"
        ],

        safety_scores[
            "safety_score"
        ],
    )


    # --------------------------------------------------------
    # SAVE SCORES
    # --------------------------------------------------------

    base.update({

        "correctness_score":
            answer_scores[
                "correctness_score"
            ],

        "keyword_score":
            answer_scores[
                "keyword_score"
            ],

        "intent_score":
            answer_scores[
                "intent_score"
            ],

        "semantic_score":
            answer_scores[
                "semantic_score"
            ],

        "safety_score":
            safety_scores[
                "safety_score"
            ],

        "safety_level":
            safety_scores[
                "safety_level"
            ],

        "overall_quality_score":
            quality_score,

        "is_error":
            False,

        "error_message":
            None,
    })


    return base


# ============================================================
# RUN EVALUATION
# ============================================================

def run_evaluation(
    run_label=None,
    force=False,
    progress_callback=None,
):
    """
    Run all questions through exactly three architectures.

    Expected:

        300 questions
        x 3 architectures
        = 900 responses

    Every successfully saved response is counted.
    """

    # --------------------------------------------------------
    # EVENT HELPER
    # --------------------------------------------------------

    def emit(
        event_type,
        **kwargs,
    ):

        if progress_callback:

            try:

                progress_callback({
                    "type": event_type,
                    **kwargs,
                })

            except Exception:

                # Progress reporting must never interrupt
                # the actual evaluation.
                pass


    # --------------------------------------------------------
    # CHECK EXISTING RUN
    # --------------------------------------------------------

    if (
        not force
        and db.has_running_evaluation()
    ):

        raise EvaluationValidationError(
            "An evaluation run is already in progress. "
            "Wait for it to finish, or use --force."
        )


    # --------------------------------------------------------
    # LOAD QUESTIONS
    # --------------------------------------------------------

    emit(
        "loading_questions"
    )

    questions = (
        load_and_validate_questions()
    )


    # --------------------------------------------------------
    # VERIFY ARCHITECTURES
    # --------------------------------------------------------

    if len(
        CHATBOT_NAMES
    ) != 3:

        raise EvaluationValidationError(
            "Evaluation configuration error: "
            "exactly 3 architectures are required."
        )


    # --------------------------------------------------------
    # CREATE DATABASE RUN
    # --------------------------------------------------------

    run_id = db.create_evaluation_run(

        run_label=run_label,

        total_questions=len(
            questions
        ),

        total_chatbots=len(
            CHATBOT_NAMES
        ),
    )


    if run_id is None:

        raise EvaluationValidationError(
            "Could not create evaluation run record "
            "in the database."
        )


    emit(

        "run_created",

        run_id=run_id,

        total_questions=len(
            questions
        ),

        total_chatbots=len(
            CHATBOT_NAMES
        ),
    )


    total_responses_saved = 0


    # ========================================================
    # MAIN EVALUATION
    # ========================================================

    try:

        for chatbot_name in CHATBOT_NAMES:

            emit(

                "testing_chatbot",

                chatbot_name=chatbot_name,
            )


            for question_row in questions:

                # ------------------------------------------------
                # GET CHATBOT RESPONSE
                # ------------------------------------------------

                try:

                    adapter_result = get_response(

                        chatbot_name,

                        question_row[
                            "question"
                        ],
                    )

                except Exception as error:

                    adapter_result = {

                        "success": False,

                        "response": "",

                        "response_time_ms":
                            0.0,

                        "error":
                            (
                                f"{type(error).__name__}: "
                                f"{error}"
                            ),
                    }


                # ------------------------------------------------
                # SCORE
                # ------------------------------------------------

                result_row = _score_single_result(

                    question_row,

                    chatbot_name,

                    adapter_result,
                )


                # ------------------------------------------------
                # SAVE TO DATABASE
                # ------------------------------------------------

                saved_id = (
                    db.save_evaluation_result(
                        run_id,
                        result_row,
                    )
                )


                # IMPORTANT:
                # Only count the response when SQLite confirms
                # that the row was actually inserted.

                if saved_id is None:

                    raise EvaluationValidationError(
                        "Failed to save evaluation result "
                        f"for {chatbot_name}, "
                        f"question "
                        f"{result_row['question_id']}."
                    )


                total_responses_saved += 1


                # ------------------------------------------------
                # PROGRESS
                # ------------------------------------------------

                emit(

                    "question_done",

                    chatbot_name=chatbot_name,

                    question_id=result_row[
                        "question_id"
                    ],

                    is_error=result_row[
                        "is_error"
                    ],

                    saved_id=saved_id,
                )


            # ----------------------------------------------------
            # CHATBOT COMPLETE
            # ----------------------------------------------------

            emit(

                "chatbot_done",

                chatbot_name=chatbot_name,
            )


        # ========================================================
        # CALCULATING METRICS
        # ========================================================

        emit(
            "calculating_metrics"
        )


        # ========================================================
        # VERIFY EXPECTED RESPONSE COUNT
        # ========================================================

        expected_responses = (
            len(questions)
            * len(CHATBOT_NAMES)
        )


        if (
            total_responses_saved
            != expected_responses
        ):

            raise EvaluationValidationError(

                "Evaluation response count mismatch. "

                f"Expected {expected_responses}, "

                f"but successfully saved "
                f"{total_responses_saved}."
            )


        # ========================================================
        # VERIFY DATABASE COUNT
        # ========================================================

        try:

            stored_results = (
                db.get_evaluation_results(
                    run_id
                )
            )

            database_count = len(
                stored_results
            )

        except Exception as error:

            raise EvaluationValidationError(
                "Evaluation finished, but database "
                "verification failed: "
                f"{type(error).__name__}: {error}"
            )


        if database_count != expected_responses:

            raise EvaluationValidationError(

                "Database verification failed. "

                f"Expected {expected_responses} "
                f"stored rows, "

                f"but found {database_count}."
            )


        # ========================================================
        # COMPLETE RUN
        # ========================================================

        finished = db.finish_evaluation_run(

            run_id,

            status="completed",

            total_responses=
                total_responses_saved,
        )


        if not finished:

            raise EvaluationValidationError(
                "Evaluation results were saved, "
                "but the run could not be marked "
                "as completed."
            )


        # ========================================================
        # COMPLETED EVENT
        # ========================================================

        emit(

            "completed",

            run_id=run_id,

            total_responses=
                total_responses_saved,

        )


        return {

            "run_id":
                run_id,

            "status":
                "completed",

            "total_questions":
                len(questions),

            "total_chatbots":
                len(CHATBOT_NAMES),

            "total_responses":
                total_responses_saved,

            "database_rows":
                database_count,
        }


    # ========================================================
    # FAILURE
    # ========================================================

    except Exception as error:

        error_message = (
            f"{type(error).__name__}: "
            f"{error}"
        )


        db.finish_evaluation_run(

            run_id,

            status="failed",

            total_responses=
                total_responses_saved,

            error_message=
                error_message,
        )


        emit(

            "failed",

            run_id=run_id,

            error=error_message,

        )


        raise


# ============================================================
# COMMAND LINE
# ============================================================

def main():

    parser = argparse.ArgumentParser(

        description=(
            "Run the MediChat automated "
            "3-architecture evaluation."
        )
    )


    parser.add_argument(

        "--label",

        type=str,

        default=None,

        help=(
            "Optional label for this "
            "evaluation run."
        ),
    )


    parser.add_argument(

        "--force",

        action="store_true",

        help=(
            "Run even if another evaluation "
            "is marked as running."
        ),
    )


    args = parser.parse_args()


    # --------------------------------------------------------
    # TERMINAL PROGRESS
    # --------------------------------------------------------

    def print_progress(event):

        event_type = event.get(
            "type",
            "event",
        )


        if event_type == "question_done":

            print(

                f"[question_done] "

                f"{event.get('chatbot_name')} "

                f"{event.get('question_id')} "

                f"saved={event.get('saved_id')} "

                f"error={event.get('is_error')}"
            )

        else:

            print(
                f"[{event_type}] {event}"
            )


    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    try:

        summary = run_evaluation(

            run_label=args.label,

            force=args.force,

            progress_callback=
                print_progress,
        )


    except EvaluationValidationError as error:

        print(
            "\n[EVALUATION ERROR]"
        )

        print(
            str(error)
        )

        return 1


    except KeyboardInterrupt:

        print(
            "\n\nEvaluation cancelled by user."
        )

        return 130


    except Exception as error:

        print(
            "\n[EVALUATION FAILED]"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return 1


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "Evaluation completed successfully."
    )

    print(
        "========================================"
    )

    print(
        f"Run ID: {summary['run_id']}"
    )

    print(
        f"Questions: "
        f"{summary['total_questions']}"
    )

    print(
        f"Architectures: "
        f"{summary['total_chatbots']}"
    )

    print(
        f"Responses saved: "
        f"{summary['total_responses']}"
    )

    print(
        f"Database rows verified: "
        f"{summary['database_rows']}"
    )

    print(
        "========================================"
    )


    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )