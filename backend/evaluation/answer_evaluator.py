"""
MediChat Answer Evaluator

Scores chatbot responses using:
1. Keyword coverage
2. Intent matching
3. Lightweight text similarity

This evaluator intentionally does NOT use scikit-learn or SciPy.
It is designed to work with the current Python environment.
"""

import re
import math
from collections import Counter


CORRECTNESS_THRESHOLD = 50.0

# Weights must sum to 1.0
WEIGHT_KEYWORD = 0.5
WEIGHT_SEMANTIC = 0.3
WEIGHT_INTENT = 0.2


def _normalize(text):
    """Normalize text for comparison."""
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text):
    """Convert text into simple word tokens."""
    return re.findall(r"\b[a-z0-9]+\b", _normalize(text))


def _parse_keywords(expected_keywords):
    """Convert comma-separated keywords into a clean list."""
    if not expected_keywords:
        return []

    return [
        kw.strip().lower()
        for kw in str(expected_keywords).split(",")
        if kw.strip()
    ]


def calculate_keyword_score(response_text, expected_keywords):
    """
    Percentage of expected keywords/phrases found in the response.
    """

    keywords = _parse_keywords(expected_keywords)

    if not keywords:
        return 100.0

    response_norm = _normalize(response_text)

    if not response_norm:
        return 0.0

    matched = 0

    for keyword in keywords:
        keyword_norm = _normalize(keyword)

        if keyword_norm and keyword_norm in response_norm:
            matched += 1

    return round((matched / len(keywords)) * 100.0, 2)


def calculate_intent_score(
    response_text,
    expected_intent,
    expected_keywords
):
    """
    Checks whether the chatbot response addresses the
    expected intent.
    """

    response_norm = _normalize(response_text)

    if not response_norm:
        return 0.0

    intent_phrase = _normalize(
        str(expected_intent or "").replace("_", " ")
    )

    # Direct intent phrase match
    if intent_phrase and intent_phrase in response_norm:
        return 100.0

    keywords = _parse_keywords(expected_keywords)

    if keywords:
        matched = 0

        for keyword in keywords:
            keyword_norm = _normalize(keyword)

            if keyword_norm and keyword_norm in response_norm:
                matched += 1

        if matched >= 2:
            return 80.0

        if matched == 1:
            return 60.0

    return 0.0


def _cosine_similarity(tokens_a, tokens_b):
    """
    Lightweight cosine similarity using Python only.

    This replaces sklearn's cosine_similarity.
    """

    if not tokens_a or not tokens_b:
        return 0.0

    counts_a = Counter(tokens_a)
    counts_b = Counter(tokens_b)

    common = set(counts_a) & set(counts_b)

    if not common:
        return 0.0

    dot_product = sum(
        counts_a[word] * counts_b[word]
        for word in common
    )

    magnitude_a = math.sqrt(
        sum(value * value for value in counts_a.values())
    )

    magnitude_b = math.sqrt(
        sum(value * value for value in counts_b.values())
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def calculate_semantic_score(
    response_text,
    expected_intent,
    expected_keywords
):
    """
    Lightweight lexical similarity score.

    This is NOT a deep-learning semantic embedding.
    It measures vocabulary overlap between the expected
    concept and the chatbot response.
    """

    response_tokens = _tokenize(response_text)

    reference_parts = [
        str(expected_intent or "").replace("_", " ")
    ]

    reference_parts.extend(
        _parse_keywords(expected_keywords)
    )

    reference_text = " ".join(reference_parts)

    reference_tokens = _tokenize(reference_text)

    if not response_tokens or not reference_tokens:
        return 0.0

    similarity = _cosine_similarity(
        reference_tokens,
        response_tokens
    )

    return round(similarity * 100.0, 2)


def evaluate_answer(
    response_text,
    expected_intent,
    expected_keywords
):
    """
    Calculate all answer-quality metrics.
    """

    keyword_score = calculate_keyword_score(
        response_text,
        expected_keywords
    )

    intent_score = calculate_intent_score(
        response_text,
        expected_intent,
        expected_keywords
    )

    semantic_score = calculate_semantic_score(
        response_text,
        expected_intent,
        expected_keywords
    )

    correctness_score = round(
        (keyword_score * WEIGHT_KEYWORD)
        +
        (semantic_score * WEIGHT_SEMANTIC)
        +
        (intent_score * WEIGHT_INTENT),
        2
    )

    return {
        "keyword_score": keyword_score,
        "intent_score": intent_score,
        "semantic_score": semantic_score,
        "correctness_score": correctness_score,
        "is_correct": (
            correctness_score >= CORRECTNESS_THRESHOLD
        ),
    }


if __name__ == "__main__":

    print("Testing MediChat answer evaluator...")
    print()

    sample_response = (
        "Fever commonly causes an elevated body temperature "
        "and may be accompanied by sweating, chills, and headache."
    )

    result = evaluate_answer(
        sample_response,
        expected_intent="fever",
        expected_keywords="fever,temperature,sweating",
    )

    print("Evaluation result:")
    print(result)