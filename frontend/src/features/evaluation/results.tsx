/* Result views for Model Evaluation and Home. */
import { AlertTriangle, Award, Download, Scale } from "lucide-react";
import { ChartCard, MetricBars } from "@/components/charts";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { archLabel, BOTS, cn, formatDate, ms, pct } from "@/lib/utils";
import type { Overview } from "@/types/api";

export interface ModelMetrics {
  key: string; version: string | null; architecture: string | null; available: boolean; error: string | null; questions: number;
  valid_predictions: number; failed: number; availability_rate: number | null; no_confident_match?: number;
  latency: { mean_ms: number | null; median_ms: number | null; p90_ms: number | null; p95_ms: number | null };
  classification?: { accuracy: number | null; macro: { precision: number; recall: number; f1: number } | null; n: number; correct: number } | null;
  classification_note?: string; response_estimates?: { keyword_coverage_mean: number; label: string; n: number };
}
export interface Run {
  run_id: string; status: string; created_at: string; finished_at: string | null; error: string | null;
  dataset: { name: string; title: string; kind: string; version: string | null; rows_usable: number; rows_excluded: number };
  selection: { selected: number; seed: number; category: string | null; mode: string };
  metrics: Record<string, ModelMetrics>; limitations: string[];
  safety?: { emergency_detection: { precision: number; recall: number; f1: number; n: number };
             per_model: Record<string, { emergency_recall: number | null; oos_decline_rate: number | null; false_alarms: number }> };
}

export function RunMeta({ items }: { items: (string | null | false | undefined)[] }) {
  return <div className="flex flex-wrap gap-1.5">{items.filter(Boolean).map((i) => <Badge key={String(i)} variant="outline">{i}</Badge>)}</div>;
}

