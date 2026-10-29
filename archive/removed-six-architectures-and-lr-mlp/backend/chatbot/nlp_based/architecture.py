"""
Architecture 2 - NLP-Based.

A small, explicit NLP pipeline (no trained model):
    1. normalise + tokenise
    2. light suffix stemming so "coughing"/"coughs" match "cough"
    3. negation scope: "no fever", "not vomiting", "without a rash" are excluded
    4. n-gram matching of stemmed tokens against the dataset symptom lexicon (Symptom-severity.csv
       vocabulary + everyday synonyms), longest phrase first
    5. entity extraction: duration, temperature, severity modifiers, body parts
The reply summarises what was understood, ranks the symptoms by the dataset's severity weight and
asks for missing details. Like the rule-based bot it does not name diseases.
"""
import re

from chatbot.symptom.base import Architecture, DISCLAIMER, join, bullet
from chatbot.symptom.knowledge import lexicon, severity, humanise, PROMPT_REVIEW

STOPWORDS = set("""a an the i me my im i'm ive i've have has had am is are was were be been being and or but so of to
in on at for with from by it its this that these those very really quite just also some any since about
feel feeling felt getting got get having been doctor please help""".split())
NEGATORS = {"no", "not", "without", "never", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't", "nor", "none"}
SEVERE = {"severe", "severely", "terrible", "unbearable", "extreme", "intense", "worst", "bad", "high", "sharp"}
MILD = {"mild", "slight", "slightly", "little", "bit", "low"}
BODY_PARTS = ["head", "chest", "stomach", "abdomen", "back", "neck", "throat", "nose", "eye", "eyes", "ear", "skin", "leg",
              "legs", "arm", "arms", "knee", "knees", "joint", "joints", "foot", "feet", "hand", "hands", "face", "scalp", "urine"]
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "few": 3, "several": 4}
DURATION = re.compile(r"\b(\d+|a|an|one|two|three|four|five|six|seven|few|several)\s+(hour|day|week|month)s?\b")
TEMPERATURE = re.compile(r"\b(\d{2,3}(?:\.\d)?)\s*(?:°|degrees?)?\s*(c|f|celsius|fahrenheit)?\b")

GUIDANCE = {
    "fever": "Rest, drink fluids and track your temperature.",
    "respiratory": "Warm fluids, rest and avoiding smoke can ease cough and congestion.",
    "digestive": "Sip fluids often and eat small, plain meals.",
    "skin": "Keep the skin clean and dry and avoid scratching or harsh products.",
    "pain": "Rest the affected area; gentle movement and warm compresses may help.",
    "general": "Sleep regularly, eat balanced meals and stay hydrated.",
    "urinary": "Drink plenty of water and do not hold in urine.",
    "head": "Rest in a quiet, dim room, drink water and take breaks from screens.",
}
GROUP = [("fever", ("fever", "chills", "shivering", "sweating")),
         ("head", ("headache", "dizziness", "vision", "balance", "behind_the_eyes")),
         ("respiratory", ("cough", "phlegm", "nose", "congestion", "sneez", "throat", "breath")),
         ("digestive", ("stomach", "abdominal", "nausea", "vomit", "diarr", "constipation", "acidity", "indigestion", "appetite", "belly")),
         ("skin", ("skin", "rash", "itch", "pimple", "blister", "peel", "blackhead", "spots")),
         ("urinary", ("urin", "micturition", "polyuria")),
         ("pain", ("pain", "ache", "stiff", "joint", "knee", "neck", "back"))]


def stem(token):
    for suf in ("ings", "ing", "ness", "ies", "ed", "es", "s"):
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)] + ("y" if suf == "ies" else "")
    return token


def tokenise(text):
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def _group(sid):
    for g, keys in GROUP:
        if any(k in sid for k in keys):
            return g
    return "general"


def _compiled_lexicon():
    """[(stemmed phrase tokens, symptom id)] longest first."""
    seen, out = set(), []
    for phrase, sid in lexicon():
        toks = tuple(stem(t) for t in tokenise(phrase))
        if toks and toks not in seen:
            seen.add(toks)
            out.append((toks, sid))
    out.sort(key=lambda x: -len(x[0]))
    return out


_LEX = None


