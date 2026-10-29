"""
language.py - ONE shared language layer for Chat, Comparison, Evaluation and the safety module.

Why it exists
-------------
The three trained architectures (rule / TF-IDF+SVM / DistilBERT) were built and trained on
ENGLISH text. dataset.normalise() removes every character outside [a-z0-9], so Devanagari text
disappears completely and Roman-script Hindi ("bukhar") is an unknown word to all three.

What it does (preprocessing only - the three architectures are NOT changed)
---------------------------------------------------------------------------
  detect_language(text)  -> "en" | "hi" (Devanagari) | "hinglish" (Hindi in Roman letters)
  canonicalise(text)     -> English text with Hindi/Hinglish medical terms replaced by their
                            English equivalents, e.g. "Mere sir mein dard hai aur chakkar aa rahe
                            hain" -> "my headache and dizziness"
  extract_symptoms(text) -> canonical symptom names found (multi-symptom support)
  small_talk(text)       -> greeting / how-are-you / thanks / bye / identity / help, if the whole
                            message is only that
  analyse(text)          -> all of the above in one dict

Limits (stated honestly)
------------------------
* This is a curated lexicon plus fuzzy matching, not a translation model. It covers common
  symptoms, body areas, medicines, doctors and question words. Unknown Hindi words are dropped
  from the canonical text, never guessed.
* Meaning-bearing terms are replaced one-to-one (bukhar -> fever, chakkar -> dizziness). Words it
  does not know are left out rather than translated loosely.
* English input is returned essentially unchanged (only a few informal aliases such as "tummy
  ache" are expanded), so English behaviour is comparable with the original evaluation.
"""
import difflib
import re
import unicodedata

# ------------------------------------------------------------------ script / language detection
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_LATIN_WORD = re.compile(r"[a-z]+")

# Roman-script Hindi function words / medical words. STRONG ones almost never occur in English.
_STRONG = set("""mujhe mujhko mere mera meri hum humko hai hain hoon ho raha rahi rahe rahā kya karu karun kare karen
karna chahiye chahie nahi nahin nhi aur bahut thoda thodi zyada jyada hota hoti hote lagta lagti lagte lag
aata aati aate aa gaya gayi gaye kyun kyon kaise kab kitna kitni kaun kaunsa kaunse kis dikhana dikhao dikhau
dawai dawa dava goli bukhar bukhaar bukar dard dukh khansi khasi sir sar pet seene seena chakkar ulti dast
kabz zukam jukam kamzori thakan neend ghabrahat udaas udasi namaste namaskar shukriya dhanyavad dhanyawad
alvida kaisa kaise kaisi aap tum tumhe apka aapka batao bataiye batayiye samjhao samjhaiye madad
saans sans dil dhadkan aankh aankhon kaan gala gale dant daant peeth kamar ghutne jodon khujli kharish
daane chhati chhaati mahwari peeriod bachcha bachche bacche bachha garbh sugar madhumeh se ko ka ki ke
bhi toh abhi kuch koi kal aaj subah raat din baar tez halka halki sirf lekin ya""".split())
_WEAK = {"se", "ko", "ka", "ki", "ke", "ya", "bhi", "toh", "abhi", "kuch", "koi", "din", "aur", "ho", "aa", "lag",
         "sir", "sar", "dil", "tum", "aap", "tez", "raat", "kal", "aaj", "sugar", "baar", "subah", "halka"}
_STRONG -= _WEAK


def _alpha_count(text):
    return sum(ch.isalpha() for ch in text)


def detect_language(text):
    """Return {'lang','script','confidence','markers'}. lang: 'en' | 'hi' | 'hinglish'."""
    text = str(text or "")
    letters = _alpha_count(text)
    if letters == 0:
        return {"lang": "en", "script": "none", "confidence": 0.0, "markers": []}
    deva = len(_DEVANAGARI.findall(text))
    if deva / letters >= 0.25:
        return {"lang": "hi", "script": "devanagari", "confidence": round(min(1.0, deva / letters + 0.2), 2),
                "markers": []}
    rk = _rkey(text.lower())
    words = _LATIN_WORD.findall(rk)
    strong = [w for w in words if w in _STRONG_KEYS]
    weak = [w for w in words if w in _WEAK_KEYS]
    hits = _hindi_only_hits(rk)                      # lexicon phrases that are not English words
    if hits and not strong:
        strong = hits[:2] + hits[:1] * 0
    score = len(strong) + 0.4 * len(weak) + (0.6 * len(hits) if hits else 0)
    if (len(strong) >= 2) or (len(strong) >= 1 and score >= 1.4) or (len(strong) == 1 and len(words) <= 2):
        conf = min(0.99, 0.5 + 0.12 * score)
        return {"lang": "hinglish", "script": "latin", "confidence": round(conf, 2), "markers": sorted(set(strong))}
    return {"lang": "en", "script": "latin", "confidence": round(max(0.55, 0.95 - 0.2 * score), 2), "markers": []}


# ---------------------------------------------------------------------------------- romanisation key
def _rkey(s):
    """Collapse common Roman-Hindi spelling variation: bukhaar/bukhar, seene/sine, doctor/daktar."""
    s = str(s).lower()
    s = re.sub(r"aa+", "a", s)
    s = re.sub(r"(ee+|ii+)", "i", s)
    s = re.sub(r"(oo+|uu+)", "u", s)
    s = re.sub(r"([bcdfghjklmnpqrstvwxyz])\1+", r"\1", s)        # double consonant -> single
    return s


_STRONG_KEYS = {_rkey(w) for w in _STRONG}
_WEAK_KEYS = {_rkey(w) for w in _WEAK}

