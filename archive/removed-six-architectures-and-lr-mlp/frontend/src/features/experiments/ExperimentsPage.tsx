import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, ChevronLeft, ChevronRight, Database, Download, XCircle } from "lucide-react";
import { EmptyState, ErrorState, PageHeader, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, Select, Skeleton } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { archLabel, formatDate, ms, pct } from "@/lib/utils";
import type { ExperimentRow } from "@/types/api";

type Inv = { file: string; documented_rows: number | null; actual_rows: number | null; bytes: number | null; purpose: string; present: boolean; discrepancy: string | null }[];
type Knowledge = { symptom: { splits: Record<string, number | null>; knowledge: { diseases_described: number; symptom_vocabulary: number; lexicon_phrases: number;
  retrieval_profiles: number; retrieval_profiles_meta: { source_rows: number; source_diseases: number; built_at: string } | null; missing: string[] } } };
const size = (b: number | null) => (b === null ? "—" : b > 2 ** 20 ? `${(b / 2 ** 20).toFixed(1)} MB` : `${(b / 1024).toFixed(1)} KB`);

export default function ExperimentsPage() {
  useDocumentTitle("Dataset & Experiments");
  const [suite, setSuite] = useState("");
  const [page, setPage] = useState(1);
  const inv = useQuery({ queryKey: ["datasets"], queryFn: () => api.get<Inv>("/datasets") });
  const kb = useQuery({ queryKey: ["eval-datasets"], queryFn: () => api.get<Knowledge>("/evaluations/datasets") });
  const exps = useQuery({ queryKey: ["experiments", suite, page], placeholderData: keepPreviousData,
    queryFn: () => api.page<ExperimentRow[]>("/experiments", { suite: suite || undefined, page, per_page: 10 }) });
  const k = kb.data?.symptom.knowledge;

  return (
    <>
      <PageHeader title="Dataset & Experiments" description="What data the platform actually has, how it is split, and every experiment that has been run."
        actions={<Button variant="outline" asChild><a href={api.href("/evaluations/history.csv")} download><Download /> comparison_results.csv</a></Button>} />

      <Card className="mb-6">
        <CardHeader><CardTitle className="flex items-center gap-2"><Database className="size-4" /> Dataset inventory</CardTitle>
          <CardDescription>Documented counts are checked against the files on disk at request time. Discrepancies are shown, not hidden.</CardDescription></CardHeader>
        <CardContent className="px-0 pb-0">
          {inv.isLoading && <Skeleton className="mx-5 mb-5 h-48" />}
          {inv.error && <div className="p-5"><ErrorState error={inv.error} onRetry={() => inv.refetch()} /></div>}
          {inv.data && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="border-y bg-muted/50 text-left text-xs text-muted-foreground"><tr>
                  <th className="px-5 py-2.5">File</th><th className="px-3 py-2.5">Purpose</th><th className="px-3 py-2.5 text-right">Documented</th>
                  <th className="px-3 py-2.5 text-right">Actual rows</th><th className="px-3 py-2.5 text-right">Size</th><th className="px-5 py-2.5">Status</th></tr></thead>
                <tbody className="divide-y tabular">
                  {inv.data.map((d) => (
                    <tr key={d.file}><td className="px-5 py-2.5 font-medium">{d.file}</td><td className="px-3 py-2.5 text-muted-foreground">{d.purpose}</td>
                      <td className="px-3 py-2.5 text-right">{d.documented_rows?.toLocaleString() ?? "—"}</td>
                      <td className="px-3 py-2.5 text-right">{d.actual_rows?.toLocaleString() ?? "—"}</td><td className="px-3 py-2.5 text-right">{size(d.bytes)}</td>
                      <td className="px-5 py-2.5">{!d.present ? <Badge variant="critical"><XCircle className="size-3" />Missing</Badge>
                        : d.discrepancy ? <Badge variant="warning" title={d.discrepancy}>{d.discrepancy}</Badge>
                        : <Badge variant="success"><CheckCircle2 className="size-3" />Matches</Badge>}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {k && (
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card className="p-5"><p className="text-sm text-muted-foreground">Symptom2Disease split (deduplicated)</p>
            <p className="mt-1 text-lg font-semibold tabular">{kb.data!.symptom.splits.train} / {kb.data!.symptom.splits.val} / {kb.data!.symptom.splits.test}</p>
            <p className="text-xs text-muted-foreground">train / validation / held-out test · stratified · seed 42</p></Card>
          <Card className="p-5"><p className="text-sm text-muted-foreground">Retrieval index</p>
            <p className="mt-1 text-lg font-semibold tabular">{k.retrieval_profiles} disease profiles</p>
            <p className="text-xs text-muted-foreground">{k.retrieval_profiles_meta ? `from ${k.retrieval_profiles_meta.source_rows.toLocaleString()} records · built ${formatDate(k.retrieval_profiles_meta.built_at)}` : "not built"}</p></Card>
          <Card className="p-5"><p className="text-sm text-muted-foreground">Symptom knowledge</p>
            <p className="mt-1 text-lg font-semibold tabular">{k.symptom_vocabulary} symptoms · {k.diseases_described} described diseases</p>
            <p className="text-xs text-muted-foreground">{k.lexicon_phrases} lexicon phrases incl. everyday synonyms</p></Card>
        </div>
      )}
      {k && k.missing.length > 0 && <Alert variant="critical" className="mb-6" title="Missing data">{k.missing.join("; ")}</Alert>}

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <div><CardTitle>Experiments</CardTitle><CardDescription>Stored in SQLite and appended to results/comparison_results.csv - never overwritten.</CardDescription></div>
          <Select value={suite} onChange={(e) => { setSuite(e.target.value); setPage(1); }} className="h-9 w-48" aria-label="Filter by suite">
            <option value="">All suites</option><option value="symptom">Six architectures</option><option value="health_qa">Health Q&amp;A</option></Select>
        </CardHeader>
        <CardContent>
          {exps.isLoading && <Skeleton className="h-40" />}
          {exps.error && <ErrorState error={exps.error} onRetry={() => exps.refetch()} />}
          {exps.data && exps.data.data.length === 0 && <EmptyState title="No experiments recorded" description="Run one from Model Evaluation; it will be listed here with its configuration." />}
          <div className="space-y-3">
            {exps.data?.data.map((e) => (
              <details key={e.id} className="group rounded-lg border">
                <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 p-3.5 hover:bg-muted/40">
                  <span className="min-w-0"><span className="block font-medium">{e.name}</span>
                    <span className="block text-xs text-muted-foreground">{formatDate(e.created_at)} · {e.split} · n={e.sample_size ?? "—"} · seed {e.random_seed ?? "—"} · dataset {e.dataset_version ?? "—"}</span></span>
                  <span className="flex gap-1.5">{e.in_sample ? <Badge variant="warning">in-sample</Badge> : <Badge variant="outline">held-out</Badge>}<StatusBadge status={e.status} /></span>
                </summary>
                <div className="border-t p-3.5">
                  <p className="mb-2 text-xs text-muted-foreground">Method: {e.evaluation_method}</p>
                  <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-sm"><thead className="text-left text-xs text-muted-foreground"><tr>
                    <th className="py-1.5">Architecture</th><th>Accuracy</th><th>Macro F1</th><th>Coverage</th><th>Median time</th></tr></thead>
                    <tbody className="tabular">{e.results.map((r) => (
                      <tr key={r.architecture} className="border-t"><td className="py-1.5 font-medium">{archLabel(r.architecture)}</td><td>{pct(r.accuracy)}</td>
                        <td>{pct(r.f1_score)}</td><td>{pct(r.coverage)}</td><td>{ms(r.median_response_time)}</td></tr>))}</tbody></table></div>
                  {e.warnings.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted-foreground">{e.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
                </div>
              </details>
            ))}
          </div>
          {exps.data && exps.data.meta.pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft /> Previous</Button>
              <span className="text-muted-foreground">Page {page} of {exps.data.meta.pages}</span>
              <Button variant="outline" size="sm" disabled={page >= exps.data.meta.pages} onClick={() => setPage((p) => p + 1)}>Next <ChevronRight /></Button>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
