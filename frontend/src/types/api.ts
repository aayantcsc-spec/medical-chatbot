/* Types mirror the Flask /api/v1 responses. Optional fields are genuinely optional in the API. */

export interface User { id: number; name: string; email: string; created_at?: string; onboarded: boolean; has_profile: boolean }

export type SafetyStatus = "passed" | "rejected" | "emergency_override" | "not_applicable";
export type BotKey = "rule" | "ml" | "dl";

export interface BotInfo { key: BotKey; name: string; architecture: string | null; available: boolean; error: string | null; version: string | null }

export interface BotResult {
  key: BotKey; name: string; status: "ok" | "no_match" | "small_talk" | "unavailable" | "error"; response: string;
  intent: string | null; intent_title: string | null; confidence: number | null; confidence_kind: string; inference_ms: number | null;
  error: string | null; architecture: string | null; version?: string | null; safety_override: boolean; category: string | null;
  language: { lang: string } | null; top_k: [string, number][];
}
export interface BotScore {
  key: BotKey; name: string; eligible: boolean; excluded_reason: string | null; correctness: number | null; safety: number | null;
  safety_level: string | null; safety_notes: string[]; quality: number | null;
  quality_parts: { relevance: number; completeness: number; clarity: number } | null; quality_notes: string[];
  speed: number | null; inference_ms: number | null; overall: number | null; unavailable: string[];
}
export interface Comparison {
  question: string; language: { lang: string; script: string | null; confidence: number | null }; canonical_text: string;
  safety: { emergency: boolean; mode: string | null; categories: string[]; notice: string | null };
  results: Partial<Record<BotKey, BotResult>>;
  overall_selection: { status: "winner" | "tie" | "undetermined"; headline: string; reason: string; winner_key: BotKey | null;
                       winner_name: string | null; tied_keys: BotKey[]; fastest_name: string | null;
                       scores: Partial<Record<BotKey, BotScore>>; excluded: { key: string; name: string; reason: string }[];
                       method: { weights: Record<string, number>; scope: string; limits: string; language_scope: string;
                                 ground_truth: { available: boolean; note?: string; dataset?: string } } };
  notes: string[]; disclaimer: string; run_id?: string;
}

export interface ChatReply {
  conversation_id: number | null; saved: boolean; reply: string; handled_by: string; bot: BotKey;
  safety_status: SafetyStatus; response_time_ms: number; language: string; state: Record<string, unknown> | null;
  details: { status?: string; intent?: string | null; confidence?: number | null; confidence_kind?: string; inference_ms?: number | null };
}

export interface Conversation {
  id: number; title: string; pinned: boolean; shared: boolean; mode: string | null; architecture: string | null;
  created_at: string; updated_at: string; message_count?: number; last_message?: string | null;
}
export interface ChatMessage {
  id: string; role: "user" | "assistant"; content: string; created_at?: string; architecture?: string | null;
  handled_by?: string | null; safety_status?: SafetyStatus | null; response_time_ms?: number | null; pending?: boolean; error?: string;
}
export interface ConversationDetail extends Conversation { messages: ChatMessage[]; share_token?: string | null }

/* ----- evaluation ----- */
export interface RunSummary {
  run_id: string; status: string; dataset: string; dataset_title: string; dataset_kind: string; mode: string; created_at: string;
  finished_at: string | null; percent: number; progress: { completed: number; total: number; errors: number }; error: string | null;
  models: Record<string, number | null>; models_included: string[]; category: string | null;
}
export interface BotOverview {
  key: BotKey; name: string;
  correctness: { held_out_accuracy: number | null; held_out_macro_f1: number | null; declined: number | null;
                 multilingual_accuracy: number | null; question_bank_accuracy: number | null };
  response_time: { median_ms: number | null; mean_ms: number | null; p95_ms: number | null };
  reliability: { answered_without_error: number | null; failed: number | null; questions: number | null };
  safety: { emergency_guidance_rate: number | null; off_topic_declined_rate: number | null; false_alarms: number | null };
  quality: { keyword_coverage: number | null; n: number | null; label: string };
}
export interface RunRef { run_id: string; dataset: string; n: number; finished_at: string }
export interface Overview {
  chatbots: BotOverview[];
  overall: { status: "winner" | "none" | "insufficient"; winner: BotKey | null; reason: string; method: string; fastest: BotKey | null };
  leaders: Record<string, BotKey[]>;
  runs: Record<"held_out_test" | "multilingual" | "safety" | "question_bank", RunRef | null>;
  safety_detection: { precision: number; recall: number; f1: number; n: number } | null;
  evaluation_required: boolean;
}
export interface HistoryPoint { id: string; created_at: string; sample_size: number; architecture: string; accuracy: number | null;
  f1_score: number | null; median_response_time: number | null }

export interface Profile {
  age_range: string | null; height: string | null; weight: string | null; smoking: string | null; activity_level: string | null;
  health_goal: string | null; consent_at: string | null; updated_at: string | null; legacy_fields: Record<string, string>;
}
