"""
MediChat - Natural Language Rule-Based Healthcare Chatbot

Purpose:
- Accept free-form natural-language health questions
- Detect emergency situations first
- Detect symptoms without requiring fixed questions
- Detect common health-question intents
- Use the existing disease/symptom datasets efficiently
- Give conservative, non-diagnostic responses

This is the Rule-Based component of the MediChat hybrid system.
"""

import csv
import os
import re


class RuleBasedBot:

    def __init__(self):

        # =========================================================
        # PATHS
        # =========================================================

        self.base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        self.project_dir = os.path.abspath(
            os.path.join(
                self.base_dir,
                "..",
                ".."
            )
        )

        self.datasets_dir = os.path.join(
            self.project_dir,
            "datasets"
        )

        # =========================================================
        # LOAD DATASETS
        # =========================================================

        self.symptom2disease = self._load_csv(
            "Symptom2Disease.csv"
        )

        self.disease_description = self._load_csv(
            "Disease_Description.csv"
        )

        self.disease_precautions = self._load_csv(
            "Disease precaution.csv"
        )

        self.symptom_severity = self._load_csv(
            "Symptom-severity.csv"
        )

        self.disease_symptoms = self._load_csv(
            "Final_Augmented_dataset_Diseases_and_Symptoms.csv"
        )

        # =========================================================
        # EMERGENCY PHRASES
        # =========================================================

        self.emergency_phrases = [

            "severe chest pain",
            "chest pain and difficulty breathing",
            "chest pain with difficulty breathing",
            "chest pain and can't breathe",
            "chest pain and cannot breathe",

            "difficulty breathing",
            "cannot breathe",
            "can't breathe",
            "unable to breathe",
            "struggling to breathe",
            "not able to breathe",

            "severe bleeding",
            "heavy bleeding",
            "uncontrolled bleeding",

            "unconscious",
            "passed out",
            "loss of consciousness",

            "seizure",

            "face drooping",
            "difficulty speaking",
            "unable to speak",

            "throat swelling",
            "swelling of throat",
            "severe allergic reaction"
        ]

        # =========================================================
        # NATURAL-LANGUAGE SYMPTOM ALIASES
        # =========================================================

        self.aliases = {

            "fever": [
                "fever",
                "high temperature",
                "running a fever",
                "feeling feverish",
                "feel feverish"
            ],

            "headache": [
                "headache",
                "head pain",
                "pain in my head",
                "my head hurts",
                "head hurts",
                "head is hurting"
            ],

            "cough": [
                "cough",
                "coughing"
            ],

            "dizziness": [
                "dizziness",
                "dizzy",
                "feeling dizzy",
                "feel dizzy",
                "lightheaded",
                "light headed"
            ],

            "nausea": [
                "nausea",
                "nauseous",
                "feeling nauseous",
                "feel nauseous"
            ],

            "vomiting": [
                "vomiting",
                "vomit",
                "throwing up",
                "threw up"
            ],

            "diarrhea": [
                "diarrhea",
                "loose motion",
                "loose motions",
                "loose stool",
                "loose stools"
            ],

            "stomach_pain": [
                "stomach pain",
                "stomach ache",
                "belly pain",
                "abdominal pain",
                "pain in my stomach",
                "my stomach hurts"
            ],

            "chest_pain": [
                "chest pain",
                "pain in my chest",
                "my chest hurts"
            ],

            "shortness_of_breath": [
                "shortness of breath",
                "breathlessness",
                "short of breath",
                "difficulty breathing"
            ],

            "sore_throat": [
                "sore throat",
                "throat pain",
                "painful throat",
                "my throat hurts"
            ],

            "skin_rash": [
                "skin rash",
                "skin rashes",
                "rash",
                "skin irritation"
            ],

            "itching": [
                "itching",
                "itchy",
                "skin itching"
            ],

            "fatigue": [
                "fatigue",
                "very tired",
                "extremely tired",
                "really tired",
                "feeling tired",
                "feel tired",
                "tired all the time",
                "exhausted",
                "low energy",
                "no energy"
            ],

            "weakness": [
                "weakness",
                "feeling weak",
                "feel weak",
                "very weak"
            ],

            "back_pain": [
                "back pain",
                "pain in my back",
                "my back hurts"
            ],

            "body_pain": [
                "body pain",
                "body ache",
                "body aches",
                "muscle pain",
                "muscle aches"
            ],

            "sleep_problem": [
                "sleep problem",
                "sleep problems",
                "poor sleep",
                "bad sleep",
                "not sleeping well",
                "cannot sleep",
                "can't sleep",
                "trouble sleeping",
                "difficulty sleeping",
                "sleeping badly",
                "lack of sleep"
            ]
        }

        # =========================================================
        # DATASET SYMPTOMS
        # =========================================================

        self.dataset_symptom_names = (
            self._build_dataset_symptom_names()
        )

        self.symptom_vocabulary = (
            self._build_symptom_vocabulary()
        )

        # =========================================================
        # FAST INDEX
        # =========================================================

        self.disease_index = (
            self._build_disease_index()
        )

        self.symptom_to_diseases = (
            self._build_symptom_to_diseases()
        )

        # =========================================================
        # DESCRIPTION / PRECAUTION INDEX
        # =========================================================

        self.description_index = (
            self._build_description_index()
        )

        self.precaution_index = (
            self._build_precaution_index()
        )

        print()
        print("=" * 65)
        print("MEDICHAT NATURAL-LANGUAGE RULE-BASED BOT")
        print("=" * 65)
        print(
            "Disease-symptom records:",
            len(self.disease_symptoms)
        )
        print(
            "Indexed diseases:",
            len(self.disease_index)
        )
        print(
            "Symptom vocabulary:",
            len(self.symptom_vocabulary)
        )
        print("=" * 65)

    # =============================================================
    # CSV LOADER
    # =============================================================

    def _load_csv(self, filename):

        path = os.path.join(
            self.datasets_dir,
            filename
        )

        if not os.path.exists(path):

            print(
                "[WARNING] Dataset not found:",
                filename
            )

            return []

        try:

            with open(
                path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                rows = []

                for row in reader:

                    cleaned = {}

                    for key, value in row.items():

                        if key is None:
                            continue

                        cleaned[str(key).strip()] = (
                            str(value).strip()
                            if value is not None
                            else ""
                        )

                    rows.append(cleaned)

                return rows

        except Exception as error:

            print(
                "[ERROR] Loading",
                filename,
                ":",
                error
            )

            return []

    # =============================================================
    # NORMALIZE TEXT
    # =============================================================

    def normalize(self, text):

        if text is None:
            return ""

        text = str(text).lower()

        # Common spelling variations
        replacements = {
            "cant": "can't",
            "wont": "won't",
            "dont": "don't",
            "ive": "i've",
            "im": "i'm",
            "id": "i'd",
            "i hae": "i have",
            "hve": "have"
        }

        for old, new in replacements.items():

            text = re.sub(
                r"\b" + re.escape(old) + r"\b",
                new,
                text
            )

        text = text.replace(
            "_",
            " "
        )

        text = re.sub(
            r"[^a-z0-9'\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =============================================================
    # PHRASE MATCH
    # =============================================================

    def _phrase_exists(
        self,
        text,
        phrase
    ):

        if not phrase:
            return False

        return re.search(
            r"\b" + re.escape(phrase) + r"\b",
            text
        ) is not None

    # =============================================================
    # DATASET SYMPTOM NAMES
    # =============================================================

    def _build_dataset_symptom_names(self):

        names = {}

        for row in self.symptom_severity:

            symptom = row.get(
                "Symptom",
                ""
            ).strip()

            if symptom:

                names[
                    self.normalize(symptom)
                ] = symptom

        if self.disease_symptoms:

            for column in self.disease_symptoms[0].keys():

                if column.lower() == "diseases":
                    continue

                if column.strip():

                    names[
                        self.normalize(column)
                    ] = column.strip()

        return names

    # =============================================================
    # SYMPTOM VOCABULARY
    # =============================================================

    def _build_symptom_vocabulary(self):

        vocabulary = set()

        for symptom in self.dataset_symptom_names:

            if symptom:
                vocabulary.add(symptom)

        for aliases in self.aliases.values():

            for alias in aliases:

                normalized = self.normalize(alias)

                if normalized:
                    vocabulary.add(normalized)

        return sorted(
            vocabulary,
            key=len,
            reverse=True
        )

    # =============================================================
    # DISEASE INDEX
    # =============================================================

    def _build_disease_index(self):

        index = {}

        for row in self.disease_symptoms:

            disease = row.get(
                "diseases",
                ""
            ).strip()

            if not disease:
                continue

            disease_key = self.normalize(
                disease
            )

            if disease_key not in index:

                index[disease_key] = {
                    "disease": disease,
                    "symptoms": set()
                }

            for column, value in row.items():

                if column.lower() == "diseases":
                    continue

                if str(value).strip() != "1":
                    continue

                symptom = self.normalize(
                    column
                )

                if symptom:

                    index[disease_key][
                        "symptoms"
                    ].add(symptom)

        return index

    # =============================================================
    # REVERSE SYMPTOM INDEX
    # =============================================================

    def _build_symptom_to_diseases(self):

        index = {}

        for disease_key, data in self.disease_index.items():

            for symptom in data["symptoms"]:

                if symptom not in index:

                    index[symptom] = set()

                index[symptom].add(
                    disease_key
                )

        return index

    # =============================================================
    # DESCRIPTION INDEX
    # =============================================================

    def _build_description_index(self):

        index = {}

        for row in self.disease_description:

            disease = row.get(
                "Disease",
                ""
            ).strip()

            description = row.get(
                "Description",
                ""
            ).strip()

            if disease:

                index[
                    self.normalize(disease)
                ] = description

        return index

    # =============================================================
    # PRECAUTION INDEX
    # =============================================================

    def _build_precaution_index(self):

        index = {}

        for row in self.disease_precautions:

            disease = row.get(
                "Disease",
                ""
            ).strip()

            if not disease:
                continue

            precautions = []

            for key, value in row.items():

                if key.lower().startswith(
                    "precaution"
                ):

                    if value and value.strip():

                        precautions.append(
                            value.strip()
                        )

            index[
                self.normalize(disease)
            ] = precautions

        return index

    # =============================================================
    # GREETING
    # =============================================================

    def is_greeting(self, text):

        return self.normalize(text) in {
            "hi",
            "hello",
            "hey",
            "hii",
            "hiii",
            "namaste",
            "good morning",
            "good afternoon",
            "good evening"
        }

    # =============================================================
    # GOODBYE
    # =============================================================

    def is_goodbye(self, text):

        return self.normalize(text) in {
            "bye",
            "goodbye",
            "good bye",
            "see you",
            "see you later"
        }

    # =============================================================
    # THANKS
    # =============================================================

    def is_thanks(self, text):

        return self.normalize(text) in {
            "thanks",
            "thank you",
            "thankyou",
            "thx",
            "thanks a lot"
        }

    # =============================================================
    # EMERGENCY
    # =============================================================

    def check_emergency(self, text):

        normalized = self.normalize(text)

        for phrase in self.emergency_phrases:

            phrase = self.normalize(
                phrase
            )

            if self._phrase_exists(
                normalized,
                phrase
            ):

                return True

        return False

    # =============================================================
    # EMERGENCY RESPONSE
    # =============================================================

    def emergency_response(self):

        return (
            "⚠️ This may describe a potentially serious "
            "medical situation.\n\n"
            "Please seek urgent medical attention or contact "
            "your local emergency service immediately.\n\n"
            "MediChat provides general health information and "
            "cannot manage medical emergencies."
        )

    # =============================================================
    # FIND SYMPTOMS
    # =============================================================

    def find_symptoms(self, text):

        normalized_text = self.normalize(
            text
        )

        found = set()

        # ---------------------------------------------
        # Natural-language aliases
        # ---------------------------------------------

        for canonical, aliases in self.aliases.items():

            for alias in aliases:

                alias_normalized = self.normalize(
                    alias
                )

                if self._phrase_exists(
                    normalized_text,
                    alias_normalized
                ):

                    # sleep_problem is an intent/context,
                    # not a disease symptom.
                    if canonical != "sleep_problem":

                        found.add(
                            canonical
                        )

                    break

        # ---------------------------------------------
        # Dataset vocabulary
        # ---------------------------------------------

        for symptom in self.symptom_vocabulary:

            if self._phrase_exists(
                normalized_text,
                symptom
            ):

                # Ignore aliases that represent the same
                # canonical symptom already detected.
                matched_canonical = None

                for canonical, aliases in self.aliases.items():

                    if symptom in [
                        self.normalize(a)
                        for a in aliases
                    ]:

                        matched_canonical = canonical
                        break

                if matched_canonical:

                    if matched_canonical != "sleep_problem":

                        found.add(
                            matched_canonical
                        )

                else:

                    original = (
                        self.dataset_symptom_names.get(
                            symptom,
                            symptom
                        )
                    )

                    found.add(
                        original.replace(
                            " ",
                            "_"
                        )
                    )

        return list(found)

    # =============================================================
    # QUESTION INTENT
    # =============================================================

    def detect_intent(self, text):

        text = self.normalize(text)

        # ---------------------------------------------
        # Sleep
        # ---------------------------------------------

        sleep_terms = [
            "sleep",
            "sleeping",
            "insomnia",
            "can't sleep",
            "cannot sleep",
            "trouble sleeping",
            "difficulty sleeping",
            "not sleeping well",
            "poor sleep"
        ]

        if any(
            term in text
            for term in sleep_terms
        ):

            return "sleep"

        # ---------------------------------------------
        # Warning signs / urgent care
        # ---------------------------------------------

        warning_terms = [
            "warning sign",
            "warning signs",
            "danger sign",
            "danger signs",
            "when should i seek",
            "when should i see a doctor",
            "when should i go to the hospital",
            "urgent medical care",
            "urgent care",
            "emergency signs",
            "serious symptoms"
        ]

        if any(
            term in text
            for term in warning_terms
        ):

            return "warning_signs"

        # ---------------------------------------------
        # Cause / reason
        # ---------------------------------------------

        cause_terms = [
            "why do i",
            "why does",
            "why am i",
            "what could cause",
            "what causes",
            "possible cause",
            "possible causes",
            "reason for",
            "what could be the reason",
            "what might be causing"
        ]

        if any(
            term in text
            for term in cause_terms
        ):

            return "cause"

        # ---------------------------------------------
        # Relationship
        # ---------------------------------------------

        relationship_terms = [
            "can stress cause",
            "can stress make",
            "can lack of sleep cause",
            "can this cause",
            "can this be caused by",
            "is it related to",
            "could this be because of",
            "could this cause"
        ]

        if any(
            term in text
            for term in relationship_terms
        ):

            return "relationship"

        # ---------------------------------------------
        # Self-care / advice
        # ---------------------------------------------

        advice_terms = [
            "what should i do",
            "what can i do",
            "how can i",
            "how do i",
            "what should i",
            "what can help",
            "how to improve",
            "how can i improve",
            "what should i take care of"
        ]

        if any(
            term in text
            for term in advice_terms
        ):

            return "self_care"

        # ---------------------------------------------
        # Duration / normality
        # ---------------------------------------------

        duration_terms = [
            "how long",
            "is it normal",
            "normal for",
            "for a week",
            "for two weeks",
            "for several days",
            "since yesterday",
            "since this morning",
            "for days",
            "for weeks"
        ]

        if any(
            term in text
            for term in duration_terms
        ):

            return "duration"

        # ---------------------------------------------
        # General information
        # ---------------------------------------------

        information_terms = [
            "what are",
            "what is",
            "tell me about",
            "explain",
            "information about",
            "symptoms of"
        ]

        if any(
            term in text
            for term in information_terms
        ):

            return "information"

        return "general"

    # =============================================================
    # SYMPTOM WEIGHT
    # =============================================================

    def get_symptom_weight(
        self,
        symptom
    ):

        normalized = self.normalize(
            symptom
        )

        for row in self.symptom_severity:

            current = self.normalize(
                row.get(
                    "Symptom",
                    ""
                )
            )

            if current == normalized:

                try:

                    return float(
                        row.get(
                            "weight",
                            1
                        )
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    return 1.0

        return 1.0

    # =============================================================
    # FIND DISEASE MATCHES
    # =============================================================

    def find_matching_diseases(
        self,
        symptoms
    ):

        if not symptoms:
            return []

        normalized_symptoms = set()

        for symptom in symptoms:

            dataset_name = (
                self._dataset_symptom_name(
                    symptom
                )
            )

            normalized = self.normalize(
                dataset_name
            )

            if normalized:

                normalized_symptoms.add(
                    normalized
                )

        if not normalized_symptoms:
            return []

        # ---------------------------------------------
        # Retrieve only relevant diseases
        # ---------------------------------------------

        candidates = set()

        for symptom in normalized_symptoms:

            candidates.update(
                self.symptom_to_diseases.get(
                    symptom,
                    set()
                )
            )

        results = []

        for disease_key in candidates:

            data = self.disease_index.get(
                disease_key
            )

            if not data:
                continue

            matched = (
                normalized_symptoms
                & data["symptoms"]
            )

            if not matched:
                continue

            matched_count = len(
                matched
            )

            coverage = (
                matched_count
                / max(
                    len(normalized_symptoms),
                    1
                )
            )

            weighted_score = sum(
                self.get_symptom_weight(
                    symptom
                )
                for symptom in matched
            )

            results.append({
                "disease": data["disease"],
                "matched_count": matched_count,
                "coverage": coverage,
                "score": weighted_score,
                "matched_symptoms": matched
            })

        results.sort(
            key=lambda item: (
                item["matched_count"],
                item["coverage"],
                item["score"]
            ),
            reverse=True
        )

        return results[:5]

    # =============================================================
    # DATASET SYMPTOM NAME
    # =============================================================

    def _dataset_symptom_name(
        self,
        symptom
    ):

        normalized = self.normalize(
            symptom
        )

        if normalized in self.dataset_symptom_names:

            return self.dataset_symptom_names[
                normalized
            ]

        return symptom

    # =============================================================
    # DESCRIPTION
    # =============================================================

    def get_description(
        self,
        disease
    ):

        return self.description_index.get(
            self.normalize(disease),
            ""
        )

    # =============================================================
    # PRECAUTIONS
    # =============================================================

    def get_precautions(
        self,
        disease
    ):

        return self.precaution_index.get(
            self.normalize(disease),
            []
        )

    # =============================================================
    # SAFE PRECAUTIONS
    # =============================================================

    def safe_precautions(
        self,
        precautions
    ):

        unsafe_terms = [
            "medicine",
            "medication",
            "drug",
            "tablet",
            "dose",
            "dosage",
            "antibiotic",
            "painkiller"
        ]

        safe = []

        for precaution in precautions:

            lower = precaution.lower()

            if any(
                term in lower
                for term in unsafe_terms
            ):
                continue

            safe.append(
                precaution
            )

        return safe[:4]

    # =============================================================
    # STRONG DATASET MATCH
    # =============================================================

    def is_strong_match(
        self,
        match,
        symptom_count
    ):

        if symptom_count <= 1:
            return False

        if (
            match["matched_count"] >= 2
            and match["coverage"] >= 1.0
        ):

            return True

        return False

    # =============================================================
    # DATASET RESPONSE
    # =============================================================

    def disease_response(
        self,
        symptoms
    ):

        matches = self.find_matching_diseases(
            symptoms
        )

        if not matches:
            return None

        best = matches[0]

        if not self.is_strong_match(
            best,
            len(symptoms)
        ):

            return None

        disease = best["disease"]

        response = (
            "The symptoms you described overlap with "
            "a pattern associated with **"
            + disease
            + "** in the MediChat reference dataset.\n\n"
        )

        description = self.get_description(
            disease
        )

        if description:

            response += (
                "**General information:**\n"
                + description
                + "\n\n"
            )

        precautions = self.safe_precautions(
            self.get_precautions(
                disease
            )
        )

        if precautions:

            response += (
                "**General precautions:**\n"
            )

            for precaution in precautions:

                response += (
                    "• "
                    + precaution
                    + "\n"
                )

            response += "\n"

        response += (
            "This is a dataset-based pattern match, "
            "not a medical diagnosis. Similar symptoms "
            "can occur with different conditions.\n\n"
            "If your symptoms are severe, persistent, "
            "unusual, or getting worse, please consult "
            "a qualified healthcare professional."
        )

        return response

    # =============================================================
    # GENERAL SYMPTOM RESPONSE
    # =============================================================

    def general_symptom_response(
        self,
        symptoms,
        intent="general"
    ):

        readable = []

        for symptom in symptoms:

            name = symptom.replace(
                "_",
                " "
            )

            if name not in readable:

                readable.append(
                    name
                )

        symptom_text = ", ".join(
            readable
        )

        if intent == "cause":

            return (
                "There can be several possible reasons for "
                + symptom_text
                + ". Different conditions, lifestyle factors, "
                "medications, and temporary illnesses can sometimes "
                "produce similar symptoms.\n\n"
                "I can't determine the specific cause from symptoms "
                "alone. If the symptom is persistent, worsening, or "
                "concerning, consider speaking with a healthcare "
                "professional."
            )

        if intent == "relationship":

            return (
                "Yes, factors such as stress, sleep, hydration, "
                "and other health or lifestyle factors can sometimes "
                "be associated with symptoms such as "
                + symptom_text
                + ".\n\n"
                "However, the presence of a symptom does not by "
                "itself establish the cause. If it continues or "
                "becomes severe, consider getting professional "
                "medical advice."
            )

        if intent == "self_care":

            return (
                "For mild "
                + symptom_text
                + ", general supportive measures such as adequate "
                "rest, hydration, and monitoring your symptoms may "
                "be helpful when appropriate.\n\n"
                "If your symptoms become severe, persist, or worsen, "
                "seek medical advice."
            )

        if intent == "duration":

            return (
                "The duration and severity of "
                + symptom_text
                + " can vary depending on the underlying cause.\n\n"
                "If the symptom is not improving, keeps returning, "
                "or becomes more severe, consider speaking with a "
                "healthcare professional."
            )

        return (
            "I understand that you're experiencing "
            + symptom_text
            + ".\n\n"
            "These symptoms can have several possible causes, "
            "so I would not want to assume a specific diagnosis.\n\n"
            "For general self-care, appropriate rest and hydration "
            "may be useful when suitable for your situation. "
            "Monitor how your symptoms change.\n\n"
            "If the symptoms are severe, persistent, unusual, "
            "or getting worse, please seek medical advice."
        )

    # =============================================================
    # SLEEP RESPONSE
    # =============================================================

    def sleep_response(
        self,
        text
    ):

        return (
            "Improving sleep often starts with keeping a consistent "
            "sleep and wake schedule and creating a comfortable, "
            "relaxing sleep environment.\n\n"
            "You can also try limiting caffeine later in the day, "
            "reducing stimulating activities close to bedtime, and "
            "allowing yourself enough time for sleep.\n\n"
            "If sleep problems continue for a long time, regularly "
            "affect your daily life, or are accompanied by concerning "
            "symptoms, consider discussing them with a healthcare "
            "professional."
        )

    # =============================================================
    # WARNING-SIGN RESPONSE
    # =============================================================

    def warning_sign_response(self):

        return (
            "Some symptoms can require urgent medical attention, "
            "especially when they are sudden, severe, rapidly "
            "worsening, or involve major difficulty breathing, "
            "severe chest pain, loss of consciousness, severe "
            "bleeding, or other serious changes.\n\n"
            "If someone is experiencing a potentially life-threatening "
            "emergency, contact local emergency services or seek "
            "urgent medical care immediately.\n\n"
            "MediChat provides general health information and cannot "
            "determine the seriousness of an individual medical "
            "condition remotely."
        )

    # =============================================================
    # GENERAL HEALTH RESPONSE
    # =============================================================

    def general_health_response(self):

        return (
            "I can help with general health information, symptoms, "
            "possible causes, self-care, warning signs, and when "
            "professional medical attention may be appropriate.\n\n"
            "You can describe your concern naturally. You don't "
            "need to choose a disease or select a chatbot type."
        )

    # =============================================================
    # OUT OF SCOPE
    # =============================================================

    def out_of_scope_response(self):

        return (
            "I'm MediChat, a healthcare-focused chatbot. "
            "You can ask health questions, describe symptoms, "
            "ask about possible causes, self-care, warning signs, "
            "or when medical attention may be appropriate.\n\n"
            "You can write your question naturally rather than "
            "using a fixed question format."
        )

    # =============================================================
    # MAIN RESPONSE
    # =============================================================

    def get_response(
        self,
        user_input
    ):

        text = self.normalize(
            user_input
        )

        # ---------------------------------------------
        # Empty
        # ---------------------------------------------

        if not text:

            return self.general_health_response()

        # ---------------------------------------------
        # SAFETY FIRST
        # ---------------------------------------------

        if self.check_emergency(text):

            return self.emergency_response()

        # ---------------------------------------------
        # Conversation
        # ---------------------------------------------

        if self.is_greeting(text):

            return (
                "Hello! I'm MediChat, your AI health assistant. "
                "Tell me about your health question or concern "
                "in your own words."
            )

        if self.is_goodbye(text):

            return (
                "Goodbye! Take care and stay well."
            )

        if self.is_thanks(text):

            return (
                "You're welcome! I'm here if you have another "
                "health question."
            )

        # ---------------------------------------------
        # Detect intent
        # ---------------------------------------------

        intent = self.detect_intent(
            text
        )

        # ---------------------------------------------
        # Sleep
        # ---------------------------------------------

        if intent == "sleep":

            return self.sleep_response(
                text
            )

        # ---------------------------------------------
        # Warning signs
        # ---------------------------------------------

        if intent == "warning_signs":

            return self.warning_sign_response()

        # ---------------------------------------------
        # Detect symptoms
        # ---------------------------------------------

        symptoms = self.find_symptoms(
            text
        )

        # ---------------------------------------------
        # Symptoms + natural-language question
        # ---------------------------------------------

        if symptoms:

            dataset_response = (
                self.disease_response(
                    symptoms
                )
            )

            if dataset_response:

                return dataset_response

            return self.general_symptom_response(
                symptoms,
                intent
            )

        # ---------------------------------------------
        # Relationship question without detected symptom
        # ---------------------------------------------

        if intent == "relationship":

            return (
                "Some health symptoms can be influenced by "
                "factors such as stress, sleep, hydration, "
                "and lifestyle. However, the relationship "
                "depends on the specific symptom and situation.\n\n"
                "If you tell me which symptom you're experiencing, "
                "I can provide more relevant general information."
            )

        # ---------------------------------------------
        # General health question
        # ---------------------------------------------

        health_words = [
            "health",
            "healthy",
            "disease",
            "condition",
            "medical",
            "doctor",
            "hospital",
            "treatment",
            "illness",
            "medicine",
            "symptom",
            "symptoms",
            "healthcare"
        ]

        if any(
            re.search(
                r"\b"
                + re.escape(word)
                + r"\b",
                text
            )
            for word in health_words
        ):

            return self.general_health_response()

        # ---------------------------------------------
        # General natural-language health-style questions
        # ---------------------------------------------

        question_words = [
            "why",
            "what",
            "how",
            "can",
            "could",
            "should",
            "is",
            "are"
        ]

        if any(
            text.startswith(word + " ")
            for word in question_words
        ):

            return (
                "I can help with that as a general health question. "
                "For a more useful answer, describe the health issue, "
                "symptom, or situation you're asking about."
            )

        # ---------------------------------------------
        # Out of scope
        # ---------------------------------------------

        return self.out_of_scope_response()


# =============================================================
# COMMAND-LINE TEST
# =============================================================

if __name__ == "__main__":

    bot = RuleBasedBot()

    print()
    print("MediChat Natural-Language Rule-Based Bot")
    print("Type 'bye' to exit.")
    print()

    while True:

        user_input = input(
            "You: "
        ).strip()

        if not user_input:
            continue

        response = bot.get_response(
            user_input
        )

        print()
        print("MediChat:")
        print(response)
        print()

        if bot.is_goodbye(
            user_input
        ):
            break