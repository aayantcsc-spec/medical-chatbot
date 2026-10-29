"""
onboarding_context.py
---------------------
Turns what the user typed during onboarding into a small, safe "user context"
for the chatbot. Used ONLY by the normal chat (never by Comparison, the
User Study or evaluation files).

Rules this file follows:
  - uses only what the user really typed; nothing is guessed or invented
  - never says "you have <disease>"; it says "you mentioned ..."
  - never gives medicine names or doses
  - never uses allergies, medications or medical conditions in a reply
    (they stay private in the profile and are not repeated in the chat)
  - is skipped for emergency questions and unrelated questions
"""

import re

# ----------------------------------------------------------------------
# topics the context can talk about
#   words : words that show a question / concern is about this topic
#   tip   : general advice (not a diagnosis)
#   warn  : when to get medical help
# ----------------------------------------------------------------------
TOPICS = {
    "headache": {
        "words": ["headache", "headaches", "migraine", "head pain", "head hurts"],
        "label": "headaches",
        "tip": "factors such as poor sleep, dehydration, stress, long screen time or irregular meals may be worth considering, and resting in a quiet place with some water often helps",
        "warn": "If a headache is sudden or severe, or comes with weakness, confusion, trouble speaking or vision changes, seek medical attention.",
    },
    "cough": {
        "words": ["cough", "coughing", "phlegm", "sore throat"],
        "label": "cough",
        "tip": "warm fluids, rest, avoiding smoke and dust and keeping the air moist can help you feel more comfortable, and most coughs from colds settle in 1 to 3 weeks",
        "warn": "See a doctor if the cough lasts more than 3 weeks, or comes with blood, high fever, chest pain or shortness of breath.",
    },
    "weight": {
        "words": ["weight", "obesity", "overweight", "bmi", "lose weight", "weight loss"],
        "label": "weight management",
        "tip": "slow and steady changes work best: more vegetables, fruit and whole grains, fewer sugary drinks and fried snacks, sensible portions and regular walking",
        "warn": "Talk to a doctor or dietitian before a big diet change, or if your weight changes without trying.",
    },
    "diet": {
        "words": ["eat", "food", "foods", "diet", "nutrition", "meal", "meals", "healthy eating"],
        "label": "diet",
        "tip": "a balanced plate with vegetables, fruit, whole grains, pulses or lean protein and healthy fats, regular meals and enough water is a good general starting point",
        "warn": "A doctor or dietitian can give personal advice, especially if you have a medical condition or food allergy.",
    },
    "sleep": {
        "words": ["sleep", "insomnia", "tired", "fatigue", "rest"],
        "label": "sleep",
        "tip": "a regular bedtime, no screens or caffeine late in the day, and a dark, quiet, cool room usually help",
        "warn": "See a doctor if sleep problems last for weeks or you feel very sleepy during the day.",
    },
    "stress": {
        "words": ["stress", "anxiety", "anxious", "worried", "overwhelmed", "mood"],
        "label": "stress",
        "tip": "regular exercise, slow breathing, enough sleep, breaks from work and talking with someone you trust can ease stress",
        "warn": "If stress affects daily life for weeks, speak to a doctor or counsellor. If you ever think of harming yourself, contact emergency services or a crisis helpline right away.",
    },
    "exercise": {
        "words": ["exercise", "workout", "fitness", "walking", "active", "gym"],
        "label": "exercise",
        "tip": "starting with a 10 to 15 minute daily walk and slowly building towards about 150 minutes of moderate activity a week is a safe general goal",
        "warn": "Stop and get medical advice if exercise causes chest pain, severe breathlessness or dizziness.",
    },
    "fever": {
        "words": ["fever", "temperature", "chills"],
        "label": "fever",
        "tip": "rest, plenty of fluids and light clothing usually help while the body fights the infection",
        "warn": "See a doctor if the fever lasts more than 3 days, goes above 39.5 C (103 F), or comes with a stiff neck, rash or trouble breathing.",
    },
    "cold": {
        "words": ["cold", "flu", "runny nose", "sneezing", "congestion"],
        "label": "cold or flu symptoms",
        "tip": "rest, warm fluids and washing hands often help, and staying home protects others",
        "warn": "See a doctor if symptoms last more than 10 days or you have trouble breathing.",
    },
    "blood_pressure": {
        "words": ["blood pressure", "hypertension", "bp"],
        "label": "blood pressure",
        "tip": "less salt, regular activity, a healthy weight and regular checks all support healthy blood pressure",
        "warn": "Seek urgent care for very high readings with chest pain, severe headache or weakness.",
    },
    "diabetes": {
        "words": ["diabetes", "blood sugar", "sugar level"],
        "label": "blood sugar",
        "tip": "regular activity, whole grains, vegetables and fewer sugary drinks support healthy blood sugar",
        "warn": "Follow your doctor's plan, and seek urgent help for confusion, vomiting or very high readings.",
    },
    "back_pain": {
        "words": ["back pain", "backache", "neck pain", "joint pain", "knee pain"],
        "label": "body aches",
        "tip": "staying gently active, good posture and short movement breaks from sitting usually help",
        "warn": "See a doctor if pain lasts more than a few weeks or comes with numbness, weakness or fever.",
    },
    "stomach": {
        "words": ["stomach", "acidity", "heartburn", "constipation", "digestion", "bloating"],
        "label": "digestion",
        "tip": "smaller meals, more fibre and water, less oily food and not lying down right after eating can help",
        "warn": "See a doctor for blood in the stool, black stools, vomiting or severe stomach pain.",
    },
}

