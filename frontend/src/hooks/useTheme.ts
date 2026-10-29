import { useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";
const KEY = "healthbot-theme";

function read(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" || v === "system" ? v : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(theme: Theme) {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", !!dark);
}

/** Per-viewer preference only (stored in this browser). */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(read);
  useEffect(() => {
    applyTheme(theme);
    try { localStorage.setItem(KEY, theme); } catch { /* storage unavailable - preference just isn't remembered */ }
    if (theme !== "system" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => applyTheme("system");
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, [theme]);
  return { theme, setTheme };
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · MediChat` : "MediChat - Comparative Analysis of Health Chatbots";
  }, [title]);
}
