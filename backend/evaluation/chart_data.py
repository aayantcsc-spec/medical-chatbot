"""
MediChat - Visual Analytics / Chart Data

Project:
Comparative Analysis of Health Chatbots Based on Framework and Architecture

Architectures:
1. Rule-Based
2. Machine Learning
3. Deep Learning

This module:
- Reads the latest completed evaluation run
- Converts sqlite3.Row objects into normal dictionaries
- Calculates real evaluation metrics
- Builds chart-ready JSON data
- Does NOT create fake/demo evaluation values
- Does NOT calculate unsupported Precision/Recall/F1 values
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import math

from database import database as db
from evaluation.chatbot_adapter import CHATBOT_NAMES


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Convert a value safely to float.
    Returns default when conversion is not possible.
    """
    if value is None:
        return default

    try:
        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """
    Convert a value safely to int.
    """
    if value is None:
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _round(value: Any, digits: int = 2) -> float:
    """
    Safe rounded float.
    """
    number = _safe_float(value, 0.0)

    if number is None:
        return 0.0

    return round(number, digits)


def _normalise_rows(rows: Any) -> List[Dict[str, Any]]:
    """
    Convert database rows into normal Python dictionaries.

    IMPORTANT:
    SQLite queries often return sqlite3.Row objects.
    sqlite3.Row does NOT have .get(), so code such as:

        row.get("chatbot_name")

    crashes.

    This function converts:
        sqlite3.Row -> dict
        dict -> dict

    and safely handles unexpected row types.
    """

    if not rows:
        return []

    normalised: List[Dict[str, Any]] = []

    for row in rows:

        # Already a normal dictionary
        if isinstance(row, dict):
            normalised.append(dict(row))
            continue

        # sqlite3.Row
        try:
            keys = row.keys()

            converted = {}

            for key in keys:
                converted[key] = row[key]

            normalised.append(converted)
            continue

        except AttributeError:
            pass

        # Generic mapping-like object
        try:
            normalised.append(dict(row))
            continue

        except (TypeError, ValueError):
            pass

    return normalised


# ============================================================
# DATABASE / EVALUATION DATA
# ============================================================

def _latest_run_results() -> Optional[List[Dict[str, Any]]]:
    """
    Load results from the latest completed evaluation run.

    Returns:
        list of normal dictionaries

    Returns None when there is no completed evaluation run.
    """

    try:
        run = db.get_latest_completed_run()
    except Exception:
        return None

    if not run:
        return None

    # Convert run itself in case database returns sqlite3.Row
    try:
        if not isinstance(run, dict):
            run = {
                key: run[key]
                for key in run.keys()
            }
    except AttributeError:
        try:
            run = dict(run)
        except Exception:
            return None

    run_id = run.get("id")

    if run_id is None:
        run_id = run.get("run_id")

    if run_id is None:
        return None

    try:
        rows = db.get_evaluation_results(run_id)
    except Exception:
        return None

    rows = _normalise_rows(rows)

    if not rows:
        return None

    return rows


# ============================================================
# BOT / ARCHITECTURE NAME HELPERS
# ============================================================

def _bot_label(name: Any) -> str:
    """
    Convert internal chatbot name into display name.
    """

    if name is None:
        return "Unknown"

    value = str(name).strip()

    lookup = {
        "rule": "Rule-Based",
        "rule_based": "Rule-Based",
        "Rule-Based": "Rule-Based",
        "Rule Based": "Rule-Based",

        "ml": "Machine Learning",
        "machine_learning": "Machine Learning",
        "Machine Learning": "Machine Learning",

        "classification": "Machine Learning",
        "classification_based": "Machine Learning",

        "nlp": "Machine Learning",
        "nlp_based": "Machine Learning",
        "NLP-Based": "Machine Learning",

        "dl": "Deep Learning",
        "deep_learning": "Deep Learning",
        "Deep Learning": "Deep Learning",

        "retrieval_based": "Deep Learning",
        "retrieval": "Deep Learning",

        "rag_based": "Deep Learning",
        "rag": "Deep Learning",

        "generation_based": "Deep Learning",
        "generation": "Deep Learning",
    }

    return lookup.get(value, value)


def _architecture_names(rows: List[Dict[str, Any]]) -> List[str]:
    """
    Return architectures actually present in evaluation results.

    Preferred project order:
        Rule-Based
        Machine Learning
        Deep Learning
    """

    found = set()

    for row in rows:

        name = row.get("chatbot_name")

        if name is None:
            name = row.get("architecture")

        if name is None:
            name = row.get("bot_type")

        if name is None:
            continue

        found.add(_bot_label(name))

    preferred_order = [
        "Rule-Based",
        "Machine Learning",
        "Deep Learning",
    ]

    result = []

    for architecture in preferred_order:
        if architecture in found:
            result.append(architecture)

    # Preserve any unexpected architecture names
    for architecture in sorted(found):
        if architecture not in result:
            result.append(architecture)

    return result


