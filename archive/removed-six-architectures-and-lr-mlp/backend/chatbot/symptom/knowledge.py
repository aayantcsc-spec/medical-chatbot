"""
knowledge.py - shared, read-only symptom/disease knowledge for the six symptom architectures.

Sources (all in datasets/, loaded lazily and once per process):
    Symptom-severity.csv        symptom vocabulary + severity weight (1-7)
    Disease_Description.csv     41 disease descriptions
    Disease precaution.csv      41 x 4 general precautions
    Symptom2Disease.csv         24 labelled patient-style descriptions (classifier training / evaluation)
    models/symptom/disease_profiles.json   built by build_profiles.py from the augmented matrix

The three disease files spell the same disease differently ("Peptic ulcer diseae", "peptic ulcer
disease", "GERD", "gastroesophageal reflux disease (gerd)" ...). DISEASE_ALIASES maps every known
spelling to ONE canonical id so retrieval, generation and evaluation agree on what a disease is.
Nothing here is a diagnosis rule; it is lookup data.
"""
import csv
import json
import os
import re
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "datasets")
PROFILE_FILE = os.path.join(BASE_DIR, "models", "symptom", "disease_profiles.json")

# canonical id -> (display name, aliases). Aliases are lower-case and matched on word boundaries.
DISEASE_ALIASES = {
    "psoriasis": ("Psoriasis", ["psoriasis"]),
    "varicose_veins": ("Varicose veins", ["varicose veins", "varicose vein"]),
    "typhoid": ("Typhoid", ["typhoid", "typhoid fever", "enteric fever"]),
    "chicken_pox": ("Chicken pox", ["chicken pox", "chickenpox", "varicella"]),
    "impetigo": ("Impetigo", ["impetigo"]),
    "dengue": ("Dengue", ["dengue", "dengue fever"]),
    "fungal_infection": ("Fungal infection", ["fungal infection", "fungal infection of the skin", "fungal infection of the hair", "ringworm"]),
    "common_cold": ("Common cold", ["common cold"]),
    "pneumonia": ("Pneumonia", ["pneumonia"]),
    "hemorrhoids": ("Hemorrhoids (piles)", ["dimorphic hemorrhoids", "dimorphic hemorrhoids(piles)", "dimorphic hemmorhoids(piles)",
                                            "hemorrhoids", "haemorrhoids", "piles"]),
    "arthritis": ("Arthritis", ["arthritis", "rheumatoid arthritis", "arthritis of the hip"]),
    "acne": ("Acne", ["acne"]),
    "bronchial_asthma": ("Bronchial asthma", ["bronchial asthma", "asthma"]),
    "hypertension": ("Hypertension (high blood pressure)", ["hypertension", "high blood pressure"]),
    "migraine": ("Migraine", ["migraine"]),
    "cervical_spondylosis": ("Cervical spondylosis", ["cervical spondylosis", "spondylosis"]),
    "jaundice": ("Jaundice", ["jaundice"]),
    "malaria": ("Malaria", ["malaria"]),
    "uti": ("Urinary tract infection", ["urinary tract infection", "uti"]),
    "allergy": ("Allergy", ["allergy", "allergies", "seasonal allergies (hay fever)", "hay fever"]),
    "gerd": ("GERD (acid reflux)", ["gerd", "gastroesophageal reflux disease", "gastroesophageal reflux disease (gerd)", "acid reflux"]),
    "drug_reaction": ("Drug reaction", ["drug reaction", "adverse drug reaction"]),
    "peptic_ulcer": ("Peptic ulcer disease", ["peptic ulcer disease", "peptic ulcer diseae", "peptic ulcer", "stomach ulcer"]),
    "diabetes": ("Diabetes", ["diabetes", "diabetes mellitus"]),
    "hypothyroidism": ("Hypothyroidism", ["hypothyroidism"]),
    "hyperthyroidism": ("Hyperthyroidism", ["hyperthyroidism"]),
    "chronic_cholestasis": ("Chronic cholestasis", ["chronic cholestasis", "cholestasis"]),
    "hepatitis_a": ("Hepatitis A", ["hepatitis a"]),
    "hepatitis_b": ("Hepatitis B", ["hepatitis b"]),
    "hepatitis_c": ("Hepatitis C", ["hepatitis c"]),
    "hepatitis_d": ("Hepatitis D", ["hepatitis d"]),
    "hepatitis_e": ("Hepatitis E", ["hepatitis e"]),
    "alcoholic_hepatitis": ("Alcoholic hepatitis", ["alcoholic hepatitis"]),
    "osteoarthritis": ("Osteoarthritis", ["osteoarthritis", "osteoarthristis"]),
    "vertigo": ("Positional vertigo (BPPV)", ["(vertigo) paroymsal positional vertigo", "paroxysmal positional vertigo",
                                              "benign paroxysmal positional vertical vertigo", "vertigo"]),
    "hypoglycemia": ("Hypoglycemia (low blood sugar)", ["hypoglycemia", "low blood sugar"]),
    "aids": ("HIV/AIDS", ["aids", "hiv"]),
    "paralysis": ("Paralysis (brain hemorrhage)", ["paralysis (brain hemorrhage)", "brain hemorrhage", "intracerebral hemorrhage"]),
    "heart_attack": ("Heart attack", ["heart attack", "myocardial infarction"]),
    "gastroenteritis": ("Gastroenteritis", ["gastroenteritis", "infectious gastroenteritis"]),
    "tuberculosis": ("Tuberculosis", ["tuberculosis", "tb"]),
}

