"""
rules.py

Health rules used by the Rule-Based Health Chatbot.

This file contains:
- symptom keywords
- general health information
- follow-up questions
- safety rules
- emergency keywords

The chatbot provides general information only.
It does NOT diagnose diseases or prescribe medication.
"""


# =========================================================
# GREETING RULES
# =========================================================

GREETING_RULES = {

    "hello": [
        "Hello! How can I help you with your health concern?"
    ],

    "hi": [
        "Hi! Please tell me about your symptoms or health question."
    ],

    "hey": [
        "Hey! How are you feeling today?"
    ],

    "good morning": [
        "Good morning! How can I help you today?"
    ],

    "good afternoon": [
        "Good afternoon! Please tell me your health concern."
    ],

    "good evening": [
        "Good evening! How can I help you today?"
    ]
}


# =========================================================
# SYMPTOM KEYWORDS
# =========================================================

SYMPTOM_KEYWORDS = {

    "fever": [
        "fever",
        "high temperature",
        "temperature"
    ],

    "headache": [
        "headache",
        "head pain",
        "pain in my head"
    ],

    "cough": [
        "cough",
        "coughing"
    ],

    "cold": [
        "cold",
        "common cold"
    ],

    "sore_throat": [
        "sore throat",
        "throat pain",
        "painful throat"
    ],

    "runny_nose": [
        "runny nose",
        "running nose"
    ],

    "blocked_nose": [
        "blocked nose",
        "stuffy nose",
        "nasal congestion"
    ],

    "stomach_pain": [
        "stomach pain",
        "stomach ache",
        "abdominal pain",
        "pain in stomach"
    ],

    "chest_pain": [
        "chest pain",
        "pain in chest"
    ],

    "back_pain": [
        "back pain",
        "pain in back"
    ],

    "body_pain": [
        "body pain",
        "body ache",
        "body aches"
    ],

    "fatigue": [
        "fatigue",
        "tired",
        "tiredness",
        "very tired",
        "lack of energy"
    ],

    "weakness": [
        "weakness",
        "feeling weak",
        "weak"
    ],

    "nausea": [
        "nausea",
        "feeling nauseous",
        "feel nauseous"
    ],

    "vomiting": [
        "vomiting",
        "throwing up",
        "vomit"
    ],

    "diarrhea": [
        "diarrhea",
        "loose motion",
        "loose motions"
    ],

    "dizziness": [
        "dizziness",
        "dizzy",
        "feeling dizzy"
    ],

    "rash": [
        "rash",
        "skin rash"
    ],

    "itching": [
        "itching",
        "itchy",
        "skin itching"
    ],

    "shortness_of_breath": [
        "shortness of breath",
        "breathing problem",
        "difficulty breathing",
        "hard to breathe",
        "cannot breathe",
        "can't breathe"
    ]
}


# =========================================================
# GENERAL HEALTH RESPONSES
# =========================================================

