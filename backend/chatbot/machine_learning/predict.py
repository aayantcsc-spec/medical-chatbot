import os
import pickle
import re


class ClassificationBot:

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    # This is an application safety threshold.
    #
    # IMPORTANT:
    # It does NOT mean that the model has medical accuracy of 20%.
    # It only determines whether a prediction is strong enough to
    # be used as a classification signal.
    MIN_CONFIDENCE = 0.20

    # Very short messages contain less information for the model.
    MIN_INPUT_WORDS = 2

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self):

        # ------------------------------------------------------
        # PROJECT ROOT
        # ------------------------------------------------------

        BASE_DIR = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".."
            )
        )

        # ------------------------------------------------------
        # MODEL DIRECTORY
        # ------------------------------------------------------

        MODEL_DIR = os.path.join(
            BASE_DIR,
            "models"
        )

        # ------------------------------------------------------
        # MODEL FILES
        # ------------------------------------------------------

        classifier_path = os.path.join(
            MODEL_DIR,
            "classifier.pkl"
        )

        tfidf_path = os.path.join(
            MODEL_DIR,
            "tfidf.pkl"
        )

        labels_path = os.path.join(
            MODEL_DIR,
            "classification_labels.pkl"
        )

        # ------------------------------------------------------
        # CHECK FILES
        # ------------------------------------------------------

        if not os.path.exists(classifier_path):

            raise FileNotFoundError(
                "classifier.pkl not found: "
                + classifier_path
            )

        if not os.path.exists(tfidf_path):

            raise FileNotFoundError(
                "tfidf.pkl not found: "
                + tfidf_path
            )

        # ------------------------------------------------------
        # LOAD CLASSIFIER
        # ------------------------------------------------------

        with open(
            classifier_path,
            "rb"
        ) as file:

            self.classifier = pickle.load(file)

        # ------------------------------------------------------
        # LOAD TF-IDF
        # ------------------------------------------------------

        with open(
            tfidf_path,
            "rb"
        ) as file:

            self.vectorizer = pickle.load(file)

        # ------------------------------------------------------
        # LOAD LABELS
        # ------------------------------------------------------

        self.labels = None

        if os.path.exists(labels_path):

            try:

                with open(
                    labels_path,
                    "rb"
                ) as file:

                    self.labels = pickle.load(file)

            except Exception:

                self.labels = None

        print(
            "Classification model loaded successfully!"
        )

    # ==========================================================
    # TEXT HELPERS
    # ==========================================================

    @staticmethod
    def clean_text(text):

        """
        Basic text normalization.

        The TF-IDF vectorizer already performs most of the
        preprocessing, so we intentionally keep this simple.
        """

        text = str(
            text or ""
        ).strip().lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text

    # ----------------------------------------------------------

    @staticmethod
    def count_words(text):

        words = re.findall(
            r"\b[a-zA-Z]{2,}\b",
            str(text or "")
        )

        return len(words)

    # ----------------------------------------------------------

    @staticmethod
    def display_label(label):

        """
        Converts an internal label into a readable label.
        """

        if not label:

            return "Health Question"

        text = str(
            label
        ).strip()

        if not text:

            return "Health Question"

        text = text.replace(
            "_",
            " "
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.title()

    # ==========================================================
    # BASIC PREDICTION
    # ==========================================================

    def predict(self, text):

        result = self.predict_with_confidence(
            text
        )

        return result["label"]

    # ==========================================================
    # CONFIDENCE LEVEL
    # ==========================================================

    @staticmethod
    def confidence_level(confidence):

        confidence = float(
            confidence or 0.0
        )

        if confidence >= 0.70:

            return "high"

        if confidence >= 0.40:

            return "medium"

        if confidence >= 0.20:

            return "low"

        return "very_low"

    # ==========================================================
    # SAFE RESULT
    # ==========================================================

    def _safe_result(
        self,
        status="uncertain",
        confidence=0.0,
        raw_label=None
    ):

        confidence = max(
            0.0,
            min(
                float(confidence),
                1.0
            )
        )

        raw_label = (
            str(raw_label).strip()
            if raw_label is not None
            else ""
        )

        return {

            # --------------------------------------------------
            # SAFE APPLICATION LABEL
            # --------------------------------------------------

            "label": "health_question",

            "label_display": "Health Question",

            # --------------------------------------------------
            # ORIGINAL MODEL OUTPUT
            # --------------------------------------------------

            "raw_label": (
                raw_label.lower()
                if raw_label
                else None
            ),

            "raw_label_display": (
                raw_label
                if raw_label
                else None
            ),

            # --------------------------------------------------
            # CONFIDENCE
            # --------------------------------------------------

            "confidence": round(
                confidence,
                4
            ),

            "confidence_percentage": round(
                confidence * 100,
                2
            ),

            # --------------------------------------------------
            # STATUS
            # --------------------------------------------------

            "is_confident": False,

            "prediction_status": status,

            "confidence_level": (
                self.confidence_level(
                    confidence
                )
            ),

            "confidence_threshold": (
                self.MIN_CONFIDENCE
            )
        }

    # ==========================================================
    # PREDICTION WITH CONFIDENCE
    # ==========================================================

    def predict_with_confidence(self, text):

        # ------------------------------------------------------
        # NORMALIZE INPUT
        # ------------------------------------------------------

        original_text = str(
            text or ""
        ).strip()

        clean_text = self.clean_text(
            original_text
        )

        # ------------------------------------------------------
        # EMPTY INPUT
        # ------------------------------------------------------

        if not clean_text:

            return self._safe_result(
                status="empty_input"
            )

        # ------------------------------------------------------
        # INPUT QUALITY
        # ------------------------------------------------------

        word_count = self.count_words(
            clean_text
        )

        # ------------------------------------------------------
        # TF-IDF TRANSFORMATION
        # ------------------------------------------------------

        try:

            vector = self.vectorizer.transform(
                [clean_text]
            )

        except Exception:

            return self._safe_result(
                status="vectorization_error"
            )

        # ------------------------------------------------------
        # CHECK WHETHER INPUT HAS KNOWN FEATURES
        # ------------------------------------------------------

        try:

            non_zero_features = int(
                vector.nnz
            )

        except Exception:

            non_zero_features = 0

        if non_zero_features == 0:

            return self._safe_result(
                status="unknown_input"
            )

        # ------------------------------------------------------
        # MODEL PREDICTION
        # ------------------------------------------------------

        try:

            prediction = self.classifier.predict(
                vector
            )[0]

        except Exception:

            return self._safe_result(
                status="prediction_error"
            )

        raw_label = str(
            prediction
        ).strip()

        # ------------------------------------------------------
        # CONFIDENCE
        # ------------------------------------------------------

        confidence = 0.0

        try:

            if hasattr(
                self.classifier,
                "predict_proba"
            ):

                probabilities = (
                    self.classifier
                    .predict_proba(vector)[0]
                )

                confidence = float(
                    max(probabilities)
                )

            elif hasattr(
                self.classifier,
                "decision_function"
            ):

                decision = (
                    self.classifier
                    .decision_function(vector)
                )

                try:

                    import numpy as np

                    values = np.asarray(
                        decision
                    ).ravel()

                    if len(values) > 0:

                        shifted = (
                            values - values.max()
                        )

                        exp_values = np.exp(
                            shifted
                        )

                        total = exp_values.sum()

                        if total > 0:

                            probabilities = (
                                exp_values / total
                            )

                            confidence = float(
                                probabilities.max()
                            )

                except Exception:

                    confidence = 0.0

        except Exception:

            confidence = 0.0

        # ------------------------------------------------------
        # SAFE CONFIDENCE RANGE
        # ------------------------------------------------------

        confidence = max(
            0.0,
            min(
                confidence,
                1.0
            )
        )

        confidence_percentage = round(
            confidence * 100,
            2
        )

        confidence_level = (
            self.confidence_level(
                confidence
            )
        )

        # ------------------------------------------------------
        # LOW-INFORMATION INPUT
        # ------------------------------------------------------
        #
        # Example:
        #
        # "fever"
        # "headache"
        #
        # Even if the classifier produces a disease label,
        # the application should not treat the result as a
        # reliable classification.
        #
        # We preserve the raw prediction for comparison and
        # evaluation.
        # ------------------------------------------------------

        if word_count < self.MIN_INPUT_WORDS:

            return {

                "label": "health_question",

                "label_display": "Health Question",

                "raw_label": raw_label.lower(),

                "raw_label_display": raw_label,

                "confidence": round(
                    confidence,
                    4
                ),

                "confidence_percentage": (
                    confidence_percentage
                ),

                "is_confident": False,

                "prediction_status": (
                    "insufficient_input"
                ),

                "confidence_level": (
                    confidence_level
                ),

                "confidence_threshold": (
                    self.MIN_CONFIDENCE
                ),

                "input_word_count": (
                    word_count
                ),

                "non_zero_features": (
                    non_zero_features
                )
            }

        # ------------------------------------------------------
        # CONFIDENCE DECISION
        # ------------------------------------------------------

        is_confident = (
            confidence >= self.MIN_CONFIDENCE
        )

        if is_confident:

            prediction_status = (
                "classification_available"
            )

            safe_label = raw_label.lower()

            safe_label_display = (
                self.display_label(
                    raw_label
                )
            )

        else:

            prediction_status = (
                "uncertain"
            )

            safe_label = (
                "health_question"
            )

            safe_label_display = (
                "Health Question"
            )

        # ------------------------------------------------------
        # RETURN COMPLETE RESULT
        # ------------------------------------------------------

        return {

            # ==================================================
            # SAFE APPLICATION OUTPUT
            # ==================================================

            "label": safe_label,

            "label_display": (
                safe_label_display
            ),

            # ==================================================
            # RAW MODEL OUTPUT
            # ==================================================

            "raw_label": raw_label.lower(),

            "raw_label_display": raw_label,

            # ==================================================
            # CONFIDENCE
            # ==================================================

            "confidence": round(
                confidence,
                4
            ),

            "confidence_percentage": (
                confidence_percentage
            ),

            "confidence_level": (
                confidence_level
            ),

            # ==================================================
            # STATUS
            # ==================================================

            "is_confident": (
                is_confident
            ),

            "prediction_status": (
                prediction_status
            ),

            # ==================================================
            # MODEL INFORMATION
            # ==================================================

            "confidence_threshold": (
                self.MIN_CONFIDENCE
            ),

            "input_word_count": (
                word_count
            ),

            "non_zero_features": (
                non_zero_features
            )
        }

    # ==========================================================
    # TOP PREDICTIONS
    # ==========================================================

    def get_top_predictions(
        self,
        text,
        top_n=3
    ):

        """
        Returns the highest probability classes.

        This is useful for:
        - comparison
        - analysis
        - research evaluation

        These predictions must NOT be displayed to users as
        confirmed medical diagnoses.
        """

        text = self.clean_text(
            text
        )

        if not text:

            return []

        try:

            vector = self.vectorizer.transform(
                [text]
            )

            if not hasattr(
                self.classifier,
                "predict_proba"
            ):

                return []

            probabilities = (
                self.classifier
                .predict_proba(vector)[0]
            )

            classes = (
                self.classifier.classes_
            )

            results = []

            for label, probability in zip(
                classes,
                probabilities
            ):

                results.append({

                    "label": str(
                        label
                    ),

                    "label_display": (
                        self.display_label(
                            label
                        )
                    ),

                    "confidence": round(
                        float(probability),
                        4
                    ),

                    "confidence_percentage": round(
                        float(probability) * 100,
                        2
                    )
                })

            results.sort(
                key=lambda item:
                    item["confidence"],
                reverse=True
            )

            return results[:max(1, int(top_n))]

        except Exception:

            return []

    # ==========================================================
    # MODEL INFORMATION
    # ==========================================================

    def model_info(self):

        info = {

            "model_type": type(
                self.classifier
            ).__name__,

            "vectorizer_type": type(
                self.vectorizer
            ).__name__,

            "confidence_threshold": (
                self.MIN_CONFIDENCE
            )
        }

        try:

            info["number_of_classes"] = len(
                self.classifier.classes_
            )

        except Exception:

            info["number_of_classes"] = None

        try:

            info["number_of_features"] = (
                len(
                    self.vectorizer
                    .get_feature_names_out()
                )
            )

        except Exception:

            info["number_of_features"] = None

        return info


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("MediChat - Machine Learning Classification Test")
    print("=" * 70)
    print()

    try:

        bot = ClassificationBot()

        print("MODEL INFORMATION")
        print("-" * 70)

        info = bot.model_info()

        for key, value in info.items():

            print(
                f"{key}: {value}"
            )

        print()
        print("=" * 70)
        print("PREDICTION TESTS")
        print("=" * 70)
        print()

        test_messages = [

            "hello",

            "fever",

            "I have fever",

            "I have a fever. What general steps can I take to care for myself?",

            "I have a high fever with chills. What should I do?",

            "I am coughing",

            "I have a headache",

            "I have itching and skin rash",

            "I have stomach pain",

            "I feel dizzy",

            "I have nausea",

            "I have chest pain",

            "I am feeling weak"

        ]

        for message in test_messages:

            print(
                "Input:",
                message
            )

            result = bot.predict_with_confidence(
                message
            )

            print(
                "Safe label:",
                result["label_display"]
            )

            print(
                "Raw prediction:",
                result["raw_label_display"]
            )

            print(
                "Confidence:",
                str(
                    result["confidence_percentage"]
                ) + "%"
            )

            print(
                "Confidence level:",
                result["confidence_level"]
            )

            print(
                "Status:",
                result["prediction_status"]
            )

            print(
                "Confident:",
                result["is_confident"]
            )

            print(
                "Input words:",
                result.get(
                    "input_word_count",
                    0
                )
            )

            print(
                "-" * 70
            )

        print()
        print(
            "Top predictions for:"
        )
        print(
            "I have fever and headache"
        )

        print()

        top_predictions = bot.get_top_predictions(
            "I have fever and headache",
            top_n=3
        )

        for index, item in enumerate(
            top_predictions,
            start=1
        ):

            print(
                f"{index}. "
                f"{item['label_display']} "
                f"- "
                f"{item['confidence_percentage']}%"
            )

        print()
        print("=" * 70)
        print(
            "ClassificationBot working!"
        )
        print("=" * 70)
        print()

    except Exception as error:

        print()
        print(
            "ClassificationBot error:"
        )

        print(
            error
        )

        print()