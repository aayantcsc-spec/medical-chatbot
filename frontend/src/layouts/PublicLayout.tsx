import { Suspense, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Logo, MedicalDisclaimer, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const LINKS = [{ to: "/#architectures", label: "Architectures" }, { to: "/architecture", label: "How it works" },
               { to: "/#methodology", label: "Methodology" }, { to: "/#safety", label: "Safety" }];

export function PublicLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link to="/" aria-label="MediChat home"><Logo /></Link>
          <nav aria-label="Primary" className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
            {LINKS.map((l) => l.to.startsWith("/#")
              ? <a key={l.to} href={l.to} className="hover:text-foreground">{l.label}</a>
              : <NavLink key={l.to} to={l.to} className={({ isActive }) => cn("hover:text-foreground", isActive && "text-foreground")}>{l.label}</NavLink>)}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            {user ? <Button asChild><Link to="/dashboard">Open dashboard</Link></Button> : <>
              <Button variant="ghost" asChild><Link to="/login">Sign in</Link></Button>
              <Button asChild><Link to="/register">Create account</Link></Button>
            </>}
          </div>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Menu">
            {open ? <X /> : <Menu />}
          </Button>
        </div>
        {open && (
          <div className="border-t bg-card md:hidden">
            <nav className="container flex flex-col gap-1 py-3" aria-label="Mobile">
              {LINKS.map((l) => <a key={l.to} href={l.to} onClick={() => setOpen(false)} className="rounded-md px-2 py-2 text-sm font-medium hover:bg-muted">{l.label}</a>)}
              <div className="mt-2 grid grid-cols-2 gap-2">
                {user ? <Button asChild className="col-span-2"><Link to="/dashboard">Open dashboard</Link></Button> : <>
                  <Button variant="outline" asChild><Link to="/login">Sign in</Link></Button>
                  <Button asChild><Link to="/register">Create account</Link></Button>
                </>}
              </div>
            </nav>
          </div>
        )}
      </header>
      <main className="flex-1">
        <Suspense fallback={<div className="py-24 text-center"><Spinner /></div>}><Outlet /></Suspense>
      </main>
      <footer className="border-t bg-card">
        <div className="container grid gap-8 py-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-sm text-sm text-muted-foreground">Comparative Analysis of Health Chatbots Based on Framework and Architecture.</p>
            <p className="max-w-sm text-sm text-muted-foreground">Thakur College of Science &amp; Commerce · Department of Artificial Intelligence and
              Machine Learning · Academic Year 2026–2027</p>
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold">Platform</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/architecture" className="hover:text-foreground">Architecture overview</Link></li>
              <li><Link to="/register" className="hover:text-foreground">Create an account</Link></li>
              <li><Link to="/login" className="hover:text-foreground">Sign in</Link></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold">Research</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="/#methodology" className="hover:text-foreground">Evaluation methodology</a></li>
              <li><a href="/#safety" className="hover:text-foreground">Medical safety</a></li>
              <li><a href="/#architectures" className="hover:text-foreground">Three architectures</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t">
          <div className="container py-5"><MedicalDisclaimer compact /></div>
        </div>
      </footer>
    </div>
  );
}

export function AuthShell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle: React.ReactNode }) {
  return (
    <div className="grid min-h-[calc(100dvh-4rem)] place-items-center bg-gradient-to-b from-accent/60 to-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="rounded-xl border bg-card p-6 shadow-card sm:p-8">{children}</div>
      </div>
    </div>
  );
}
