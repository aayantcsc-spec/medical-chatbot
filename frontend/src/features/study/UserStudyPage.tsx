import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Download, Send } from "lucide-react";
import { EmptyState, ErrorState, PageHeader, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, CardContent, CardHeader, CardTitle, Label, Select, Textarea } from "@/components/ui/primitives";
import { Checkbox } from "@/components/ui/overlays";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";
import { archLabel, cn, formatDate, num } from "@/lib/utils";

type RunItem = { run_id: string; question: string; created_at: string; rated?: boolean };
type Slot = { slot: string; token: string; position: number; response: string; ratable: boolean; my_rating: Record<string, number | string | null> | null };
type RunDetail = { run_id: string; question: string; responses: Slot[]; criteria: string[]; scale: string };
type Summary = { participants: number; completed_ratings: number; min_participants: number; sufficient: boolean;
  per_architecture: Record<string, { n: number; mean: Record<string, number | null>; n_rated: Record<string, number> }>; criteria: string[] };

function RateRun({ id }: { id: string }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["study-run", id], queryFn: () => api.get<RunDetail>(`/study/runs/${id}`) });
  const [ratings, setRatings] = useState<Record<string, Record<string, string>>>({});
  const [consent, setConsent] = useState(false);
  useEffect(() => {
    if (q.data) setRatings(Object.fromEntries(q.data.responses.map((r) => [r.token,
      Object.fromEntries([...q.data.criteria, "comment"].map((c) => [c, r.my_rating?.[c] == null ? "" : String(r.my_rating[c])]))])));
  }, [q.data]);
  const submit = useMutation({
    mutationFn: () => api.post("/study/ratings", {
      run_id: id, consent,
      positions: Object.fromEntries(q.data!.responses.map((r) => [r.token, r.position])),
      ratings: Object.fromEntries(q.data!.responses.filter((r) => r.ratable).map((r) => [r.token, Object.fromEntries(Object.entries(ratings[r.token] ?? {})
        .map(([k, v]) => [k, k === "comment" ? v : v === "" ? null : Number(v)]))])),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["study-summary"] }); qc.invalidateQueries({ queryKey: ["study-run", id] }); },
  });
  if (q.isLoading) return <div className="py-10 text-center"><Spinner /></div>;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  return (
    <div className="space-y-4">
      <Card className="p-5"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Question</p><p className="mt-1 font-medium">{d.question}</p>
        <p className="mt-2 text-xs text-muted-foreground">Replies are shown as A/B/C in an order shuffled for you. Bot names are hidden so they don't influence your ratings. Scale: {d.scale}.</p></Card>
      <div className="grid gap-4 lg:grid-cols-3">
        {d.responses.map((r) => (
          <Card key={r.token} className="flex flex-col">
            <CardHeader className="pb-2"><CardTitle>Reply {r.slot}</CardTitle></CardHeader>
            <CardContent className="flex flex-1 flex-col gap-3">
              <div className="max-h-64 overflow-y-auto rounded-md border bg-background/60 p-3 text-sm scrollbar-thin"><Markdown text={r.response || "(no reply)"} /></div>
              {r.ratable ? d.criteria.map((c) => (
                <div key={c} className="grid grid-cols-[1fr_auto] items-center gap-2">
                  <Label htmlFor={`${r.token}-${c}`} className="text-xs capitalize">{c === "safety" ? "Perceived safety" : c}</Label>
                  <Select id={`${r.token}-${c}`} className="h-8 w-28 text-xs" value={ratings[r.token]?.[c] ?? ""}
                    onChange={(e) => setRatings((s) => ({ ...s, [r.token]: { ...s[r.token], [c]: e.target.value } }))}>
                    <option value="">N/A</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</Select>
                </div>
              )) : <p className="text-xs text-muted-foreground">This bot could not answer, so there is nothing to rate.</p>}
              {r.ratable && <Textarea rows={2} maxLength={500} placeholder="Optional comment" className="text-xs" aria-label={`Comment on reply ${r.slot}`}
                value={ratings[r.token]?.comment ?? ""} onChange={(e) => setRatings((s) => ({ ...s, [r.token]: { ...s[r.token], comment: e.target.value } }))} />}
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="space-y-3 p-5">
        <label className="flex items-start gap-3 text-sm"><Checkbox checked={consent} onCheckedChange={(v) => setConsent(v === true)} className="mt-0.5" />
          <span>I agree that my ratings are stored under a pseudonymous participant ID and used for this research project. I can stop at any time.</span></label>
        {submit.error && <Alert variant="critical">{(submit.error as Error).message}</Alert>}
        {submit.isSuccess && <Alert variant="success">Ratings saved. Submitting again updates them - nothing is duplicated.</Alert>}
        <Button onClick={() => submit.mutate()} disabled={!consent} loading={submit.isPending}><Send /> Submit ratings</Button>
      </Card>
    </div>
  );
}

export default function UserStudyPage() {
  useDocumentTitle("User Study");
  const runs = useQuery({ queryKey: ["study-runs"], queryFn: () => api.get<RunItem[]>("/study/runs") });
  const summary = useQuery({ queryKey: ["study-summary"], queryFn: () => api.get<Summary>("/study/summary") });
  const [active, setActive] = useState<string>("");
  const id = active || runs.data?.[0]?.run_id || "";
  const s = summary.data;

  return (
    <>
      <PageHeader title="User Study" description="Rate Health Q&A replies for helpfulness, relevance, clarity, trustworthiness and perceived safety. Ratings measure perception, not medical correctness."
        actions={<Button variant="outline" asChild><a href={api.href("/study/export.csv")} download><Download /> Export CSV</a></Button>} />
      <Alert variant="info" className="mb-5">You can only rate your own comparison runs, because other people's questions may contain personal health information.
        Ethics approval for a study with participants is the responsibility of your institution.</Alert>
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-4">
          {runs.isLoading && <Spinner />}
          {runs.error && <ErrorState error={runs.error} onRetry={() => runs.refetch()} />}
          {runs.data && runs.data.length === 0 && (
            <EmptyState icon={ClipboardCheck} title="Nothing to rate yet" description="Ask a question in Health Q&A Comparison while signed in - each comparison is saved here for rating."
              action={<Button asChild><Link to="/health-qa-comparison">Open Health Q&amp;A Comparison</Link></Button>} />
          )}
          {runs.data && runs.data.length > 0 && (
            <>
              <div className="max-w-xl space-y-1.5"><Label htmlFor="run">Comparison to rate</Label>
                <Select id="run" value={id} onChange={(e) => setActive(e.target.value)}>
                  {runs.data.map((r) => <option key={r.run_id} value={r.run_id}>{formatDate(r.created_at)} · {r.question.slice(0, 70)}</option>)}</Select></div>
              {id && <RateRun key={id} id={id} />}
            </>
          )}
        </div>
        <Card className="h-fit">
          <CardHeader><CardTitle>Study summary</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {summary.isLoading && <Spinner />}
            {s && <>
              <p><strong>{s.participants}</strong> participants · <strong>{s.completed_ratings}</strong> ratings</p>
              {!s.sufficient ? <Alert variant="warning">Averages are shown from {s.min_participants} participants. Below that, do not draw conclusions.</Alert> : (
                <div className="space-y-3">{Object.entries(s.per_architecture).map(([k, v]) => (
                  <div key={k}><p className="font-medium">{archLabel(k)} <span className="text-xs font-normal text-muted-foreground">· {v.n} ratings</span></p>
                    <div className="mt-1 flex flex-wrap gap-1.5">{s.criteria.map((c) => {
                      const m = v.mean[c] ?? null;
                      return <Badge key={c} variant="muted" className={cn(m === null && "opacity-60")}>{c}: {m === null ? "—" : num(m, 1)}</Badge>;
                    })}</div></div>))}</div>
              )}
            </>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