def analyse(text):
    """Return the structured NLP analysis of one message (also reused by the Generation-Based bot)."""
    global _LEX
    if _LEX is None:
        _LEX = _compiled_lexicon()
    tokens = tokenise(text)
    stems = [stem(t) for t in tokens]
    used = [False] * len(stems)
    found, negated = {}, []
    for phrase, sid in _LEX:
        n = len(phrase)
        for i in range(len(stems) - n + 1):
            if any(used[i:i + n]) or tuple(stems[i:i + n]) != phrase:
                continue
            for j in range(i, i + n):
                used[j] = True
            window = tokens[max(0, i - 4):i]
            if any(w in NEGATORS for w in window):
                negated.append(sid)
                continue
            mods = set(tokens[max(0, i - 2):i])
            sev = "severe" if mods & SEVERE else "mild" if mods & MILD else None
            if sid not in found:
                found[sid] = {"id": sid, "name": humanise(sid), "modifier": sev, "weight": severity().get(sid)}
    dur = DURATION.search(" ".join(tokens))
    duration = None
    if dur:
        qty = dur.group(1)
        duration = {"value": int(qty) if qty.isdigit() else NUMBER_WORDS.get(qty, 1), "unit": dur.group(2), "text": dur.group(0)}
    temp = None
    for m in TEMPERATURE.finditer(str(text or "").lower()):
        v = float(m.group(1))
        if 35 <= v <= 43 or 95 <= v <= 110:
            temp = {"value": v, "unit": "C" if v < 50 else "F"}
            break
    body = sorted({b for b in BODY_PARTS if b in tokens})
    symptoms = sorted(found.values(), key=lambda s: (-(s["weight"] or 0), s["name"]))
    content = [t for t in tokens if t not in STOPWORDS]
    return {"tokens": tokens, "content_tokens": content, "symptoms": symptoms, "negated": sorted(set(negated)),
            "duration": duration, "temperature": temp, "body_parts": body}


class NlpBasedArchitecture(Architecture):
    key = "nlp_based"
    name = "NLP-Based"
    method = "Tokenisation, stemming, negation handling and entity extraction over the dataset symptom lexicon"

    def version(self):
        return "nlp-v1"

    def _answer(self, text, context):
        a = analyse(text)
        extracted = {k: a[k] for k in ("symptoms", "negated", "duration", "temperature", "body_parts")}
        evidence = [{"type": "entity", "symptom": s["name"], "severity_weight": s["weight"], "modifier": s["modifier"]}
                    for s in a["symptoms"]]
        if not a["symptoms"]:
            msg = "I could not identify a symptom in your message."
            if a["negated"]:
                msg += " I noted that you do NOT have: " + ", ".join(humanise(n) for n in a["negated"]) + "."
            return {"status": "no_match", "extracted": extracted, "evidence": evidence,
                    "response": join(msg, "Please describe what you are feeling (for example: 'I have had a cough and fever for 2 days').", DISCLAIMER)}
        names = [s["name"] + (f" ({s['modifier']})" if s["modifier"] else "") for s in a["symptoms"]]
        summary = "I identified these symptoms: " + ", ".join(names) + "."
        if a["negated"]:
            summary += " You said you do not have: " + ", ".join(humanise(n) for n in a["negated"]) + "."
        if a["duration"]:
            summary += f" Duration: {a['duration']['text']}."
        if a["temperature"]:
            summary += f" Temperature mentioned: {a['temperature']['value']:g} {a['temperature']['unit']}."
        groups = []
        for s in a["symptoms"]:
            g = _group(s["id"])
            if g not in groups:
                groups.append(g)
        care = [GUIDANCE[g] for g in groups][:4]
        review = [s["name"] for s in a["symptoms"] if s["id"] in PROMPT_REVIEW or s["modifier"] == "severe" or (s["weight"] or 0) >= 6]
        if a["temperature"] and ((a["temperature"]["unit"] == "C" and a["temperature"]["value"] >= 39.5)
                                 or (a["temperature"]["unit"] == "F" and a["temperature"]["value"] >= 103)):
            review.append("high temperature")
        parts = [summary, "General guidance:\n" + bullet(care)]
        if review:
            parts.append("These need a doctor's review soon: " + ", ".join(dict.fromkeys(review)) + ".")
        else:
            parts.append("See a doctor if the symptoms get worse, new symptoms appear, or they last more than a few days.")
        missing = []
        if not a["duration"] and not context.get("duration"):
            missing.append("how long you have had them")
        if not any(s["modifier"] for s in a["symptoms"]):
            missing.append("how severe they are")
        if missing:
            parts.append("To help further, tell me " + " and ".join(missing) + ".")
        parts.append(DISCLAIMER)
        return {"status": "ok", "response": join(*parts), "extracted": extracted, "evidence": evidence}
