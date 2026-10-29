import { useState } from "react";
import { History, Library } from "lucide-react";
import { ErrorState, PageHeader } from "@/components/common";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, Input } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";
import { archLabel, pct } from "@/lib/utils";
import { HealthQaCompare, useTopics } from "./HealthQaCompare";

export default function HealthQaComparisonPage() {
  useDocumentTitle("Health Q&A Comparison");
  const topics = useTopics();
  const [filter, setFilter] = useState("");
  const t = topics.data;
  return (
    <>
      <PageHeader eyebrow="Separate from the six-architecture system" title="Health Q&A Comparison"
        description="One general health question, three independently trained bots. Each reply is checked for safety and scored for relevance, completeness and clarity; an unsafe reply can never be selected." />
      {topics.error && <ErrorState error={topics.error} onRetry={() => topics.refetch()} className="mb-6" />}
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <HealthQaCompare topics={t} />
        <aside className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><Library className="size-4" /> Knowledge base</CardTitle>
              <CardDescription>{t ? `${t.topic_count} topics across ${t.categories.length} categories` : "Loading…"}</CardDescription></CardHeader>
            <CardContent>
              <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter categories" aria-label="Filter categories" className="mb-3 h-9" />
              <div className="flex max-h-56 flex-wrap gap-1.5 overflow-y-auto scrollbar-thin">
                {t?.categories.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase())).map((c) => <Badge key={c.id} variant="muted">{c.name}</Badge>)}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">Questions outside these topics get a polite "I'm not sure - please ask a doctor" reply.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Model status</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {t && Object.values(t.models).map((m) => (
                <div key={m.key} className="flex items-start justify-between gap-2">
                  <span className="min-w-0"><span className="block font-medium">{archLabel(m.key)}</span>
                    <span className="block truncate text-xs text-muted-foreground" title={m.architecture}>{m.architecture}</span></span>
                  <Badge variant={m.available ? "success" : "critical"}>{m.available ? "Ready" : "Unavailable"}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
          {t && (
            <Card className="border-dashed">
              <CardHeader><CardTitle className="flex items-center gap-2"><History className="size-4" /> Historical reference</CardTitle>
                <CardDescription>{t.historical_reference.status}</CardDescription></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>Logistic Regression topic accuracy: <strong>{pct(t.historical_reference.values.ml_logistic_regression_topic_accuracy, 0)}</strong></p>
                <p>MLP topic accuracy: <strong>{pct(t.historical_reference.values.dl_mlp_topic_accuracy, 0)}</strong></p>
                <p className="text-xs text-muted-foreground">{t.historical_reference.provenance}</p>
              </CardContent>
            </Card>
          )}
        </aside>
      </div>
    </>
  );
}
