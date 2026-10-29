/* =========================================================
   MediChat - chat client
   Talks to:  POST /api/health-chat/ask        (question -> reply, persisted)
              GET  /api/conversations[?search] (sidebar)
              GET  /api/conversations/<id>     (open a conversation)
              POST /api/conversations/new      (new chat)
              POST /api/conversations/<id>/open
              DELETE /api/conversations/<id>
   Notes
   - The models classify a question into a health topic; they do not generate tokens, so the
     finished reply is rendered at once after a typing indicator. Nothing pretends to stream.
   - Markdown is rendered by escaping ALL text first and only then adding a small set of tags, so
     model or user text can never inject HTML.
========================================================= */
(() => {
    "use strict";

    const $ = (sel, root = document) => root.querySelector(sel);
    const els = {
        messages: $("#messages"), welcome: $("#welcomeScreen"), form: $("#chatForm"), input: $("#messageInput"),
        send: $("#sendBtn"), count: $("#charCount"), list: $("#convList"), search: $("#searchBox"),
        newChat: $("#newChatBtn"), banner: $("#banner"), menu: $("#mobileMenuBtn"), overlay: $("#mobileOverlay"),
        sidebar: $("#mcSidebar"),
    };
    const MAX = 1000;                                   // server limit for one question (comparison_service.MAX_QUESTION_CHARS)
    const state = { conversationId: null, contextTopic: null, busy: false, lastQuestion: null, searchTimer: null };

    /* ---------------------------------------------------------- safe markdown */
    const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

    function inline(text) {
        let t = esc(text);
        t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
        t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        t = t.replace(/(^|[\s(])_([^_]+)_(?=$|[\s).,;:!?])/g, "$1<em>$2</em>");
        return t;
    }

    function renderMarkdown(md) {
        const lines = String(md || "").replace(/\r/g, "").split("\n");
        const out = [];
        let list = null, para = [];
        const flushPara = () => { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } };
        const flushList = () => { if (list) { out.push(`<${list.tag}>` + list.items.map((i) => "<li>" + inline(i) + "</li>").join("") + `</${list.tag}>`); list = null; } };
        for (const raw of lines) {
            const line = raw.trimEnd();
            let m;
            if (!line.trim()) { flushPara(); flushList(); continue; }
            if ((m = line.match(/^(#{1,4})\s+(.*)$/))) { flushPara(); flushList(); out.push(`<h4 class="mc-md-h">${inline(m[2])}</h4>`); continue; }
            if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== "ul") { flushList(); list = { tag: "ul", items: [] }; } list.items.push(m[1]); continue; }
            if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== "ol") { flushList(); list = { tag: "ol", items: [] }; } list.items.push(m[1]); continue; }
            flushList();
            para.push(line.trim());
        }
        flushPara(); flushList();
        return out.join("");
    }

    /* ------------------------------------------------------------- helpers */
    function notify(message, kind = "") {
        if (!els.banner) return;
        els.banner.textContent = message || "";
        els.banner.className = "mc-banner" + (message ? " visible " + kind : "");
        if (message && kind !== "error") setTimeout(() => { if (els.banner.textContent === message) notify(""); }, 5000);
    }

    async function api(url, options = {}) {
        const res = await fetch(url, { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...options });
        let data = {};
        try { data = await res.json(); } catch (_) { /* non-JSON error page */ }
        if (res.status === 401 || data.login_required) { window.location.href = "/login"; throw new Error("Please sign in again."); }
        if (!res.ok || data.success === false) {
            const err = new Error(data.error || data.response || `Request failed (${res.status}).`);
            err.status = res.status;
            throw err;
        }
        return data;
    }

    const nearBottom = () => els.messages.scrollHeight - els.messages.scrollTop - els.messages.clientHeight < 140;
    function scrollLatest(force = false) { if (force || nearBottom()) els.messages.scrollTo({ top: els.messages.scrollHeight, behavior: "smooth" }); }
    function hideWelcome() { if (els.welcome) els.welcome.hidden = true; }
    function showWelcome() { if (els.welcome) els.welcome.hidden = false; }

    function setBusy(busy) {
        state.busy = busy;
        els.send.disabled = busy;
        els.input.setAttribute("aria-busy", busy ? "true" : "false");
        els.send.classList.toggle("is-loading", busy);
    }

    function autoGrow() {
        els.input.style.height = "auto";
        els.input.style.height = Math.min(els.input.scrollHeight, 200) + "px";
        const n = els.input.value.length;
        els.count.textContent = `${n} / ${MAX}`;
        els.count.hidden = n < MAX * 0.7;
        els.count.classList.toggle("over", n > MAX);
    }

    /* ------------------------------------------------------------ messages */
    function addUser(text) {
        const div = document.createElement("div");
        div.className = "mc-message-user";
        div.textContent = text;                          // textContent: never HTML
        els.messages.appendChild(div);
        scrollLatest(true);
        return div;
    }

    function addAssistant(markdown, meta) {
        const wrap = document.createElement("div");
        wrap.className = "mc-message-assistant";
        wrap.dataset.markdown = markdown;
        const body = document.createElement("div");
        body.className = "mc-md";
        body.innerHTML = renderMarkdown(markdown);
        wrap.appendChild(body);

        const bar = document.createElement("div");
        bar.className = "mc-msg-bar";
        const info = document.createElement("span");
        info.className = "mc-msg-meta";
        info.textContent = meta || "";
        const copy = document.createElement("button");
        copy.type = "button"; copy.className = "mc-msg-btn"; copy.textContent = "Copy";
        copy.setAttribute("aria-label", "Copy this response");
        copy.addEventListener("click", async () => {
            try { await navigator.clipboard.writeText(markdown.replace(/^#{1,4}\s+/gm, "").replace(/\*\*|_(?=\S)/g, "")); copy.textContent = "Copied"; }
            catch (_) { copy.textContent = "Press Ctrl+C"; }
            setTimeout(() => (copy.textContent = "Copy"), 1600);
        });
        bar.append(info, copy);
        wrap.appendChild(bar);
        els.messages.appendChild(wrap);
        scrollLatest(true);
        return wrap;
    }

    function addTyping() {
        const div = document.createElement("div");
        div.className = "mc-message-assistant mc-typing";
        div.setAttribute("role", "status");
        div.setAttribute("aria-label", "MediChat is preparing a reply");
        div.innerHTML = '<span></span><span></span><span></span>';
        els.messages.appendChild(div);
        scrollLatest(true);
        return div;
    }

    function addError(message, retry) {
        const div = document.createElement("div");
        div.className = "mc-message-assistant mc-error";
        div.setAttribute("role", "alert");
        const p = document.createElement("p");
        p.textContent = message;
        div.appendChild(p);
        if (retry) {
            const btn = document.createElement("button");
            btn.type = "button"; btn.className = "mc-msg-btn"; btn.textContent = "Retry";
            btn.addEventListener("click", () => { div.remove(); retry(); });
            div.appendChild(btn);
        }
        els.messages.appendChild(div);
        scrollLatest(true);
    }

    const LANG_NAME = { en: "English", hi: "Hindi", hinglish: "Hinglish" };
    function metaFor(data) {
        const r = data.result || {};
        const parts = [];
        if (r.status === "small_talk") parts.push("Conversation");
        else if (data.answered_by_name) parts.push("Answered by " + data.answered_by_name);
        const lang = r.language && r.language.lang;
        if (lang) parts.push(LANG_NAME[lang] || lang);
        if (r.inference_ms != null) parts.push(Math.round(r.inference_ms) + " ms");
        return parts.join(" · ");
    }

    /* ----------------------------------------------------------------- send */
    async function ask(question) {
        if (state.busy) return;
        question = question.trim();
        if (!question) return;
        if (question.length > MAX) { notify(`Please keep your message under ${MAX} characters.`, "error"); return; }
        hideWelcome();
        state.lastQuestion = question;
        addUser(question);
        els.input.value = ""; autoGrow();
        setBusy(true);
        const typing = addTyping();
        try {
            const data = await api("/api/health-chat/ask", {
                method: "POST",
                body: JSON.stringify({ question, conversation_id: state.conversationId, context_topic: state.contextTopic }),
            });
            typing.remove();
            state.conversationId = data.conversation_id || state.conversationId;
            state.contextTopic = data.next_context_topic || state.contextTopic;
            const text = data.reply || (data.result && data.result.response) || "";
            addAssistant(text, metaFor(data));
            loadConversations();
        } catch (err) {
            typing.remove();
            addError(err.message || "Something went wrong. Please try again.", () => ask(question));
        } finally {
            setBusy(false);
            els.input.focus();
        }
    }

    /* -------------------------------------------------------- conversations */
    function clearMessages() {
        els.messages.querySelectorAll(".mc-message-user, .mc-message-assistant").forEach((n) => n.remove());
    }

    async function openConversation(id) {
        try {
            const data = await api(`/api/conversations/${id}`);
            api(`/api/conversations/${id}/open`, { method: "POST" }).catch(() => {});
            clearMessages();
            state.conversationId = id;
            state.contextTopic = null;
            const msgs = (data.data && data.data.messages) || [];
            if (msgs.length) hideWelcome(); else showWelcome();
            msgs.forEach((m) => {
                if (m.user_message) addUser(m.user_message);
                if (m.bot_response) addAssistant(m.bot_response, m.chatbot_type ? "Answered by " + m.chatbot_type : "");
            });
            markActive();
            els.sidebar.classList.remove("open"); els.overlay.classList.remove("show");
            scrollLatest(true);
        } catch (err) { notify(err.message, "error"); }
    }

    async function newConversation() {
        if (state.busy) return;
        try {
            const data = await api("/api/conversations/new", { method: "POST" });
            clearMessages();
            state.conversationId = data.conversation_id;
            state.contextTopic = null;
            showWelcome();
            await loadConversations();
            els.input.focus();
            els.sidebar.classList.remove("open"); els.overlay.classList.remove("show");
        } catch (err) { notify(err.message, "error"); }
    }

    async function deleteConversation(id, title) {
        if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
        try {
            await api(`/api/conversations/${id}`, { method: "DELETE" });
            if (state.conversationId === id) { clearMessages(); showWelcome(); state.conversationId = null; state.contextTopic = null; }
            loadConversations();
        } catch (err) { notify(err.message, "error"); }
    }

    function markActive() {
        els.list.querySelectorAll(".mc-conversation-item").forEach((n) =>
            n.classList.toggle("active", Number(n.dataset.id) === state.conversationId));
    }

    async function loadConversations() {
        const q = els.search.value.trim();
        try {
            const data = await api("/api/conversations" + (q ? "?search=" + encodeURIComponent(q) : ""));
            const rows = (data.data || []).filter((r) => !r.archived);
            els.list.innerHTML = "";
            if (!rows.length) {
                const empty = document.createElement("div");
                empty.className = "mc-conversation-empty";
                empty.textContent = q ? "No matching chats." : "No conversations yet. Ask your first question.";
                els.list.appendChild(empty);
                return;
            }
            rows.forEach((r) => {
                const item = document.createElement("div");
                item.className = "mc-conversation-item";
                item.dataset.id = r.id;
                const open = document.createElement("button");
                open.type = "button"; open.className = "mc-conversation-open";
                open.textContent = (r.pinned ? "📌 " : "") + (r.title || "New Conversation");
                open.addEventListener("click", () => openConversation(r.id));
                const del = document.createElement("button");
                del.type = "button"; del.className = "mc-conversation-del"; del.textContent = "×";
                del.setAttribute("aria-label", "Delete conversation " + (r.title || ""));
                del.addEventListener("click", (e) => { e.stopPropagation(); deleteConversation(r.id, r.title || "this conversation"); });
                item.append(open, del);
                els.list.appendChild(item);
            });
            markActive();
        } catch (err) {
            els.list.innerHTML = "";
            const e = document.createElement("div");
            e.className = "mc-conversation-empty";
            e.textContent = "Could not load conversations.";
            els.list.appendChild(e);
        }
    }

    /* ---------------------------------------------------------------- wiring */
    els.form.addEventListener("submit", (e) => { e.preventDefault(); ask(els.input.value); });
    els.input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(els.input.value); }
    });
    els.input.addEventListener("input", autoGrow);
    els.newChat.addEventListener("click", newConversation);
    els.search.addEventListener("input", () => { clearTimeout(state.searchTimer); state.searchTimer = setTimeout(loadConversations, 250); });
    document.querySelectorAll(".mc-quick-btn").forEach((b) => b.addEventListener("click", () => ask(b.dataset.question || "")));
    if (els.menu) els.menu.addEventListener("click", () => { els.sidebar.classList.toggle("open"); els.overlay.classList.toggle("show"); });
    if (els.overlay) els.overlay.addEventListener("click", () => { els.sidebar.classList.remove("open"); els.overlay.classList.remove("show"); });

    autoGrow();
    loadConversations();
})();
