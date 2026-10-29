"""
MediChat - Deep Learning Model Training
=======================================

Project:
    Comparative Analysis of Health Chatbots Based on
    Framework and Architecture

Architectures:
    1. Rule-Based       -> Rules + Keywords
    2. Machine Learning -> TF-IDF + SVM
    3. Deep Learning    -> DistilBERT

IMPORTANT:
    Rule-Based, ML and DL all use the SAME intents.json
    so the comparison is based on the same intent classes.

Training source:
    chatbot/rule_based/intents.json

Output:
    models/distilbert_medical/
    models/dl_metrics.json
"""

import os
import json
import random

import numpy as np
import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support
)

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)


# ==============================================================
# PROJECT PATHS
# ==============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..")
)

INTENTS_FILE = os.path.join(
    PROJECT_ROOT,
    "chatbot",
    "rule_based",
    "intents.json"
)

MODELS_DIR = os.path.join(
    PROJECT_ROOT,
    "models"
)

MODEL_OUTPUT_DIR = os.path.join(
    MODELS_DIR,
    "distilbert_medical"
)

METRICS_FILE = os.path.join(
    MODELS_DIR,
    "dl_metrics.json"
)

LOG_DIR = os.path.join(
    PROJECT_ROOT,
    "logs"
)

os.makedirs(
    MODELS_DIR,
    exist_ok=True
)

os.makedirs(
    LOG_DIR,
    exist_ok=True
)


# ==============================================================
# SETTINGS
# ==============================================================

BASE_MODEL = "distilbert-base-uncased"

TEST_SIZE = 0.20

RANDOM_STATE = 42

MAX_LENGTH = 128

NUM_EPOCHS = 3

BATCH_SIZE = 8

LEARNING_RATE = 2e-5


# ==============================================================
# REPRODUCIBILITY
# ==============================================================

def set_seed(seed=42):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():

        torch.cuda.manual_seed_all(seed)


# ==============================================================
# LOAD INTENTS
# ==============================================================

