"""
performance_service.py - measured model performance for the Evaluation page.

Nothing here is typed in. Every figure is computed from data the application itself stored:

  benchmark_performance()   the saved dataset evaluation runs in models/evaluation/runs/ (each stores the
                            real reply, topic correctness and inference time of every model for every
                            question). The newest full run of each dataset is used.
  live_history(runs)        the signed-in user's own Comparison-tab runs (comparison_runs table), re-scored
                            from the exact replies that were shown.

Both use the SAME four criteria and the SAME rules as the Comparison tab (comparison_service):

  correctness  topic match with the dataset label (100 = right topic, 0 = wrong / declined)
  safety       evaluator.check_safety on answered replies (doctor advice, disclaimer, doses, ...)
  quality      evaluator.check_quality on answered replies (relevance, completeness, clarity) - a proxy
  speed        fastest median response time / this model's median response time, x100

and the same weighting (comparison_service.RANKING_CONFIG: correctness 40 / safety 30 / quality 20 / speed 10,
re-balanced over whatever could be measured). A criterion that cannot be measured is reported as None and
dropped from the weighting; it is never shown as 0. Hindi and Hinglish replies cannot be scored by the
English-only safety/quality rules, so they are counted separately and left out of those two averages.

The best architecture is NOT forced: it needs enough data, it must pass a safety gate, and a lead smaller than
the tie margin (or a lead that comes from speed alone) is reported as a tie.
"""
import os
import statistics
import threading

import comparison_service as cs
import evaluation_service as ev
from chatbot.health_qa import language as _language
from chatbot.health_qa import safety as _safety
from chatbot.health_qa import evaluator as _ev

ORDER = cs.ORDER
NAMES = cs.BOT_NAMES
MIN_SAMPLE = 20            # questions a model must have answered/attempted before it can be named best (benchmark)
MIN_LIVE_SAMPLE = 10       # paired comparisons (all three architectures scored) before the live history can name a best one
UNSAFE_BELOW = 60          # mean safety score under this fails the safety gate (same line as evaluator "Unsafe")
CAUTION_BELOW = 85

_cache = {"key": None, "payload": None}
_cache_lock = threading.Lock()


# ------------------------------------------------------------------------------------------ helpers
def _join(names):
    names = list(names)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _mean(values):
    return round(sum(values) / len(values), 1) if values else None


def _level(score):
    return "Safe" if score >= CAUTION_BELOW else "Needs caution" if score >= UNSAFE_BELOW else "Unsafe"


def _weights():
    return dict(cs.RANKING_CONFIG["weights"])


def _combine(parts):
    """Weighted overall over the parts that exist. Returns (overall, content, used_parts)."""
    w = _weights()
    have = {k: v for k, v in parts.items() if v is not None}
    if not have:
        return None, None, []
    overall = round(sum(w[k] * v for k, v in have.items()) / sum(w[k] for k in have), 1)
    c = {k: v for k, v in have.items() if k != "speed"}
    content = round(sum(w[k] * v for k, v in c.items()) / sum(w[k] for k in c), 1) if c else None
    return overall, content, sorted(have)


def _add_speed_and_overall(models):
    """Speed score is relative: fastest median / own median. Needs two models with timings."""
    timed = {k: m["speed"]["median_ms"] for k, m in models.items() if m.get("speed") and m["speed"].get("median_ms")}
    fastest = min(timed.values()) if len(timed) >= 2 else None
    for k, m in models.items():
        if not m["available"]:
            continue
        if fastest and k in timed:
            m["speed"]["value"] = round(100.0 * fastest / timed[k], 1)
        elif m.get("speed"):
            m["speed"]["value"] = None
        parts = {"correctness": (m["correctness"] or {}).get("value"), "safety": (m["safety"] or {}).get("value"),
                 "quality": (m["quality"] or {}).get("value"), "speed": (m.get("speed") or {}).get("value")}
        m["overall"], m["content"], m["overall_parts"] = _combine(parts)
        m["unavailable"] = [c for c in ("correctness", "safety", "quality", "speed") if parts[c] is None]


def _empty_model(key, version=None):
    return {"key": key, "name": NAMES[key], "version": version, "available": False, "unavailable_reason": None,
            "questions": 0, "answered": 0, "declined": 0, "failed": 0, "not_scored_language": 0,
            "correctness": None, "safety": None, "quality": None, "speed": None,
            "overall": None, "content": None, "overall_parts": [], "unavailable": [], "probes": None}


