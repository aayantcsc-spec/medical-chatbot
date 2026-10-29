# MediChat

**Comparative Analysis of Health Chatbots Based on Framework and Architecture**

Thakur College of Science & Commerce · Department of Artificial Intelligence and Machine Learning · Academic Year 2026–2027

MediChat compares different AI approaches for healthcare questions and evaluates their response quality, correctness,
response time, and safety. It has exactly three chatbots:

| Chatbot | Approach | Implementation |
|---|---|---|
| **Rule-Based** | rules, keywords, phrase patterns, mapped responses | `chatbot/health_qa/rule_engine.py` (no training) |
| **TF-IDF + SVM** | machine learning | `models/svm/svm_pipeline.pkl` (TF-IDF word + char n-grams, LinearSVC) |
| **DistilBERT** | deep learning | `models/distilbert_medical/` (fine-tuned `distilbert-base-uncased`, CPU) |

All three run locally. MediChat uses no LLMs, no RAG and no external AI APIs.

> MediChat gives general health information for education and research. It does not diagnose or prescribe, and it
> has not been clinically validated. In an emergency call 112 (India) or your local emergency number.

## Run it

Requirements: Python 3.11+ (developed on 3.13) and Node 20+.

```bash
python -m venv .venv
.venv\Scripts\activate                       # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt       # DistilBERT CPU build: pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
cd frontend && npm install && npm run build && cd ..
cd backend && python app.py                   # http://127.0.0.1:5000
```

For frontend development with hot reload, also run `cd frontend && npm run dev` (http://localhost:5173, or the next
free port). The database is created and migrated automatically on startup.

## Features

- **Home**: the three approaches, quick actions, and measured results (only when evaluation runs exist).
- **Chat**: ask anything in your own words (English, Hindi or Hinglish) to one chatbot. Replies are short:
  the answer, up to three practical points, when to get medical help, and "Not a diagnosis".
  Emergencies get an urgent response first.
- **Comparison**: one custom question goes to all three chatbots. You see each chatbot's reply, its server-side
  inference time and confidence (labelled), and its automated safety and quality checks. Above them is
  **"Best Response for This Question"** or **"No Clear Winner"**, with the reason.
- **Model Evaluation**: correctness, safety, response quality (provisional), response time and reliability, each
  charted on the same test questions, with sample sizes, runs, CSV export, and an overall verdict that follows a
  documented rule.
- **User Study**: blinded A/B/C ratings (1–5) of real comparison replies, with averages shown only from 5 participants up.
- **Chat History, Health Profile, Settings**: search, share and delete conversations; an optional minimal profile;
  account deletion.

## Measured results (29 Oct 2026, full datasets)

| | Rule-Based | TF-IDF + SVM | DistilBERT |
|---|---|---|---|
| Held-out topic accuracy (n = 155) | **74.8%** | 66.5% | 69.0% |
| Hindi/Hinglish accuracy (n = 52) | **92.3%** | 88.5% | 86.5% |
| Question-bank accuracy, lenient (n = 288) | 75.0% | 45.5% | **81.9%** |
| Emergency guidance shown (38 emergencies) | 100% | 100% | 100% |
| Off-topic questions declined (18) | 100% | 100% | 66.7% |
| Median inference time (held-out) | 44.8 ms | **5.3 ms** | 22.8 ms |
| Failures | 0 | 0 | 0 |

Under the documented rule, **Rule-Based** is the overall best: it is best or within 2 points of the best on
held-out correctness, emergency guidance, off-topic declining and reliability. DistilBERT is best on the
question bank, and the SVM is fastest. "Correctness" means the right health topic was recognised; it does not
mean the answer was verified as medically correct. See [docs/evaluation-methodology.md](docs/evaluation-methodology.md).

Re-run evaluations from the Model Evaluation page, or from the command line:

```bash
cd backend
python -m evaluation.evaluator                          # held-out test split
python -m evaluation.evaluator --dataset safety         # also: multilingual, question_bank
```

## Tests

```bash
cd backend && python -m pytest tests -q        # 203 tests
cd frontend && npm test                        # 9 tests
```

## Layout

```
backend/
  app.py                       Flask app: /api/v1 + serves the built frontend
  api/                         auth, profile, chat, comparison (+ user study), evaluations, diagnostics
  chatbot/health_qa/           knowledge base (91 topics), language layer, the 3 pipelines, reply composer, trainers
  chatbot/orchestrator/conversation_manager.py   Chat logic shared by all three chatbots
  chatbot/medical/safety.py    emergency check + response safety gate
  comparison_service.py        same question -> three chatbots + best-response selection
  evaluation_service.py        dataset evaluation (same questions for all three)
  database/                    sqlite layer, migrations, repository
  models/, datasets/
  legacy_app.py, templates/, static/   the original Jinja UI, unchanged (reference only)
frontend/                      React + Vite + TypeScript + Tailwind
archive/                       removed modules (six-architecture system, LogReg/MLP bots), kept for reference
docs/                          architecture, evaluation methodology, medical safety, API
```
