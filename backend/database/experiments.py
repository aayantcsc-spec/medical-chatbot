"""
experiments.py - evaluation experiments + per-chatbot results in SQLite (for dashboards and filters).

The full detail of every run stays in models/evaluation/runs/<run_id>.json (evaluation_service.py);
these rows are the queryable summary. Only the three MediChat chatbots are recorded:
rule (Rule-Based), ml (TF-IDF + SVM), dl (DistilBERT).
"""
import json

from database.database import get_db
from database.migrations import migrate

MODELS = ("rule", "ml", "dl")
_ready = False


def ensure_schema():
    global _ready
    if not _ready:
        migrate()
        _ready = True


def record_health_qa_run(state):
    """state = a completed evaluation_service run."""
    ensure_schema()
    ds = state["dataset"]
    sel = state.get("selection") or {}
    with get_db() as conn:
        conn.execute("""
            INSERT INTO experiments (id, name, suite, dataset_name, dataset_version, split, sample_size, random_seed,
                                     evaluation_method, in_sample, status, user_id, warnings_json, created_at, finished_at)
            VALUES (?, ?, 'health_qa', ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET status = excluded.status, finished_at = excluded.finished_at""",
            (state["run_id"], f"Evaluation - {ds['title']}", ds["name"], ds.get("version"), ds["title"], sel.get("selected"),
             sel.get("seed"), f"{state.get('mode')} selection, same questions for all three chatbots", state["status"],
             state.get("user_id"), json.dumps(state.get("limitations") or []), state["created_at"], state.get("finished_at")))
        for k, m in (state.get("metrics") or {}).items():
            if k not in MODELS:
                continue
            c = m.get("classification") or {}
            macro = c.get("macro") or {}
            lat = m.get("latency") or {}
            conn.execute("""
                INSERT INTO performance_results (experiment_id, architecture, accuracy, precision, recall, f1_score,
                    coverage, mean_response_time, median_response_time, successful_requests, failed_requests)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id, architecture) DO UPDATE SET accuracy = excluded.accuracy""",
                (state["run_id"], k, c.get("accuracy"), macro.get("precision"), macro.get("recall"), macro.get("f1"),
                 m.get("availability_rate"), lat.get("mean_ms"), lat.get("median_ms"), m.get("valid_predictions"), m.get("failed")))


def history(dataset="held_out_test", limit=200):
    """Per-chatbot accuracy / latency over completed runs of one dataset, oldest first (line charts)."""
    ensure_schema()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.id, e.created_at, e.sample_size, e.dataset_name, p.architecture, p.accuracy, p.f1_score,
                   p.median_response_time, p.mean_response_time, p.successful_requests, p.failed_requests
            FROM performance_results p JOIN experiments e ON e.id = p.experiment_id
            WHERE e.status = 'completed' AND e.dataset_name = ? ORDER BY e.created_at ASC LIMIT ?""", (dataset, int(limit))).fetchall()
    return [dict(r) for r in rows]


def counts():
    ensure_schema()
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS total, SUM(status = 'completed') AS completed, MAX(created_at) AS latest FROM experiments").fetchone()
    return {"total": row["total"] or 0, "completed": row["completed"] or 0, "latest": row["latest"]}