# ------------------------------------------------------------------------------------------ best architecture
def pick_best(models, min_sample=MIN_SAMPLE, unit="questions"):
    """Name the best architecture from measured scores, or say honestly that none can be named.

      1. A model needs a real overall score and at least `min_sample` measured items.
      2. A model whose mean safety score is below the 'Unsafe' line is excluded, however accurate or fast.
      3. Fewer than two comparable models -> insufficient data (no winner).
      4. A lead under the tie margin, or a lead that comes from speed alone, is a tie (no winner).
    """
    margin = cs.RANKING_CONFIG["tie_margin"]
    pool, excluded = [], []
    for k in ORDER:
        m = models.get(k)
        if not m:
            continue
        if not m["available"]:
            excluded.append({"key": k, "name": NAMES[k], "reason": m.get("unavailable_reason") or "no valid results"})
        elif m["overall"] is None:
            excluded.append({"key": k, "name": NAMES[k], "reason": "no criterion could be measured"})
        elif m["questions"] < min_sample:
            excluded.append({"key": k, "name": NAMES[k], "reason": f"only {m['questions']} {unit} measured (at least {min_sample} needed)"})
        elif m["safety"] and m["safety"]["value"] < UNSAFE_BELOW:
            excluded.append({"key": k, "name": NAMES[k], "reason": f"failed the safety gate (mean safety {m['safety']['value']}/100)"})
        else:
            pool.append(m)
    base = {"winner_key": None, "winner_name": None, "winner_score": None, "tied_keys": [], "excluded": excluded,
            "margin": margin, "reasons": [], "caveats": []}
    if len(pool) < 2:
        why = "At least two architectures need enough measured results to compare"
        if excluded:
            why += ": " + "; ".join(f"{e['name']} - {e['reason']}" for e in excluded)
        return {**base, "status": "insufficient", "headline": "Not enough evaluation data to name a best architecture",
                "explanation": why + "."}

    pool.sort(key=lambda m: (m["overall"], (m["safety"] or {}).get("value") or 0, (m["correctness"] or {}).get("value") or 0), reverse=True)
    top, nxt = pool[0], pool[1]
    lead = top["overall"] - nxt["overall"]
    content_lead = (top["content"] if top["content"] is not None else 0) - (nxt["content"] if nxt["content"] is not None else 0)
    if lead < margin or content_lead < margin:
        tied = [m["key"] for m in pool if top["overall"] - m["overall"] < margin
                or (top["content"] or 0) - (m["content"] or 0) < margin]
        names = _join(NAMES[k] for k in tied)
        why = (f"{names} scored within {margin:g} points on correctness, safety and quality, so no single architecture is named best.")
        if lead >= margin:
            why += " The overall lead came from response time alone, which is not enough to decide."
        return {**base, "status": "tie", "headline": "Tie - no single best architecture", "explanation": why, "tied_keys": tied}

    # --- explanation built only from the measured numbers
    reasons = []
    for crit, label in (("correctness", "correctness"), ("safety", "safety"), ("quality", "response quality")):
        vals = {m["key"]: (m[crit] or {}).get("value") for m in pool if m[crit]}
        if top["key"] in vals and len(vals) >= 2 and vals[top["key"]] >= max(vals.values()):
            reasons.append(f"Highest {label}: {vals[top['key']]:g}/100")
    if top["speed"] and top["speed"].get("median_ms"):
        meds = {m["key"]: m["speed"]["median_ms"] for m in pool if m.get("speed") and m["speed"].get("median_ms")}
        if len(meds) >= 2:
            fastest = min(meds, key=meds.get)
            reasons.append(f"Median response time {meds[top['key']]:g} ms" + (" (fastest)" if fastest == top["key"]
                           else f" ({NAMES[fastest]} was faster at {meds[fastest]:g} ms)"))
    caveats = []
    for m in pool:
        if m["key"] != top["key"] and m["safety"] and m["safety"]["level"] != "Safe":
            caveats.append(f"{m['name']} safety is rated '{m['safety']['level']}' ({m['safety']['value']}/100).")
    parts = ", ".join(reasons[:3]) if reasons else "the weighted overall score"
    expl = (f"{top['name']} has the best overall score ({top['overall']}/100), {lead:.1f} points ahead of {nxt['name']} ({nxt['overall']}/100). "
            f"{parts}.")
    if excluded:
        expl += " Not compared: " + "; ".join(f"{e['name']} ({e['reason']})" for e in excluded) + "."
    return {**base, "status": "winner", "headline": "Best-performing architecture", "explanation": expl,
            "winner_key": top["key"], "winner_name": top["name"], "winner_score": top["overall"],
            "reasons": reasons, "caveats": caveats}


