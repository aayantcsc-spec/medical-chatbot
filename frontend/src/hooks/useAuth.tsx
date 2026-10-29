import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, setCsrfToken } from "@/lib/api";
import type { User } from "@/types/api";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<unknown>;
}
const Ctx = createContext<AuthCtx | null>(null);

type AuthPayload = { user: User | null; csrf_token: string };

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const d = await api.get<AuthPayload>("/auth/me");
      setCsrfToken(d.csrf_token);
      return d.user;
    },
    staleTime: 60_000,
    retry: 1,
  });

  const onAuth = (d: AuthPayload) => {
    setCsrfToken(d.csrf_token);
    qc.clear();
    qc.setQueryData(["me"], d.user);
    return d.user as User;
  };
  const loginM = useMutation({ mutationFn: (v: { email: string; password: string }) => api.post<AuthPayload>("/auth/login", v) });
  const registerM = useMutation({ mutationFn: (v: { name: string; email: string; password: string }) => api.post<AuthPayload>("/auth/register", v) });

  const value = useMemo<AuthCtx>(() => ({
    user: me.data ?? null,
    loading: me.isLoading,
    login: async (email, password) => onAuth(await loginM.mutateAsync({ email, password })),
    register: async (name, email, password) => onAuth(await registerM.mutateAsync({ name, email, password })),
    logout: async () => {
      const d = await api.post<{ csrf_token: string }>("/auth/logout");
      setCsrfToken(d.csrf_token);
      qc.clear();
      qc.setQueryData(["me"], null);
    },
    refresh: () => me.refetch(),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [me.data, me.isLoading]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside <AuthProvider>");
  return c;
}
