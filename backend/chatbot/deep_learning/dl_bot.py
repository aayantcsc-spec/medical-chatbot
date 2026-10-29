"""
MediChat - Deep Learning Bot

Architecture:
    DistilBERT Transformer + sequence classification

Purpose:
    Classifies healthcare questions into MediChat's medical intents.

This bot is intentionally independent from the Machine Learning bot.
The ML architecture uses:
    TF-IDF + SVM

The Deep Learning architecture uses:
    DistilBERT

Both use the same medical intent labels so their performance
can be compared fairly.
"""

import os
import json

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)


class DeepLearningBot:

    def __init__(self):

        # ==========================================================
        # PROJECT PATHS
        # ==========================================================

        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        models_dir = os.path.join(base_dir, "models")

        self.model_dir = os.path.join(
            models_dir,
            "distilbert_medical"
        )

        self.metrics_path = os.path.join(
            models_dir,
            "dl_metrics.json"
        )

        # ==========================================================
        # CHECK MODEL
        # ==========================================================

        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(
                "\nDistilBERT model not found:\n"
                f"{self.model_dir}\n\n"
                "Run:\n"
                "chatbot/deep_learning/train_dl_model.py\n"
                "to train the Deep Learning model first."
            )

        # ==========================================================
        # DEVICE
        # ==========================================================

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        # ==========================================================
        # LOAD TOKENIZER
        # ==========================================================

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_dir
        )

        # ==========================================================
        # LOAD DISTILBERT
        # ==========================================================

        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_dir
        )

        self.model.to(self.device)
        self.model.eval()

        # ==========================================================
        # LOAD LABELS
        # ==========================================================

        self.labels = {}

        config_path = os.path.join(
            self.model_dir,
            "config.json"
        )

        if os.path.exists(config_path):

            try:

                with open(
                    config_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    config = json.load(f)

                self.labels = config.get(
                    "id2label",
                    {}
                )

            except Exception:
                self.labels = {}

        # ==========================================================
        # LOAD METRICS
        # ==========================================================

        self.metrics = None

        if os.path.exists(self.metrics_path):

            try:

                with open(
                    self.metrics_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    self.metrics = json.load(f)

            except Exception:
                self.metrics = None

        print(
            "Deep Learning model "
            "(DistilBERT) loaded successfully!"
        )

        print(
            f"Device: {self.device}"
        )

    # ==============================================================
    # LABEL CONVERSION
    # ==============================================================

    def _get_label(self, prediction_id):

        prediction_id = int(prediction_id)

        # HuggingFace normally stores id2label keys as strings
        label = self.labels.get(
            str(prediction_id)
        )

        if label is None:

            label = self.labels.get(
                prediction_id
            )

        if label is None:

            label = f"class_{prediction_id}"

        return str(label).strip()

    # ==============================================================
    # PREDICT
    #
    # Keeps the same contract used by bot_registry.py
    # ==============================================================

    def predict(self, text):

        result = self.predict_with_confidence(text)

        return result["label"]

    # ==============================================================
    # PREDICT WITH CONFIDENCE
    # ==============================================================

    def predict_with_confidence(self, text):

        text = str(text or "").strip()

        if not text:

            return {
                "label": "general_health",
                "label_display": "General Health",
                "confidence": 0.0,
                "confidence_percentage": 0.0
            }

        # ----------------------------------------------------------
        # TOKENIZATION
        # ----------------------------------------------------------

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        # ----------------------------------------------------------
        # MODEL PREDICTION
        # ----------------------------------------------------------

        with torch.no_grad():

            outputs = self.model(
                **inputs
            )

            probabilities = torch.softmax(
                outputs.logits,
                dim=-1
            )

            confidence, prediction = torch.max(
                probabilities,
                dim=-1
            )

        prediction_id = prediction.item()

        confidence_value = confidence.item()

        label = self._get_label(
            prediction_id
        )

        return {
            "label": label.lower(),
            "label_display": label,
            "confidence": round(
                confidence_value,
                4
            ),
            "confidence_percentage": round(
                confidence_value * 100,
                2
            )
        }

    # ==============================================================
    # MODEL INFORMATION
    # ==============================================================

    def model_info(self):

        num_classes = None

        try:

            num_classes = self.model.config.num_labels

        except Exception:
            pass

        return {

            "architecture":
                "Deep Learning",

            "model_type":
                "DistilBERT Transformer",

            "base_model":
                "distilbert-base-uncased",

            "num_classes":
                num_classes,

            "device":
                str(self.device),

            "held_out_metrics":
                self.metrics,

            "disclosure": (
                "This architecture uses a pre-trained "
                "DistilBERT transformer model for contextual "
                "medical intent classification. Unlike the "
                "Machine Learning architecture, which uses "
                "TF-IDF features with a traditional classifier, "
                "this model uses transformer-based contextual "
                "representations."
            )
        }


# ==============================================================
# DIRECT TEST
# ==============================================================

if __name__ == "__main__":

    print(
        "\nTesting MediChat Deep Learning Bot...\n"
    )

    try:

        bot = DeepLearningBot()

        print(
            "\nMODEL INFORMATION:"
        )

        print(
            json.dumps(
                bot.model_info(),
                indent=4
            )
        )

        test_messages = [

            "I have fever and headache",

            "What are the symptoms of dengue?",

            "What is paracetamol used for?",

            "What causes stomach pain?",

            "How can I prevent dengue?",

            "Since yesterday",

            "I have severe chest pain",

            "Could these symptoms be dengue?",

            "What can I do for a sore throat?",

            "What does high hemoglobin mean?",

            "What should I eat when I have fever?",

            "How can I improve my sleep?",

            "Can this medicine cause dizziness?",

            "When should I see a doctor for this cough?",

            "Which vaccines are recommended for adults?",

            "What does hypertension mean?"
        ]

        print(
            "\nPREDICTIONS:\n"
        )

        for message in test_messages:

            result = bot.predict_with_confidence(
                message
            )

            print(
                f"{message!r}\n"
                f"  → {result['label_display']}"
                f" ({result['confidence_percentage']}%)\n"
            )

    except Exception as error:

        print(
            "\nERROR:\n"
            f"{error}"
        )