def load_intents():

    print("\n==========================================")
    print("Loading MediChat intents")
    print("==========================================")

    if not os.path.exists(INTENTS_FILE):

        raise FileNotFoundError(
            f"\nintents.json not found:\n{INTENTS_FILE}"
        )

    with open(
        INTENTS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if "intents" not in data:

        raise ValueError(
            "intents.json must contain an 'intents' list."
        )

    rows = []

    for intent in data["intents"]:

        tag = str(
            intent.get("tag", "")
        ).strip()

        patterns = intent.get(
            "patterns",
            []
        )

        if not tag:
            continue

        if not isinstance(
            patterns,
            list
        ):
            continue

        for pattern in patterns:

            pattern = str(
                pattern
            ).strip()

            if pattern:

                rows.append({
                    "text": pattern,
                    "label": tag
                })

    if not rows:

        raise ValueError(
            "No training patterns found in intents.json."
        )

    df = pd.DataFrame(rows)

    df = df.drop_duplicates(
        subset=[
            "text",
            "label"
        ]
    )

    df = df.reset_index(
        drop=True
    )

    print(
        f"Training patterns: {len(df)}"
    )

    print(
        f"Number of intents: "
        f"{df['label'].nunique()}"
    )

    print("\nIntent distribution:")

    counts = (
        df["label"]
        .value_counts()
        .sort_index()
    )

    for label, count in counts.items():

        print(
            f"  {label}: {count}"
        )

    return df


# ==============================================================
# VALIDATE DATA
# ==============================================================

def validate_class_counts(df):

    counts = (
        df["label"]
        .value_counts()
    )

    too_small = counts[
        counts < 2
    ]

    if len(too_small) > 0:

        print("\nERROR:")
        print(
            "These intents have fewer than 2 patterns:"
        )

        for label, count in too_small.items():

            print(
                f"  {label}: {count}"
            )

        raise ValueError(
            "\nEach intent needs at least 2 patterns "
            "for stratified train/test splitting."
        )


# ==============================================================
# PREPARE LABELS
# ==============================================================

def prepare_labels(df):

    labels = sorted(
        df["label"]
        .unique()
        .tolist()
    )

    label2id = {
        label: index
        for index, label in enumerate(labels)
    }

    id2label = {
        index: label
        for index, label in enumerate(labels)
    }

    df = df.copy()

    df["label_id"] = (
        df["label"]
        .map(label2id)
        .astype(int)
    )

    return (
        df,
        label2id,
        id2label
    )


# ==============================================================
# TRAIN / TEST SPLIT
# ==============================================================

def split_data(df):

    print("\n==========================================")
    print("Creating train/test split")
    print("==========================================")

    train_df, test_df = train_test_split(

        df,

        test_size=TEST_SIZE,

        random_state=RANDOM_STATE,

        stratify=df["label_id"]
    )

    train_df = train_df.reset_index(
        drop=True
    )

    test_df = test_df.reset_index(
        drop=True
    )

    print(
        f"Training samples: {len(train_df)}"
    )

    print(
        f"Testing samples: {len(test_df)}"
    )

    return (
        train_df,
        test_df
    )


# ==============================================================
# CREATE HUGGING FACE DATASETS
# ==============================================================

def create_hf_datasets(
    train_df,
    test_df
):

    train_dataset = Dataset.from_pandas(

        train_df[
            ["text", "label_id"]
        ],

        preserve_index=False
    )

    test_dataset = Dataset.from_pandas(

        test_df[
            ["text", "label_id"]
        ],

        preserve_index=False
    )

    train_dataset = train_dataset.rename_column(
        "label_id",
        "labels"
    )

    test_dataset = test_dataset.rename_column(
        "label_id",
        "labels"
    )

    return (
        train_dataset,
        test_dataset
    )


# ==============================================================
# TOKENIZATION
# ==============================================================

def tokenize_datasets(
    train_dataset,
    test_dataset,
    tokenizer
):

    def tokenize(batch):

        return tokenizer(

            batch["text"],

            truncation=True,

            padding="max_length",

            max_length=MAX_LENGTH
        )

    print("\n==========================================")
    print("Tokenizing healthcare questions")
    print("==========================================")

    train_dataset = train_dataset.map(

        tokenize,

        batched=True
    )

    test_dataset = test_dataset.map(

        tokenize,

        batched=True
    )

    columns = [
        "input_ids",
        "attention_mask",
        "labels"
    ]

    if (
        "token_type_ids"
        in train_dataset.column_names
    ):

        columns.append(
            "token_type_ids"
        )

    train_dataset.set_format(

        type="torch",

        columns=columns
    )

    test_dataset.set_format(

        type="torch",

        columns=columns
    )

    return (
        train_dataset,
        test_dataset
    )


# ==============================================================
# METRICS
# ==============================================================

def compute_metrics(
    evaluation_result
):

    predictions = (
        evaluation_result.predictions
    )

    labels = (
        evaluation_result.label_ids
    )

    predicted_labels = np.argmax(

        predictions,

        axis=-1
    )

    accuracy = accuracy_score(

        labels,

        predicted_labels
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(

            labels,

            predicted_labels,

            average="weighted",

            zero_division=0
        )
    )

    return {

        "accuracy":
            float(accuracy),

        "precision_weighted":
            float(precision),

        "recall_weighted":
            float(recall),

        "f1_weighted":
            float(f1)
    }


# ==============================================================
# MAIN
# ==============================================================

def main():

    print("\n")
    print("==============================================")
    print("       MEDICHAT DEEP LEARNING TRAINING")
    print("==============================================")

    print(
        "\nArchitecture : Deep Learning"
    )

    print(
        "Model        : DistilBERT"
    )

    print(
        f"Base model   : {BASE_MODEL}"
    )

    print(
        f"Training data: {INTENTS_FILE}"
    )

    print(
        "Common source: intents.json"
    )

    print(
        f"Device       : "
        f"{'CUDA/GPU' if torch.cuda.is_available() else 'CPU'}"
    )

    set_seed(
        RANDOM_STATE
    )

    # ==========================================================
    # LOAD DATA
    # ==========================================================

    df = load_intents()

    # ==========================================================
    # VALIDATE DATA
    # ==========================================================

    validate_class_counts(
        df
    )

    # ==========================================================
    # LABEL ENCODING
    # ==========================================================

    (
        df,
        label2id,
        id2label
    ) = prepare_labels(
        df
    )

    # ==========================================================
    # SPLIT DATA
    # ==========================================================

    (
        train_df,
        test_df
    ) = split_data(
        df
    )

    # ==========================================================
    # CREATE HF DATASETS
    # ==========================================================

    (
        train_dataset,
        test_dataset
    ) = create_hf_datasets(

        train_df,

        test_df
    )

    # ==========================================================
    # TOKENIZER
    # ==========================================================

    print("\n==========================================")
    print("Loading DistilBERT tokenizer")
    print("==========================================")

    tokenizer = AutoTokenizer.from_pretrained(

        BASE_MODEL
    )

    # ==========================================================
    # TOKENIZE
    # ==========================================================

    (
        train_dataset,
        test_dataset
    ) = tokenize_datasets(

        train_dataset,

        test_dataset,

        tokenizer
    )

    # ==========================================================
    # MODEL
    # ==========================================================

    print("\n==========================================")
    print("Loading DistilBERT classifier")
    print("==========================================")

    model = (
        AutoModelForSequenceClassification
        .from_pretrained(

            BASE_MODEL,

            num_labels=len(label2id),

            label2id=label2id,

            id2label=id2label
        )
    )

    # ==========================================================
    # TRAINING ARGUMENTS
    # ==========================================================

    print("\n==========================================")
    print("Preparing training configuration")
    print("==========================================")

    # IMPORTANT:
    # Your installed Transformers version does not accept
    # warmup_ratio, so it has intentionally been removed.
    #
    # CPU is being used, therefore fp16 is disabled.

    training_args = TrainingArguments(

        output_dir=MODEL_OUTPUT_DIR,

        num_train_epochs=NUM_EPOCHS,

        per_device_train_batch_size=BATCH_SIZE,

        per_device_eval_batch_size=BATCH_SIZE,

        learning_rate=LEARNING_RATE,

        weight_decay=0.01,

        logging_dir=LOG_DIR,

        logging_steps=10,

        eval_strategy="epoch",

        save_strategy="epoch",

        load_best_model_at_end=True,

        metric_for_best_model="f1_weighted",

        greater_is_better=True,

        save_total_limit=1,

        report_to="none",

        fp16=False
    )

    # ==========================================================
    # TRAINER
    # ==========================================================

    trainer = Trainer(

        model=model,

        args=training_args,

        train_dataset=train_dataset,

        eval_dataset=test_dataset,

        processing_class=tokenizer,

        compute_metrics=compute_metrics
    )

    # ==========================================================
    # TRAIN
    # ==========================================================

    print("\n==========================================")
    print("STARTING DISTILBERT TRAINING")
    print("==========================================")

    print(
        "\nTraining source:"
    )

    print(
        "chatbot/rule_based/intents.json"
    )

    print(
        "\nTraining the model on the same "
        "intent patterns used by the other architectures."
    )

    print(
        "\nCPU training may take some time."
    )

    train_result = trainer.train()

    print("\n==========================================")
    print("DISTILBERT TRAINING COMPLETED")
    print("==========================================")

    # ==========================================================
    # EVALUATION
    # ==========================================================

    print("\n==========================================")
    print("HELD-OUT TEST EVALUATION")
    print("==========================================")

    evaluation = trainer.evaluate()

    accuracy = float(
        evaluation.get(
            "eval_accuracy",
            0.0
        )
    )

    precision = float(
        evaluation.get(
            "eval_precision_weighted",
            0.0
        )
    )

    recall = float(
        evaluation.get(
            "eval_recall_weighted",
            0.0
        )
    )

    f1 = float(
        evaluation.get(
            "eval_f1_weighted",
            0.0
        )
    )

    print(
        f"\nAccuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1 Score : {f1:.4f}"
    )

    # ==========================================================
    # SAVE MODEL
    # ==========================================================

    print("\n==========================================")
    print("SAVING DISTILBERT MODEL")
    print("==========================================")

    trainer.save_model(
        MODEL_OUTPUT_DIR
    )

    tokenizer.save_pretrained(
        MODEL_OUTPUT_DIR
    )

    print(
        f"\nModel saved to:\n"
        f"{MODEL_OUTPUT_DIR}"
    )

    # ==========================================================
    # SAVE METRICS
    # ==========================================================

    metrics = {

        "model":
            "DistilBERT",

        "architecture_label":
            "Deep Learning",

        "base_model":
            BASE_MODEL,

        "training_source":
            "chatbot/rule_based/intents.json",

        "training_source_type":
            "intent_patterns",

        "train_rows":
            int(len(train_df)),

        "test_rows":
            int(len(test_df)),

        "total_rows":
            int(len(df)),

        "num_classes":
            int(len(label2id)),

        "max_length":
            MAX_LENGTH,

        "epochs":
            NUM_EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "learning_rate":
            LEARNING_RATE,

        "accuracy":
            round(
                accuracy,
                4
            ),

        "precision_weighted":
            round(
                precision,
                4
            ),

        "recall_weighted":
            round(
                recall,
                4
            ),

        "f1_weighted":
            round(
                f1,
                4
            ),

        "training_loss":
            float(
                train_result.training_loss
            ),

        "device":
            str(
                trainer.args.device
            )
    }

    with open(

        METRICS_FILE,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            metrics,

            f,

            indent=4
        )

    print(
        f"\nMetrics saved to:\n"
        f"{METRICS_FILE}"
    )

    # ==========================================================
    # SANITY TEST
    # ==========================================================

    print("\n==========================================")
    print("SANITY TEST")
    print("==========================================")

    test_questions = [

        "hello",

        "I have fever",

        "I have a headache",

        "I am coughing",

        "I have stomach pain",

        "I feel dizzy",

        "I am vomiting",

        "I have chest pain",

        "What is paracetamol used for?",

        "I need to see a doctor",

        "How much water should I drink?",

        "I cannot sleep",

        "What should I eat?",

        "I want to exercise",

        "I have difficulty breathing"
    ]

    model.eval()

    device = next(
        model.parameters()
    ).device

    for question in test_questions:

        inputs = tokenizer(

            question,

            return_tensors="pt",

            truncation=True,

            padding=True,

            max_length=MAX_LENGTH
        )

        inputs = {

            key: value.to(device)

            for key, value in inputs.items()
        }

        with torch.no_grad():

            outputs = model(
                **inputs
            )

            probabilities = torch.softmax(

                outputs.logits,

                dim=-1
            )

            confidence, prediction = (
                torch.max(

                    probabilities,

                    dim=-1
                )
            )

        prediction_id = (
            prediction.item()
        )

        predicted_label = id2label[
            prediction_id
        ]

        confidence_value = (
            confidence.item() * 100
        )

        print(
            f"\nQuestion: {question}"
        )

        print(
            f"Prediction: {predicted_label}"
        )

        print(
            f"Confidence: "
            f"{confidence_value:.2f}%"
        )

    # ==========================================================
    # COMPLETE
    # ==========================================================

    print("\n")
    print("==============================================")
    print("DEEP LEARNING MODEL READY")
    print("==============================================")

    print(
        "\nArchitecture:"
    )

    print(
        "Deep Learning -> DistilBERT"
    )

    print(
        "\nCommon training source:"
    )

    print(
        "intents.json"
    )

    print(
        "\nModel folder:"
    )

    print(
        MODEL_OUTPUT_DIR
    )

    print(
        "\nMetrics file:"
    )

    print(
        METRICS_FILE
    )

    print(
        "\nNext step:"
    )

    print(
        "Run dl_bot.py to test predictions."
    )


# ==============================================================
# RUN
# ==============================================================

if __name__ == "__main__":

    main()