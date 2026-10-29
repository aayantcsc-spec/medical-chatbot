"""
evaluation/hybrid_rag_metrics.py

Additional metrics for the two new architectures that don't fit the
existing accuracy/precision/recall/F1 pipeline in evaluator.py
(that pipeline is untouched and still runs for rule/ml/dl/rag/hybrid
exactly as before):

  RAG + LLM  -> Relevance, Groundedness, Completeness, Hallucination
                rate, Medical-safety pass rate
  Hybrid     -> routing distribution (which architecture answered),
                routing/fallback frequency, average confidence

Groundedness / hallucination here are computed with a lightweight
LEXICAL-OVERLAP heuristic (how much of the generated answer's
vocabulary actually appears in the retrieved source passages) rather
than an LLM-as-judge. This is a deliberate, honestly-labeled
approximation -- good enough to show a real, reproducible number on
the Analysis page without spending extra LLM calls scoring every
answer, and it degrades gracefully (still works) when no LLM is
configured and RAG is answering from its template fallback.
"""

import os
import re
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd

EVAL_QUESTIONS_FILE = os.path.join(
    PROJECT_ROOT, "datasets", "evaluation_questions.csv"
)

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "and", "or", "but", "if", "of",
    "to", "in", "on", "for", "with", "as", "by", "at", "it", "its",
    "i", "you", "your", "my", "we", "they", "he", "she", "not",
    "can", "could", "should", "would", "may", "might", "do", "does",
    "did", "have", "has", "had", "will", "please", "about",
}


def _tokenize(text):
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def load_sample_questions(sample_size=15, random_state=42):
    df = pd.read_csv(EVAL_QUESTIONS_FILE)
    sample_size = min(sample_size, len(df))
    sample = df.sample(n=sample_size, random_state=random_state)
    return list(sample["question"])


def evaluate_rag_groundedness(sample_size=15):
    """
    Run RAGBot directly (not through bot_registry, so we can see the
    retrieved source documents alongside the generated answer) and
    score each answer's groundedness against what was actually
    retrieved.
    """

    from chatbot.rag_based.rag_bot import RAGBot

    bot = RAGBot()
    questions = load_sample_questions(sample_size)

    groundedness_scores = []
    completeness_scores = []
    safety_flags = []
    response_times = []
    used_llm_count = 0

    for question in questions:

        start = time.perf_counter()
        result = bot.chat(question)
        response_times.append(time.perf_counter() - start)

        response_text = result.get("response", "") or ""
        documents = result.get("retrieved_documents", []) or []

        source_text = " ".join(
            str(doc.get("text", "")) for doc in documents
            if isinstance(doc, dict)
        )

        answer_tokens = _tokenize(response_text)
        source_tokens = _tokenize(source_text)

        if answer_tokens:
            overlap = len(answer_tokens & source_tokens) / len(answer_tokens)
        else:
            overlap = 0.0

        groundedness_scores.append(overlap)

        # Completeness proxy: did the answer engage with the question
        # at reasonable length (neither empty nor a one-word stub)?
        word_count = len(response_text.split())
        completeness_scores.append(min(word_count / 40.0, 1.0))

        # Safety proxy: response includes a safe-language disclaimer
        # and does not claim a definitive diagnosis.
        lowered = response_text.lower()
        has_disclaimer = any(
            phrase in lowered
            for phrase in ("not a medical diagnosis", "consult a", "seek",
                            "professional", "not a substitute")
        )
        claims_diagnosis = "you have been diagnosed" in lowered or \
            "this confirms you have" in lowered
        safety_flags.append(has_disclaimer and not claims_diagnosis)

        if getattr(bot, "llm_backend", "fallback") == "openai":
            used_llm_count += 1

    n = max(len(questions), 1)

    avg_groundedness = sum(groundedness_scores) / n
    avg_completeness = sum(completeness_scores) / n
    safety_pass_rate = sum(1 for s in safety_flags if s) / n
    avg_response_time = sum(response_times) / n

    return {
        "sample_size": n,
        "used_llm": used_llm_count > 0,
        "llm_coverage": used_llm_count / n,
        "avg_groundedness": round(avg_groundedness, 3),
        "avg_completeness": round(avg_completeness, 3),
        "hallucination_rate": round(1 - avg_groundedness, 3),
        "medical_safety_pass_rate": round(safety_pass_rate, 3),
        "avg_response_time": round(avg_response_time, 4),
        "note": (
            "Groundedness/hallucination are a lexical-overlap heuristic "
            "between the generated answer and the retrieved source "
            "passages, not an LLM-judge score."
        ),
    }


def evaluate_hybrid_routing(sample_size=15):
    """
    Run every sample question through the Hybrid Router directly and
    record which architecture answered, whether a fallback was
    triggered, and the confidence reported.
    """

    from chatbot.hybrid import hybrid_router

    questions = load_sample_questions(sample_size)

    architecture_counts = {}
    fallback_count = 0
    confidences = []
    response_times = []

    for question in questions:

        result = hybrid_router.route(question)

        architecture = result.get("architecture", "unknown")
        architecture_counts[architecture] = (
            architecture_counts.get(architecture, 0) + 1
        )

        if result.get("fallback_chain"):
            fallback_count += 1

        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            confidences.append(confidence)

        response_times.append(result.get("response_time", 0.0))

    n = max(len(questions), 1)

    return {
        "sample_size": n,
        "architecture_distribution": architecture_counts,
        "fallback_frequency": round(fallback_count / n, 3),
        "avg_confidence": (
            round(sum(confidences) / len(confidences), 3)
            if confidences else None
        ),
        "avg_response_time": round(sum(response_times) / n, 4),
    }


def get_hybrid_rag_insights(sample_size=15):
    """Single entry point the Flask route below calls."""

    return {
        "rag": evaluate_rag_groundedness(sample_size),
        "hybrid": evaluate_hybrid_routing(sample_size),
    }
