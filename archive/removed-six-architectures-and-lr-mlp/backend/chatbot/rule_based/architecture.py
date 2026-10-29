"""
Architecture 1 - Rule-Based.

Hand-written IF-THEN rules: each rule lists trigger keywords (plain substring/word matches on the
normalised message) and a fixed reply. The first-ranked rule (most triggers matched, then rule
priority) answers; up to two further matched rules add one line each. No learning, no dataset
lookup, no disease names - this architecture deliberately gives general symptom guidance only.
"""
import re

from chatbot.symptom.base import Architecture, DISCLAIMER, join, bullet
from chatbot.symptom.knowledge import norm

# (rule id, priority, trigger keywords, overview, self-care, see-a-doctor-if)
RULES = [
    ("fever", 9, ["fever", "temperature", "feverish", "hot and cold", "chills"],
     "A fever is usually the body's response to an infection.",
     ["Rest and drink plenty of fluids.", "Wear light clothing and keep the room comfortable.",
      "Check your temperature every few hours and note it down."],
     "the fever lasts more than 3 days, goes above 39.5 C (103 F), or comes with a stiff neck, rash, confusion or breathing trouble"),
    ("cough_cold", 7, ["cough", "sneez", "runny nose", "blocked nose", "stuffy nose", "congestion", "sore throat", "cold"],
     "Coughs, sneezing and a sore throat are commonly caused by viral infections of the nose and throat.",
     ["Drink warm fluids and rest.", "Steam inhalation or saline rinses may ease a blocked nose.",
      "Cover coughs and sneezes and wash your hands often."],
     "symptoms last more than 10 days, you cough up blood, have a high fever, or feel short of breath"),
    ("headache", 8, ["headache", "head ache", "head hurts", "migraine", "head pain"],
     "Headaches are very common and often linked to tension, dehydration, poor sleep or screen strain.",
     ["Drink water and rest in a quiet, dim room.", "Take regular breaks from screens.",
      "Keep a note of when headaches happen and what might trigger them."],
     "the headache is sudden and severe, follows a head injury, or comes with fever, a stiff neck, weakness or vision changes"),
    ("stomach", 8, ["stomach", "abdominal", "abdomen", "belly", "tummy", "nausea", "vomit", "diarrh", "loose motion", "acidity", "heartburn", "indigestion"],
     "Stomach upset, nausea or loose motions are often caused by infections, food, or acidity.",
     ["Sip water or oral rehydration solution often.", "Eat small, plain meals and avoid oily or spicy food.",
      "Wash your hands well before eating."],
     "you cannot keep fluids down, see blood in vomit or stool, have severe pain, or show signs of dehydration"),
    ("skin", 6, ["rash", "itch", "pimple", "acne", "blister", "spots", "peeling", "scaly", "skin"],
     "Skin rashes and itching have many causes, including allergic reactions, infections and irritation.",
     ["Keep the area clean and dry.", "Avoid scratching and harsh soaps.", "Wear loose cotton clothing."],
     "the rash spreads quickly, blisters, is painful, or comes with fever or swelling of the face"),
    ("joint_body", 6, ["joint", "knee", "back pain", "neck pain", "body ache", "muscle", "stiff"],
     "Joint, back and muscle pain often come from strain, posture or inflammation.",
     ["Rest the painful area and avoid heavy lifting.", "Gentle stretching and warm compresses may help.",
      "Keep a good posture when sitting."],
     "the pain is severe, follows an injury, or comes with swelling, redness, fever or numbness"),
    ("urinary", 7, ["urin", "pee", "burning when", "bladder"],
     "Burning or frequent urination is often linked to an infection of the urinary tract.",
     ["Drink plenty of water.", "Do not hold in urine for long periods.", "Keep the genital area clean."],
     "you have fever, back or side pain, blood in urine, or symptoms that do not improve in 1-2 days"),
    ("fatigue", 5, ["tired", "fatigue", "weak", "exhausted", "no energy", "lethargic"],
     "Tiredness can be caused by poor sleep, stress, diet, infections or other health conditions.",
     ["Aim for regular sleep at the same times each day.", "Eat balanced meals and stay hydrated.",
      "Take short walks if you are able to."],
     "tiredness lasts more than 2 weeks, or comes with weight loss, fever, breathlessness or low mood"),
    ("dizziness", 7, ["dizzy", "dizziness", "light headed", "lightheaded", "spinning", "vertigo"],
     "Dizziness can be caused by dehydration, low blood sugar, inner-ear problems or standing up quickly.",
     ["Sit or lie down until it passes.", "Drink water and eat something if you have skipped meals.",
      "Stand up slowly."],
     "you faint, have chest pain, slurred speech, weakness on one side, or the dizziness keeps returning"),
    ("eyes_yellow", 9, ["yellow skin", "yellow eyes", "yellowish", "dark urine"],
     "Yellowing of the skin or eyes, or very dark urine, can be a sign of a liver or blood problem.",
     ["Avoid alcohol.", "Drink plenty of water.", "Rest."],
     "you notice yellow skin or eyes at all - this needs a doctor's review soon"),
    ("breathing", 10, ["breathless", "short of breath", "wheez", "breathing"],
     "Breathlessness or wheezing can be linked to asthma, infections, allergies or heart and lung conditions.",
     ["Sit upright and try to stay calm.", "Avoid smoke, dust and other triggers.",
      "Use a prescribed inhaler only as your doctor has instructed."],
     "breathlessness is new, getting worse, or comes with chest pain, blue lips or confusion - seek care urgently"),
]

DURATION = re.compile(r"\b(\d+|a|one|two|three|four|five|six|seven|few|several)\s+(hour|day|week|month)s?\b|\bsince (yesterday|last \w+|morning)\b")


class RuleBasedArchitecture(Architecture):
    key = "rule_based"
    name = "Rule-Based"
    method = "Hand-written IF-THEN keyword rules with fixed replies (no learning, no disease names)"

    def version(self):
        return f"rules-{len(RULES)}"

    def _answer(self, text, context):
        t = " " + norm(text) + " "
        fired = []
        for rid, prio, triggers, *_ in RULES:
            hits = [k for k in triggers if k in t]
            if hits:
                fired.append((len(hits), prio, rid, hits))
        fired.sort(key=lambda x: (-x[0], -x[1]))
        evidence = [{"type": "rule", "rule": rid, "matched_keywords": hits} for _, _, rid, hits in fired]
        if not fired:
            return {"status": "no_match", "evidence": [],
                    "response": join("I could not match your message to one of my symptom rules. Please describe your "
                                     "main symptom (for example fever, cough, headache, stomach pain or rash) and how long you have had it.",
                                     DISCLAIMER)}
        rules = {r[0]: r for r in RULES}
        _, _, overview, care, doctor = rules[fired[0][2]][1:]
        extras = [rules[f[2]][3] for f in fired[1:3]]
        duration = DURATION.search(t)
        parts = [overview]
        if extras:
            parts.append("You also mentioned other symptoms. " + " ".join(extras))
        parts.append("What you can do:\n" + bullet(care))
        parts.append(f"See a doctor if {doctor}.")
        if not duration and not context.get("duration"):
            parts.append("How long have you had these symptoms?")
        parts.append(DISCLAIMER)
        return {"status": "ok", "response": join(*parts), "evidence": evidence,
                "extracted": {"rules_fired": [f[2] for f in fired], "duration_mentioned": bool(duration)}}