# ----------------------------------------------------------------------------------- lexicon
# (english, [variants]).  "~" in a variant = optional postposition (mein/me/ka/ki/ke) between words.
# Variants are matched after _rkey() on the Roman side, and on NFC-normalised Devanagari directly.
# Order matters: longer / more specific phrases first.
_LEX = [
    # --- emergency-bearing phrases first
    ("cannot breathe", ["saans nahi aa rahi", "saans nahi aa raha", "saans nahi le pa", "sans nahi aa", "saans ruk",
                        "dam ghut", "sans nahi le", "सांस नहीं आ", "साँस नहीं आ", "सांस नहीं ले", "साँस नहीं ले",
                        "सांस रुक", "साँस रुक", "दम घुट"]),
    ("difficulty breathing", ["saans ~ dikkat", "saans ~ takleef", "saans ~ problem", "saans ~ pareshani",
                              "saans ~ mushkil", "sans ~ dikkat", "sans ~ takleef", "saans lene ~ dikkat",
                              "सांस ~ दिक्कत", "सांस ~ तकलीफ", "सांस ~ परेशानी", "साँस ~ दिक्कत", "साँस ~ तकलीफ",
                              "साँस ~ परेशानी", "सांस लेने ~ दिक्कत", "सांस लेने ~ तकलीफ", "साँस लेने ~ तकलीफ",
                              "साँस लेने ~ दिक्कत", "सांस लेने ~ कठिनाई"]),
    ("shortness of breath", ["saans phul", "sans phul", "saans ~ phulna", "सांस फूल", "साँस फूल", "हांफ", "haanf",
                             "hafna"]),
    ("chest pain", ["seene ~ dard", "sine ~ dard", "seena dard", "chhati ~ dard", "chati ~ dard", "chhaati ~ dard",
                    "chest ~ dard", "seene ~ jalan", "seene ~ bhaari", "seene ~ bhari", "seene ~ dabav", "सीने ~ दर्द",
                    "छाती ~ दर्द", "सीने ~ जलन", "सीने ~ भारीपन", "सीने ~ दबाव", "सीने ~ जकड़न", "seene ~ jakdan"]),
    ("heart palpitations", ["dil ki dhadkan", "dhadkan tez", "dhadkan badh", "dil ~ dhadak", "दिल की धड़कन", "धड़कन तेज",
                            "धड़कन बढ़"]),
    ("face drooping and slurred speech", ["chehra tedha", "munh tedha", "chehra latak", "chehra lataka", "bolna ladkhada", "bolne mein ladkhada",
                                         "zubaan ladkhada", "jubaan ladkhada", "चेहरा टेढ़ा", "मुंह टेढ़ा", "चेहरा लटक", "जुबान लड़खड़ा",
                                         "ज़बान लड़खड़ा", "बोलने में लड़खड़ा", "बोल नहीं पा"]),
    ("heavy bleeding", ["bahut khoon", "zyada khoon", "jyada khoon", "khoon beh", "khoon aa raha", "बहुत खून", "ज्यादा खून", "खून बह", "खून आ रहा"]),
    ("took too many pills", ["bahut saari goli", "bahut sari goli", "zyada goliyan kha", "saari goliyan kha", "sari goliyan kha",
                             "बहुत सारी गोलियां", "ज्यादा गोलियां खा", "सारी गोलियां खा", "ढेर सारी गोलियां"]),
    ("unconscious", ["behosh", "bhosh ~ nahi", "होश नहीं", "बेहोश"]),
    ("bleeding that does not stop", ["khoon bahut beh", "khoon bahut bah", "khoon zyada beh", "खून बहुत बह", "खून ज्यादा बह", "khoon ruk nahi", "khoon band nahi", "khoon bah raha", "khun nahi ruk",
                                     "खून नहीं रुक", "खून बह रहा", "खून रुक नहीं"]),
    ("vomiting blood", ["khoon ki ulti", "ulti ~ khoon", "khun ki ulti", "खून की उल्टी", "उल्टी ~ खून"]),
    ("suicidal thoughts", ["marne ka man", "marne ki ichha", "marne ka khayal", "mar jaun", "mar jau", "mar jana", "mar jane", "jaan de du", "jaan de dun", "khatam kar du", "khatam kar lu", "suicide", "sucide", "मरने का मन", "मरने की इच्छा", "मरने का ख्याल", "मर जाऊं", "मर जाऊँ", "मर जाना", "मर जाने", "ख़तम कर दू", "खत्म कर दू", "जान दे दू", "jaan dene", "marna chahta", "marna chahti", "mar jana chahta", "mar jana chahti",
                           "khud ko khatam", "khudkushi", "atmahatya", "jeena nahi chahta", "jeena nahi chahti",
                           "jine ka mann nahi", "zindagi khatam", "zindagi se thak", "apni jaan", "aatmhatya",
                           "मरना चाहता", "मरना चाहती", "खुदकुशी", "आत्महत्या", "जान देना", "जान दे दू", "जीने का मन नहीं",
                           "जीना नहीं चाहता", "जीना नहीं चाहती", "ज़िंदगी खत्म", "जिंदगी खत्म", "खुद को खत्म",
                           "खुद को खतम"]),
    ("swallowed poison", ["zeher kha", "zehar kha", "jahar kha", "zeher pi", "jahar pi", "ज़हर खा", "जहर खा", "ज़हर पी",
                          "जहर पी"]),
    ("seizure", ["daura pada", "daura padta", "daura pade", "daura pad", "daura aa", "mirgi", "दौरा पड़", "दौरा आ", "मिर्गी"]),
    # --- symptoms
    ("fever", ["bukhar", "bukar", "bukhr", "tez bukhar", "bhukar", "bukhaar", "taap", "tapman badh", "badan garam",
               "बुखार", "बुख़ार", "ज्वर", "तापमान बढ़", "बदन गरम", "बदन गर्म", "तेज़ बुखार"]),
    ("headache", ["sir ~ dard", "sar ~ dard", "ser ~ dard", "sirdard", "sardard", "mathe ~ dard", "sir phat", "sir bhari",
                  "sir me bhaari", "सिर ~ दर्द", "सर ~ दर्द", "सिरदर्द", "सरदर्द", "माथे ~ दर्द", "सिर फट", "सिर भारी",
                  "सिर ~ भारीपन"]),
    ("dizziness", ["chakkar", "chakar", "chakkar aa", "sir ghoom", "sar ghoom", "ghoomta", "चक्कर", "सिर घूम", "सर घूम"]),
    ("stomach pain", ["pet ~ dard", "pet ~ marod", "pet ~ dukh", "petdard", "pet ~ jalan", "pet ~ aithan", "pet ~ kharab",
                      "पेट ~ दर्द", "पेट ~ मरोड़", "पेटदर्द", "पेट ~ जलन", "पेट ~ ऐंठन", "पेट ~ खराब", "पेट खराब"]),
    ("vomiting", ["ulti", "ultee", "ulti aa", "ulti ho", "ulti jaisa", "उल्टी", "उलटी", "वमन"]),
    ("nausea", ["ji michla", "jee michla", "mitli", "matli", "michli", "जी मिचल", "मतली", "मिचली"]),
    ("diarrhea", ["dast", "patle dast", "loose motion", "loose motions", "pait chal", "pet chal", "दस्त", "पतले दस्त",
                  "लूज मोशन", "पेट चल"]),
    ("constipation", ["kabz", "kabj", "pet saaf nahi", "पेट साफ नहीं", "कब्ज", "कब्ज़"]),
    ("acidity", ["acidity", "gas ~ problem", "gas ban", "gas ~ dikkat", "seene ~ jalan ~ khane", "khatti dakar",
                 "khatta dakar", "एसिडिटी", "गैस ~ समस्या", "गैस बन", "खट्टी डकार", "अपच", "apach"]),
    ("cough", ["khansi", "khasi", "khaansi", "khaasi", "khansi ho", "sookhi khansi", "balgam wali khansi", "खांसी", "खाँसी",
               "खासी", "सूखी खांसी", "बलगम"]),
    ("common cold", ["zukam", "jukam", "zukaam", "nazla", "naak behna", "naak beh", "naak band", "सर्दी जुकाम", "ज़ुकाम",
                     "जुकाम", "सर्दी", "नज़ला", "नजला", "नाक बह", "नाक बंद"]),
    ("sore throat", ["gale ~ dard", "gala dard", "gale ~ kharash", "gala kharab", "gale ~ kharab", "gale ~ jalan",
                     "गले ~ दर्द", "गला दर्द", "गले ~ खराश", "गला खराब", "गले ~ खराब", "गले ~ जलन"]),
    ("fatigue", ["thakan", "thakawat", "thakaan", "thaka thaka", "bahut thak", "थकान", "थकावट", "थका थका", "बहुत थक"]),
    ("weakness", ["kamzori", "kamjori", "kamzor", "weakness", "कमज़ोरी", "कमजोरी", "कमज़ोर", "कमजोर"]),
    ("insomnia", ["neend nahi", "neend ~ nahi aati", "neend kam", "neend ~ problem", "so nahi pa", "नींद नहीं", "नींद ~ समस्या",
                  "नींद कम", "अनिद्रा", "सो नहीं पा"]),
    ("anxiety", ["ghabrahat", "ghabrahat ho", "ghabra", "bechaini", "chinta", "tension ho", "घबराहट", "घबरा", "बेचैनी",
                 "चिंता", "चिन्ता"]),
    ("stress", ["tanav", "stress", "mansik tanav", "mental tension", "तनाव", "मानसिक तनाव"]),
    ("low mood", ["udas", "udasi", "udaas", "mann nahi lag", "man nahi lag", "dil nahi lag", "kuch accha nahi lag",
                  "depression", "उदास", "उदासी", "मन नहीं लग", "दिल नहीं लग", "अवसाद", "डिप्रेशन"]),
    ("toothache", ["dant ~ dard", "daant ~ dard", "dant dard", "daant dard", "दांत ~ दर्द", "दाँत ~ दर्द", "दर्द ~ दांत"]),
    ("gum problems", ["masude", "masuron", "masoode", "मसूड़े", "मसूड़ों"]),
    ("eye irritation", ["aankh ~ jalan", "aankhon ~ jalan", "ankh ~ jalan", "aankh ~ lal", "aankh ~ dard", "aankh ~ pani",
                        "आंख ~ जलन", "आँख ~ जलन", "आंखों ~ जलन", "आँखों ~ जलन", "आंख ~ लाल", "आँख ~ लाल", "आंख ~ दर्द",
                        "आँख ~ दर्द", "आंख ~ पानी", "आँख ~ पानी"]),
    ("blurred vision", ["dhundhla dikh", "dhundhla", "nazar kamzor", "nazar ~ dhundh", "धुंधला दिख", "धुंधला", "नज़र कमज़ोर",
                        "नजर कमजोर"]),
    ("ear pain", ["kaan ~ dard", "kan ~ dard", "kaan ~ bahna", "कान ~ दर्द", "कान ~ बहना"]),
    ("skin rash", ["daane", "dane", "chakatte", "chakte", "lal nishan", "rash", "kharish", "khujli", "khujlee", "khaj",
                   "दाने", "चकत्ते", "लाल निशान", "खुजली", "खुजलि", "खाज", "त्वचा ~ समस्या", "twacha ~ samasya",
                   "twacha", "त्वचा"]),
    ("joint pain", ["jodon ~ dard", "jodo ~ dard", "jod ~ dard", "ghutne ~ dard", "ghutno ~ dard", "ghutne",
                    "जोड़ों ~ दर्द", "जोड़ो ~ दर्द", "घुटने ~ दर्द", "घुटनों ~ दर्द", "गठिया", "gathiya"]),
    ("back pain", ["peeth ~ dard", "pith ~ dard", "kamar ~ dard", "kamar dard", "peth dard", "पीठ ~ दर्द", "कमर ~ दर्द",
                   "कमर दर्द"]),
    ("numbness", ["sunn", "sunnpan", "jhunjhuni", "jhanjhanahat", "सुन्न", "सुन्नपन", "झुनझुनी", "झनझनाहट"]),
    ("menstrual pain", ["period ~ dard", "periods ~ dard", "mahwari ~ dard", "masik ~ dard", "pet ~ period", "पीरियड ~ दर्द",
                        "पीरियड्स ~ दर्द", "माहवारी ~ दर्द", "मासिक ~ दर्द"]),
    ("periods", ["period", "periods", "mahwari", "mahavari", "masik dharm", "paridh", "पीरियड", "पीरियड्स", "माहवारी",
                 "मासिक धर्म", "मासिक"]),
    ("pregnant", ["garbhwati", "garbh", "pregnant", "pregnancy", "garbhavastha", "गर्भवती", "गर्भ", "गर्भावस्था",
                  "प्रेग्नेंट", "प्रेग्नेंसी"]),
    ("urinary burning", ["peshab ~ jalan", "pesab ~ jalan", "urine ~ jalan", "peshab ~ dard", "पेशाब ~ जलन", "पेशाब ~ दर्द",
                         "पेशाब में जलन"]),
    ("diabetes", ["madhumeh", "diabetes", "diabeties", "sugar ki bimari", "sugar badh", "sugar level", "blood sugar",
                  "शुगर", "मधुमेह", "डायबिटीज", "डायबिटीस", "शक्कर की बीमारी"]),
    ("blood pressure", ["blood pressure", "bp ", "bp high", "bp low", "raktchap", "raktachap", "ब्लड प्रेशर", "रक्तचाप", "बीपी"]),
    ("cholesterol", ["cholesterol", "kolesterol", "कोलेस्ट्रॉल", "कोलेस्ट्रोल"]),
    # --- people
    ("child", ["bachcha", "bachche", "bacche", "bachha", "baccha", "bache", "shishu", "baalak", "बच्चा", "बच्चे", "बच्चों",
               "बच्ची", "शिशु", "बालक"]),
    ("elderly", ["buzurg", "bujurg", "dadi", "dada", "nani", "nana", "बुज़ुर्ग", "बुजुर्ग", "दादी", "दादा", "नानी", "नाना"]),
    # --- medicine / care words
    ("medicine", ["dawai", "dawa", "davai", "dava", "goli", "tablet", "dawaiyan", "दवा", "दवाई", "दवाइयाँ", "दवाइयां", "गोली",
                  "टैबलेट"]),
    ("how many tablets should i take", ["kitni goli", "kitni dawai", "kitni tablet", "goli kitni", "dawai kitni", "dose kitni",
                                        "dose kitna", "kitni dose", "kitna dose", "कितनी गोली", "कितनी दवा", "कितनी दवाई",
                                        "कितनी टैबलेट", "मात्रा", "खुराक"]),
    ("doctor", ["doctor", "doktor", "daktar", "dactar", "chikitsak", "vaidya", "डॉक्टर", "डाक्टर", "चिकित्सक", "वैद्य"]),
    ("hospital", ["aspatal", "hospital", "haspatal", "अस्पताल"]),
    ("blood test", ["blood test", "khoon ki jaanch", "khoon ki janch", "report", "jaanch", "janch", "खून की जांच", "ब्लड टेस्ट",
                    "रिपोर्ट", "जांच"]),
    ("exercise", ["vyayam", "exercise", "kasrat", "व्यायाम", "कसरत"]),
    ("diet", ["khana", "aahar", "ahar", "diet", "khane", "खाना", "आहार", "खाने"]),
    ("sleep", ["neend", "sona", "नींद", "सोना"]),
    ("water", ["pani", "paani", "पानी"]),
    ("vaccine", ["teeka", "tika", "vaccine", "टीका", "टीकाकरण", "वैक्सीन"]),
    # --- question frames (kept short and meaning-preserving)
    ("which doctor should i see", ["kis doctor", "kaun se doctor", "kaunse doctor", "kaunsa doctor", "kon se doctor",
                                   "kon sa doctor", "kis specialist", "kaun sa specialist", "kis daktar", "kaun se daktar",
                                   "doctor ko kab dikha", "किस डॉक्टर", "कौन से डॉक्टर", "कौनसे डॉक्टर", "कौन सा डॉक्टर",
                                   "किसे दिखाऊ", "किसे दिखाना", "किसको दिखाना"]),
    ("when should i see a doctor", ["doctor ko kab dikha", "kab doctor", "doctor ke paas kab", "daktar ko kab",
                                    "डॉक्टर को कब दिखा", "कब डॉक्टर", "डॉक्टर के पास कब"]),
    ("what should i do", ["kya karu", "kya karun", "kya karoon", "kya kare", "kya karen", "kya karna chahiye", "kya karna hai",
                          "kya karna", "kya upay", "kya upaay", "kya ilaaj", "kya ilaj", "kuch upay", "क्या करूं", "क्या करूँ",
                          "क्या करें", "क्या करना चाहिए", "क्या करना है", "क्या उपाय", "क्या इलाज", "क्या करे"]),
    ("what is", ["kya hota hai", "kya hai", "kya hota", "क्या होता है", "क्या है"]),
    ("what are the causes", ["kya karan", "kya wajah", "kaaran kya", "karan kya", "wajah kya", "kya reason", "क्या कारण",
                             "क्या वजह", "कारण क्या", "वजह क्या", "क्यों हो"]),
    ("why", ["kyun", "kyon", "kyu", "क्यों", "क्यूं"]),
    ("how", ["kaise", "kese", "कैसे"]),
    ("when", ["kab", "कब"]),
    ("how long", ["kitne din", "kitne dino", "kitna samay", "कितने दिन", "कितने दिनों", "कितना समय"]),
    ("explain in simple words", ["aasan shabdo", "aasan bhasha", "saral shabdo", "saral bhasha", "simple mein samjha",
                                 "आसान शब्दों", "आसान भाषा", "सरल शब्दों", "सरल भाषा", "सरल में समझा"]),
    ("what next", ["aage kya", "ab kya", "iske baad kya", "आगे क्या", "अब क्या", "इसके बाद क्या"]),
    ("tell me more", ["aur batao", "aur bataiye", "aur jaankari", "aur jankari", "thoda aur", "और बताओ", "और बताइए",
                      "और जानकारी", "थोड़ा और"]),
    ("prevention", ["bachav", "roktham", "rokne ke", "bachne ke", "बचाव", "रोकथाम", "रोकने के", "बचने के"]),
    ("and", ["aur", "tatha", "और", "तथा"]),
    ("i have", ["mujhe", "mujhko", "mujhme", "mere ko", "मुझे", "मुझको", "मेरे को"]),
    ("my", ["mere", "mera", "meri", "मेरे", "मेरा", "मेरी"]),
    ("he has", ["use hai", "unhe hai", "usko", "unko", "उसे", "उसको", "उन्हें", "उनको"]),
    ("severe", ["bahut tez", "tez dard", "bahut zyada", "bahut jyada", "behad", "asahniya", "बहुत तेज़", "बहुत तेज", "तेज़ दर्द",
                "बहुत ज्यादा", "बहुत ज़्यादा", "बेहद", "असहनीय"]),
    ("sudden", ["achanak", "अचानक"]),
    ("persistent", ["lagatar", "baar baar", "kai din se", "kaafi din se", "bahut din se", "लगातार", "बार बार", "कई दिन से",
                    "काफी दिन से", "बहुत दिन से", "kaafi dino"]),
    ("pain", ["dard", "peeda", "दर्द", "पीड़ा"]),
]