/** Overall verdict + one chart per metric, all from the latest completed runs. */
export function OverviewResults({ o, compact = false }: { o: Overview; compact?: boolean }) {
  const bots = o.chatbots;
  const bars = (f: (b: Overview["chatbots"][number]) => number | null, note: string) =>
    bots.map((b) => ({ key: b.key, label: archLabel(b.key), value: f(b), note }));
  const n = (k: keyof Overview["runs"]) => o.runs[k]?.n;
  const winner = o.overall.status === "winner";
  return (
    <div className="space-y-4">
      <Card className={cn("border-l-4 p-5", winner ? "border-l-primary" : "border-l-warning")}>
        <div className="flex items-center gap-2">
          {winner ? <Award className="size-5 text-primary" /> : <Scale className="size-5 text-warning" />}
          <h2 className="font-semibold">{winner ? `Best-performing chatbot overall: ${archLabel(o.overall.winner)}` : "No reliable overall winner"}</h2>
        </div>
        <p className="mt-2 text-sm">{o.overall.reason}</p>
        {o.overall.fastest && <p className="mt-1 text-sm text-muted-foreground">Fastest (median inference time): {archLabel(o.overall.fastest)} - speed does not decide the winner.</p>}
        <p className="mt-2 text-xs text-muted-foreground">{o.overall.method}</p>
      </Card>
      <div className={cn("grid gap-4", compact ? "lg:grid-cols-2" : "lg:grid-cols-2 xl:grid-cols-3")}>
        <ChartCard title="Correctness" description={`Topic accuracy on the held-out test split${n("held_out_test") ? ` (n = ${n("held_out_test")})` : ""}. Higher is better.`}
          table={{ columns: ["Chatbot", "Held-out", "Macro F1", "Hindi/Hinglish", "Question bank", "Declined"],
                   rows: bots.map((b) => [archLabel(b.key), pct(b.correctness.held_out_accuracy), pct(b.correctness.held_out_macro_f1),
                                          pct(b.correctness.multilingual_accuracy), pct(b.correctness.question_bank_accuracy), b.correctness.declined ?? "—"]) }}>
          <MetricBars data={bars((b) => b.correctness.held_out_accuracy, "Held-out accuracy")} format={(v) => pct(v, 0)} domain={[0, 1]} emptyLabel="No run yet" />
        </ChartCard>
        <ChartCard title="Safety" description={`Emergency questions answered with urgent-care guidance${n("safety") ? ` (${n("safety")} probes)` : ""}. Higher is better.`}
          table={{ columns: ["Chatbot", "Emergency guidance", "Off-topic declined", "False alarms"],
                   rows: bots.map((b) => [archLabel(b.key), pct(b.safety.emergency_guidance_rate), pct(b.safety.off_topic_declined_rate), b.safety.false_alarms ?? "—"]) }}
          footer="Automated checks against the project's safety probe set - not a clinical validation. Use the table for off-topic declining.">
          <MetricBars data={bars((b) => b.safety.emergency_guidance_rate, "Emergency guidance")} format={(v) => pct(v, 0)} domain={[0, 1]} emptyLabel="No safety run yet" />
        </ChartCard>
        <ChartCard title="Off-topic questions declined" description="Non-health questions the chatbot correctly refused to answer. Higher is better."
          table={{ columns: ["Chatbot", "Declined"], rows: bots.map((b) => [archLabel(b.key), pct(b.safety.off_topic_declined_rate)]) }}>
          <MetricBars data={bars((b) => b.safety.off_topic_declined_rate, "Off-topic declined")} format={(v) => pct(v, 0)} domain={[0, 1]} emptyLabel="No safety run yet" />
        </ChartCard>
        <ChartCard title="Response quality (provisional)" description="Automated keyword-coverage estimate on the question bank. Not human-validated."
          table={{ columns: ["Chatbot", "Keyword coverage", "n"], rows: bots.map((b) => [archLabel(b.key), pct(b.quality.keyword_coverage), b.quality.n ?? "—"]) }}
          footer={bots[0]?.quality.label}>
          <MetricBars data={bars((b) => b.quality.keyword_coverage, "Keyword coverage")} format={(v) => pct(v, 0)} domain={[0, 1]} emptyLabel="Needs a question-bank run" />
        </ChartCard>
        <ChartCard title="Average response time" description="Median model inference time per question (ms). Lower is better."
          table={{ columns: ["Chatbot", "Median", "Mean", "p95"], rows: bots.map((b) => [archLabel(b.key), ms(b.response_time.median_ms), ms(b.response_time.mean_ms), ms(b.response_time.p95_ms)]) }}>
          <MetricBars data={bars((b) => b.response_time.median_ms, "Median")} format={(v) => `${v.toFixed(0)} ms`} emptyLabel="No run yet" />
        </ChartCard>
        <ChartCard title="Reliability" description="Questions answered without a model failure on the held-out run. Higher is better."
          table={{ columns: ["Chatbot", "Answered without error", "Failed", "Questions"],
                   rows: bots.map((b) => [archLabel(b.key), pct(b.reliability.answered_without_error), b.reliability.failed ?? "—", b.reliability.questions ?? "—"]) }}>
          <MetricBars data={bars((b) => b.reliability.answered_without_error, "Success rate")} format={(v) => pct(v, 0)} domain={[0, 1]} emptyLabel="No run yet" />
        </ChartCard>
      </div>
      {!compact && (
        <Alert variant="warning" title="Limitations">
          <ul className="list-disc space-y-1 pl-4">
            <li>Test questions are author-written, not real patient conversations; scores measure generalisation to new wording.</li>
            <li>Correctness = the chatbot recognised the right health topic. It does not prove the answer is medically correct.</li>
            <li>The Hindi/Hinglish and safety sets were written by the project team; treat them as regression checks.</li>
            <li>Response quality is an automated estimate. Human ratings are collected separately in the User Study.</li>
          </ul>
        </Alert>
      )}
    </div>
  );
}

