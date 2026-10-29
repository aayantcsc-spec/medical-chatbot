import time
import os
import sys


# ==========================================
# PROJECT ROOT
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
# IMPORT DATABASE
# ==========================================

from database.database import save_performance


# ==========================================
# MEASURE RESPONSE TIME
# ==========================================

def measure_response_time(
    chatbot_function,
    chatbot_type="Unknown"
):
    """
    Measures chatbot response time.

    chatbot_function:
        Function that runs the chatbot.

    chatbot_type:
        Name of chatbot architecture.
    """

    start_time = time.perf_counter()

    try:

        # Run chatbot
        response = chatbot_function()

        end_time = time.perf_counter()

        # Calculate time in seconds
        response_time = end_time - start_time

        # Save result
        save_performance(
            chatbot_type=chatbot_type,
            response_time=response_time
        )

        return response, response_time

    except Exception as error:

        end_time = time.perf_counter()

        response_time = end_time - start_time

        print(
            "Response time error:",
            error
        )

        return None, response_time


# ==========================================
# SIMPLE TIMER
# ==========================================

def calculate_response_time(
    start_time,
    end_time
):

    return end_time - start_time


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("Testing response time module...")

    def test_chatbot():

        time.sleep(0.5)

        return "Test chatbot response"

    response, response_time = measure_response_time(
        chatbot_function=test_chatbot,
        chatbot_type="Test"
    )

    print()
    print("Response:", response)
    print(
        "Response Time:",
        round(response_time, 4),
        "seconds"
    )

    print()
    print("Response time module working!")