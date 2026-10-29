import os
import re
import pandas as pd


# ============================================================
# PROJECT PATH
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

DATASET_DIR = os.path.join(
    PROJECT_ROOT,
    "datasets"
)

SYMPTOM_DISEASE_PATH = os.path.join(
    DATASET_DIR,
    "Symptom2Disease.csv"
)

DISEASE_SYMPTOMS_PATH = os.path.join(
    DATASET_DIR,
    "Final_Augmented_dataset_Diseases_and_Symptoms.csv"
)


# ============================================================
# DATASET VARIABLES
# ============================================================

symptom_disease_df = None
disease_symptoms_df = None


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if text is None:
        return ""

    text = str(text).lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# LOAD SYMPTOM2DISEASE DATASET
# ============================================================

def load_symptom_disease():

    global symptom_disease_df

    if symptom_disease_df is not None:
        return symptom_disease_df

    try:

        if not os.path.exists(SYMPTOM_DISEASE_PATH):

            print(
                "Symptom2Disease.csv not found:"
            )

            print(
                SYMPTOM_DISEASE_PATH
            )

            return None

        df = pd.read_csv(
            SYMPTOM_DISEASE_PATH,
            encoding="utf-8"
        )

        df.columns = (
            df.columns
            .str.strip()
        )

        print(
            "Symptom2Disease columns:",
            list(df.columns)
        )

        symptom_disease_df = df

        print(
            f"Symptom2Disease loaded: "
            f"{len(df)} rows"
        )

        return symptom_disease_df

    except Exception as e:

        print(
            "Error loading Symptom2Disease:",
            e
        )

        return None


# ============================================================
# LOAD DISEASE SYMPTOMS DATASET
# ============================================================

def load_disease_symptoms():

    global disease_symptoms_df

    if disease_symptoms_df is not None:
        return disease_symptoms_df

    try:

        if not os.path.exists(
            DISEASE_SYMPTOMS_PATH
        ):

            print(
                "Final_Augmented_dataset_Diseases_and_Symptoms.csv not found:"
            )

            print(
                DISEASE_SYMPTOMS_PATH
            )

            return None

        df = pd.read_csv(
            DISEASE_SYMPTOMS_PATH,
            encoding="utf-8"
        )

        df.columns = (
            df.columns
            .str.strip()
        )

        print(
            "DiseaseAndSymptoms columns:",
            list(df.columns)
        )

        disease_symptoms_df = df

        print(
            f"DiseaseAndSymptoms loaded: "
            f"{len(df)} rows"
        )

        return disease_symptoms_df

    except Exception as e:

        print(
            "Error loading DiseaseAndSymptoms:",
            e
        )

        return None


# ============================================================
# COMMON SYMPTOMS
# ============================================================

COMMON_SYMPTOMS = [

    "fever",
    "cough",
    "headache",
    "fatigue",
    "weakness",
    "nausea",
    "vomiting",
    "diarrhea",
    "dizziness",
    "chest pain",
    "shortness of breath",
    "breathing difficulty",
    "sore throat",
    "runny nose",
    "stuffy nose",
    "sneezing",
    "body pain",
    "muscle pain",
    "joint pain",
    "abdominal pain",
    "stomach pain",
    "back pain",
    "rash",
    "itching",
    "swelling",
    "chills",
    "loss of appetite",
    "weight loss",
    "weight gain",
    "blurred vision",
    "dry mouth",
    "dehydration",
    "constipation",
    "blood in stool",
    "blood in urine",
    "difficulty swallowing",
    "loss of consciousness"
]


# ============================================================
# SYMPTOM EXTRACTION
# ============================================================

def extract_symptoms(query):

    if not query:
        return []

    normalized_query = normalize_text(
        query
    )

    found_symptoms = []

    # Longer phrases first
    symptoms_sorted = sorted(
        COMMON_SYMPTOMS,
        key=len,
        reverse=True
    )

    for symptom in symptoms_sorted:

        normalized_symptom = normalize_text(
            symptom
        )

        if normalized_symptom in normalized_query:

            if symptom not in found_symptoms:

                found_symptoms.append(
                    symptom
                )

    return found_symptoms


# ============================================================
# FIND DISEASES FROM SYMPTOM2DISEASE
# ============================================================

