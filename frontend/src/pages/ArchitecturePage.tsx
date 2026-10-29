import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

type Stage = { id: string; title: string; sub: string; detail: string; tone?: "safety" | "bot" };
const STAGES: Stage[] = [
  { id: "ui", title: "Web interface", sub: "Chat · Comparison", detail: "You type a question in your own words. The browser only sends it; nothing is decided in the browser." },
  { id: "api", title: "Flask API", sub: "/api/v1", detail: "Checks the input (1-1,000 characters) and your session, and returns one consistent JSON response. Internal errors are logged, never shown." },
  { id: "safety", title: "Emergency check", sub: "before any chatbot", tone: "safety", detail: "Emergency wording (English, Hindi, Hinglish) - such as chest pain with breathing difficulty - is detected on the question itself and answered with urgent guidance (call 112 in India) before any model runs." },
  { id: "lang", title: "Language layer", sub: "same for all three", detail: "Greetings are answered without a model. Hindi and Hinglish health terms are converted to English so all three chatbots receive identical input." },
  { id: "bot", title: "Selected chatbot", sub: "Rule-Based · TF-IDF + SVM · DistilBERT", tone: "bot", detail: "Each chatbot predicts the health topic with its own method. If it is not confident, it says so instead of guessing." },
  { id: "reply", title: "Reply + safety gate", sub: "concise, with timing", detail: "A short answer is written for the predicted topic. A reply that gives a medicine dose, claims a diagnosis or discourages seeing a doctor is rejected and replaced with safe guidance." },
];

const ARCHS = [
  ["Rule-Based", "Keyword and phrase rules over 91 health topics, spelling repair, emergency rules.", "No training. Every match can be traced to a rule.", "Predictable and explainable; misses unusual wording."],
  ["TF-IDF + SVM (Machine Learning)", "TF-IDF word and character n-grams; linear SVM trained on labelled questions; a reject threshold tuned on validation data.", "Learns from examples.", "Very fast; depends on words seen in training."],
  ["DistilBERT (Deep Learning)", "Fine-tuned distilbert-base-uncased transformer classifier, run locally on CPU.", "Understands context.", "Handles new phrasing; slower and can answer off-topic questions."],
];

export default function ArchitecturePage() {
  useDocumentTitle("How it works");
  const [active, setActive] = useState("safety");
  const stage = STAGES.find((s) => s.id === active)!;
  return (
    <div className="container py-12">
      <PageHeader title="How a question is processed" description="Click a stage to see what it does. Every chatbot goes through the same path, which keeps the comparison fair." />
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="p-4 sm:p-6">
          <ol className="flex flex-col items-stretch gap-2" aria-label="Request flow">
            {STAGES.map((s, i) => (
              <li key={s.id} className="flex flex-col items-center">
                <button onClick={() => setActive(s.id)} aria-pressed={active === s.id}
                  className={cn("w-full max-w-md rounded-xl border px-4 py-3 text-left transition-all",
                    active === s.id ? "border-primary bg-accent ring-2 ring-primary/20" : "bg-card hover:border-primary/40")}>
                  <span className="flex items-center justify-between gap-3">
                    <span className="font-semibold">{s.title}</span>
                    {s.tone === "safety" && <Badge variant="success">Always first</Badge>}
                    {s.tone === "bot" && <Badge variant="muted">You choose</Badge>}
                  </span>
                  <span className="text-xs text-muted-foreground">{s.sub}</span>
                </button>
                {i < STAGES.length - 1 && <span aria-hidden className="my-0.5 h-5 w-px bg-border" />}
              </li>
            ))}
          </ol>
        </Card>
        <Card className="h-fit p-6 lg:sticky lg:top-24" aria-live="polite">
          <h2 className="text-xl font-semibold">{stage.title}</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{stage.detail}</p>
        </Card>
      </div>
      <h2 className="mb-4 mt-14 text-2xl font-semibold">The three chatbots</h2>
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="border-b bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr><th className="px-4 py-3">Chatbot</th><th className="px-4 py-3">Method</th><th className="px-4 py-3">Character</th><th className="px-4 py-3">Trade-off</th></tr>
          </thead>
          <tbody className="divide-y">
            {ARCHS.map(([n, m, o, t]) => (
              <tr key={n} className="align-top"><td className="px-4 py-3 font-medium">{n}</td><td className="px-4 py-3 text-muted-foreground">{m}</td>
                <td className="px-4 py-3">{o}</td><td className="px-4 py-3 text-muted-foreground">{t}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-10"><Button asChild><Link to="/register">Try MediChat <ArrowRight /></Link></Button></div>
    </div>
  );
}
