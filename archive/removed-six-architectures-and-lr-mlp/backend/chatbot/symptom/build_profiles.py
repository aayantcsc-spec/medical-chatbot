"""
build_profiles.py - condense the disease/symptom matrix into a small retrieval index.

Source: datasets/Final_Augmented_dataset_Diseases_and_Symptoms.csv
        (one row per synthetic patient record: a 'diseases' column + one 0/1 column per symptom).
        The README of the original project names DiseaseAndSymptoms.csv (4,920 rows); that file is
        not in this archive, so this larger matrix is used instead and the substitution is recorded
        in the output's metadata.

Output: models/symptom/disease_profiles.json
        {disease: {"rows": n, "symptoms": [[symptom, share_of_rows], ...]}}  (share >= MIN_SHARE)

Only the standard library is used, and the file is streamed, so this runs in modest memory.

Run:  python -m chatbot.symptom.build_profiles
"""
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(BASE_DIR, "datasets", "Final_Augmented_dataset_Diseases_and_Symptoms.csv")
OUT_DIR = os.path.join(BASE_DIR, "models", "symptom")
OUT_FILE = os.path.join(OUT_DIR, "disease_profiles.json")

MIN_ROWS = 10          # diseases with fewer records are too sparse to profile
MIN_SHARE = 0.15       # keep symptoms present in at least 15% of a disease's records
MAX_SYMPTOMS = 25


def build(source=SOURCE, out_file=OUT_FILE):
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Missing dataset: {os.path.relpath(source, BASE_DIR)}")
    start = time.perf_counter()
    counts, totals = {}, {}
    sha = hashlib.sha256()
    with open(source, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        if not header or header[0].strip().lower() != "diseases":
            raise ValueError("Expected first column 'diseases'; found " + repr(header[:1]))
        symptoms = [h.strip() for h in header[1:]]
        sha.update(",".join(header).encode())
        n_rows = 0
        for row in reader:
            if not row:
                continue
            n_rows += 1
            disease = row[0].strip().lower()
            if not disease:
                continue
            totals[disease] = totals.get(disease, 0) + 1
            c = counts.setdefault(disease, {})
            for i, v in enumerate(row[1:]):
                if v == "1":
                    c[i] = c.get(i, 0) + 1

    profiles = {}
    for disease, total in totals.items():
        if total < MIN_ROWS:
            continue
        ranked = sorted(((symptoms[i], n / total) for i, n in counts[disease].items()), key=lambda x: -x[1])
        kept = [[s, round(share, 3)] for s, share in ranked if share >= MIN_SHARE][:MAX_SYMPTOMS]
        if kept:
            profiles[disease] = {"rows": total, "symptoms": kept}

    meta = {"source": os.path.relpath(source, BASE_DIR).replace("\\", "/"),
            "source_header_sha256": sha.hexdigest()[:12],
            "source_rows": n_rows, "source_diseases": len(totals), "source_symptom_columns": len(symptoms),
            "profiled_diseases": len(profiles), "min_rows": MIN_ROWS, "min_share": MIN_SHARE,
            "max_symptoms": MAX_SYMPTOMS, "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "build_seconds": round(time.perf_counter() - start, 1),
            "note": "Substitute for DiseaseAndSymptoms.csv, which is documented but absent from this archive."}
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    tmp = out_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "profiles": profiles}, f)
    os.replace(tmp, out_file)
    return meta


if __name__ == "__main__":
    m = build(*(sys.argv[1:2] or []))
    print(json.dumps(m, indent=2))