def search_symptom_diseases(
    symptoms,
    top_k=5
):

    df = load_symptom_disease()

    if df is None or df.empty:
        return []

    if not symptoms:
        return []

    columns = list(df.columns)

    # Detect likely columns automatically
    disease_column = None
    symptom_column = None

    for column in columns:

        normalized_column = (
            normalize_text(column)
        )

        if (
            "disease" in normalized_column
            or normalized_column == "label"
        ):

            disease_column = column

        if (
            "symptom" in normalized_column
            or normalized_column == "text"
        ):

            symptom_column = column

    if disease_column is None:
        return []

    if symptom_column is None:

        # Try first non-disease column
        for column in columns:

            if column != disease_column:

                symptom_column = column
                break

    if symptom_column is None:
        return []

    disease_scores = {}

    for _, row in df.iterrows():

        disease = str(
            row[disease_column]
        ).strip()

        symptom_text = normalize_text(
            row[symptom_column]
        )

        if not disease or not symptom_text:
            continue

        matched = 0

        for symptom in symptoms:

            if normalize_text(symptom) in symptom_text:

                matched += 1

        if matched > 0:

            disease_scores[disease] = (
                disease_scores.get(
                    disease,
                    0
                ) + matched
            )

    results = []

    for disease, score in disease_scores.items():

        results.append({
            "disease": disease,
            "matched_symptoms": score
        })

    results.sort(
        key=lambda x: x["matched_symptoms"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# FIND DISEASES FROM DISEASEANDSYMPTOMS
# ============================================================

def search_disease_symptoms(
    symptoms,
    top_k=5
):

    df = load_disease_symptoms()

    if df is None or df.empty:
        return []

    if not symptoms:
        return []

    columns = list(df.columns)

    disease_column = None

    # Find disease column
    for column in columns:

        normalized_column = (
            normalize_text(column)
        )

        if (
            "disease" in normalized_column
            or normalized_column == "label"
        ):

            disease_column = column
            break

    if disease_column is None:
        return []

    symptom_columns = [
        column
        for column in columns
        if column != disease_column
    ]

    disease_scores = {}

    for _, row in df.iterrows():

        disease = str(
            row[disease_column]
        ).strip()

        if not disease:
            continue

        row_text = " ".join(
            str(row[column])
            for column in symptom_columns
            if pd.notna(row[column])
        )

        row_text = normalize_text(
            row_text
        )

        matched = 0

        for symptom in symptoms:

            if normalize_text(symptom) in row_text:

                matched += 1

        if matched > 0:

            disease_scores[disease] = max(
                disease_scores.get(
                    disease,
                    0
                ),
                matched
            )

    results = []

    for disease, score in disease_scores.items():

        results.append({
            "disease": disease,
            "matched_symptoms": score
        })

    results.sort(
        key=lambda x: x["matched_symptoms"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# COMPLETE SYMPTOM ANALYSIS
# ============================================================

def analyze_symptoms(query):

    symptoms = extract_symptoms(
        query
    )

    if not symptoms:

        return {
            "query": query,
            "symptoms": [],
            "possible_conditions": [],
            "message": (
                "I could not identify a "
                "clear symptom from your message."
            )
        }

    # Search first dataset
    results_1 = search_symptom_diseases(
        symptoms,
        top_k=5
    )

    # Search second dataset
    results_2 = search_disease_symptoms(
        symptoms,
        top_k=5
    )

    # Combine results
    combined = {}

    for result in results_1:

        disease = result["disease"]

        combined[disease] = (
            combined.get(disease, 0)
            + result["matched_symptoms"]
        )

    for result in results_2:

        disease = result["disease"]

        combined[disease] = (
            combined.get(disease, 0)
            + result["matched_symptoms"]
        )

    possible_conditions = []

    for disease, score in combined.items():

        possible_conditions.append({
            "disease": disease,
            "score": score
        })

    possible_conditions.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    possible_conditions = (
        possible_conditions[:5]
    )

    return {
        "query": query,
        "symptoms": symptoms,
        "possible_conditions":
            possible_conditions,
        "message": (
            "These are possible matches "
            "based on the symptoms provided. "
            "They are not a confirmed diagnosis."
        )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 60)
    print("        MEDICAL SYMPTOM ANALYZER TEST")
    print("=" * 60)

    test_queries = [

        "I have fever, headache and cough",

        "I am feeling dizzy and weak",

        "I have stomach pain and vomiting",

        "I have a rash and itching"

    ]

    for query in test_queries:

        print("\n")
        print("-" * 60)
        print("USER:")
        print(query)

        result = analyze_symptoms(
            query
        )

        print("\nEXTRACTED SYMPTOMS:")

        if result["symptoms"]:

            for symptom in result["symptoms"]:

                print(
                    f"  ✓ {symptom}"
                )

        else:

            print("  None")

        print(
            "\nPOSSIBLE CONDITIONS:"
        )

        if result["possible_conditions"]:

            for condition in result[
                "possible_conditions"
            ]:

                print(
                    f"  • "
                    f"{condition['disease']} "
                    f"(score: "
                    f"{condition['score']})"
                )

        else:

            print(
                "  No matching condition found."
            )

    print("\n")
    print("=" * 60)
    print("             TEST COMPLETE")
    print("=" * 60)