# Everyday wording -> symptom vocabulary id (Symptom-severity.csv names, plus a few common extras).
# The id is what the rule/NLP/generation modules reason about.
SYMPTOM_SYNONYMS = {
    "high_fever": ["high fever", "high temperature", "very hot", "burning up", "fever of 103", "fever of 104"],
    "mild_fever": ["mild fever", "low grade fever", "slight fever", "low fever"],
    "fever": ["fever", "feverish", "temperature", "febrile"],
    "chills": ["chills", "chilly", "feel cold"],
    "shivering": ["shivering", "shiver", "shaking with cold"],
    "headache": ["headache", "head ache", "head hurts", "head is pounding", "head pain", "pain in my head"],
    "cough": ["cough", "coughing"],
    "phlegm": ["phlegm", "mucus", "sputum"],
    "runny_nose": ["runny nose", "running nose", "nose is running", "dripping nose"],
    "congestion": ["congestion", "blocked nose", "stuffy nose", "nasal congestion", "stuffed up"],
    "continuous_sneezing": ["sneezing", "sneeze", "keep sneezing"],
    "throat_irritation": ["sore throat", "throat irritation", "scratchy throat", "throat hurts", "throat pain"],
    "breathlessness": ["breathless", "breathlessness", "short of breath", "out of breath", "wheezing", "wheeze"],
    "chest_pain": ["chest pain", "pain in my chest", "chest hurts"],
    "fatigue": ["fatigue", "tired", "tiredness", "exhausted", "no energy", "worn out", "weak and tired"],
    "lethargy": ["lethargy", "lethargic", "sluggish"],
    "malaise": ["malaise", "unwell", "feel sick in general"],
    "nausea": ["nausea", "nauseous", "feel sick", "queasy", "want to throw up"],
    "vomiting": ["vomiting", "vomit", "throwing up", "threw up", "puking"],
    "diarrhoea": ["diarrhoea", "diarrhea", "loose motion", "loose motions", "loose stools", "watery stool"],
    "constipation": ["constipation", "constipated", "hard stools", "can't pass stool"],
    "stomach_pain": ["stomach pain", "stomach ache", "stomachache", "tummy ache", "stomach hurts"],
    "abdominal_pain": ["abdominal pain", "abdomen pain", "pain in my abdomen", "belly pain", "cramping in my belly"],
    "acidity": ["acidity", "heartburn", "acid reflux", "burning in my chest after eating", "sour taste"],
    "indigestion": ["indigestion", "bloating", "bloated", "gas"],
    "loss_of_appetite": ["loss of appetite", "no appetite", "not hungry", "don't feel like eating"],
    "joint_pain": ["joint pain", "joints hurt", "aching joints", "painful joints"],
    "swelling_joints": ["swollen joints", "joint swelling", "swelling in my joints"],
    "movement_stiffness": ["stiffness", "stiff joints", "stiff in the morning"],
    "knee_pain": ["knee pain", "knees hurt"],
    "back_pain": ["back pain", "backache", "lower back pain"],
    "neck_pain": ["neck pain", "neck hurts", "stiff neck"],
    "muscle_pain": ["muscle pain", "body ache", "body aches", "body pain", "aching muscles", "myalgia"],
    "itching": ["itching", "itchy", "itch"],
    "skin_rash": ["rash", "skin rash", "red spots", "red patches", "hives"],
    "skin_peeling": ["peeling", "skin peeling", "flaky skin", "scaly"],
    "blister": ["blister", "blisters", "fluid filled bumps"],
    "pus_filled_pimples": ["pimples", "pus filled pimples", "zits", "breakouts"],
    "blackheads": ["blackheads", "whiteheads"],
    "yellowish_skin": ["yellow skin", "yellowish skin", "skin turning yellow"],
    "yellowing_of_eyes": ["yellow eyes", "eyes turning yellow", "yellowing of eyes"],
    "dark_urine": ["dark urine", "dark coloured urine", "brown urine"],
    "burning_micturition": ["burning urination", "burning when i pee", "pain while urinating", "burning sensation when urinating", "painful urination"],
    "continuous_feel_of_urine": ["frequent urination", "urge to urinate", "need to pee often", "urinating often"],
    "foul_smell_ofurine": ["smelly urine", "foul smelling urine", "cloudy urine"],
    "polyuria": ["peeing a lot", "excessive urination", "polyuria"],
    "excessive_hunger": ["always hungry", "excessive hunger", "very hungry"],
    "weight_loss": ["weight loss", "losing weight", "lost weight"],
    "weight_gain": ["weight gain", "gaining weight", "put on weight"],
    "dizziness": ["dizzy", "dizziness", "light headed", "lightheaded", "spinning"],
    "loss_of_balance": ["loss of balance", "unsteady", "off balance"],
    "blurred_and_distorted_vision": ["blurred vision", "blurry vision", "vision is blurry"],
    "pain_behind_the_eyes": ["pain behind my eyes", "pain behind the eyes", "eye pain"],
    "redness_of_eyes": ["red eyes", "redness of eyes", "eyes are red"],
    "watering_from_eyes": ["watery eyes", "eyes watering", "teary eyes"],
    "sweating": ["sweating", "sweaty", "night sweats"],
    "dehydration": ["dehydrated", "dehydration", "very thirsty", "dry mouth"],
    "palpitations": ["palpitations", "heart racing", "heart pounding", "fast heartbeat"],
    "anxiety": ["anxious", "anxiety", "nervous", "worried all the time"],
    "swollen_legs": ["swollen legs", "leg swelling", "swollen ankles"],
    "prominent_veins_on_calf": ["bulging veins", "veins on my legs", "visible veins", "twisted veins"],
    "pain_in_anal_region": ["anal pain", "pain in my bottom", "pain around the anus"],
    "bloody_stool": ["blood in stool", "bloody stool", "blood when i poop"],
    "pain_during_bowel_movements": ["painful bowel movements", "pain when passing stool"],
    "red_spots_over_body": ["red spots all over", "spots all over my body"],
    "swelled_lymph_nodes": ["swollen glands", "swollen lymph nodes"],
    "irritability": ["irritable", "irritability"],
    "lack_of_concentration": ["can't concentrate", "lack of concentration", "brain fog"],
    "visual_disturbances": ["visual disturbances", "seeing flashes", "aura"],
}

