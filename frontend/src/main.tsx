import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { AuthProvider } from "@/hooks/useAuth";
import { TooltipProvider } from "@/components/ui/overlays";
import { applyTheme, type Theme } from "@/hooks/useTheme";
import { ApiError } from "@/lib/api";
import "./index.css";

try { applyTheme((localStorage.getItem("healthbot-theme") as Theme) || "system"); } catch { applyTheme("system"); }

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // never retry auth / validation / not-found errors; retry network blips once
      retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
