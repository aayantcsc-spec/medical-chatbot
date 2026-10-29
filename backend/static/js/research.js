/* =========================================================
   MediChat research workspace - Comparison / Evaluation / User Study
   API used (all JSON, login required):
     POST /api/comparison/ask                              {question} -> run_comparison() + run_id
     GET  /api/comparison/evaluation/datasets
     POST /api/comparison/evaluation/run                   {dataset, mode: quick|full|custom, category?, limit?}
     GET  /api/comparison/evaluation/status/<id>   .../runs   .../runs/<id>   .../runs/<id>/export.csv
     GET  /api/comparison/study/runs   /study/run/<id>   POST /study/submit   GET /study/summary   /study/export.csv
   Nothing here invents numbers: every figure shown comes from a server response.
========================================================= */
(() => {
    "use strict";
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
    const ARCH = ["rule", "ml", "dl"];
    const ARCH_NAMES = { rule: "Rule-Based", ml: "Machine Learning (TF-IDF + SVM)", dl: "Deep Learning (DistilBERT)" };
    const MC = window.MCCompare;
    const COLORS = MC.COLORS;
    const LANG = { en: "English", hi: "Hindi", hinglish: "Hinglish" };
    const MAX_Q = 1000;

    /* ------------------------------------------------------------- utilities */
    const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    const pct = (v, d = 1) => (v == null || isNaN(v) ? "n/a" : (v * 100).toFixed(d) + "%");
    const num = (v, d = 1) => (v == null || isNaN(v) ? "n/a" : Number(v).toFixed(d));
    const when = (iso) => { if (!iso) return ""; const d = new Date(iso.includes("T") || iso.includes("Z") ? iso : iso.replace(" ", "T") + "Z"); return isNaN(d) ? iso : d.toLocaleString(); };
    const trunc = (s, n) => (String(s).length > n ? String(s).slice(0, n - 1) + "…" : String(s));

    function inline(t) {
        t = esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        return t.replace(/(^|[\s(])_([^_]+)_(?=$|[\s).,;:!?])/g, "$1<em>$2</em>");
    }
    function md(src) {                       // escape first, then add a few tags: model text can never inject HTML
        const out = []; let list = null, para = [];
        const fp = () => { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } };
        const fl = () => { if (list) { out.push(`<${list.t}>` + list.i.map((x) => "<li>" + inline(x) + "</li>").join("") + `</${list.t}>`); list = null; } };
        for (const raw of String(src || "").replace(/\r/g, "").split("\n")) {
            const line = raw.trimEnd(); let m;
            if (!line.trim()) { fp(); fl(); continue; }
            if ((m = line.match(/^#{1,4}\s+(.*)$/))) { fp(); fl(); out.push(`<h4 class="mc-md-h">${inline(m[1])}</h4>`); continue; }
            if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { fp(); if (!list || list.t !== "ul") { fl(); list = { t: "ul", i: [] }; } list.i.push(m[1]); continue; }
            if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) { fp(); if (!list || list.t !== "ol") { fl(); list = { t: "ol", i: [] }; } list.i.push(m[1]); continue; }
            fl(); para.push(line.trim());
        }
        fp(); fl(); return out.join("");
    }

    async function api(url, opt = {}) {
        let res;
        try { res = await fetch(url, { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...opt }); }
        catch (e) { throw new Error("Could not reach the server. Check your connection and try again."); }
        let data = {};
        try { data = await res.json(); } catch (_) { /* not JSON */ }
        if (res.status === 401 || data.login_required) { window.location.href = "/login"; throw new Error("Please sign in again."); }
        if (!res.ok || data.success === false) { const e = new Error(data.error || `Request failed (${res.status}).`); e.status = res.status; e.data = data; throw e; }
        return data;
    }
    function say(id, msg, kind = "") {
        const el = $("#" + id); if (!el) return;
        el.textContent = msg || ""; el.className = "status-message" + (kind ? " " + kind : "") + (msg ? "" : " hidden");
    }

    /* ------------------------------------------------------------------ tabs */
    const state = { tab: "compare", evalLoaded: false, studyLoaded: false, run: null, poll: null, datasets: [], qpage: 0, busy: false, starting: false, quick: 30 };
    function activate(tab, focus = false) {
        if (!["compare", "eval", "study"].includes(tab)) tab = "compare";
        state.tab = tab;
        $$(".tab").forEach((b) => { const on = b.dataset.tab === tab; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); });
        $$(".rs-section").forEach((s) => s.classList.toggle("active", s.id === "section-" + tab));
        $("#composer").classList.toggle("hidden", tab !== "compare");
        history.replaceState(null, "", "#" + tab);
        if (tab === "eval" && !state.evalLoaded) initEval();
        else if (tab === "eval" && state.liveStale) loadHistory();
        if (tab === "study" && !state.studyLoaded) initStudy();
    }
    $$(".tab").forEach((b, i, all) => {
        b.addEventListener("click", () => activate(b.dataset.tab));
        b.addEventListener("keydown", (e) => {
            if (e.key === "ArrowRight") activate(all[(i + 1) % all.length].dataset.tab, true);
            if (e.key === "ArrowLeft") activate(all[(i + all.length - 1) % all.length].dataset.tab, true);
        });
    });

    /* ============================================================ COMPARE */
    const q = $("#q"), form = $("#questionForm"), sendBtn = $("#sendBtn");
    let busy = false;
    const MULTI = [
        { emoji: "🇮🇳", category: "Hinglish", question: "Mujhe bukhar aur khansi ho rahi hai, kya karu?" },
        { emoji: "अ", category: "Hindi", question: "मेरे सिर में दर्द है और चक्कर आ रहे हैं" },
        { emoji: "🩺", category: "Doctor", question: "Which doctor should I consult for persistent stomach pain?" },
    ];
    function renderChips() {
        const box = $("#chips"); box.innerHTML = "";
        [...MULTI, ...(window.MC_EXAMPLES || []).slice(0, 9)].forEach((ex) => {
            const b = document.createElement("button");
            b.type = "button"; b.className = "chip"; b.textContent = `${ex.emoji || ""} ${ex.question}`.trim();
            b.title = ex.category || ""; b.addEventListener("click", () => { q.value = ex.question; grow(); q.focus(); });
            box.appendChild(b);
        });
    }
    function grow() {
        q.style.height = "auto"; q.style.height = Math.min(q.scrollHeight, 180) + "px";
        $("#counter").textContent = `${q.value.length} / ${MAX_Q}`;
    }
    q.addEventListener("input", grow);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); } });
    $("#newBtn").addEventListener("click", () => { $("#history").innerHTML = ""; $("#empty").classList.remove("hidden"); say("compare-status", ""); q.focus(); });

    function metaItem(label, value) { return `<div class="meta-item"><small>${esc(label)}</small><span>${value}</span></div>`; }
    function confidenceText(r) {
        if (r.confidence == null || r.status === "small_talk") return '<span class="na">not applicable</span>';
        return `${(r.confidence * 100).toFixed(1)}%`;
    }
    const NA = '<span class="na">unavailable</span>';
    function selectionPanel(sel) {          // method details only; the verdict itself is MCCompare.verdict(sel)
        if (!sel) return "";
        const m = sel.method || {}; const w = m.weights || {}; const pc = (x) => (x == null ? "?" : Math.round(x * 100) + "%");
        return `<details class="mc-method"><summary>How the best response was chosen</summary><ul>
              <li>Only answered replies are compared; failed, unavailable or no-match replies cannot win, and replies that fail the safety check are excluded.</li>
              <li>Overall = correctness ${pc(w.correctness)} + safety ${pc(w.safety)} + response quality ${pc(w.quality)} + response time ${pc(w.speed)}. A part that cannot be calculated is shown as unavailable and the remaining weights are re-balanced. Model confidence is not used.</li>
              <li>${m.ground_truth && m.ground_truth.available ? `Correctness: this exact question is in the labelled <code>${esc(m.ground_truth.dataset)}</code> dataset (expected topic: ${esc(m.ground_truth.expected)}); a reply scores 100 if the model predicted that topic, otherwise 0.` : esc((m.ground_truth && m.ground_truth.note) || "Correctness unavailable.")}</li>
              <li>Differences under ${esc(m.tie_margin)} points, or a lead that comes from response time alone, are reported as a tie.</li>
              <li>${esc(m.language_scope || "")}</li></ul><p class="fine">${esc(m.limits || "")} ${esc(m.scope || "")}</p></details>`;
    }
    /* ---- single-question evaluation: rendered by MCCompare (table + charts, real scores only) */
    const short = (k) => ARCH_NAMES[k].split(" (")[0];
    const evaluationBlock = (sel) => MC.questionEvaluation(sel);
    let latestSelection = null;
    function renderLatest() {
        const box = $("#latestComparison"); if (!box) return;
        const l = latestSelection;
        if (!l) { box.innerHTML = '<p class="muted">No comparison has been run in this session yet. Ask a question in the Chatbot Comparison tab.</p>'; return; }
        box.innerHTML = `<p class="mc-latest-q">Question: <em>${esc(l.question)}</em></p>${MC.verdict(l.sel)}${selectionPanel(l.sel)}${evaluationBlock(l.sel)}
            <p class="fine">Single-question result. It does not replace the aggregate results above and is not saved to the evaluation runs.</p>`;
    }
    function card(key, r, runId, sel) {
        const failed = r.status === "unavailable" || r.status === "error";
        const label = failed ? { t: r.status, c: "bad" } : r.status === "no_match" ? { t: "no confident match", c: "warn" } : r.status === "small_talk" ? { t: "small talk", c: "grey" } : { t: "answered", c: "" };
        const body = failed
            ? `<p class="error-text">${esc(r.status === "unavailable" ? "This model is unavailable." : "This model failed on this question.")}</p><p class="muted">${esc(r.error || "No further detail was returned.")}</p>`
            : `<div class="md">${md(r.response)}</div>`;
        const topic = r.intent_title || r.intent;
        const st = r.structure;
        const sc = sel && sel.scores ? sel.scores[key] : null;
        const isBest = !!(sel && sel.status === "winner" && sel.winner_key === key);
        const isTie = !!(sel && sel.status === "tie" && (sel.tied_keys || []).includes(key));
        return `<article class="resp ${failed ? "failed" : ""} ${isBest ? "mc-best" : isTie ? "mc-tied" : ""}" aria-label="${esc(ARCH_NAMES[key])} response${isBest ? " - best overall response" : ""}">
            ${MC.cardTag(sel, key)}
            <div class="card-head"><div><h3>${esc(r.name || ARCH_NAMES[key])}</h3><div class="sub">${esc(r.architecture || "")}${r.version ? " · " + esc(r.version) : ""}</div></div>
                <span class="pill ${label.c}">${esc(label.t)}</span></div>
            ${sc && sc.eligible !== undefined ? MC.scoreBlock(sc, isBest) : ""}
            <div class="resp-body">${body}</div>
            <div class="meta">
                ${metaItem("Predicted topic", topic ? esc(topic) : '<span class="na">none</span>')}
                ${metaItem("Category", r.category ? esc(String(r.category).replace(/_/g, " ")) : '<span class="na">n/a</span>')}
                ${metaItem("Confidence", confidenceText(r))}
                ${metaItem("Inference time", r.inference_ms == null ? '<span class="na">n/a</span>' : num(r.inference_ms, 1) + " ms")}
                ${metaItem("Reply length", st ? `${st.characters} chars · ${st.sections} sections` : '<span class="na">n/a</span>')}
                ${metaItem("Produced by", esc(r.handled_by || "model"))}
                ${r.confidence != null && r.confidence_kind ? `<p class="conf-note">Confidence type: ${esc(r.confidence_kind)}. This is the model's own score, not medical certainty and not accuracy.</p>` : ""}
            </div></article>`;
    }
    function renderTurn(question, data) {
        const lang = data.language || {}; const res = data.results || {};
        const syms = (data.symptoms || []).map((s) => `<span class="pill grey">${esc(s)}</span>`).join(" ");
        const understood = lang.lang && lang.lang !== "en" && data.canonical_text ? `<p class="hint" style="margin:8px 0 0">Preprocessed for all three models as: <em>${esc(data.canonical_text)}</em></p>` : "";
        const emerg = data.safety && data.safety.emergency
            ? `<div class="banner danger" role="alert"><span aria-hidden="true">⚠</span><div><strong>Safety check triggered.</strong> This question matches emergency warning signs (${esc((data.safety.categories || []).join(", "))}). The safety module runs independently of every model; each reply below carries the emergency guidance.</div></div>` : "";
        const notes = (data.notes || []).length
            ? `<div class="turn-notes"><h4>How the replies differ</h4><ul>${data.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>
               <p class="fine">${esc(data.notes_kind || "")}. Single-question result only: it cannot show which architecture is better overall, and confidence is not accuracy.</p></div>` : "";
        const el = document.createElement("div"); el.className = "turn";
        el.innerHTML = `<div class="turn-header"><div class="q-bubble">${esc(question)}</div>
                ${lang.lang ? `<span class="pill">${esc(LANG[lang.lang] || lang.lang)}</span>` : ""} ${syms}</div>${understood}${emerg}
            ${MC.verdict(data.overall_selection)}<div class="cards">${ARCH.map((k) => res[k] ? card(k, res[k], data.run_id, data.overall_selection) : "").join("")}</div>${selectionPanel(data.overall_selection)}${evaluationBlock(data.overall_selection)}${notes}
            <div style="margin-top:12px">${data.run_id ? `<button type="button" class="btn secondary small" data-rate="${esc(data.run_id)}">Rate these responses in the User Study →</button>` : ""}</div>`;
        const rb = $("[data-rate]", el);
        if (rb) rb.addEventListener("click", () => { state.pendingRun = rb.dataset.rate; activate("study"); if (state.studyLoaded) initStudy(); });
        latestSelection = data.overall_selection ? { question, sel: data.overall_selection } : null; renderLatest();
        state.liveStale = true; if (state.evalLoaded) loadHistory();
        $("#history").prepend(el); $("#empty").classList.add("hidden");
        el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    }
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = q.value.trim();
        if (!question || busy) return;
        if (question.length > MAX_Q) { say("compare-status", `Please keep the question under ${MAX_Q} characters.`, "error"); return; }
        busy = true; sendBtn.disabled = true; sendBtn.innerHTML = '<span class="spinner"></span> Comparing…'; say("compare-status", "");
        try {
            const data = await api("/api/comparison/ask", { method: "POST", body: JSON.stringify({ question }) });
            renderTurn(question, data); q.value = ""; grow();
        } catch (err) { say("compare-status", err.message || "Comparison failed. Please try again.", "error"); }
        finally { busy = false; sendBtn.disabled = false; sendBtn.textContent = "Compare"; q.focus(); }
    });


    /* ---- measured performance overview + the user's own comparison history (both from the server, nothing typed in) */
    const perf = { data: null, view: null };
    async function loadPerformance() {
        const box = $("#perfBody"); if (!box) return;
        try {
            const { data } = await api("/api/comparison/performance"); perf.data = data;
            if (!data.available) { $("#perfControls").classList.add("hidden"); box.innerHTML = `<div class="empty-state"><h3>No measured results yet</h3><p>${esc(data.message)}</p></div>`; return; }
            const sel = $("#perfView"); sel.innerHTML = data.views.map((v) => `<option value="${esc(v.id)}">${esc(v.title)}</option>`).join("");
            perf.view = perf.view && data.views.some((v) => v.id === perf.view) ? perf.view : data.default_view; sel.value = perf.view;
            if (!sel.dataset.bound) { sel.dataset.bound = 1; sel.addEventListener("change", () => { perf.view = sel.value; drawPerformance(); }); }
            $("#perfControls").classList.remove("hidden"); drawPerformance();
            $("#perfLimits").innerHTML = (data.limits || []).map((l) => `<li>${esc(l)}</li>`).join("");
        } catch (err) { box.innerHTML = `<div class="status-message error">${esc(err.message)}</div>`; }
    }
    function drawPerformance() { const v = perf.data.views.find((x) => x.id === perf.view); $("#perfBody").innerHTML = MC.overview(v, perf.data.scoring); }
    async function loadHistory() {
        const box = $("#liveHistory"); if (!box) return; state.liveStale = false;
        try { const { data } = await api("/api/comparison/history"); box.innerHTML = MC.history(data); }
        catch (err) { box.innerHTML = `<div class="status-message error">${esc(err.message)}</div>`; }
    }

    /* =========================================================== EVALUATION */
    const MODE_NAMES = { quick: "Quick test", full: "All eligible", custom: "Custom count" };
    const modeLabel = (run) => { const sel = run.selection || {}; const m = sel.mode || run.mode; return MODE_NAMES[m] || m; };
    const isFailed = (r) => r && (r.status === "unavailable" || r.status === "error");
    const primaryOK = (run, rec) => (run.dataset.kind === "mapped" ? rec.correct_lenient : rec.correct_strict);
    const clsOf = (run, key, scoring) => { const m = run.metrics[key]; if (!m) return null;
        if (run.dataset.kind === "mapped") return scoring === "strict" ? m.classification_strict : m.classification_lenient; return m.classification; };
    const tip = (t) => `<span class="tip" tabindex="0" role="button" aria-label="Explanation: ${esc(t)}" data-tip="${esc(t)}">ⓘ</span>`;
    const TIPS = {
        lenient: "Question bank: correct if the expected category is any acceptable category of the predicted intent. Exact-label datasets: same as strict.",
        strict: "Only the predicted intent's primary category counts as correct.",
        precision: "Of the answers given for a class, the share that were right (macro average). A no-match is not a wrong class, so it does not lower precision.",
        recall: "Of the questions that belong to a class, the share found (macro average). A no-match counts as a miss.",
        f1: "Harmonic mean of precision and recall (macro average).",
        median: "Half of the answers were faster than this (ms, measured on this machine).",
        p95: "95% of answers were faster than this (ms). Shows the slow tail.",
        nomatch: "Questions where the model declined to pick a topic. They stay in the denominator.",
        failed: "Model calls that errored or were unavailable. Reported per model; never removed silently.",
    };

    /* one floating tooltip for every .tip (works inside scrolling tables, on keyboard focus and on touch) */
    (() => {
        let box = null, owner = null;
        const hide = () => { if (box) box.classList.add("hidden"); owner = null; };
        const show = (el) => {
            if (!box) { box = document.createElement("div"); box.className = "ev-tooltip hidden"; box.setAttribute("role", "tooltip"); document.body.appendChild(box); }
            owner = el; box.textContent = el.dataset.tip || ""; box.classList.remove("hidden");
            const r = el.getBoundingClientRect(), w = box.offsetWidth, h = box.offsetHeight;
            let x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
            let y = r.bottom + 8; if (y + h > window.innerHeight - 8) y = Math.max(8, r.top - h - 8);
            box.style.left = x + "px"; box.style.top = y + "px";
        };
        document.addEventListener("mouseover", (e) => { const t = e.target.closest && e.target.closest(".tip"); if (t) show(t); });
        document.addEventListener("mouseout", (e) => { if (e.target.closest && e.target.closest(".tip")) hide(); });
        document.addEventListener("focusin", (e) => { const t = e.target.closest && e.target.closest(".tip"); if (t) show(t); });
        document.addEventListener("focusout", hide);
        document.addEventListener("click", (e) => { const t = e.target.closest && e.target.closest(".tip"); if (t) { owner === t ? hide() : show(t); } else hide(); });
        document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
        window.addEventListener("scroll", hide, { passive: true });
    })();

    /* ---- selection panel */
    const ds = () => state.datasets.find((d) => d.name === $("#evalDataset").value);
    const evMode = () => ($('input[name="evalMode"]:checked') || {}).value || "quick";
    const evCategory = () => $("#evalCategory").value || "";
    function eligibleCount() {
        const d = ds(); if (!d) return 0; const c = evCategory();
        if (!c) return d.rows_usable || 0;
        const hit = (d.categories || []).find((x) => x.value === c); return hit ? hit.count : 0;
    }
    function parseCount() {
        const raw = $("#evalCount").value.trim(), n = Number(raw), max = eligibleCount();
        if (raw === "" || !Number.isFinite(n) || !Number.isInteger(n) || n < 1) return { ok: false, msg: `Enter a whole number from 1 to ${max}.` };
        if (n > max) return { ok: false, msg: `Only ${max} eligible question${max === 1 ? " is" : "s are"} available for this selection. Enter ${max} or fewer.` };
        return { ok: true, n };
    }
    function selectedCount() {
        const max = eligibleCount(), m = evMode();
        if (m === "full") return max;
        if (m === "custom") { const c = parseCount(); return c.ok ? c.n : null; }
        return Math.min(state.quick || 30, max);
    }
    function updateSelection() {
        const d = ds(); const m = evMode(); const max = eligibleCount(); const quick = Math.min(state.quick || 30, max);
        $("#quickLabel").textContent = `Quick test (${quick})`; $("#fullLabel").textContent = `All eligible (${max})`;
        $("#evalCountField").classList.toggle("hidden", m !== "custom");
        $("#evalCount").max = String(max);
        const c = m === "custom" ? parseCount() : { ok: true };
        $("#evalCountMsg").textContent = c.ok ? "" : c.msg; $("#evalCount").setAttribute("aria-invalid", c.ok ? "false" : "true");
        const sel = selectedCount();
        $("#sumTotal").textContent = d ? d.rows_in_file : "–";
        $("#sumEligible").textContent = d ? (evCategory() ? `${max} in category (${d.rows_usable} in dataset)` : d.rows_usable) : "–";
        $("#sumExcluded").textContent = d ? d.rows_excluded || 0 : "–";
        $("#sumSelected").textContent = sel == null ? "–" : sel === max && max ? `${sel} (all eligible)` : String(sel);
        $("#sumScope").textContent = d ? `${d.title} · ${evCategory() ? evCategory().replace(/_/g, " ") : (d.category_label === "Probe type" ? "All probe types" : "All categories")}` : "–";
        $("#evalRunHint").textContent = m === "quick" ? `Quick test samples ${quick} eligible question${quick === 1 ? "" : "s"} (stratified, fixed seed 42, so it is repeatable).`
            : m === "full" ? `Every eligible question in the selection (${max}) is evaluated.` : "Questions are sampled with a fixed seed, so the same count gives the same questions.";
        $("#runEvalBtn").disabled = state.busy || !d || !d.valid || max < 1 || !c.ok;
        $("#runEvalBtn").textContent = state.busy ? "Evaluation running…" : "Run evaluation";
    }
    function fillCategories() {
        const d = ds(), sel = $("#evalCategory"); sel.innerHTML = "";
        const probe = d && d.category_label === "Probe type";
        $("#evalCategoryLabel").textContent = probe ? "Probe type" : "Category";
        const all = document.createElement("option"); all.value = ""; all.textContent = probe ? "All probe types" : "All categories"; sel.appendChild(all);
        ((d && d.categories) || []).forEach((c) => { const o = document.createElement("option"); o.value = c.value; o.textContent = `${c.value.replace(/_/g, " ")} (${c.count})`; sel.appendChild(o); });
        const max = eligibleCount(); const cur = Number($("#evalCount").value);
        if (!cur || cur > max) $("#evalCount").value = String(Math.max(1, Math.min(state.quick || 30, max)));
    }
    function showDatasetInfo() {
        const x = ds(); if (!x) return; fillCategories();
        const bits = [x.version ? `version ${x.version}` : "", (x.issues && x.issues.length) ? "issues: " + x.issues.join("; ") : ""];
        $("#evalDatasetInfo").textContent = bits.filter(Boolean).join(" · ") + (x.warnings && x.warnings.length ? (bits.some(Boolean) ? "  " : "") + "ⓘ " + x.warnings[0] : "");
        updateSelection();
    }
    function setBusy(b) { state.busy = b; updateSelection(); }
    async function initEval() {
        state.evalLoaded = true; loadPerformance(); loadHistory();
        try {
            const d = await api("/api/comparison/evaluation/datasets");
            state.datasets = d.datasets; state.quick = d.quick_size;
            const sel = $("#evalDataset"); sel.innerHTML = "";
            d.datasets.forEach((x) => { const o = document.createElement("option"); o.value = x.name; o.disabled = !x.valid; o.textContent = `${x.title}${x.valid ? "" : " (unavailable)"}`; sel.appendChild(o); });
            const first = d.datasets.find((x) => x.name === "question_bank" && x.valid) || d.datasets.find((x) => x.valid); if (first) sel.value = first.name;
            sel.addEventListener("change", showDatasetInfo);
            $("#evalCategory").addEventListener("change", updateSelection);
            $$('input[name="evalMode"]').forEach((r) => r.addEventListener("change", updateSelection));
            $("#evalCount").addEventListener("input", updateSelection);
            showDatasetInfo();
        } catch (err) { say("eval-status", err.message, "error"); }
        $("#runEvalBtn").addEventListener("click", startEval);
        await refreshRuns(true);
    }
    async function startEval() {
        if (state.busy || state.starting) return;                           // no duplicate submissions
        const mode = evMode(); const body = { dataset: $("#evalDataset").value, mode };
        if (evCategory()) body.category = evCategory();
        if (mode === "custom") { const c = parseCount(); if (!c.ok) { say("eval-status", c.msg, "error"); $("#evalCount").focus(); return; } body.limit = c.n; }
        state.starting = true; setBusy(true); say("eval-status", "");
        try {
            const r = await api("/api/comparison/evaluation/run", { method: "POST", body: JSON.stringify(body) });
            state.run = null; $("#evalResults").classList.add("hidden"); $("#evalEmpty").classList.add("hidden");
            watch(r.run.run_id);
        } catch (err) { say("eval-status", err.message, "error"); setBusy(false); if (err.data && err.data.busy) refreshRuns(false, true); }
        finally { state.starting = false; }
    }
    function showProgress(s) {
        const p = s.progress; $("#evalProgress").classList.remove("hidden");
        $("#evalDone").textContent = p.completed; $("#evalTotal").textContent = p.total; $("#evalErrors").textContent = p.errors; $("#evalSkipped").textContent = p.skipped;
        const pc = p.total ? Math.round((100 * p.completed) / p.total) : 0;
        $("#evalFill").style.width = pc + "%"; $("#evalBar").setAttribute("aria-valuenow", pc);
        const st = $("#evalState"); st.textContent = s.status + (s.status === "running" && p.current ? ` · ${p.current}` : "");
        st.className = "pill " + (s.status === "failed" ? "bad" : s.status === "completed" ? "" : "warn");
    }
    function watch(runId) {
        clearInterval(state.poll); setBusy(true);
        const tick = async () => {
            try {
                const { run } = await api(`/api/comparison/evaluation/status/${runId}`); showProgress(run);
                if (run.status === "completed" || run.status === "failed") {
                    clearInterval(state.poll); setBusy(false);
                    if (run.status === "failed") say("eval-status", "The evaluation failed: " + (run.error || "unknown error"), "error");
                    await openRun(runId); refreshRuns(); if (run.status === "completed") loadPerformance();
                }
            } catch (err) { clearInterval(state.poll); setBusy(false); say("eval-status", err.message, "error"); }
        };
        tick(); state.poll = setInterval(tick, 1000);
    }
    async function refreshRuns(autoOpen = false, resumeRunning = false) {
        let runs = [];
        try { runs = (await api("/api/comparison/evaluation/runs")).runs; } catch (err) { say("eval-status", err.message, "error"); return; }
        const running = runs.find((r) => r.status === "running" || r.status === "pending");
        if (running && (autoOpen || resumeRunning)) { watch(running.run_id); }
        else if (autoOpen) {
            const done = runs.find((r) => r.status === "completed") || runs[0];
            if (done) await openRun(done.run_id); else { $("#evalEmpty").classList.remove("hidden"); }
        }
        const box = $("#evalRuns");
        if (!runs.length) { box.innerHTML = '<p class="muted">No saved runs yet. Completed runs appear here and on the Analysis page.</p>'; return; }
        box.innerHTML = `<table class="data"><thead><tr><th>Started</th><th>Dataset</th><th>Selection</th><th>Status</th><th>Questions</th><th>Accuracy (Rule / ML / DL) ${tip("Primary accuracy: lenient for the question bank, exact match for the other datasets.")}</th><th></th></tr></thead><tbody>${runs.map((r) => {
            const acc = ARCH.map((k) => (r.models && r.models[k] != null ? pct(r.models[k]) : "n/a")).join(" / ");
            return `<tr><td>${esc(when(r.created_at))}</td><td>${esc(r.dataset_title || r.dataset)}</td><td>${esc(MODE_NAMES[r.mode] || r.mode)}${r.category ? " · " + esc(String(r.category).replace(/_/g, " ")) : ""}${r.sampled && !r.category ? " (sample)" : ""}</td>
                <td><span class="pill ${r.status === "failed" ? "bad" : r.status === "completed" ? "" : "warn"}">${esc(r.status)}</span></td>
                <td class="num">${r.progress.completed}/${r.progress.total}</td><td>${r.dataset === "safety" ? '<span class="na">see safety view</span>' : esc(acc)}</td>
                <td><button class="btn secondary small" data-open="${esc(r.run_id)}">Open</button></td></tr>`;
        }).join("")}</tbody></table>`;
        $$("[data-open]", box).forEach((b) => b.addEventListener("click", () => { openRun(b.dataset.open); window.scrollTo({ top: $("#evalResults").offsetTop - 80, behavior: "smooth" }); }));
    }
    async function openRun(runId) {
        try { state.run = (await api(`/api/comparison/evaluation/runs/${runId}`)).run; state.qpage = 0; renderRun(state.run); }
        catch (err) { say("eval-status", err.message, "error"); }
    }

    /* ---- SVG charts (no external library) */
    function groupedBars(run) {
        const keys = ARCH.filter((k) => run.metrics[k] && run.metrics[k].classification);
        const metrics = [["accuracy", "Accuracy"], ["precision", "Precision"], ["recall", "Recall"], ["f1", "F1"]];
        const W = 640, H = 270, L = 40, B = 40, T = 14, gw = (W - L - 10) / metrics.length;
        let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Accuracy, macro precision, macro recall and macro F1 per model" style="width:100%;height:auto">`;
        for (let i = 0; i <= 4; i++) { const y = T + (H - T - B) * (1 - i / 4); s += `<line x1="${L}" x2="${W - 6}" y1="${y}" y2="${y}" stroke="#E5E5DB"/><text x="${L - 6}" y="${y + 4}" font-size="11" text-anchor="end" fill="#55635A">${i * 25}%</text>`; }
        metrics.forEach(([m, label], gi) => {
            const bw = Math.min(30, (gw - 18) / keys.length);
            keys.forEach((k, ki) => {
                const c = run.metrics[k].classification; const v = m === "accuracy" ? c.accuracy : c.macro[m];
                const h = (H - T - B) * (v || 0); const x = L + gi * gw + 9 + ki * bw; const y = H - B - h;
                s += `<rect x="${x}" y="${y}" width="${bw - 3}" height="${h}" rx="3" fill="${COLORS[k]}"><title>${esc(ARCH_NAMES[k])} ${label}: ${pct(v)}</title></rect>`;
                s += `<text x="${x + (bw - 3) / 2}" y="${y - 4}" font-size="11" text-anchor="middle" fill="#24392F">${Math.round((v || 0) * 100)}</text>`;
            });
            s += `<text x="${L + gi * gw + gw / 2}" y="${H - 18}" font-size="12" text-anchor="middle" fill="#344E41">${label}</text>`;
        });
        return s + "</svg>" + `<div class="legend">${keys.map((k) => `<span><i style="background:${COLORS[k]}"></i>${esc(ARCH_NAMES[k])}</span>`).join("")}</div>`;
    }
    function latencyBars(run) {
        const keys = ARCH.filter((k) => run.metrics[k] && run.metrics[k].latency && run.metrics[k].latency.median_ms != null);
        if (!keys.length) return '<p class="muted">No successful predictions, so no latency to show.</p>';
        const max = Math.max(...keys.map((k) => run.metrics[k].latency.p95_ms || run.metrics[k].latency.median_ms)) * 1.1 || 1;
        return keys.map((k) => { const l = run.metrics[k].latency;
            return `<div class="bar-row" style="grid-template-columns:90px 1fr 130px"><span>${esc(short(k))}</span>
              <div class="bar" title="median ${l.median_ms} ms · p95 ${l.p95_ms} ms"><div class="bar-fill" style="width:${(100 * l.median_ms) / max}%;background:${COLORS[k]}"></div></div>
              <span class="hint">${num(l.median_ms, 1)} / ${num(l.p95_ms, 1)} ms</span></div>`; }).join("") + '<p class="chart-note">Bar = median; numbers = median / 95th percentile.</p>';
    }
    function confusion(run, key, scoring) {
        const c = clsOf(run, key, scoring);
        if (!c || !c.labels) return '<p class="muted">No classification metrics for this model in this run.</p>';
        const labels = c.labels, cm = c.confusion_matrix;
        if (labels.length > 24) {
            const pairs = []; labels.forEach((t, i) => labels.forEach((p, j) => { if (i !== j && cm[i][j] > 0) pairs.push([t, p, cm[i][j]]); }));
            pairs.sort((a, b) => b[2] - a[2]);
            return `<p class="chart-note">${labels.length} classes is too many for a readable grid. Most frequent confusions (expected → predicted):</p>
              <div class="scroll"><table class="data"><thead><tr><th>Expected</th><th>Predicted</th><th>Count</th></tr></thead><tbody>${pairs.slice(0, 15).map((p) => `<tr><td>${esc(p[0])}</td><td>${esc(p[1] === "NO_MATCH" ? "no match" : p[1])}</td><td class="num">${p[2]}</td></tr>`).join("") || '<tr><td colspan="3">No confusions.</td></tr>'}</tbody></table></div>`;
        }
        const max = Math.max(1, ...cm.flat());
        return `<div class="scroll"><table class="heat"><thead><tr><th></th>${labels.map((l) => `<th title="${esc(l)}">${esc(trunc(l === "NO_MATCH" ? "no match" : l, 9))}</th>`).join("")}</tr></thead><tbody>${cm.map((row, i) =>
            `<tr><th class="row">${esc(labels[i] === "NO_MATCH" ? "no match" : labels[i])}</th>${row.map((v, j) => `<td style="background:rgba(${i === j ? "88,129,87" : "185,74,72"},${v ? 0.12 + 0.75 * (v / max) : 0});" title="expected ${esc(labels[i])}, predicted ${esc(labels[j])}: ${v}">${v || ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
            <p class="chart-note">Rows = expected, columns = predicted. Green diagonal = correct.</p>`;
    }
    function perClass(run, key, scoring) {
        const c = clsOf(run, key, scoring); if (!c) return '<p class="muted">No classification metrics for this model.</p>';
        const rows = Object.entries(c.per_class).filter(([, v]) => v.support > 0).sort((a, b) => a[1].f1 - b[1].f1);
        return `<div class="scroll"><table class="data"><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>${rows.map(([l, v]) => `<tr><td>${esc(l)}</td><td class="num">${pct(v.precision, 0)}</td><td class="num">${pct(v.recall, 0)}</td><td class="num">${pct(v.f1, 0)}</td><td class="num">${v.support}</td></tr>`).join("")}</tbody></table></div><p class="chart-note">Sorted by F1, weakest first. Classes with very few questions give unstable values.</p>`;
    }

    /* ---- run results */
    function selectionText(run) {
        const sel = run.selection || {}, d = run.dataset;
        const total = run.progress.total;
        if (!run.selection) return `${MODE_NAMES[run.mode] || run.mode}${run.sampled ? " (sample)" : ""} · ${total} questions`;
        const cat = sel.category ? String(sel.category).replace(/_/g, " ") : (d.kind === "safety" ? "All probe types" : "All categories");
        return `${MODE_NAMES[sel.mode] || sel.mode} · ${cat} · ${total} of ${sel.category_eligible} eligible`;
    }
    function summaryTable(run) {
        const kind = run.dataset.kind;
        if (run.safety) {
            const s = run.safety;
            return `<div class="scroll"><table class="data ev-sum"><thead><tr><th>Model</th><th>Emergency guidance shown</th><th>False alarms</th><th>Out-of-scope declined</th><th>Median ${tip(TIPS.median)}</th><th>P95 ${tip(TIPS.p95)}</th><th>Succeeded / failed ${tip(TIPS.failed)}</th></tr></thead><tbody>${ARCH.filter((k) => s.per_model[k] && run.metrics[k]).map((k) => { const p = s.per_model[k], l = run.metrics[k].latency || {};
                return `<tr><th scope="row">${esc(short(k))}<small>${esc(run.metrics[k].version || "")}</small></th><td class="num">${p.emergency_surfaced}/${p.emergency_total}</td><td class="num">${p.false_alarms}/${p.non_emergency_total}</td><td class="num">${p.oos_declined}/${p.oos_total}</td><td class="num">${l.median_ms == null ? "n/a" : num(l.median_ms, 1) + " ms"}</td><td class="num">${l.p95_ms == null ? "n/a" : num(l.p95_ms, 1) + " ms"}</td><td class="num">${run.metrics[k].valid_predictions} / ${run.metrics[k].failed}</td></tr>`; }).join("")}</tbody></table></div>`;
        }
        return `<div class="scroll"><table class="data ev-sum"><thead><tr><th>Model</th><th>Lenient accuracy ${tip(TIPS.lenient)}</th><th>Strict accuracy ${tip(TIPS.strict)}</th><th>Precision ${tip(TIPS.precision)}</th><th>Recall ${tip(TIPS.recall)}</th><th>F1 ${tip(TIPS.f1)}</th><th>Median ${tip(TIPS.median)}</th><th>P95 ${tip(TIPS.p95)}</th><th>No match ${tip(TIPS.nomatch)}</th><th>Succeeded / failed ${tip(TIPS.failed)}</th></tr></thead><tbody>${ARCH.map((k) => {
            const m = run.metrics[k]; if (!m || !m.key) return `<tr><th scope="row">${esc(short(k))}</th><td colspan="9" class="muted">No data.</td></tr>`;
            const head = `<th scope="row">${esc(short(k))}<small>${esc(m.version || "")}</small></th>`;
            if (!m.valid_predictions) return `<tr class="ev-fail">${head}<td colspan="9"><span class="bad">Unavailable.</span> ${esc(m.error || "Every prediction failed.")} No metrics are shown because no valid prediction exists. (failed ${m.failed}/${m.questions})</td></tr>`;
            const len = kind === "mapped" ? m.classification_lenient : m.classification, str = kind === "mapped" ? m.classification_strict : m.classification, c = m.classification, l = m.latency;
            return `<tr>${head}<td class="num"><b>${pct(len.accuracy)}</b></td><td class="num">${pct(str.accuracy)}</td><td class="num">${pct(c.macro.precision)}</td><td class="num">${pct(c.macro.recall)}</td><td class="num">${pct(c.macro.f1)}</td><td class="num">${num(l.median_ms, 1)} ms</td><td class="num">${num(l.p95_ms, 1)} ms</td><td class="num">${m.no_confident_match}</td><td class="num">${m.valid_predictions} / ${m.failed}</td></tr>`; }).join("")}</tbody></table></div>
            <p class="chart-note">Precision, recall and F1 are macro averages over classes present in the data${kind === "mapped" ? " and use lenient scoring" : ""}. n = ${run.progress.completed} questions per model.${kind === "mapped" ? "" : " Exact-label dataset: lenient and strict accuracy are the same."}</p>`;
    }
    function failuresPanel(run) {
        const fails = []; (run.per_question || []).forEach((r) => ARCH.forEach((k) => { const x = r.models[k]; if (isFailed(x)) fails.push({ id: r.id, k, status: x.status, error: x.error }); }));
        const ex = (run.dataset.validation && run.dataset.validation.excluded) || [];
        let h = "";
        h += `<details class="fold"><summary>Excluded questions (${ex.length}) ${tip("Removed for every model alike before the run.")}</summary>${ex.length ? `<div class="scroll"><table class="data"><thead><tr><th>Row</th><th>Question</th><th>Reason</th></tr></thead><tbody>${ex.map((x) => `<tr><td>${esc(x.id)}</td><td>${esc(x.question)}</td><td>${esc(x.reason)}</td></tr>`).join("")}</tbody></table></div>` : '<p class="muted">No rows were excluded.</p>'}</details>`;
        h += `<details class="fold"><summary>Model failures (${fails.length})</summary>${fails.length ? `<div class="scroll"><table class="data"><thead><tr><th>Question</th><th>Model</th><th>Status</th><th>Error</th></tr></thead><tbody>${fails.slice(0, 200).map((f) => `<tr><td>${esc(f.id)}</td><td>${esc(short(f.k))}</td><td>${esc(f.status)}</td><td>${esc(f.error || "")}</td></tr>`).join("")}</tbody></table></div>${fails.length > 200 ? `<p class="hint">Showing the first 200 of ${fails.length}.</p>` : ""}` : '<p class="muted">No model call failed in this run.</p>'}</details>`;
        return h;
    }
    function renderRun(run) {
        $("#evalEmpty").classList.add("hidden"); const box = $("#evalResults"); box.classList.remove("hidden");
        const d = run.dataset, kind = d.kind;
        const lim = (run.limitations || []).map((l) => `<li>${esc(l)}</li>`).join("");
        const hasCls = ARCH.some((k) => run.metrics[k] && run.metrics[k].classification);
        const tabs = run.safety ? [["safety", "Safety results"], ["preds", "Question results"], ["latency", "Latency"]]
            : [...(hasCls ? [["cm", "Confusion matrices"], ["pc", "Per-class metrics"]] : []), ["preds", "Question results"], ["latency", "Latency"]];
        let h = `<div class="panel ev-result"><div class="ev-result-head"><div><h2>Results</h2>
              <p class="muted ev-meta"><strong>${esc(d.title)}</strong> · ${esc(selectionText(run))}<br>Run <code>${esc(run.run_id)}</code> · ${esc(when(run.created_at))} · dataset version <code>${esc(d.version || "n/a")}</code>
              · <span class="pill ${run.status === "completed" ? "" : "bad"}">${esc(run.status)}</span> ${run.sampled ? '<span class="pill warn">sample, not all eligible questions</span>' : '<span class="pill">all eligible questions</span>'}</p></div>
              <a class="btn secondary small" href="/api/comparison/evaluation/runs/${encodeURIComponent(run.run_id)}/export.csv">Download CSV</a></div>
              <p class="ev-counts">Evaluated <strong>${run.progress.completed}</strong> of ${d.rows_in_file} rows in the file · excluded by validation <strong>${d.rows_excluded || 0}</strong> · model failures <strong>${run.progress.errors}</strong>.</p>
              ${run.error ? `<p class="error-text">Run error: ${esc(run.error)}</p>` : ""}
              ${summaryTable(run)}
              ${kind === "mapped" ? `<div class="banner info ev-map"><span aria-hidden="true">ⓘ</span><div>Question-bank labels are 19 coarse categories; the models predict 91 intents. Scores use the author-defined mapping in <code>datasets/evaluation_label_map.json</code>, so they depend on that mapping.</div></div>` : ""}
              ${lim ? `<details class="fold"><summary>Limitations of this run</summary><ul>${lim}</ul></details>` : ""}
              ${failuresPanel(run)}</div>`;
        h += `<div class="panel"><div class="ev-tabs" role="tablist" aria-label="Detailed results">${tabs.map(([id, label], i) => `<button type="button" class="ev-tab" role="tab" id="evt-${id}" data-evtab="${id}" aria-selected="${i === 0}" aria-controls="evp-${id}" tabindex="${i === 0 ? 0 : -1}">${esc(label)}</button>`).join("")}</div>
            ${tabs.map(([id], i) => `<div class="ev-tabpanel ${i === 0 ? "" : "hidden"}" role="tabpanel" id="evp-${id}" aria-labelledby="evt-${id}"></div>`).join("")}</div>`;
        box.innerHTML = h;
        const cmModelOptions = ARCH.filter((k) => run.metrics[k] && run.metrics[k].classification).map((k) => `<option value="${k}">${esc(ARCH_NAMES[k])}</option>`).join("");
        const scoringSel = kind === "mapped" ? `<select id="%S" aria-label="Scoring"><option value="lenient">Lenient scoring</option><option value="strict">Strict scoring</option></select>` : "";
        tabs.forEach(([id]) => {
            const p = $("#evp-" + id);
            if (id === "cm") {
                p.innerHTML = `<div class="ev-bar"><select id="cmModel" aria-label="Model">${cmModelOptions}</select>${scoringSel.replace("%S", "cmScoring")}</div><div id="cmBody"></div>`;
                const upd = () => { $("#cmBody").innerHTML = confusion(run, $("#cmModel").value, ($("#cmScoring") || {}).value); };
                $("#cmModel").addEventListener("change", upd); if ($("#cmScoring")) $("#cmScoring").addEventListener("change", upd); upd();
            } else if (id === "pc") {
                p.innerHTML = `<div class="ev-bar"><select id="pcModel" aria-label="Model">${cmModelOptions}</select>${scoringSel.replace("%S", "pcScoring")}</div><div id="pcBody"></div>`;
                const upd = () => { $("#pcBody").innerHTML = perClass(run, $("#pcModel").value, ($("#pcScoring") || {}).value); };
                $("#pcModel").addEventListener("change", upd); if ($("#pcScoring")) $("#pcScoring").addEventListener("change", upd); upd();
            } else if (id === "safety") { p.innerHTML = renderSafety(run); }
            else if (id === "latency") { p.innerHTML = latencyPanel(run); }
            else if (id === "preds") { p.innerHTML = predictionsShell(run); bindPredictions(run); }
        });
        if (hasCls && !run.safety) {
            const holder = document.createElement("details"); holder.className = "fold"; holder.open = true;
            holder.innerHTML = `<summary>Visual comparison: accuracy, precision, recall, F1</summary><p class="chart-note" style="margin-top:8px">${kind === "mapped" ? "Lenient scoring." : "Exact intent match."} Macro averages over classes present in the data.</p>${groupedBars(run)}`;
            $(".ev-result", box).appendChild(holder);
        }
        const tl = $$(".ev-tab", box);
        const act = (id, focus) => tl.forEach((b) => { const on = b.dataset.evtab === id; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); $("#evp-" + b.dataset.evtab).classList.toggle("hidden", !on); });
        tl.forEach((b, i) => { b.addEventListener("click", () => act(b.dataset.evtab)); b.addEventListener("keydown", (e) => {
            if (e.key === "ArrowRight") act(tl[(i + 1) % tl.length].dataset.evtab, true); if (e.key === "ArrowLeft") act(tl[(i + tl.length - 1) % tl.length].dataset.evtab, true); }); });
    }
    function latencyPanel(run) {
        const keys = ARCH.filter((k) => run.metrics[k]);
        return `<div class="scroll"><table class="data"><thead><tr><th>Model</th><th>Mean</th><th>Median</th><th>P90</th><th>P95</th><th>Min</th><th>Max</th><th>n</th></tr></thead><tbody>${keys.map((k) => { const l = run.metrics[k].latency || {};
            return `<tr><th scope="row">${esc(short(k))}</th>${["mean_ms", "median_ms", "p90_ms", "p95_ms", "min_ms", "max_ms"].map((f) => `<td class="num">${l[f] == null ? "n/a" : num(l[f], 1) + " ms"}</td>`).join("")}<td class="num">${l.n || 0}</td></tr>`; }).join("")}</tbody></table></div>
            <div style="margin-top:14px">${latencyBars(run)}</div><p class="chart-note">Measured per question inside each pipeline on the machine that ran the evaluation (single run; not a benchmark of hardware or load). Failed calls are excluded.</p>`;
    }
    function predictionsShell(run) {
        const cats = [...new Set((run.per_question || []).map((r) => (run.dataset.kind === "safety" ? (r.extra || {}).kind : r.expected)).filter(Boolean))].sort();
        return `<div class="form-row ev-filters"><div class="field"><label for="qfSearch">Search question or label</label><input type="text" id="qfSearch" autocomplete="off"></div>
            <div class="field ev-narrow"><label for="qfModel">Model</label><select id="qfModel"><option value="">All models</option>${ARCH.map((k) => `<option value="${k}">${esc(short(k))}</option>`).join("")}</select></div>
            <div class="field ev-narrow"><label for="qfOut">Outcome</label><select id="qfOut"><option value="">Any</option><option value="wrong">Incorrect</option><option value="right">Correct</option><option value="nomatch">No match</option><option value="disagree">Models disagree</option><option value="failed">Model failed</option></select></div>
            <div class="field ev-narrow"><label for="qfCat">${run.dataset.kind === "safety" ? "Probe type" : "Expected category"}</label><select id="qfCat"><option value="">All</option>${cats.map((c) => `<option value="${esc(c)}">${esc(String(c).replace(/_/g, " "))}</option>`).join("")}</select></div></div>
            <div class="scroll"><table class="data" id="qTable"></table></div><div class="pager" id="qPager"></div>`;
    }
    function bindPredictions(run) {
        ["qfSearch", "qfModel", "qfOut", "qfCat"].forEach((id) => $("#" + id).addEventListener("input", () => { state.qpage = 0; renderQuestions(run); }));
        renderQuestions(run);
    }
    function outcomeOf(run, rec) {            // true / false / null (failed)
        if (isFailed(rec)) return null;
        if (run.safety) return null;
        return !!primaryOK(run, rec);
    }
    function renderQuestions(run) {
        const text = $("#qfSearch").value.toLowerCase(), mf = $("#qfModel").value, of = $("#qfOut").value, cf = $("#qfCat").value, per = 25, safety = !!run.safety;
        const rows = (run.per_question || []).filter((r) => {
            const cat = safety ? (r.extra || {}).kind : r.expected;
            if (cf && cat !== cf) return false;
            if (text && !(r.question.toLowerCase().includes(text) || String(r.expected).toLowerCase().includes(text))) return false;
            const recs = (mf ? [r.models[mf]] : Object.values(r.models)).filter(Boolean);
            if (of === "failed") return recs.some(isFailed);
            if (of === "nomatch") return recs.some((x) => x.status === "no_match" || x.predicted === "NO_MATCH");
            if (safety) { if (of === "wrong") return recs.some((x) => !isFailed(x) && ((r.expected === "1" && !x.safety_override) || (r.expected === "0" && (r.extra || {}).kind === "out_of_scope" && x.status !== "no_match") || (r.expected === "0" && x.safety_override))); return true; }
            if (of === "wrong") return recs.some((x) => outcomeOf(run, x) === false);
            if (of === "right") return recs.length > 0 && recs.every((x) => outcomeOf(run, x) === true);
            if (of === "disagree") { const o = Object.values(r.models).map((x) => outcomeOf(run, x)); return new Set(o).size > 1; }
            return true;
        });
        const pages = Math.max(1, Math.ceil(rows.length / per)); state.qpage = Math.min(state.qpage, pages - 1);
        const slice = rows.slice(state.qpage * per, (state.qpage + 1) * per); const keys = mf ? [mf] : ARCH.filter((k) => run.metrics[k]);
        const cellFor = (r, k) => { const x = r.models[k]; if (!x) return "<td></td>";
            if (isFailed(x)) return `<td><span class="bad">failed</span><br><span class="hint">${esc(trunc(x.error || "", 60))}</span></td>`;
            if (safety) { const em = r.expected === "1", oos = (r.extra || {}).kind === "out_of_scope";
                const good = em ? !!x.safety_override : oos ? x.status === "no_match" : !x.safety_override;
                return `<td><span class="${good ? "ok" : "bad"}">${good ? "✓" : "✗"}</span> ${em ? (x.safety_override ? "guidance shown" : "guidance NOT shown") : oos ? (x.status === "no_match" ? "declined" : "answered") : (x.safety_override ? "false alarm" : "normal reply")}<br><span class="hint">${esc(x.intent || "—")} · ${x.inference_ms == null ? "" : num(x.inference_ms, 0) + " ms"}</span></td>`; }
            const ok = primaryOK(run, x), strictNote = run.dataset.kind === "mapped" && x.correct_lenient && !x.correct_strict ? ' <span class="pill warn" title="Counts as correct only under lenient scoring">lenient only</span>' : "";
            return `<td><span class="${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"}</span> ${esc(x.predicted === "NO_MATCH" ? "no match" : x.predicted)}${strictNote}<br><span class="hint">${esc(x.intent || "—")} · ${x.inference_ms == null ? "" : num(x.inference_ms, 0) + " ms"}</span></td>`; };
        $("#qTable").innerHTML = `<thead><tr><th>ID</th><th>Question</th><th>Lang</th><th>${safety ? "Probe · expected" : "Expected"}</th>${keys.map((k) => `<th>${esc(short(k))}</th>`).join("")}</tr></thead><tbody>${slice.map((r) =>
            `<tr><td>${esc(r.id)}</td><td class="ev-q">${esc(r.question)}</td><td>${esc(LANG[r.lang] || r.lang || "")}</td><td>${safety ? esc(String((r.extra || {}).kind || "").replace(/_/g, " ")) + " · " + (r.expected === "1" ? "emergency" : "not emergency") : esc(r.expected)}</td>${keys.map((k) => cellFor(r, k)).join("")}</tr>`).join("") || `<tr><td colspan="${4 + keys.length}" class="muted">No rows match the filters.</td></tr>`}</tbody>`;
        $("#qPager").innerHTML = `<span>${rows.length} rows · page ${state.qpage + 1} of ${pages}</span><button class="btn secondary small" id="pgPrev" ${state.qpage === 0 ? "disabled" : ""}>Previous</button><button class="btn secondary small" id="pgNext" ${state.qpage >= pages - 1 ? "disabled" : ""}>Next</button>`;
        $("#pgPrev").onclick = () => { state.qpage--; renderQuestions(run); }; $("#pgNext").onclick = () => { state.qpage++; renderQuestions(run); };
    }
    function renderSafety(run) {
        const s = run.safety, e = s.emergency_detection;
        const langRows = Object.entries(s.by_language_recall).map(([l, v]) => `<tr><td>${esc(LANG[l] || l)}</td><td class="num">${v.detected}/${v.emergencies}</td><td class="num">${pct(v.recall, 0)}</td></tr>`).join("");
        return `<div class="eval-grid"><div class="metric-card"><h3>Emergency detection</h3><div class="sub">model-independent safety module · n=${e.n}</div><div class="metric-value">${pct(e.recall, 0)}</div><div class="metric-label">Recall (emergencies caught)</div>
              <div class="metric-detail"><div><b>${pct(e.precision, 0)}</b><small>Precision</small></div><div><b>${pct(e.f1, 0)}</b><small>F1</small></div><div><b>${pct(e.accuracy, 0)}</b><small>Accuracy</small></div></div></div>
              <div class="metric-card"><h3>Recall by language</h3><div class="scroll"><table class="data"><thead><tr><th>Language</th><th>Caught</th><th>Recall</th></tr></thead><tbody>${langRows}</tbody></table></div></div>
              <div class="metric-card"><h3>Missed / false alarms</h3><p class="${s.missed_emergencies.length ? "bad" : "ok"}">Missed emergencies: ${s.missed_emergencies.length}</p>${s.missed_emergencies.map((x) => `<p class="hint">${esc(x)}</p>`).join("")}<p class="${s.false_alarms.length ? "bad" : "ok"}">False alarms: ${s.false_alarms.length}</p>${s.false_alarms.map((x) => `<p class="hint">${esc(x)}</p>`).join("")}</div></div>
          <p class="chart-note">${esc(s.note)} Out-of-scope = non-health questions the model should decline instead of answering. These checks are separate from classification accuracy and do not show that any answer is medically safe.</p>`;
    }

    /* ============================================================ USER STUDY */
    const CRITERIA = [["helpfulness", "Helpfulness", "Would this help you decide what to do next?"], ["relevance", "Relevance", "Does it answer what was asked?"],
        ["clarity", "Clarity", "Is it easy to read and understand?"], ["trustworthiness", "Trustworthiness", "Does it feel reliable (your impression)?"],
        ["safety", "Perceived safety", "Does it feel appropriately cautious and safe?"]];
    async function initStudy() {
        state.studyLoaded = true; say("study-status", "");
        try {
            const { runs } = await api("/api/comparison/study/runs");
            const sel = $("#studyRun"); sel.innerHTML = "";
            if (!runs.length) { sel.innerHTML = '<option value="">No comparison runs yet</option>'; $("#studyForm").innerHTML = '<div class="empty-state"><h3>Nothing to rate yet</h3><p>Ask a question in the <strong>Chatbot Comparison</strong> tab first. Every comparison is saved and can then be rated here.</p></div>'; }
            else {
                runs.forEach((r) => { const o = document.createElement("option"); o.value = r.run_id; o.textContent = `${when(r.created_at)} - ${trunc(r.question, 70)}`; sel.appendChild(o); });
                const want = state.pendingRun && runs.some((r) => r.run_id === state.pendingRun) ? state.pendingRun : runs[0].run_id; sel.value = want; state.pendingRun = null; await loadStudyRun(want);
            }
        } catch (err) { say("study-status", err.message, "error"); }
        if (!$("#studyRun").dataset.bound) { $("#studyRun").dataset.bound = 1; $("#studyRun").addEventListener("change", (e) => e.target.value && loadStudyRun(e.target.value)); $("#studyReload").addEventListener("click", () => { state.studyLoaded = false; initStudy(); }); }
        loadSummary();
    }
    function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
    async function loadStudyRun(runId) {
        try { const { run } = await api(`/api/comparison/study/run/${encodeURIComponent(runId)}`); renderStudyForm(run); say("study-status", ""); }
        catch (err) { say("study-status", err.message, "error"); $("#studyForm").innerHTML = ""; }
    }
    function renderStudyForm(run) {
        const order = shuffle(ARCH); const letters = ["A", "B", "C"]; const box = $("#studyForm");
        box.innerHTML = `<div class="panel"><h2>Question</h2><div class="q-bubble" style="display:inline-block">${esc(run.question)}</div></div>` + order.map((k, idx) => {
            const r = run.responses[k]; const my = r.my_rating || {};
            const head = `<header><h3>Response ${letters[idx]}</h3><span class="pill grey" data-reveal="${k}" data-name="${esc(r.name || ARCH_NAMES[k])}${r.version ? " · " + esc(r.version) : ""}">model hidden</span></header>`;
            if (!r.ratable) return `<div class="rate-card">${head}<p class="muted">This model was unavailable or failed on this question, so there is nothing to rate.</p></div>`;
            return `<div class="rate-card" data-arch="${k}" data-pos="${idx + 1}">${head}<div class="rate-response md">${md(r.response)}</div><div class="rate-grid">${CRITERIA.map(([c, label, desc]) =>
                `<fieldset class="rate-row"><legend>${esc(label)}</legend><div><div class="scale" role="radiogroup" aria-label="${esc(label)}: ${esc(desc)}">${[1, 2, 3, 4, 5].map((n) =>
                    `<label><input type="radio" name="${k}-${c}" value="${n}" ${my[c] === n ? "checked" : ""}><span>${n}</span></label>`).join("")}<label class="na"><input type="radio" name="${k}-${c}" value="na" ${my[c] == null ? "checked" : ""}><span>N/A</span></label></div>
                    <div class="scale-hint"><span>1 = poor</span><span>${esc(desc)}</span><span>5 = excellent</span></div></div></fieldset>`).join("")}</div>
                <div class="field" style="margin-top:12px"><label for="cm-${k}">Optional comment (do not include personal details)</label><textarea class="field-input" id="cm-${k}" rows="2" maxlength="1000">${esc(my.comment || "")}</textarea></div></div>`;
        }).join("") + `<label class="consent"><input type="checkbox" id="consent"><span>I understand these ratings are stored under a pseudonymous ID together with the question and responses, and I consent to their use in this research. (This does not replace institutional ethics approval.)</span></label>
            <button class="btn" id="studySubmit" type="button">Save my ratings</button><p class="hint" style="margin-top:8px">Leave a row on N/A if it does not apply. Saving again for the same run updates your earlier ratings; it never creates duplicates.</p>`;
        $("#studySubmit") && $("#studySubmit").addEventListener("click", () => submitStudy(run));
    }
    async function submitStudy(run) {
        const ratings = {}, positions = {};
        $$("#studyForm .rate-card[data-arch]").forEach((cardEl) => {
            const k = cardEl.dataset.arch; positions[k] = Number(cardEl.dataset.pos); const r = {};
            CRITERIA.forEach(([c]) => { const v = ($(`input[name="${k}-${c}"]:checked`, cardEl) || {}).value; r[c] = !v || v === "na" ? null : Number(v); });
            r.comment = $(`#cm-${k}`).value.trim(); ratings[k] = r;
        });
        if (!$("#consent").checked) { say("study-status", "Please tick the consent box before saving.", "error"); $("#consent").focus(); return; }
        const any = Object.values(ratings).some((r) => CRITERIA.some(([c]) => r[c] != null));
        if (!any) { say("study-status", "Rate at least one criterion for at least one response (everything is still N/A).", "error"); return; }
        const btn = $("#studySubmit"); btn.disabled = true;
        try {
            const r = await api("/api/comparison/study/submit", { method: "POST", body: JSON.stringify({ run_id: run.run_id, ratings, positions, consent: true }) });
            say("study-status", `Saved. ${r.created} new and ${r.updated} updated rating${r.saved === 1 ? "" : "s"}${r.skipped ? `; ${r.skipped} response${r.skipped === 1 ? "" : "s"} skipped (all N/A or unavailable)` : ""}. Thank you.`, "success");
            $$("[data-reveal]").forEach((p) => { p.textContent = p.dataset.name; p.className = "pill"; });
            window.scrollTo({ top: 0, behavior: "smooth" }); loadSummary();
        } catch (err) { say("study-status", err.message, "error"); }
        finally { btn.disabled = false; }
    }
    async function loadSummary() {
        const box = $("#studySummary");
        try {
            const { data } = await api("/api/comparison/study/summary");
            if (!data.completed_ratings) { box.innerHTML = '<div class="empty-state"><h3>No participant ratings yet</h3><p>Aggregate results appear here once ratings are saved. Nothing is shown until real data exists.</p></div>'; return; }
            let h = `<div class="eval-grid"><div class="metric-card"><div class="metric-value">${data.participants}</div><div class="metric-label">Participants</div></div>
                <div class="metric-card"><div class="metric-value">${data.runs_rated}</div><div class="metric-label">Comparison runs rated</div></div>
                <div class="metric-card"><div class="metric-value">${data.completed_ratings}</div><div class="metric-label">Response ratings</div></div></div>`;
            if (!data.sufficient) h += `<div class="banner"><span aria-hidden="true">ⓘ</span><div>Only <strong>${data.participants}</strong> participant${data.participants === 1 ? "" : "s"} so far. Averages are shown once at least <strong>${data.min_participants}</strong> participants have rated, to avoid drawing conclusions from very small samples. Raw data is available in the CSV export.</div></div>`;
            else {
                h += `<div class="panel"><h2>Average perceived rating (1-5)</h2><p class="chart-note">${esc(data.note)} N/A answers are excluded from averages.</p>` + data.criteria.map((c) => {
                    const label = (CRITERIA.find((x) => x[0] === c) || [c, c])[1];
                    return `<h4 style="margin:14px 0 4px;font:800 14px Manrope">${esc(label)}</h4>` + ARCH.filter((k) => data.per_architecture[k]).map((k) => { const e = data.per_architecture[k]; const m = e.mean[c];
                        return `<div class="bar-row"><span>${esc(ARCH_NAMES[k].split(" (")[0])}</span><div class="bar"><div class="bar-fill" style="width:${m == null ? 0 : (m / 5) * 100}%;background:${COLORS[k]}"></div></div><span>${m == null ? "n/a" : m.toFixed(2)}</span></div><div class="hint" style="margin:-2px 0 4px 120px">n=${e.n_rated[c]} rated · ${e.not_applicable[c]} N/A</div>`; }).join("");
                }).join("") + "</div>";
            }
            box.innerHTML = h;
        } catch (err) { box.innerHTML = `<div class="status-message error">${esc(err.message)}</div>`; }
    }

    /* ----------------------------------------------------------------- boot */
    renderChips(); renderLatest(); grow(); activate((location.hash || "#compare").slice(1));
})();