# English informal aliases -> canonical English. Applied to every language (kept deliberately small).
_EN_ALIASES = [
    (r"\b(tummy|belly|stomach) ?(ache|hurts?|aching)\b", "stomach pain"),
    (r"\bhead ?ache\b|\bmy head (hurts?|is (hurting|pounding|killing me))\b", "headache"),
    (r"\b(running|have|having|got) a (high )?temperature\b", "fever"),
    (r"\b(feel(ing)?|am|i'm|im) (dizzy|light ?headed|giddy)\b|\bdizzy\b|\blight ?headed\b|\bvertigo\b", "dizziness"),
    (r"\b(throwing up|threw up|puking|vomit(ed|ing)? )\b", "vomiting"),
    (r"\bloose motions?\b|\bwatery stools?\b", "diarrhea"),
    (r"\bcan'?t sleep\b|\bnot able to sleep\b|\btrouble sleeping\b|\bunable to sleep\b", "insomnia"),
    (r"\bbreathless(ness)?\b|\bout of breath\b|\bhard to breathe\b|\bcan'?t breathe properly\b",
     "shortness of breath"),
    (r"\bsugar (problem|level|disease)\b", "diabetes"),
    (r"\bbp\b", "blood pressure"),
    (r"\bsir dard\b", "headache"),
]