HEALTH_RESPONSES = {

    "fever": (
        "Fever is an increase in body temperature that can occur "
        "with infections and other conditions. Rest, staying "
        "hydrated, and monitoring your symptoms can be helpful. "
        "If the fever is very high, persistent, or accompanied "
        "by serious symptoms, consult a healthcare professional."
    ),

    "headache": (
        "Headaches can have many causes, including stress, "
        "dehydration, lack of sleep, or illness. Try to rest "
        "and stay hydrated. If the headache is sudden, extremely "
        "severe, persistent, or accompanied by other serious "
        "symptoms, seek medical attention."
    ),

    "cough": (
        "A cough can occur with conditions such as a cold, "
        "respiratory infection, allergies, or irritation. "
        "Pay attention to how long it lasts and whether you "
        "have fever, breathing difficulty, or chest pain."
    ),

    "cold": (
        "A common cold can cause symptoms such as a runny nose, "
        "sore throat, cough, and congestion. Rest and adequate "
        "fluid intake may help. If symptoms become severe or "
        "persistent, consult a healthcare professional."
    ),

    "sore_throat": (
        "A sore throat can occur with a cold, viral infection, "
        "or other conditions. Warm fluids and adequate hydration "
        "may provide comfort. If you have severe difficulty "
        "swallowing or breathing, seek medical attention."
    ),

    "runny_nose": (
        "A runny nose can occur because of a cold, allergies, "
        "or irritation. Monitor your other symptoms and stay "
        "hydrated. If symptoms persist or become severe, "
        "consider speaking with a healthcare professional."
    ),

    "blocked_nose": (
        "A blocked nose can happen with colds, allergies, or "
        "sinus-related problems. Rest and adequate hydration "
        "may help. Persistent or severe symptoms should be "
        "discussed with a healthcare professional."
    ),

    "stomach_pain": (
        "Stomach or abdominal pain can have many possible causes. "
        "The location, duration, and severity of the pain are "
        "important. If the pain is severe, sudden, persistent, "
        "or associated with serious symptoms, seek medical care."
    ),

    "chest_pain": (
        "Chest pain can have many causes, including some that "
        "require urgent medical attention. If the pain is severe "
        "or occurs with breathing difficulty, sweating, fainting, "
        "or pain spreading to other areas, seek emergency medical "
        "attention immediately."
    ),

    "back_pain": (
        "Back pain can result from muscle strain, posture, injury, "
        "or other conditions. Rest and avoiding activities that "
        "worsen the pain may help. Severe or persistent pain "
        "should be evaluated by a healthcare professional."
    ),

    "body_pain": (
        "Body aches can occur with infections, physical activity, "
        "fatigue, or other conditions. Rest, hydration, and "
        "monitoring other symptoms can be helpful."
    ),

    "fatigue": (
        "Fatigue or tiredness can have many causes, including "
        "lack of sleep, stress, dehydration, illness, or other "
        "health conditions. If fatigue continues for a long time "
        "or significantly affects daily activities, consult a "
        "healthcare professional."
    ),

    "weakness": (
        "Weakness can occur because of tiredness, dehydration, "
        "illness, nutritional problems, or other conditions. "
        "If the weakness is sudden, severe, or associated with "
        "other serious symptoms, seek medical attention."
    ),

    "nausea": (
        "Nausea is the feeling that you may vomit. It can occur "
        "with infections, digestive problems, motion sickness, "
        "or other conditions. Monitor your symptoms and stay "
        "hydrated. Persistent or severe nausea should be "
        "evaluated by a healthcare professional."
    ),

    "vomiting": (
        "Vomiting can occur because of infections, digestive "
        "problems, food-related illness, or other causes. "
        "Maintaining hydration is important. Seek medical help "
        "if vomiting is severe, persistent, or accompanied by "
        "signs of dehydration or other serious symptoms."
    ),

    "diarrhea": (
        "Diarrhea can occur due to infections, food-related "
        "illness, digestive conditions, or other causes. "
        "Replacing lost fluids is important. If diarrhea is "
        "severe, persistent, or accompanied by blood or signs "
        "of dehydration, seek medical attention."
    ),

    "dizziness": (
        "Dizziness can have several causes, including dehydration, "
        "low blood pressure, illness, or other conditions. Sit or "
        "lie down safely if you feel dizzy and avoid activities "
        "where falling could be dangerous. Persistent or severe "
        "dizziness should be evaluated by a healthcare professional."
    ),

    "rash": (
        "A skin rash can have many causes, including irritation, "
        "allergies, infections, or other conditions. Avoid "
        "scratching the affected area and monitor for changes. "
        "If the rash is widespread, rapidly worsening, or occurs "
        "with breathing difficulty or swelling, seek medical care."
    ),

    "itching": (
        "Itching can occur because of dry skin, irritation, "
        "allergies, insect bites, or other conditions. Try to "
        "identify possible triggers and avoid scratching. "
        "Persistent or severe itching should be discussed with "
        "a healthcare professional."
    ),

    "shortness_of_breath": (
        "Breathing difficulty can sometimes indicate a serious "
        "condition. If you are having significant difficulty "
        "breathing, especially with chest pain, fainting, blue "
        "lips, or severe weakness, seek emergency medical "
        "attention immediately."
    )
}


