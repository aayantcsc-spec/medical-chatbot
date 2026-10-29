import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ChevronDown, GitCompareArrows, Info, Siren, Timer } from "lucide-react";
import { ChartCard, MetricBars } from "@/components/charts";
import { ErrorState, SafetyBadge, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, CardContent, CardHeader, Label, Skeleton, Textarea } from "@/components/ui/primitives";
import { Checkbox } from "@/components/ui/overlays";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { archColor, archLabel, cn, ms } from "@/lib/utils";
import type { ArchitectureInfo, ArchitectureResult, SymptomComparison as Result, SymptomKey } from "@/types/api";

const EXAMPLES = ["I've had a high fever and chills for three days with a bad headache",
                  "My skin is itchy with red scaly patches on my elbows and knees",
                  "I keep coughing and my nose is running, but I have no fever",
                  "It burns when I pee and I need to go all the time"];

function EvidenceList({ r }: { r: ArchitectureResult }) {
  if (!r.evidence?.length) return <p className="text-xs text-muted-foreground">No evidence records for this reply.</p>;
  return (
    <ul className="space-y-1.5 text-xs">
      {r.evidence.slice(0, 5).map((e, i) => (
        <li key={i} className="rounded-md bg-muted/60 px-2.5 py-1.5">
          {e.type === "rule" && <>Rule <strong>{e.rule}</strong> fired on: {e.matched_keywords?.join(", ")}</>}
          {e.type === "entity" && <>Symptom <strong>{e.symptom}</strong>{e.modifier ? ` (${e.modifier})` : ""} · dataset severity {e.severity_weight ?? "—"}</>}
          {e.type === "model_score" && <>Class <strong>{e.label_name}</strong> · score {e.score?.toFixed(3)}</>}
          {e.type === "retrieved_record" && (e.record
            ? <>Record <strong>{e.record}</strong> · similarity {e.similarity?.toFixed(3)}{e.matched_symptoms?.length ? ` · shared: ${e.matched_symptoms.join(", ")}` : ""}</>
            : <>Q&amp;A record #{String(e.record_id)} “{e.question}” · similarity {e.similarity?.toFixed(3)}</>)}
          {e.type === "template" && <>Content-plan message: <strong>{e.message}</strong></>}
        </li>
      ))}
    </ul>
  );
}

function ResultCard({ r, info, fastest }: { r: ArchitectureResult; info?: ArchitectureInfo; fastest: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="h-full">
      <Card className="flex h-full flex-col overflow-hidden">
        <div className="h-1" style={{ background: archColor(r.architecture) }} aria-hidden />
        <CardHeader className="gap-2 pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0"><h3 className="font-semibold">{r.name}</h3><p className="text-xs text-muted-foreground">{info?.method}</p></div>
            <StatusBadge status={r.status} />
          </div>
          <div className="flex flex-wrap gap-1.5">
            <SafetyBadge status={r.safety?.status} />
            <Badge variant="outline"><Timer className="size-3" />{ms(r.response_time_ms)}{fastest && " · fastest"}</Badge>
            {r.prediction?.label_name && <Badge variant="secondary" title={r.prediction.score_kind}>Closest: {r.prediction.label_name} ({r.prediction.score?.toFixed(2)})</Badge>}
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          {r.error ? <Alert variant="critical" title="This architecture could not answer">{r.error}</Alert> : (
            <div className="max-h-80 overflow-y-auto rounded-lg border bg-background/60 p-3 text-sm leading-relaxed scrollbar-thin"><Markdown text={r.response} /></div>
          )}
          {r.withheld_response && r.safety.status === "rejected" && (
            <p className="text-xs text-warning">The model's reply was withheld: {r.safety.reasons.join("; ")}.</p>
          )}
          {r.prediction && <p className="text-[11px] text-muted-foreground">Score type: {r.prediction.score_kind}</p>}
          <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
            className="mt-auto flex items-center gap-1 self-start text-xs font-medium text-primary hover:underline">
            <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />Evidence &amp; extracted information
          </button>
          {open && <EvidenceList r={r} />}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function SymptomComparison() {
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<SymptomKey[] | null>(null);
  const archs = useQuery({ queryKey: ["architectures"], queryFn: () => api.get<{ architectures: ArchitectureInfo[]; note: string }>("/comparison/architectures"), staleTime: Infinity });
  const keys = selected ?? archs.data?.architectures.map((a) => a.key) ?? [];
  const run = useMutation({ mutationFn: (v: { input: string; architectures: SymptomKey[] }) => api.post<Result>("/comparison/run", v) });
  const toggle = (k: SymptomKey) => setSelected((s) => { const cur = s ?? keys; return cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]; });
  const submit = (t = text) => { if (t.trim() && keys.length) { setText(t); run.mutate({ input: t.trim(), architectures: keys }); } };
  const data = run.data;
  const results = data ? (Object.values(data.results) as ArchitectureResult[]) : [];
  const infoOf = (k: string) => archs.data?.architectures.find((a) => a.key === k);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <div className="space-y-1.5">
            <Label htmlFor="sym-input">Symptom description</Label>
            <Textarea id="sym-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} rows={3}
              placeholder="Describe symptoms in your own words, e.g. 'I've had a sore throat and fever since yesterday'" />
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLES.map((ex) => <button type="button" key={ex} onClick={() => submit(ex)} disabled={run.isPending}
                className="rounded-full border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground">{ex}</button>)}
            </div>
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-medium">Architectures</legend>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(archs.data?.architectures ?? []).map((a) => (
                <label key={a.key} className={cn("flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 text-sm", keys.includes(a.key) && "border-primary/40 bg-accent/40")}>
                  <Checkbox checked={keys.includes(a.key)} onCheckedChange={() => toggle(a.key)} disabled={!a.available} className="mt-0.5" />
                  <span><span className="font-medium">{a.name}</span>{!a.available && <span className="block text-xs text-critical">{a.unavailable_reason}</span>}</span>
                </label>
              ))}
              {archs.isLoading && [0, 1, 2].map((i) => <Skeleton key={i} className="h-11" />)}
            </div>
          </fieldset>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" loading={run.isPending} disabled={!text.trim() || !keys.length}><GitCompareArrows /> Compare Responses</Button>
            <span className="text-xs text-muted-foreground">{keys.length} selected · the same text and safety check for every architecture</span>
          </div>
        </form>
      </Card>

      {run.error && <ErrorState error={run.error} onRetry={() => submit()} />}
      {run.isPending && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {keys.map((k) => (
            <Card key={k} className="space-y-3 p-5"><p className="text-sm font-semibold">{archLabel(k)}</p>
              <Skeleton className="h-4 w-1/2" /><Skeleton className="h-24 w-full" /><Skeleton className="h-3 w-2/3" /></Card>
          ))}
        </div>
      )}
      {data && !run.isPending && (
        <>
          {data.safety.emergency && (
            <Alert variant="critical" title="Possible emergency detected - urgent guidance replaced every ordinary reply">
              <span className="inline-flex items-center gap-1"><Siren className="size-3.5" /> Detected: {data.safety.categories.join(", ")}. This happens before any architecture's answer is shown.</span>
            </Alert>
          )}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {results.map((r) => <ResultCard key={r.architecture} r={r} info={infoOf(r.architecture)} fastest={data.summary.fastest === r.architecture && results.length > 1} />)}
          </div>
          <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
            <Card className="p-5">
              <h3 className="font-semibold">Comparison summary</h3>
              <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-muted-foreground">Answered</dt><dd className="font-semibold">{data.summary.answered.length} of {results.length}</dd></div>
                <div><dt className="text-muted-foreground">No confident match</dt><dd className="font-semibold">{data.summary.no_match.length}</dd></div>
                <div><dt className="text-muted-foreground">Fastest</dt><dd className="font-semibold">{archLabel(data.summary.fastest)}</dd></div>
                <div><dt className="text-muted-foreground">Failed</dt><dd className="font-semibold">{data.summary.failed.length}</dd></div>
              </dl>
              {data.summary.label_disagreement && <p className="mt-3 text-sm text-warning">The label-predicting architectures disagree about the closest condition - a reminder that none of them is a diagnosis.</p>}
              <p className="mt-3 flex gap-2 text-xs text-muted-foreground"><Info className="mt-px size-3.5 shrink-0" />{data.summary.note}</p>
            </Card>
            <ChartCard title="Response time for this query" description="Single request each - see Model Evaluation for averages over many inputs."
              table={{ columns: ["Architecture", "Response time", "Status"], rows: results.map((r) => [r.name, ms(r.response_time_ms), r.status]) }}>
              <MetricBars height={200} data={results.map((r) => ({ key: r.architecture, label: r.name, value: r.response_time_ms, note: "Response time" }))}
                format={(v) => `${v.toFixed(1)} ms`} />
            </ChartCard>
          </div>
        </>
      )}
      {archs.error && <ErrorState error={archs.error} onRetry={() => archs.refetch()} />}
    </div>
  );
}
