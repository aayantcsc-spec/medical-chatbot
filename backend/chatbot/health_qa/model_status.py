"""
model_status.py - READ-ONLY check of the three architectures' trained artifacts.

    python -m chatbot.health_qa.model_status            # human-readable report
    python -m chatbot.health_qa.model_status --json     # machine-readable

It never trains, downloads or overwrites anything. It answers:
  * which artifact file does each pipeline actually load, and does it exist?
  * do the label spaces of the SVM, DistilBERT and the knowledge base agree (91 intents)?
  * do the DistilBERT model and tokenizer belong together?
  * how old is each model, what data was it trained on, and is the stored metadata consistent?
  * which files in models/ are LEGACY (not used by the three pipelines) and whose metrics must not be cited?
  * what do the most recent saved evaluation runs say?
Exit code 0 = no problems found, 1 = at least one problem.
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = os.path.join(BASE, "models")

# files the three CURRENT pipelines load (see pipelines.py / bots.py). Everything else in models/ is legacy.
USED = {"svm/svm_pipeline.pkl", "svm/svm_meta.json", "distilbert_medical/model.safetensors", "distilbert_medical/config.json",
        "distilbert_medical/tokenizer.json", "distilbert_medical/tokenizer_config.json", "distilbert_medical/label_map.json",
        "distilbert_medical/training_config.json", "distilbert_medical/training_history.json", "evaluation/comparison_eval.json"}


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def collect():
    problems, notes, report = [], [], {}
    from chatbot.health_qa.knowledge import TOPIC_BY_ID
    kb = set(TOPIC_BY_ID)
    report["knowledge_base_intents"] = len(kb)

    # ---- SVM
    meta = _load(os.path.join(MODELS, "svm", "svm_meta.json"))
    pkl = os.path.join(MODELS, "svm", "svm_pipeline.pkl")
    svm = {"artifact": "models/svm/svm_pipeline.pkl", "exists": os.path.isfile(pkl), "meta": bool(meta)}
    if not svm["exists"]:
        problems.append("SVM artifact models/svm/svm_pipeline.pkl is missing - the ML pipeline will report 'unavailable'.")
    if meta:
        svm.update({k: meta.get(k) for k in ("run_id", "trained_at", "architecture", "train_examples", "val_examples", "classes",
                                              "min_margin", "sklearn_version")})
        if meta.get("classes") != len(kb):
            problems.append(f"SVM trained on {meta.get('classes')} classes but the knowledge base has {len(kb)} intents.")
        if isinstance(meta.get("min_margin"), (int, float)) and meta["min_margin"] < 0:
            notes.append(f"SVM rejection margin is negative ({meta['min_margin']}): it will rarely say 'no confident match', so out-of-scope "
                         "questions are mostly detected by the knowledge base's out_of_scope intent, not by a confidence threshold.")
    else:
        problems.append("models/svm/svm_meta.json is missing or unreadable.")
    try:
        import sklearn
        if meta and meta.get("sklearn_version") and meta["sklearn_version"] != sklearn.__version__:
            notes.append(f"SVM was trained with scikit-learn {meta['sklearn_version']} but {sklearn.__version__} is installed; "
                         "retrain if loading warns or predictions differ.")
    except ImportError:
        problems.append("scikit-learn is not installed; the SVM cannot load.")
    report["svm"] = svm

    # ---- DistilBERT
    d = os.path.join(MODELS, "distilbert_medical")
    cfg, lmap, tcfg = (_load(os.path.join(d, n)) for n in ("config.json", "label_map.json", "training_config.json"))
    weights = os.path.join(d, "model.safetensors")
    dl = {"artifact": "models/distilbert_medical/", "weights_exist": os.path.isfile(weights),
          "weights_mb": round(os.path.getsize(weights) / 1e6, 1) if os.path.isfile(weights) else None}
    if not dl["weights_exist"]:
        problems.append("DistilBERT weights models/distilbert_medical/model.safetensors are missing.")
    if tcfg:
        dl.update({k: tcfg.get(k) for k in ("run_id", "trained_at", "base_model", "train_examples", "val_examples", "classes",
                                             "epochs_run", "best_val_loss", "device", "max_length", "seed")})
        if tcfg.get("base_model", "").endswith("uncased") and "multilingual" not in tcfg.get("base_model", ""):
            notes.append(f"DistilBERT base model is '{tcfg['base_model']}' (English-only vocabulary). It has not seen Hindi or Hinglish; "
                         "those questions reach it only through the shared English-canonical preprocessing (language.py).")
        if (tcfg.get("best_val_loss") or 0) > 0.8:
            notes.append(f"DistilBERT best validation loss is {tcfg['best_val_loss']} after {tcfg.get('epochs_run')} epochs: the model is under-fit "
                         "relative to the 91-class task. More epochs / data / a different learning rate would be needed to improve it.")
    else:
        problems.append("models/distilbert_medical/training_config.json is missing or unreadable.")
    if lmap:
        labels = lmap.get("id2label_list") or []
        dl["labels"] = len(labels)
        if set(labels) != kb:
            problems.append(f"DistilBERT label map differs from the knowledge base (only in DL: {sorted(set(labels) - kb)[:5]}, "
                            f"only in KB: {sorted(kb - set(labels))[:5]}).")
        if cfg and cfg.get("num_labels", len(cfg.get("id2label", {}))) not in (len(labels), None) and len(cfg.get("id2label", {})) != len(labels):
            problems.append("DistilBERT config.json label count does not match label_map.json.")
    else:
        problems.append("models/distilbert_medical/label_map.json is missing or unreadable.")
    tok = _load(os.path.join(d, "tokenizer.json"))
    if cfg and tok:
        vocab = len((tok.get("model") or {}).get("vocab") or {})
        dl["model_type"], dl["config_vocab_size"], dl["tokenizer_vocab_size"] = cfg.get("model_type"), cfg.get("vocab_size"), vocab
        if cfg.get("model_type") != "distilbert":
            problems.append(f"config.json model_type is '{cfg.get('model_type')}', expected 'distilbert'.")
        if vocab and cfg.get("vocab_size") and vocab != cfg["vocab_size"]:
            problems.append(f"Tokenizer vocabulary ({vocab}) does not match the model's vocab_size ({cfg['vocab_size']}): wrong tokenizer/model pairing.")
    for mod in ("torch", "transformers"):
        try:
            __import__(mod)
        except ImportError:
            problems.append(f"'{mod}' is not installed here: the DistilBERT pipeline will report 'unavailable' (nothing is faked).")
    report["distilbert"] = dl

    # ---- SVM vs DL agree?
    if lmap and meta:
        report["label_spaces_agree"] = (meta.get("classes") == len(lmap.get("id2label_list") or []) == len(kb))

    # ---- legacy files
    legacy = []
    for p in glob.glob(os.path.join(MODELS, "**", "*"), recursive=True):
        if os.path.isfile(p):
            rel = os.path.relpath(p, MODELS).replace(os.sep, "/")
            if rel not in USED and not rel.startswith("evaluation/runs/") and not rel.endswith("_eval_backup.json"):
                legacy.append(rel)
    report["legacy_files_not_used_by_the_three_pipelines"] = sorted(legacy)
    old = _load(os.path.join(MODELS, "health_qa_metrics.json"))
    if old and old.get("topics") != len(kb):
        notes.append(f"models/health_qa_metrics.json describes {old.get('topics')} topics (ml_accuracy {old.get('ml_accuracy')}, "
                     f"dl_accuracy {old.get('dl_accuracy')}) but the current system has {len(kb)} intents. Those figures are from an older model "
                     "generation and must NOT be cited for the current SVM/DistilBERT.")

    # ---- saved evaluations
    runs = []
    for p in sorted(glob.glob(os.path.join(MODELS, "evaluation", "runs", "*.json")), reverse=True)[:6]:
        r = _load(p)
        if r:
            runs.append({"run_id": r.get("run_id"), "dataset": r["dataset"]["name"], "status": r.get("status"),
                         "evaluated": r["progress"]["total"], "accuracy": {k: (m.get("classification") or {}).get("accuracy") for k, m in (r.get("metrics") or {}).items()}})
    report["recent_saved_evaluations"] = runs
    if not runs:
        notes.append("No saved evaluation runs yet. Run one from the Model Evaluation tab or `python -c \"import evaluation_service as e; e.start_run('held_out_test','full',wait=True)\"`.")
    ev = _load(os.path.join(MODELS, "evaluation", "comparison_eval.json"))
    if ev:
        dls = [p for p in ev.get("pipelines", []) if p.get("key") == "dl"]
        if dls and dls[0].get("status") in ("unavailable", "error", None):
            notes.append(f"comparison_eval.json records DistilBERT as '{dls[0].get('status')}' - re-run `python -m chatbot.health_qa.evaluate`.")
    return {"problems": problems, "notes": notes, "report": report}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only model artifact check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = collect()
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print("MODEL STATUS (read-only)\n")
        print(json.dumps(out["report"], indent=2, default=str))
        print("\nPROBLEMS:" + ("" if out["problems"] else " none"))
        for p in out["problems"]:
            print("  x", p)
        print("\nNOTES:" + ("" if out["notes"] else " none"))
        for n in out["notes"]:
            print("  -", n)
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
