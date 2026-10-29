import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

export const ms = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v < 10 ? `${v.toFixed(2)} ms` : v < 1000 ? `${v.toFixed(0)} ms` : `${(v / 1000).toFixed(2)} s`;

export const num = (v: number | null | undefined, digits = 2) => (v === null || v === undefined ? "—" : v.toFixed(digits));

/** SQLite timestamps are UTC without a zone; ISO strings from run files already carry one. */
export function toDate(value?: string | null) {
  if (!value) return null;
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : value.replace(" ", "T") + "Z";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(value?: string | null, withTime = true) {
  const d = toDate(value);
  if (!d) return "—";
  return d.toLocaleString(undefined, withTime
    ? { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "numeric", month: "short", year: "numeric" });
}

export function relativeTime(value?: string | null) {
  const d = toDate(value);
  if (!d) return "";
  const s = Math.round((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
  return formatDate(value, false);
}

export const BOTS = ["rule", "ml", "dl"] as const;
export const ARCH_LABELS: Record<string, string> = {
  rule: "Rule-Based", ml: "TF-IDF + SVM", dl: "DistilBERT",
  // labels for conversations saved before the scope was fixed to three chatbots
  rule_based: "Rule-Based (archived)", nlp_based: "NLP-Based (archived)", classification: "Classification (archived)",
  retrieval_based: "Retrieval (archived)", rag_based: "RAG (archived)", generation_based: "Generation (archived)",
  lr: "Logistic Regression (archived)", mlp: "MLP (archived)", comparison: "Comparison",
};
export const ARCH_KIND: Record<string, string> = { rule: "Rule-Based", ml: "Machine Learning", dl: "Deep Learning" };
export const archLabel = (k?: string | null) => (k ? ARCH_LABELS[k] ?? k : "—");

/** Fixed colour per chatbot (validated slots 1-3: distinguishable for all pairs, incl. colour-vision deficiency). */
export const ARCH_COLORS: Record<string, string> = { rule: "hsl(var(--chart-1))", ml: "hsl(var(--chart-2))", dl: "hsl(var(--chart-3))" };
export const archColor = (k: string) => ARCH_COLORS[k] ?? "hsl(var(--muted-foreground))";
