import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, ShieldCheck } from "lucide-react";
import { Logo, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Card, Input, Label, Select, Textarea } from "@/components/ui/primitives";
import { Checkbox } from "@/components/ui/overlays";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Choices = { age_range: string[]; smoking: string[]; activity_level: string[] };
const STEPS = ["Your name", "Optional details", "Before you start"];

export default function OnboardingPage() {
  useDocumentTitle("Welcome");
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState(user?.name ?? "");
  const [form, setForm] = useState({ age_range: "", height: "", weight: "", smoking: "", activity_level: "", health_goal: "" });
  const [ack, setAck] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const choices = useQuery({ queryKey: ["profile"], queryFn: () => api.get<{ choices: Choices; purpose: string }>("/profile") });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function finish() {
    setSaving(true);
    setError(null);
    try {
      if (name.trim() && name.trim() !== user?.name) await api.patch("/auth/me", { name: name.trim() });
      await api.put("/profile", { ...form, acknowledged: true });
      await refresh();
      navigate("/dashboard", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Your answers could not be saved. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const canNext = step === 0 ? name.trim().length > 0 : true;
  return (
    <div className="grid min-h-[calc(100dvh-4rem)] place-items-center bg-gradient-to-b from-accent/60 to-background px-4 py-10">
      <div className="w-full max-w-xl">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <Logo compact />
          <h1 className="text-2xl font-semibold">Welcome to MediChat</h1>
          <ol className="flex items-center gap-2 text-xs" aria-label="Progress">
            {STEPS.map((s, i) => (
              <li key={s} className="flex items-center gap-2">
                <span className={cn("grid size-6 place-items-center rounded-full border text-[11px] font-semibold",
                  i < step ? "border-success bg-success text-white" : i === step ? "border-primary bg-primary text-primary-foreground" : "bg-card text-muted-foreground")}
                  aria-current={i === step ? "step" : undefined}>{i < step ? <Check className="size-3.5" /> : i + 1}</span>
                <span className={cn("hidden sm:inline", i === step ? "font-medium" : "text-muted-foreground")}>{s}</span>
                {i < STEPS.length - 1 && <span className="h-px w-6 bg-border" aria-hidden />}
              </li>
            ))}
          </ol>
        </div>
        <Card className="overflow-hidden p-6 sm:p-8">
          {choices.isLoading ? <div className="py-10 text-center"><Spinner /></div> : (
            <AnimatePresence mode="wait">
              <motion.div key={step} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }} transition={{ duration: 0.2 }}>
                {step === 0 && (
                  <div className="space-y-4">
                    <div><h2 className="text-lg font-semibold">What should we call you?</h2>
                      <p className="text-sm text-muted-foreground">Shown in the app only.</p></div>
                    <div className="space-y-1.5"><Label htmlFor="dn">Display name</Label>
                      <Input id="dn" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoFocus /></div>
                  </div>
                )}
                {step === 1 && (
                  <div className="space-y-4">
                    <div><h2 className="text-lg font-semibold">A few optional details</h2>
                      <p className="text-sm text-muted-foreground">{choices.data?.purpose ?? "All fields are optional."} Skip anything you prefer not to share.</p></div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-1.5"><Label htmlFor="age">Age range</Label>
                        <Select id="age" value={form.age_range} onChange={set("age_range")}>
                          <option value="">Prefer not to say</option>
                          {choices.data?.choices.age_range.filter((c) => c !== "prefer not to say").map((c) => <option key={c} value={c}>{c}</option>)}
                        </Select></div>
                      <div className="space-y-1.5"><Label htmlFor="act">Activity level</Label>
                        <Select id="act" value={form.activity_level} onChange={set("activity_level")}>
                          <option value="">Prefer not to say</option>
                          {choices.data?.choices.activity_level.filter((c) => c !== "prefer not to say").map((c) => <option key={c} value={c}>{c}</option>)}
                        </Select></div>
                      <div className="space-y-1.5"><Label htmlFor="h">Height</Label>
                        <Input id="h" placeholder="e.g. 168 cm" maxLength={20} value={form.height} onChange={set("height")} /></div>
                      <div className="space-y-1.5"><Label htmlFor="w">Weight</Label>
                        <Input id="w" placeholder="e.g. 62 kg" maxLength={20} value={form.weight} onChange={set("weight")} /></div>
                      <div className="space-y-1.5"><Label htmlFor="sm">Smoking</Label>
                        <Select id="sm" value={form.smoking} onChange={set("smoking")}>
                          <option value="">Prefer not to say</option>
                          {choices.data?.choices.smoking.filter((c) => c !== "prefer not to say").map((c) => <option key={c} value={c}>{c}</option>)}
                        </Select></div>
                      <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="goal">Lifestyle goal</Label>
                        <Textarea id="goal" rows={2} maxLength={120} placeholder="e.g. sleep better, walk more" value={form.health_goal} onChange={set("health_goal")} /></div>
                    </div>
                  </div>
                )}
                {step === 2 && (
                  <div className="space-y-5">
                    <div className="flex gap-3"><ShieldCheck className="size-6 shrink-0 text-secondary" aria-hidden />
                      <div><h2 className="text-lg font-semibold">How to use MediChat safely</h2>
                        <p className="text-sm text-muted-foreground">Please read and confirm.</p></div></div>
                    <ul className="space-y-2 rounded-lg bg-muted/60 p-4 text-sm">
                      <li>• MediChat is a <strong>research and educational</strong> tool. It gives general information only.</li>
                      <li>• It <strong>cannot diagnose</strong> conditions, prescribe medicines or replace a doctor.</li>
                      <li>• Chatbot scores are model outputs, <strong>not medical certainty</strong>.</li>
                      <li>• In an emergency, call <strong>112</strong> (India) or your local emergency number - don't wait for a chatbot.</li>
                    </ul>
                    <label className="flex cursor-pointer items-start gap-3 rounded-lg border p-3">
                      <Checkbox checked={ack} onCheckedChange={(v) => setAck(v === true)} className="mt-0.5" aria-describedby="ack-text" />
                      <span id="ack-text" className="text-sm">I understand MediChat is for research and education and is not a substitute for professional medical care.</span>
                    </label>
                    {error && <Alert variant="critical">{error}</Alert>}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          )}
          <div className="mt-8 flex items-center justify-between gap-3">
            <Button variant="ghost" onClick={() => setStep((s) => s - 1)} disabled={step === 0}><ArrowLeft /> Back</Button>
            {step < 2 ? <Button onClick={() => setStep((s) => s + 1)} disabled={!canNext}>{step === 1 ? "Continue" : "Next"} <ArrowRight /></Button>
              : <Button onClick={finish} disabled={!ack} loading={saving}>Go to dashboard <ArrowRight /></Button>}
          </div>
        </Card>
      </div>
    </div>
  );
}