_SEVERE_ADV = ["bahut", "bohot", "tez", "zyada", "jyada", "behad", "bhayankar", "तेज़", "तेज", "बहुत", "ज्यादा", "ज़्यादा", "बेहद", "भयंकर"]
_PERSIST_ADV = ["lagatar", "baar baar", "hamesha", "kai din se", "लगातार", "बार बार", "हमेशा"]
_OTHER_ADV = ["halka", "halki", "kaafi", "achanak", "thoda", "thodi", "हल्का", "हल्की", "काफी", "अचानक", "थोड़ा", "थोड़ी"]
_ADV_ALL = "|".join(re.escape(_rkey(a) if re.match(r"[a-z ]+$", a) else a) for a in _SEVERE_ADV + _PERSIST_ADV + _OTHER_ADV)
_POSTPOSITION = (r"(?:\s*(?:mein|me|main|mai|men|ka|ki|ke|ko|में|मे|का|की|के|को))?"
                 r"(?:\s+(?:" + _ADV_ALL + r")){0,2}")


def _adverb_prefix(matched):
    m = matched.lower()
    k = _rkey(m)
    if any((a in m or a in k) for a in [_rkey(x) if re.match(r"[a-z ]+$", x) else x for x in _SEVERE_ADV]):
        return "severe "
    if any((a in m or a in k) for a in [_rkey(x) if re.match(r"[a-z ]+$", x) else x for x in _PERSIST_ADV]):
        return "persistent "
    return ""


