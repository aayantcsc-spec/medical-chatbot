"""
safety.py - emergency detection that is SEPARATE from every model's scoring.

It looks only at the user's question, never at a model's prediction or confidence, so a wrong
or low-confidence model can never hide an emergency. It gives general first guidance only - no
diagnosis and no medicine doses.

assess(question) returns
    emergency   True when the wording describes a possible life-threatening situation
    mode        "emergency" | "informational" | None
                "informational" = a general education question about an emergency topic
                ("What are the warning signs of a stroke?") with no sign it is happening now.
                Self-harm wording is NEVER treated as informational.
    categories  names of the matched emergency classes
    notice      first message to show (emergency number / crisis support)
    guidance    short immediate-action lines for the matched classes

Emergency numbers: 112 = India's national emergency number. Tele-MANAS (Government of India,
free, 24x7 mental-health helpline): 14416 or 1800-891-4416 (checked against official/government
pages on 2026-10-24). Re-check before any public deployment.
"""
import re

_PATTERNS = {
    "chest pain / possible heart attack": r"chest (pain|pressure|tightness|feels? (very )?(tight|heavy))|heart attack|crushing pain|pain (spreading|radiating) (to|down) (my |the )?(left )?(arm|jaw)",
    "severe breathing difficulty": r"can('|no)?t (breathe|catch my breath)|cannot breathe|(severe|sudden|acute) (shortness of breath|difficulty breathing|breathlessness)|difficulty breathing|trouble breathing|struggling to breathe|"
                                   r"short(ness)? of breath|gasping|breathing (is )?(getting )?(very |so )?(hard|difficult)|lips (are )?(turning )?blue|not breathing",
    "possible stroke": r"stroke|face (is )?droop|mouth (is )?droop|drooping|slurred speech|sudden (weakness|numbness)|one side of (my|the|his|her) (body|face)|can'?t lift (his|her|my) arm",
    "loss of consciousness / seizure": r"unconscious|passed out|fainted|not responding|unresponsive|seizure|convulsion|having a fit|\bfits?\b",
    "severe bleeding": r"severe bleeding|heavy bleeding|bleeding (heavily|a lot|badly|won'?t stop|will not stop|that (won'?t|will not|does not|doesn'?t) stop)|vomiting blood|vomited blood|coughing (up )?blood",
    "poisoning / overdose": r"overdos|poison|(swallowed|ate|drank|drink|swallow) (some |a |the |an )?(bleach|pills?|tablets?|chemicals?|kerosene|phenyl|detergent|acid|pesticide|insecticide|rat poison|cleaning|battery|medicines?)|took too many (pills|tablets)",
    "choking / severe allergic reaction": r"choking|anaphyla|throat (is )?(closing|swelling)|(face|lips|tongue) (is |are )?swelling|swollen (lips|tongue|face) .*breath",
    "pregnancy emergency": r"(bleeding|fluid leaking|baby (is )?not moving).{0,25}(pregnan|baby)|pregnan\w*.{0,30}(heavy bleeding|severe pain|not moving)",
    "thoughts of self-harm": r"suicid|sucid|suicidal thoughts|kill(ing)? myself|hang myself|cut my wrists|jump off|want to die|end my life|ending my life|harm myself|hurt myself|self[- ]harm|don'?t want to (be alive|live)|no reason to live|better off dead|want to disappear forever|hurting myself|better off without me|have a plan to (end|die|kill)",
    "mental health crisis": r"hurt (someone|others|somebody)|harm (someone|others)|hearing voices (telling|that tell)|panic attack.{0,30}(dying|can'?t breathe)|losing control of my mind|mental breakdown|going crazy",
}
_COMPILED = {k: re.compile(v, re.I) for k, v in _PATTERNS.items()}

