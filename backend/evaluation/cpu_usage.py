import os
import sys
import time
import psutil


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
# GET CURRENT CPU USAGE
# ==========================================

def get_cpu_usage(interval=0.1):

    process = psutil.Process(
        os.getpid()
    )

    cpu_percent = process.cpu_percent(
        interval=interval
    )

    return cpu_percent


# ==========================================
# MEASURE CPU USAGE
# ==========================================

def measure_cpu_usage(
    chatbot_function,
    chatbot_type="Unknown"
):

    process = psutil.Process(
        os.getpid()
    )

    # Start CPU measurement
    process.cpu_percent(
        interval=None
    )

    start_time = time.perf_counter()

    try:

        # Run chatbot
        response = chatbot_function()

        end_time = time.perf_counter()

        # Measure CPU usage
        cpu_usage = process.cpu_percent(
            interval=None
        )

        response_time = (
            end_time - start_time
        )

        return {
            "response": response,
            "cpu_usage": round(
                cpu_usage,
                2
            ),
            "response_time": round(
                response_time,
                4
            ),
            "chatbot_type": chatbot_type
        }

    except Exception as error:

        end_time = time.perf_counter()

        print(
            "CPU measurement error:",
            error
        )

        return {
            "response": None,
            "cpu_usage": 0.0,
            "response_time": round(
                end_time - start_time,
                4
            ),
            "chatbot_type": chatbot_type
        }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print(
        "Testing CPU usage module..."
    )

    def test_chatbot():

        # Simulate CPU processing
        total = 0

        for i in range(1000000):
            total += i

        time.sleep(0.2)

        return "Test chatbot response"

    result = measure_cpu_usage(
        chatbot_function=test_chatbot,
        chatbot_type="Test"
    )

    print()

    print(
        "Response:",
        result["response"]
    )

    print(
        "CPU Usage:",
        result["cpu_usage"],
        "%"
    )

    print(
        "Response Time:",
        result["response_time"],
        "seconds"
    )

    print()

    print(
        "CPU usage module working!"
    )