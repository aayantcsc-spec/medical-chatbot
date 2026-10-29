# ============================================================
# HEALTH CHATBOT - DATASET LOADER
# ============================================================

import os
import csv
import re


# ============================================================
# PROJECT ROOT
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        CURRENT_DIR,
        "..",
        ".."
    )
)

DATASET_DIR = os.path.join(
    PROJECT_ROOT,
    "datasets"
)


# ============================================================
# DATASET PATHS
# ============================================================

SYMPTOM2DISEASE_FILE = os.path.join(
    DATASET_DIR,
    "Symptom2Disease.csv"
)

DISEASE_SYMPTOMS_FILE = os.path.join(
    DATASET_DIR,
    "DiseaseAndSymptoms.csv"
)

PRECAUTION_FILE = os.path.join(
    DATASET_DIR,
    "Disease precaution.csv"
)

MEDICAL_QA_FILE = os.path.join(
    DATASET_DIR,
    "medical_qa.csv"
)


# ============================================================
# STORAGE
# ============================================================

symptom2disease_data = []
disease_symptoms_data = []
precaution_data = []
medical_qa_data = []


# ============================================================
# NORMALIZE
# ============================================================

def normalize(text):

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-zA-Z0-9\s]",
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
# GENERIC CSV LOADER
# ============================================================

def load_csv(file_path):

    data = []

    if not os.path.exists(file_path):

        print(
            "[DATASET NOT FOUND]",
            file_path
        )

        return data

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                cleaned_row = {}

                for key, value in row.items():

                    if key is None:
                        continue

                    cleaned_key = str(
                        key
                    ).strip()

                    cleaned_value = (
                        str(value).strip()
                        if value is not None
                        else ""
                    )

                    cleaned_row[
                        cleaned_key
                    ] = cleaned_value

                if cleaned_row:
                    data.append(
                        cleaned_row
                    )

        print(
            f"[DATASET LOADED] "
            f"{os.path.basename(file_path)} "
            f"-> {len(data)} rows"
        )

    except Exception as error:

        print(
            f"[DATASET ERROR] "
            f"{os.path.basename(file_path)}:",
            error
        )

    return data


# ============================================================
# LOAD ALL DATASETS
# ============================================================

def load_all_datasets():

    global symptom2disease_data
    global disease_symptoms_data
    global precaution_data
    global medical_qa_data

    print()
    print("=" * 70)
    print("HEALTH CHATBOT - LOADING MEDICAL DATASETS")
    print("=" * 70)

    # --------------------------------------------------------
    # Symptom -> Disease
    # --------------------------------------------------------

    symptom2disease_data = load_csv(
        SYMPTOM2DISEASE_FILE
    )

    # --------------------------------------------------------
    # Disease -> Symptoms
    # --------------------------------------------------------

    disease_symptoms_data = load_csv(
        DISEASE_SYMPTOMS_FILE
    )

    # --------------------------------------------------------
    # Disease -> Precautions
    # --------------------------------------------------------

    precaution_data = load_csv(
        PRECAUTION_FILE
    )

    # --------------------------------------------------------
    # Medical Question -> Answer
    # --------------------------------------------------------

    medical_qa_data = load_csv(
        MEDICAL_QA_FILE
    )

    print("=" * 70)

    print(
        "Symptom2Disease:",
        len(symptom2disease_data)
    )

    print(
        "DiseaseAndSymptoms:",
        len(disease_symptoms_data)
    )

    print(
        "Disease precaution:",
        len(precaution_data)
    )

    print(
        "Medical QA:",
        len(medical_qa_data)
    )

    print("=" * 70)
    print()


# ============================================================
# SEARCH - MEDICAL QA
# ============================================================