def _nfc(text):
    text = unicodedata.normalize("NFC", str(text or ""))
    # fold nukta forms and chandrabindu so क़/ख़/ग़/ज़/ड़/ढ़/फ़ and ँ/ं variants all match
    for a, b in (("क़", "क"), ("ख़", "ख"), ("ग़", "ग"), ("ज़", "ज"), ("ड़", "ड"), ("ढ़", "ढ"), ("फ़", "फ"), ("ऩ", "न"),
                 ("ँ", "ं"), ("\u093c", "")):
        text = text.replace(a, b)
    return text


def _compile_variant(variant):
    is_deva = bool(_DEVANAGARI.search(variant))
    v = _nfc(variant) if is_deva else _rkey(variant)
    parts = [p for p in v.split() if p]
    out = []
    for p in parts:
        out.append(_POSTPOSITION if p == "~" else re.escape(p))
    pat = r"\s*".join(x for x in out)
    pat = pat.replace(r"\s*" + _POSTPOSITION, _POSTPOSITION).replace(_POSTPOSITION + r"\s*", _POSTPOSITION + r"\s*")
    if is_deva:
        # Devanagari has no \b; require no Devanagari letter directly before the match
        return re.compile(r"(?<![\u0900-\u097F])" + pat), True
    return re.compile(r"(?<![a-z])" + pat + r"(?![a-z])"), False


_COMPILED = []     # (regex, is_deva, english, variant_length)
for _en, _vars in _LEX:
    for _v in _vars:
        _rx, _dv = _compile_variant(_v)
        _COMPILED.append((_rx, _dv, _en, len(_v)))
# longer variants first so "seene mein dard" is matched before "dard"
_COMPILED.sort(key=lambda t: -t[3])

def _english_vocab():
    """Every word that appears in the English knowledge base (so 'doctor', 'rash', 'period' are English)."""
    words = set()
    try:
        from chatbot.health_qa.knowledge import TOPICS
        for t in TOPICS:
            for field in ("short", "details", "advice", "doctor"):
                words.update(re.findall(r"[a-z]+", str(t.get(field, "")).lower()))
            for q in t.get("questions", []):
                words.update(re.findall(r"[a-z]+", str(q).lower()))
            for k in t.get("keywords", []):
                words.update(re.findall(r"[a-z]+", str(k).lower()))
    except Exception:
        pass
    return words | {_rkey(w) for w in words}


