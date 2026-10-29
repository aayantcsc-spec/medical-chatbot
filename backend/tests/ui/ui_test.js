const { JSDOM, CookieJar } = require("jsdom");
const fs = require("fs");
const BASE = "http://127.0.0.1:5057";
const COOKIE = "session=" + fs.readFileSync(require("path").join(__dirname, "cookie.txt"), "utf8").trim();
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  PASS", m); } else { fail++; console.log("  FAIL", m); } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, ms = 90000, step = 150) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = fn(); if (v) return v; } catch (_) {} await sleep(step); } return null; }

async function open(path, opts = {}) {
  const jar = new CookieJar(); jar.setCookieSync(COOKIE + "; Path=/", BASE);
  let failNext = opts.failFirstAsk || false;
  const dom = await JSDOM.fromURL(BASE + path, {
    runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, cookieJar: jar,
    beforeParse(w) {
      w.fetch = (u, o = {}) => {
        if (failNext && String(u).includes("/api/health-chat/ask")) { failNext = false; return Promise.reject(new TypeError("network down")); }
        return fetch(new URL(u, BASE), { ...o, headers: { ...(o.headers || {}), Cookie: COOKIE } });
      };
      w.HTMLElement.prototype.scrollIntoView = () => {}; w.scrollTo = () => {}; w.Element.prototype.scrollTo = () => {};
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
      w.confirm = () => true; w.alert = () => { w.__alerted = true; };
    },
  });
  await until(() => dom.window.document.readyState === "complete", 15000);
  await sleep(300);
  return dom;
}
function type(dom, sel, text) { const el = dom.window.document.querySelector(sel); el.value = text; el.dispatchEvent(new dom.window.Event("input", { bubbles: true })); return el; }
function enter(dom, el, shift = false) { el.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Enter", shiftKey: shift, bubbles: true, cancelable: true })); }
const click = (dom, el) => el.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, cancelable: true }));