# =========================================================
# FOLLOW-UP QUESTIONS
# =========================================================

FOLLOW_UP_QUESTIONS = {

    "fever": (
        "How long have you had the fever, and do you have "
        "any other symptoms such as cough, headache, or body pain?"
    ),

    "headache": (
        "How long have you had the headache, and would you "
        "describe the pain as mild, moderate, or severe?"
    ),

    "cough": (
        "How long have you had the cough? Is it dry, or "
        "are you coughing up mucus?"
    ),

    "cold": (
        "How long have you had the cold symptoms? Do you "
        "also have fever, cough, or sore throat?"
    ),

    "sore_throat": (
        "How long have you had the sore throat? Do you also "
        "have fever, cough, or difficulty swallowing?"
    ),

    "stomach_pain": (
        "Where exactly is the stomach pain, how long has "
        "it been present, and how severe is it?"
    ),

    "chest_pain": (
        "When did the chest pain begin, and are you experiencing "
        "difficulty breathing, sweating, dizziness, or fainting?"
    ),

    "back_pain": (
        "When did the back pain start, and did it occur after "
        "any physical activity or injury?"
    ),

    "nausea": (
        "How long have you been feeling nauseous? Are you "
        "also experiencing vomiting or stomach pain?"
    ),

    "vomiting": (
        "How long have you been vomiting, and are you able "
        "to keep fluids down?"
    ),

    "diarrhea": (
        "How long have you had diarrhea, and are you experiencing "
        "fever, vomiting, or signs of dehydration?"
    ),

    "dizziness": (
        "When does the dizziness occur? Are you also experiencing "
        "weakness, fainting, vomiting, or a headache?"
    ),

    "rash": (
        "When did the rash appear, and is it spreading or "
        "associated with itching, swelling, or fever?"
    ),

    "fatigue": (
        "How long have you been feeling tired, and have you "
        "noticed any other symptoms?"
    ),

    "weakness": (
        "When did the weakness begin, and is it affecting "
        "your whole body or one particular area?"
    )
}


# =========================================================
# EMERGENCY KEYWORDS
# =========================================================

EMERGENCY_KEYWORDS = [

    "chest pain",

    "severe chest pain",

    "difficulty breathing",

    "cannot breathe",

    "can't breathe",

    "severe bleeding",

    "unconscious",

    "passed out",

    "fainted",

    "seizure",

    "stroke",

    "face drooping",

    "speech difficulty",

    "severe allergic reaction",

    "swelling of throat",

    "suicidal",

    "suicide",

    "self harm",

    "self-harm"
]


# =========================================================
# MEDICATION KEYWORDS
# =========================================================

MEDICATION_KEYWORDS = [

    "medicine",

    "medication",

    "tablet",

    "tablets",

    "pill",

    "pills",

    "drug",

    "drugs",

    "dose",

    "dosage",

    "antibiotic",

    "antibiotics",

    "painkiller",

    "painkiller dosage",

    "what should i take",

    "which medicine",

    "which tablet",

    "which pill"
]


# =========================================================
# MEDICATION SAFETY RESPONSE
# =========================================================

MEDICATION_SAFETY_RESPONSE = (
    "I can provide general health information, but I cannot "
    "recommend a specific medicine, dosage, or prescription. "
    "Please consult a qualified doctor or pharmacist for "
    "personalized medication advice."
)


# =========================================================
# EMERGENCY RESPONSE
# =========================================================

