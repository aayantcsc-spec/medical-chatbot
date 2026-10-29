import axios, { AxiosError, type AxiosRequestConfig } from "axios";

/** Error thrown for every failed API call. `code` comes from the backend envelope. */
export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public field?: string,
  ) {
    super(message);
  }
}

export interface Envelope<T> {
  success: boolean;
  data: T;
  meta?: PageMeta;
  error?: { code: string; message: string; field?: string };
}
export interface PageMeta { page: number; per_page: number; total: number; pages: number }

const client = axios.create({ baseURL: "/api/v1", withCredentials: true, timeout: 60_000 });

let csrfToken: string | null = null;
export const setCsrfToken = (t: string | null | undefined) => { if (t) csrfToken = t; };

async function ensureCsrf() {
  if (!csrfToken) {
    const r = await client.get<Envelope<{ csrf_token: string }>>("/auth/csrf");
    csrfToken = r.data.data.csrf_token;
  }
  return csrfToken;
}

client.interceptors.request.use(async (config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (!["get", "head", "options"].includes(method)) {
    config.headers.set("X-CSRF-Token", await ensureCsrf());
  }
  return config;
});

function toApiError(e: unknown): ApiError {
  const err = e as AxiosError<Envelope<unknown>>;
  if (err.response) {
    const env = err.response.data;
    if (env && typeof env === "object" && env.error) {
      return new ApiError(env.error.message, env.error.code, err.response.status, env.error.field);
    }
    return new ApiError("The server returned an unexpected response.", "HTTP_ERROR", err.response.status);
  }
  if (err.code === "ECONNABORTED") return new ApiError("The request timed out. Please try again.", "TIMEOUT", 0);
  return new ApiError("Cannot reach the MediChat server. Is the backend running?", "NETWORK_ERROR", 0);
}

async function request<T>(config: AxiosRequestConfig, retryCsrf = true): Promise<Envelope<T>> {
  try {
    const r = await client.request<Envelope<T>>(config);
    return r.data;
  } catch (e) {
    const apiErr = toApiError(e);
    if (apiErr.code === "CSRF_FAILED" && retryCsrf) {
      csrfToken = null; // session rotated (login/logout in another tab) - fetch a fresh token once
      return request<T>(config, false);
    }
    throw apiErr;
  }
}

export const api = {
  get: async <T>(url: string, params?: Record<string, unknown>) => (await request<T>({ method: "get", url, params })).data,
  page: async <T>(url: string, params?: Record<string, unknown>) => {
    const env = await request<T>({ method: "get", url, params });
    return { data: env.data, meta: env.meta as PageMeta };
  },
  post: async <T>(url: string, body?: unknown) => (await request<T>({ method: "post", url, data: body ?? {} })).data,
  put: async <T>(url: string, body?: unknown) => (await request<T>({ method: "put", url, data: body ?? {} })).data,
  patch: async <T>(url: string, body?: unknown) => (await request<T>({ method: "patch", url, data: body ?? {} })).data,
  del: async <T>(url: string, body?: unknown) => (await request<T>({ method: "delete", url, data: body ?? {} })).data,
  /** URL for file downloads (CSV exports) - the browser sends the session cookie. */
  href: (url: string) => `/api/v1${url}`,
};
