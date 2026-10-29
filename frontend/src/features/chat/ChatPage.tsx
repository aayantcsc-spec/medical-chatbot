/* Chat as a consultation: MediChat on the left, the patient on the right, oldest first, composer at the bottom. */
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Copy, Eraser, HelpCircle, MessageSquarePlus, PanelLeft, RotateCcw, Search, SendHorizonal, ShieldAlert, Siren, Stethoscope, Timer, Trash2, UserRound } from "lucide-react";
import { EmptyState, ErrorState, SafetyBadge, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Input, Label, Select, Skeleton, Textarea } from "@/components/ui/primitives";
import { Dialog, DialogClose, DialogContent, Sheet, Tooltip } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api, ApiError } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { archLabel, cn, ms, relativeTime, toDate } from "@/lib/utils";
import type { BotInfo, BotKey, ChatMessage, ChatReply, Conversation, ConversationDetail } from "@/types/api";

type Options = { bots: BotInfo[]; examples: string[]; notice: string };
type QA = { q: ChatMessage; a: ChatMessage | null };
const PREF_KEY = "medichat-chat-bot";
const BOT_KEYS: BotKey[] = ["rule", "ml", "dl"];

function readPref(): BotKey {
  try {
    const v = localStorage.getItem(PREF_KEY) as BotKey | null;
    if (v && BOT_KEYS.includes(v)) return v;
  } catch { /* fall through */ }
  return "rule";
}

