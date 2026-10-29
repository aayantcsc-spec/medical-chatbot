import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, FlaskConical, ListChecks, Play } from "lucide-react";
import { EmptyState, ErrorState, LoadingCards, PageHeader, Spinner, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardContent, CardHeader, CardTitle, Input, Label, Progress, Select, Skeleton } from "@/components/ui/primitives";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { cn, formatDate, relativeTime } from "@/lib/utils";
import type { Overview, RunSummary } from "@/types/api";
import { OverviewResults, RunResults, type Run } from "./results";

type Datasets = { datasets: { name: string; title: string; kind: string; rows_usable: number; valid: boolean; issues: string[];
                              categories: { value: string; count: number }[]; warnings: string[] }[]; quick_size: number };
type Status = { run_id: string; status: string; error: string | null; percent: number; progress: { completed: number; total: number } };

function RunForm({ onStarted }: { onStarted: (id: string) => void }) {
  const ds = useQuery({ queryKey: ["eval-datasets"], queryFn: () => api.get<Datasets>("/evaluations/datasets") });
  const [dataset, setDataset] = useState("held_out_test");
  const [mode, setMode] = useState("full");
  const [limit, setLimit] = useState("50");
  const [category, setCategory] = useState("");
  const qc = useQueryClient();
  const start = useMutation({
    mutationFn: () => api.post<{ run_id: string }>("/evaluations", { dataset, mode, limit: mode === "custom" ? Number(limit) : null, category: category || null }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["evaluations"] }); onStarted(r.run_id); },
  });
  if (ds.isLoading) return <Skeleton className="h-56" />;
  if (ds.error) return <ErrorState error={ds.error} onRetry={() => ds.refetch()} />;
  const cur = ds.data!.datasets.find((d) => d.name === dataset);
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); start.mutate(); }}>
      <p className="text-sm text-muted-foreground">All three chatbots answer exactly the same questions.</p>
      <div className="space-y-1.5"><Label htmlFor="ds">Dataset</Label>
        <Select id="ds" value={dataset} onChange={(e) => { setDataset(e.target.value); setCategory(""); }}>
          {ds.data!.datasets.map((d) => <option key={d.name} value={d.name} disabled={!d.valid}>{d.title} · {d.rows_usable} usable</option>)}
        </Select>
        {cur?.warnings?.[0] && <p className="text-xs text-muted-foreground">{cur.warnings[0]}</p>}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5"><Label htmlFor="mode">Questions</Label>
          <Select id="mode" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="full">All eligible</option><option value="quick">Quick test ({ds.data!.quick_size})</option><option value="custom">Custom count</option>
          </Select></div>
        {mode === "custom" ? <div className="space-y-1.5"><Label htmlFor="lim">Count</Label><Input id="lim" type="number" min={1} value={limit} onChange={(e) => setLimit(e.target.value)} /></div>
          : <div className="space-y-1.5"><Label htmlFor="cat">Category</Label>
            <Select id="cat" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All</option>
              {cur?.categories.map((c) => <option key={c.value} value={c.value}>{c.value} ({c.count})</option>)}</Select></div>}
      </div>
      {mode !== "full" && <Alert variant="warning">A sample gives less reliable numbers. Use “All eligible” for results you report.</Alert>}
      {start.error && <Alert variant="critical">{(start.error as Error).message}</Alert>}
      <Button type="submit" loading={start.isPending}><Play /> Run evaluation</Button>
    </form>
  );
}

function RunView({ id }: { id: string }) {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["eval-status", id], queryFn: () => api.get<Status>(`/evaluations/${id}/status`),
    refetchInterval: (q) => (q.state.data && ["completed", "failed"].includes(q.state.data.status) ? false : 1000),
  });
  const done = status.data?.status === "completed";
  useEffect(() => { if (done) { qc.invalidateQueries({ queryKey: ["evaluations"] }); qc.invalidateQueries({ queryKey: ["overview"] }); } }, [done, qc]);
  const detail = useQuery({ queryKey: ["evaluation", id], enabled: done, queryFn: () => api.get<Run>(`/evaluations/${id}`) });
  if (status.error) return <ErrorState error={status.error} onRetry={() => status.refetch()} />;
  if (!status.data) return <Spinner label="Loading run" />;
  if (status.data.status === "failed") return <Alert variant="critical" title="This evaluation failed">{status.data.error}</Alert>;
  if (!done) {
    return (
      <Card className="p-6" aria-live="polite">
        <div className="mb-3 flex items-center justify-between text-sm"><span className="font-medium">Running…</span>
          <span className="tabular text-muted-foreground">{status.data.progress.completed} / {status.data.progress.total} questions · {status.data.percent}%</span></div>
        <Progress value={status.data.percent} label="Evaluation progress" />
        <p className="mt-3 text-xs text-muted-foreground">The run continues on the server if you leave this page.</p>
      </Card>
    );
  }
  if (detail.isLoading) return <Spinner label="Loading results" />;
  if (detail.error) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />;
  return <RunResults run={detail.data!} />;
}

