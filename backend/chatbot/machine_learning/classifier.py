"""
classifier.py

Reusable machine-learning classification module
for MediChat.

Architecture:
    Machine Learning

Responsibilities:
- Load trained TF-IDF + classifier
- Predict intents
- Calculate confidence
- Detect uncertain predictions
- Return top predictions
- Provide model information

Important:
A low-confidence classification is NOT treated as a reliable
medical intent. The original prediction is still preserved for
research and comparison.
"""

import os
import pickle
import re


# =========================================================
# PATH CONFIGURATION
# =========================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.abspath(
    os.path.join(
        CURRENT_DIR,
        "..",
        ".."
    )
)

MODELS_DIR = os.path.join(
    PROJECT_DIR,
    "models"
)

TFIDF_PATH = os.path.join(
    MODELS_DIR,
    "tfidf.pkl"
)

CLASSIFIER_PATH = os.path.join(
    MODELS_DIR,
    "classifier.pkl"
)

LABELS_PATH = os.path.join(
    MODELS_DIR,
    "classification_labels.pkl"
)


# =========================================================
# CONFIDENCE CONFIGURATION
# =========================================================

# Predictions below this value are treated as uncertain.
#
# This does NOT change the trained model.
# It only prevents a weak prediction from being treated
# as a reliable intent by the application.
#
# Example:
#
# Bronchial Asthma = 0.0748
#
# 0.0748 < 0.20
#
# Therefore:
# prediction_status = "uncertain"
#
MIN_CONFIDENCE = 0.20


# =========================================================
# TEXT PREPROCESSING
# =========================================================

def clean_text(text):
    """
    Clean text before sending it to the ML model.
    """

    if text is None:
        return ""

    text = str(text).lower()

    # Remove apostrophes
    text = text.replace(
        "'",
        ""
    )

    # Remove punctuation
    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    # Remove extra spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# CLASSIFIER CLASS
# =========================================================

