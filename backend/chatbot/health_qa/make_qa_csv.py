"""
Creates datasets/medical_qa.csv (columns: qtype, question, answer) from knowledge.py.
The older MedicalQA search in chatbot/medical uses this file. It was missing before,
which is why many questions only got a generic reply.

Run from the project folder:
    python -m chatbot.health_qa.make_qa_csv
"""
import csv
import os

from chatbot.health_qa.knowledge import TOPICS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(BASE_DIR, "datasets", "medical_qa.csv")

if __name__ == "__main__":
    rows = 0
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["qtype", "question", "answer"])
        for t in TOPICS:
            answer = " ".join([t["short"], t["details"], t["advice"], t["doctor"]])
            for q in t["questions"]:
                writer.writerow([t["category"].lower(), q, answer])
                rows += 1
    print("wrote", rows, "rows to", OUT)