_EN_VOCAB = _english_vocab()
_HI_ONLY = []          # compiled Roman variants containing at least one word that is not English
for _en, _vars in _LEX:
    for _v in _vars:
        if _DEVANAGARI.search(_v):
            continue
        _ws = [w for w in _rkey(_v).split() if w != "~"]
        if _ws and any(w not in _EN_VOCAB for w in _ws):
            _HI_ONLY.append((_compile_variant(_v)[0], _v))


def _hindi_only_hits(rkey_text):
    return [v for rx, v in _HI_ONLY if rx.search(rkey_text)]


# words that only add noise once the meaning words have been replaced
_HI_FILLER = set(_rkey(w) for w in """hai hain hoon ho raha rahi rahe hota hoti hote hua hui hue tha thi the gaya gayi gaye
ka ki ke ko se mein me main mai men par pe toh to bhi hi na nahi nahin nhi ye yeh woh wo is us un in kuch koi
liye lie wala wali wale jo jab tab abhi phir bas zara zyada jyada thoda thodi sa si se aa aata aati aate lag lagta
lagti lagte ho rahe kar kara karta karti karte kiya kijiye kijie please plz pls ji sahab sir_ madam
batao bataiye batayiye bata do dijiye dijie dikhana dikhao dikhau dikhaun dikha chahiye chahie rehta rehti rehte rahta rahti rahte raha""".split())
_HI_FILLER -= {_rkey("hi")}           # "hi" is a greeting in English


def canonicalise(text):
    """Return English-canonical text. English input is only lightly touched."""
    original = str(text or "")
    lang = detect_language(original)["lang"]
    if lang == "en":
        out = original.lower()
        for rx, rep in _EN_ALIASES:
            out = re.sub(rx, rep, out)
        return re.sub(r"\s+", " ", out).strip()

    if lang == "hi":
        work = _nfc(original).lower()
        # transliterated English words written in Devanagari are handled by the lexicon; latin parts stay
    else:
        work = _rkey(original.lower())
    work = re.sub(r"[?!.,;:\"“”‘’()\[\]{}|।/\\]", " ", work)

    # replace longest variants first, marking replacements so they are not re-matched
    marks = []

    def stash(en):
        marks.append(en)
        return f" \u0001{len(marks) - 1}\u0002 "

    for rx, is_deva, en, _ in _COMPILED:
        work = rx.sub(lambda m, en=en: stash(_adverb_prefix(m.group(0)) + en if en.endswith(("pain", "ache", "burning")) else en), work)

    pieces = []
    for tok in work.split():
        m = re.fullmatch(r"\u0001(\d+)\u0002", tok)
        if m:
            pieces.append(marks[int(m.group(1))])
        elif _DEVANAGARI.search(tok):
            continue                                   # unknown Devanagari word: dropped, never guessed
        else:
            plain = re.sub(r"[^a-z0-9'\-]", "", tok)
            if not plain:
                continue
            if plain in _HI_FILLER or _rkey(plain) in _HI_FILLER:
                continue
            fuzzy = _fuzzy_hindi_word(plain) if lang == "hinglish" else None
            pieces.append(fuzzy or plain)
    out = " ".join(pieces)
    out = re.sub(r"\bi have my\b", "my", out)
    out = re.sub(r"\bmy (fever|headache|cough|dizziness|stomach pain|chest pain|back pain|joint pain)\b", r"i have \1", out)
    out = re.sub(r"\b(\w+(?: \w+)?) and and\b", r"\1 and", out)
    for rx, rep in _EN_ALIASES:
        out = re.sub(rx, rep, out)
    return re.sub(r"\s+", " ", out).strip()


_FUZZY_VOCAB = {}
for _en, _vars in _LEX:
    for _v in _vars:
        _words = _v.split()
        if len(_words) == 1 and not _DEVANAGARI.search(_v) and len(_v) >= 5:     # single-word variants only
            _FUZZY_VOCAB[_rkey(_v)] = _en
_ENGLISH_COMMON = set("""please about which should would could their there these those where other still after before
cough fever pain doctor sleep which water blood""".split())


def _fuzzy_hindi_word(word):
    """Single-word typo repair for Roman Hindi (e.g. 'bukhaarr' -> fever). Conservative cutoff."""
    if len(word) < 5 or word in _ENGLISH_COMMON or word in _FUZZY_VOCAB:
        return _FUZZY_VOCAB.get(word)
    m = difflib.get_close_matches(word, list(_FUZZY_VOCAB), n=1, cutoff=0.86)
    return _FUZZY_VOCAB[m[0]] if m else None


# --------------------------------------------------------------------------- symptom extraction
_SYMPTOMS = {
    "fever": r"\bfever|feverish|high temperature|chills\b",
    "headache": r"\bheadache|migraine|head pain\b",
    "dizziness": r"\bdizz\w*|light ?headed|vertigo|giddy\b",
    "cough": r"\bcough\w*\b",
    "stomach pain": r"\bstomach (pain|ache)|abdominal pain|belly pain|tummy\b",
    "vomiting": r"\bvomit\w*|throwing up\b",
    "nausea": r"\bnausea|nauseous|feel sick\b",
    "diarrhea": r"\bdiarrh?oea|diarrhea|loose motions?\b",
    "constipation": r"\bconstipat\w*\b",
    "chest pain": r"\bchest (pain|pressure|tightness)\b",
    "shortness of breath": r"\bshort(ness)? of breath|difficulty breathing|cannot breathe|breathless\w*|trouble breathing\b",
    "sore throat": r"\bsore throat|throat pain\b",
    "common cold": r"\bcommon cold|runny nose|blocked nose|\bcold\b",
    "fatigue": r"\bfatigue|tired(ness)?|exhaust\w*\b",
    "weakness": r"\bweak(ness)?\b",
    "insomnia": r"\binsomnia|cannot sleep|trouble sleeping\b",
    "anxiety": r"\banxi\w+|panic\b",
    "stress": r"\bstress\w*\b",
    "low mood": r"\blow mood|sad(ness)?|depress\w*\b",
    "toothache": r"\btoothache|tooth pain|dental pain\b",
    "eye irritation": r"\beye (pain|irritation|redness|burning)|red eyes?\b",
    "blurred vision": r"\bblurr?ed vision|blurry\b",
    "ear pain": r"\bear ?(ache|pain)\b",
    "skin rash": r"\brash|itch\w*|hives\b",
    "joint pain": r"\bjoint pain|knee pain|arthritis\b",
    "back pain": r"\bback pain\b",
    "numbness": r"\bnumb\w*|tingling\b",
    "menstrual pain": r"\bperiod (pain|cramps?)|menstrual (pain|cramps?)\b",
    "urinary burning": r"\bburning (urination|while urinating)|urinary burning|burning urine\b",
    "heart palpitations": r"\bpalpitation\w*|heart (racing|pounding)\b",
}
_SYMPTOM_RX = {k: re.compile(v, re.I) for k, v in _SYMPTOMS.items()}

