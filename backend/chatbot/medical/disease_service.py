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

DISEASE_SYMPTOMS_PATH = os.path.join(
    DATASET_DIR,
    "DiseaseAndSymptoms.csv"
)

DISEASE_PRECAUTION_PATH = os.path.join(
    DATASET_DIR,
    "Disease precaution.csv"
)


# ============================================================
# DATASET CACHE
# ============================================================

disease_symptoms_df = None
disease_precaution_df = None


# ============================================================
# TEXT NORMALIZATION
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
# LOAD DISEASE + SYMPTOMS DATASET
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
                "DiseaseAndSymptoms.csv not found:"
            )

            print(
                DISEASE_SYMPTOMS_PATH
            )

            return None

        disease_symptoms_df = pd.read_csv(
            DISEASE_SYMPTOMS_PATH,
            encoding="utf-8"
        )

        disease_symptoms_df.columns = (
            disease_symptoms_df.columns
            .str.strip()
        )

        print(
            "DiseaseAndSymptoms loaded:",
            len(disease_symptoms_df),
            "rows"
        )

        print(
            "Columns:",
            list(disease_symptoms_df.columns)
        )

        return disease_symptoms_df

    except Exception as e:

        print(
            "Error loading DiseaseAndSymptoms:",
            e
        )

        return None


# ============================================================
# LOAD PRECAUTION DATASET
# ============================================================

def load_disease_precautions():

    global disease_precaution_df

    if disease_precaution_df is not None:
        return disease_precaution_df

    try:

        if not os.path.exists(
            DISEASE_PRECAUTION_PATH
        ):

            print(
                "Disease precaution.csv not found:"
            )

            print(
                DISEASE_PRECAUTION_PATH
            )

            return None

        disease_precaution_df = pd.read_csv(
            DISEASE_PRECAUTION_PATH,
            encoding="utf-8"
        )

        disease_precaution_df.columns = (
            disease_precaution_df.columns
            .str.strip()
        )

        print(
            "Disease precaution loaded:",
            len(disease_precaution_df),
            "rows"
        )

        print(
            "Columns:",
            list(disease_precaution_df.columns)
        )

        return disease_precaution_df

    except Exception as e:

        print(
            "Error loading Disease precaution:",
            e
        )

        return None


# ============================================================
# FIND DISEASE COLUMN
# ============================================================

def find_disease_column(df):

    if df is None:
        return None

    for column in df.columns:

        normalized = normalize_text(
            column
        )

        if normalized in [
            "disease",
            "diseases",
            "condition",
            "diagnosis",
            "label"
        ]:

            return column

        if "disease" in normalized:

            return column

    return None


# ============================================================
# FIND DISEASE IN USER QUERY
# ============================================================

def find_disease(query):

    if not query:
        return None

    query_normalized = normalize_text(
        query
    )

    candidates = []

    # --------------------------------------------------------
    # Search disease/symptom dataset
    # --------------------------------------------------------

    df = load_disease_symptoms()

    if df is not None and not df.empty:

        disease_column = find_disease_column(
            df
        )

        if disease_column:

            for disease in df[
                disease_column
            ].dropna().unique():

                disease_text = str(
                    disease
                ).strip()

                normalized_disease = (
                    normalize_text(
                        disease_text
                    )
                )

                if not normalized_disease:
                    continue

                if normalized_disease in query_normalized:

                    candidates.append(
                        (
                            disease_text,
                            len(normalized_disease)
                        )
                    )

    # --------------------------------------------------------
    # Search precaution dataset
    # --------------------------------------------------------

    df = load_disease_precautions()

    if df is not None and not df.empty:

        disease_column = find_disease_column(
            df
        )

        if disease_column:

            for disease in df[
                disease_column
            ].dropna().unique():

                disease_text = str(
                    disease
                ).strip()

                normalized_disease = (
                    normalize_text(
                        disease_text
                    )
                )

                if not normalized_disease:
                    continue

                if normalized_disease in query_normalized:

                    candidates.append(
                        (
                            disease_text,
                            len(normalized_disease)
                        )
                    )

    if not candidates:
        return None

    # Prefer longest matching disease name
    candidates.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return candidates[0][0]


# ============================================================
# GET DISEASE SYMPTOMS
# ============================================================

