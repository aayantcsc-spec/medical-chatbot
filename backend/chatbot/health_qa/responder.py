"""
responder.py - the ONE shared response layer used by Chat and Comparison for all three models.

    question -> (model predicts intent) -> curated topic text -> safety checks -> displayed reply

The models only choose the intent. This module turns the intent into text from the curated
knowledge base. Each architecture keeps its own *style* of answer so the three outputs differ
as their predictions differ:
    rule : overview + when to see a doctor
    ml   : overview + key facts + when to see a doctor
    dl   : overview + what you can do + when to see a doctor
The emergency override is identical for all three, so safety never depends on the model.
"""
from chatbot.health_qa.knowledge import TOPIC_BY_ID, DISCLAIMER
from chatbot.health_qa.taxonomy import (CATEGORY_BY_ID, META_INTENTS, care_line,
                                        categories_of, primary_category)

FALLBACK = ("I am not confident I understood that as a health topic I know about. I can give general "
            "information on common symptoms, first aid, medicine safety, nutrition, exercise, sleep, "
            "mental health, children's, women's, men's and older adults' health, tests and vaccines, and "
            "which doctor to see. Please rephrase, and speak to a qualified healthcare professional about "
            "your own situation. " + DISCLAIMER)

CLARIFY = ("I want to be sure I understand. Which part of the body or which symptom is bothering you, "
           "how long has it been going on, and is it getting worse? " + DISCLAIMER)

# one useful follow-up question per category, asked when more detail would change the advice
FOLLOW_UPS = {
    "physical_symptoms": "How long have you had this, and is it getting worse or are there other symptoms?",
    "infections_fever": "How high is the temperature, how many days has it lasted, and is there a rash, cough or trouble breathing?",
    "childrens_health": "How old is the child, and is the child drinking, passing urine and playing normally?",
    "pregnancy_maternal": "How many weeks pregnant are you, and are you having any bleeding, severe pain or reduced baby movements?",
    "womens_health": "How long has this been going on, and could you be pregnant?",
    "digestive_health": "How long has it lasted, and is there vomiting, blood in stool or weight loss?",
    "respiratory_health": "Is it getting worse, and do you have fever or any trouble breathing at rest?",
    "skin_hair": "How long has it been there, is it spreading, and did you start anything new recently?",
    "stress_anxiety": "How long have you felt this way, and is it affecting your sleep or daily life?",
    "depression_low_mood": "How long have you felt this way, and have you had any thoughts of harming yourself?",
    "emotional_wellbeing": "Would you like to tell me a little about what has been happening?",
    "doctor_guidance": "Which symptom or body area is it, and how long has it been going on?",
    "medication_information": "Which medicine do you mean? A pharmacist can check it against your other medicines.",
    "treatment_information": "Which condition do you mean?",
    "medical_tests_reports": "Which test or value are you asking about?",
    "sleep_problems": "How long have you had trouble sleeping, and what do you do before bed?",
    "diet_nutrition": "Do you have a medical condition, such as diabetes or kidney disease, that changes what you should eat?",
    "fitness_exercise": "Do you have any health condition, injury or pain that limits exercise?",
    "diabetes_blood_sugar": "Have you been diagnosed, and what are your recent blood sugar readings?",
    "blood_pressure": "Have you measured your blood pressure, and what were the readings?",
    "allergies": "What seems to trigger it, and have you ever had swelling or trouble breathing?",
}


def _join(*parts):
    return "\n\n".join(p for p in parts if p)


def _emergency_text(safe, topic):
    parts = [safe["notice"]]
    if safe["guidance"]:
        parts.append("While you wait for help: " + " ".join(safe["guidance"]))
    if topic and topic.get("urgent") and topic["id"] not in META_INTENTS:
        parts.append(topic["short"])
        parts.append(topic["advice"])
    parts.append("This is general safety information, not a diagnosis. " + "It does not replace emergency care.")
    return _join(*parts)


def _meta_text(topic_id, style, context_topic):
    ctx = TOPIC_BY_ID.get(context_topic) if context_topic else None
    if topic_id == "out_of_scope":
        t = TOPIC_BY_ID["out_of_scope"]
        return _join(t["short"], t["details"], t["advice"], DISCLAIMER)
    if ctx is None:
        t = TOPIC_BY_ID[topic_id]
        return _join(t["short"], "I do not have an earlier health topic in this conversation to refer to. " + t["advice"], DISCLAIMER)
    if topic_id == "follow_up_simplify":
        return _join("In simple words: " + ctx["short"], "Main thing to remember: " + ctx["doctor"], DISCLAIMER)
    return _join("Next steps for '" + ctx["id"].replace("_", " ") + "':", ctx["advice"], ctx["doctor"], care_line(ctx["id"]), DISCLAIMER)


def build_response(style, topic_id, safe, context_topic=None, ask_followup=True):
    """Return (text, safety_override: bool). `topic_id` may be None (no match)."""
    topic = TOPIC_BY_ID.get(topic_id) if topic_id else None
    if safe.get("emergency"):
        return _emergency_text(safe, topic), True
    if topic is None:
        return FALLBACK, False
    if topic_id in META_INTENTS:
        return _meta_text(topic_id, style, context_topic), False
    if style == "rule":
        body = [topic["short"], topic["doctor"]]
    elif style == "ml":
        body = [topic["short"], "Key points: " + topic["details"], topic["doctor"]]
    else:
        body = [topic["short"], "What you can do: " + topic["advice"], topic["doctor"]]
    cat = primary_category(topic_id)
    care = None if topic.get("urgent") else care_line(topic_id)
    follow = None
    if ask_followup and not topic.get("urgent"):
        q = FOLLOW_UPS.get(cat)
        follow = ("To give more useful guidance: " + q) if q else None
    support = SUPPORT_LINE if _SUPPORT_CATS & set(categories_of(topic_id)) and topic_id != "mental_health_crisis" else None
    return _join(*body, support, care, follow, DISCLAIMER), False


_SUPPORT_CATS = {"mental_health", "stress_anxiety", "depression_low_mood", "emotional_wellbeing"}
SUPPORT_LINE = ("Free, confidential support is available any time from Tele-MANAS (Government of India) on 14416 "
                "or 1800-891-4416. If you ever feel unsafe, call 112.")


def category_info(topic_id):
    cats = categories_of(topic_id)
    return {"category": cats[0] if cats else None,
            "category_name": CATEGORY_BY_ID[cats[0]]["name"] if cats else None,
            "categories": cats}