# symptom -> knowledge-base topic id (used to give each symptom of a multi-symptom question its own guidance)
SYMPTOM_TOPIC = {
    "fever": "fever", "headache": "headache", "dizziness": "dizziness", "cough": "cough",
    "stomach pain": "indigestion", "vomiting": "food_poisoning", "nausea": "indigestion", "diarrhea": "food_poisoning",
    "constipation": "indigestion", "chest pain": "chest_pain_emergency", "shortness of breath": "breathing_difficulty",
    "sore throat": "sore_throat", "common cold": "common_cold", "fatigue": "fatigue", "weakness": "fatigue",
    "insomnia": "insomnia", "anxiety": "anxiety_signs", "stress": "stress_signs", "low mood": "low_mood_support",
    "toothache": "toothache", "eye irritation": "eye_irritation", "blurred vision": "eye_strain", "ear pain": None,
    "skin rash": "skin_rash", "joint pain": "joint_pain", "back pain": "back_pain", "numbness": "numbness_tingling",
    "menstrual pain": "menstrual_cramps", "urinary burning": "uti", "heart palpitations": "heart_warning_signs",
}


def extract_symptoms(canonical_text):
    text = str(canonical_text or "").lower()
    found = [name for name, rx in _SYMPTOM_RX.items() if rx.search(text)]
    # "stomach pain" subsumes a bare "pain"; "cannot breathe" etc. already map to shortness of breath
    return found


# ---------------------------------------------------------------------------------- small talk
_PUNCT = re.compile(r"[^\w\u0900-\u097F\s']")


def _plain(text):
    t = _PUNCT.sub(" ", _nfc(text).lower())
    t = re.sub(r"\b(please|plz|pls|ji|sir|madam|medichat|bot|dear|bhai|dost|friend)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_SMALL = [
    ("greeting", r"(hi+|hey+|hello+|hii+|helo|hola|namaste|namaskar|namaskaar|good (morning|afternoon|evening|day)|"
                 r"gm|नमस्ते|नमस्कार|हेलो|हैलो|हाय|सुप्रभात|शुभ (प्रभात|संध्या)|pranam|pranaam|प्रणाम|sat sri akal|jai (shri|shree) (krishna|ram)|"
                 r"hi there|hello there|hey there)( (there|everyone|team|all|ji))?"),
    ("how_are_you", r"(hi |hello |hey |namaste )?(how are you( doing)?|how r u|how are u|how do you do|what'?s up|wassup|sup|how is it going|"
                    r"kaise ho|kaise hain|kese ho|aap kaise (ho|hain)|tum kaise ho|kaisa hai|kya haal hai|kaisi ho|"
                    r"आप कैसे हैं|कैसे हो|कैसे हैं|क्या हाल है|आप कैसी हैं)( aap)?( hain| ho)?"),
    ("thanks", r"(thanks?( a lot| so much| a ton)?|thank you( so much| very much| a lot)?|thankyou|thx|ty|tysm|much appreciated|"
               r"shukriya|shukria|shukriyaa|dhanyavad|dhanyawad|dhanyabad|bahut (shukriya|dhanyavad)|"
               r"धन्यवाद|शुक्रिया|बहुत धन्यवाद|आभार|thanks (a lot|bro))( (you|ji|doctor))?"),
    ("bye", r"(bye+( bye)?|goodbye|good bye|see you( later| soon)?|see ya|take care|ttyl|talk to you later|alvida|phir milte hain|"
            r"phir milenge|chalta hu|chalti hu|tata|ok bye|okay bye|good night|gn|अलविदा|फिर मिलेंगे|चलता हूं|चलती हूं|टाटा|"
            r"गुड नाइट|शुभ रात्रि|खुदा हाफिज़|bye bye)"),
    ("identity", r"(who are you|what are you|what is your name|your name|tum kaun ho|aap kaun ho|aap kaun hain|tumhara naam kya hai|"
                 r"aapka naam kya hai|apka naam kya hai|are you (a )?(bot|human|robot|doctor|ai)|are you real|"
                 r"तुम कौन हो|आप कौन हैं|आप कौन हो|आपका नाम क्या है|तुम्हारा नाम क्या है)"),
    ("help", r"(help|help me|what can you do|how can you help( me)?|how do you work|kya kar sakte ho|kya kar sakti ho|"
             r"aap kya kar sakte hain|aap meri kaise madad|madad karo|madad chahiye|meri madad karo|मदद करो|मदद चाहिए|आप क्या कर सकते हैं|"
             r"आप मेरी कैसे मदद|तुम क्या कर सकते हो)"),
    ("ack", r"(ok|okay|k|fine|great|nice|cool|good|got it|understood|i see|alright|theek hai|thik hai|accha|achha|acha|samajh gaya|"
            r"samajh gayi|ठीक है|अच्छा|समझ गया|समझ गई|बढ़िया)( (ok|thanks|ji))?"),
]
_SMALL_RX = [(k, re.compile(r"^(?:" + v + r")$")) for k, v in _SMALL]
_GREETING_PREFIX = re.compile(r"^(?:" + _SMALL[0][1] + r")(?![A-Za-z\u0900-\u097F])[\s,!.]*", re.I)


