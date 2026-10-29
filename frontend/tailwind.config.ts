import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const token = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1280px" } },
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        background: token("background"),
        foreground: token("foreground"),
        card: { DEFAULT: token("card"), foreground: token("card-foreground") },
        muted: { DEFAULT: token("muted"), foreground: token("muted-foreground") },
        border: token("border"),
        input: token("input"),
        ring: token("ring"),
        primary: { DEFAULT: token("primary"), foreground: token("primary-foreground") },
        secondary: { DEFAULT: token("secondary"), foreground: token("secondary-foreground") },
        accent: { DEFAULT: token("accent"), foreground: token("accent-foreground") },
        success: { DEFAULT: token("success"), soft: token("success-soft") },
        warning: { DEFAULT: token("warning"), soft: token("warning-soft") },
        critical: { DEFAULT: token("critical"), soft: token("critical-soft") },
        sidebar: { DEFAULT: token("sidebar"), foreground: token("sidebar-foreground"), muted: token("sidebar-muted") },
        chart: { 1: token("chart-1"), 2: token("chart-2"), 3: token("chart-3"), 4: token("chart-4"), 5: token("chart-5"), 6: token("chart-6") },
      },
      borderRadius: { lg: "0.75rem", md: "0.5rem", sm: "0.375rem", xl: "1rem" },
      boxShadow: {
        card: "0 1px 2px 0 rgb(17 34 68 / 0.06), 0 1px 3px 0 rgb(17 34 68 / 0.08)",
        lift: "0 6px 20px -6px rgb(17 34 68 / 0.18)",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
