# MediChat - Comparison, Training, Evaluation and User Study (update notes)

The project is a **Flask** app (not Streamlit); it was kept as Flask. Comparison now sends ONE question to THREE
independent pipelines (`chatbot/health_qa/pipelines.py`):

| Key | Architecture | Artifact |
|---|---|---|
| rule | keyword/phrase rules | none (no training) |
| ml | TF-IDF + linear SVM | `models/svm/` |
| dl | fine-tuned `distilbert-base-uncased` | `models/distilbert_medical/` |

**DistilBERT status: NOT TRAINED in the delivered project.** It was written but could not be run where this update
was built (no PyTorch / transformers / Hugging Face access, 1 CPU, 3 GB RAM). Until you train it, the DL card shows "model unavailable" with the
exact instruction. No other model's answer is ever substituted.

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Train
```bash
python -m chatbot.health_qa.dataset          # rebuild 70/15/15 group-aware split -> datasets/intent_splits/
python -m chatbot.health_qa.train_svm        # trains + saves models/svm/ (about 1 s)
python -m chatbot.health_qa.train_distilbert # needs internet once for base weights; CPU ok; saves models/distilbert_medical/
```
Rule-Based needs no training (edit keywords in `chatbot/health_qa/knowledge.py`).

## Evaluate (reproduces every number shown on the Model Evaluation tab)
```bash
python -m chatbot.health_qa.evaluate         # writes models/evaluation/comparison_eval.json
```
Same held-out `datasets/intent_splits/test.csv` plus `datasets/safety_oos_eval.csv` (author-written out-of-scope and
emergency probes) is used for all three pipelines. Unavailable pipelines are recorded as unavailable, with no metrics.

## Tests
```bash
python -m unittest discover -s tests -v
```

## User Study
Participants rate the three responses on the Comparison tab (1-5 for correctness, relevance, clarity, completeness,
perceived safety, optional comment) after ticking consent. Stored in tables `comparison_runs` and
`comparison_study_ratings` (created automatically; older tables untouched). Response order is shuffled per question
and the true architecture and display position are stored. Participant IDs are salted hashes of the login id.
View aggregates on the "User Study Results" tab; export real rows at `/api/comparison/study/export.csv`.

## Data used and not used
Intent data = the project's own hand-written topics in `knowledge.py` (435 questions, 54 topics). `Symptom2Disease.csv`
and the augmented disease file map symptoms to disease names, not health questions, so they were NOT used for this
intent task. See `datasets/intent_splits/split_report.json`.

## Known limitations
- Test set is 57 questions written by the same team as the training questions; it measures new wording of known
  topics, not real patient language. Metrics are noisy.
- The SVM recipe (adding labelled keyword phrases as train-only rows) was adopted after a first test-set evaluation
  showed weak results, so its test score is slightly optimistic. Re-collect a fresh test set for the final report.
- Rule keywords were written by the same team who wrote the questions, which favours the rule-based bot.
- No clinician-reviewed reference answers exist; correctness is measured only by the User Study (perceptions).
- Old modules (`chatbot/machine_learning`, `chatbot/deep_learning`, Analysis, older User Study) were left untouched.


---
## 46-category update (latest)
* `chatbot/health_qa/taxonomy.py` - the 46 categories, first point of care / specialist per category, topic -> category map.
* `chatbot/health_qa/knowledge_extra.py` - 37 new topics + extra phrasings (all author-written, NOT clinician-reviewed, no real patient data).
  91 intents / 961 labelled questions in total.
* `chatbot/health_qa/safety.py` - 10 emergency classes with immediate-action lines, informational-vs-personal detection,
  Tele-MANAS (14416 / 1800-891-4416) and 112. Overrides every model identically.
* `chatbot/health_qa/responder.py` - ONE shared response layer (Chat + Comparison). `rule_engine.py` - rule-based pipeline.
* `pipelines.py` - each pipeline offers `predict_intent`, `predict_with_confidence`, `predict_top_k`, `model_info`.
* Chat API: `POST /api/health-chat/ask` {question, context_topic?} uses `comparison_service.route_chat` (routing policy:
  available pipeline with the highest held-out accuracy; says which model answered, `compared_models: false`).
  **The existing /chat page UI still runs on the old ConversationManager and was NOT rewired to this endpoint.**
* Tests: `python -m unittest discover -s tests -v` (56 tests).

### Train DistilBERT (not done here)
```bash
pip install -r requirements.txt
python -m chatbot.health_qa.dataset
python -m chatbot.health_qa.train_distilbert     # CPU ok (~15-40 min); needs internet once for distilbert-base-uncased
python -m chatbot.health_qa.evaluate             # refreshes models/evaluation/comparison_eval.json incl. DL
```

### Safety-layer caveat
Keyword patterns were widened AFTER the first evaluation showed 3 missed probes (phenyl, "killing myself", indirect wording),
so the 20/20 probe result is optimistic. Indirect wording without keywords ("everything feels pointless") is still NOT detected.


---
## Best-response + performance update (latest)
**Comparison tab** - every comparison now shows a dark-teal **Best Response** banner, a trophy badge on the winning card (teal border, subtle tint),
and four scores per reply (correctness, safety, response quality, response time) plus an overall score. Ties and "unable to determine"
are shown as such; nothing is crowned when the evidence is not there. Winner = `overall_selection.winner_key` from the backend only.

**Model Evaluation tab** - new *Model performance overview* (per-architecture score cards, 4 criterion graphs + overall, best-performing
architecture with a measured explanation, selectable dataset) and *Your comparison history*. All figures are calculated from data the app stored:
`models/evaluation/runs/*.json` and the `comparison_runs` table. No number is typed in and no model is retrained or re-run.

| File | Change |
|---|---|
| `comparison_service.py` | `score_text()` shared scorer, `scoring_info()`; Hindi/Hinglish replies are "unavailable" for safety/quality (English-only rules); ties report the fastest reply without crowning it |
| `performance_service.py` | NEW - benchmark aggregation, `pick_best()` (safety gate, tie margin, min sample), live history re-scoring |
| `app.py` | `/comparison` passes scoring config; NEW read-only `GET /api/comparison/performance`, `GET /api/comparison/history` (own runs only) |
| `database/database.py` | NEW read-only `list_comparison_runs_with_results()`; no schema change |
| `templates/comparison.html`, `static/js/comparison.js` (NEW), `static/js/research.js`, `static/css/comparison.css` | UI. `comparison.css` was previously unlinked; the old file is in `static/css/_archive/` |
| `tests/test_performance.py`, `tests/ui/comparison_render_test.js` | NEW tests (`node tests/ui/comparison_render_test.js`) |

Scoring: overall = correctness 40 + safety 30 + quality 20 + response time 10, re-balanced over what could be measured. Tie margin 2 points; a lead from
speed alone is a tie; a model whose mean safety is below 60 cannot win; at least 20 measured questions (10 paired comparisons for live history) are required.
Limits: safety/quality are rule-based proxies (not clinician review); Hindi/Hinglish replies are not scored by them.
