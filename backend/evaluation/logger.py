import os
import sys
import time


# ==========================================
# ADD PROJECT ROOT TO PYTHON PATH
# ==========================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ==========================================
# IMPORT DATABASE FUNCTIONS
# ==========================================

from database.database import save_chat


# ==========================================
# LOG CHAT
# ==========================================

def log_chat(
    user_message,
    bot_response,
    chatbot_type="Unknown",
    response_time=0.0
):

    try:

        save_chat(
            user_message=user_message,
            bot_response=bot_response,
            chatbot_type=chatbot_type,
            response_time=response_time
        )

        print("Chat interaction saved successfully!")

    except Exception as error:

        print(
            "Error saving chat:",
            error
        )


# ==========================================
# MEASURE RESPONSE TIME
# ==========================================

def log_chat_with_timer(
    user_message,
    bot_function,
    chatbot_type="Unknown"
):

    start_time = time.perf_counter()

    try:

        # Run chatbot
        bot_response = bot_function()

        # Calculate response time
        end_time = time.perf_counter()

        response_time = end_time - start_time

        # Save chat
        log_chat(
            user_message=user_message,
            bot_response=bot_response,
            chatbot_type=chatbot_type,
            response_time=response_time
        )

        return bot_response, response_time

    except Exception as error:

        end_time = time.perf_counter()

        response_time = end_time - start_time

        print(
            "Chatbot error:",
            error
        )

        return "Error", response_time


# ==========================================
# TEST LOGGER
# ==========================================

if __name__ == "__main__":

    print("Testing logger...")

    log_chat(
        user_message="I have a headache",
        bot_response="Please consult a healthcare professional.",
        chatbot_type="Classification",
        response_time=0.25
    )

    print("Logger test completed!")