function time(value?: string) {
  const d = toDate(value) ?? new Date();
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/** messages are stored as alternating user / assistant turns -> question/answer pairs */
function toPairs(messages: ChatMessage[]): QA[] {
  const out: QA[] = [];
  for (const m of messages) {
    if (m.role === "user") out.push({ q: m, a: null });
    else if (out.length && !out[out.length - 1]!.a) out[out.length - 1]!.a = m;
  }
  return out;
}

function ConversationList({ activeId, onPick }: { activeId?: number; onPick?: () => void }) {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => { const t = setTimeout(() => setDebounced(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const list = useQuery({ queryKey: ["chats", { q: debounced }], queryFn: () => api.page<Conversation[]>("/chats", { q: debounced || undefined, per_page: 50 }) });
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="relative px-3 pb-2">
        <Search className="pointer-events-none absolute left-6 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search questions" aria-label="Search history" className="h-9 pl-9" />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2 scrollbar-thin">
        {list.isLoading && <div className="space-y-2 p-1">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}</div>}
        {list.error && <p className="p-3 text-xs text-critical">Could not load history.</p>}
        {list.data && list.data.data.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-muted-foreground">{debounced ? "Nothing matches your search." : "Your saved Q&A sessions appear here."}</p>
        )}
        <ul className="space-y-0.5">
          {list.data?.data.map((c) => (
            <li key={c.id}>
              <Link to={`/chat/${c.id}`} onClick={onPick} aria-current={c.id === activeId ? "page" : undefined}
                className={cn("block rounded-lg px-3 py-2 hover:bg-muted", c.id === activeId && "bg-accent text-accent-foreground hover:bg-accent")}>
                <span className="block truncate text-sm font-medium">{c.pinned ? "📌 " : ""}{c.title}</span>
                <span className="block truncate text-xs text-muted-foreground">{archLabel(c.architecture)} · {c.message_count ?? 0} questions · {relativeTime(c.updated_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

const GREETING = "Hello, I'm MediChat. What brings you in today? Tell me your symptoms, how long you have had them, and anything that makes them better or worse.";

function DoctorAvatar({ urgent = false }: { urgent?: boolean }) {
  return (
    <span className={cn("grid size-9 shrink-0 place-items-center rounded-full shadow-card", urgent ? "bg-critical text-white" : "bg-primary text-primary-foreground")} aria-hidden>
      {urgent ? <Siren className="size-4" /> : <Stethoscope className="size-4" />}
    </span>
  );
}

/** Left side of the consultation: MediChat speaking. */
function DoctorBubble({ name, urgent = false, children }: { name: string; urgent?: boolean; children: ReactNode }) {
  return (
    <motion.article initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
      aria-label="MediChat" className="flex items-start gap-3 pr-6 sm:pr-16">
      <DoctorAvatar urgent={urgent} />
      <div className="min-w-0 flex-1">
        <p className={cn("mb-1 text-xs font-semibold", urgent ? "text-critical" : "text-primary")}>{name}</p>
        <div className={cn("rounded-2xl rounded-tl-sm border px-4 py-3 shadow-card", urgent ? "border-critical/40 bg-critical-soft" : "bg-card")}>{children}</div>
      </div>
    </motion.article>
  );
}

/** Right side of the consultation: the patient (user). */
function PatientBubble({ msg }: { msg: ChatMessage }) {
  return (
    <motion.article initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
      aria-label="You" className="flex flex-row-reverse items-start gap-3 pl-6 sm:pl-16">
      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground shadow-card" aria-hidden><UserRound className="size-4" /></span>
      <div className="flex min-w-0 flex-col items-end">
        <p className="mb-1 text-xs font-semibold text-muted-foreground">You</p>
        <p className="whitespace-pre-wrap break-words rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-[15px] leading-relaxed text-primary-foreground shadow-card">{msg.content}</p>
        <time dateTime={msg.created_at} className="mt-1 text-[11px] text-muted-foreground">{time(msg.created_at)}</time>
      </div>
    </motion.article>
  );
}

function Turn({ pair, onRetry }: { pair: QA; onRetry?: () => void }) {
  const { q, a } = pair;
  const urgent = a?.safety_status === "emergency_override";
  const [copied, setCopied] = useState(false);
  const name = urgent ? "MediChat — Urgent response"
    : a?.architecture && BOT_KEYS.includes(a.architecture as BotKey) ? `MediChat · ${archLabel(a.architecture)}` : "MediChat";
  return (
    <>
      <PatientBubble msg={q} />
      {q.error ? (
        <DoctorBubble name="MediChat">
          <Alert variant="critical" title="This question could not be answered"
            action={onRetry && <Button size="sm" variant="outline" onClick={onRetry}><RotateCcw /> Retry</Button>}>{q.error}</Alert>
        </DoctorBubble>
      ) : !a ? (
        <DoctorBubble name="MediChat">
          <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status" aria-label="Finding an answer">
            <span className="flex gap-1" aria-hidden>{[0, 1, 2].map((i) => <span key={i} className="size-1.5 animate-bounce rounded-full bg-primary/70" style={{ animationDelay: `${i * 150}ms` }} />)}</span>
            Reviewing your question…
          </div>
        </DoctorBubble>
      ) : (
        <DoctorBubble name={name} urgent={urgent}>
          <Markdown text={a.content} className="break-words text-[15px] leading-relaxed" />
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-2 text-[11px] text-muted-foreground">
            <time dateTime={a.created_at}>{time(a.created_at)}</time>
            {a.response_time_ms !== null && a.response_time_ms !== undefined && <span className="inline-flex items-center gap-1"><Timer className="size-3" />{ms(a.response_time_ms)}</span>}
            {a.safety_status && a.safety_status !== "passed" && <SafetyBadge status={a.safety_status} />}
            {a.handled_by && !BOT_KEYS.includes(a.handled_by as BotKey) && <span>{a.handled_by}</span>}
            <button onClick={async () => { try { await navigator.clipboard.writeText(a.content); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard blocked */ } }}
              className="inline-flex items-center gap-1 hover:text-foreground" aria-label="Copy answer"><Copy className="size-3" />{copied ? "Copied" : "Copy"}</button>
          </div>
        </DoctorBubble>
      )}
    </>
  );
}

export default function ChatPage() {
  useDocumentTitle("Chat");
  const { conversationId } = useParams();
  const convId = conversationId ? Number(conversationId) : undefined;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [pref, setPref] = useState<BotKey>(readPref);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [drawer, setDrawer] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const options = useQuery({ queryKey: ["chat-options"], queryFn: () => api.get<Options>("/chat/options"), staleTime: Infinity });
  const detail = useQuery({ queryKey: ["chat", convId], enabled: !!convId, queryFn: () => api.get<ConversationDetail>(`/chats/${convId}`) });

  useEffect(() => { try { localStorage.setItem(PREF_KEY, pref); } catch { /* not remembered */ } }, [pref]);
  useEffect(() => {
    if (!convId) { setMessages([]); return; }
    if (detail.data) {
      setMessages(detail.data.messages);
      const a = detail.data.architecture as BotKey | null;
      if (a && BOT_KEYS.includes(a)) setPref(a);
    }
  }, [convId, detail.data]);

  const send = useMutation({
    mutationFn: (text: string) => api.post<ChatReply>("/chat", { message: text, bot: pref, conversation_id: convId ?? null }),
  });

  async function submit(text: string, retryOf?: string) {
    const clean = text.trim();
    if (!clean || send.isPending) return;
    const id = retryOf ?? `local-${Date.now()}`;
    const now = new Date().toISOString();
    setMessages((m) => retryOf ? m.map((x) => x.id === id ? { ...x, error: undefined, pending: true } : x)
                               : [...m, { id, role: "user", content: clean, created_at: now, pending: true }]);
    if (!retryOf) setInput("");
    try {
      const r = await send.mutateAsync(clean);
      setMessages((m) => [...m.map((x) => x.id === id ? { ...x, pending: false } : x),
        { id: `${id}-a`, role: "assistant", content: r.reply, created_at: new Date().toISOString(), handled_by: r.handled_by,
          safety_status: r.safety_status, response_time_ms: r.response_time_ms, architecture: r.bot }]);
      qc.invalidateQueries({ queryKey: ["chats"] });
      qc.invalidateQueries({ queryKey: ["analytics", "summary"] });
      if (r.conversation_id && r.conversation_id !== convId) {
        qc.setQueryData(["chat", r.conversation_id], undefined);
        navigate(`/chat/${r.conversation_id}`, { replace: true });
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Network error";
      setMessages((m) => m.map((x) => x.id === id ? { ...x, pending: false, error: msg } : x));
    }
    inputRef.current?.focus();
  }

  const del = useMutation({
    mutationFn: () => api.del(`/chats/${convId}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["chats"] }); setConfirmDelete(false); navigate("/chat"); },
  });

  const bots = options.data?.bots ?? [];
  const activeBot = useMemo(() => bots.find((b) => b.key === pref), [bots, pref]);
  const pairs = useMemo(() => toPairs(messages), [messages]);                    // oldest first, like a consultation
  const waiting = send.isPending;
  useEffect(() => { endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }); }, [messages]);

  const sidebar = (onPick?: () => void) => (
    <>
      <div className="space-y-3 p-3">
        <Button className="w-full" onClick={() => { onPick?.(); navigate("/chat"); setMessages([]); inputRef.current?.focus(); }}>
          <MessageSquarePlus /> New consultation
        </Button>
        <div className="space-y-2 rounded-lg border bg-background/60 p-3">
          <Label htmlFor="bot" className="text-xs text-muted-foreground">Chatbot answering your questions</Label>
          <Select id="bot" value={pref} className="h-9" onChange={(e) => setPref(e.target.value as BotKey)}>
            {(bots.length ? bots : BOT_KEYS.map((k) => ({ key: k, available: true }) as BotInfo)).map((b) => (
              <option key={b.key} value={b.key} disabled={!b.available}>{archLabel(b.key)}{!b.available ? " (unavailable)" : ""}</option>))}
          </Select>
          {activeBot?.architecture && <p className="text-[11px] leading-snug text-muted-foreground">{activeBot.architecture}</p>}
          {activeBot && !activeBot.available && <p className="text-[11px] text-critical">{activeBot.error}</p>}
        </div>
      </div>
      <p className="px-4 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">History</p>
      <ConversationList activeId={convId} onPick={onPick} />
    </>
  );

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100dvh-4rem)] sm:-mx-6 lg:-mx-8 lg:-my-8">
      <aside className="hidden w-72 shrink-0 flex-col border-r bg-card/60 md:flex" aria-label="History">{sidebar()}</aside>
      <Sheet open={drawer} onOpenChange={setDrawer} title="History">
        <div className="flex h-full flex-col bg-card text-card-foreground">{sidebar(() => setDrawer(false))}</div>
      </Sheet>

      <section className="flex min-w-0 flex-1 flex-col" aria-label="Consultation">
        <div className="shrink-0 border-b bg-card/60 px-4 py-3 sm:px-6">
          <div className="mx-auto flex w-full max-w-3xl items-center gap-2">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setDrawer(true)} aria-label="Open history"><PanelLeft /></Button>
            <DoctorAvatar />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-base font-semibold">{detail.data?.title ?? "New consultation"}</h1>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="size-1.5 rounded-full bg-success" aria-hidden />MediChat is answering with <span className="font-medium text-foreground">{archLabel(pref)}</span>
              </p>
            </div>
            {convId && <Tooltip content="Delete this session"><Button variant="ghost" size="icon" onClick={() => setConfirmDelete(true)} aria-label="Delete session"><Trash2 /></Button></Tooltip>}
            {!convId && messages.length > 0 && <Tooltip content="Clear"><Button variant="ghost" size="icon" onClick={() => setMessages([])} aria-label="Clear questions"><Eraser /></Button></Tooltip>}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6 sm:px-6" aria-live="polite">
            {convId && detail.isLoading && <div className="py-10 text-center"><Spinner label="Loading session" /></div>}
            {convId && detail.error && (detail.error instanceof ApiError && detail.error.status === 404
              ? <EmptyState title="Session not found" description="It may have been deleted." action={<Button asChild><Link to="/chat">Start a new consultation</Link></Button>} />
              : <ErrorState error={detail.error} onRetry={() => detail.refetch()} />)}

            {!(convId && (detail.isLoading || detail.error)) && (
              <DoctorBubble name="MediChat">
                <p className="text-[15px] leading-relaxed">{GREETING}</p>
                {!convId && pairs.length === 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><HelpCircle className="size-3.5" /> You could start with</p>
                    <div className="flex flex-wrap gap-2">
                      {(options.data?.examples ?? []).map((ex) => (
                        <button key={ex} onClick={() => submit(ex)} disabled={waiting}
                          className="rounded-full border bg-background px-3 py-1.5 text-left text-sm transition-colors hover:border-primary/50 hover:bg-accent">{ex}</button>
                      ))}
                    </div>
                  </div>
                )}
              </DoctorBubble>
            )}

            {pairs.map((p) => <Turn key={p.q.id} pair={p} onRetry={p.q.error ? () => submit(p.q.content, p.q.id) : undefined} />)}
            <div ref={endRef} />
          </div>
        </div>

        <form className="shrink-0 border-t bg-card/60 px-4 pb-3 pt-3 sm:px-6" onSubmit={(e) => { e.preventDefault(); submit(input); }}>
          <div className="mx-auto w-full max-w-3xl">
            <div className="flex items-end gap-2 rounded-2xl border bg-background p-2 shadow-card focus-within:ring-2 focus-within:ring-ring">
              <Label htmlFor="ask" className="sr-only">Your health question</Label>
              <Textarea id="ask" ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} rows={1} maxLength={1000}
                placeholder="Describe your symptoms or ask a health question…"
                className="max-h-40 min-h-[44px] flex-1 resize-none border-0 bg-transparent text-[15px] shadow-none focus-visible:ring-0"
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(input); } }} />
              <Button type="submit" disabled={!input.trim() || waiting} loading={waiting} className="rounded-xl">{!waiting && <SendHorizonal />} Send</Button>
            </div>
            <p className="mt-2 flex items-start gap-1.5 text-[11px] text-muted-foreground"><ShieldAlert className="mt-px size-3.5 shrink-0 text-warning" aria-hidden />
              <span className="flex-1">{options.data?.notice ?? "MediChat provides general health information. It cannot diagnose conditions or replace a doctor."} In an emergency call 112.</span>
              <span className="hidden tabular sm:inline">{input.length}/1000</span></p>
          </div>
        </form>
      </section>

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent title="Delete this session?" description="All its questions and answers are removed permanently.">
          {del.error && <Alert variant="critical" className="mb-3">{(del.error as Error).message}</Alert>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button variant="destructive" loading={del.isPending} onClick={() => del.mutate()}><Trash2 /> Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
