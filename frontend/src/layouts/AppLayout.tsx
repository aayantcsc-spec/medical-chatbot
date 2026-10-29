import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronRight, ChevronsLeft, ChevronsRight, LogOut, Menu, Moon, Settings, Sun, UserRound } from "lucide-react";
import { Logo, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
         DropdownMenuTrigger, Sheet, Tooltip } from "@/components/ui/overlays";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";
import { EXTRA_TITLES, NAV } from "./nav";

const COLLAPSE_KEY = "healthbot-sidebar-collapsed";

function initials(name?: string) {
  return (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";
}

function SidebarNav({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2 scrollbar-thin">
      {NAV.map(({ to, label, icon: Icon }) => {
        const link = (
          <NavLink key={to} to={to} onClick={onNavigate}
            className={({ isActive }) => cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive ? "bg-accent text-accent-foreground" : "text-sidebar-muted hover:bg-muted hover:text-sidebar-foreground",
              collapsed && "justify-center px-2",
            )}>
            {({ isActive }) => (
              <>
                <Icon className={cn("size-[18px] shrink-0", isActive ? "text-primary" : "")} aria-hidden />
                {!collapsed && <span className="truncate">{label}</span>}
                {collapsed && <span className="sr-only">{label}</span>}
              </>
            )}
          </NavLink>
        );
        return collapsed ? <Tooltip key={to} content={label} side="right">{link}</Tooltip> : link;
      })}
    </nav>
  );
}

function UserFooter({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="border-t p-3">
      <DropdownMenu>
        <DropdownMenuTrigger className={cn("flex w-full items-center gap-3 rounded-lg p-2 text-left hover:bg-muted", collapsed && "justify-center")}>
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{initials(user?.name)}</span>
          {!collapsed && (
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-sidebar-foreground">{user?.name}</span>
              <span className="block truncate text-xs text-sidebar-muted">{user?.email}</span>
            </span>
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Signed in as {user?.email}</DropdownMenuLabel>
          <DropdownMenuItem onSelect={() => { onNavigate?.(); navigate("/profile"); }}><UserRound /> Health profile</DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { onNavigate?.(); navigate("/settings"); }}><Settings /> Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={async () => { await logout(); navigate("/login"); }} className="text-critical"><LogOut /> Log out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

export function AppLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(COLLAPSE_KEY) === "1"; } catch { return false; }
  });
  useEffect(() => { try { localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0"); } catch { /* not remembered */ } }, [collapsed]);
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  const current = NAV.find((n) => location.pathname === n.to || location.pathname.startsWith(n.to + "/"));
  const title = current?.label ?? EXTRA_TITLES[location.pathname] ?? "MediChat";
  const dark = theme === "dark" || (theme === "system" && !!window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  return (
    <div className="flex min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:shadow-lift">Skip to content</a>

      {/* desktop sidebar */}
      <aside className={cn("sticky top-0 hidden h-dvh shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex",
                           collapsed ? "w-[72px]" : "w-64")}>
        <div className={cn("flex h-16 items-center px-5", collapsed && "justify-center px-0")}>
          <Link to="/dashboard" aria-label="MediChat home"><Logo compact={collapsed} inverted /></Link>
        </div>
        <SidebarNav collapsed={collapsed} />
        <button onClick={() => setCollapsed((c) => !c)}
          className="mx-3 mb-1 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-sidebar-muted hover:bg-muted hover:text-sidebar-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronsRight className="mx-auto size-4" /> : <><ChevronsLeft className="size-4" /> Collapse</>}
        </button>
        <UserFooter collapsed={collapsed} />
      </aside>

      {/* mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen} title="Navigation">
        <div className="flex h-16 items-center px-5"><Logo inverted /></div>
        <SidebarNav collapsed={false} onNavigate={() => setMobileOpen(false)} />
        <UserFooter collapsed={false} onNavigate={() => setMobileOpen(false)} />
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur sm:px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu />
          </Button>
          <nav aria-label="Breadcrumb" className="min-w-0 flex-1">
            <ol className="flex items-center gap-1.5 text-sm">
              <li className="hidden text-muted-foreground sm:block"><Link to="/dashboard" className="hover:text-foreground">MediChat</Link></li>
              <li className="hidden sm:block" aria-hidden><ChevronRight className="size-3.5 text-muted-foreground" /></li>
              <li className="truncate font-medium" aria-current="page">{title}</li>
            </ol>
          </nav>
          <Button variant="ghost" size="icon" aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
                  onClick={() => setTheme(dark ? "light" : "dark")} title={`Theme: ${theme}`}>
            {dark ? <Sun /> : <Moon />}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger aria-label="Account menu"
              className="grid size-9 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground focus-visible:ring-2 focus-visible:ring-ring">
              {initials(user?.name)}
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>{user?.name}</DropdownMenuLabel>
              <DropdownMenuItem onSelect={() => navigate("/profile")}><UserRound /> Health profile</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate("/settings")}><Settings /> Settings</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={async () => { await logout(); navigate("/login"); }} className="text-critical"><LogOut /> Log out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Suspense fallback={<div className="py-20 text-center"><Spinner label="Loading page" /></div>}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
