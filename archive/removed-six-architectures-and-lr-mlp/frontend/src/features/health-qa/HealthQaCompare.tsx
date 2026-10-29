import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Award, Ban, Scale, Siren, Timer } from "lucide-react";
import { ErrorState, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, CardContent, CardHeader, Label, Progress, Skeleton, Textarea } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { archColor, archLabel, cn, ms } from "@/lib/utils";
import type { HealthQaKey, HqaComparison, HqaResult, HqaScore } from "@/types/api";

export type Topics = {
  topic_count: number; categories: { id: string; name: string }[]; examples: { emoji: string; category: string; question: string }[];
  model_sets: Record<"spec" | "current", HealthQaKey[]>;
  models: Record<HealthQaKey, { key: string; name: string; available: boolean; architecture?: string; version?: string; error?: string }>;
  historical_reference: { values: Record<string, number>; provenance: string; status: string };
};
export const SET_LABELS = {
  spec: { title: "Specification set", desc: "Rule-Based · TF-IDF + Logistic Regression · TF-IDF + MLPClassifier" },
  current: { title: "Upgraded set", desc: "Rule-Based · TF-IDF + SVM · fine-tuned DistilBERT" },
};

function ScoreRow({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      {value === null || value === undefined ? <span className="text-muted-foreground">not scored</span> : <Progress value={value} label={label} className="h-1.5" />}
      <span className="text-right font-medium tabular">{value ?? "—"}</span>
    </div>
  );
}

