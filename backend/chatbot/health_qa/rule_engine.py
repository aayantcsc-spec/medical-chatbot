"""
rule_engine.py - the Rule-Based architecture (no training).

Order of work (emergency first, as required):
  1. emergency rules  - safety.assess() hits are mapped straight to an emergency topic
  2. spelling repair  - unknown words are matched to known keyword words (difflib, cutoff 0.84)
  3. special rules    - medicine-dose requests, "which doctor" questions (by body area)
  4. keyword scoring  - whole-word / phrase match over each topic's keywords (phrases count double)
  5. clarification    - vague symptom wording with no match -> ask a question instead of guessing
Rules and keywords live in knowledge.py / knowledge_extra.py, not in the UI.
Keyword matching is NOT a diagnosis: it only selects which curated information to show.
"""
import difflib
import re

from chatbot.health_qa import safety
from chatbot.health_qa.knowledge import TOPICS, TOPIC_BY_ID

_EMERGENCY_TOPIC = {
    "chest pain / possible heart attack": "chest_pain_emergency",
    "severe breathing difficulty": "breathing_difficulty",
    "possible stroke": "stroke_signs",
    "loss of consciousness / seizure": "emergency_warning_signs_general",
    "severe bleeding": "severe_bleeding",
    "poisoning / overdose": "poisoning",
    "pregnancy emergency": "emergency_warning_signs_general",
    "thoughts of self-harm": "self_harm",
    "mental health crisis": "mental_health_crisis",
}
_DOCTOR_WORDS = re.compile(r"\b(doctor|doctar|specialist|consult|physician|who treats|which dept|see a)\b")
_DOCTOR_AREAS = [   # first match wins
    ("doctor_thyroid", r"thyroid|goitre|goiter|hormone|tsh"),
    ("doctor_skin", r"skin|rash|acne|itch|eczema|hair|dermat|psoriasis"),
    ("doctor_digestive", r"stomach|gastric|acidity|digest|constipation|diarrh|liver|abdom|ulcer|bowel"),
    ("doctor_joint_bone", r"joint|knee|bone|arthritis|back pain|orthop|rheumat|shoulder|fracture"),
    ("doctor_headache_neuro", r"headache|migraine|seizure|numb|neuro|brain|nerve|dizz"),
]
_DOSE = re.compile(r"(how (much|many)|dose|dosage|dosege|\bmg\b|increase my dose).{0,40}(take|tablet|pill|medicine|medicin|syrup|paracetamol|ibuprofen|antibiotic|crocin|dose)|"
                   r"(dose|dosage|dosege) (of|for)|how (often|many times) can i take")
_VAGUE = re.compile(r"\b(pain|hurts?|hurting|unwell|sick|ill|symptoms?|problem|feeling|feel|ache|aching|weak|not well)\b")

_vocab = set()
for _t in TOPICS:
    for _k in _t["keywords"]:
        _vocab.update(w for w in re.findall(r"[a-z]+", _k) if len(w) >= 5)
_STATIC = {"temprature": "temperature", "helth": "health", "stomack": "stomach", "headace": "headache", "hedache": "headache",
           "diarhea": "diarrhea", "diabeties": "diabetes", "presure": "pressure", "slepp": "sleep", "symtoms": "symptoms"}


def clean(text):
    text = re.sub(r"[^a-z0-9\s\-']", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def repair_spelling(text):
    out = []
    for w in text.split():
        if w in _STATIC:
            out.append(_STATIC[w])
        elif len(w) >= 6 and w not in _vocab:
            m = difflib.get_close_matches(w, _vocab, n=1, cutoff=0.84)
            out.append(m[0] if m else w)
        else:
            out.append(w)
    return " ".join(out)


def _score(text):
    scores = {}
    padded = " " + text + " "
    for t in TOPICS:
        s = 0
        for kw in t["keywords"]:
            if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", padded):
                s += 2 if " " in kw else 1
        if s:
            scores[t["id"]] = s
    return scores


def classify(question):
    """Return dict(topic, ranking[(topic, strength)], rule, clarify)."""
    raw = clean(question)
    text = repair_spelling(raw)
    safe = safety.assess(question)
    if safe["emergency"]:                                   # 1. emergency first
        for cat in safe["categories"]:
            if cat in _EMERGENCY_TOPIC:
                t = _EMERGENCY_TOPIC[cat]
                return {"topic": t, "ranking": [(t, 1.0)], "rule": "emergency", "clarify": False}
    if safe["mode"] == "informational":                      # "What are the signs of a stroke?" -> that topic
        for cat in safe["categories"]:
            if cat in _EMERGENCY_TOPIC:
                t = _EMERGENCY_TOPIC[cat]
                return {"topic": t, "ranking": [(t, 1.0)], "rule": "emergency_topic_info", "clarify": False}
    if _DOSE.search(text):                                   # 3a. never answer with a dose
        return {"topic": "medication_dosage_request", "ranking": [("medication_dosage_request", 1.0)],
                "rule": "dose_request", "clarify": False}
    if _DOCTOR_WORDS.search(text):                           # 3b. "which doctor" by body area
        for tid, rx in _DOCTOR_AREAS:
            if re.search(rx, text):
                return {"topic": tid, "ranking": [(tid, 1.0)], "rule": "doctor_area", "clarify": False}
    scores = _score(text)                                    # 4. keyword scoring
    if not scores:
        return {"topic": None, "ranking": [], "rule": "none", "clarify": bool(_VAGUE.search(text))}
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if _DOCTOR_WORDS.search(text) and ranked[0][0] not in ("out_of_scope",):
        if not any(tid.startswith("doctor_") for tid, _ in ranked[:2]):
            ranked.insert(0, ("doctor_general_guidance", ranked[0][1] + 1))
    top = ranked[0][0]
    return {"topic": top, "ranking": [(t, min(1.0, s / 3)) for t, s in ranked[:5]], "rule": "keywords", "clarify": False}