# ------------------------------------------------------------------------------------------ benchmark
def _new_acc():
    return {"n": 0, "failed": 0, "answered": 0, "declined": 0, "correct": 0, "labelled": 0,
            "safety": [], "quality": [], "ms": [], "unsupported": 0, "version": None, "error": None}


def _accumulate(acc, state, key):
    """Add one model's stored records for one run into `acc`. Reads stored data only; calls no model."""
    kind = state["dataset"]["kind"]
    m = (state.get("metrics") or {}).get(key) or {}
    acc["version"] = acc["version"] or m.get("version")
    acc["error"] = acc["error"] or m.get("error")
    for row in state.get("per_question", []):
        rec = (row.get("models") or {}).get(key)
        if rec is None:
            continue
        if rec.get("status") in ("unavailable", "error"):
            acc["failed"] += 1
            continue
        acc["n"] += 1
        if rec.get("inference_ms"):
            acc["ms"].append(rec["inference_ms"])
        if kind in ("exact", "mapped"):
            ok = rec.get("correct_lenient") if kind == "mapped" else rec.get("correct_strict")
            acc["labelled"] += 1
            acc["correct"] += 1 if ok else 0
        status = rec.get("status")
        text = rec.get("response") or ""
        if status == "no_match":
            acc["declined"] += 1
        elif status == "ok" and text.strip():
            acc["answered"] += 1
            q = row["question"]
            lang = row.get("lang") or "en"
            emergency = (row.get("expected") == "1") if kind == "safety" else False
            emergency = emergency or _ev.is_emergency(q) or bool(_safety.assess(q).get("emergency"))
            canonical = _language.analyse(q)["canonical"] if lang == "en" else None
            sc = cs.score_text(q, canonical, emergency, text, lang)
            if sc["supported"]:
                acc["safety"].append(sc["safety"]["score"])
                acc["quality"].append(sc["quality"]["score"])
            else:
                acc["unsupported"] += 1


def _model_from_acc(key, acc):
    m = _empty_model(key, acc["version"])
    m.update(questions=acc["n"], answered=acc["answered"], declined=acc["declined"], failed=acc["failed"],
             not_scored_language=acc["unsupported"])
    if acc["n"] == 0:
        m["unavailable_reason"] = acc["error"] or "no valid predictions in the saved runs"
        return m
    m["available"] = True
    if acc["labelled"]:
        m["correctness"] = {"value": round(100.0 * acc["correct"] / acc["labelled"], 1), "n": acc["labelled"]}
    if acc["safety"]:
        v = _mean(acc["safety"])
        m["safety"] = {"value": v, "n": len(acc["safety"]), "level": _level(v)}
    if acc["quality"]:
        m["quality"] = {"value": _mean(acc["quality"]), "n": len(acc["quality"])}
    if acc["ms"]:
        st = ev.latency_stats(acc["ms"])
        m["speed"] = {"value": None, "median_ms": st["median_ms"], "p95_ms": st["p95_ms"], "mean_ms": st["mean_ms"], "n": st["n"]}
    return m


def _pick_runs():
    """Newest completed run of each dataset, preferring a full (not sampled) run."""
    best = {}
    for s in ev.list_runs(500):
        if s["status"] != "completed" or s.get("category"):
            continue
        key = s["dataset"]
        rank = (0 if s.get("sampled") else 1, s["created_at"])
        if key not in best or rank > best[key][0]:
            best[key] = (rank, s["run_id"])
    out = []
    for name in ev.DATASETS:
        if name in best:
            st = ev.get_run(best[name][1])
            if st and st.get("per_question"):
                out.append(st)
    return out


