/* Chart building blocks (Recharts). Rules followed (dataviz skill):
   - one measure per chart, one y-axis; colour follows the architecture (fixed slot), never its rank
   - thin marks, 4px rounded data-ends on bars, 2px lines, recessive grid
   - hover tooltip on every chart; text in text tokens, never in the series colour
   - legend for >= 2 series; every chart has a Table view (relief for sub-3:1 light-mode slots) */
import { useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
         type TooltipProps } from "recharts";
import { BarChart3, Table2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/primitives";
import { archColor, cn } from "@/lib/utils";

const AXIS = { fontSize: 12, fill: "hsl(var(--muted-foreground))" };
const GRID = "hsl(var(--chart-grid))";

export interface TableSpec { columns: string[]; rows: (string | number | ReactNode)[][] }

export function ChartCard({ title, description, table, legend, children, className, footer }: {
  title: string; description?: ReactNode; table?: TableSpec; legend?: { key: string; label: string }[];
  children: ReactNode; className?: string; footer?: ReactNode;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");
  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="min-w-0 space-y-1"><CardTitle>{title}</CardTitle>{description && <CardDescription>{description}</CardDescription>}</div>
        {table && (
          <div className="flex shrink-0 rounded-md border p-0.5" role="group" aria-label={`${title} view`}>
            {(["chart", "table"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} aria-pressed={view === v} aria-label={v === "chart" ? "Chart view" : "Table view"}
                className={cn("grid size-7 place-items-center rounded text-muted-foreground", view === v && "bg-muted text-foreground")}>
                {v === "chart" ? <BarChart3 className="size-4" /> : <Table2 className="size-4" />}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="flex-1">
        {legend && legend.length >= 2 && view === "chart" && (
          <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground" aria-label="Legend">
            {legend.map((l) => (
              <li key={l.key} className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm" style={{ background: archColor(l.key) }} aria-hidden />{l.label}</li>
            ))}
          </ul>
        )}
        {view === "chart" || !table ? children : (
          <div className="max-h-80 overflow-auto rounded-md border">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-muted text-xs text-muted-foreground">
                <tr>{table.columns.map((c) => <th key={c} className="px-3 py-2 font-medium">{c}</th>)}</tr>
              </thead>
              <tbody className="divide-y">
                {table.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={cn("px-3 py-2", j > 0 && "tabular")}>{c}</td>)}</tr>)}
              </tbody>
            </table>
          </div>
        )}
        {footer && <div className="mt-3 text-xs text-muted-foreground">{footer}</div>}
      </CardContent>
    </Card>
  );
}

function TooltipBox({ title, rows }: { title?: ReactNode; rows: { key: string; label: string; value: string }[] }) {
  return (
    <div className="min-w-[10rem] rounded-lg border bg-card px-3 py-2 text-xs shadow-lift">
      {title && <p className="mb-1 font-semibold text-foreground">{title}</p>}
      {rows.map((r) => (
        <p key={r.key} className="flex items-center justify-between gap-4 text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm" style={{ background: archColor(r.key) }} />{r.label}</span>
          <span className="font-medium text-foreground tabular">{r.value}</span>
        </p>
      ))}
    </div>
  );
}

export interface BarDatum { key: string; label: string; value: number | null; note?: string }

/** One measure across architectures. Bars are coloured by architecture; the x-axis names each one. */
export function MetricBars({ data, format, domain, height = 240, emptyLabel = "Not applicable" }: {
  data: BarDatum[]; format: (v: number) => string; domain?: [number, number]; height?: number; emptyLabel?: string;
}) {
  const rows = data.map((d) => ({ ...d, plot: d.value ?? 0 }));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }} barCategoryGap="28%">
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval={0}
                 tickFormatter={(v: string) => (v.length > 12 ? v.replace("-Based", "").replace("Classification", "Classif.") : v)} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={domain ?? [0, "auto"]} tickFormatter={(v: number) => format(v)} width={56} />
          <Tooltip cursor={{ fill: "hsl(var(--muted))", opacity: 0.6 }}
            content={({ active, payload }: TooltipProps<number, string>) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]!.payload as BarDatum;
              return <TooltipBox title={d.label} rows={[{ key: d.key, label: d.note ?? "Value", value: d.value === null ? emptyLabel : format(d.value) }]} />;
            }} />
          <Bar dataKey="plot" radius={[4, 4, 0, 0]} maxBarSize={48} stroke="hsl(var(--card))" strokeWidth={2}>
            {rows.map((d) => <Cell key={d.key} fill={d.value === null ? "hsl(var(--muted))" : archColor(d.key)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Change over runs, one line per architecture (legend rendered by ChartCard). */
export function HistoryLines({ rows, series, format, domain, height = 260 }: {
  rows: Record<string, number | string | null>[]; series: { key: string; label: string }[]; format: (v: number) => string;
  domain?: [number, number]; height?: number;
}) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={domain ?? [0, "auto"]} tickFormatter={(v: number) => format(v)} width={56} />
          <Tooltip cursor={{ stroke: "hsl(var(--muted-foreground))", strokeDasharray: "3 3" }}
            content={({ active, payload, label }: TooltipProps<number, string>) => {
              if (!active || !payload?.length) return null;
              return <TooltipBox title={label} rows={payload.filter((p) => p.value !== null && p.value !== undefined)
                .map((p) => ({ key: String(p.dataKey), label: series.find((s) => s.key === p.dataKey)?.label ?? String(p.dataKey), value: format(Number(p.value)) }))} />;
            }} />
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} stroke={archColor(s.key)} strokeWidth={2} connectNulls
                  dot={{ r: 4, strokeWidth: 2, stroke: "hsl(var(--card))", fill: archColor(s.key) }} activeDot={{ r: 5 }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Counts per bucket for a single series (sequential, one hue). */
export function CountBars({ data, height = 220, xLabel }: { data: { name: string; count: number }[]; height?: number; xLabel?: string }) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: xLabel ? 16 : 0, left: -16 }} barCategoryGap="18%">
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd"
                 label={xLabel ? { value: xLabel, position: "insideBottom", offset: -10, style: AXIS } : undefined} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} width={44} />
          <Tooltip cursor={{ fill: "hsl(var(--muted))", opacity: 0.6 }}
            content={({ active, payload }: TooltipProps<number, string>) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]!.payload as { name: string; count: number };
              return <div className="rounded-lg border bg-card px-3 py-2 text-xs shadow-lift"><p className="font-semibold">{d.name}</p>
                <p className="text-muted-foreground">Count: <span className="font-medium text-foreground">{d.count}</span></p></div>;
            }} />
          <Bar dataKey="count" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} maxBarSize={40} stroke="hsl(var(--card))" strokeWidth={2} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
