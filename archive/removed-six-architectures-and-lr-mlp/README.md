# Archived: six-architecture system and the Logistic Regression / MLP bots

Removed from the running application on 29 Oct 2026, when the project scope was fixed to **exactly three
chatbots** (Rule-Based, TF-IDF + SVM, DistilBERT) and no RAG. Nothing here is imported by the app.

Contents (paths mirror `backend/`):

| Path | What it was |
|---|---|
| `chatbot/{nlp_based,classification,retrieval_based,rag_based,generation_based,symptom}/`, `chatbot/rule_based/architecture.py` | the six symptom architectures, their shared knowledge base and registry |
| `evaluation/symptom_evaluator.py`, `evaluation/evaluator.py` | their held-out evaluator and CLI |
| `tests/test_symptom_architectures.py` | their tests |
| `chatbot/health_qa/train_lr_mlp.py`, `models/health_lr/`, `models/health_mlp/` | Health Q&A Logistic Regression and MLP bots |
| `models/symptom/`, `datasets/symptom_splits/` | trained classifier, retrieval profiles, deduplicated Symptom2Disease split |
| `models/evaluation/symptom_runs/`, `results/comparison_results.csv` | the real evaluation runs of the six architectures |

Measured results of these modules are recorded in those run files. To restore any of them, move the folder
back into `backend/` and re-register it (they will not run on their own in the current app).
