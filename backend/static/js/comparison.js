/* =========================================================
   MediChat - Comparison / Evaluation rendering (pure functions: data in, HTML string out).
   No fetching, no state, no invented numbers. The winner is ONLY ever read from the backend payload
   (overall_selection.winner_key / performance best.winner_key), so every view agrees with the server.
   Used by research.js; also loadable in Node for tests (module.exports).
========================================================= */
(function (root) {
    "use strict";
    const ARCH = ["rule", "ml", "dl"];
    const NAMES = { rule: "Rule-Based", ml: "Machine Learning (TF-IDF + SVM)", dl: "Deep Learning (DistilBERT)" };
    const SHORT = { rule: "Rule-Based", ml: "Machine Learning", dl: "Deep Learning" };
    const COLORS = { rule: "#5BB8AD", ml: "#0F8F85", dl: "#0A3B3A" };
    const CRITERIA = [
        ["correctness", "Correctness", "Topic matches the dataset label"],
        ["safety", "Safety", "Doctor advice, disclaimer, no risky content"],
        ["quality", "Response quality", "Relevance, completeness, clarity (proxy)"],
        ["speed", "Response time", "Fastest median time / this time"],
    ];
    const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    const isNum = (v) => typeof v === "number" && isFinite(v);
    const num = (v, d = 1) => (isNum(v) ? (Math.round(v * 10 ** d) / 10 ** d).toString() : "n/a");
    const val = (x) => (x && typeof x === "object" ? x.value : x);           // aggregate metrics are {value, n}
    const TROPHY = (px = 18) => `<svg class="mc-trophy" width="${px}" height="${px}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M7 3h10v2h3a1 1 0 0 1 1 1v1.5a4.5 4.5 0 0 1-4.1 4.48A5.5 5.5 0 0 1 13 15.9V18h3a1 1 0 0 1 1 1v2H7v-2a1 1 0 0 1 1-1h3v-2.1a5.5 5.5 0 0 1-3.9-3.92A4.5 4.5 0 0 1 3 7.5V6a1 1 0 0 1 1-1h3V3Zm-2 4.5c0 1.2.8 2.2 1.9 2.45A5.6 5.6 0 0 1 6.9 9V7H5v.5Zm12.1 1.5c0 .17-.02.34-.05.5A2.5 2.5 0 0 0 19 7.5V7h-1.9v2Z"/></svg>`;

    const bestKey = (sel) => (sel && sel.status === "winner" ? sel.winner_key : null);
    const isTied = (sel, k) => !!(sel && sel.status === "tie" && (sel.tied_keys || []).includes(k));

    /* ---------- verdict banner (above the three cards) ---------- */
    function verdict(sel) {
        if (!sel) return "";
        if (sel.status === "winner") {
            return `<section class="mc-verdict win" role="status" aria-label="Best response"><div class="mc-verdict-icon">${TROPHY(26)}</div>
              <div><p class="mc-verdict-kicker">Best Response</p><h3>${esc(sel.winner_name)} <span class="mc-verdict-score">${esc(num(sel.winner_score))}/100</span></h3>
              <p>${esc(sel.reason || "")}</p></div></section>`;
        }
        const tie = sel.status === "tie";
        return `<section class="mc-verdict ${tie ? "tie" : "none"}" role="status"><div class="mc-verdict-icon" aria-hidden="true">${tie ? "=" : "i"}</div>
          <div><h3>${esc(sel.headline || "No best response")}</h3><p>${esc(sel.reason || "")}</p></div></section>`;
    }

    /* ---------- tag across the top of each card ---------- */
    function cardTag(sel, k) {
        if (bestKey(sel) === k) {
            const sc = (sel.scores || {})[k] || {};
            return `<div class="mc-best-tag"><span class="mc-badge">${TROPHY(16)} Best Response</span><strong>${esc(num(sc.overall != null ? sc.overall : sel.winner_score))}<small>/100</small></strong></div>`;
        }
        if (isTied(sel, k)) return `<div class="mc-tie-tag">Tied - no single best response${sel.fastest_key === k ? " · fastest" : ""}</div>`;
        return "";
    }

    /* ---------- score block inside each card ---------- */
    function scoreBlock(sc, isBest) {
        if (!sc) return "";
        const na = (c) => (sc.unavailable || []).includes(c) ? "unavailable" : "n/a";
        const rows = CRITERIA.map(([c, label]) => {
            const v = sc[c];
            const bar = isNum(v) ? `<span class="mc-mini"><span style="width:${Math.max(2, Math.min(100, v))}%"></span></span>` : `<span class="mc-mini off"></span>`;
            const t = c === "speed" && isNum(sc.inference_ms) ? ` title="${esc(num(sc.inference_ms))} ms measured"` : "";
            return `<div class="mc-score-row"${t}><span>${esc(label)}</span>${bar}<b>${isNum(v) ? esc(num(v, v % 1 ? 1 : 0)) : `<em>${na(c)}</em>`}</b></div>`;
        }).join("");
        const lvl = sc.safety_level ? `<span class="pill ${sc.safety_level === "Safe" ? "" : sc.safety_level === "Unsafe" ? "bad" : "warn"}">${esc(sc.safety_level)}</span>` : "";
        const overall = isNum(sc.overall)
            ? `<div class="mc-overall${isBest ? " best" : ""}"><b>${esc(num(sc.overall))}</b><span>overall<br>out of 100</span>${lvl}</div>`
            : `<div class="mc-overall off"><b>Not scored</b><span>${esc(sc.excluded_reason || "no reply to score")}</span></div>`;
        return `<div class="mc-scores" aria-label="Evaluation scores">${overall}<div class="mc-score-rows">${rows}</div></div>`;
    }

    /* ---------- bar charts (HTML/CSS, responsive, values always printed) ---------- */
    function chart(title, hint, rows, opt = {}) {
        const have = rows.filter((r) => isNum(r.value));
        const max = opt.max || Math.max(1, ...have.map((r) => r.value)) * 1.05;
        const lead = have.length >= 2 ? (opt.lowerBetter ? Math.min : Math.max)(...have.map((r) => r.value)) : null;
        const li = rows.map((r) => {
            if (!isNum(r.value)) return `<li class="off"><span class="mc-bar-name">${esc(r.name)}</span><span class="mc-bar-track" title="${esc(r.title || "not measured")}"></span><span class="mc-bar-val">n/a</span></li>`;
            const w = Math.max(1.5, Math.min(100, (100 * r.value) / max));
            return `<li class="${lead !== null && r.value === lead ? "lead" : ""}"><span class="mc-bar-name">${esc(r.name)}</span>
              <span class="mc-bar-track" title="${esc(r.title || "")}"><span class="mc-bar-fill" style="width:${w}%;background:${COLORS[r.key]}"></span></span>
              <span class="mc-bar-val">${esc(opt.fmt ? opt.fmt(r.value) : num(r.value))}</span></li>`;
        }).join("");
        return `<figure class="mc-chart" role="group" aria-label="${esc(title)}, ${esc(hint)}"><figcaption><strong>${esc(title)}</strong><span>${esc(hint)}</span></figcaption><ol class="mc-bars">${li}</ol></figure>`;
    }
    function charts(models) {          // models: {key: {correctness, safety, quality, speed, overall, ms}} numbers or {value}
        const R = (c, f) => ARCH.filter((k) => models[k]).map((k) => ({ key: k, name: SHORT[k], value: f ? f(models[k]) : val(models[k][c]),
            title: `${NAMES[k]}: ${val(models[k][c]) == null ? "not measured" : num(val(models[k][c]))}` }));
        const ms = (m) => (m.inference_ms != null ? m.inference_ms : m.ms != null ? m.ms : m.speed && typeof m.speed === "object" ? m.speed.median_ms : null);
        const time = ARCH.filter((k) => models[k]).map((k) => ({ key: k, name: SHORT[k], value: ms(models[k]), title: `${NAMES[k]}: ${ms(models[k]) == null ? "not measured" : num(ms(models[k]), 1) + " ms"}` }));
        return `<div class="mc-charts">${chart("Overall", "out of 100 · higher is better", R("overall"), { max: 100 })}
          ${chart("Correctness", "out of 100 · higher is better", R("correctness"), { max: 100 })}
          ${chart("Safety", "out of 100 · higher is better", R("safety"), { max: 100 })}
          ${chart("Response quality", "out of 100 · higher is better", R("quality"), { max: 100 })}
          ${chart("Response time", "milliseconds · lower is better", time, { lowerBetter: true, fmt: (v) => num(v, 1) + " ms" })}</div>
          <p class="chart-note">A criterion that could not be measured shows n/a and is left out of the overall score; it is never drawn as 0.</p>`;
    }

    /* ---------- single question: table + charts ---------- */
    function questionEvaluation(sel) {
        if (!sel || !sel.scores) return "";
        const best = bestKey(sel);
        const cell = (x) => (isNum(x) ? esc(num(x, x % 1 ? 1 : 0)) : '<span class="na">n/a</span>');
        const rows = ARCH.map((k) => {
            const s = sel.scores[k]; if (!s) return "";
            return `<tr${best === k ? ' class="mc-best-row"' : ""}><th scope="row">${best === k ? TROPHY(14) + " " : ""}${esc(SHORT[k])}</th>${CRITERIA.map(([c]) => `<td class="num">${cell(s[c])}</td>`).join("")}
              <td class="num"><strong>${isNum(s.overall) ? esc(num(s.overall)) : '<span class="na">not scored</span>'}</strong></td><td>${esc(s.excluded_reason || "")}</td></tr>`;
        }).join("");
        return `<div class="mc-eval"><h4>Evaluation of this question</h4>
          <p class="fine">Scores out of 100 for this exact question, calculated by the evaluation rules. Separate from the dataset evaluation on the Model Evaluation tab.</p>
          <div class="scroll"><table class="data"><thead><tr><th>Model</th>${CRITERIA.map(([, l]) => `<th>${esc(l)}</th>`).join("")}<th>Overall</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table></div>
          ${charts(sel.scores)}</div>`;
    }

    /* ---------- Evaluation tab: measured performance overview ---------- */
    function bestBanner(best, label) {
        if (!best) return "";
        if (best.status === "winner") {
            return `<section class="mc-verdict win" role="status"><div class="mc-verdict-icon">${TROPHY(26)}</div><div><p class="mc-verdict-kicker">${esc(label || "Best-performing architecture")}</p>
              <h3>${esc(best.winner_name)} <span class="mc-verdict-score">${esc(num(best.winner_score))}/100</span></h3><p>${esc(best.explanation)}</p>
              ${(best.caveats || []).map((c) => `<p class="mc-caveat">${esc(c)}</p>`).join("")}</div></section>`;
        }
        return `<section class="mc-verdict ${best.status === "tie" ? "tie" : "none"}" role="status"><div class="mc-verdict-icon" aria-hidden="true">${best.status === "tie" ? "=" : "i"}</div>
          <div><h3>${esc(best.headline)}</h3><p>${esc(best.explanation)}</p></div></section>`;
    }
    function modelCard(m, isBest, tied) {
        const tag = isBest ? `<div class="mc-best-tag"><span class="mc-badge">${TROPHY(16)} Best-performing</span><strong>${esc(num(m.overall))}<small>/100</small></strong></div>` : tied ? '<div class="mc-tie-tag">Tied for best</div>' : "";
        if (!m.available) {
            return `<article class="resp mc-model failed" aria-label="${esc(NAMES[m.key])}">${tag}<div class="card-head"><div><h3>${esc(m.name)}</h3></div><span class="pill bad">no data</span></div>
              <div class="resp-body"><p class="muted">${esc(m.unavailable_reason || "No measured results.")}</p></div></article>`;
        }
        const n = (x) => (x ? ` <small>n=${x.n}</small>` : "");
        const flat = { correctness: val(m.correctness), safety: val(m.safety), quality: val(m.quality), speed: val(m.speed), overall: m.overall, unavailable: m.unavailable, inference_ms: m.speed && m.speed.median_ms, safety_level: m.safety && m.safety.level };
        const facts = [
            `<div><small>Answered</small><span>${m.answered} of ${m.questions}${m.declined ? ` · ${m.declined} declined` : ""}</span></div>`,
            m.speed && m.speed.median_ms != null ? `<div><small>Median time</small><span>${esc(num(m.speed.median_ms, 1))} ms${m.speed.p95_ms != null ? ` · p95 ${esc(num(m.speed.p95_ms, 1))} ms` : ""}</span></div>` : "",
            m.not_scored_language ? `<div><small>Hindi / Hinglish replies</small><span>${m.not_scored_language} not scored for safety or quality</span></div>` : "",
            m.probes ? `<div><small>Emergency guidance</small><span>${m.probes.emergency_surfaced}/${m.probes.emergency_total} shown · ${m.probes.false_alarms} false alarms</span></div>
              <div><small>Out-of-scope declined</small><span>${m.probes.oos_declined}/${m.probes.oos_total}</span></div>` : "",
            m.wins != null ? `<div><small>Single-question wins</small><span>${m.wins}${m.ties ? ` · ${m.ties} ties` : ""}</span></div>` : "",
            m.failed ? `<div><small>Failed calls</small><span>${m.failed}</span></div>` : "",
        ].join("");
        return `<article class="resp mc-model ${isBest ? "mc-best" : tied ? "mc-tied" : ""}" aria-label="${esc(NAMES[m.key])}${isBest ? " - best-performing architecture" : ""}">${tag}
          <div class="card-head"><div><h3>${esc(m.name)}</h3><div class="sub">${esc(NAMES[m.key])}${m.version ? " · " + esc(m.version) : ""}</div></div></div>
          <div class="resp-body">${scoreBlock(flat, isBest)}<p class="mc-ns">${["correctness", "safety", "quality"].map((c) => m[c] ? `${esc(CRITERIA.find((x) => x[0] === c)[1])}${n(m[c])}` : "").filter(Boolean).join(" · ")}</p></div>
          <div class="meta mc-facts">${facts}</div></article>`;
    }
    function overview(view, scoring) {
        if (!view) return "";
        const best = view.best || {};
        const w = (scoring && scoring.weights) || {};
        const pc = (x) => (x == null ? "?" : Math.round(x * 100) + "%");
        const runs = (view.runs || []).map((r) => `<li><strong>${esc(r.title)}</strong> · ${r.questions} questions · ${r.sampled ? "sample" : "all eligible"} · run <code>${esc(r.run_id)}</code></li>`).join("");
        return `${bestBanner(best)}
          <div class="cards mc-model-cards">${ARCH.map((k) => view.models[k] ? modelCard(view.models[k], best.status === "winner" && best.winner_key === k, best.status === "tie" && (best.tied_keys || []).includes(k)) : "").join("")}</div>
          <div class="panel mc-graphs"><h2>Score comparison</h2>
            <p class="muted">Overall = correctness ${pc(w.correctness)} + safety ${pc(w.safety)} + response quality ${pc(w.quality)} + response time ${pc(w.speed)}, re-balanced over what could be measured. Differences under ${esc(scoring && scoring.tie_margin)} points are a tie; a lead from response time alone is not enough to name a best architecture.</p>
            ${charts(view.models)}</div>
          <details class="fold"><summary>Data behind these scores</summary><ul class="mc-src">${runs}</ul>
            <p class="hint">Scores are recalculated from the replies, topic matches and timings stored in these saved runs (scoring rules v${esc(scoring && scoring.version)}).</p></details>`;
    }

    /* ---------- Evaluation tab: the user's own comparison history ---------- */
    function history(h) {
        if (!h || !h.count) return '<p class="muted">No comparisons saved yet. Ask a question in the Chatbot Comparison tab and it will appear here with its scores.</p>';
        const c = h.counts || {};
        const best = bestBanner(h.best, "Best architecture across your comparisons");
        const sum = `<div class="scroll"><table class="data ev-sum"><thead><tr><th>Model</th><th>Scored</th><th>Wins</th><th>Ties</th><th>Correctness</th><th>Safety</th><th>Quality</th><th>Median time</th><th>Mean overall</th></tr></thead><tbody>${ARCH.map((k) => {
            const m = h.models[k]; const f = (x) => (x ? esc(num(x.value)) : '<span class="na">n/a</span>');
            return `<tr><th scope="row">${esc(SHORT[k])}</th><td class="num">${m.questions}</td><td class="num">${m.wins}</td><td class="num">${m.ties}</td><td class="num">${f(m.correctness)}</td><td class="num">${f(m.safety)}</td><td class="num">${f(m.quality)}</td><td class="num">${m.speed && m.speed.median_ms != null ? esc(num(m.speed.median_ms, 1)) + " ms" : '<span class="na">n/a</span>'}</td><td class="num"><strong>${m.overall == null ? '<span class="na">n/a</span>' : esc(num(m.overall))}</strong></td></tr>`;
        }).join("")}</tbody></table></div>
          <p class="chart-note">${h.count} comparison${h.count === 1 ? "" : "s"}: ${c.winner || 0} with a best response, ${c.tie || 0} tied, ${c.undetermined || 0} undetermined. Correctness only exists for questions that are in the labelled datasets.</p>`;
        const rows = h.items.map((it) => {
            const res = it.status === "winner" ? `<span class="mc-win-pill">${TROPHY(13)} ${esc(SHORT[it.winner_key])}</span>` : it.status === "tie" ? '<span class="pill warn">Tie</span>' : '<span class="pill grey">Undetermined</span>';
            const cells = ARCH.map((k) => { const s = it.scores[k]; return `<td class="num${it.winner_key === k ? " mc-win-cell" : ""}">${s && isNum(s.overall) ? esc(num(s.overall)) : '<span class="na">–</span>'}</td>`; }).join("");
            return `<tr><td>${esc(new Date(String(it.created_at).replace(" ", "T") + (String(it.created_at).includes("Z") ? "" : "Z")).toLocaleString())}</td><td class="ev-q">${esc(it.question)}<details class="mc-row-detail"><summary>Scores and reason</summary><p>${esc(it.reason)}</p>
              <table class="data"><thead><tr><th>Model</th>${CRITERIA.map(([, l]) => `<th>${esc(l)}</th>`).join("")}</tr></thead><tbody>${ARCH.map((k) => { const s = it.scores[k] || {}; return `<tr><th scope="row">${esc(SHORT[k])}</th>${CRITERIA.map(([cc]) => `<td class="num">${isNum(s[cc]) ? esc(num(s[cc])) : '<span class="na">n/a</span>'}</td>`).join("")}</tr>`; }).join("")}</tbody></table></details></td><td>${res}</td>${cells}</tr>`;
        }).join("");
        return `${best}${sum}<div class="scroll" style="margin-top:14px"><table class="data"><thead><tr><th>When</th><th>Question</th><th>Result</th>${ARCH.map((k) => `<th>${esc(SHORT[k])}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>
          <p class="hint">${esc(h.note || "")}</p>`;
    }

    const api = { ARCH, NAMES, SHORT, COLORS, CRITERIA, TROPHY, bestKey, isTied, verdict, cardTag, scoreBlock, chart, charts, questionEvaluation, bestBanner, modelCard, overview, history };
    if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MCCompare = api;
})(typeof window !== "undefined" ? window : globalThis);
