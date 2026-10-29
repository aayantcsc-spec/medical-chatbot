# -*- coding: utf-8 -*-
"""
chat_reply.py - turns (predicted topic + question analysis) into a short, localised reply.

The three architectures only choose the TOPIC. This module writes the reply in one concise shape:

    one or two sentences that answer the question (with an uncertainty note for symptoms)
    up to three practical bullets
    one line on when to get medical help
    footer: "General health information · Not a diagnosis"

Doctor questions get a specialty suggestion; emergencies get an urgent response only.
`style` keeps each architecture's own level of detail (rule < ml < dl) so Comparison still shows
three different answers; style "chat" (the Chat page) uses the full concise reply.
Emergency handling is identical for every style and cannot be skipped. Output is Markdown
(**bold** labels and "- " bullets only).
"""
import re

from chatbot.health_qa import localized
from chatbot.health_qa.knowledge import TOPIC_BY_ID
from chatbot.health_qa.taxonomy import META_INTENTS, categories_of

_SENTENCE_SPLIT = re.compile(r"(?<=[.।])\s+(?=[A-Z0-9\u0900-\u097F])")

_DOCTOR_TOPIC_AREA = {"doctor_digestive": "digestive", "doctor_skin": "skin", "doctor_thyroid": "thyroid",
                      "doctor_joint_bone": "joint", "doctor_headache_neuro": "headache", "doctor_general_guidance": None}
_MENTAL_CATS = {"thoughts of self-harm", "mental health crisis"}


# ------------------------------------------------------------------------------------ helpers
def _sentences(text):
    return [p.strip() for p in _SENTENCE_SPLIT.split(str(text or "").strip()) if p.strip()]


def _bullets(text, limit=None):
    parts = _sentences(text)[:limit] if limit else _sentences(text)
    if len(parts) < 2:
        return " ".join(parts)
    return "\n".join("- " + p for p in parts)


def _first(text, n=2):
    return " ".join(_sentences(text)[:n])


def _section(title, body):
    """Bold inline label (no headings - replies stay compact)."""
    body = str(body or "").strip()
    return f"**{title}:** {body}" if body else ""


def _join(*parts):
    return "\n\n".join(p for p in parts if p)


def _footer(S):
    return f"_{S['footer']}_"


def specialty_area(canonical, topic_id=None):
    """Pick the specialty area from the topic (if it is a doctor_* topic) or from the wording."""
    if topic_id in _DOCTOR_TOPIC_AREA and _DOCTOR_TOPIC_AREA[topic_id]:
        return _DOCTOR_TOPIC_AREA[topic_id]
    import re as _re
    text = str(canonical or "").lower()
    for key, rx, _spec in localized.SPECIALTY_AREAS:
        if _re.search(rx, text):
            return key
    return "general"


def specialty_block(canonical, lang, topic_id=None):
    S = localized.strings(lang)
    key = specialty_area(canonical, topic_id)
    spec = next((s for k, _, s in localized.SPECIALTY_AREAS if k == key), "General Physician")
    first, sooner = localized.SPECIALTY_TEXT.get(key, localized.SPECIALTY_TEXT["general"]).get(
        lang, localized.SPECIALTY_TEXT["general"]["en"])
    lines = [first]
    if key != "general":
        lines.append(f"**{S['doctor']}:** {spec}")
    lines.append(f"**{S['see_sooner']}:** {sooner}")
    lines.append(S["emerg_not_routine"])
    return _join(*lines, f"_{S['not_dx']}_")


def emergency_text(safe, topic, analysis):
    """Localised emergency reply; the same content logic for every architecture."""
    lang = analysis.get("lang", "en")
    S = localized.strings(lang)
    cats = safe.get("categories", [])
    if "thoughts of self-harm" in cats:
        notice = S["selfharm"]
    elif cats and set(cats) <= _MENTAL_CATS:
        notice = S["mentalcrisis"]
    else:
        notice = S["emergency"]
    if lang == "en":
        guidance = [g for g in safe.get("guidance", []) if g]
    else:
        table = localized.GUIDANCE.get(lang, {})
        guidance = [table[c] for c in cats if c in table]
    parts = [f"**{S['warn']}** · {notice}"]
    if guidance:
        parts.append(f"**{S['while']}:**\n" + "\n".join("- " + g for g in guidance))
    parts.append(f"_{S['emerg_close']}_")
    return _join(*parts)


def _topic_pieces(topic, lang):
    """(short, advice, doctor, details, translated_ok)."""
    loc = localized.topic_text(topic["id"], lang) if lang != "en" else None
    if loc:
        return loc[0], loc[1], loc[2], "", True
    return topic["short"], topic["advice"], topic["doctor"], topic.get("details", ""), lang == "en"


