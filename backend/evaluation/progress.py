"""
progress.py

Very small in-memory progress tracker for the "Run Comparative
Evaluation" button. A full evaluation run (50 questions x 6
architectures = 300 chatbot calls) can take a while, so app.py runs
it in a background thread and the frontend polls a status endpoint
instead of blocking one HTTP request for the whole run.

This intentionally does not use a task queue (Celery/RQ) -- that
would be a disproportionate amount of new infrastructure for a
final-year Flask project running on a single dev server. A
process-local dict is a reasonable, honest scope for this use case;
it documents the limitation clearly (progress is lost on server
restart, and there can only be one active evaluation at a time,
which lines up with the "prevent duplicate runs" requirement anyway).
"""

import threading

_lock = threading.Lock()
_current = {
    "active": False,
    "run_id": None,
    "stage": None,          # e.g. "loading_questions", "testing_chatbot", "completed", "failed"
    "current_chatbot": None,
    "chatbots_done": [],
    "questions_done_for_current_chatbot": 0,
    "total_questions": 0,
    "total_chatbots": 0,
    "total_responses": 0,
    "error": None,
}


def reset(total_questions=0, total_chatbots=0):
    with _lock:
        _current.update({
            "active": True,
            "run_id": None,
            "stage": "starting",
            "current_chatbot": None,
            "chatbots_done": [],
            "questions_done_for_current_chatbot": 0,
            "total_questions": total_questions,
            "total_chatbots": total_chatbots,
            "total_responses": 0,
            "error": None,
        })


def update_from_event(event):
    with _lock:
        event_type = event.get("type")

        if event_type == "loading_questions":
            _current["stage"] = "loading_questions"

        elif event_type == "run_created":
            _current["run_id"] = event.get("run_id")
            _current["total_questions"] = event.get("total_questions", 0)
            _current["total_chatbots"] = event.get("total_chatbots", 0)
            _current["stage"] = "running"

        elif event_type == "testing_chatbot":
            _current["current_chatbot"] = event.get("chatbot_name")
            _current["questions_done_for_current_chatbot"] = 0
            _current["stage"] = "running"

        elif event_type == "question_done":
            _current["questions_done_for_current_chatbot"] += 1
            _current["total_responses"] += 1

        elif event_type == "chatbot_done":
            name = event.get("chatbot_name")
            if name and name not in _current["chatbots_done"]:
                _current["chatbots_done"].append(name)

        elif event_type == "calculating_metrics":
            _current["stage"] = "calculating_metrics"

        elif event_type == "completed":
            _current["stage"] = "completed"
            _current["active"] = False
            _current["total_responses"] = event.get("total_responses", _current["total_responses"])

        elif event_type == "failed":
            _current["stage"] = "failed"
            _current["active"] = False
            _current["error"] = event.get("error")


def get_status():
    with _lock:
        return dict(_current)
