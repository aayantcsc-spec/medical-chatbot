"""
Architecture 6 - Generation-Based (template natural-language generation).

A classic NLG pipeline, no neural model:
    1. Input understanding  - structured slots from the NLP analyser (symptoms, severity, duration,
                              temperature) plus conversation context (e.g. a duration given earlier).
    2. Content planning     - which messages to say: acknowledgement, restatement, common general
                              causes, self-care, warning signs, and a next step whose urgency depends
                              on severity and duration.
    3. Surface realisation  - each message is written from one of several sentence templates. The
                              template is chosen by a stable hash of the input, so the same message
                              always produces the same reply (reproducible evaluation).
It never names a specific disease for the user and never mentions medicine doses.
"""
import hashlib

from chatbot.symptom.base import Architecture, DISCLAIMER, join, bullet
from chatbot.nlp_based.architecture import analyse, _group
from chatbot.symptom.knowledge import PROMPT_REVIEW

ACK = {
    "severe": ["I'm sorry you're dealing with this - it sounds really uncomfortable.",
               "That sounds hard to cope with, and it's right to take it seriously."],
    "normal": ["Thanks for describing how you feel.", "I understand - let's go through this step by step.",
               "Thank you for the details."],
}
CAUSES = {
    "fever": "Fever is most often the body fighting an infection, such as a viral illness.",
    "respiratory": "Cough, congestion and throat symptoms are commonly caused by viral infections, allergic reactions or irritants like smoke.",
    "digestive": "Stomach symptoms are often linked to infections, something you ate, or acidity.",
    "skin": "Skin symptoms can come from allergic reactions, irritation, infections or dryness.",
    "urinary": "Urinary burning or frequency is commonly linked to an infection of the urinary tract.",
    "pain": "Aches and stiffness often come from strain, posture, overuse or inflammation.",
    "general": "Feeling tired or unwell can have many causes, including poor sleep, stress and infections.",
    "head": "Headaches and dizziness are often linked to dehydration, tension, poor sleep or an infection.",
}
CARE = {
    "fever": "Rest and drink plenty of fluids; light clothing can help you stay comfortable.",
    "respiratory": "Warm drinks, rest and steam may ease your breathing passages.",
    "digestive": "Take small sips of water or oral rehydration solution and eat plain, light food.",
    "skin": "Keep the skin clean and dry, and try not to scratch.",
    "urinary": "Drink more water and don't hold in urine.",
    "pain": "Rest the area, keep a good posture, and try gentle stretching or a warm compress.",
    "general": "Aim for regular sleep, balanced meals and enough water.",
    "head": "Rest in a quiet, dim room, drink water and take a break from screens.",
}
RED_FLAGS = {
    "fever": "a fever above 39.5 C (103 F), a stiff neck, a rash that doesn't fade, or confusion",
    "respiratory": "breathlessness, chest pain, or coughing up blood",
    "digestive": "blood in vomit or stool, severe pain, or being unable to keep fluids down",
    "skin": "a rash that spreads fast, blisters widely, or comes with fever or face swelling",
    "urinary": "fever, pain in your side or back, or blood in the urine",
    "pain": "severe pain after an injury, numbness, weakness, or a hot swollen joint",
    "general": "weight loss you can't explain, fainting, or symptoms that keep getting worse",
    "head": "a sudden, severe headache, a stiff neck, confusion, weakness on one side, or changes in vision",
}
NEXT = {
    "urgent": ["Please arrange to see a doctor today.", "It would be best to get a medical review today rather than wait."],
    "soon": ["Because this has gone on for a while, please book a doctor's appointment in the next day or two.",
             "Given how long this has lasted, it's a good idea to see a doctor soon."],
    "watch": ["If things don't improve in 2-3 days, please see a doctor.",
              "Keep an eye on how you feel, and see a doctor if it isn't improving in a few days."],
}


def _pick(options, seed):
    return options[seed % len(options)]


def _days(duration):
    if not duration:
        return None
    return duration["value"] * {"hour": 1 / 24, "day": 1, "week": 7, "month": 30}[duration["unit"]]


class GenerationArchitecture(Architecture):
    key = "generation_based"
    name = "Generation-Based"
    method = "Template NLG: slot extraction -> content plan -> templated sentence realisation"

    def version(self):
        return "nlg-templates-v1"

    def _answer(self, text, context):
        a = analyse(text)
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        duration = a["duration"] or context.get("duration")
        slots = {"symptoms": [s["name"] for s in a["symptoms"]], "severe": any(s["modifier"] == "severe" for s in a["symptoms"]),
                 "duration": duration, "temperature": a["temperature"], "negated": a["negated"]}
        if not a["symptoms"]:
            return {"status": "no_match", "extracted": {"slots": slots},
                    "response": join("I'd like to help, but I couldn't pick out a symptom from your message.",
                                     "Could you tell me what you're feeling, where, and for how long?", DISCLAIMER)}
        groups = []
        for s in a["symptoms"]:
            g = _group(s["id"])
            if g not in groups:
                groups.append(g)
        days = _days(duration)
        high_temp = a["temperature"] and ((a["temperature"]["unit"] == "C" and a["temperature"]["value"] >= 39.5)
                                          or (a["temperature"]["unit"] == "F" and a["temperature"]["value"] >= 103))
        concerning = slots["severe"] or high_temp or any(s["id"] in PROMPT_REVIEW for s in a["symptoms"])
        urgency = "urgent" if concerning else "soon" if (days is not None and days >= 3) else "watch"
        plan = ["acknowledge", "restate", "causes", "self_care", "red_flags", "next_step"]

        names = slots["symptoms"]
        listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        restate = f"You mentioned {listed}" + (f" for {duration['text']}" if duration else "") + "."
        if high_temp:
            restate += f" A temperature of {a['temperature']['value']:g} {a['temperature']['unit']} is high."
        sentences = {
            "acknowledge": _pick(ACK["severe" if concerning else "normal"], seed),
            "restate": restate,
            "causes": " ".join(CAUSES[g] for g in groups[:2]),
            "self_care": "Things that usually help:\n" + bullet(CARE[g] for g in groups[:3]),
            "red_flags": "Get medical help quickly if you notice " + "; or ".join(RED_FLAGS[g] for g in groups[:2]) + ".",
            "next_step": _pick(NEXT[urgency], seed >> 4),
        }
        tail = [] if duration else ["How long have you had these symptoms? That helps me give better guidance."]
        response = join(*[sentences[p] for p in plan], *tail, DISCLAIMER)
        return {"status": "ok", "response": response,
                "extracted": {"slots": slots, "content_plan": plan, "urgency": urgency, "groups": groups},
                "evidence": [{"type": "template", "message": p} for p in plan]}