export default function ModelEvaluationPage() {
  useDocumentTitle("Model Evaluation");
  const [tab, setTab] = useState("overview");
  const [active, setActive] = useState<string | null>(null);
  const overview = useQuery({ queryKey: ["overview"], queryFn: () => api.get<Overview>("/analytics/overview") });
  const runs = useQuery({ queryKey: ["evaluations"], queryFn: () => api.page<RunSummary[]>("/evaluations", { per_page: 50 }) });
  const list = runs.data?.data ?? [];
  const shown = active ?? list.find((r) => r.status === "completed")?.run_id ?? null;

  return (
    <>
      <PageHeader title="Model Evaluation" description="Measured performance of the Rule-Based, TF-IDF + SVM and DistilBERT chatbots on the same test questions: correctness, safety, response quality, response time and reliability." />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList aria-label="Model evaluation">
          <TabsTrigger value="overview"><BarChart3 /> Results overview</TabsTrigger>
          <TabsTrigger value="runs"><ListChecks /> Runs</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          {overview.isLoading && <LoadingCards count={6} />}
          {overview.error && <ErrorState error={overview.error} onRetry={() => overview.refetch()} />}
          {overview.data && (overview.data.evaluation_required
            ? <EmptyState icon={FlaskConical} title="Evaluation required" description="No completed held-out evaluation exists yet. Run one in the Runs tab - nothing is shown until real results exist."
                action={<Button onClick={() => setTab("runs")}><Play /> Run an evaluation</Button>} />
            : <>
                <div className="mb-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                  {Object.entries(overview.data.runs).map(([k, r]) => (
                    <span key={k}>{r ? <>{r.dataset}: <strong className="text-foreground">n = {r.n}</strong> · {formatDate(r.finished_at)}</>
                                     : <>{k.replace(/_/g, " ")}: <em>not run yet</em></>}</span>))}
                </div>
                <OverviewResults o={overview.data} />
              </>)}
        </TabsContent>
        <TabsContent value="runs">
          <div className="grid gap-6 xl:grid-cols-[340px_1fr]">
            <div className="space-y-6">
              <Card><CardHeader><CardTitle>New evaluation</CardTitle></CardHeader><CardContent><RunForm onStarted={setActive} /></CardContent></Card>
              <Card><CardHeader><CardTitle>Previous runs</CardTitle></CardHeader>
                <CardContent className="px-2">
                  {runs.isLoading && <Skeleton className="mx-3 h-32" />}
                  {runs.error && <ErrorState error={runs.error} onRetry={() => runs.refetch()} />}
                  {runs.data && list.length === 0 && <p className="px-3 py-4 text-sm text-muted-foreground">No runs yet.</p>}
                  <ul className="max-h-[28rem] space-y-0.5 overflow-y-auto scrollbar-thin">
                    {list.map((r) => (
                      <li key={r.run_id}><button onClick={() => setActive(r.run_id)} aria-current={shown === r.run_id}
                        className={cn("flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted", shown === r.run_id && "bg-accent")}>
                        <span className="min-w-0"><span className="block truncate font-medium">{r.dataset_title}</span>
                          <span className="block text-xs text-muted-foreground">{r.progress.total} questions · {relativeTime(r.created_at)}</span></span>
                        <StatusBadge status={r.status} /></button></li>
                    ))}
                  </ul>
                </CardContent></Card>
            </div>
            <div className="min-w-0">{shown ? <RunView key={shown} id={shown} /> : !runs.isLoading &&
              <EmptyState title="Evaluation required" description="Run your first evaluation to see results here." />}</div>
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
}
