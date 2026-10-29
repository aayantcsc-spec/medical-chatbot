"""
train_distilbert.py - fine-tunes distilbert-base-uncased on the MediChat intent splits.

REQUIRES: torch and transformers (pip install -r requirements.txt) and internet access
ONCE to download the pretrained weights (downloading weights is NOT fine-tuning; the
fine-tuning below is what makes the checkpoint MediChat-specific).

  * Uses datasets/intent_splits/{train,val}.csv  (70/15/15 split built by dataset.py).
  * Test split is never read here.
  * Early stopping on validation loss (patience 3), best weights restored.
  * Seeds fixed. CPU-friendly (batch 16, max_length 128). No paid APIs.
  * Saves model, tokenizer, label_map.json, training_config.json, training_history.json
    into models/distilbert_medical/.

Run:  python -m chatbot.health_qa.train_distilbert [--epochs 15] [--lr 5e-5] [--batch 16]
"""
import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

from chatbot.health_qa.dataset import load_split, build, normalise, SEED
from chatbot.health_qa.pipelines import DISTILBERT_DIR

MODEL_NAME = "distilbert-base-uncased"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max_length", type=int, default=128)
    ap.add_argument("--patience", type=int, default=3)
    args = ap.parse_args()

    try:
        import numpy as np
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc}. Run: pip install torch transformers") from exc

    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    build(write=True)
    tr, va = load_split("train"), load_split("val")
    labels = sorted({r["label"] for r in tr})
    l2i = {l: i for i, l in enumerate(labels)}

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(labels),
        id2label={i: l for l, i in l2i.items()}, label2id=l2i)

    def encode(rows):
        enc = tok([normalise(r["text"]) for r in rows], padding=True, truncation=True,
                  max_length=args.max_length, return_tensors="pt")
        return enc, torch.tensor([l2i[r["label"]] for r in rows])

    xtr, ytr = encode(tr)
    xva, yva = encode(va)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    history, best, bad, best_state = [], float("inf"), 0, None
    start = time.perf_counter()

    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(ytr))
        total = 0.0
        for i in range(0, len(perm), args.batch):
            b = perm[i:i + args.batch]
            out = model(input_ids=xtr["input_ids"][b], attention_mask=xtr["attention_mask"][b], labels=ytr[b])
            opt.zero_grad(); out.loss.backward(); opt.step()
            total += out.loss.item() * len(b)
        model.eval()
        with torch.no_grad():
            vo = model(input_ids=xva["input_ids"], attention_mask=xva["attention_mask"], labels=yva)
        val_acc = (vo.logits.argmax(-1) == yva).float().mean().item()
        history.append({"epoch": epoch, "train_loss": round(total / len(ytr), 4),
                        "val_loss": round(vo.loss.item(), 4), "val_accuracy": round(val_acc, 4)})
        print(history[-1])
        if vo.loss.item() < best - 1e-4:
            best, bad = vo.loss.item(), 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= args.patience:
                print("early stopping"); break
    model.load_state_dict(best_state)
    seconds = time.perf_counter() - start

    os.makedirs(DISTILBERT_DIR, exist_ok=True)
    model.save_pretrained(DISTILBERT_DIR); tok.save_pretrained(DISTILBERT_DIR)
    cfg = {"run_id": "distilbert-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
           "trained_at": datetime.now(timezone.utc).isoformat(), "base_model": MODEL_NAME, "seed": SEED,
           "hyperparameters": vars(args), "train_examples": len(tr), "val_examples": len(va),
           "classes": len(labels), "epochs_run": len(history), "best_val_loss": round(best, 4),
           "training_seconds": round(seconds, 2), "device": "cuda" if torch.cuda.is_available() else "cpu",
           "max_length": args.max_length, "min_confidence": 0.0,
           "torch_version": torch.__version__}
    json.dump(cfg, open(os.path.join(DISTILBERT_DIR, "training_config.json"), "w"), indent=2)
    json.dump({"id2label_list": labels}, open(os.path.join(DISTILBERT_DIR, "label_map.json"), "w"), indent=2)
    json.dump(history, open(os.path.join(DISTILBERT_DIR, "training_history.json"), "w"), indent=2)
    print("saved to", DISTILBERT_DIR)


if __name__ == "__main__":
    main()
