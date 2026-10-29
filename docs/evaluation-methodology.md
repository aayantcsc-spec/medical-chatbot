# Evaluation methodology

All numbers come from completed runs of `evaluation_service.py`. Every run sends **the same questions to all three
chatbots**. A run is saved to `models/evaluation/runs/<run_id>.json` with its configuration, dataset version
(SHA-256 prefix), seed, per-question outputs and limitations. Until a real run exists, the UI shows
"Evaluation required".

## Datasets

| Dataset | Questions | Labels | Used for |
|---|---|---|---|
| Held-out test split (`intent_splits/test.csv`) | 155 | 91 exact intents | correctness, response time, reliability |
| Hindi + Hinglish (`multilingual_eval.csv`) | 52 | 91 intents | correctness in other languages |
| Question bank (`evaluation_questions.csv`) | 288 usable of 300 | 19 categories (mapped) | correctness (lenient/strict), response-quality estimate |
| Safety probes | 74 | emergency / non-emergency / off-topic | safety |

**Leakage control.** The models are trained on `train.csv` and tuned on `val.csv`. Before scoring, any question
that also appears in train or validation is excluded, as are duplicates and conflicting duplicates. The
exclusions are listed in each run.

## Metrics

| Metric | Definition | Better |
|---|---|---|
| Correctness | Predicted topic = expected topic. Accuracy plus macro precision/recall/F1 over the true classes. "No confident match" counts as wrong. | higher |
| Safety | Share of 38 emergency probes answered with urgent-care guidance; share of 18 off-topic questions declined; false alarms. Emergency detection itself is model-independent. | higher |
| Response quality | **Provisional automated estimate**: share of each question's expected keywords that appear in the reply. Not human-validated. Human ratings are in the User Study. | higher |
| Response time | Median, mean and p95 of server-side inference time per question (ms). Single process, sequential, models warm. | lower |
| Reliability | Share of questions answered without a model failure; failure count. | higher |

These metrics are **never combined into one score**.

**Overall best chatbot.** A chatbot is named overall best only if, on the latest completed runs, it is best or
within 2 percentage points of the best on **every one** of: held-out correctness, emergency guidance, off-topic
declining and reliability. Response time and the quality estimate are reported but never decide the result.
If no chatbot meets this, or a required run is missing, the page shows "No reliable overall winner".

## Results (29 Oct 2026)

See the table in the [README](../README.md). The current verdict is that Rule-Based is overall best under this rule.
DistilBERT leads on the question bank, and the SVM is fastest.

## Limitations

1. The test questions are author-written, not real patient conversations. The scores measure generalisation to new
   wording on the same topics.
2. Correctness means the topic was recognised. It does not prove the reply is medically correct; that would need
   review by clinicians.
3. The Hindi/Hinglish and safety sets were written by the project team and partly used while building the
   language layer, so they are regression sets.
4. Question-bank scores depend on an author-made category map (`evaluation_label_map.json`).
5. The samples are small (155 / 52 / 288 / 74). Differences of a few points are within noise, and no significance
   testing is performed.
6. Response times depend on the computer and its load. Compare them only within one run.
