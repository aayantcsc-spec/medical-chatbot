# Architecture

## Request flow

```
Browser (React)  ──JSON + session cookie + X-CSRF-Token──►  Flask /api/v1
                                                              │
          Chat: ConversationManager            Comparison: comparison_service.run_comparison
          (chatbot/orchestrator/conversation_manager.py)       (same question → all three)
                                                              │
   1. emergency check on the question (chatbot/health_qa/safety.py) → urgent response, stop
   2. language layer: greetings answered without a model; Hindi/Hinglish → English canonical text
   3. the chatbot(s) predict a health TOPIC:
        Rule-Based   rule_engine.py   keyword/phrase rules, spelling repair, emergency rules
        TF-IDF + SVM svm_pipeline.pkl TF-IDF features → LinearSVC, reject threshold from validation
        DistilBERT   distilbert_medical/  fine-tuned transformer, softmax, confidence threshold
   4. chat_reply.compose writes a short reply for that topic (localised), per-chatbot detail level
   5. response safety gate (chatbot/medical/safety.py): doses / diagnosis claims / "don't see a doctor" → rejected
```

Each chatbot predicts its own topic, so replies to the same question can differ. That difference is what the
comparison studies. A chatbot that is not confident says so rather than guessing, and the result is reported as
`no_match`, never as a successful prediction. A chatbot whose model files are missing reports `unavailable`
with the reason, and another model's answer is never substituted.

## Timing

`inference_ms` is measured inside each pipeline with `time.perf_counter()`, from the start of its own processing
to the end of reply composition. Network and browser rendering time are excluded. Models are loaded once per
process and warmed up in the background at startup, so model loading never counts as inference time.

## Best response for one question (`comparison_service.rank_responses`)

- Only replies with status `ok` are compared. A reply rated **Unsafe** is excluded, however fluent it is.
- The score is correctness 40 (only if the question is in a labelled dataset), safety 30, quality 20 and speed 10,
  re-normalised over the parts that can be measured. Model confidence is never used.
- A lead under 2 points, or a lead that comes only from speed, gives **No Clear Winner**.
- These are automated heuristics, labelled as such in the UI. They are not human-validated medical correctness.

## Data

SQLite (`backend/healthbot.db`), with additive, versioned migrations (`database/migrations.py`):
- `users`, `health_profiles`, `conversations` and `chats` hold the messages.
- `comparison_runs` and `comparison_study_ratings` hold the user study.
- `experiments` and `performance_results` hold evaluation summaries.

The full detail of each evaluation run is in `models/evaluation/runs/<id>.json`.

## Scope change (29 Oct 2026)

The project was fixed to exactly three chatbots. The six-architecture symptom system (including a RAG module) and
the Logistic Regression and MLP bots were moved to `archive/` with their models and evaluation runs.
Migration `004_three_chatbots_only` removed their summary rows from SQLite. `legacy_app.py` is the original Jinja
application and is kept unchanged for reference; it still contains the old hybrid/RAG code and is not part of the
running MediChat app.
