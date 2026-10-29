"""
Train the ML and DL health bots and print how well they do.

Run from the project folder:
    python -m chatbot.health_qa.train
"""
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from chatbot.health_qa import bots


def evaluate(builder, texts, labels):
    # hold out 20% of the questions to test on unseen wording
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42)
    model = builder().fit(x_train, y_train)
    return round(accuracy_score(y_test, model.predict(x_test)), 4), len(x_train), len(x_test)


if __name__ == "__main__":
    texts, labels = bots.get_training_data()
    ml_acc, n_train, n_test = evaluate(bots.build_ml_model, texts, labels)
    dl_acc, _, _ = evaluate(bots.build_dl_model, texts, labels)
    print("topics:", len(set(labels)), "| train rows:", n_train, "| test rows:", n_test)
    print("ML  (TF-IDF + Logistic Regression) accuracy:", ml_acc)
    print("DL  (TF-IDF chars + neural network) accuracy:", dl_acc)

    bots.train_and_save("both")          # final models use all the data
    metrics = {"ml_accuracy": ml_acc, "dl_accuracy": dl_acc,
               "topics": len(set(labels)), "train_rows": n_train, "test_rows": n_test}
    with open(os.path.join(bots.MODEL_DIR, "health_qa_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("models saved in", bots.MODEL_DIR)
