# MediChat upgrade notes

What was changed, what was measured, how to re-run it, and what is **not** done.
Every number below comes from a saved run in `models/evaluation/runs/` (re-run: see "Reproduce").

## 1. What was wrong when I inspected the project

| Finding | Evidence |
|---|---|
| **The Chat page had no JavaScript.** `templates/chat.html` ended with the placeholder "Keep your existing chat JavaScript here"; `static/js/` held only `main.js`. | Nothing could be sent from the page. |
| **Hindi (Devanagari) text was erased** before reaching any model: `dataset.normalise()` keeps only `[a-z0-9 '-]`. Roman-script Hindi ("bukhar") was an unknown word. | Probe: every Hindi/Hinglish question fell through to the generic fallback. |
| **Safety gap:** `seene mein dard ho raha hai saans nahi aa rahi` (chest pain + cannot breathe) got the generic fallback with **no emergency notice**. | Safety patterns were English-only. |
| Greetings, thanks, bye → generic fallback. "Headache and dizzy" answered only headache. | Probe. |
| `models/evaluation/comparison_eval.json` recorded DistilBERT as *unavailable* although it had been trained (and it was never evaluated). | File timestamps (eval 12:06, training 12:28). |
| `datasets/evaluation_expected.csv` is **0 bytes**. The 300-question bank has its own `expected_intent` column, so it is not needed, and it is not used. | `ls -l`. |
| The question bank has **19 coarse labels**; the models predict **91 intents**; only 2 labels overlap by name. Scoring them directly would be invalid. | Schema check. |
| `models/health_qa_metrics.json` (ML 82.7 %, DL 86.7 %) describes an **older 54-topic model generation** and is not comparable to the current system. | `model_status` flags it. **Do not cite those numbers.** |
| Study table forced NOT NULL "correctness/completeness" ratings (no N/A, no helpfulness/trustworthiness). | Schema. |
| `comparison.html` had a nested duplicate `<style>` tag. | Source. |

The 56 existing tests passed before I started and all still pass.

## 2. What was built

**Language layer** (`chatbot/health_qa/language.py`, `localized.py`, `chat_reply.py`) - shared by Chat, Comparison, Evaluation and the safety module.
* Detects English / Hindi (Devanagari) / Hinglish; converts Hindi/Hinglish medical terms to English *canonical* text (≈200 curated phrases, spelling-variant folding, typo repair, severity/duration adverbs) and extracts multiple symptoms.
* The three architectures are **unchanged**; they simply receive the same canonical text. English input is returned essentially unchanged.
* Small talk (greeting / how-are-you / thanks / bye / identity / help) is answered by this front-end, **not by a model**, and is labelled that way (`handled_by`).
* Replies are structured by question kind (definition, symptom, doctor, medication, test, prevention/lifestyle, follow-up) and written in the user's language. Doctor questions get specialty guidance for 15 areas (not a diagnosis; emergency warning signs override routine advice). Multi-symptom questions get an explicit "I cannot say what is behind them" paragraph.
* Safety (`safety.py`) now checks the raw text **and** the canonical text, so language detection or routing cannot bypass it. Localised emergency / self-harm text uses 112 and Tele-MANAS (14416 / 1800-891-4416).

**Chat** - `static/js/chat.js` (new), `chat.html`/`chat.css` (updated), `/api/health-chat/ask` now persists each turn into the existing `conversations`/`chats` tables (ownership-checked), keeps the response contract (`result`, `answered_by`, …) and adds `conversation_id`, `next_context_topic`, `reply`. Enter / Shift+Enter, auto-grow input, typing indicator, error + Retry, copy, new/open/delete/search conversations, sanitised markdown (everything is HTML-escaped *before* formatting), responsive layout. **There is no fake streaming:** the models classify topics rather than generate tokens, so the finished reply appears after a typing indicator.

**Comparison** - same `run_comparison()`/`run_one()`/`/api/comparison/ask`; added language metadata, architecture + model version, measured time, confidence *with its type*, predicted topic, errors shown per card, and a "how the replies differ" note that is purely structural. **No winner is declared and no quality score is invented.**