# Symptoms that, alone, warrant prompt (not necessarily emergency) medical review.
PROMPT_REVIEW = {"high_fever", "chest_pain", "breathlessness", "bloody_stool", "yellowing_of_eyes",
                 "yellowish_skin", "blurred_and_distorted_vision", "palpitations", "weight_loss", "dark_urine"}

_lock = threading.RLock()     # re-entrant: loaders call canonical_disease(), which uses the cache too
_cache = {}


def norm(text):
    """Lower-case, keep letters/digits/apostrophes, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9'\s]", " ", str(text or "").lower())).strip()


def humanise(symptom_id):
    s = symptom_id.replace("_", " ").replace("feets", "feet").replace("ofurine", "of urine")
    return re.sub(r"\s+", " ", s).strip()


def _read_csv(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.isfile(path):
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _alias_index():
    idx = {}
    for cid, (_, aliases) in DISEASE_ALIASES.items():
        for a in aliases:
            idx[norm(a)] = cid
    return idx


def canonical_disease(name):
    """Any spelling from any of the datasets -> canonical id, or None if unknown."""
    if not name:
        return None
    n = norm(name)
    idx = _get("alias_index", _alias_index)
    if n in idx:
        return idx[n]
    n2 = norm(re.sub(r"\(.*?\)", " ", str(name)))
    return idx.get(n2)


def display_name(cid):
    return DISEASE_ALIASES.get(cid, (cid.replace("_", " ").capitalize(), []))[0]


def _get(key, builder):
    with _lock:
        if key not in _cache:
            _cache[key] = builder()
        return _cache[key]


def _load_diseases():
    """canonical id -> {id, name, description, precautions[]} for the 41 described diseases."""
    out = {}
    for r in _read_csv("Disease_Description.csv") or []:
        cid = canonical_disease(r.get("Disease"))
        if cid:
            out.setdefault(cid, {"id": cid, "name": display_name(cid), "description": "", "precautions": []})
            out[cid]["description"] = (r.get("Description") or "").strip()
    for r in _read_csv("Disease precaution.csv") or []:
        cid = canonical_disease(r.get("Disease"))
        if cid:
            rec = out.setdefault(cid, {"id": cid, "name": display_name(cid), "description": "", "precautions": []})
            rec["precautions"] = [p.strip() for k, p in sorted(r.items()) if k and k.startswith("Precaution") and p and p.strip()]
    return out


def diseases():
    return _get("diseases", _load_diseases)


def _load_severity():
    return {r["Symptom"].strip(): int(r["weight"]) for r in (_read_csv("Symptom-severity.csv") or [])
            if r.get("Symptom") and str(r.get("weight", "")).strip().isdigit()}


def severity():
    return _get("severity", _load_severity)


def _load_lexicon():
    """phrase -> symptom id. Dataset names first, then everyday synonyms (which win on conflicts)."""
    lex = {}
    for sid in severity():
        if sid in ("prognosis", "family_history", "extra_marital_contacts", "receiving_blood_transfusion",
                   "receiving_unsterile_injections", "history_of_alcohol_consumption"):
            continue
        lex[norm(humanise(sid))] = sid
    for sid, phrases in SYMPTOM_SYNONYMS.items():
        for p in phrases:
            lex[norm(p)] = sid
    # longest phrases first so "high fever" wins over "fever"
    return sorted(lex.items(), key=lambda kv: -len(kv[0]))


def lexicon():
    return _get("lexicon", _load_lexicon)


def _load_profiles():
    if not os.path.isfile(PROFILE_FILE):
        return {"meta": None, "profiles": {}}
    with open(PROFILE_FILE, encoding="utf-8") as f:
        return json.load(f)


def profiles():
    """{'meta':..., 'profiles': {disease_name: {'rows', 'symptoms': [[name, share], ...]}}}"""
    return _get("profiles", _load_profiles)


def load_symptom2disease():
    """[(text, canonical_label, raw_label)] from Symptom2Disease.csv. Raises if the file is missing."""
    rows = _read_csv("Symptom2Disease.csv")
    if rows is None:
        raise FileNotFoundError("datasets/Symptom2Disease.csv is missing")
    out = []
    for r in rows:
        text, raw = (r.get("text") or "").strip(), (r.get("label") or "").strip()
        if text and raw:
            out.append((text, canonical_disease(raw) or norm(raw).replace(" ", "_"), raw))
    return out


def mentioned_diseases(text):
    """Canonical ids of every disease named in a piece of text (word-boundary alias match)."""
    t = " " + norm(text) + " "
    found = set()
    for cid, (_, aliases) in DISEASE_ALIASES.items():
        for a in aliases:
            if f" {norm(a)} " in t:
                found.add(cid)
                break
    return found


def status():
    """What is loaded and what is missing - shown on the Dataset & Experiments page."""
    p = profiles()
    return {"diseases_described": len(diseases()), "symptom_vocabulary": len(severity()),
            "lexicon_phrases": len(lexicon()), "retrieval_profiles": len(p.get("profiles", {})),
            "retrieval_profiles_meta": p.get("meta"),
            "missing": [n for n in ("Disease_Description.csv", "Disease precaution.csv", "Symptom-severity.csv", "Symptom2Disease.csv")
                        if not os.path.isfile(os.path.join(DATA_DIR, n))]
                       + ([] if os.path.isfile(PROFILE_FILE) else ["models/symptom/disease_profiles.json (run: python -m chatbot.symptom.build_profiles)"])}
