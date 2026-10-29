"""
chatbot/pipeline_logging.py

Single place that configures a "medichat.pipeline" logger used by the
hybrid routing pipeline (chatbot/hybrid/hybrid_router.py,
chatbot/orchestrator/bot_registry.py, chatbot/rag_based/llm_client.py).

Previously these modules used bare print() statements. That meant no
timestamps, no severity levels, and no way to turn the noise down (or
up) without editing code -- every load success, load failure, and LLM
error printed identically to stdout. get_logger() gives every pipeline
module the same configured logger instead, controllable via the
LOG_LEVEL environment variable (e.g. LOG_LEVEL=DEBUG).
"""

import logging
import os

_CONFIGURED = False


def get_logger(name="medichat.pipeline"):
    global _CONFIGURED

    if not _CONFIGURED:
        level_name = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
        level = getattr(logging, level_name, logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

        root = logging.getLogger("medichat")
        root.setLevel(level)
        # Avoid duplicate handlers if get_logger() is called again
        # (e.g. Flask's reloader re-importing modules).
        if not root.handlers:
            root.addHandler(handler)
        root.propagate = False

        _CONFIGURED = True

    return logging.getLogger(name)
