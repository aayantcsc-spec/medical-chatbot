import { Link } from "react-router-dom";
import { ArrowRight, Brain, CheckCircle2, ClipboardCheck, Cpu, GitCompareArrows, ListChecks, ShieldCheck, Timer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { useDocumentTitle } from "@/hooks/useTheme";

const APPROACHES = [
  { icon: ListChecks, kind: "Rule-Based", name: "Rules & keywords", text: "Predefined rules, keywords, phrase patterns and mapped responses. No training - every decision can be traced to a rule." },
  { icon: Cpu, kind: "Machine Learning", name: "TF-IDF + SVM", text: "Questions are turned into TF-IDF features and a linear Support Vector Machine, trained on labelled questions, predicts the topic." },
  { icon: Brain, kind: "Deep Learning", name: "DistilBERT", text: "A fine-tuned DistilBERT transformer reads the whole question in context to predict the topic." },
];
const METRICS = [
  { icon: CheckCircle2, name: "Correctness", text: "Is the right health topic recognised? Measured on held-out questions the models never trained on." },
  { icon: ShieldCheck, name: "Safety", text: "Urgent-care guidance for emergencies, declining off-topic questions, no doses or diagnosis claims." },
  { icon: ClipboardCheck, name: "Response quality", text: "Automated relevance, completeness and clarity checks, plus blinded human ratings in the User Study." },
  { icon: Timer, name: "Response time", text: "Model inference time per question, measured the same way for all three." },
];

export default function LandingPage() {
  useDocumentTitle("");
  return (
    <>
      <section className="border-b bg-gradient-to-b from-accent/70 to-background">
        <div className="container grid gap-10 py-14 md:py-20 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div className="space-y-6">
            <p className="text-sm font-medium text-primary">Final-year B.Sc. AI &amp; ML research project</p>
            <h1 className="text-4xl font-bold leading-tight text-balance sm:text-5xl">MediChat</h1>
            <p className="text-xl font-medium text-foreground/90 text-balance">Comparative Analysis of Health Chatbots Based on Framework and Architecture</p>
            <p className="max-w-xl text-muted-foreground">
              MediChat compares different AI approaches for healthcare questions and evaluates their response quality, correctness, response time, and safety.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button size="lg" asChild><Link to="/register">Get started <ArrowRight /></Link></Button>
              <Button size="lg" variant="outline" asChild><Link to="/login">Sign in</Link></Button>
            </div>
          </div>
          <Card className="space-y-4 p-6">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">One question, three answers</p>
            <p className="rounded-lg bg-muted p-3 text-sm font-medium">“What can cause fever and headache?”</p>
            {APPROACHES.map(({ icon: Icon, kind, name }) => (
              <div key={kind} className="flex items-center gap-3 rounded-lg border p-3">
                <Icon className="size-5 text-primary" aria-hidden />
                <div><p className="text-sm font-semibold">{name}</p><p className="text-xs text-muted-foreground">{kind}</p></div>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">Replies are compared on correctness, safety, quality and speed.</p>
          </Card>
        </div>
      </section>

      <section id="architectures" className="container scroll-mt-20 py-16">
        <h2 className="text-2xl font-semibold">Three chatbot architectures</h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">Each answers the same question independently, using its own logic. Their answers can differ - that difference is what the project studies.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {APPROACHES.map(({ icon: Icon, kind, name, text }) => (
            <Card key={kind} className="p-5">
              <span className="mb-3 grid size-10 place-items-center rounded-lg bg-accent text-accent-foreground"><Icon className="size-5" aria-hidden /></span>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{kind}</p>
              <h3 className="font-semibold">{name}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{text}</p>
            </Card>
          ))}
        </div>
        <div className="mt-6"><Button variant="link" asChild><Link to="/architecture">How a question is processed <ArrowRight /></Link></Button></div>
      </section>

      <section id="methodology" className="scroll-mt-20 border-y bg-card py-16">
        <div className="container">
          <h2 className="text-2xl font-semibold">What is measured</h2>
          <p className="mt-2 max-w-2xl text-muted-foreground">All three chatbots answer the same test questions. Metrics are reported separately and only from real evaluation runs.</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {METRICS.map(({ icon: Icon, name, text }) => (
              <div key={name} className="space-y-2"><Icon className="size-5 text-primary" aria-hidden /><h3 className="font-semibold">{name}</h3><p className="text-sm text-muted-foreground">{text}</p></div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-3 text-sm">
            <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5"><GitCompareArrows className="size-4 text-primary" />Side-by-side comparison of your own question</span>
            <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5"><ClipboardCheck className="size-4 text-primary" />Blinded user study</span>
          </div>
        </div>
      </section>

      <section id="safety" className="container scroll-mt-20 py-16">
        <div className="rounded-2xl border border-warning/30 bg-warning-soft p-6 sm:p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-start">
            <ShieldCheck className="size-7 shrink-0 text-warning" aria-hidden />
            <div className="space-y-2">
              <h2 className="text-lg font-semibold">Health disclaimer</h2>
              <p className="text-sm text-foreground/80">MediChat gives general health information for education and research. It does not diagnose conditions, prescribe medicines
                or replace a qualified healthcare professional, and it has not been clinically validated. If you think you may be having an emergency,
                call <strong>112</strong> in India or your local emergency number.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