export function RunResults({ run }: { run: Run }) {
  const models = BOTS.map((k) => [k, run.metrics?.[k]] as const).filter(([, m]) => m);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <RunMeta items={[run.dataset.title, `n = ${run.selection.selected}`, `seed ${run.selection.seed}`, run.selection.category && `category ${run.selection.category}`,
                         run.dataset.version && `dataset ${run.dataset.version}`, formatDate(run.finished_at)]} />
        <Button variant="outline" size="sm" asChild><a href={api.href(`/evaluations/${run.run_id}/export.csv`)} download><Download /> Export CSV</a></Button>
      </div>
      {run.limitations?.length > 0 && <Alert variant="warning" title="Limitations of this run"><ul className="list-disc space-y-1 pl-4">{run.limitations.map((w) => <li key={w}>{w}</li>)}</ul></Alert>}
      {run.dataset.kind !== "safety" && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>{["Chatbot", "Accuracy", "Macro P", "Macro R", "Macro F1", "Declined", "Median", "p95", "Success", "Failed"].map((h) => <th key={h} className="px-3 py-2.5 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y tabular">
              {models.map(([k, m]) => (
                <tr key={k}><td className="px-3 py-2.5 font-medium">{archLabel(k)}</td>
                  <td className="px-3 py-2.5">{pct(m!.classification?.accuracy)}</td><td className="px-3 py-2.5">{pct(m!.classification?.macro?.precision)}</td>
                  <td className="px-3 py-2.5">{pct(m!.classification?.macro?.recall)}</td><td className="px-3 py-2.5">{pct(m!.classification?.macro?.f1)}</td>
                  <td className="px-3 py-2.5">{m!.no_confident_match ?? "—"}</td><td className="px-3 py-2.5">{ms(m!.latency?.median_ms)}</td>
                  <td className="px-3 py-2.5">{ms(m!.latency?.p95_ms)}</td><td className="px-3 py-2.5">{pct(m!.availability_rate)}</td>
                  <td className="px-3 py-2.5">{m!.failed ? <span className="font-semibold text-critical">{m!.failed}</span> : 0}{m!.error && <span className="block text-xs text-critical">{m!.error}</span>}</td></tr>
              ))}
            </tbody>
          </table>
          <p className="border-t px-3 py-2 text-xs text-muted-foreground">{models[0]?.[1]?.classification_note} Precision, recall and F1 are macro averages over the true classes. "Declined" = no confident topic (counted as wrong).</p>
        </Card>
      )}
      {run.safety && (
        <Card className="p-5">
          <h3 className="font-semibold">Safety (assessed separately from correctness)</h3>
          <p className="mt-1 text-sm">Emergency detection: precision <strong>{pct(run.safety.emergency_detection.precision)}</strong>, recall{" "}
            <strong>{pct(run.safety.emergency_detection.recall)}</strong> on {run.safety.emergency_detection.n} probes (model-independent).</p>
          <div className="mt-3 overflow-x-auto"><table className="w-full text-sm"><thead className="text-left text-xs text-muted-foreground"><tr>
            <th className="py-1.5">Chatbot</th><th>Urgent guidance shown</th><th>Off-topic declined</th><th>False alarms</th></tr></thead>
            <tbody className="tabular">{BOTS.filter((k) => run.safety!.per_model[k]).map((k) => { const p = run.safety!.per_model[k]!; return (
              <tr key={k} className="border-t"><td className="py-1.5 font-medium">{archLabel(k)}</td><td>{pct(p.emergency_recall)}</td><td>{pct(p.oos_decline_rate)}</td><td>{p.false_alarms}</td></tr>); })}
            </tbody></table></div>
        </Card>
      )}
      <p className="flex items-start gap-2 text-xs text-muted-foreground"><AlertTriangle className="mt-px size-3.5 shrink-0" />
        Accuracy measures whether the chatbot recognised the question's topic - not whether its answer is medically correct.</p>
    </div>
  );
}
