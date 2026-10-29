import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Link2Off } from "lucide-react";
import { EmptyState, ErrorState, MedicalDisclaimer, Spinner } from "@/components/common";
import { Card } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api, ApiError } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { cn, formatDate } from "@/lib/utils";

type Shared = { title: string; created_at: string; messages: { role: "user" | "assistant"; content: string }[] };

export default function SharedConversationPage() {
  useDocumentTitle("Shared conversation");
  const { token = "" } = useParams();
  const q = useQuery({ queryKey: ["shared", token], queryFn: () => api.get<Shared>(`/shared/${encodeURIComponent(token)}`) });
  return (
    <div className="container max-w-3xl py-10">
      {q.isLoading && <div className="py-16 text-center"><Spinner /></div>}
      {q.error instanceof ApiError && q.error.status === 404 && (
        <EmptyState icon={Link2Off} title="This conversation is not shared" description="The link is invalid, or the owner stopped sharing it." />
      )}
      {q.error && !(q.error instanceof ApiError && q.error.status === 404) && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <p className="text-xs font-semibold uppercase tracking-wider text-secondary">Shared conversation · read-only</p>
          <h1 className="mt-1 text-2xl font-semibold">{q.data.title}</h1>
          <p className="text-sm text-muted-foreground">Started {formatDate(q.data.created_at)}</p>
          <Card className="mt-6 space-y-4 p-4 sm:p-6">
            {q.data.messages.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  m.role === "user" ? "rounded-br-md bg-primary text-primary-foreground" : "rounded-bl-md border bg-muted/40")}>
                  {m.role === "user" ? m.content : <Markdown text={m.content} />}
                </div>
              </div>
            ))}
          </Card>
          <MedicalDisclaimer compact className="mt-6" />
        </>
      )}
    </div>
  );
}