def _meta_reply(topic_id, context_topic, analysis):
    lang = analysis.get("lang", "en")
    S = localized.strings(lang)
    if topic_id == "out_of_scope":
        return S["oos"]
    ctx = TOPIC_BY_ID.get(context_topic) if context_topic else None
    if ctx is None:
        if lang == "en":
            t = TOPIC_BY_ID[topic_id]
            return _join(t["short"], "I do not have an earlier health topic in this conversation to refer to. " + t["advice"])
        return S["no_answer"]
    short, advice, doctor, _d, ok = _topic_pieces(ctx, lang)
    note = "" if ok else f"_{S['en_only']}_"
    if topic_id == "follow_up_simplify":
        lead = {"en": "In simple words", "hinglish": "Aasan shabdon mein", "hi": "आसान शब्दों में"}[lang]
        rem = {"en": "Main thing to remember", "hinglish": "Yaad rakhne wali mukhya baat", "hi": "याद रखने वाली मुख्य बात"}[lang]
        return _join(f"**{lead}:** {short}", f"**{rem}:** {doctor}", note)
    nxt = {"en": "Next steps", "hinglish": "Agle kadam", "hi": "अगले कदम"}[lang]
    return _join(f"**{nxt}:**\n" + _bullets(advice + " " + doctor, 4), note)


# ----------------------------------------------------------------------------------- compose
def compose(style, topic_id, safe, analysis, context_topic=None, reply_topic=None):
    """Return (markdown reply, emergency_override: bool).

    topic_id    - what the architecture predicted (None = no confident match)
    reply_topic - optional topic to present instead (used for follow-ups like "why?" with context)
    """
    lang = analysis.get("lang", "en")
    S = localized.strings(lang)
    shown_id = reply_topic or topic_id
    topic = TOPIC_BY_ID.get(shown_id) if shown_id else None

    if safe.get("emergency"):
        return emergency_text(safe, topic, analysis), True

    kind = analysis.get("question_kind") or "general"
    canon = analysis.get("canonical", "")
    symptoms = analysis.get("symptoms", [])

    if topic is None:
        if symptoms or kind == "symptom":
            return _join(S["no_answer"], _footer(S)), False
        return S["fallback"], False

    if shown_id in META_INTENTS:
        return _join(_meta_reply(shown_id, context_topic, analysis), _footer(S)), False

    # ---- doctor / specialty questions: who to see first, when to go sooner
    if kind == "doctor" or shown_id in _DOCTOR_TOPIC_AREA:
        return specialty_block(canon, lang, shown_id if shown_id in _DOCTOR_TOPIC_AREA else None), False   # ends with its own "not a diagnosis"

    short, advice, doctor, details, translated = _topic_pieces(topic, lang)
    note = "" if translated else f"_{S['en_only']}_"
    urgent = bool(topic.get("urgent"))
    multi = len(symptoms) >= 2
    parts = []

    # ---- 1. the answer: one or two sentences
    if multi:
        names = ", ".join(_symptom_label(s, lang) for s in symptoms[:4])
        parts.append(S["multi_intro"].format(symptoms=names))
    elif kind == "symptom" and not urgent:
        parts.append(f"{_first(short)} {S['uncertain_short']}")
    else:
        parts.append(_first(short, 3))

    # ---- 2. up to three practical bullets (rule = none, ml = key facts, dl/chat = what to do)
    if style == "ml" and details and kind in ("definition", "general", "test", "prevention"):
        parts.append(_bullets(details, 3))
    elif style in ("dl", "chat", "ml") and advice:
        parts.append(_bullets(advice, 3))

    # ---- 3. when to get help (one short line; warning signs for urgent topics)
    if doctor:
        line = _first(doctor)
        parts.append(f"**{S['warn']}:** {line}" if urgent else line)

    # Q&A style: the reply answers the question and never asks one back.
    cats = set(categories_of(shown_id))
    if cats & {"mental_health", "stress_anxiety", "depression_low_mood", "emotional_wellbeing"} and shown_id != "mental_health_crisis":
        parts.append(S["support"])

    parts.append(note)
    parts.append(_footer(S))
    return _join(*parts), False


_SYMPTOM_LABELS = {
    "hinglish": {"fever": "bukhar", "headache": "sir dard", "dizziness": "chakkar", "cough": "khansi", "stomach pain": "pet dard",
                 "vomiting": "ulti", "nausea": "ji michlana", "diarrhea": "dast", "constipation": "kabz", "chest pain": "seene mein dard",
                 "shortness of breath": "saans ki dikkat", "sore throat": "gale mein dard", "common cold": "zukam", "fatigue": "thakan",
                 "weakness": "kamzori", "insomnia": "neend ki dikkat", "anxiety": "ghabrahat", "stress": "stress", "low mood": "udasi",
                 "toothache": "daant dard", "skin rash": "rash/khujli", "joint pain": "jodon ka dard", "back pain": "kamar dard"},
    "hi": {"fever": "बुखार", "headache": "सिरदर्द", "dizziness": "चक्कर", "cough": "खांसी", "stomach pain": "पेट दर्द",
           "vomiting": "उल्टी", "nausea": "जी मिचलाना", "diarrhea": "दस्त", "constipation": "कब्ज़", "chest pain": "सीने में दर्द",
           "shortness of breath": "सांस की दिक्कत", "sore throat": "गले में दर्द", "common cold": "सर्दी-जुकाम", "fatigue": "थकान",
           "weakness": "कमज़ोरी", "insomnia": "नींद की दिक्कत", "anxiety": "घबराहट", "stress": "तनाव", "low mood": "उदासी",
           "toothache": "दांत दर्द", "skin rash": "रैश/खुजली", "joint pain": "जोड़ों का दर्द", "back pain": "कमर दर्द"},
}


def _symptom_label(sym, lang):
    return _SYMPTOM_LABELS.get(lang, {}).get(sym, sym)