**Evaluation** (`evaluation_service.py`, new endpoints under `/api/comparison/evaluation/…`) - validates the dataset (missing/empty file, columns, label mismatch, duplicates, conflicting duplicates, **training-data overlap**), runs all three real pipelines in a background thread with real progress, records per-question outputs/errors/latency, computes accuracy, macro P/R/F1, per-class metrics, confusion matrices, latency mean/median/p90/p95, availability, saves `models/evaluation/runs/<run_id>.json` (atomic write, dataset hash, model versions), lists/reopens previous runs, exports CSV. One run at a time; chat is not blocked. A model that crashes or is unavailable is counted as failed and gets **no** metrics.

**User Study** - existing table migrated without data loss (copy → swap, idempotent, verified); criteria are now helpfulness, relevance, clarity, trustworthiness and *perceived* safety, each 1-5 or N/A, plus a comment. Question/response text is read from the stored run, never from the browser. Re-submitting updates (never duplicates). Participants see only their own runs, responses appear blinded as A/B/C in random order, consent is required, participant IDs are pseudonymous, averages appear only from 5 participants, CSV export included.

**Design** - `static/css/research.css` + `static/js/research.js` + rewritten `templates/comparison.html` use your tokens (forest/sage/cream/sand, DM Sans + Manrope), focus rings, reduced-motion support, empty/loading/error/success states. Chat uses the same palette. Back-to-Dashboard link and login gates kept.

## 3. Measured results (final code; reproducible)

Classification accuracy; "n" = questions scored.

| Dataset | n | Rule-Based | ML (TF-IDF+SVM) | DL (DistilBERT) |
|---|---|---|---|---|
| Held-out test split, 91 intents (exact) | 155 | **0.748** | 0.664 | 0.690 |
| Hinglish + Hindi, 91 intents (exact) | 52 | **0.923** | 0.885 | 0.865 |
| Question bank, 19 categories, *lenient* | 288 | 0.750 | 0.455 | **0.819** |
| Question bank, *strict* (primary category) | 288 | 0.677 | 0.413 | **0.753** |

Macro F1 - held-out: 0.729 / 0.681 / 0.615 · multilingual: 0.917 / 0.881 / 0.838 · question bank (lenient): 0.755 / 0.550 / 0.825.
Median latency per question: rule ≈ 38 ms, SVM ≈ 4 ms, DistilBERT ≈ 45 ms (single CPU core).
"No confident match" on the question bank: rule 32, **SVM 115**, DL 0 - the SVM's low score there is mostly *rejection*, not wrong answers.

**Safety (assessed separately from relevance)** - 74 probes (20 English, 10 Hinglish, 8 Hindi emergencies + non-emergency + out-of-scope): emergency detection precision 1.00 / recall 1.00 (English 20/20, Hinglish 10/10, Hindi 8/8), 0 false alarms. All three models surface emergency guidance 38/38. Out-of-scope questions declined: rule 18/18, SVM 18/18, **DistilBERT 12/18** (it answers some non-health questions).

Interpretation: no model is "best". DistilBERT is best on the question bank but weakest on the strict held-out split and on declining off-topic questions; the rule model is best on the held-out and multilingual sets. One question or one dataset does not decide this.

**Software tests:** 150 Python tests (`python -m pytest tests -q`; also `python -m unittest discover -s tests`) pass **both** with DistilBERT available and with torch hidden. Mutation checks confirmed the evaluation tests fail when the F1 formula or the failed-model handling is deliberately broken. A headless-DOM suite (`tests/ui`, 63 checks) drove the real pages against the real server: chat send/retry/history, comparison cards, evaluation run + progress + saved-run restore after reload, blinded study rating + persistence.

## 4. Limitations and what is NOT done (please read)