# questions with no health word in them, that depend on earlier context
VAGUE_PATTERNS = [
    "how can i feel better", "how do i feel better", "what should i do",
    "what can i do", "what should i eat", "what can i eat", "any tips",
    "any advice", "how can i improve", "how to improve", "what helps",
    "what do you suggest", "how can i get better", "will it get better",
    "what is good for me", "give me some tips", "what should i avoid",
]

EMERGENCY_WORDS = [
    "chest pain", "heart attack", "can't breathe", "cannot breathe", "trouble breathing",
    "difficulty breathing", "severe bleeding", "unconscious", "seizure", "stroke",
    "overdose", "poison", "swallowed", "suicide", "suicidal", "kill myself",
    "harm myself", "hurt myself", "want to die", "choking", "face drooping",
    "slurred speech", "coughing blood", "vomiting blood",
]

MAX_FIELD_LENGTH = 120


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _field(profile, key):
    """Read one field from a dict or sqlite3.Row. Returns clean text or ''."""
    if profile is None:
        return ""
    try:
        value = profile[key]
    except (KeyError, IndexError, TypeError):
        return ""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if text.lower() in ("none", "n/a", "na", "no", "nil", "-", "null"):
        return ""
    return text[:MAX_FIELD_LENGTH]


def _has_word(text, word):
    pattern = r"(?<![a-z])" + re.escape(word) + r"(?![a-z])"
    return re.search(pattern, text.lower()) is not None


def detect_topics(text):
    """Returns the list of topic ids whose words appear in the text."""
    found = []
    for topic_id, topic in TOPICS.items():
        if any(_has_word(text, w) for w in topic["words"]):
            found.append(topic_id)
    return found


def is_emergency(text):
    text = str(text or "").lower()
    return any(w in text for w in EMERGENCY_WORDS)


def is_vague(question):
    q = re.sub(r"[^a-z' ]", "", str(question or "").lower()).strip()
    return any(p in q for p in VAGUE_PATTERNS)


# ----------------------------------------------------------------------
# the context object
# ----------------------------------------------------------------------
def build_context(profile):
    """
    Build the user context from the saved onboarding profile.
    Only what the user typed is used. Empty fields are left empty.
    """
    concern = _field(profile, "health_concern")
    goal = _field(profile, "health_goal")
    activity = _field(profile, "activity_level")
    smoking = _field(profile, "smoking")

    return {
        "concern": concern,
        "goal": goal,
        "activity_level": activity,
        "smoking": smoking,
        "concern_topics": detect_topics(concern),
        "goal_topics": detect_topics(goal),
        # True when there is something to personalise with
        "has_context": bool(concern or goal),
    }


def summary_items(profile):
    """Short list for the 'Your Health Context' card: [(label, value), ...].
    Shows only the concern and goal. Allergies, medications and conditions are never shown."""
    ctx = build_context(profile)
    items = []
    if ctx["concern"]:
        items.append(("Health concern", ctx["concern"]))
    if ctx["goal"]:
        items.append(("Goal", ctx["goal"]))
    return items


# ----------------------------------------------------------------------
# used by the Rule-Based bot
# ----------------------------------------------------------------------
def rule_keywords(context, question):
    """
    The Rule-Based bot works with keywords. When the question is vague
    (for example 'How can I feel better?') and the user told us a concern
    during onboarding, return that concern so the bot's own keyword rules
    can match it. Otherwise return '' and the question is used as it is.
    """
    if not context or not context.get("concern"):
        return ""
    if is_emergency(question):
        return ""
    if detect_topics(question):          # the question already has its own keywords
        return ""
    if is_vague(question):
        return context["concern"]
    return ""


# ----------------------------------------------------------------------
# used by every bot AFTER it has answered
# ----------------------------------------------------------------------
def personalised_note(context, question):
    """
    Returns one short paragraph that connects the question to what the user
    shared during onboarding, or '' if it is not relevant.

    The bot's own answer is never replaced; this text is added after it.
    """
    if not context or not context.get("has_context"):
        return ""
    if is_emergency(question):
        return ""                         # emergencies: safety advice only

    question_topics = detect_topics(question)
    vague = is_vague(question)

    concern_topics = context["concern_topics"]
    goal_topics = context["goal_topics"]

    # 1) which onboarding topic is relevant to THIS question?
    chosen, source = None, None
    for t in question_topics:
        if t in concern_topics:
            chosen, source = t, "concern"
            break
        if t in goal_topics:
            chosen, source = t, "goal"
            break
    if chosen is None and vague:
        if concern_topics:
            chosen, source = concern_topics[0], "concern"
        elif goal_topics:
            chosen, source = goal_topics[0], "goal"
    if chosen is None:
        return ""                         # unrelated question: no forced personalisation

    topic = TOPICS[chosen]

    # 2) write the note in natural words
    if source == "concern":
        text = (f"Since {topic['label']} {'is' if not topic['label'].endswith('s') else 'are'} "
                f"one of the concerns you mentioned during onboarding, {topic['tip']}.")
    else:
        text = (f"Since you mentioned a goal related to {topic['label']} during onboarding, "
                f"{topic['tip']}.")

    # 3) a second goal that links to the first (for example headaches + better sleep)
    for g in goal_topics:
        if g != chosen:
            text += (f" Because your goal involves {TOPICS[g]['label']}, "
                     f"{TOPICS[g]['tip']}.")
            break

    # 4) lifestyle details only when they matter for the question
    if chosen == "exercise" and context["activity_level"]:
        text += (f" You described your activity level as \"{context['activity_level']}\", "
                 "so increase activity gradually.")
    if chosen == "cough" and context["smoking"] and context["smoking"].lower().startswith(("yes", "current", "daily", "smok", "occasion")):
        text += " Avoiding smoke, including your own, gives the airways a chance to recover."

    text += " " + topic["warn"]
    text += " This is general information based on what you shared, not a diagnosis."
    return text
