"""
MediChat - Machine Learning Training

Architecture:
    TF-IDF + Support Vector Machine (SVM)

Training source:
    chatbot/rule_based/intents.json

Important:
    Rule-Based, Machine Learning, and Deep Learning use
    the same intent patterns so their results can be
    compared fairly.

Machine Learning:
    TF-IDF + Linear SVM

Deep Learning:
    DistilBERT
"""

import os
import json
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..")
)

INTENTS_PATH = os.path.join(
    PROJECT_ROOT,
    "chatbot",
    "rule_based",
    "intents.json"
)

MODELS_DIR = os.path.join(
    PROJECT_ROOT,
    "models"
)

os.makedirs(
    MODELS_DIR,
    exist_ok=True
)


# ============================================================
# CHECK FILE
# ============================================================

if not os.path.exists(INTENTS_PATH):

    raise FileNotFoundError(
        "\nintents.json not found:\n"
        + INTENTS_PATH
    )


print("=" * 70)
print("MEDICHAT MACHINE LEARNING TRAINING")
print("=" * 70)

print("\nArchitecture:")
print("TF-IDF + Linear SVM")

print("\nTraining source:")
print(INTENTS_PATH)


# ============================================================
# LOAD INTENTS
# ============================================================

with open(
    INTENTS_PATH,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


intents = data.get(
    "intents",
    []
)


if not intents:

    raise ValueError(
        "No intents found in intents.json."
    )


# ============================================================
# CREATE TRAINING DATA
# ============================================================

texts = []
labels = []


for intent in intents:

    tag = str(
        intent.get("tag", "")
    ).strip()

    patterns = intent.get(
        "patterns",
        []
    )

    if not tag:
        continue

    for pattern in patterns:

        pattern = str(
            pattern
        ).strip()

        if not pattern:
            continue

        texts.append(
            pattern
        )

        labels.append(
            tag
        )


if not texts:

    raise ValueError(
        "No training patterns found in intents.json."
    )


print("\nTraining examples:")
print(len(texts))

print(
    "Number of intents:",
    len(set(labels))
)


print("\nIntent classes:")

for label in sorted(
    set(labels)
):

    count = labels.count(
        label
    )

    print(
        f"  {label}: {count}"
    )


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(

    texts,

    labels,

    test_size=0.20,

    random_state=42,

    stratify=labels
)


print("\n")
print("=" * 70)
print("DATA SPLIT")
print("=" * 70)

print(
    "Training examples:",
    len(X_train)
)

print(
    "Testing examples :",
    len(X_test)
)


# ============================================================
# TF-IDF
# ============================================================

print("\n")
print("=" * 70)
print("TF-IDF FEATURE EXTRACTION")
print("=" * 70)


vectorizer = TfidfVectorizer(

    lowercase=True,

    stop_words="english",

    ngram_range=(1, 2),

    max_features=10000,

    sublinear_tf=True
)


X_train_vectorized = (
    vectorizer.fit_transform(
        X_train
    )
)

X_test_vectorized = (
    vectorizer.transform(
        X_test
    )
)


print(
    "Vocabulary size:",
    len(
        vectorizer.vocabulary_
    )
)


# ============================================================
# LINEAR SVM
# ============================================================

print("\n")
print("=" * 70)
print("TRAINING LINEAR SVM")
print("=" * 70)


classifier = LinearSVC(
    C=1.0,
    random_state=42
)


classifier.fit(
    X_train_vectorized,
    y_train
)


print(
    "\nSVM model trained successfully."
)


# ============================================================
# HELD-OUT EVALUATION
# ============================================================

y_pred = classifier.predict(
    X_test_vectorized
)


accuracy = accuracy_score(
    y_test,
    y_pred
)


precision, recall, f1, _ = (
    precision_recall_fscore_support(

        y_test,

        y_pred,

        average="weighted",

        zero_division=0
    )
)


ml_metrics = {

    "model":
        "TF-IDF + Linear SVM",

    "architecture_label":
        "Machine Learning",

    "training_source":
        "chatbot/rule_based/intents.json",

    "train_rows":
        int(len(X_train)),

    "test_rows":
        int(len(X_test)),

    "num_classes":
        int(len(set(labels))),

    "accuracy":
        round(
            float(accuracy),
            4
        ),

    "precision_weighted":
        round(
            float(precision),
            4
        ),

    "recall_weighted":
        round(
            float(recall),
            4
        ),

    "f1_weighted":
        round(
            float(f1),
            4
        )
}


print("\n")
print("=" * 70)
print("HELD-OUT MACHINE LEARNING METRICS")
print("=" * 70)


for key, value in ml_metrics.items():

    print(
        f"{key}: {value}"
    )


# ============================================================
# TRAIN FINAL MODEL ON ALL INTENTS
# ============================================================

print("\n")
print("=" * 70)
print("TRAINING FINAL MODEL")
print("=" * 70)


final_vectorizer = TfidfVectorizer(

    lowercase=True,

    stop_words="english",

    ngram_range=(1, 2),

    max_features=10000,

    sublinear_tf=True
)


X_all_vectorized = (
    final_vectorizer.fit_transform(
        texts
    )
)


final_classifier = LinearSVC(

    C=1.0,

    random_state=42
)


final_classifier.fit(
    X_all_vectorized,
    labels
)


print(
    "Final SVM model trained successfully."
)


# ============================================================
# SAVE FILE PATHS
# ============================================================

classifier_path = os.path.join(
    MODELS_DIR,
    "classifier.pkl"
)

tfidf_path = os.path.join(
    MODELS_DIR,
    "tfidf.pkl"
)

model_path = os.path.join(
    MODELS_DIR,
    "model.pkl"
)

vectorizer_path = os.path.join(
    MODELS_DIR,
    "vectorizer.pkl"
)

labels_path = os.path.join(
    MODELS_DIR,
    "classification_labels.pkl"
)

metrics_path = os.path.join(
    MODELS_DIR,
    "ml_metrics.json"
)


# ============================================================
# SAVE CLASSIFIER
# ============================================================

with open(
    classifier_path,
    "wb"
) as file:

    pickle.dump(
        final_classifier,
        file
    )


# ============================================================
# SAVE TF-IDF
# ============================================================

with open(
    tfidf_path,
    "wb"
) as file:

    pickle.dump(
        final_vectorizer,
        file
    )


# ============================================================
# COMPATIBILITY FILES
# ============================================================

with open(
    model_path,
    "wb"
) as file:

    pickle.dump(
        final_classifier,
        file
    )


with open(
    vectorizer_path,
    "wb"
) as file:

    pickle.dump(
        final_vectorizer,
        file
    )


# ============================================================
# SAVE LABELS
# ============================================================

unique_labels = sorted(
    set(labels)
)


with open(
    labels_path,
    "wb"
) as file:

    pickle.dump(
        unique_labels,
        file
    )


# ============================================================
# SAVE METRICS
# ============================================================

with open(
    metrics_path,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        ml_metrics,
        file,
        indent=4
    )


# ============================================================
# TEST PREDICTIONS
# ============================================================

print("\n")
print("=" * 70)
print("MACHINE LEARNING TEST PREDICTIONS")
print("=" * 70)


test_questions = [

    "I have fever",

    "I have fever and headache",

    "What should I do for a cough?",

    "I have stomach pain",

    "I feel dizzy",

    "I am vomiting",

    "What medicine is used for fever?",

    "Should I see a doctor?",

    "How much water should I drink?",

    "How can I sleep better?",

    "I have severe chest pain",

    "What is hypertension?"
]


for question in test_questions:

    vector = (
        final_vectorizer.transform(
            [question]
        )
    )

    prediction = (
        final_classifier.predict(
            vector
        )[0]
    )

    # LinearSVC does not provide
    # predict_proba().
    # decision_function gives a
    # confidence-like score.

    try:

        decision_scores = (
            final_classifier
            .decision_function(
                vector
            )
        )

        confidence = float(
            max(
                decision_scores[0]
            )
        )

    except Exception:

        confidence = 0.0


    print(
        f"\nInput      : {question}"
    )

    print(
        f"Prediction : {prediction}"
    )

    print(
        f"Score      : {confidence:.4f}"
    )


# ============================================================
# FINISHED
# ============================================================

print("\n")
print("=" * 70)
print("MACHINE LEARNING TRAINING COMPLETE")
print("=" * 70)

print(
    "\nArchitecture: TF-IDF + Linear SVM"
)

print(
    "Training source: intents.json"
)

print(
    f"Number of intents: {len(unique_labels)}"
)

print(
    "\nSaved:"
)

print(
    classifier_path
)

print(
    tfidf_path
)

print(
    labels_path
)

print(
    metrics_path
)