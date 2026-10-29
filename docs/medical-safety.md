# Medical safety and responsible AI

MediChat is an educational research tool. It does not diagnose, rule out or confirm conditions, does not
prescribe or give doses, and has not been clinically validated.

## Safeguards

| # | Safeguard | Where |
|---|---|---|
| 1 | Visible disclaimer on the landing page, the chat input, the footer and onboarding | `frontend/src/components/common.tsx` (`MedicalDisclaimer`), Chat page |
| 2 | Emergency detection runs on the **user's message before any bot**, in English, Hindi and Hinglish. It never looks at model output or confidence. | `chatbot/health_qa/safety.py`, called through `chatbot/medical/safety.py` |
| 3 | An emergency **replaces** the ordinary reply with urgent guidance (112, Tele-MANAS 14416 for self-harm), with no questionnaire first. | `ConversationManager.process`, `pipelines._Base.predict` (all three chatbots) |
| 4 | Informational questions about emergencies ("What are the warning signs of a stroke?") are recognised and not treated as alarms. Self-harm wording is never treated as informational. | `safety.assess` |
| 5 | **Response gate**: a reply giving a medicine dose, claiming a diagnosis ("You have …"), or discouraging a doctor visit is **rejected** and replaced by a safe fallback. It is not just down-scored. The original is kept as `withheld_response` for research transparency. | `chatbot/medical/safety.py` |
| 6 | In the Comparison, a reply rated Unsafe can never be selected as best. If no reply is eligible, "No Clear Winner" is shown. | `comparison_service.rank_responses` |
| 7 | Symptom replies say "These symptoms alone cannot identify the cause"; every reply ends "Not a diagnosis"; model confidence is labelled "not clinically calibrated" and never used to choose a best reply. | `chatbot/health_qa/chat_reply.py`, Comparison page |
| 8 | Unsupported or low-confidence input gets an explicit limitation message instead of a guess. | each pipeline's `no_match` path |
| 9 | Safety status is stored per message (`chats.safety_status`). No extra personal details are stored for safety. | `database/repository.py` |

Tests cover all of this across phrasings and languages: `backend/tests/test_multilingual_chat.py`,
`test_medichat46.py`, `test_best_response.py` and `test_api_v1.py` (emergency-first for every chatbot). On the 74-probe safety set,
detection precision and recall are both 1.00.

## Personal data

- Registration asks only for name, email and password. Passwords are stored as werkzeug salted hashes.
- The health profile is optional and minimal: age range, height, weight, smoking, activity and a lifestyle goal.
  It is never used to change an answer or infer a diagnosis. Fields collected by the earlier version
  (allergies, conditions, medications …) are no longer collected, and the user can erase them from the Profile page.
- Users can only access their own conversations; every query is scoped by `user_id` in SQL.
- Shared conversation links are opt-in, read-only and revocable.
- User-study ratings use a salted pseudonymous participant id, and responses are blinded (A/B/C, shuffled).
- Logs never contain passwords, tokens or message text from chat requests.

## Retention

- Deleting a conversation removes it and its messages permanently.
- Deleting the profile removes the profile row.
- Deleting the account removes the user, profile, conversations, messages, saved comparisons and their
  study ratings. Evaluation experiments the user started are kept but de-linked, because they contain
  no personal data.

## Before any public deployment

- Have Hindi/Hinglish safety text reviewed by a clinician and a professional translator.
- Re-check emergency numbers for the target region.
- Obtain ethics approval for any study with participants.
- Serve over HTTPS with `SESSION_COOKIE_SECURE=true`, and move rate-limit storage to Redis.