def small_talk(text):
    """Return kind if the WHOLE message is small talk, else None."""
    plain = _plain(text)
    if not plain or len(plain) > 60:
        return None
    plain_k = _rkey(plain) if not _DEVANAGARI.search(plain) else plain
    for kind, rx in _SMALL_RX:
        if rx.match(plain) or rx.match(plain_k):
            return kind
    # "hi, how are you" / "hello thanks" - two small-talk parts in one message
    parts = [p for p in re.split(r"[,.!?]| and | aur ", plain) if p.strip()]
    if 1 < len(parts) <= 3:
        kinds = []
        for p in parts:
            p = p.strip()
            hit = next((k for k, rx in _SMALL_RX if rx.match(p) or rx.match(_rkey(p))), None)
            if not hit:
                return None
            kinds.append(hit)
        order = ["how_are_you", "thanks", "bye", "identity", "help", "greeting", "ack"]
        return sorted(kinds, key=order.index)[0]
    return None


def strip_greeting(text):
    """'Hello, I have a fever' -> 'I have a fever' (so a greeting never blocks a health question)."""
    return _GREETING_PREFIX.sub("", _plain_keep_case(text), count=1).strip() or str(text or "").strip()


def _plain_keep_case(text):
    return str(text or "").strip()


# ---------------------------------------------------------------------- question-kind detection
_DOCTOR_Q = re.compile(r"\b(which|what|whom|who|kon|kaun|kis)\b.{0,30}\b(doctor|specialist|physician|department|dept)\b|"
                       r"\b(should i|can i|do i need to|need to|to) (see|visit|consult|meet|go to)\b.{0,25}\b(doctor|specialist)\b|"
                       r"\bwhich doctor\b|\bwho treats\b|\bdoctor should\b|\bconsult\b.{0,20}\bdoctor|\bspecialist\b", re.I)
_DEFINE_Q = re.compile(r"^\s*(what is|what are|what's|define|explain|tell me about|meaning of|what does .* mean)\b", re.I)
_WHEN_DOC_Q = re.compile(r"\bwhen (should|do|must) (i|we|someone|a person|you)\b.{0,40}\b(see|visit|consult|contact|seek|call)\b|"
                         r"\bwhen to (see|visit|consult|seek)\b", re.I)
_MED_Q = re.compile(r"\b(medicine|medication|tablet|pill|dose|dosage|paracetamol|ibuprofen|antibiotic|crocin|syrup|drug)\b", re.I)
_TEST_Q = re.compile(r"\b(blood test|test|report|cbc|hba1c|lipid|thyroid profile|x-?ray|mri|ct scan|scan|ecg|urine test)\b", re.I)
_PREVENT_Q = re.compile(r"\b(prevent|prevention|avoid|reduce (the )?risk|protect|stay healthy|vaccin\w*)\b", re.I)
_LIFESTYLE_Q = re.compile(r"\b(diet|exercise|workout|sleep|nutrition|weight|lifestyle|healthy habits?|eat|yoga|walking|hydrat\w*)\b", re.I)
_SYMPTOM_STATEMENT = re.compile(r"\b(i have|i am having|i'?ve got|i feel|i am feeling|i'm feeling|my|having|suffering|since|"
                                r"for the (last|past)|from yesterday|started)\b", re.I)
_FOLLOWUP = re.compile(r"^\s*(and |but |also |what about |how about |ok(ay)? (and|but|so) )?(why( is that| does that happen)?|"
                       r"what (should|can|do) i do( now| next)?|what next|what now|is it (serious|dangerous|normal|safe)|"
                       r"how long (will|does) (it|this) (last|take)|can you explain( more| again| simpler)?|explain (more|again|simpler|in simple words)|"
                       r"tell me more|more (details|information)|simpler|in simple words|what else|should i (worry|be worried)|"
                       r"is that (serious|normal|dangerous)|when (should|do) i (see|call|go)( a doctor)?|which doctor|"
                       r"what (causes|caused) (it|this|that)|how (can|do) i (treat|prevent|avoid|fix) (it|this|that)|"
                       r"does (it|this) (go away|spread)|will it go away|any (other )?(tips|advice|remedies)|what about (food|diet|medicine|medicines|exercise))\??\s*$", re.I)


def question_kind(canonical_text):
    t = str(canonical_text or "")
    if _DOCTOR_Q.search(t):
        return "doctor"
    if _MED_Q.search(t):
        return "medication"
    if _TEST_Q.search(t):
        return "test"
    if _WHEN_DOC_Q.search(t):
        return "when_to_seek"
    if _DEFINE_Q.search(t):
        return "definition"
    if _PREVENT_Q.search(t):
        return "prevention"
    if _SYMPTOM_STATEMENT.search(t):
        return "symptom"
    if _LIFESTYLE_Q.search(t):
        return "lifestyle"
    return "general"


def is_followup(canonical_text):
    return bool(_FOLLOWUP.match(str(canonical_text or "").strip()))


def analyse(text):
    """Everything the pipelines / chat need to know about one raw message."""
    raw = str(text or "")
    lang = detect_language(raw)
    canon = canonicalise(raw)
    kind = small_talk(raw)
    body = canon if kind is None else ""
    # a greeting in front of a real question must not hide the question
    if kind is None:
        stripped = strip_greeting(raw)
        if stripped and stripped != raw.strip():
            canon = canonicalise(stripped)
            body = canon
    syms = extract_symptoms(canon)
    return {"lang": lang["lang"], "script": lang["script"], "lang_confidence": lang["confidence"],
            "markers": lang["markers"], "canonical": canon, "symptoms": syms,
            "small_talk": kind, "question_kind": question_kind(body) if body else None,
            "followup": is_followup(body)}
