import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Award, Ban, GitCompareArrows, Info, Scale, Siren, Timer } from "lucide-react";
import { ChartCard, MetricBars } from "@/components/charts";
import { ErrorState, PageHeader, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, CardContent, CardHeader, Label, Progress, Skeleton, Textarea } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { ARCH_KIND, archColor, archLabel, BOTS, cn, ms } from "@/lib/utils";
import type { BotInfo, BotResult, BotScore, Comparison } from "@/types/api";

type Options = { bots: BotInfo[]; examples: { emoji: string; category: string; question: string }[]; topic_count: number };

function ScoreRow({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      {value === null || value === undefined ? <span className="text-muted-foreground">not scored</span> : <Progress value={value} label={label} className="h-1.5" />}
      <span className="text-right font-medium tabular">{value ?? "—"}</span>
    </div>
  );
}

function BotCard({ r, s, winner, tied }: { r: BotResult; s?: BotScore; winner: boolean; tied: boolean }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="h-full">
      <Card className={cn("flex h-full flex-col overflow-hidden", winner && "ring-2 ring-primary/50")}>
        <div className="h-1" style={{ background: archColor(r.key) }} aria-hidden />
        <CardHeader className="gap-2 pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{ARCH_KIND[r.key]}</p>
              <h3 className="font-semibold">{archLabel(r.key)}</h3>
            </div>
            {winner ? <Badge variant="success"><Award className="size-3" />Best</Badge> : tied ? <Badge><Scale className="size-3" />Tied</Badge> : <StatusBadge status={r.status} />}
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline" title="Model inference time, measured on the server"><Timer className="size-3" />{ms(r.inference_ms)}</Badge>
            {r.intent_title && <Badge variant="muted">Topic: {r.intent_title}</Badge>}
            {r.safety_override && <Badge variant="critical"><Siren className="size-3" />Urgent response</Badge>}
            {s && !s.eligible && s.excluded_reason && <Badge variant="warning"><Ban className="size-3" />Not compared</Badge>}
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          {r.error ? <Alert variant="critical" title="This chatbot could not answer">{r.error}</Alert>
            : <div className="max-h-80 overflow-y-auto rounded-lg border bg-background p-3 text-sm leading-relaxed scrollbar-thin"><Markdown text={r.response} /></div>}
          {s && (
            <div className="mt-auto space-y-1.5 rounded-lg bg-muted/60 p-3">
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Automated assessment</p>
              <ScoreRow label="Relevance" value={s.quality_parts?.relevance} />
              <ScoreRow label="Completeness" value={s.quality_parts?.completeness} />
              <ScoreRow label="Clarity" value={s.quality_parts?.clarity} />
              <ScoreRow label="Safety" value={s.safety} />
              {s.correctness !== null && <ScoreRow label="Correctness" value={s.correctness} />}
              {s.safety_level && <p className="pt-1 text-xs"><span className="text-muted-foreground">Safety check:</span>{" "}
                <span className={cn("font-medium", s.safety_level === "Unsafe" ? "text-critical" : s.safety_level === "Safe" ? "text-success" : "text-warning")}>{s.safety_level}</span>
                {" - "}{s.safety_notes.join("; ")}</p>}
              {!s.eligible && s.excluded_reason && <p className="text-xs text-warning">Not compared: {s.excluded_reason}</p>}
              {r.confidence !== null && <p className="text-[11px] text-muted-foreground">Model score {r.confidence.toFixed(2)} ({r.confidence_kind}). Not used to pick the best response.</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function ComparisonPage() {
  useDocumentTitle("Comparison");
  const [question, setQuestion] = useState("");
  const options = useQuery({ queryKey: ["comparison-options"], queryFn: () => api.get<Options>("/comparison/options"), staleTime: 300_000 });
  const run = useMutation({ mutationFn: (q: string) => api.post<Comparison>("/comparison/ask", { question: q }) });
  const submit = (q = question) => { if (q.trim()) { setQuestion(q); run.mutate(q.trim()); } };
  const d = run.data;
  const sel = d?.overall_selection;
  const results = d ? BOTS.map((k) => d.results[k]).filter(Boolean) as BotResult[] : [];

  return (
    <>
      <PageHeader title="Comparison" description="Ask one health question. The exact same question is sent to the Rule-Based, TF-IDF + SVM and DistilBERT chatbots, each running its own model." />
      <Card className="mb-6 p-5">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <Label htmlFor="cq">Your question</Label>
          <Textarea id="cq" value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={1000}
            placeholder="e.g. What can cause fever and headache?  (English, Hindi or Hinglish)"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
          <div className="flex flex-wrap gap-1.5">
            {(options.data?.examples ?? []).slice(0, 6).map((ex) => (
              <button type="button" key={ex.question} onClick={() => submit(ex.question)} disabled={run.isPending}
                className="rounded-full border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground">{ex.question}</button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button type="submit" loading={run.isPending} disabled={!question.trim()}><GitCompareArrows /> Compare responses</Button>
            {options.data?.bots.filter((b) => !b.available).map((b) => (
              <span key={b.key} className="text-xs text-critical">{archLabel(b.key)} unavailable: {b.error}</span>
            ))}
          </div>
        </form>
      </Card>

      {run.error && <ErrorState error={run.error} onRetry={() => submit()} />}
      {run.isPending && (
        <div className="grid gap-4 md:grid-cols-3" aria-busy="true">
          {BOTS.map((k) => <Card key={k} className="space-y-3 p-5"><p className="text-sm font-semibold">{archLabel(k)}</p><Skeleton className="h-32" /><Skeleton className="h-16" /></Card>)}
        </div>
      )}
      {d && sel && !run.isPending && (
        <div className="space-y-5">
          {d.safety.emergency && (
            <Alert variant="critical" title="Urgent response - this may be a medical emergency">
              Call <strong>112</strong> in India or your local emergency number now. Every chatbot shows urgent-care guidance instead of an ordinary answer.
            </Alert>
          )}
          <p className="text-sm text-muted-foreground">Question: <span className="font-medium text-foreground">“{d.question}”</span></p>
          <Card className={cn("border-l-4 p-5", sel.status === "winner" ? "border-l-primary" : "border-l-warning")}>
            <div className="flex flex-wrap items-center gap-2">
              {sel.status === "winner" ? <Award className="size-5 text-primary" /> : <Scale className="size-5 text-warning" />}
              <h2 className="font-semibold">{sel.status === "winner" ? `Best Response for This Question: ${archLabel(sel.winner_key)}` : "No Clear Winner"}</h2>
            </div>
            <p className="mt-2 text-sm">{sel.reason}</p>
            <p className="mt-2 flex gap-1.5 text-xs text-muted-foreground"><Info className="mt-px size-3.5 shrink-0" />
              Automated assessment for this question only - not human-validated medical correctness. Unsafe replies are never selected;
              the longest, fastest or most confident reply does not win by default.</p>
            <details className="mt-2 text-xs text-muted-foreground">
              <summary className="cursor-pointer font-medium text-foreground">How it is decided</summary>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                <li>Weights: {Object.entries(sel.method.weights).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(", ")} (re-balanced over what can be scored).</li>
                <li>{sel.method.ground_truth.available ? `Correctness is checked against the labelled dataset (${sel.method.ground_truth.dataset}).` : sel.method.ground_truth.note}</li>
                <li>A lead smaller than the tie margin, or a lead from speed alone, gives “No Clear Winner”.</li>
                <li>{sel.method.limits}</li><li>{sel.method.language_scope}</li>
              </ul>
            </details>
          </Card>
          <div className="grid gap-4 md:grid-cols-3">
            {results.map((r) => <BotCard key={r.key} r={r} s={sel.scores[r.key]} winner={sel.winner_key === r.key} tied={sel.tied_keys.includes(r.key)} />)}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Response time for this question" description="Model inference time on the server (browser rendering not included)."
              table={{ columns: ["Chatbot", "Inference time", "Status"], rows: results.map((r) => [archLabel(r.key), ms(r.inference_ms), r.status]) }}>
              <MetricBars height={200} data={results.map((r) => ({ key: r.key, label: archLabel(r.key), value: r.inference_ms, note: "Inference time" }))}
                format={(v) => `${v.toFixed(1)} ms`} />
            </ChartCard>
            <Card className="p-5">
              <h3 className="text-sm font-semibold">How the replies differ</h3>
              {d.notes.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{d.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                : <p className="mt-2 text-sm text-muted-foreground">No structural differences detected.</p>}
              <p className="mt-3 text-xs text-muted-foreground">{d.run_id ? "Saved - you can rate these replies (blinded) in User Study." : "Sign in to save comparisons for the User Study."}</p>
            </Card>
          </div>
        </div>
      )}
      {options.error && <ErrorState error={options.error} onRetry={() => options.refetch()} />}
    </>
  );
}
