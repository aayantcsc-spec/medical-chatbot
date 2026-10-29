"""
evaluator.py - command-line evaluation of the three MediChat chatbots (Rule-Based, TF-IDF + SVM, DistilBERT).

    python -m evaluation.evaluator                                  # held-out test split, all questions
    python -m evaluation.evaluator --dataset multilingual
    python -m evaluation.evaluator --dataset safety
    python -m evaluation.evaluator --dataset question_bank --limit 60

Uses evaluation_service.py (same questions for all three chatbots, leakage checks). Each run is saved to
models/evaluation/runs/<run_id>.json and recorded in SQLite for the Model Evaluation page.
The original evaluator is kept in evaluation/legacy_evaluator.py for reference.
"""
import argparse
import sys

import evaluation_service as ev
from database import experiments as exp


def main(argv=None):
    p = argparse.ArgumentParser(description="Evaluate the three MediChat chatbots.")
    p.add_argument("--dataset", default="held_out_test", choices=list(ev.DATASETS))
    p.add_argument("--limit", type=int, default=None, help="number of questions (default: all eligible)")
    a = p.parse_args(argv)
    exp.ensure_schema()
    st = ev.start_run(a.dataset, "custom" if a.limit else "full", limit=a.limit, wait=True, on_finish=exp.record_health_qa_run)
    run = ev.get_run(st["run_id"])
    if run["status"] != "completed":
        print("Evaluation failed:", run.get("error"), file=sys.stderr)
        return 1
    print(f"Run {run['run_id']} | {run['dataset']['title']} | n={run['selection']['selected']} | seed={run['selection']['seed']}")
    for k, m in run["metrics"].items():
        c = m.get("classification") or {}
        print(f"  {k:5s} accuracy={c.get('accuracy')} macroF1={(c.get('macro') or {}).get('f1')} "
              f"median={m['latency']['median_ms']} ms failed={m['failed']}")
    if run.get("safety"):
        for k, s in run["safety"]["per_model"].items():
            print(f"  {k:5s} emergency guidance={s['emergency_recall']} off-topic declined={s['oos_decline_rate']}")
    for w in run.get("limitations") or []:
        print("NOTE:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
