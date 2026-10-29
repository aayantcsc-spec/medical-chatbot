import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ExternalLink, History, Link2, Pin, PinOff, Search, Share2, Trash2 } from "lucide-react";
import { EmptyState, ErrorState, PageHeader, SafetyBadge, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, Input, Skeleton } from "@/components/ui/primitives";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { archLabel, cn, formatDate, relativeTime } from "@/lib/utils";
import type { Conversation, ConversationDetail } from "@/types/api";

function Detail({ id, onDeleted }: { id: number; onDeleted: () => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["chat", id], queryFn: () => api.get<ConversationDetail>(`/chats/${id}`) });
  const [confirm, setConfirm] = useState(false);
  const [copied, setCopied] = useState(false);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["chat", id] }); qc.invalidateQueries({ queryKey: ["chats"] }); };
  const pin = useMutation({ mutationFn: (pinned: boolean) => api.patch(`/chats/${id}`, { pinned }), onSuccess: refresh });
  const share = useMutation({ mutationFn: (on: boolean) => on ? api.post(`/chats/${id}/share`) : api.del(`/chats/${id}/share`), onSuccess: refresh });
  const del = useMutation({ mutationFn: () => api.del(`/chats/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ["chats"] }); setConfirm(false); onDeleted(); } });

  if (q.isLoading) return <div className="p-10 text-center"><Spinner /></div>;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const c = q.data!;
  const url = c.share_token ? `${window.location.origin}/shared/${c.share_token}` : null;
  return (
    <Card className="flex h-full flex-col">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b p-4">
        <div className="min-w-0"><h2 className="truncate font-semibold">{c.title}</h2>
          <p className="text-xs text-muted-foreground">{formatDate(c.created_at)} · {archLabel(c.architecture)} · {c.messages.length} messages</p></div>
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" asChild><Link to={`/chat/${c.id}`}><ExternalLink /> Continue</Link></Button>
          <Button size="sm" variant="ghost" onClick={() => pin.mutate(!c.pinned)} aria-label={c.pinned ? "Unpin" : "Pin"}>{c.pinned ? <PinOff /> : <Pin />}</Button>
          <Button size="sm" variant="ghost" onClick={() => share.mutate(!c.shared)} loading={share.isPending} aria-label={c.shared ? "Stop sharing" : "Share"}><Share2 /></Button>
          <Button size="sm" variant="ghost" className="text-critical" onClick={() => setConfirm(true)} aria-label="Delete"><Trash2 /></Button>
        </div>
      </div>
      {url && (
        <div className="flex flex-wrap items-center gap-2 border-b bg-accent/40 px-4 py-2 text-xs">
          <Link2 className="size-3.5" /><span className="min-w-0 flex-1 truncate">{url}</span>
          <Button size="sm" variant="link" onClick={async () => { try { await navigator.clipboard.writeText(url); setCopied(true); } catch { /* blocked */ } }}>{copied ? "Copied" : "Copy link"}</Button>
          <span className="w-full text-muted-foreground">Anyone with this link can read this conversation. Stop sharing to revoke it.</span>
        </div>
      )}
      <div className="max-h-[60vh] flex-1 space-y-3 overflow-y-auto p-4 scrollbar-thin">
        {c.messages.map((m) => (
          <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn("max-w-[85%] rounded-2xl px-3.5 py-2 text-sm", m.role === "user" ? "rounded-br-md bg-primary text-primary-foreground" : "rounded-bl-md border bg-muted/40")}>
              {m.role === "user" ? m.content : <Markdown text={m.content} />}
              {m.role === "assistant" && <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                {archLabel(m.architecture)}{m.safety_status && m.safety_status !== "passed" && <SafetyBadge status={m.safety_status} />}</div>}
            </div>
          </div>
        ))}
      </div>
      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent title="Delete this conversation?" description="Its messages are removed permanently and any share link stops working.">
          <div className="flex justify-end gap-2"><DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button variant="destructive" loading={del.isPending} onClick={() => del.mutate()}>Delete</Button></div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

export default function HistoryPage() {
  useDocumentTitle("Chat History");
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const mode = "";
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => { const t = setTimeout(() => { setDebounced(q.trim()); setPage(1); }, 250); return () => clearTimeout(t); }, [q]);
  const list = useQuery({ queryKey: ["chats", { q: debounced, mode, page }], placeholderData: keepPreviousData,
    queryFn: () => api.page<Conversation[]>("/chats", { q: debounced || undefined, page, per_page: 15 }) });
  const rows = list.data?.data ?? [];
  const meta = list.data?.meta;

  return (
    <>
      <PageHeader title="Chat History" description="Your saved conversations. Only you can see them. Unsaved chats (when signed out) are never stored." />
      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search titles and messages" className="pl-9" aria-label="Search conversations" /></div>
      </div>
      {list.error && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.isLoading && <div className="space-y-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}</div>}
      {list.data && rows.length === 0 && (
        <EmptyState icon={History} title={debounced || mode ? "No matching conversations" : "No saved conversations yet"}
          description={debounced || mode ? "Try a different search or filter." : "Conversations you start in Chat are saved here automatically."}
          action={!(debounced || mode) && <Button asChild><Link to="/chat">Start a chat</Link></Button>} />
      )}
      {rows.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
          <div>
            <Card className="divide-y overflow-hidden">
              {rows.map((c) => (
                <button key={c.id} onClick={() => setSelected(c.id)} aria-current={selected === c.id}
                  className={cn("flex w-full items-start gap-3 p-3.5 text-left hover:bg-muted/50", selected === c.id && "bg-accent/60")}>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1.5 truncate text-sm font-medium">{c.pinned && <Pin className="size-3 shrink-0 text-primary" />}{c.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{c.last_message}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5"><Badge variant="muted">{archLabel(c.architecture)}</Badge>
                      <Badge variant="outline">{c.message_count} turns</Badge>{c.shared && <Badge variant="default">Shared</Badge>}</div>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground" title={formatDate(c.updated_at)}>{relativeTime(c.updated_at)}</span>
                </button>
              ))}
            </Card>
            {meta && meta.pages > 1 && (
              <div className="mt-3 flex items-center justify-between text-sm">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft /> Previous</Button>
                <span className="text-muted-foreground">Page {meta.page} of {meta.pages} · {meta.total} total</span>
                <Button variant="outline" size="sm" disabled={page >= meta.pages} onClick={() => setPage((p) => p + 1)}>Next <ChevronRight /></Button>
              </div>
            )}
          </div>
          <div className="lg:sticky lg:top-20 lg:self-start">
            {selected ? <Detail key={selected} id={selected} onDeleted={() => setSelected(null)} />
              : <Alert variant="info">Select a conversation to read it, continue it, share it or delete it.</Alert>}
          </div>
        </div>
      )}
    </>
  );
}
