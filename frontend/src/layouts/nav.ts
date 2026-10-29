import { ClipboardCheck, FlaskConical, GitCompareArrows, History, House, MessageSquareText, Settings, UserRound } from "lucide-react";

export const NAV = [
  { to: "/dashboard", label: "Home", icon: House },
  { to: "/chat", label: "Chat", icon: MessageSquareText },
  { to: "/comparison", label: "Comparison", icon: GitCompareArrows },
  { to: "/model-evaluation", label: "Model Evaluation", icon: FlaskConical },
  { to: "/user-study", label: "User Study", icon: ClipboardCheck },
  { to: "/history", label: "Chat History", icon: History },
  { to: "/profile", label: "Health Profile", icon: UserRound },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export const EXTRA_TITLES: Record<string, string> = { "/onboarding": "Welcome" };