function BotCard({ r, s, winner, tied }: { r: HqaResult; s?: HqaScore; winner: boolean; tied: boolean }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="h-full">
      <Card className={cn("flex h-full flex-col overflow-hidden", winner && "ring-2 ring-success/50")}>
        <div className="h-1" style={{ background: archColor(r.key) }} aria-hidden />
        <CardHeader className="gap-2 pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0"><h3 className="font-semibold">{r.name}</h3><p className="text-xs text-muted-foreground">{r.architecture}</p></div>
            {winner ? <Badge variant="success"><Award className="size-3" />Selected</Badge> : tied ? <Badge variant="default"><Scale className="size-3" />Tied</Badge> : <StatusBadge status={r.status} />}
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline"><Timer className="size-3" />{ms(r.inference_ms)}</Badge>
            {r.intent_title && <Badge variant="secondary">Topic: {r.intent_title}</Badge>}
            {r.safety_override && <Badge variant="critical"><Siren className="size-3" />Emergency guidance</Badge>}
            {s && !s.eligible && s.excluded_reason && <Badge variant="warning"><Ban className="size-3" />Not compared</Badge>}
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          {r.error ? <Alert variant="critical" title="This bot could not answer">{r.error}</Alert>
            : <div className="max-h-72 overflow-y-auto rounded-lg border bg-background/60 p-3 text-sm leading-relaxed scrollbar-thin"><Markdown text={r.response} /></div>}
          {s && (
            <div className="mt-auto space-y-1.5 rounded-lg bg-muted/50 p-3">
              <ScoreRow label="Relevance" value={s.quality_parts?.relevance} />
              <ScoreRow label="Completeness" value={s.quality_parts?.completeness} />
              <ScoreRow label="Clarity" value={s.quality_parts?.clarity} />
              <ScoreRow label="Safety" value={s.safety} />
              {s.safety_level && <p className="pt-1 text-xs"><span className="text-muted-foreground">Safety check:</span>{" "}
                <span className={cn("font-medium", s.safety_level === "Unsafe" ? "text-critical" : s.safety_level === "Safe" ? "text-success" : "text-warning")}>{s.safety_level}</span>
                {" - "}{s.safety_notes.join("; ")}</p>}
              {!s.eligible && s.excluded_reason && <p className="text-xs text-warning">Excluded: {s.excluded_reason}</p>}
              {r.confidence !== null && <p className="text-[11px] text-muted-foreground">Model score {r.confidence.toFixed(2)} - {r.confidence_kind}. Not used for selection.</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function HealthQaCompare({ topics }: { topics?: Topics }) {
  const [question, setQuestion] = useState("");
  const [set, setSet] = useState<"spec" | "current">("spec");
  const run = useMutation({ mutationFn: (v: { question: string; model_set: string }) => api.post<HqaComparison>("/health-qa/compare", v) });
  const submit = (q = question) => { if (q.trim()) { setQuestion(q); run.mutate({ question: q.trim(), model_set: set }); } };
  const d = run.data;
  const sel = d?.overall_selection;
  const keys = topics?.model_sets[set] ?? (set === "spec" ? ["rule", "lr", "mlp"] : ["rule", "ml", "dl"]);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <fieldset>
            <legend className="mb-2 text-sm font-medium">Bot set</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {(["spec", "current"] as const).map((k) => (
                <label key={k} className={cn("flex cursor-pointer items-start gap-3 rounded-lg border p-3", set === k && "border-primary/50 bg-accent/40")}>
                  <input type="radio" name="set" value={k} checked={set === k} onChange={() => setSet(k)} className="mt-1 accent-[hsl(var(--primary))]" />
                  <span><span className="block text-sm font-medium">{SET_LABELS[k].title}</span><span className="block text-xs text-muted-foreground">{SET_LABELS[k].desc}</span>
                    {topics && topics.model_sets[k].some((m) => !topics.models[m]?.available) &&
                      <span className="mt-1 block text-xs text-critical">Some models unavailable: {topics.model_sets[k].filter((m) => !topics.models[m]?.available).map(archLabel).join(", ")}</span>}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="space-y-1.5">
            <Label htmlFor="hqa-q">Health question</Label>
            <Textarea id="hqa-q" value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={1000}
              placeholder="e.g. What is the difference between a cold and the flu?  (English, Hindi or Hinglish)" />
            {topics && <div className="flex flex-wrap gap-1.5">
              {topics.examples.slice(0, 6).map((ex) => <button type="button" key={ex.question} onClick={() => submit(ex.question)} disabled={run.isPending}
                className="rounded-full border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground">{ex.emoji} {ex.question}</button>)}
            </div>}
          </div>
          <Button type="submit" loading={run.isPending} disabled={!question.trim()}>Compare Responses</Button>
        </form>
      </Card>

      {run.error && <ErrorState error={run.error} onRetry={() => submit()} />}
      {run.isPending && (
        <div className="grid gap-4 md:grid-cols-3" aria-busy="true">
          {keys.map((k) => <Card key={k} className="space-y-3 p-5"><p className="text-sm font-semibold">{archLabel(k)}</p><Skeleton className="h-32" /><Skeleton className="h-16" /></Card>)}
        </div>
      )}
      {d && sel && !run.isPending && (
        <>
          {d.safety.emergency && <Alert variant="critical" title="Possible emergency detected">Urgent-care guidance is shown first by every bot. Detected: {d.safety.categories.join(", ")}.</Alert>}
          <Card className={cn("border-l-4 p-5", sel.status === "winner" ? "border-l-success" : sel.status === "tie" ? "border-l-primary" : "border-l-warning")}>
            <div className="flex flex-wrap items-center gap-2">
              {sel.status === "winner" ? <Award className="size-5 text-success" /> : <Scale className="size-5 text-primary" />}
              <h3 className="font-semibold">{sel.headline}{sel.winner_name ? `: ${sel.winner_name}` : ""}</h3>
            </div>
            <p className="mt-2 text-sm">{sel.reason}</p>
            <details className="mt-3 text-xs text-muted-foreground">
              <summary className="cursor-pointer font-medium text-foreground">How the selection works</summary>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                <li>Weights: {Object.entries(sel.method.weights).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(", ")} (re-balanced over what can be scored).</li>
                <li>A reply rated <strong>Unsafe</strong> is excluded - it can never be selected, however fast or fluent.</li>
                <li>{sel.method.ground_truth.available ? `Correctness is scored against the labelled dataset (${sel.method.ground_truth.dataset}).` : sel.method.ground_truth.note}</li>
                <li>{sel.method.scope}</li><li>{sel.method.limits}</li><li>{sel.method.language_scope}</li>
              </ul>
            </details>
          </Card>
          <div className="grid gap-4 md:grid-cols-3">
            {(Object.values(d.results) as HqaResult[]).map((r) => (
              <BotCard key={r.key} r={r} s={sel.scores[r.key]} winner={sel.winner_key === r.key} tied={sel.tied_keys.includes(r.key)} />
            ))}
          </div>
          {d.notes.length > 0 && (
            <Card className="p-5"><h3 className="text-sm font-semibold">How the replies differ</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{d.notes.map((n) => <li key={n}>{n}</li>)}</ul>
              <p className="mt-2 text-xs text-muted-foreground">Structural comparison only - not a statement of medical correctness. {d.run_id && "Saved for the User Study."}</p>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export function useTopics() {
  return useQuery({ queryKey: ["hqa-topics"], queryFn: () => api.get<Topics>("/health-qa/topics"), staleTime: 300_000 });
}
