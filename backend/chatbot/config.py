"""
chatbot/config.py

Single source of truth for the Hybrid AI layer's configurable
values: confidence thresholds used by the Hybrid Router, and LLM
settings used by the RAG+LLM architecture.

Nothing in the existing Rule/ML/DL/medical modules is imported or
changed by this file -- it is purely additive. Every value can be
overridden via environment variables (.env) without touching code,
per the project brief ("thresholds should be configurable rather
than hard-coded throughout the project").
"""

import os


def _get_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# ============================================================
# HYBRID ROUTER CONFIDENCE THRESHOLDS
#
# Used by chatbot/hybrid/hybrid_router.py to decide, per the
# project brief's "CONFIDENCE-BASED HYBRID ROUTING" section:
#
#   ML confidence >= HIGH            -> use ML alone
#   MEDIUM <= ML confidence < HIGH   -> compare ML vs DL, take the
#                                        stronger of the two
#   ML confidence < MEDIUM           -> fall through to DL /
#                                        Retrieval / RAG+LLM
# ============================================================

ML_CONFIDENCE_HIGH = _get_float("HYBRID_ML_CONFIDENCE_HIGH", 0.65)
ML_CONFIDENCE_MEDIUM = _get_float("HYBRID_ML_CONFIDENCE_MEDIUM", 0.35)

DL_CONFIDENCE_HIGH = _get_float("HYBRID_DL_CONFIDENCE_HIGH", 0.60)
DL_CONFIDENCE_MEDIUM = _get_float("HYBRID_DL_CONFIDENCE_MEDIUM", 0.30)

# Below this, retrieval/RAG results are considered too weak to
# present as a standalone answer and the router falls back further.
RETRIEVAL_CONFIDENCE_MIN = _get_float("HYBRID_RETRIEVAL_CONFIDENCE_MIN", 0.15)

# A query is treated as "complex" (routed toward Retrieval + RAG/LLM
# rather than ML/DL classification) once it mentions at least this
# many distinct symptom-like tokens, or exceeds the word-count cutoff.
COMPLEX_QUERY_MIN_SYMPTOMS = int(os.environ.get("HYBRID_COMPLEX_MIN_SYMPTOMS", 2))
COMPLEX_QUERY_MIN_WORDS = int(os.environ.get("HYBRID_COMPLEX_MIN_WORDS", 14))


# ============================================================
# RAG + LLM SETTINGS
# ============================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TIMEOUT_SECONDS = _get_float("OPENAI_TIMEOUT_SECONDS", 20.0)
OPENAI_MAX_TOKENS = int(os.environ.get("OPENAI_MAX_TOKENS", 300))

# Master switch: even with a key present, the LLM layer can be
# disabled (e.g. for an offline viva/demo) without removing the key
# from .env.
LLM_ENABLED = _get_bool("LLM_ENABLED", True)

# One quick retry on transient failures (timeouts, connection resets,
# rate limits) before giving up on a single request -- cheap insurance
# against a one-off network blip without doubling normal-case latency.
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", 1))
LLM_RETRY_BACKOFF_SECONDS = _get_float("LLM_RETRY_BACKOFF_SECONDS", 0.5)

# Circuit breaker: once this many CONSECUTIVE calls fail, stop trying
# the LLM entirely for LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS and fall
# back to RAG/DL/ML/Rule immediately instead of paying the full
# OPENAI_TIMEOUT_SECONDS cost on every request during an outage.
LLM_CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get("LLM_CIRCUIT_BREAKER_THRESHOLD", 3))
LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS = _get_float(
    "LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60.0
)


def llm_available():
    """True only if the LLM layer is enabled AND a key is configured."""
    return LLM_ENABLED and bool(OPENAI_API_KEY)


# ============================================================
# RAG LOCAL FALLBACK (transformers)
#
# When no OpenAI key is configured, RAGBot falls back to a local
# transformers text2text model. Loading transformers/torch is heavy
# and, on some environments (e.g. a Python version torch doesn't
# fully support yet), can hang rather than just being slow. Set this
# to false in .env to skip that fallback entirely and go straight to
# RAG's template-based response instead -- no code changes needed.
# ============================================================

RAG_LOCAL_FALLBACK_ENABLED = _get_bool("RAG_LOCAL_FALLBACK_ENABLED", True)


# ============================================================
# HYBRID MODE UI
# ============================================================

# Whether the chat UI shows the "Hybrid Mode" / "Response generated
# using: ..." indicator described in the project brief.
SHOW_HYBRID_INDICATOR = _get_bool("SHOW_HYBRID_INDICATOR", True)