def search_medical_qa(
    query,
    top_k=10
):

    if not medical_qa_data:
        return []

    query_normalized = normalize(
        query
    )

    query_words = set(
        query_normalized.split()
    )

    if not query_words:
        return []

    results = []

    for row in medical_qa_data:

        question = (
            row.get("Question", "")
            or row.get("question", "")
            or ""
        )

        answer = (
            row.get("Answer", "")
            or row.get("answer", "")
            or ""
        )

        qtype = (
            row.get("qtype", "")
            or row.get("QType", "")
            or ""
        )

        if not question or not answer:
            continue

        question_normalized = normalize(
            question
        )

        question_words = set(
            question_normalized.split()
        )

        common_words = (
            query_words
            & question_words
        )

        # ----------------------------------------------------
        # Basic word similarity
        # ----------------------------------------------------

        if query_words:

            score = (
                len(common_words)
                / len(query_words)
            ) * 100

        else:

            score = 0

        # ----------------------------------------------------
        # Exact phrase match
        # ----------------------------------------------------

        if (
            query_normalized
            and query_normalized
            in question_normalized
        ):

            score += 50

        # ----------------------------------------------------
        # Individual important words
        # ----------------------------------------------------

        important_words = [

            word
            for word in query_words

            if len(word) >= 4

        ]

        for word in important_words:

            if word in question_normalized:

                score += 5

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        if score > 0:

            results.append({

                "qtype": qtype,

                "question": question,

                "answer": answer,

                "score": round(
                    score,
                    2
                )
            })

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    results.sort(
        key=lambda item:
        item["score"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# SEARCH - SYMPTOM TO DISEASE
# ============================================================

def search_symptom2disease(
    query,
    top_k=5
):

    if not symptom2disease_data:
        return []

    query_normalized = normalize(
        query
    )

    query_words = set(
        query_normalized.split()
    )

    results = []

    for row in symptom2disease_data:

        row_text = " ".join(
            str(value)
            for value in row.values()
            if value
        )

        normalized_row = normalize(
            row_text
        )

        row_words = set(
            normalized_row.split()
        )

        common = (
            query_words
            & row_words
        )

        if not query_words:
            continue

        score = (
            len(common)
            / len(query_words)
        ) * 100

        if score > 0:

            result = dict(row)

            result["score"] = round(
                score,
                2
            )

            # ------------------------------------------------
            # Try to standardize disease name
            # ------------------------------------------------

            disease = (

                row.get("label", "")

                or row.get("Label", "")

                or row.get("Disease", "")

                or row.get("disease", "")

                or ""
            )

            result["label"] = disease

            results.append(
                result
            )

    results.sort(
        key=lambda item:
        item.get(
            "score",
            0
        ),
        reverse=True
    )

    return results[:top_k]


# ============================================================
# SEARCH - DISEASE SYMPTOMS
# ============================================================

def search_disease_symptoms(
    query,
    top_k=5
):

    if not disease_symptoms_data:
        return []

    query_normalized = normalize(
        query
    )

    results = []

    for row in disease_symptoms_data:

        disease = (

            row.get("Disease", "")

            or row.get("disease", "")

            or ""
        )

        if not disease:
            continue

        disease_normalized = normalize(
            disease
        )

        score = 0

        # ----------------------------------------------------
        # Disease name match
        # ----------------------------------------------------

        if (
            query_normalized
            and query_normalized
            in disease_normalized
        ):

            score += 100

        else:

            query_words = set(
                query_normalized.split()
            )

            disease_words = set(
                disease_normalized.split()
            )

            common = (
                query_words
                & disease_words
            )

            if query_words:

                score += (
                    len(common)
                    / len(query_words)
                ) * 100

        # ----------------------------------------------------
        # Search symptoms too
        # ----------------------------------------------------

        row_text = " ".join(
            str(value)
            for value in row.values()
            if value
        )

        normalized_row = normalize(
            row_text
        )

        query_words = set(
            query_normalized.split()
        )

        row_words = set(
            normalized_row.split()
        )

        common = (
            query_words
            & row_words
        )

        if query_words:

            score += (
                len(common)
                / len(query_words)
            ) * 20

        if score > 0:

            result = dict(row)

            result["score"] = round(
                score,
                2
            )

            results.append(
                result
            )

    results.sort(
        key=lambda item:
        item.get(
            "score",
            0
        ),
        reverse=True
    )

    return results[:top_k]


# ============================================================
# SEARCH - PRECAUTIONS
# ============================================================

def search_precautions(
    query,
    top_k=5
):

    if not precaution_data:
        return []

    query_normalized = normalize(
        query
    )

    query_words = set(
        query_normalized.split()
    )

    results = []

    for row in precaution_data:

        row_text = " ".join(
            str(value)
            for value in row.values()
            if value
        )

        normalized_row = normalize(
            row_text
        )

        row_words = set(
            normalized_row.split()
        )

        common = (
            query_words
            & row_words
        )

        if not query_words:
            continue

        score = (
            len(common)
            / len(query_words)
        ) * 100

        if score > 0:

            result = dict(row)

            result["score"] = round(
                score,
                2
            )

            results.append(
                result
            )

    results.sort(
        key=lambda item:
        item.get(
            "score",
            0
        ),
        reverse=True
    )

    return results[:top_k]


# ============================================================
# GET DATASET COUNTS
# ============================================================

def get_dataset_status():

    return {

        "symptom2disease":
            len(symptom2disease_data),

        "disease_symptoms":
            len(disease_symptoms_data),

        "precautions":
            len(precaution_data),

        "medical_qa":
            len(medical_qa_data)
    }


# ============================================================
# TEST MEDICAL QA
# ============================================================

def test_medical_qa():

    print()
    print("=" * 70)
    print("TESTING MEDICAL QA SEARCH")
    print("=" * 70)

    test_questions = [

        "What are the symptoms of LCM?",

        "Who is at risk for LCM?",

        "What is fever?",

        "What are symptoms of headache?",

        "How can diabetes be prevented?"
    ]

    for question in test_questions:

        print()
        print(
            "QUESTION:",
            question
        )

        results = search_medical_qa(
            question,
            top_k=3
        )

        if not results:

            print(
                "No medical QA result found."
            )

            continue

        for index, result in enumerate(
            results,
            start=1
        ):

            print()
            print(
                f"Result {index}"
            )

            print(
                "Type:",
                result.get(
                    "qtype",
                    ""
                )
            )

            print(
                "Score:",
                result.get(
                    "score",
                    0
                )
            )

            print(
                "Question:",
                result.get(
                    "question",
                    ""
                )
            )

            answer = result.get(
                "answer",
                ""
            )

            print(
                "Answer:",
                answer[:300]
            )

    print()
    print("=" * 70)


# ============================================================
# LOAD DATASETS WHEN MODULE STARTS
# ============================================================

load_all_datasets()


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("HEALTH CHATBOT DATASET LOADER")
    print("=" * 70)

    print(
        "Dataset directory:",
        DATASET_DIR
    )

    print()

    print(
        "Dataset Status:"
    )

    status = get_dataset_status()

    for name, count in status.items():

        print(
            f"  {name}: {count}"
        )

    test_medical_qa()

    print()
    print(
        "DATASET LOADER TEST COMPLETED"
    )
    print("=" * 70)