# ============================================================
# NUMERIC METRIC HELPERS
# ============================================================

def _metric_values(
    rows: List[Dict[str, Any]],
    architecture: str,
    field: str,
) -> List[float]:

    values = []

    for row in rows:

        chatbot_name = row.get("chatbot_name")

        if chatbot_name is None:
            chatbot_name = row.get("architecture")

        if _bot_label(chatbot_name) != architecture:
            continue

        value = _safe_float(row.get(field))

        if value is not None:
            values.append(value)

    return values


def _average(
    rows: List[Dict[str, Any]],
    architecture: str,
    field: str,
) -> Optional[float]:

    values = _metric_values(
        rows,
        architecture,
        field,
    )

    if not values:
        return None

    return sum(values) / len(values)


def _percentage(
    rows: List[Dict[str, Any]],
    architecture: str,
    field: str,
) -> Optional[float]:

    value = _average(
        rows,
        architecture,
        field,
    )

    if value is None:
        return None

    # Evaluation scores are normally stored between 0 and 1.
    # If already stored as 0-100, keep them.
    if value <= 1:
        return value * 100

    return value


# ============================================================
# ARCHITECTURE SUMMARY
# ============================================================

def _architecture_summary(
    rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    architectures = _architecture_names(rows)

    summary = []

    for architecture in architectures:

        architecture_rows = [
            row
            for row in rows
            if _bot_label(
                row.get("chatbot_name")
                or row.get("architecture")
                or row.get("bot_type")
            ) == architecture
        ]

        total = len(architecture_rows)

        error_count = sum(
            1
            for row in architecture_rows
            if _safe_int(row.get("is_error"), 0) == 1
        )

        valid_rows = [
            row
            for row in architecture_rows
            if _safe_int(row.get("is_error"), 0) != 1
        ]

        correctness = _percentage(
            rows,
            architecture,
            "correctness_score",
        )

        safety = _percentage(
            rows,
            architecture,
            "safety_score",
        )

        quality = _percentage(
            rows,
            architecture,
            "overall_quality_score",
        )

        response_time = _average(
            rows,
            architecture,
            "response_time_ms",
        )

        summary.append({
            "architecture": architecture,
            "total_questions": total,
            "evaluated_responses": len(valid_rows),
            "errors": error_count,
            "correctness": (
                round(correctness, 2)
                if correctness is not None
                else None
            ),
            "safety": (
                round(safety, 2)
                if safety is not None
                else None
            ),
            "quality": (
                round(quality, 2)
                if quality is not None
                else None
            ),
            "response_time_ms": (
                round(response_time, 2)
                if response_time is not None
                else None
            ),
        })

    return summary


# ============================================================
# ACCURACY / CORRECTNESS CHART
# ============================================================

def _accuracy_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        value = _percentage(
            rows,
            architecture,
            "correctness_score",
        )

        data.append({
            "architecture": architecture,
            "accuracy": (
                round(value, 2)
                if value is not None
                else 0
            ),
        })

    return {
        "title": "Correctness Comparison",
        "description": (
            "Average correctness score calculated "
            "from the completed evaluation results."
        ),
        "data": data,
    }


# ============================================================
# PRECISION / RECALL / F1
# ============================================================

def _prf_chart(
    rows: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Precision, Recall and F1 are NOT calculated by the current
    evaluation runner.

    Therefore this function intentionally returns None.

    This prevents fake metrics from appearing in the dashboard.
    """

    required_fields = [
        "precision",
        "recall",
        "f1",
    ]

    if not rows:
        return None

    # Only produce this chart if actual fields exist.
    available = all(
        any(
            _safe_float(row.get(field)) is not None
            for row in rows
        )
        for field in required_fields
    )

    if not available:
        return None

    data = []

    for architecture in _architecture_names(rows):

        values = {}

        for field in required_fields:

            value = _percentage(
                rows,
                architecture,
                field,
            )

            values[field] = (
                round(value, 2)
                if value is not None
                else 0
            )

        data.append({
            "architecture": architecture,
            **values,
        })

    return {
        "title": "Precision, Recall and F1",
        "description": (
            "Metrics calculated from stored evaluation results."
        ),
        "data": data,
    }


# ============================================================
# RESPONSE TIME
# ============================================================

def _response_time_data(
    rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    data = []

    for architecture in _architecture_names(rows):

        value = _average(
            rows,
            architecture,
            "response_time_ms",
        )

        data.append({
            "architecture": architecture,
            "response_time_ms": (
                round(value, 2)
                if value is not None
                else 0
            ),
        })

    return data


def _response_time_comparison(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    return {
        "title": "Average Response Time",
        "description": (
            "Average response time measured during the "
            "evaluation run."
        ),
        "data": _response_time_data(rows),
    }


# ============================================================
# QUALITY
# ============================================================

def _quality_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        quality = _percentage(
            rows,
            architecture,
            "overall_quality_score",
        )

        data.append({
            "architecture": architecture,
            "quality": (
                round(quality, 2)
                if quality is not None
                else 0
            ),
        })

    return {
        "title": "Overall Response Quality",
        "description": (
            "Average overall quality score from the "
            "completed evaluation."
        ),
        "data": data,
    }


# ============================================================
# SAFETY
# ============================================================

def _safety_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        safety = _percentage(
            rows,
            architecture,
            "safety_score",
        )

        data.append({
            "architecture": architecture,
            "safety": (
                round(safety, 2)
                if safety is not None
                else 0
            ),
        })

    return {
        "title": "Safety Score Comparison",
        "description": (
            "Average safety score across the evaluated "
            "healthcare questions."
        ),
        "data": data,
    }


# ============================================================
# KEYWORD SCORE
# ============================================================

def _keyword_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        score = _percentage(
            rows,
            architecture,
            "keyword_score",
        )

        data.append({
            "architecture": architecture,
            "keyword_score": (
                round(score, 2)
                if score is not None
                else 0
            ),
        })

    return {
        "title": "Keyword Matching Score",
        "description": (
            "Average keyword matching score calculated "
            "from the evaluation results."
        ),
        "data": data,
    }


# ============================================================
# INTENT SCORE
# ============================================================

def _intent_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        score = _percentage(
            rows,
            architecture,
            "intent_score",
        )

        data.append({
            "architecture": architecture,
            "intent_score": (
                round(score, 2)
                if score is not None
                else 0
            ),
        })

    return {
        "title": "Intent Recognition Score",
        "description": (
            "Average intent recognition score calculated "
            "from the evaluation results."
        ),
        "data": data,
    }


# ============================================================
# SEMANTIC SCORE
# ============================================================

def _semantic_chart(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    data = []

    for architecture in _architecture_names(rows):

        score = _percentage(
            rows,
            architecture,
            "semantic_score",
        )

        data.append({
            "architecture": architecture,
            "semantic_score": (
                round(score, 2)
                if score is not None
                else 0
            ),
        })

    return {
        "title": "Semantic Similarity Score",
        "description": (
            "Average semantic score calculated from "
            "the evaluation results."
        ),
        "data": data,
    }


# ============================================================
# CATEGORY HEATMAP
# ============================================================

def _category_heatmap(
    rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    categories = sorted({
        str(row.get("category")).strip()
        for row in rows
        if row.get("category") not in (None, "")
    })

    architectures = _architecture_names(rows)

    data = []

    for category in categories:

        item = {
            "category": category
        }

        for architecture in architectures:

            category_rows = [
                row
                for row in rows
                if str(row.get("category")).strip() == category
                and _bot_label(
                    row.get("chatbot_name")
                    or row.get("architecture")
                    or row.get("bot_type")
                ) == architecture
            ]

            values = [
                _safe_float(
                    row.get("overall_quality_score")
                )
                for row in category_rows
            ]

            values = [
                value
                for value in values
                if value is not None
            ]

            if values:
                average = sum(values) / len(values)

                if average <= 1:
                    average *= 100

                item[architecture] = round(
                    average,
                    2,
                )

            else:
                item[architecture] = 0

        data.append(item)

    return data


# ============================================================
# QUESTION-BY-QUESTION ANALYSIS
# ============================================================

def _question_analysis(
    rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    data = []

    for row in rows:

        chatbot_name = (
            row.get("chatbot_name")
            or row.get("architecture")
            or row.get("bot_type")
        )

        correctness = _safe_float(
            row.get("correctness_score")
        )

        keyword = _safe_float(
            row.get("keyword_score")
        )

        intent = _safe_float(
            row.get("intent_score")
        )

        semantic = _safe_float(
            row.get("semantic_score")
        )

        safety = _safe_float(
            row.get("safety_score")
        )

        quality = _safe_float(
            row.get("overall_quality_score")
        )

        # Convert 0-1 values into percentages.
        metric_values = [
            correctness,
            keyword,
            intent,
            semantic,
            safety,
            quality,
        ]

        if any(
            value is not None and value <= 1
            for value in metric_values
        ):
            if correctness is not None:
                correctness *= 100

            if keyword is not None:
                keyword *= 100

            if intent is not None:
                intent *= 100

            if semantic is not None:
                semantic *= 100

            if safety is not None:
                safety *= 100

            if quality is not None:
                quality *= 100

        data.append({
            "question_id": row.get("question_id"),
            "category": row.get("category"),
            "architecture": _bot_label(chatbot_name),
            "question": row.get("question"),
            "response": row.get("response"),

            "correctness_score": (
                round(correctness, 2)
                if correctness is not None
                else None
            ),

            "keyword_score": (
                round(keyword, 2)
                if keyword is not None
                else None
            ),

            "intent_score": (
                round(intent, 2)
                if intent is not None
                else None
            ),

            "semantic_score": (
                round(semantic, 2)
                if semantic is not None
                else None
            ),

            "safety_score": (
                round(safety, 2)
                if safety is not None
                else None
            ),

            "overall_quality_score": (
                round(quality, 2)
                if quality is not None
                else None
            ),

            "response_time_ms": (
                round(
                    _safe_float(
                        row.get("response_time_ms"),
                        0,
                    ),
                    2,
                )
            ),

            "safety_level": row.get("safety_level"),

            "is_error": _safe_int(
                row.get("is_error"),
                0,
            ),

            "error_message": row.get(
                "error_message"
            ),
        })

    return data


# ============================================================
# RUN INFORMATION
# ============================================================

def _run_information(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:

    architectures = _architecture_names(rows)

    question_ids = {
        row.get("question_id")
        for row in rows
        if row.get("question_id") is not None
    }

    total_rows = len(rows)

    errors = sum(
        1
        for row in rows
        if _safe_int(row.get("is_error"), 0) == 1
    )

    successful = total_rows - errors

    return {
        "total_results": total_rows,
        "unique_questions": len(question_ids),
        "architectures": architectures,
        "architecture_count": len(architectures),
        "successful_results": successful,
        "error_results": errors,
        "has_real_data": total_rows > 0,
    }


# ============================================================
# MAIN DATASET BUILDER
# ============================================================

def build_chart_dataset() -> Dict[str, Any]:
    """
    Main function used by:

        /api/analysis/charts

    Returns a JSON-serialisable dictionary.

    IMPORTANT:
    No fake values are generated when evaluation data is absent.
    """

    rows = _latest_run_results()

    # --------------------------------------------------------
    # No completed evaluation
    # --------------------------------------------------------

    if not rows:

        return {
            "success": True,
            "has_real_data": False,

            "message": (
                "No completed evaluation results are available yet."
            ),

            "run": {
                "total_results": 0,
                "unique_questions": 0,
                "architectures": [],
                "architecture_count": 0,
                "successful_results": 0,
                "error_results": 0,
                "has_real_data": False,
            },

            "summary": [],

            "accuracy": {
                "title": "Correctness Comparison",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "prf": None,

            "response_time": {
                "title": "Average Response Time",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "quality": {
                "title": "Overall Response Quality",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "safety": {
                "title": "Safety Score Comparison",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "keyword": {
                "title": "Keyword Matching Score",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "intent": {
                "title": "Intent Recognition Score",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "semantic": {
                "title": "Semantic Similarity Score",
                "description": (
                    "No completed evaluation data available."
                ),
                "data": [],
            },

            "category_heatmap": [],

            "question_analysis": [],
        }

    # --------------------------------------------------------
    # Real completed evaluation exists
    # --------------------------------------------------------

    summary = _architecture_summary(rows)

    result = {
        "success": True,

        "has_real_data": True,

        "message": (
            "Visual analytics generated from the latest "
            "completed evaluation run."
        ),

        "run": _run_information(rows),

        "summary": summary,

        "accuracy": _accuracy_chart(rows),

        "prf": _prf_chart(rows),

        "response_time": _response_time_comparison(rows),

        "quality": _quality_chart(rows),

        "safety": _safety_chart(rows),

        "keyword": _keyword_chart(rows),

        "intent": _intent_chart(rows),

        "semantic": _semantic_chart(rows),

        "category_heatmap": _category_heatmap(rows),

        "question_analysis": _question_analysis(rows),
    }

    return result


# ============================================================
# OPTIONAL ALIASES
# ============================================================

def get_chart_data() -> Dict[str, Any]:
    """
    Backward-compatible alias.
    """
    return build_chart_dataset()


def load_chart_data() -> Dict[str, Any]:
    """
    Backward-compatible alias.
    """
    return build_chart_dataset()


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    import json

    print("=" * 70)
    print("MediChat Chart Data Test")
    print("=" * 70)

    try:

        data = build_chart_dataset()

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as exc:

        print()
        print("ERROR:")
        print(type(exc).__name__)
        print(str(exc))
        print()

        raise