_GUIDANCE = {
    "chest pain / possible heart attack": "Stop what you are doing, sit down and stay as calm as you can. Do not drive yourself. Loosen tight clothing.",
    "severe breathing difficulty": "Sit upright, loosen tight clothing and try slow breaths. Do not lie flat. If the person has a prescribed inhaler or emergency medicine, use it as their doctor has instructed.",
    "possible stroke": "Note the time the symptoms started and tell the emergency team. Do not give food, drink or medicine by mouth. Keep the person safe and still.",
    "loss of consciousness / seizure": "Check if the person is breathing. If breathing normally, lay them on their side. If not breathing normally and you are trained, start CPR. During a seizure, protect the head and do not put anything in the mouth.",
    "severe bleeding": "Press firmly on the wound with a clean cloth or clothing and keep pressing. Do not remove soaked cloth - add more on top. Raise the injured limb if possible.",
    "poisoning / overdose": "Do not make the person vomit unless a medical professional tells you to. Keep the container or tablets to show the team, and stay with the person.",
    "choking / severe allergic reaction": "For choking: if the person cannot cough, speak or breathe, give back blows and abdominal thrusts if you are trained. For a severe allergic reaction: use an adrenaline auto-injector if one has been prescribed, and lie down with legs raised unless breathing is hard.",
    "pregnancy emergency": "Lie down on your left side and do not wait for symptoms to settle. Have someone take you to hospital or call for an ambulance.",
    "thoughts of self-harm": "",
    "mental health crisis": "Move to a safe place, keep away from anything that could cause harm and stay with someone you trust.",
}

EMERGENCY_NOTICE = ("This may be a medical emergency. Please call your local emergency number now "
                    "(112 in India; 108 for an ambulance in many states) or go to the nearest hospital. "
                    "Do not wait for an online answer.")
SELF_HARM_NOTICE = ("I am really sorry you are feeling this much pain, and I am glad you said it. You deserve support right now. "
                    "If you might act on these thoughts, please call 112 or go to the nearest emergency department. "
                    "You can also call Tele-MANAS, India's free 24x7 mental health helpline, on 14416 or 1800-891-4416, "
                    "and please tell someone you trust so you are not alone tonight.")
MENTAL_CRISIS_NOTICE = ("This sounds like a mental health emergency, and you deserve help right now. Please call 112 or go to the "
                        "nearest emergency department. Tele-MANAS (free, 24x7) is on 14416 or 1800-891-4416. "
                        "If you are with someone who is in crisis, stay with them and keep everyone safe.")

_PERSONAL = re.compile(r"\b(i|i'm|im|i've|my|me|we|he|she|they|his|her|their|someone|somebody|friend|father|mother|dad|mom|child|baby|son|daughter|husband|wife|grand\w+|patient)\b|right now|\bnow\b|please help|\bhelp\b", re.I)
_EDU = re.compile(r"^\s*(what (is|are)|what's|how (do|to|can) (you |i |we )?(recogni[sz]e|identify|spot|know)|tell me about|explain|define|signs of|symptoms of|warning signs|what causes|why (do|does|is))\b", re.I)


def _canonical(q):
    """English-canonical form of Hindi/Hinglish text so the English patterns also see it.
    Imported lazily; if the language layer ever fails, safety still runs on the raw text."""
    try:
        from chatbot.health_qa import language
        return language.canonicalise(q)
    except Exception:                                        # never let a language bug disable safety
        return ""


def assess(question):
    """Return {'emergency','mode','categories','notice','guidance'}.

    The patterns run on the raw text AND on its English-canonical form, so Hindi (Devanagari)
    and Hinglish emergencies are caught exactly like English ones. `notice`/`guidance` are the
    English texts; chat/comparison localise them via localized.py using `categories`."""
    q = str(question or "")
    canon = _canonical(q)
    texts = [q] + ([canon] if canon and canon != q.lower() else [])
    hits = []
    for name, rx in _COMPILED.items():
        if any(rx.search(t) for t in texts):
            hits.append(name)
    if not hits:
        return {"emergency": False, "mode": None, "categories": [], "notice": None, "guidance": []}
    mental = {"thoughts of self-harm", "mental health crisis"}
    joined = " ".join(texts)
    informational = (not (set(hits) & {"thoughts of self-harm"})
                     and any(_EDU.search(t) for t in texts) and not _PERSONAL.search(joined))
    if informational:
        return {"emergency": False, "mode": "informational", "categories": hits,
                "notice": None, "guidance": []}
    if "thoughts of self-harm" in hits:
        notice = SELF_HARM_NOTICE
    elif set(hits) <= mental:
        notice = MENTAL_CRISIS_NOTICE
    else:
        notice = EMERGENCY_NOTICE
    guidance = [_GUIDANCE[h] for h in hits if _GUIDANCE.get(h)]
    return {"emergency": True, "mode": "emergency", "categories": hits, "notice": notice, "guidance": guidance}
