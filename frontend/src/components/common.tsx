import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, CircleSlash, FlaskConical, Loader2, RefreshCw, ShieldAlert, ShieldCheck, ShieldX, Siren } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import type { SafetyStatus } from "@/types/api";

export function Logo({ className, compact = false, inverted = false }: { className?: string; compact?: boolean; inverted?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 font-semibold", className)}>
      <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="8" fill="hsl(var(--primary))" />
        <path d="M13 8h6v5h5v6h-5v5h-6v-5H8v-6h5z" fill="hsl(var(--primary-foreground))" />
      </svg>
      {!compact && (
        <span className="leading-tight">
          <span className={cn("block text-[15px]", inverted ? "text-sidebar-foreground" : "text-foreground")}>MediChat</span>
          <span className={cn("block text-[11px] font-medium text-muted-foreground", inverted && "text-sidebar-muted")}>Health chatbot research</span>
        </span>
      )}
    </span>
  );
}

export function PageHeader({ title, description, actions, eyebrow }: { title: string; description?: ReactNode; actions?: ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 space-y-1.5">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-secondary">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold text-balance sm:text-[28px]">{title}</h1>
        {description && <p className="max-w-3xl text-sm text-muted-foreground sm:text-[15px]">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon = FlaskConical, title, description, action, className }: {
  icon?: typeof FlaskConical; title: string; description?: ReactNode; action?: ReactNode; className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-xl border border-dashed bg-card/50 px-6 py-12 text-center", className)}>
      <div className="mb-4 grid size-12 place-items-center rounded-full bg-accent text-accent-foreground"><Icon className="size-6" aria-hidden /></div>
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="mt-1.5 max-w-md text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className={cn("flex flex-col items-center gap-3 rounded-xl border border-critical/30 bg-critical-soft px-6 py-8 text-center", className)}>
      <AlertCircle className="size-6 text-critical" aria-hidden />
      <div>
        <p className="font-semibold text-critical">Could not load this</p>
        <p className="mt-1 text-sm text-foreground/80">{message}</p>
      </div>
      {onRetry && <Button variant="outline" size="sm" onClick={onRetry}><RefreshCw /> Try again</Button>}
    </div>
  );
}

export function LoadingCards({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-3", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="space-y-3 p-5"><Skeleton className="h-4 w-1/3" /><Skeleton className="h-7 w-1/2" /><Skeleton className="h-3 w-full" /></Card>
      ))}
    </div>
  );
}

export const Spinner = ({ label = "Loading" }: { label?: string }) => (
  <span className="inline-flex items-center gap-2 text-sm text-muted-foreground" role="status"><Loader2 className="size-4 animate-spin" />{label}</span>
);

export function StatCard({ label, value, hint, icon: Icon, tone = "default" }: {
  label: string; value: ReactNode; hint?: ReactNode; icon?: typeof FlaskConical; tone?: "default" | "success" | "warning";
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        {Icon && <span className={cn("grid size-9 place-items-center rounded-lg", tone === "success" ? "bg-success-soft text-success" :
          tone === "warning" ? "bg-warning-soft text-warning" : "bg-accent text-accent-foreground")}><Icon className="size-[18px]" aria-hidden /></span>}
      </div>
      <p className="mt-2 text-2xl font-semibold tabular">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}

const SAFETY: Record<SafetyStatus, { label: string; variant: "success" | "critical" | "warning" | "muted"; Icon: typeof ShieldCheck; hint: string }> = {
  passed: { label: "Safety passed", variant: "success", Icon: ShieldCheck, hint: "No dose, diagnosis claim or advice against seeing a doctor was found." },
  rejected: { label: "Reply withheld", variant: "warning", Icon: ShieldX, hint: "The reply failed the safety gate and was replaced with safe guidance." },
  emergency_override: { label: "Emergency guidance", variant: "critical", Icon: Siren, hint: "Urgent-care guidance replaced the ordinary reply." },
  not_applicable: { label: "Not checked", variant: "muted", Icon: ShieldAlert, hint: "No reply to check." },
};
export function SafetyBadge({ status }: { status?: SafetyStatus | null }) {
  const s = SAFETY[status ?? "not_applicable"] ?? SAFETY.not_applicable;
  return <Badge variant={s.variant} title={s.hint}><s.Icon className="size-3" aria-hidden />{s.label}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { v: "success" | "warning" | "critical" | "muted" | "default"; label: string; Icon?: typeof ShieldCheck }> = {
    ok: { v: "success", label: "Answered", Icon: CheckCircle2 }, completed: { v: "success", label: "Completed", Icon: CheckCircle2 },
    no_match: { v: "warning", label: "No confident match", Icon: CircleSlash }, unsupported: { v: "warning", label: "Unsupported" },
    small_talk: { v: "muted", label: "Small talk" }, running: { v: "default", label: "Running" }, pending: { v: "muted", label: "Queued" },
    error: { v: "critical", label: "Error", Icon: AlertCircle }, failed: { v: "critical", label: "Failed", Icon: AlertCircle },
    unavailable: { v: "critical", label: "Unavailable", Icon: AlertCircle },
  };
  const s = map[status] ?? { v: "muted" as const, label: status };
  return <Badge variant={s.v}>{s.Icon && <s.Icon className="size-3" aria-hidden />}{s.label}</Badge>;
}

export function MedicalDisclaimer({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <p className={cn("flex items-start gap-2 text-muted-foreground", compact ? "text-xs" : "text-sm", className)}>
      <ShieldAlert className={cn("mt-0.5 shrink-0 text-warning", compact ? "size-3.5" : "size-4")} aria-hidden />
      <span>MediChat provides general health information for education and research. It cannot diagnose conditions or replace a doctor.
        In an emergency call <strong className="text-foreground">112</strong> (India) or your local emergency number.</span>
    </p>
  );
}

export const TextLink = ({ to, children }: { to: string; children: ReactNode }) => (
  <Link to={to} className="font-medium text-primary underline-offset-4 hover:underline">{children}</Link>
);
