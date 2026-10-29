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
# GET CURRENT MEMORY USAGE
# ==========================================

def get_memory_usage():

    process = psutil.Process(
        os.getpid()
    )

    memory_bytes = process.memory_info().rss

    # Convert bytes to MB
    memory_mb = memory_bytes / (
        1024 * 1024
    )

    return memory_mb


# ==========================================
# MEASURE MEMORY USAGE
# ==========================================

def measure_memory_usage(
    chatbot_function,
    chatbot_type="Unknown"
):

    # Memory before chatbot
    memory_before = get_memory_usage()

    try:

        # Run chatbot
        response = chatbot_function()

        # Memory after chatbot
        memory_after = get_memory_usage()

        # Difference
        memory_used = (
            memory_after - memory_before
        )

        return {
            "response": response,
            "memory_before_mb": round(
                memory_before,
                4
            ),
            "memory_after_mb": round(
                memory_after,
                4
            ),
            "memory_used_mb": round(
                memory_used,
                4
            ),
            "chatbot_type": chatbot_type
        }

    except Exception as error:

        print(
            "Memory measurement error:",
            error
        )

        return {
            "response": None,
            "memory_before_mb": round(
                memory_before,
                4
            ),
            "memory_after_mb": round(
                get_memory_usage(),
                4
            ),
            "memory_used_mb": 0.0,
            "chatbot_type": chatbot_type
        }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print(
        "Testing memory usage module..."
    )

    def test_chatbot():

        # Simulate chatbot processing
        data = []

        for i in range(100000):
            data.append(i)

        time.sleep(0.2)

        return "Test chatbot response"

    result = measure_memory_usage(
        chatbot_function=test_chatbot,
        chatbot_type="Test"
    )

    print()

    print(
        "Response:",
        result["response"]
    )

    print(
        "Memory Before:",
        result["memory_before_mb"],
        "MB"
    )

    print(
        "Memory After:",
        result["memory_after_mb"],
        "MB"
    )

    print(
        "Memory Used:",
        result["memory_used_mb"],
        "MB"
    )

    print()

    print(
        "Memory usage module working!"
    )