class HealthClassifier:
    """
    Main reusable ML classification class.

    It loads:

        tfidf.pkl
        classifier.pkl
        classification_labels.pkl

    and provides prediction functions.
    """

    def __init__(
        self,
        tfidf_path=TFIDF_PATH,
        classifier_path=CLASSIFIER_PATH,
        labels_path=LABELS_PATH
    ):

        self.tfidf_path = tfidf_path

        self.classifier_path = classifier_path

        self.labels_path = labels_path

        self.vectorizer = None

        self.model = None

        self.labels = None

        self.loaded = False

        self.load()

    # =====================================================
    # LOAD MODELS
    # =====================================================

    def load(self):
        """
        Load the trained ML components.
        """

        if not os.path.exists(
            self.tfidf_path
        ):

            raise FileNotFoundError(
                "TF-IDF model not found: "
                + self.tfidf_path
                + "\nRun train_model.py first."
            )

        if not os.path.exists(
            self.classifier_path
        ):

            raise FileNotFoundError(
                "Classifier model not found: "
                + self.classifier_path
                + "\nRun train_model.py first."
            )

        # -------------------------------------------------
        # Load TF-IDF vectorizer
        # -------------------------------------------------

        with open(
            self.tfidf_path,
            "rb"
        ) as file:

            self.vectorizer = pickle.load(
                file
            )

        # -------------------------------------------------
        # Load classifier
        # -------------------------------------------------

        with open(
            self.classifier_path,
            "rb"
        ) as file:

            self.model = pickle.load(
                file
            )

        # -------------------------------------------------
        # Load labels
        # -------------------------------------------------

        if os.path.exists(
            self.labels_path
        ):

            try:

                with open(
                    self.labels_path,
                    "rb"
                ) as file:

                    self.labels = pickle.load(
                        file
                    )

            except Exception:

                self.labels = (
                    self.model.classes_
                )

        else:

            self.labels = (
                self.model.classes_
            )

        self.loaded = True

    # =====================================================
    # CHECK STATUS
    # =====================================================

    def is_loaded(self):
        """
        Return True if the classifier is ready.
        """

        return (
            self.loaded
            and
            self.vectorizer is not None
            and
            self.model is not None
        )

    # =====================================================
    # TRANSFORM TEXT
    # =====================================================

    def transform(
        self,
        text
    ):
        """
        Convert text into TF-IDF features.
        """

        if not self.is_loaded():

            raise RuntimeError(
                "Classifier model is not loaded."
            )

        cleaned = clean_text(
            text
        )

        if not cleaned:

            raise ValueError(
                "Input message is empty."
            )

        return self.vectorizer.transform(
            [cleaned]
        )

    # =====================================================
    # PREDICT
    # =====================================================

    def predict(
        self,
        text
    ):
        """
        Predict one raw intent.

        This method preserves the original classifier
        prediction and does not apply the confidence
        threshold.

        Use predict_with_confidence() when application
        logic needs confidence handling.
        """

        vector = self.transform(
            text
        )

        prediction = self.model.predict(
            vector
        )

        return prediction[0]

    # =====================================================
    # PREDICT WITH CONFIDENCE
    # =====================================================

    def predict_with_confidence(
        self,
        text
    ):
        """
        Predict intent and confidence.

        Returns both the original classifier prediction
        and a safe interpretation of that prediction.

        Example:

        {
            "intent": "health_question",
            "raw_intent": "bronchial asthma",
            "confidence": 0.0748,
            "confidence_percentage": 7.48,
            "confidence_level": "Very Low",
            "is_confident": False,
            "prediction_status": "uncertain"
        }

        The raw prediction is preserved for evaluation.
        """

        vector = self.transform(
            text
        )

        # -------------------------------------------------
        # Raw prediction
        # -------------------------------------------------

        prediction = self.model.predict(
            vector
        )

        raw_intent = str(
            prediction[0]
        ).strip()

        # -------------------------------------------------
        # Probability
        # -------------------------------------------------

        confidence = 0.0

        try:

            probabilities = (
                self.model.predict_proba(
                    vector
                )[0]
            )

            confidence = float(
                max(probabilities)
            )

        except Exception:

            confidence = 0.0

        confidence = max(
            0.0,
            min(
                confidence,
                1.0
            )
        )

        # -------------------------------------------------
        # Confidence interpretation
        # -------------------------------------------------

        is_confident = (
            confidence >= MIN_CONFIDENCE
        )

        if is_confident:

            safe_intent = raw_intent

            prediction_status = (
                "confident"
            )

        else:

            # Do NOT present the weak classifier label
            # as a reliable medical intent.
            safe_intent = (
                "health_question"
            )

            prediction_status = (
                "uncertain"
            )

        return {

            # -------------------------------------------------
            # Application-safe intent
            # -------------------------------------------------

            "intent":
                safe_intent,

            # -------------------------------------------------
            # Original classifier result
            # -------------------------------------------------

            "raw_intent":
                raw_intent,

            # -------------------------------------------------
            # Confidence
            # -------------------------------------------------

            "confidence":
                round(
                    confidence,
                    4
                ),

            "confidence_percentage":
                round(
                    confidence * 100,
                    2
                ),

            # -------------------------------------------------
            # Status
            # -------------------------------------------------

            "confidence_level":
                self.confidence_level(
                    confidence
                ),

            "is_confident":
                is_confident,

            "prediction_status":
                prediction_status,

            "confidence_threshold":
                MIN_CONFIDENCE
        }

    # =====================================================
    # TOP PREDICTIONS
    # =====================================================

    def top_predictions(
        self,
        text,
        top_n=5
    ):
        """
        Return the most probable raw intents.

        These are useful for research/evaluation.
        """

        vector = self.transform(
            text
        )

        try:

            probabilities = (
                self.model.predict_proba(
                    vector
                )[0]
            )

        except Exception:

            predicted = self.model.predict(
                vector
            )[0]

            return [
                {
                    "intent":
                        str(predicted),

                    "confidence":
                        1.0,

                    "confidence_percentage":
                        100.0
                }
            ]

        classes = (
            self.model.classes_
        )

        results = []

        for index, probability in enumerate(
            probabilities
        ):

            results.append({

                "intent":
                    str(
                        classes[index]
                    ),

                "confidence":
                    round(
                        float(
                            probability
                        ),
                        4
                    ),

                "confidence_percentage":
                    round(
                        float(
                            probability
                        ) * 100,
                        2
                    )

            })

        results.sort(
            key=lambda item:
                item["confidence"],
            reverse=True
        )

        return results[
            :top_n
        ]

    # =====================================================
    # CONFIDENCE LEVEL
    # =====================================================

    @staticmethod
    def confidence_level(
        confidence
    ):
        """
        Convert probability into a simple
        confidence category.
        """

        try:

            confidence = float(
                confidence
            )

        except Exception:

            confidence = 0.0

        if confidence >= 0.80:

            return "Very High"

        if confidence >= 0.65:

            return "High"

        if confidence >= 0.50:

            return "Medium"

        if confidence >= 0.35:

            return "Low"

        return "Very Low"

    # =====================================================
    # FULL ANALYSIS
    # =====================================================

    def analyze(
        self,
        text,
        top_n=5
    ):
        """
        Perform complete classification analysis.
        """

        result = (
            self.predict_with_confidence(
                text
            )
        )

        confidence = result[
            "confidence"
        ]

        return {

            "input":
                text,

            "intent":
                result["intent"],

            "raw_intent":
                result["raw_intent"],

            "confidence":
                confidence,

            "confidence_percentage":
                result[
                    "confidence_percentage"
                ],

            "confidence_level":
                result[
                    "confidence_level"
                ],

            "is_confident":
                result[
                    "is_confident"
                ],

            "prediction_status":
                result[
                    "prediction_status"
                ],

            "confidence_threshold":
                result[
                    "confidence_threshold"
                ],

            "top_predictions":
                self.top_predictions(
                    text,
                    top_n
                )
        }

    # =====================================================
    # GET MODEL INFORMATION
    # =====================================================

    def model_info(self):
        """
        Return information about the trained model.
        """

        if not self.is_loaded():

            return {
                "loaded": False
            }

        try:

            number_of_classes = len(
                self.model.classes_
            )

        except Exception:

            number_of_classes = 0

        try:

            number_of_features = len(
                self.vectorizer.get_feature_names_out()
            )

        except Exception:

            number_of_features = 0

        return {

            "loaded":
                True,

            "model_type":
                type(
                    self.model
                ).__name__,

            "vectorizer":
                type(
                    self.vectorizer
                ).__name__,

            "number_of_classes":
                number_of_classes,

            "number_of_features":
                number_of_features,

            "confidence_threshold":
                MIN_CONFIDENCE,

            "classes":
                list(
                    self.model.classes_
                )
        }