EMERGENCY_RESPONSE = (
    "This may describe a potentially serious medical situation. "
    "Please seek urgent medical attention or contact your local "
    "emergency service immediately. This chatbot cannot handle "
    "medical emergencies."
)


# =========================================================
# GENERAL RESPONSE
# =========================================================

GENERAL_HEALTH_RESPONSE = (
    "I can help with general health information. Please describe "
    "your symptoms, how long you have had them, and whether "
    "they are mild, moderate, or severe."
)


# =========================================================
# UNKNOWN RESPONSE
# =========================================================

UNKNOWN_RESPONSE = (
    "I'm not completely sure how to answer that. Please describe "
    "your health concern or symptoms in simple words. For example, "
    "you can say 'I have a headache' or 'I have fever and cough.'"
)


# =========================================================
# SAFETY DISCLAIMER
# =========================================================

SAFETY_DISCLAIMER = (
    "This chatbot provides general health information only. "
    "It does not replace professional medical advice, diagnosis, "
    "or treatment."
)


# =========================================================
# FUNCTION: FIND SYMPTOMS
# =========================================================

def find_symptoms(message):
    """
    Find known symptoms inside a user message.

    Returns:
        list: detected symptom names
    """

    message = message.lower()

    detected = []

    for symptom, keywords in SYMPTOM_KEYWORDS.items():

        for keyword in keywords:

            if keyword in message:

                if symptom not in detected:

                    detected.append(symptom)

                break

    return detected


# =========================================================
# FUNCTION: CHECK EMERGENCY
# =========================================================

def check_emergency(message):
    """
    Check whether a message contains emergency keywords.

    Returns:
        bool
    """

    message = message.lower()

    for keyword in EMERGENCY_KEYWORDS:

        if keyword in message:

            return True

    return False


# =========================================================
# FUNCTION: CHECK MEDICATION QUESTION
# =========================================================

def check_medication_question(message):
    """
    Check whether the user is asking about medication.

    Returns:
        bool
    """

    message = message.lower()

    for keyword in MEDICATION_KEYWORDS:

        if keyword in message:

            return True

    return False


# =========================================================
# FUNCTION: GET HEALTH RESPONSE
# =========================================================

def get_health_response(symptom):
    """
    Return general information for a symptom.
    """

    return HEALTH_RESPONSES.get(
        symptom,
        GENERAL_HEALTH_RESPONSE
    )


# =========================================================
# FUNCTION: GET FOLLOW-UP
# =========================================================

def get_follow_up_question(symptom):
    """
    Return a follow-up question for a symptom.
    """

    return FOLLOW_UP_QUESTIONS.get(
        symptom
    )


# =========================================================
# FUNCTION: GET PRIMARY SYMPTOM
# =========================================================

def get_primary_symptom(symptoms):
    """
    Select the most important symptom from
    a list of detected symptoms.
    """

    if not symptoms:

        return None

    # Emergency-related symptoms get priority
    if "chest_pain" in symptoms:

        return "chest_pain"

    if "shortness_of_breath" in symptoms:

        return "shortness_of_breath"

    # Otherwise return first detected symptom
    return symptoms[0]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_messages = [

        "I have fever",

        "I have headache and cough",

        "My stomach hurts",

        "I have chest pain",

        "Which medicine should I take?"

    ]

    print("=" * 60)
    print("TESTING HEALTH RULES")
    print("=" * 60)

    for message in test_messages:

        print("\nUser:", message)

        symptoms = find_symptoms(message)

        print("Symptoms:", symptoms)

        print(
            "Emergency:",
            check_emergency(message)
        )

        print(
            "Medication:",
            check_medication_question(message)
        )

        primary = get_primary_symptom(
            symptoms
        )

        if primary:

            print(
                "Primary symptom:",
                primary
            )

            print(
                "Response:",
                get_health_response(primary)
            )

            question = get_follow_up_question(
                primary
            )

            if question:

                print(
                    "Follow-up:",
                    question
                )