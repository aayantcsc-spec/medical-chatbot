"""
chatbot_adapter.py

Common adapter used by the MediChat automated evaluation system.

Current project architectures:

    1. Rule-Based
    2. Machine Learning
    3. Deep Learning

This adapter does NOT implement the chatbots itself.

It only:

    1. Maps architecture display names to bot_registry keys.
    2. Measures response time consistently.
    3. Normalizes chatbot responses into one common format.
    4. Prevents one chatbot failure from stopping evaluation.
"""


import os
import sys
import time
import traceback


# ============================================================
# PROJECT PATH
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# CANONICAL ARCHITECTURE LIST
#
# IMPORTANT:
# Only these three architectures are used for the
# comparative-analysis evaluation.
#
# Expected:
#
# 300 questions
# x
# 3 architectures
# =
# 900 responses
# ============================================================

CHATBOT_NAMES = [
    "Rule-Based",
    "Machine Learning",
    "Deep Learning",
]


# ============================================================
# DISPLAY NAME -> BOT REGISTRY KEY
# ============================================================

_NAME_TO_BOT_TYPE = {

    "Rule-Based":
        "rule",

    "Machine Learning":
        "ml",

    "Deep Learning":
        "dl",
}


# ============================================================
# VALIDATION
# ============================================================

def is_valid_chatbot_name(chatbot_name):
    """
    Return True only for the three supported
    evaluation architectures.
    """

    return chatbot_name in _NAME_TO_BOT_TYPE


# ============================================================
# COMMON RESPONSE ADAPTER
# ============================================================

def get_response(
    chatbot_name,
    question
):
    """
    Common evaluation interface:

        get_response(chatbot_name, question)

    The actual chatbot implementation remains inside:

        chatbot/orchestrator/bot_registry.py

    This function only routes and normalizes the result.
    """

    # --------------------------------------------------------
    # INVALID ARCHITECTURE
    # --------------------------------------------------------

    if not is_valid_chatbot_name(
        chatbot_name
    ):

        return {

            "chatbot_name":
                chatbot_name,

            "response":
                "",

            "response_time_ms":
                0.0,

            "success":
                False,

            "error":
                (
                    f"Invalid chatbot name: "
                    f"'{chatbot_name}'"
                ),
        }


    # --------------------------------------------------------
    # GET INTERNAL BOT TYPE
    # --------------------------------------------------------

    bot_type = _NAME_TO_BOT_TYPE[
        chatbot_name
    ]


    # --------------------------------------------------------
    # LAZY IMPORT
    #
    # Keeps ML/model imports out of application startup.
    # --------------------------------------------------------

    from chatbot.orchestrator.bot_registry import (
        get_bot_response
    )


    # --------------------------------------------------------
    # START TIMER
    # --------------------------------------------------------

    start_time = time.perf_counter()


    try:

        # ----------------------------------------------------
        # CALL EXISTING CHATBOT
        # ----------------------------------------------------

        result = get_bot_response(
            bot_type,
            question
        )


        # ----------------------------------------------------
        # RESPONSE TIME
        # ----------------------------------------------------

        elapsed_ms = (
            time.perf_counter()
            - start_time
        ) * 1000.0


        # ----------------------------------------------------
        # NO RESULT / UNAVAILABLE BOT
        # ----------------------------------------------------

        if (
            not result
            or not result.get("available")
        ):

            error_message = (
                (result or {}).get("error")
                or
                "No response returned."
            )

            return {

                "chatbot_name":
                    chatbot_name,

                "response":
                    "",

                "response_time_ms":
                    round(
                        elapsed_ms,
                        3
                    ),

                "success":
                    False,

                "error":
                    error_message,
            }


        # ----------------------------------------------------
        # GET RESPONSE TEXT
        # ----------------------------------------------------

        response_text = (
            result.get("response")
            or ""
        )


        # ----------------------------------------------------
        # EMPTY RESPONSE
        # ----------------------------------------------------

        if not str(
            response_text
        ).strip():

            return {

                "chatbot_name":
                    chatbot_name,

                "response":
                    "",

                "response_time_ms":
                    round(
                        elapsed_ms,
                        3
                    ),

                "success":
                    False,

                "error":
                    (
                        "Chatbot returned "
                        "an empty response."
                    ),
            }


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return {

            "chatbot_name":
                chatbot_name,

            "response":
                str(response_text),

            "response_time_ms":
                round(
                    elapsed_ms,
                    3
                ),

            "success":
                True,

            "error":
                None,
        }


    # --------------------------------------------------------
    # NEVER LET ONE CHATBOT CRASH THE WHOLE EVALUATION
    # --------------------------------------------------------

    except Exception as error:

        elapsed_ms = (
            time.perf_counter()
            - start_time
        ) * 1000.0


        traceback.print_exc()


        return {

            "chatbot_name":
                chatbot_name,

            "response":
                "",

            "response_time_ms":
                round(
                    max(
                        elapsed_ms,
                        0.0
                    ),
                    3
                ),

            "success":
                False,

            "error":
                (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
        }


# ============================================================
# CHATBOT AVAILABILITY CHECK
# ============================================================

def check_chatbots_available():
    """
    Check only the three project architectures.

    A harmless 'hello' message is used.

    Returns:

        {
            "Rule-Based": {
                "available": True/False,
                "error": ...
            },
            ...
        }
    """

    report = {}


    for chatbot_name in CHATBOT_NAMES:

        result = get_response(
            chatbot_name,
            "hello"
        )


        report[chatbot_name] = {

            "available":
                bool(
                    result["success"]
                ),

            "error":
                result["error"],
        }


    return report