(async () => {
  /* ------------------------------------------------ COMPARISON */
  console.log("\n[Comparison tab]");
  let dom = await open("/comparison"); let d = dom.window.document;
  ok(d.querySelectorAll(".tab").length === 3, "three tabs present");
  ok(/Chatbot Comparison/.test(d.body.textContent) && /Model Evaluation/.test(d.body.textContent) && /User Study Results/.test(d.body.textContent), "existing tab names kept");
  ok(!!d.querySelector('a[href="/dashboard"]'), "Back to Dashboard link kept");
  ok(d.querySelectorAll("#chips .chip").length >= 9, "example chips rendered");
  ok(!d.getElementById("empty").classList.contains("hidden"), "empty state shown before first question");

  const Q = "Mujhe bukhar aur khansi ho rahi hai, kya karu?";
  let ta = type(dom, "#q", Q);
  enter(dom, ta, true);   // Shift+Enter must NOT submit
  await sleep(400); ok(d.querySelectorAll(".turn").length === 0, "Shift+Enter does not submit");
  enter(dom, ta);
  const turn = await until(() => d.querySelector(".turn"), 120000);
  ok(!!turn, "Enter submits and a comparison turn renders");
  ok(d.querySelectorAll(".turn .resp").length === 3, "three independent response cards");
  ok(d.querySelector(".q-bubble").textContent === Q, "original question shown verbatim");
  ok(/Hinglish/.test(turn.textContent), "language chip says Hinglish");
  ok(/Preprocessed for all three models as/.test(turn.textContent), "canonical preprocessing is disclosed");
  const names = [...d.querySelectorAll(".resp h3")].map((x) => x.textContent);
  ok(names.join("|").includes("Rule-Based") && names.join("|").includes("TF-IDF + SVM") && names.join("|").includes("DistilBERT"), "architecture names: " + names.join(" / "));
  ok([...d.querySelectorAll(".resp .sub")].every((x) => /·/.test(x.textContent)), "model version shown on every card");
  ok([...d.querySelectorAll(".resp")].every((c) => /Inference time/.test(c.textContent) && /\d ms/.test(c.textContent)), "measured inference time on every card");
  ok([...d.querySelectorAll(".resp")].every((c) => /Confidence/.test(c.textContent)), "confidence shown with its type note");
  ok(/Ho sakne wale karan/.test(d.querySelector(".resp").textContent), "reply is in Hinglish (rule card)");
  ok(!!d.querySelector(".turn-notes"), "differences summary rendered");
  ok(!/winner|best model/i.test(d.querySelector(".turn-notes").textContent.replace("No winner is declared", "")), "no winner declared");
  ok(!!d.querySelector("[data-rate]"), "link to rate in User Study present");
  const runId = d.querySelector("[data-rate]").dataset.rate;

  type(dom, "#q", '<img src=x onerror="alert(1)"> what is diabetes?');
  enter(dom, d.getElementById("q"));
  await until(() => d.querySelectorAll(".turn").length === 2, 60000);
  ok(d.querySelectorAll(".turn").length === 2 && d.querySelector("img") === null && !dom.window.__alerted, "HTML in a question is escaped (no <img>, no script run)");

  type(dom, "#q", "seene mein dard ho raha hai saans nahi aa rahi"); enter(dom, d.getElementById("q"));
  await until(() => d.querySelectorAll(".turn").length === 3, 60000);
  const emerg = d.querySelector(".turn"); // newest first
  ok(!!emerg.querySelector(".banner.danger"), "emergency question shows independent safety banner");
  ok([...emerg.querySelectorAll(".resp")].every((c) => /112/.test(c.textContent)), "all three replies carry the emergency number");

  /* ------------------------------------------------ EVALUATION */
  console.log("\n[Evaluation tab]");
  click(dom, d.getElementById("tab-eval"));
  await until(() => d.querySelectorAll("#evalDataset option").length === 4, 10000);
  ok(d.querySelectorAll("#evalDataset option").length === 4, "four datasets listed from the API");
  await until(() => !d.getElementById("evalEmpty").classList.contains("hidden"), 8000);
  ok(!d.getElementById("evalEmpty").classList.contains("hidden") && /No evaluation has been run yet/.test(d.getElementById("evalEmpty").textContent), "empty state explains how to start (no stuck 0 / N)");
  ok(/Quick test \(30\)/.test(d.getElementById("quickLabel").textContent), "quick test size shown: " + d.getElementById("quickLabel").textContent);
  d.getElementById("evalDataset").value = "multilingual"; d.getElementById("evalDataset").dispatchEvent(new dom.window.Event("change"));
  ok(/Full dataset \(52\)/.test(d.getElementById("fullLabel").textContent), "full size shown from dataset: " + d.getElementById("fullLabel").textContent);
  d.querySelector('input[name="evalMode"][value="full"]').checked = true;
  click(dom, d.getElementById("runEvalBtn"));
  await until(() => !d.getElementById("evalProgress").classList.contains("hidden"), 8000);
  ok(!d.getElementById("evalProgress").classList.contains("hidden"), "progress panel appears on run");
  const res = await until(() => /Evaluated/.test(d.getElementById("evalResults").textContent) && d.querySelectorAll(".metric-card").length >= 3 && d.getElementById("evalState").textContent === "completed", 150000);
  ok(!!res, "run completes and results render");
  ok(d.getElementById("evalDone").textContent === "52" && d.getElementById("evalTotal").textContent === "52", "progress ended at 52 / 52");
  const cards = [...d.querySelectorAll("#evalResults .metric-card")].map((c) => c.textContent);
  ok(cards.slice(0, 3).every((t) => /\d+(\.\d)?%/.test(t)), "three model cards show measured percentages");
  ok(!!d.querySelector("#evalResults svg"), "accuracy/precision/recall/F1 chart drawn");
  ok(!!d.querySelector("#qTable tbody tr"), "question-by-question table has rows");
  ok(!!d.querySelector('a[href*="export.csv"]'), "CSV download link present");
  await until(() => d.querySelectorAll("#evalRuns tbody tr").length === 1, 8000); ok(d.querySelectorAll("#evalRuns tbody tr").length === 1, "previous-runs table lists the saved run");
  const evalText = d.getElementById("evalResults").textContent;

  /* ------------------------------------------------ STUDY */
  console.log("\n[User Study tab]");
  click(dom, d.getElementById("tab-study"));
  await until(() => d.querySelectorAll("#studyRun option").length >= 3, 10000);
  ok(d.querySelectorAll("#studyRun option").length === 3, "study lists the user's 3 comparison runs");
  await until(() => d.querySelectorAll(".rate-card").length >= 3, 10000);
  ok(d.querySelectorAll(".rate-card").length === 3, "three blinded response cards (A/B/C)");
  ok([...d.querySelectorAll(".rate-card header h3")].map((x) => x.textContent).sort().join() === "Response A,Response B,Response C", "responses labelled A/B/C");
  ok([...d.querySelectorAll("[data-reveal]")].every((p) => p.textContent === "model hidden"), "model names hidden before saving");
  ok(d.querySelectorAll('.rate-card input[type="radio"][value="na"]:checked').length === 15, "every criterion defaults to N/A (5 x 3)");
  click(dom, d.getElementById("studySubmit"));
  await sleep(300);
  ok(/consent/i.test(d.getElementById("study-status").textContent), "saving without consent is blocked");
  d.getElementById("consent").checked = true;
  click(dom, d.getElementById("studySubmit"));
  await sleep(300);
  ok(/Rate at least one/.test(d.getElementById("study-status").textContent), "all-N/A submission is blocked with a message");
  const card = d.querySelector(".rate-card"); const arch = card.dataset.arch;
  d.querySelector(`input[name="${arch}-helpfulness"][value="4"]`).checked = true;
  d.querySelector(`input[name="${arch}-clarity"][value="5"]`).checked = true;
  d.getElementById("cm-" + arch).value = "clear and calm";
  click(dom, d.getElementById("studySubmit"));
  await until(() => /Saved\./.test(d.getElementById("study-status").textContent), 8000);
  ok(/Saved\. 1 new/.test(d.getElementById("study-status").textContent), "confirmation shown: " + d.getElementById("study-status").textContent.slice(0, 40));
  ok([...d.querySelectorAll("[data-reveal]")].some((p) => p.textContent !== "model hidden"), "model name revealed after saving");
  await until(() => /participant/i.test(d.getElementById("studySummary").textContent), 8000);
  ok(/Only\s+1\s+participant/.test(d.getElementById("studySummary").textContent) && !/Average perceived rating/.test(d.getElementById("studySummary").textContent), "aggregate withheld below minimum sample, count shown honestly");

  /* ---------------- reload: persistence */
  console.log("\n[Refresh persistence]");
  dom.window.close();
  dom = await open("/comparison#eval"); d = dom.window.document;
  const restored = await until(() => d.querySelectorAll(".metric-card").length >= 3 && /Hinglish \+ Hindi/.test(d.getElementById("evalResults").textContent), 15000);
  ok(!!restored, "after a refresh the saved evaluation is shown again, not reset");
  ok(d.getElementById("evalResults").textContent.includes(evalText.match(/Run\s+\S+/)[0]), "same run id restored");
  click(dom, d.getElementById("tab-study"));
  await until(() => d.querySelectorAll(".rate-card").length === 3, 10000);
  const pre = d.querySelector(`input[name="${arch}-helpfulness"][value="4"]`);
  ok(pre && pre.checked, "earlier rating is pre-filled when reopening the run");
  ok(d.getElementById(`cm-${arch}`).value === "clear and calm", "earlier comment pre-filled");
  dom.window.close();

  /* ------------------------------------------------ CHAT */
  console.log("\n[Chat page]");
  dom = await open("/chat", { failFirstAsk: true }); d = dom.window.document;
  ok(!!d.getElementById("messageInput") && !!d.getElementById("sendBtn"), "chat input present");
  ok(d.querySelectorAll(".mc-quick-btn").length >= 5, "quick prompts incl. Hindi/Hinglish");
  ta = type(dom, "#messageInput", "Mujhe bukhar aur khansi ho rahi hai, kya karu?");
  enter(dom, ta, true); await sleep(300);
  ok(d.querySelectorAll(".mc-message-user").length === 0, "Shift+Enter does not send");
  enter(dom, ta);
  await until(() => d.querySelector(".mc-error"), 8000);
  ok(!!d.querySelector(".mc-error") && /Retry/.test(d.querySelector(".mc-error").textContent), "network failure shows an error with a Retry button");
  click(dom, d.querySelector(".mc-error .mc-msg-btn"));
  await until(() => d.querySelector(".mc-message-assistant:not(.mc-typing):not(.mc-error) .mc-md"), 20000);
  const a1 = d.querySelector(".mc-message-assistant .mc-md");
  ok(!!a1 && /Ho sakne wale karan/.test(a1.textContent), "retry succeeds; Hinglish structured reply rendered");
  ok(d.querySelectorAll(".mc-message-user").length === 2 || d.querySelectorAll(".mc-message-user").length === 1, "user bubble(s) present");
  ok(!!a1.querySelector("h4.mc-md-h") && !!a1.querySelector("li, p"), "markdown rendered to headings/paragraphs");
  ok(!!d.querySelector(".mc-msg-bar .mc-msg-btn") && /Hinglish/.test(d.querySelector(".mc-msg-meta").textContent), "copy button + language/model meta line");
  ok(d.getElementById("welcomeScreen").hidden === true, "welcome screen hidden after first message");
  await until(() => d.querySelectorAll(".mc-conversation-item").length === 1, 8000);
  ok(d.querySelectorAll(".mc-conversation-item").length === 1, "conversation appears in sidebar history");

  type(dom, "#messageInput", "Namaste"); enter(dom, d.getElementById("messageInput"));
  await until(() => [...d.querySelectorAll(".mc-message-assistant")].some((x) => /Namaste! Main MediChat hoon/.test(x.textContent)), 20000);
  ok([...d.querySelectorAll(".mc-message-assistant")].some((x) => /Namaste! Main MediChat hoon/.test(x.textContent)), "greeting answered exactly as specified");
  ok(d.querySelectorAll(".mc-conversation-item").length === 1, "same conversation reused (no duplicate chats)");

  const nAssist = d.querySelectorAll(".mc-message-assistant").length;
  type(dom, "#messageInput", "<b>bold?</b> what is diabetes"); enter(dom, d.getElementById("messageInput"));
  await until(() => d.querySelectorAll(".mc-message-assistant:not(.mc-typing)").length > nAssist, 20000);
  const users = d.querySelectorAll(".mc-message-user"); ok(users[users.length - 1].textContent.includes("<b>bold?</b>") && d.querySelector(".mc-message-user b") === null, "user HTML shown as text, not executed");

  click(dom, d.getElementById("newChatBtn"));
  await until(() => d.querySelectorAll(".mc-message-user").length === 0, 8000);
  ok(d.querySelectorAll(".mc-message-user").length === 0 && d.getElementById("welcomeScreen").hidden === false, "New conversation clears the thread and shows the welcome screen");
  await until(() => d.querySelectorAll(".mc-conversation-open").length >= 2, 8000);
  const first = [...d.querySelectorAll(".mc-conversation-open")].find((b) => /^Mujhe bukhar/.test(b.textContent));
  click(dom, first);
  await until(() => d.querySelectorAll(".mc-message-user").length >= 2, 8000);
  ok(d.querySelectorAll(".mc-message-user").length >= 2, "opening a past conversation restores its messages from the database");
  dom.window.close();

  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("TEST CRASH", e); process.exit(2); });
