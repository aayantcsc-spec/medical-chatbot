"""
chatbot/data/preprocessing.py

Reusable dataset preprocessing pipeline, added because none existed
in the project. This module NEVER modifies the original CSVs in
datasets/ -- it reads them, cleans a copy in memory, and writes the
result to datasets/processed/. Existing files (train.csv,
test_disease.csv, etc.) that were already hand-prepared are left
completely untouched; this pipeline produces its OWN, clearly
labeled, reproducible output alongside them.

Used for:
    - Symptom2Disease.csv   (text, label)
    - DiseaseAndSymptoms.csv
    - Disease precaution.csv
    - medical_qa.csv

Functions here are intentionally generic (operate on any DataFrame +
a list of text columns) so the same pipeline works across all four
datasets without duplicating logic per file.
"""

import os
import re
import sys
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd

DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets")
PROCESSED_DIR = os.path.join(DATASETS_DIR, "processed")


def normalize_text(text):
    """
    Same normalization convention already used by
    chatbot/data/dataset_loader.py's normalize(), duplicated here
    (not imported) so this module has no import-time dependency on
    the live retrieval stack and can be run standalone as a
    preprocessing/reporting script.
    """

    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""

    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_duplicates(df, subset=None):
    before = len(df)
    df = df.drop_duplicates(subset=subset)
    removed = before - len(df)
    return df, removed


def handle_missing_values(df, required_columns):
    before = len(df)
    df = df.dropna(subset=required_columns)
    for col in required_columns:
        df = df[df[col].astype(str).str.strip() != ""]
    removed = before - len(df)
    return df, removed


def normalize_text_columns(df, text_columns):
    df = df.copy()
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)
    return df


def standardize_label_column(df, label_column):
    """Lowercase + strip a label column so 'Fever', ' fever ', 'FEVER'
    are all treated as the same class."""

    df = df.copy()
    if label_column in df.columns:
        df[label_column] = (
            df[label_column].astype(str).str.strip().str.lower()
        )
    return df


def validate_columns(df, required_columns):
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing required column(s): {missing}. "
            f"Found columns: {list(df.columns)}"
        )


def train_val_test_split(df, train_frac=0.8, val_frac=0.1,
                          random_state=42):
    """
    Reproducible split (fixed random_state) into train/val/test.
    train_frac + val_frac must be < 1.0; the remainder is test.
    """

    if not 0 < train_frac < 1 or not 0 <= val_frac < 1:
        raise ValueError("train_frac/val_frac must be fractions of 1.0")
    if train_frac + val_frac >= 1.0:
        raise ValueError("train_frac + val_frac must leave room for a test split")

    shuffled = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)

    n = len(shuffled)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train_df = shuffled.iloc[:train_end]
    val_df = shuffled.iloc[train_end:val_end]
    test_df = shuffled.iloc[val_end:]

    return train_df, val_df, test_df


def preprocess_dataset(filename, text_columns, label_column=None,
                        split=False, train_frac=0.8, val_frac=0.1):
    """
    Full pipeline for one CSV in datasets/:
        load -> validate columns -> drop missing -> drop duplicates
             -> normalize text -> standardize label -> (optional split)
             -> save to datasets/processed/ -> return stats

    Does not touch the original file in datasets/.
    """

    source_path = os.path.join(DATASETS_DIR, filename)

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Dataset not found: {source_path}")

    df = pd.read_csv(source_path)
    original_count = len(df)

    required_columns = list(text_columns) + (
        [label_column] if label_column else []
    )
    validate_columns(df, required_columns)

    df, missing_removed = handle_missing_values(df, required_columns)
    df, duplicates_removed = remove_duplicates(df)

    df = normalize_text_columns(df, text_columns)

    if label_column:
        df = standardize_label_column(df, label_column)

    os.makedirs(PROCESSED_DIR, exist_ok=True)

    stats = {
        "source_file": filename,
        "original_rows": original_count,
        "rows_removed_missing": missing_removed,
        "rows_removed_duplicates": duplicates_removed,
        "final_rows": len(df),
        "columns": list(df.columns),
    }

    if label_column and label_column in df.columns:
        stats["num_classes"] = int(df[label_column].nunique())
        stats["class_distribution"] = (
            df[label_column].value_counts().to_dict()
        )

    base_name = os.path.splitext(filename)[0].replace(" ", "_")

    if split:
        train_df, val_df, test_df = train_val_test_split(
            df, train_frac=train_frac, val_frac=val_frac
        )

        train_df.to_csv(
            os.path.join(PROCESSED_DIR, f"{base_name}_train.csv"), index=False
        )
        val_df.to_csv(
            os.path.join(PROCESSED_DIR, f"{base_name}_val.csv"), index=False
        )
        test_df.to_csv(
            os.path.join(PROCESSED_DIR, f"{base_name}_test.csv"), index=False
        )

        stats["split"] = {
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
        }
    else:
        df.to_csv(
            os.path.join(PROCESSED_DIR, f"{base_name}_processed.csv"), index=False
        )

    return stats


# ============================================================
# PROJECT-SPECIFIC CONFIGURATION for the four datasets named in
# the project brief. Add an entry here to preprocess another file
# with the same pipeline.
# ============================================================

DATASET_CONFIGS = [
    {
        "filename": "Symptom2Disease.csv",
        "text_columns": ["text"],
        "label_column": "label",
        "split": True,
    },
    {
        "filename": "DiseaseAndSymptoms.csv",
        "text_columns": [
            c for c in
            ["Symptom_1", "Symptom_2", "Symptom_3"]
        ],
        "label_column": "Disease",
        "split": False,
    },
    {
        "filename": "Disease precaution.csv",
        "text_columns": [],
        "label_column": "Disease",
        "split": False,
    },
    {
        "filename": "medical_qa.csv",
        "text_columns": ["question", "answer"],
        "label_column": None,
        "split": False,
    },
]


def run_all_preprocessing(verbose=True):
    """Run the pipeline for every dataset in DATASET_CONFIGS and save
    a combined stats report to datasets/processed/preprocessing_report.json"""

    report = {}

    for config in DATASET_CONFIGS:
        filename = config["filename"]
        source_path = os.path.join(DATASETS_DIR, filename)

        if not os.path.exists(source_path):
            if verbose:
                print(f"[SKIP] {filename} not found in datasets/.")
            continue

        try:
            # Only pass columns that actually exist in this file, so
            # a dataset with a slightly different schema doesn't hard-fail.
            df_preview = pd.read_csv(source_path, nrows=1)
            text_columns = [
                c for c in config["text_columns"] if c in df_preview.columns
            ]

            stats = preprocess_dataset(
                filename,
                text_columns=text_columns,
                label_column=config["label_column"],
                split=config["split"],
            )

            report[filename] = stats

            if verbose:
                print(f"[OK] {filename}: {stats['original_rows']} -> "
                      f"{stats['final_rows']} rows "
                      f"(-{stats['rows_removed_missing']} missing, "
                      f"-{stats['rows_removed_duplicates']} duplicates)")

        except Exception as error:  # noqa: BLE001
            report[filename] = {"error": str(error)}
            if verbose:
                print(f"[ERROR] {filename}: {error}")

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    report_path = os.path.join(PROCESSED_DIR, "preprocessing_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    if verbose:
        print(f"\nReport saved to {report_path}")

    return report


if __name__ == "__main__":
    run_all_preprocessing()