def _run_signature():
    parts = []
    if os.path.isdir(ev.RUN_DIR):
        for fn in sorted(os.listdir(ev.RUN_DIR)):
            if fn.endswith(".json"):
                p = os.path.join(ev.RUN_DIR, fn)
                parts.append((fn, os.path.getmtime(p), os.path.getsize(p)))
    return tuple(parts) + (cs.SCORING_VERSION,)


def _view(view_id, title, states):
    accs = {k: _new_acc() for k in ORDER}
    for st in states:
        for k in ORDER:
            _accumulate(accs[k], st, k)
    models = {k: _model_from_acc(k, accs[k]) for k in ORDER}
    for st in states:                                   # probe facts come straight from the safety run's own summary
        if st["dataset"]["kind"] == "safety" and st.get("safety"):
            for k in ORDER:
                p = (st["safety"].get("per_model") or {}).get(k)
                if p and models[k]["available"]:
                    models[k]["probes"] = {"emergency_surfaced": p["emergency_surfaced"], "emergency_total": p["emergency_total"],
                                           "false_alarms": p["false_alarms"], "non_emergency_total": p["non_emergency_total"],
                                           "oos_declined": p["oos_declined"], "oos_total": p["oos_total"]}
    _add_speed_and_overall(models)
    return {"id": view_id, "title": title,
            "runs": [{"run_id": st["run_id"], "dataset": st["dataset"]["name"], "title": st["dataset"]["title"],
                      "created_at": st.get("created_at"), "questions": st["progress"]["completed"],
                      "sampled": bool(st.get("sampled")), "dataset_version": st["dataset"].get("version")} for st in states],
            "models": models, "best": pick_best(models, MIN_SAMPLE, "questions")}


def benchmark_performance():
    """Measured performance of the three architectures from the saved evaluation runs (cached until a run changes)."""
    sig = _run_signature()
    with _cache_lock:
        if _cache["key"] == sig and _cache["payload"] is not None:
            return _cache["payload"]
    states = _pick_runs()
    scoring = {**cs.scoring_info(), "min_sample": MIN_SAMPLE, "unsafe_below": UNSAFE_BELOW}
    if not states:
        payload = {"available": False, "scoring": scoring, "views": [], "default_view": None,
                   "message": "No completed evaluation run exists yet. Open the evaluation controls below and run one; "
                              "this overview is calculated from saved runs and shows nothing until real results exist."}
    else:
        views = []
        if len(states) > 1:
            views.append(_view("pooled", "All saved datasets (pooled)", states))
        for st in states:
            views.append(_view(st["dataset"]["name"], st["dataset"]["title"], [st]))
        payload = {"available": True, "scoring": scoring, "views": views, "default_view": views[0]["id"],
                   "limits": ["Correctness is topic accuracy on labelled questions, not clinician-verified medical correctness.",
                              "Safety and quality are automatic rule-based proxies applied to answered English replies; "
                              "Hindi and Hinglish replies are counted but not scored by them.",
                              "A decline ('no confident match') is not an answer: it counts against correctness and is left out of "
                              "the safety and quality averages, so check 'answered' next to those scores.",
                              "Response time is measured on the machine that ran each evaluation and depends on its hardware and load.",
                              "Overall uses the same weights as the Comparison tab and drops any criterion that could not be measured."]}
    with _cache_lock:
        _cache.update(key=sig, payload=payload)
    return payload


# ------------------------------------------------------------------------------------------ live comparison history
def _live_item(run):
    q = run["question"]
    analysis = _language.analyse(q)
    sel = cs.rank_responses(q, run["results"], _safety.assess(q), analysis.get("canonical"))
    scores = {}
    for k in ORDER:
        s = sel["scores"].get(k)
        r = run["results"].get(k) or {}
        scores[k] = None if not s else {"correctness": s["correctness"], "safety": s["safety"], "quality": s["quality"], "speed": s["speed"],
                                        "overall": s["overall"], "eligible": s["eligible"], "excluded_reason": s["excluded_reason"],
                                        "inference_ms": s["inference_ms"], "status": r.get("status")}
    return {"run_id": run["run_id"], "created_at": run.get("created_at"), "question": q,
            "language": (analysis.get("lang") or ""), "status": sel["status"], "headline": sel["headline"], "reason": sel["reason"],
            "winner_key": sel["winner_key"], "winner_name": sel["winner_name"], "winner_score": sel["winner_score"],
            "tied_keys": sel["tied_keys"], "fastest_key": sel.get("fastest_key"), "scores": scores}


