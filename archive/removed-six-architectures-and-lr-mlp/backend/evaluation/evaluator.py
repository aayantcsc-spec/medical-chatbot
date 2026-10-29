"""
evaluator.py - command-line entry point for the six-architecture evaluation.

    python -m evaluation.evaluator --sample-size 30
    python -m evaluation.evaluator --sample-size 0 --seed 7                # 0 = the whole held-out test split
    python -m evaluation.evaluator --architectures classification retrieval_based
    python -m evaluation.evaluator --legacy-full-dataset                   # reproduce the original in-sample setup

The work is done by evaluation/symptom_evaluator.py (held-out split, same inputs for every
architecture, separate task/coverage/safety/latency metrics). Results are appended to
results/comparison_results.csv and stored in SQLite, never overwritten.
The original evaluator is kept unchanged in evaluation/legacy_evaluator.py for reference.
"""
import argparse
import json
import sys

from evaluation import symptom_evaluator as se


def main(argv=None):
    p = argparse.ArgumentParser(description="Evaluate the six symptom architectures on held-out data.")
    p.add_argument("--sample-size", type=int, default=30, help="inputs to sample (0 = all held-out rows)")
    p.add_argument("--seed", type=int, default=se.DEFAULT_SEED)
    p.add_argument("--architectures", nargs="*", default=None)
    p.add_argument("--legacy-full-dataset", action="store_true",
                   help="evaluate on ALL of Symptom2Disease.csv (in-sample for the classifier; labelled as such)")
    a = p.parse_args(argv)

    from database import experiments
    experiments.ensure_schema()
    st = se.start(sample_size=a.sample_size or None, seed=a.seed, architectures=a.architectures,
                  legacy_full_dataset=a.legacy_full_dataset, wait=True, on_finish=experiments.record_symptom_run)
    if st["status"] != "completed":
        print("Evaluation failed:", st["error"], file=sys.stderr)
        return 1
    s = se.summary(st)
    print(f"Run {s['run_id']} | {s['split']} | n={s['sample_size']} | seed={s['seed']}")
    print(f"{'architecture':18s} {'acc':>6s} {'F1':>6s} {'legacy':>7s} {'cover':>6s} {'safe':>6s} {'med ms':>8s} {'cpu%':>6s}")
    fmt = lambda v: "   -  " if v is None else f"{v:6.3f}"
    for k, m in s["architectures"].items():
        print(f"{k:18s} {fmt(m['accuracy'])} {fmt(m['f1_macro'])} {fmt(m['legacy_mention_accuracy']):>7s} "
              f"{fmt(m['coverage'])} {fmt(m['safety_pass_rate'])} {m['median_ms'] or 0:8.2f} {m['cpu_percent'] or 0:6.1f}")
    for w in s["warnings"]:
        print("NOTE:", w)
    print("Appended to results/comparison_results.csv; detail in models/evaluation/symptom_runs/" + s["run_id"] + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
