import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bot, Brain, ClipboardCheck, Cpu, FlaskConical, GitCompareArrows, ListChecks, MessageSquareText } from "lucide-react";
import { ErrorState, LoadingCards, MedicalDisclaimer } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { archColor, archLabel, ms, pct, relativeTime } from "@/lib/utils";
import type { Conversation, Overview } from "@/types/api";

interface Summary {
  activity: { conversations: number; messages: number; comparisons: number; recent_conversations: Conversation[] };
  experiments: { total: number; completed: number; latest: string | null };
  overview: Overview;
}

export const APPROACHES = [
  { key: "rule", icon: ListChecks, kind: "Rule-Based", name: "Rule-Based chatbot",
    text: "Predefined rules, keywords and phrase patterns map a question to a health topic. No training - fully explainable." },
  { key: "ml", icon: Cpu, kind: "Machine Learning", name: "TF-IDF + SVM",
    text: "Questions become TF-IDF word/character features; a linear SVM trained on labelled questions predicts the topic." },
  { key: "dl", icon: Brain, kind: "Deep Learning", name: "DistilBERT",
    text: "A fine-tuned DistilBERT transformer reads the whole question in context and predicts the topic." },
] as const;

const LINKS = [
  { to: "/chat", icon: MessageSquareText, title: "Chat", text: "Ask your own health question to one chatbot." },
  { to: "/comparison", icon: GitCompareArrows, title: "Comparison", text: "Send one question to all three and compare." },
  { to: "/model-evaluation", icon: FlaskConical, title: "Model Evaluation", text: "Measured correctness, safety, quality and speed." },
  { to: "/user-study", icon: ClipboardCheck, title: "User Study", text: "Rate replies without knowing which chatbot wrote them." },
];

export default function DashboardPage() {
  useDocumentTitle("Home");
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["analytics", "summary"], queryFn: () => api.get<Summary>("/analytics/summary") });

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border bg-card p-6 sm:p-8">
        <p className="text-sm font-medium text-primary">Welcome{user?.name ? `, ${user.name.split(" ")[0]}` : ""}</p>
        <h1 className="mt-1 text-2xl font-semibold sm:text-3xl">MediChat</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          MediChat compares different AI approaches for healthcare questions and evaluates their response quality, correctness, response time, and safety.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button size="lg" asChild><Link to="/chat"><MessageSquareText /> Ask a health question</Link></Button>
          <Button size="lg" variant="outline" asChild><Link to="/comparison"><GitCompareArrows /> Compare all three</Link></Button>
        </div>
      </section>

      <section aria-labelledby="approaches">
        <h2 id="approaches" className="mb-3 text-lg font-semibold">Three chatbot approaches</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {APPROACHES.map(({ key, icon: Icon, kind, name, text }) => (
            <Card key={key} className="p-5">
              <div className="mb-3 flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-lg bg-accent text-accent-foreground"><Icon className="size-5" aria-hidden /></span>
                <div><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{kind}</p><p className="font-semibold">{name}</p></div>
              </div>
              <p className="text-sm text-muted-foreground">{text}</p>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="go" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="go" className="sr-only">Sections</h2>
        {LINKS.map(({ to, icon: Icon, title, text }) => (
          <Link key={to} to={to} className="group flex items-start gap-3 rounded-xl border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/40">
            <Icon className="mt-0.5 size-5 text-primary" aria-hidden />
            <span className="min-w-0 flex-1"><span className="flex items-center gap-1 font-medium">{title}<ArrowRight className="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" /></span>
              <span className="block text-sm text-muted-foreground">{text}</span></span>
          </Link>
        ))}
      </section>

      {q.isLoading && <LoadingCards count={3} />}
      {q.error && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle>Research results</CardTitle>
              <Button variant="link" size="sm" asChild><Link to="/model-evaluation">Details <ArrowRight /></Link></Button>
            </CardHeader>
            <CardContent>
              {q.data.overview.evaluation_required ? (
                <p className="py-6 text-center text-sm text-muted-foreground">No evaluation results yet. <Link to="/model-evaluation" className="font-medium text-primary hover:underline">Run an evaluation</Link> to see measured results.</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-2">Chatbot</th><th>Held-out accuracy</th><th>Emergency guidance</th><th>Median time</th></tr></thead>
                      <tbody className="tabular">{q.data.overview.chatbots.map((b) => (
                        <tr key={b.key} className="border-t"><td className="py-2.5 font-medium"><span className="mr-2 inline-block size-2.5 rounded-sm align-middle" style={{ background: archColor(b.key) }} />{archLabel(b.key)}</td>
                          <td>{pct(b.correctness.held_out_accuracy)}</td><td>{pct(b.safety.emergency_guidance_rate)}</td><td>{ms(b.response_time.median_ms)}</td></tr>))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-3 text-sm"><span className="font-medium">{q.data.overview.overall.status === "winner" ? `Overall: ${archLabel(q.data.overview.overall.winner)}` : "No reliable overall winner"}</span>
                    <span className="text-muted-foreground"> - {q.data.overview.overall.reason}</span></p>
                  <p className="mt-1 text-xs text-muted-foreground">Held-out set n = {q.data.overview.runs.held_out_test?.n}. Correctness means the right health topic was recognised, not verified medical correctness.</p>
                </>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle>Recent conversations</CardTitle>
              <Button variant="link" size="sm" asChild><Link to="/history">All <ArrowRight /></Link></Button>
            </CardHeader>
            <CardContent>
              {q.data.activity.recent_conversations.length === 0
                ? <p className="py-6 text-center text-sm text-muted-foreground">No conversations yet.</p>
                : <ul className="divide-y">{q.data.activity.recent_conversations.map((c) => (
                    <li key={c.id}><Link to={`/chat/${c.id}`} className="flex items-center gap-3 rounded-md px-1 py-2.5 hover:bg-muted/50">
                      <Bot className="size-4 shrink-0 text-primary" />
                      <span className="min-w-0 flex-1 truncate text-sm">{c.title}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">{relativeTime(c.updated_at)}</span></Link></li>))}</ul>}
            </CardContent>
          </Card>
        </div>
      )}
      <MedicalDisclaimer />
    </div>
  );
}