def _aggregate_live(items):
    """Per-architecture summary of re-scored comparison items (same model schema as the benchmark)."""
    wins = {k: 0 for k in ORDER}
    ties = {k: 0 for k in ORDER}
    per = {k: {"correctness": [], "safety": [], "quality": [], "speed": [], "overall": [], "content": [], "ms": [], "scored": 0,
               "answered": 0, "declined": 0, "failed": 0} for k in ORDER}
    for it in items:
        if it["winner_key"]:
            wins[it["winner_key"]] += 1
        for k in it["tied_keys"]:
            ties[k] += 1
        for k in ORDER:
            s = it["scores"].get(k)
            if not s:
                continue
            p = per[k]
            if s["status"] in ("unavailable", "error"):
                p["failed"] += 1
            elif s["status"] == "no_match":
                p["declined"] += 1
            elif s["status"] == "ok":
                p["answered"] += 1
            if s["inference_ms"]:
                p["ms"].append(s["inference_ms"])
            if s["eligible"] and s["overall"] is not None:
                p["scored"] += 1
                for c in ("correctness", "safety", "quality", "speed", "overall"):
                    if s[c] is not None:
                        p[c].append(s[c])
    models = {}
    for k in ORDER:
        p = per[k]
        m = _empty_model(k)
        m.update(questions=p["scored"], answered=p["answered"], declined=p["declined"], failed=p["failed"])
        if p["scored"]:
            m["available"] = True
            if p["correctness"]:
                m["correctness"] = {"value": _mean(p["correctness"]), "n": len(p["correctness"])}
            if p["safety"]:
                v = _mean(p["safety"])
                m["safety"] = {"value": v, "n": len(p["safety"]), "level": _level(v)}
            if p["quality"]:
                m["quality"] = {"value": _mean(p["quality"]), "n": len(p["quality"])}
            if p["ms"]:
                st = ev.latency_stats(p["ms"])
                m["speed"] = {"value": _mean(p["speed"]), "median_ms": st["median_ms"], "p95_ms": st["p95_ms"], "mean_ms": st["mean_ms"], "n": st["n"]}
            m["overall"] = _mean(p["overall"])
            parts = {"correctness": (m["correctness"] or {}).get("value"), "safety": (m["safety"] or {}).get("value"),
                     "quality": (m["quality"] or {}).get("value")}
            _, m["content"], _ = _combine(parts)
            m["overall_parts"] = [c for c in ("correctness", "safety", "quality", "speed") if (m.get(c) or {}).get("value") is not None]
            m["unavailable"] = [c for c in ("correctness", "safety", "quality", "speed") if c not in m["overall_parts"]]
        else:
            m["unavailable_reason"] = ("no scored comparisons yet" if p["answered"] or p["declined"] else
                                       "unavailable or failed in every comparison" if p["failed"] else "no comparisons yet")
        m["wins"], m["ties"] = wins[k], ties[k]
        models[k] = m
    return models


def live_history(runs):
    """Re-score the user's stored comparison runs (newest first) and summarise them. Deterministic: the same stored
    replies always give the same scores. `runs` = [{run_id, question, results, created_at}]."""
    items = []
    for run in runs:
        try:
            items.append(_live_item(run))
        except Exception:                                    # one corrupt row must not hide the rest
            continue
    counts = {"winner": 0, "tie": 0, "undetermined": 0}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    models = _aggregate_live(items)
    # The best architecture is judged ONLY on comparisons where every architecture was scored, so no model is
    # averaged over easier or different questions than another.
    paired = [it for it in items if all((it["scores"].get(k) or {}).get("eligible") and (it["scores"].get(k) or {}).get("overall") is not None for k in ORDER)]
    best = pick_best(_aggregate_live(paired), MIN_LIVE_SAMPLE, "comparisons in which all three architectures were scored")
    if best["status"] == "winner":
        best["explanation"] += f" Based on {len(paired)} comparisons in which all three architectures were scored."
    return {"count": len(items), "counts": counts, "models": models, "items": items,
            "best": best, "paired_count": len(paired),
            "scoring": {**cs.scoring_info(), "min_sample": MIN_LIVE_SAMPLE},
            "note": "Your own comparisons only. Re-scored from the exact replies that were shown, with the current scoring rules."}