# =========================================================
# HELPER FUNCTION
# =========================================================

def classify(
    message
):
    """
    Simple helper function.

    Example:

        result = classify(
            "I have fever"
        )
    """

    classifier = HealthClassifier()

    return classifier.predict_with_confidence(
        message
    )


# =========================================================
# INTERACTIVE TEST
# =========================================================

def run_test():

    print(
        "=" * 60
    )

    print(
        "MEDICHAT MACHINE LEARNING CLASSIFIER"
    )

    print(
        "=" * 60
    )

    try:

        classifier = HealthClassifier()

    except Exception as error:

        print(
            "\nError:",
            error
        )

        return

    print(
        "\nModel information:"
    )

    info = classifier.model_info()

    print(
        "Loaded:",
        info["loaded"]
    )

    print(
        "Model:",
        info["model_type"]
    )

    print(
        "Vectorizer:",
        info["vectorizer"]
    )

    print(
        "Number of intents:",
        info["number_of_classes"]
    )

    print(
        "Number of features:",
        info["number_of_features"]
    )

    print(
        "Confidence threshold:",
        f"{MIN_CONFIDENCE * 100:.0f}%"
    )

    print(
        "\nType 'exit' to stop."
    )

    while True:

        message = input(
            "\nYou: "
        ).strip()

        if message.lower() in [
            "exit",
            "quit"
        ]:

            print(
                "Bot: Goodbye!"
            )

            break

        if not message:

            print(
                "Bot: Please enter a message."
            )

            continue

        try:

            result = classifier.analyze(
                message
            )

            print(
                "\nRaw ML Prediction:",
                result["raw_intent"]
            )

            print(
                "Application Intent:",
                result["intent"]
            )

            print(
                "Confidence:",
                f"{result['confidence_percentage']:.2f}%"
            )

            print(
                "Confidence Level:",
                result["confidence_level"]
            )

            print(
                "Prediction Status:",
                result["prediction_status"]
            )

            print(
                "Confident:",
                result["is_confident"]
            )

            print(
                "\nTop Predictions:"
            )

            for item in result[
                "top_predictions"
            ]:

                print(
                    f"{item['intent']:<30}"
                    f"{item['confidence_percentage']:>7.2f}%"
                )

        except Exception as error:

            print(
                "Prediction error:",
                error
            )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    run_test()