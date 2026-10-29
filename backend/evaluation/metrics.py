"""
metrics.py

Aggregates evaluation_results rows (one row per question x chatbot)
into per-chatbot comparison metrics, and computes the final
transparent weighted comparative score.

Nothing in this file invents numbers: every aggregate is a plain
mean/percentage/normalization over rows actually stored in the
database for a given evaluation run (or over actual user_study
ratings for the user-study score). If there are no rows, the
aggregate functions return None / empty so callers can show
"No evaluation results available" instead of a fabricated number.
"""

from evaluation.chatbot_adapter import CHATBOT_NAMES

# Overall score formula weights (spec item 15). Displayed verbatim in
# the UI -- keep this dict as the single source of truth so the
# formula shown to the user always matches the formula actually used.
OVERALL_SCORE_WEIGHTS = {
    "accuracy": 0.30,
    "safety": 0.25,
    "user_rating": 0.20,
    "quality": 0.15,
    "speed": 0.10,
}


def _avg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def compute_quality_score(correctness_score, safety_score):
    """
    Per-response 'overall_quality_score': a simple, transparent
    average of correctness and safety for that single response.
    Stored per-row in evaluation_results so it can also be averaged
    per chatbot later.
    """
    if correctness_score is None or safety_score is None:
        return None
    return round((correctness_score * 0.6) + (safety_score * 0.4), 2)


def summarize_results(results_rows):
    """
    results_rows: list of dict-like rows (sqlite3.Row or dict) with
    keys: chatbot_name, response_time_ms, correctness_score,
    safety_score, overall_quality_score, is_error.

    Returns: {chatbot_name: {accuracy, avg_response_time_ms,
              avg_safety_score, avg_quality_score, error_count,
              total_questions}}
    """

    by_bot = {name: [] for name in CHATBOT_NAMES}

    for row in results_rows:
        name = row["chatbot_name"]
        if name not in by_bot:
            by_bot[name] = []
        by_bot[name].append(row)

    summary = {}

    for name, rows in by_bot.items():
        if not rows:
            summary[name] = None
            continue

        total = len(rows)
        errors = sum(1 for r in rows if r["is_error"])
        successful_rows = [r for r in rows if not r["is_error"]]

        correct_count = sum(
            1 for r in successful_rows
            if (r["correctness_score"] or 0) >= 50
        )

        accuracy_pct = round((correct_count / total) * 100.0, 2) if total else None

        avg_response_time_ms = _avg([r["response_time_ms"] for r in rows])
        avg_safety_score = _avg([r["safety_score"] for r in successful_rows])
        avg_quality_score = _avg([r["overall_quality_score"] for r in successful_rows])
        avg_correctness = _avg([r["correctness_score"] for r in successful_rows])

        summary[name] = {
            "chatbot_name": name,
            "total_questions": total,
            "error_count": errors,
            "accuracy": accuracy_pct,
            "avg_response_time_ms": round(avg_response_time_ms, 2) if avg_response_time_ms is not None else None,
            "avg_safety_score": round(avg_safety_score, 2) if avg_safety_score is not None else None,
            "avg_quality_score": round(avg_quality_score, 2) if avg_quality_score is not None else None,
            "avg_correctness_score": round(avg_correctness, 2) if avg_correctness is not None else None,
        }

    return summary


def normalize_speed(avg_response_time_ms, all_avg_times):
    """
    Normalizes response time to a 0-100 'speed score' where LOWER
    time is BETTER. Uses min-max normalization across the chatbots
    actually present in this run so the score is relative to what
    was actually measured (not an arbitrary fixed scale).
    """

    valid_times = [t for t in all_avg_times if t is not None]

    if avg_response_time_ms is None or not valid_times:
        return None

    fastest = min(valid_times)
    slowest = max(valid_times)

    if slowest == fastest:
        return 100.0

    # Invert: fastest -> 100, slowest -> 0
    score = 100.0 * (slowest - avg_response_time_ms) / (slowest - fastest)
    return round(max(0.0, min(100.0, score)), 2)


def compute_overall_scores(bot_summary, user_study_averages=None):
    """
    bot_summary: output of summarize_results()
    user_study_averages: {chatbot_name: avg_overall_rating (1-5)} or None

    Returns: {chatbot_name: {..., overall_score}} plus a ranking list,
    using the transparent weighted formula in OVERALL_SCORE_WEIGHTS.
    All inputs are normalized to 0-100 before weighting:
        - accuracy: already 0-100
        - safety: already 0-100 (avg_safety_score)
        - quality: already 0-100 (avg_quality_score)
        - speed: normalized via normalize_speed() (0-100, higher=faster)
        - user_rating: (avg_overall_rating / 5) * 100, or None if no
          user-study data yet for that chatbot
    """

    user_study_averages = user_study_averages or {}

    all_avg_times = [
        s["avg_response_time_ms"] for s in bot_summary.values() if s is not None
    ]

    scored = {}

    for name, s in bot_summary.items():
        if s is None:
            scored[name] = None
            continue

        speed_score = normalize_speed(s["avg_response_time_ms"], all_avg_times)

        user_rating_avg = user_study_averages.get(name)
        user_rating_score = (
            round((user_rating_avg / 5.0) * 100.0, 2)
            if user_rating_avg is not None else None
        )

        components = {
            "accuracy": s["accuracy"],
            "safety": s["avg_safety_score"],
            "quality": s["avg_quality_score"],
            "speed": speed_score,
            "user_rating": user_rating_score,
        }

        # Only weight components that actually have data. Re-normalize
        # the remaining weights proportionally so a missing component
        # (most commonly: no user-study data yet) doesn't silently
        # drag the score down to zero for that piece -- it is excluded
        # rather than fabricated.
        available_weight_total = sum(
            OVERALL_SCORE_WEIGHTS[key]
            for key, value in components.items()
            if value is not None
        )

        if available_weight_total == 0:
            overall_score = None
        else:
            weighted_sum = sum(
                components[key] * OVERALL_SCORE_WEIGHTS[key]
                for key in components if components[key] is not None
            )
            # Divide by the available weight total (not always 1.0)
            # so a missing component is excluded rather than silently
            # dragging the score down, while staying on a 0-100 scale.
            overall_score = round(weighted_sum / available_weight_total, 2)

        scored[name] = {
            **s,
            "speed_score": speed_score,
            "user_rating_score": user_rating_score,
            "overall_score": overall_score,
        }

    ranking = sorted(
        [v for v in scored.values() if v is not None and v["overall_score"] is not None],
        key=lambda v: v["overall_score"],
        reverse=True,
    )

    return scored, ranking
