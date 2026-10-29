# REST API (`/api/v1`)

Envelope: `{"success": true, "data": ..., "meta"?: {page, per_page, total, pages}}`, or on error
`{"success": false, "error": {"code", "message", "field"?}}`.

- **Auth:** session cookie (HttpOnly, SameSite=Lax).
- **CSRF:** every POST/PUT/PATCH/DELETE sends `X-CSRF-Token`, obtained from `GET /auth/csrf`.
- **Errors:** internal errors return `500 PROCESSING_ERROR` with no details. Unknown `/api` paths return 404.
- **Rate limit:** register and login are rate-limited.

Chatbot keys: `rule` (Rule-Based), `ml` (TF-IDF + SVM), `dl` (DistilBERT).

| Method | Path | Notes |
|---|---|---|
| GET | `/auth/csrf`, `/auth/me` | |
| POST | `/auth/register` `{name, email, password}` · `/auth/login` · `/auth/logout` | |
| PATCH / DELETE | `/auth/me` `{name}` · `/auth/account` `{confirm: "DELETE"}` | 🔒 |
| GET / PUT / DELETE | `/profile` | 🔒 optional fields + research acknowledgement |
| GET | `/chat/options` | the three chatbots (availability, architecture), example questions |
| POST | `/chat` `{message, bot, conversation_id?, save?}` | → `{reply, bot, handled_by, safety_status, response_time_ms, conversation_id, details{intent, confidence, inference_ms}}` |
| GET | `/chats?q&page` · `/chats/:id` | 🔒 own conversations only |
| PATCH / DELETE | `/chats/:id` | 🔒 |
| POST / DELETE | `/chats/:id/share` | 🔒 · `GET /shared/:token` is public, read-only |
| GET | `/comparison/options` | chatbots, examples, scoring rules |
| POST | `/comparison/ask` `{question}` | the same question to all three → `results{rule,ml,dl}`, `overall_selection`, `run_id` (if signed in) |
| GET | `/study/runs` · `/study/runs/:id` · `/study/summary` · `/study/export.csv` | 🔒 blinded user study |
| POST | `/study/ratings` `{run_id, consent: true, ratings, positions}` | 🔒 |
| GET | `/evaluations/datasets` · `/evaluations` · `/evaluations/:id` · `/evaluations/:id/status` · `/evaluations/:id/export.csv` | 🔒 |
| POST | `/evaluations` `{dataset, mode: quick\|full\|custom, limit?, category?}` | 🔒 → 202; 409 if a run is in progress |
| GET | `/analytics/overview` · `/analytics/summary` · `/analytics/history?dataset` | 🔒 per-metric results + overall verdict |
| GET | `/health` · `/diagnostics/database` · `/diagnostics/routes` · `/diagnostics/models` | diagnostics 🔒 (no paths or secrets) |

🔒 = requires sign-in.