def get_disease_symptoms(disease):

    df = load_disease_symptoms()

    if df is None or df.empty:
        return []

    disease_column = find_disease_column(
        df
    )

    if disease_column is None:
        return []

    target = normalize_text(
        disease
    )

    matching_rows = df[
        df[disease_column]
        .astype(str)
        .apply(
            lambda x:
            normalize_text(x) == target
        )
    ]

    if matching_rows.empty:
        return []

    row = matching_rows.iloc[0]

    symptoms = []

    for column in df.columns:

        if column == disease_column:
            continue

        value = row[column]

        if pd.isna(value):
            continue

        value = str(value).strip()

        if not value:
            continue

        normalized_value = normalize_text(
            value
        )

        # Ignore empty/invalid values
        if normalized_value in [
            "",
            "none",
            "nan"
        ]:

            continue

        symptoms.append(value)

    # Remove duplicates
    unique_symptoms = []

    for symptom in symptoms:

        if symptom not in unique_symptoms:

            unique_symptoms.append(
                symptom
            )

    return unique_symptoms


# ============================================================
# GET DISEASE PRECAUTIONS
# ============================================================

def get_disease_precautions(disease):

    df = load_disease_precautions()

    if df is None or df.empty:
        return []

    disease_column = find_disease_column(
        df
    )

    if disease_column is None:
        return []

    target = normalize_text(
        disease
    )

    matching_rows = df[
        df[disease_column]
        .astype(str)
        .apply(
            lambda x:
            normalize_text(x) == target
        )
    ]

    if matching_rows.empty:
        return []

    row = matching_rows.iloc[0]

    precautions = []

    for column in df.columns:

        if column == disease_column:
            continue

        value = row[column]

        if pd.isna(value):
            continue

        value = str(value).strip()

        if not value:
            continue

        if normalize_text(value) in [
            "",
            "none",
            "nan"
        ]:

            continue

        precautions.append(value)

    return precautions


# ============================================================
# DISEASE INFORMATION
# ============================================================

def get_disease_information(disease):

    if not disease:

        return None

    symptoms = get_disease_symptoms(
        disease
    )

    precautions = get_disease_precautions(
        disease
    )

    return {
        "disease": disease,
        "symptoms": symptoms,
        "precautions": precautions
    }


# ============================================================
# FORMAT RESPONSE
# ============================================================

def format_disease_response(
    information
):

    if not information:
        return None

    disease = information[
        "disease"
    ]

    symptoms = information[
        "symptoms"
    ]

    precautions = information[
        "precautions"
    ]

    response_parts = []

    response_parts.append(
        f"Here is some general information "
        f"about {disease}."
    )

    # --------------------------------------------------------
    # Symptoms
    # --------------------------------------------------------

    if symptoms:

        response_parts.append(
            "\nCommonly associated symptoms:"
        )

        for symptom in symptoms[:10]:

            response_parts.append(
                f"• {symptom}"
            )

    # --------------------------------------------------------
    # Precautions
    # --------------------------------------------------------

    if precautions:

        response_parts.append(
            "\nGeneral precautions:"
        )

        for precaution in precautions[:10]:

            response_parts.append(
                f"• {precaution}"
            )

    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    response_parts.append(
        "\nThis information is for general "
        "educational purposes and does not "
        "confirm a diagnosis."
    )

    return "\n".join(
        response_parts
    )


# ============================================================
# MAIN DISEASE QUERY FUNCTION
# ============================================================

def answer_disease_query(query):

    disease = find_disease(
        query
    )

    if not disease:

        return {
            "found": False,
            "disease": None,
            "response": (
                "I could not identify a specific "
                "disease in your question."
            )
        }

    information = get_disease_information(
        disease
    )

    response = format_disease_response(
        information
    )

    return {
        "found": True,
        "disease": disease,
        "symptoms": information[
            "symptoms"
        ],
        "precautions": information[
            "precautions"
        ],
        "response": response
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 65)
    print("             DISEASE SERVICE TEST")
    print("=" * 65)

    test_queries = [

        "What are the symptoms of dengue?",

        "Tell me about malaria",

        "What precautions should I take for flu?",

        "What are the symptoms of common cold?"

    ]

    for query in test_queries:

        print("\n")
        print("-" * 65)

        print("USER:")
        print(query)

        result = answer_disease_query(
            query
        )

        print("\nDISEASE:")
        print(
            result["disease"]
        )

        print("\nRESPONSE:")

        print(
            result["response"]
        )

    print("\n")
    print("=" * 65)
    print("                  TEST COMPLETE")
    print("=" * 65)