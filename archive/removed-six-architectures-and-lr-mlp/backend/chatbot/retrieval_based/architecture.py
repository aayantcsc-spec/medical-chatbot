"""
Architecture 4 - Retrieval-Based.

TF-IDF similarity search over structured disease records. One document per disease:
    * symptom profile from models/symptom/disease_profiles.json (built from the augmented
      disease/symptom matrix; each symptom repeated in proportion to how often it occurs), and/or
    * the dataset description (Disease_Description.csv) for the 41 described diseases.
Records for the same disease from both sources are merged via knowledge.canonical_disease().

The query is the user's text plus the dataset names of symptoms the NLP lexicon recognises in it
(so "throwing up" also searches "vomiting"). Cosine similarity ranks records; anything below
MIN_SIMILARITY is not shown. Nothing is trained on Symptom2Disease.csv, so evaluating this
architecture on that file involves no leakage.
"""
import threading

from chatbot.symptom.base import Architecture, DISCLAIMER, join
from chatbot.symptom.knowledge import diseases, profiles, canonical_disease, display_name, humanise, norm

MIN_SIMILARITY = 0.12      # documented relevance threshold (cosine, TF-IDF space)
TOP_K = 3


class RetrievalArchitecture(Architecture):
    key = "retrieval_based"
    name = "Retrieval-Based"
    method = f"TF-IDF cosine search over disease symptom profiles and descriptions (threshold {MIN_SIMILARITY})"
    predicts_label = True

    def __init__(self):
        self._index = None
        self._error = None
        self._lock = threading.Lock()

    def _build(self):
        with self._lock:
            if self._index is not None or self._error:
                return
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
            except ImportError:
                self._error = "scikit-learn is not installed (pip install -r requirements.txt)"
                return
            docs = {}
            for name, prof in profiles().get("profiles", {}).items():
                cid = canonical_disease(name) or "profile:" + name
                d = docs.setdefault(cid, {"id": cid, "name": display_name(cid) if not cid.startswith("profile:") else name.capitalize(),
                                          "symptoms": [], "description": "", "sources": []})
                d["symptoms"] = [s for s, _ in prof["symptoms"]]
                d["weights"] = prof["symptoms"]
                d["sources"].append(f"symptom profile ({prof['rows']} records)")
            for cid, rec in diseases().items():
                d = docs.setdefault(cid, {"id": cid, "name": rec["name"], "symptoms": [], "description": "", "sources": []})
                d["description"] = rec["description"]
                d["precautions"] = rec["precautions"]
                d["sources"].append("Disease_Description.csv")
            if not docs:
                self._error = "No disease records found. Run: python -m chatbot.symptom.build_profiles"
                return
            items = sorted(docs.values(), key=lambda d: d["id"])
            texts = []
            for d in items:
                sym = " ".join(" ".join([s] * (1 + int(share * 4))) for s, share in d.get("weights", []))
                texts.append(sym + " " + d["description"])
            vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
            matrix = vec.fit_transform(texts)
            self._index = {"items": items, "vec": vec, "matrix": matrix}

    def available(self):
        self._build()
        return self._index is not None, self._error

    def version(self):
        meta = profiles().get("meta") or {}
        return f"tfidf-{meta.get('source_header_sha256', 'noprofiles')}-{len(diseases())}desc"

    def _query(self, text):
        from chatbot.nlp_based.architecture import analyse, NEGATORS
        a = analyse(text)
        terms = [humanise(s["id"]) for s in a["symptoms"]]
        # drop negated wording ("no fever") so it does not pull in fever records
        toks, kept, skip = a["tokens"], [], 0
        for t in toks:
            if t in NEGATORS:
                skip = 3
                continue
            if skip:
                skip -= 1
                continue
            kept.append(t)
        return " ".join(kept) + " " + " ".join(terms), terms

    def search(self, text, k=TOP_K):
        self._build()
        if self._index is None:
            raise RuntimeError(self._error or "retrieval index unavailable")
        q, terms = self._query(text)
        sims = (self._index["matrix"] @ self._index["vec"].transform([q]).T).toarray().ravel()
        order = sims.argsort()[::-1][:k]
        qwords = set(norm(q).split())
        out = []
        for i in order:
            d = self._index["items"][i]
            matched = [s for s in d["symptoms"] if set(norm(s).split()) & qwords][:6]
            out.append({"record": d, "similarity": float(sims[i]), "matched": matched})
        return out, terms

    def _answer(self, text, context):
        hits, terms = self.search(text)
        evidence = [{"type": "retrieved_record", "record_id": h["record"]["id"], "record": h["record"]["name"],
                     "similarity": round(h["similarity"], 4), "matched_symptoms": h["matched"], "sources": h["record"]["sources"]}
                    for h in hits]
        relevant = [h for h in hits if h["similarity"] >= MIN_SIMILARITY]
        extracted = {"query_expansion": terms}
        if not relevant:
            best = hits[0]["similarity"] if hits else 0.0
            return {"status": "no_match", "evidence": evidence, "extracted": extracted,
                    "prediction": {"label": None, "label_name": None, "score": round(best, 4), "score_kind": "cosine similarity"},
                    "response": join(f"I could not find a disease record that matches your description closely enough "
                                     f"(best similarity {best:.2f}, threshold {MIN_SIMILARITY}).",
                                     "Could you describe your main symptoms in more detail - where, how long, and how severe?",
                                     DISCLAIMER)}
        top = relevant[0]
        lines = []
        for h in relevant:
            r = h["record"]
            why = f" - shared symptoms: {', '.join(h['matched'])}" if h["matched"] else ""
            lines.append(f"- **{r['name']}** (similarity {h['similarity']:.2f}){why}")
        parts = ["These records in the dataset have symptom profiles most similar to your description. "
                 "Similarity is word overlap, not a diagnosis:", "\n".join(lines)]
        desc = top["record"].get("description")
        if desc:
            parts.append(f"About {top['record']['name']}: {desc}")
        parts.append("Please see a doctor to find out what is actually causing your symptoms, especially if they are severe or getting worse.")
        parts.append(DISCLAIMER)
        rid = top["record"]["id"]
        return {"status": "ok", "response": join(*parts), "evidence": evidence, "extracted": extracted,
                "prediction": {"label": None if rid.startswith("profile:") else rid, "label_name": top["record"]["name"],
                               "score": round(top["similarity"], 4), "score_kind": "cosine similarity (TF-IDF), not a probability"}}
