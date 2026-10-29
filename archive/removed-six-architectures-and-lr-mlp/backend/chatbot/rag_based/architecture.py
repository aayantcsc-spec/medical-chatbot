"""
Architecture 5 - RAG-Based (retrieval + template composition).

1. Retrieve: TF-IDF over datasets/medical_qa.csv (question text counted twice, answer once), cosine
   similarity, top RETRIEVE_K records.
2. Augment/compose: the reply is assembled ONLY from the retrieved answers - the best record's
   answer, plus one sentence-level excerpt from each further record that adds new information -
   and every record used is listed as a numbered source.

There is no language model here. An optional generative step could be added later through an
environment-configured provider; until then this is described as retrieval + template composition.
"""
import csv
import os
import re
import threading

from chatbot.symptom.base import Architecture, DISCLAIMER, join
from chatbot.symptom.knowledge import DATA_DIR, norm

QA_FILE = os.path.join(DATA_DIR, "medical_qa.csv")
MIN_SIMILARITY = 0.20
RETRIEVE_K = 3


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


class RagArchitecture(Architecture):
    key = "rag_based"
    name = "RAG-Based"
    method = f"Retrieve top-{RETRIEVE_K} records from medical_qa.csv (TF-IDF), compose the reply only from them, cite sources"

    def __init__(self):
        self._index, self._error = None, None
        self._lock = threading.Lock()

    def _build(self):
        with self._lock:
            if self._index is not None or self._error:
                return
            if not os.path.isfile(QA_FILE):
                self._error = "datasets/medical_qa.csv is missing. Run: python -m chatbot.health_qa.make_qa_csv"
                return
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
            except ImportError:
                self._error = "scikit-learn is not installed (pip install -r requirements.txt)"
                return
            with open(QA_FILE, newline="", encoding="utf-8-sig") as f:
                rows = [dict(r, record_id=i + 1) for i, r in enumerate(csv.DictReader(f))
                        if (r.get("question") or "").strip() and (r.get("answer") or "").strip()]
            if not rows:
                self._error = "datasets/medical_qa.csv has no usable question/answer rows"
                return
            vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
            matrix = vec.fit_transform([f"{r['question']} {r['question']} {r['answer']}" for r in rows])
            self._index = {"rows": rows, "vec": vec, "matrix": matrix}

    def available(self):
        self._build()
        return self._index is not None, self._error

    def version(self):
        self._build()
        return f"qa-{len(self._index['rows'])}" if self._index else "unavailable"

    def retrieve(self, text, k=RETRIEVE_K):
        sims = (self._index["matrix"] @ self._index["vec"].transform([text]).T).toarray().ravel()
        order = sims.argsort()[::-1][:k]
        return [(self._index["rows"][i], float(sims[i])) for i in order]

    def _answer(self, text, context):
        hits = self.retrieve(text)
        evidence = [{"type": "retrieved_record", "record_id": r["record_id"], "question": r["question"],
                     "category": r.get("qtype"), "similarity": round(s, 4)} for r, s in hits]
        used = [(r, s) for r, s in hits if s >= MIN_SIMILARITY]
        if not used:
            best = hits[0][1] if hits else 0.0
            return {"status": "no_match", "evidence": evidence,
                    "response": join(f"I could not find a reference answer in my Q&A dataset that matches your question "
                                     f"(best similarity {best:.2f}, threshold {MIN_SIMILARITY}).",
                                     "Please rephrase, or ask a doctor or pharmacist.", DISCLAIMER)}
        best, _ = used[0]
        seen = {norm(s) for s in _sentences(best["answer"])}
        extra = []
        for r, _ in used[1:]:
            if norm(r["answer"]) == norm(best["answer"]):
                continue
            new = [s for s in _sentences(r["answer"]) if norm(s) not in seen]
            if new:
                extra.append((r, new[0]))
                seen.add(norm(new[0]))
        cited = [best] + [r for r, _ in extra]
        parts = [best["answer"].strip() + " [1]"]
        if extra:
            parts.append("Related information: " + " ".join(f"{s} [{i + 2}]" for i, (_, s) in enumerate(extra)))
        parts.append("Sources (medical_qa.csv): " + "; ".join(f"[{i + 1}] record {r['record_id']}: \"{r['question']}\""
                                                              for i, r in enumerate(cited)))
        parts.append(DISCLAIMER)
        return {"status": "ok", "response": join(*parts), "evidence": evidence,
                "extracted": {"records_used": [r["record_id"] for r in cited]}}
