import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Monitor, Moon, Sun, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from "@/components/ui/primitives";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/overlays";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle, useTheme, type Theme } from "@/hooks/useTheme";
import { api, setCsrfToken } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";

export default function SettingsPage() {
  useDocumentTitle("Settings");
  const { user, refresh } = useAuth();
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name ?? "");
  const [confirmText, setConfirmText] = useState("");
  const [open, setOpen] = useState(false);
  const rename = useMutation({ mutationFn: () => api.patch("/auth/me", { name }), onSuccess: () => refresh() });
  const remove = useMutation({
    mutationFn: () => api.del<{ csrf_token: string }>("/auth/account", { confirm: confirmText }),
    onSuccess: (d) => { setCsrfToken(d.csrf_token); qc.clear(); qc.setQueryData(["me"], null); navigate("/", { replace: true }); },
  });

  return (
    <>
      <PageHeader title="Settings" description="Appearance, account details and data controls." />
      <div className="grid max-w-3xl gap-6">
        <Card>
          <CardHeader><CardTitle>Appearance</CardTitle><CardDescription>Stored only in this browser.</CardDescription></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Theme">
              {([["light", "Light", Sun], ["dark", "Dark", Moon], ["system", "System", Monitor]] as [Theme, string, typeof Sun][]).map(([v, label, Icon]) => (
                <button key={v} role="radio" aria-checked={theme === v} onClick={() => setTheme(v)}
                  className={cn("flex flex-col items-center gap-2 rounded-lg border p-4 text-sm font-medium hover:bg-muted/50", theme === v && "border-primary bg-accent text-accent-foreground")}>
                  <Icon className="size-5" />{label}</button>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Account</CardTitle><CardDescription>{user?.email} · member since {formatDate(user?.created_at, false)}</CardDescription></CardHeader>
          <CardContent>
            <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(e) => { e.preventDefault(); rename.mutate(); }}>
              <div className="flex-1 space-y-1.5"><Label htmlFor="name">Display name</Label><Input id="name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} /></div>
              <Button type="submit" loading={rename.isPending} disabled={!name.trim() || name === user?.name}>Save</Button>
            </form>
            {rename.isSuccess && <Alert variant="success" className="mt-3">Name updated.</Alert>}
            {rename.error && <Alert variant="critical" className="mt-3">{(rename.error as Error).message}</Alert>}
            <p className="mt-4 text-xs text-muted-foreground">Password reset by email is not available in this local build (no mail server is configured).</p>
          </CardContent>
        </Card>
        <Card className="border-critical/30">
          <CardHeader><CardTitle className="text-critical">Delete account</CardTitle>
            <CardDescription>Permanently removes your account, health profile, all conversations and your saved comparisons. Evaluation experiments you started stay
              (they contain no personal data) but are no longer linked to you. This cannot be undone.</CardDescription></CardHeader>
          <CardContent><Button variant="destructive" onClick={() => setOpen(true)}><Trash2 /> Delete my account</Button></CardContent>
        </Card>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent title="Delete your account permanently?" description="Type DELETE to confirm.">
          <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} aria-label="Type DELETE to confirm" autoComplete="off" />
          {remove.error && <Alert variant="critical" className="mt-3">{(remove.error as Error).message}</Alert>}
          <div className="mt-4 flex justify-end gap-2"><DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button variant="destructive" disabled={confirmText !== "DELETE"} loading={remove.isPending} onClick={() => remove.mutate()}>Delete account</Button></div>
        </DialogContent>
      </Dialog>
    </>
  );
}