1. **Hindi/Hinglish support is a front-end, not trained into the models.** All three models were trained on English only (DistilBERT base is `distilbert-base-uncased`). The lexicon covers common symptoms, body areas, medicines, doctors and question words; unknown Hindi words are dropped, never guessed. Spelling-variant and typo repair is conservative. I did **not** train on Hindi/Hinglish data (none exists in the project and I will not fabricate training data).
2. **Evaluation data is not independent.** `multilingual_eval.csv` (52 items) was written by the same team that wrote the lexicon, and `safety_multilingual_eval.csv` was used while fixing lexicon gaps, so it is a *regression set*, not unseen data - the evaluation page says so. The question bank is author-written about the same topics as the training data; scores measure generalisation to new wording, not real patient language. 12 of its 300 rows are excluded (6 conflicting-label duplicates, 5 duplicates, 1 overlap with training data).
3. **The 19-category question-bank scores depend on `datasets/evaluation_label_map.json`**, an author-made mapping (strict and lenient scoring are both reported). It is an assumption, not clinical ground truth.
4. **Localised content is partial and unreviewed.** Hindi/Hinglish text exists for 27 topics, all safety notices, headings, small talk and 15 specialty areas. Other topics are shown in English with an explicit note. Translations were not reviewed by a clinician or professional translator - do that before any public use.
5. **No model was retrained.** (a) DistilBERT's best validation loss is 1.108 after 15 epochs - it is under-fit - but fine-tuning needs `distilbert-base-uncased` from huggingface.co, which this sandbox cannot reach. (b) Retraining the SVM reproduced exactly the same held-out accuracy (0.6645, verified in a throw-away copy), and no new labelled data exists to improve it. A multilingual checkpoint (e.g. `distilbert-base-multilingual-cased`) would be the natural research extension; keep the English baseline for a fair comparison. Commands are in §5.
6. **Free-text answer quality is not measured.** The only automatic response measure is keyword coverage (labelled *estimate*, 0.32-0.42). A proper rubric (correctness, relevance, completeness, clarity, safety) needs human reviewers; the User Study collects *perceived* quality only.
7. **User Study scope:** participants can open only their own comparison runs (other users' questions may contain personal health information). A multi-participant study therefore needs either one account per participant running the same questions, or a curated shared question-set feature (not built). Consent is collected in the UI, but **ethics approval is your institution's responsibility**; this software provides none.
8. **Not verified visually.** The UI was exercised in a headless DOM (jsdom), not a real browser: layout, colours, mobile breakpoints and fonts were **not** inspected. Please open each page on desktop and phone.
9. **Untouched legacy:** `/analysis`, `/user-study`, `/api/evaluation/*`, and the older six-architecture modules are unchanged (several modules they import are not in the archive). `models/*.pkl`, `ml_metrics.json`, `dl_metrics.json`, `health_qa_metrics.json` are legacy and unused by the three pipelines.
10. Evaluation runs use a background thread inside the web process and file storage (fine for one researcher; use a task queue for multi-user deployments). The "errors" counter counts failed *model calls* (3 per question if all three fail).
11. MediChat is a research and educational application. It does not diagnose or prescribe.

## 5. Reproduce

```bash
pip install -r requirements.txt            # + torch, transformers for DistilBERT
python -m pytest tests -q                  # 150 tests
python -m chatbot.health_qa.model_status   # read-only artifact / label / metadata check
python -c "import evaluation_service as e; print(e.start_run('held_out_test','full',wait=True))"
python -m chatbot.health_qa.evaluate       # regenerates models/evaluation/comparison_eval.json (used by chat routing)

# headless UI test (needs node + `npm i jsdom` in tests/ui)
python tests/ui/ui_server.py &             # temp DB + signed session cookie, port 5057
node tests/ui/ui_test.js

# training (separate from app start-up; overwrites artifacts - back them up first)
python -m chatbot.health_qa.train_svm
python -m chatbot.health_qa.train_distilbert --epochs 30 --lr 3e-5 --patience 5     # needs internet for the base model
```
Training scripts fit on the train split, tune on validation and never touch the test split. Do not add the evaluation files to training, or the reported numbers stop being held-out.

## 6. Files

New: `chatbot/health_qa/{language,localized,chat_reply,model_status}.py`, `evaluation_service.py`, `static/js/{chat,research}.js`, `static/css/research.css`, `datasets/{evaluation_label_map.json,multilingual_eval.csv,safety_multilingual_eval.csv}`, `tests/{test_multilingual_chat,test_evaluation,test_comparison_study,test_model_status}.py`, `tests/ui/*`, `models/evaluation/runs/*.json` (4 saved runs).
Modified: `app.py` (chat endpoint; evaluation + study endpoints), `comparison_service.py`, `chatbot/health_qa/{pipelines,safety}.py`, `database/database.py` (study table migration + study logic), `templates/{chat,comparison}.html`, `static/css/chat.css`, `models/evaluation/comparison_eval.json` (regenerated; original backed up), two environment-coupled tests in `tests/` (they assumed DistilBERT was always unavailable).
