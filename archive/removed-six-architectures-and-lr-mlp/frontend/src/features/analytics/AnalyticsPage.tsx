import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { ChartCard, CountBars, HistoryLines, MetricBars } from "@/components/charts";
import { EmptyState, ErrorState, LoadingCards, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Label, Select } from "@/components/ui/primitives";
import { Checkbox } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { archColor, archLabel, formatDate, ms, num, pct } from "@/lib/utils";
import type { HistoryPoint, SymptomRunSummary } from "@/types/api";
import { historyRows } from "@/pages/DashboardPage";

type Arch = {
  evaluation_required: boolean; run: SymptomRunSummary | null;
  response_time_distribution: Record<string, { bucket: string; count: number }[]>;
  sample_distribution: { label: string; count: number }[];
  runs: { run_id: string; created_at: string; sample_size: number; status: string; in_sample: boolean }[];
};
const HISTORY_METRICS = { coverage: "Coverage", accuracy: "Accuracy", f1_score: "Macro F1", median_response_time: "Median response time" } as const;

export default function AnalyticsPage() {
  useDocumentTitle("Performance Analytics");
  const [runId, setRunId] = useState<string>("");
  const [hidden, setHidden] = useState<string[]>([]);
  const [metric, setMetric] = useState<keyof typeof HISTORY_METRICS>("coverage");
  const [distArch, setDistArch] = useState<string>("");
  const q = useQuery({ queryKey: ["analytics", "architectures", runId], queryFn: () => api.get<Arch>("/analytics/architectures", runId ? { run_id: runId } : undefined) });
  const hist = useQuery({ queryKey: ["analytics", "history", "symptom"], queryFn: () => api.get<HistoryPoint[]>("/analytics/history", { suite: "symptom" }) });

  const run = q.data?.run;
  const all = useMemo(() => (run ? Object.entries(run.architectures) : []), [run]);
  const archs = all.filter(([k]) => !hidden.includes(k));
  const labelled = archs.filter(([, a]) => a.predicts_label);
  const series = all.map(([k, a]) => ({ key: k, label: a.name })).filter((s) => !hidden.includes(s.key));
  const rows = historyRows(hist.data ?? [], metric);
  const isTime = metric === "median_response_time";
  const dk = distArch || archs[0]?.[0] || "";
  const dist = q.data?.response_time_distribution[dk] ?? [];

  if (q.isLoading) return <><PageHeader title="Performance Analytics" /><LoadingCards count={6} /></>;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (q.data?.evaluation_required || !run) {
    return (
      <>
        <PageHeader title="Performance Analytics" description="Charts built only from saved experiment results." />
        <EmptyState title="Evaluation required" description="Analytics appear after your first completed six-architecture evaluation. Nothing is estimated or pre-filled."
          action={<Button asChild><Link to="/model-evaluation"><FlaskConical /> Run Evaluation</Link></Button>} />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Performance Analytics" description="Measured results for the six symptom architectures. Choose an experiment and filter architectures; every chart has a table view." />
      <div className="mb-5 flex flex-col gap-4 rounded-xl border bg-card p-4 lg:flex-row lg:items-end">
        <div className="min-w-[16rem] space-y-1.5"><Label htmlFor="run">Experiment</Label>
          <Select id="run" value={runId || run.run_id} onChange={(e) => setRunId(e.target.value)}>
            {q.data!.runs.filter((r) => r.status === "completed").map((r) => (
              <option key={r.run_id} value={r.run_id}>{formatDate(r.created_at)} · n={r.sample_size}{r.in_sample ? " · in-sample" : ""}</option>))}
          </Select></div>
        <fieldset className="flex-1"><legend className="mb-1.5 text-sm font-medium">Architectures</legend>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {all.map(([k, a]) => (
              <label key={k} className="flex cursor-pointer items-center gap-2 text-sm">
                <Checkbox checked={!hidden.includes(k)} onCheckedChange={() => setHidden((h) => h.includes(k) ? h.filter((x) => x !== k) : [...h, k])} />
                <span className="size-2.5 rounded-sm" style={{ background: archColor(k) }} aria-hidden />{a.name}
              </label>
            ))}
          </div></fieldset>
      </div>
      {run.in_sample && <Alert variant="critical" className="mb-4" title="In-sample experiment">The classifier was trained on part of this data - its scores are not generalisation estimates.</Alert>}
      {run.sample_size < 50 && <Alert variant="warning" className="mb-4">Only {run.sample_size} inputs in this run - treat differences as indicative, not significant.</Alert>}

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Architecture performance" description="Share of inputs answered (coverage) - the one task measure every architecture shares."
          table={{ columns: ["Architecture", "Coverage", "Safety pass"], rows: archs.map(([, a]) => [a.name, pct(a.coverage), pct(a.safety_pass_rate)]) }}>
          <MetricBars data={archs.map(([k, a]) => ({ key: k, label: a.name, value: a.coverage, note: "Coverage" }))} format={(v) => pct(v, 0)} domain={[0, 1]} />
        </ChartCard>
        <ChartCard title="Accuracy and macro F1" description="Disease-label metrics; only Classification- and Retrieval-Based predict labels."
          table={{ columns: ["Architecture", "Accuracy", "Precision", "Recall", "F1", "Top-3"], rows: labelled.map(([, a]) => [a.name, pct(a.accuracy), pct(a.precision_macro), pct(a.recall_macro), pct(a.f1_macro), pct(a.top3_hit_rate)]) }}
          footer="Macro averages over true classes. Abstentions count as wrong.">
          {labelled.length ? (
            <div className="grid grid-cols-2 gap-2">
              <div><p className="mb-1 text-xs font-medium text-muted-foreground">Accuracy</p>
                <MetricBars height={220} data={labelled.map(([k, a]) => ({ key: k, label: a.name, value: a.accuracy, note: "Accuracy" }))} format={(v) => pct(v, 0)} domain={[0, 1]} /></div>
              <div><p className="mb-1 text-xs font-medium text-muted-foreground">Macro F1</p>
                <MetricBars height={220} data={labelled.map(([k, a]) => ({ key: k, label: a.name, value: a.f1_macro, note: "Macro F1" }))} format={(v) => pct(v, 0)} domain={[0, 1]} /></div>
            </div>) : <p className="py-12 text-center text-sm text-muted-foreground">No label-predicting architecture selected.</p>}
        </ChartCard>
        <ChartCard title="Response time" description="Median milliseconds per request (sequential requests, single process, warm models)."
          table={{ columns: ["Architecture", "Median", "Mean"], rows: archs.map(([, a]) => [a.name, ms(a.median_ms), ms(a.mean_ms)]) }}>
          <MetricBars data={archs.map(([k, a]) => ({ key: k, label: a.name, value: a.median_ms, note: "Median" }))} format={(v) => `${v.toFixed(1)} ms`} />
        </ChartCard>
        <ChartCard title="Resource usage - CPU" description="Process CPU time ÷ wall time, percent of one core, during each architecture's requests."
          table={{ columns: ["Architecture", "CPU", "Δ memory (RSS)"], rows: archs.map(([, a]) => [a.name, a.cpu_percent === null ? "—" : `${a.cpu_percent}%`, `${num(a.memory_delta_mb, 2)} MB`]) }}
          footer="Measured with psutil. Depends on hardware, OS and concurrent load; memory change is shown in the table (it is usually near zero once models are loaded).">
          <MetricBars data={archs.map(([k, a]) => ({ key: k, label: a.name, value: a.cpu_percent, note: "CPU" }))} format={(v) => `${v.toFixed(0)}%`} />
        </ChartCard>
        <ChartCard title="Response-time distribution" description="How individual request times spread for one architecture."
          table={{ columns: ["Bucket", "Requests"], rows: dist.map((d) => [d.bucket, d.count]) }}>
          <div className="mb-2 max-w-xs"><Label htmlFor="dist" className="sr-only">Architecture</Label>
            <Select id="dist" value={dk} onChange={(e) => setDistArch(e.target.value)} className="h-9">
              {archs.map(([k, a]) => <option key={k} value={k}>{a.name}</option>)}</Select></div>
          <CountBars data={dist.map((d) => ({ name: d.bucket.replace(" ms", ""), count: d.count }))} xLabel="milliseconds" height={200} />
        </ChartCard>
        <ChartCard title="Evaluation sample distribution" description={`${q.data!.sample_distribution.length} disease labels in this run's inputs (stratified sample).`}
          table={{ columns: ["Label", "Inputs"], rows: q.data!.sample_distribution.map((d) => [archLabel(d.label), d.count]) }}>
          <CountBars data={q.data!.sample_distribution.map((d) => ({ name: d.label.replace(/_/g, " "), count: d.count }))} height={240} />
        </ChartCard>
        <ChartCard className="lg:col-span-2" title="Experiment history" legend={series}
          description="One point per completed run. Runs with different sample sizes or in-sample data are not strictly comparable."
          table={{ columns: ["Run", ...series.map((s) => s.label)], rows: rows.map((r) => [String(r.label), ...series.map((s) => isTime ? ms(r[s.key] as number | null) : pct(r[s.key] as number | null))]) }}
          footer={rows.length < 2 ? "Run another evaluation to see change over time." : undefined}>
          <div className="mb-2 max-w-xs"><Label htmlFor="hm" className="sr-only">Metric</Label>
            <Select id="hm" value={metric} onChange={(e) => setMetric(e.target.value as keyof typeof HISTORY_METRICS)} className="h-9">
              {Object.entries(HISTORY_METRICS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></div>
          <HistoryLines rows={rows} series={series} format={(v) => (isTime ? `${v.toFixed(1)} ms` : pct(v, 0))} domain={isTime ? undefined : [0, 1]} />
        </ChartCard>
      </div>
    </>
  );
}
