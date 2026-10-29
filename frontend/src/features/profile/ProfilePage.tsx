import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, ShieldCheck, Trash2 } from "lucide-react";
import { ErrorState, PageHeader, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, Select, Textarea } from "@/components/ui/primitives";
import { Checkbox, Dialog, DialogClose, DialogContent } from "@/components/ui/overlays";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useTheme";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Profile } from "@/types/api";

type Resp = { profile: Profile | null; choices: Record<"age_range" | "smoking" | "activity_level", string[]>; purpose: string };
const EMPTY = { age_range: "", height: "", weight: "", smoking: "", activity_level: "", health_goal: "" };
const LEGACY_LABELS: Record<string, string> = { age: "Age", sex: "Sex", allergies: "Allergies", medical_conditions: "Medical conditions",
  medications: "Medications", health_notes: "Health notes", health_concern: "Health concern" };

export default function ProfilePage() {
  useDocumentTitle("Health Profile");
  const qc = useQueryClient();
  const { refresh } = useAuth();
  const q = useQuery({ queryKey: ["profile"], queryFn: () => api.get<Resp>("/profile") });
  const [form, setForm] = useState(EMPTY);
  const [clearLegacy, setClearLegacy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    const p = q.data?.profile;
    if (p) setForm({ age_range: p.age_range ?? "", height: p.height ?? "", weight: p.weight ?? "", smoking: p.smoking ?? "",
                     activity_level: p.activity_level ?? "", health_goal: p.health_goal ?? "" });
  }, [q.data]);
  const save = useMutation({
    mutationFn: () => api.put("/profile", { ...form, acknowledged: !q.data?.profile?.consent_at ? true : undefined, clear_legacy_fields: clearLegacy }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["profile"] }); setSaved(true); setClearLegacy(false); setTimeout(() => setSaved(false), 2500); refresh(); },
  });
  const del = useMutation({ mutationFn: () => api.del("/profile"), onSuccess: async () => { setConfirm(false); setForm(EMPTY); await qc.invalidateQueries({ queryKey: ["profile"] }); } });
  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  if (q.isLoading) return <div className="py-20 text-center"><Spinner /></div>;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const p = q.data!.profile;
  const legacy = Object.entries(p?.legacy_fields ?? {});
  const select = (k: "age_range" | "smoking" | "activity_level", label: string) => (
    <div className="space-y-1.5"><Label htmlFor={k}>{label}</Label>
      <Select id={k} value={form[k]} onChange={set(k)}><option value="">Not provided</option>
        {q.data!.choices[k].map((c) => <option key={c} value={c}>{c}</option>)}</Select></div>
  );

  return (
    <>
      <PageHeader title="Health Profile" description="Optional information you choose to share. You can change or delete it at any time." />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card>
          <CardHeader><CardTitle>Your details</CardTitle><CardDescription>{q.data!.purpose}</CardDescription></CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
              <div className="grid gap-4 sm:grid-cols-2">
                {select("age_range", "Age range")}
                {select("activity_level", "Activity level")}
                <div className="space-y-1.5"><Label htmlFor="height">Height</Label><Input id="height" maxLength={20} value={form.height} onChange={set("height")} placeholder="e.g. 168 cm" /></div>
                <div className="space-y-1.5"><Label htmlFor="weight">Weight</Label><Input id="weight" maxLength={20} value={form.weight} onChange={set("weight")} placeholder="e.g. 62 kg" /></div>
                {select("smoking", "Smoking")}
                <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="goal">Lifestyle goal</Label>
                  <Textarea id="goal" rows={2} maxLength={120} value={form.health_goal} onChange={set("health_goal")} /></div>
              </div>
              {legacy.length > 0 && (
                <Alert variant="warning" title="Older profile fields are stored">
                  <p>An earlier version of this app collected: {legacy.map(([k]) => LEGACY_LABELS[k] ?? k).join(", ")}. They are not needed and are not used.</p>
                  <label className="mt-2 flex items-center gap-2"><Checkbox checked={clearLegacy} onCheckedChange={(v) => setClearLegacy(v === true)} />Remove them when I save</label>
                </Alert>
              )}
              {save.error && <Alert variant="critical">{(save.error as Error).message}</Alert>}
              {saved && <Alert variant="success">Profile saved.</Alert>}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" loading={save.isPending}><Save /> Save changes</Button>
                {p && <Button type="button" variant="outline" className="text-critical" onClick={() => setConfirm(true)}><Trash2 /> Delete profile</Button>}
              </div>
            </form>
          </CardContent>
        </Card>
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex gap-3"><ShieldCheck className="size-5 shrink-0 text-secondary" />
              <div className="space-y-2 text-sm">
                <p className="font-semibold">How this is used</p>
                <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
                  <li>Never used to diagnose or to change a chatbot's answer.</li>
                  <li>Not shared with any external service.</li>
                  <li>Deleting the profile removes it immediately; deleting your account (Settings) removes everything.</li>
                </ul>
              </div></div>
          </Card>
          <Card className="p-5 text-sm">
            <p className="text-muted-foreground">Research acknowledgement</p>
            <p className="font-medium">{p?.consent_at ? `Confirmed ${formatDate(p.consent_at)}` : "Not yet confirmed"}</p>
            {p?.updated_at && <p className="mt-2 text-xs text-muted-foreground">Last updated {formatDate(p.updated_at)}</p>}
          </Card>
        </div>
      </div>
      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent title="Delete your health profile?" description="All profile fields are removed permanently. Your account and conversations are kept. You'll be asked to confirm the research acknowledgement again.">
          <div className="flex justify-end gap-2"><DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button variant="destructive" loading={del.isPending} onClick={() => del.mutate()}>Delete profile</Button></div>
        </DialogContent>
      </Dialog>
    </>
  );
}
