import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const get = vi.fn();
const post = vi.fn();
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { get: (...a: unknown[]) => get(...a), post: (...a: unknown[]) => post(...a), page: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), href: (u: string) => u } };
});

import { Markdown } from "@/lib/markdown";
import { ErrorState } from "@/components/common";
import { ApiError } from "@/lib/api";
import App from "@/App";
import { AuthProvider } from "@/hooks/useAuth";
import { TooltipProvider } from "@/components/ui/overlays";
import DashboardPage from "@/pages/DashboardPage";
import ComparisonPage from "@/features/comparison/ComparisonPage";

function wrap(ui: ReactNode, path = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}><TooltipProvider>{ui}</TooltipProvider></MemoryRouter></QueryClientProvider>,
  );
}

const ME = { id: 1, name: "Asha Rao", email: "a@example.com", onboarded: true, has_profile: true };

beforeEach(() => { get.mockReset(); post.mockReset(); });

describe("Markdown", () => {
  it("never renders HTML from a reply", () => {
    const { container } = render(<Markdown text={"### Title\n- **bold** item\n<img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("<img src=x onerror=alert(1)>");
    expect(screen.getByText("bold").tagName).toBe("STRONG");
  });
});

describe("ErrorState", () => {
  it("shows the message and retries", async () => {
    const retry = vi.fn();
    render(<ErrorState error={new ApiError("Server unavailable", "X", 503)} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Server unavailable");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalled();
  });
});

describe("Route protection", () => {
  it("redirects signed-out users to sign in", async () => {
    get.mockImplementation((url: string) => (url === "/auth/me" ? Promise.resolve({ user: null, csrf_token: "t" }) : Promise.reject(new Error("unexpected"))));
    wrap(<AuthProvider><App /></AuthProvider>, "/dashboard");
    expect(await screen.findByRole("heading", { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it("sends users who have not onboarded to onboarding", async () => {
    get.mockImplementation((url: string) => {
      if (url === "/auth/me") return Promise.resolve({ user: { ...ME, onboarded: false }, csrf_token: "t" });
      if (url === "/profile") return Promise.resolve({ profile: null, purpose: "Optional.", choices: { age_range: ["18-29"], smoking: ["never"], activity_level: ["low"] } });
      return Promise.reject(new Error(url));
    });
    wrap(<AuthProvider><App /></AuthProvider>, "/chat");
    expect(await screen.findByText(/welcome to medichat/i)).toBeInTheDocument();
  });
});

describe("Login form", () => {
  it("submits the typed password (regression: PasswordInput must forward its ref)", async () => {
    get.mockImplementation((url: string) => (url === "/auth/me" ? Promise.resolve({ user: null, csrf_token: "t" }) : Promise.reject(new Error(url))));
    post.mockResolvedValue({ user: ME, csrf_token: "t2" });
    wrap(<AuthProvider><App /></AuthProvider>, "/login");
    await userEvent.type(await screen.findByLabelText(/^email$/i), "demo@healthbot.local");
    await userEvent.type(screen.getByLabelText(/^password$/i), "Demo1234");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/auth/login", { email: "demo@healthbot.local", password: "Demo1234" }));
    expect(screen.queryByText("Required")).toBeNull();
  });
});

const EMPTY_BOT = (key: string, name: string) => ({ key, name,
  correctness: { held_out_accuracy: null, held_out_macro_f1: null, declined: null, multilingual_accuracy: null, question_bank_accuracy: null },
  response_time: { median_ms: null, mean_ms: null, p95_ms: null }, reliability: { answered_without_error: null, failed: null, questions: null },
  safety: { emergency_guidance_rate: null, off_topic_declined_rate: null, false_alarms: null }, quality: { keyword_coverage: null, n: null, label: "" } });

describe("Home", () => {
  it("shows the three approaches and no invented numbers before any evaluation", async () => {
    get.mockImplementation((url: string) => {
      if (url === "/auth/me") return Promise.resolve({ user: ME, csrf_token: "t" });
      if (url === "/analytics/summary") return Promise.resolve({
        activity: { conversations: 0, messages: 0, comparisons: 0, recent_conversations: [] },
        experiments: { total: 0, completed: 0, latest: null },
        overview: { chatbots: [EMPTY_BOT("rule", "Rule-Based"), EMPTY_BOT("ml", "SVM"), EMPTY_BOT("dl", "DistilBERT")],
                    overall: { status: "insufficient", winner: null, reason: "none", method: "", fastest: null }, leaders: {},
                    runs: { held_out_test: null, multilingual: null, safety: null, question_bank: null }, safety_detection: null, evaluation_required: true } });
      return Promise.reject(new Error(url));
    });
    wrap(<AuthProvider><DashboardPage /></AuthProvider>);
    expect(await screen.findByText(/no evaluation results yet/i)).toBeInTheDocument();
    expect(screen.getByText("TF-IDF + SVM")).toBeInTheDocument();
    expect(screen.getByText("DistilBERT")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.getByRole("link", { name: /ask a health question/i })).toHaveAttribute("href", "/chat");
  });

  it("shows an error with retry when the API fails", async () => {
    get.mockImplementation((url: string) => url === "/auth/me" ? Promise.resolve({ user: ME, csrf_token: "t" })
      : Promise.reject(new ApiError("Cannot reach the MediChat server.", "NETWORK_ERROR", 0)));
    wrap(<AuthProvider><DashboardPage /></AuthProvider>);
    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach/i);
  });
});

describe("Comparison", () => {
  const res = (key: string, extra = {}) => ({ key, name: key, status: "ok", response: `Reply from ${key}`, intent: "fever", intent_title: "Fever",
    confidence: 0.8, confidence_kind: "score", inference_ms: 3.2, error: null, architecture: "x", safety_override: false, category: null, language: null, top_k: [], ...extra });

  it("sends the same question to all three, shows loading, results, errors and 'No Clear Winner'", async () => {
    get.mockResolvedValue({ bots: [], examples: [], topic_count: 91 });
    let resolve!: (v: unknown) => void;
    post.mockReturnValue(new Promise((r) => { resolve = r; }));
    wrap(<ComparisonPage />);
    await userEvent.type(screen.getByLabelText(/your question/i), "What can cause fever and headache?");
    await userEvent.click(screen.getByRole("button", { name: /compare responses/i }));
    expect(post).toHaveBeenCalledWith("/comparison/ask", { question: "What can cause fever and headache?" });
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    resolve({ question: "What can cause fever and headache?", language: { lang: "en" }, canonical_text: "", notes: [], disclaimer: "",
      safety: { emergency: false, mode: null, categories: [], notice: null },
      results: { rule: res("rule"), ml: res("ml"), dl: res("dl", { status: "unavailable", error: "DistilBERT checkpoint not found", response: "" }) },
      overall_selection: { status: "tie", headline: "No Clear Winner", reason: "Scores within 2 points.", winner_key: null, winner_name: null, tied_keys: ["rule", "ml"],
        fastest_name: null, scores: {}, excluded: [], method: { weights: { safety: 0.3 }, scope: "", limits: "", language_scope: "", ground_truth: { available: false, note: "n/a" } } } });
    expect(await screen.findByRole("heading", { name: "No Clear Winner" })).toBeInTheDocument();
    expect(screen.getByText("Reply from rule")).toBeInTheDocument();
    expect(screen.getByText("DistilBERT checkpoint not found")).toBeInTheDocument();
  });

  it("shows the urgent banner for an emergency", async () => {
    get.mockResolvedValue({ bots: [], examples: [], topic_count: 91 });
    post.mockResolvedValue({ question: "chest pain", language: { lang: "en" }, canonical_text: "", notes: [], disclaimer: "",
      safety: { emergency: true, mode: "emergency", categories: ["chest pain"], notice: "Call 112" },
      results: { rule: res("rule", { safety_override: true }) },
      overall_selection: { status: "undetermined", headline: "No Clear Winner", reason: "x", winner_key: null, winner_name: null, tied_keys: [],
        fastest_name: null, scores: {}, excluded: [], method: { weights: {}, scope: "", limits: "", language_scope: "", ground_truth: { available: false } } } });
    wrap(<ComparisonPage />);
    await userEvent.type(screen.getByLabelText(/your question/i), "I have chest pain and difficulty breathing.");
    await userEvent.click(screen.getByRole("button", { name: /compare responses/i }));
    expect(await screen.findByText(/urgent response - this may be a medical emergency/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/112/).length).toBeGreaterThan(0));
  });
});

describe("Chat (consultation layout)", () => {
  it("shows the patient's question and MediChat's answer as a conversation", async () => {
    get.mockImplementation((url: string) => {
      if (url === "/auth/me") return Promise.resolve({ user: ME, csrf_token: "t" });
      if (url === "/chat/options") return Promise.resolve({ bots: [{ key: "rule", name: "Rule-Based", architecture: "rules", available: true, error: null, version: "v2" }],
                                                            examples: ["What is a balanced diet?"], notice: "General information only." });
      return Promise.reject(new Error(url));
    });
    post.mockResolvedValue({ conversation_id: null, saved: false, reply: "A balanced diet includes vegetables and fruit.\n\n_General health information · Not a diagnosis_",
      handled_by: "rule", bot: "rule", safety_status: "passed", response_time_ms: 12.5, language: "en", state: {}, details: {} });
    const { default: ChatPage } = await import("@/features/chat/ChatPage");
    wrap(<AuthProvider><ChatPage /></AuthProvider>, "/chat");
    await userEvent.click(await screen.findByRole("button", { name: "What is a balanced diet?" }));
    expect(post).toHaveBeenCalledWith("/chat", { message: "What is a balanced diet?", bot: "rule", conversation_id: null });
    expect(await screen.findByRole("article", { name: "You" })).toHaveTextContent("What is a balanced diet?");
    expect(await screen.findByText("MediChat · Rule-Based")).toBeInTheDocument();
    expect(screen.getByText(/a balanced diet includes vegetables/i)).toBeInTheDocument();
  });
});

describe("Chat (consultation layout)", () => {
  it("opens with a greeting and keeps the conversation oldest first", async () => {
    get.mockImplementation((url: string) => url === "/chat/options"
      ? Promise.resolve({ bots: [{ key: "rule", name: "Rule-Based", architecture: "rules", available: true, error: null, version: "v" }], examples: ["What is a balanced diet?"], notice: "General info." })
      : Promise.reject(new Error(url)));
    post.mockImplementation((_u: string, body: { message: string }) => Promise.resolve({ conversation_id: null, saved: false, reply: `Answer to: ${body.message}`,
      handled_by: "rule", bot: "rule", safety_status: "passed", response_time_ms: 12, language: "en", state: {}, details: {} }));
    const ChatPage = (await import("@/features/chat/ChatPage")).default;
    wrap(<ChatPage />, "/chat");
    const box = await screen.findByLabelText(/your health question/i);
    await userEvent.type(box, "First question{Enter}");
    await screen.findByText("Answer to: First question");
    await userEvent.type(box, "Second question{Enter}");
    await screen.findByText("Answer to: Second question");
    expect(screen.getByText(/what brings you in today/i)).toBeInTheDocument();
    const asked = screen.getAllByRole("article", { name: "You" }).map((a) => a.querySelector("p:nth-of-type(2)")?.textContent);
    expect(asked).toEqual(["First question", "Second question"]);
    expect(screen.getAllByText(/MediChat · Rule-Based/).length).toBe(2);
  });
});
