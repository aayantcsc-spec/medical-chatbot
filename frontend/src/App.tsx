import { lazy, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Spinner } from "@/components/common";
import { useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/layouts/AppLayout";
import { PublicLayout } from "@/layouts/PublicLayout";

// Public pages load eagerly (first paint); app pages are split into their own chunks.
import LandingPage from "@/pages/LandingPage";
import { LoginPage, RegisterPage, ForgotPasswordPage } from "@/pages/AuthPages";
const ArchitecturePage = lazy(() => import("@/pages/ArchitecturePage"));
const SharedConversationPage = lazy(() => import("@/pages/SharedConversationPage"));
const OnboardingPage = lazy(() => import("@/pages/OnboardingPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const ChatPage = lazy(() => import("@/features/chat/ChatPage"));
const ComparisonPage = lazy(() => import("@/features/comparison/ComparisonPage"));
const ModelEvaluationPage = lazy(() => import("@/features/evaluation/ModelEvaluationPage"));
const HistoryPage = lazy(() => import("@/features/history/HistoryPage"));
const ProfilePage = lazy(() => import("@/features/profile/ProfilePage"));
const UserStudyPage = lazy(() => import("@/features/study/UserStudyPage"));
const SettingsPage = lazy(() => import("@/features/settings/SettingsPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));

const FullScreenLoading = () => <div className="grid min-h-dvh place-items-center"><Spinner label="Loading MediChat" /></div>;

/** Signed-in users only; first-time users go through onboarding first. */
function RequireAuth({ children, allowUnonboarded = false }: { children: ReactNode; allowUnonboarded?: boolean }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (!user.onboarded && !allowUnonboarded) return <Navigate to="/onboarding" replace />;
  return <>{children}</>;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoading />;
  if (user) return <Navigate to={user.onboarded ? "/dashboard" : "/onboarding"} replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<LandingPage />} />
        <Route path="architecture" element={<ArchitecturePage />} />
        <Route path="login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="shared/:token" element={<SharedConversationPage />} />
        <Route path="onboarding" element={<RequireAuth allowUnonboarded><OnboardingPage /></RequireAuth>} />
      </Route>
      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="chat/:conversationId" element={<ChatPage />} />
        <Route path="comparison" element={<ComparisonPage />} />
        <Route path="model-evaluation" element={<ModelEvaluationPage />} />
        <Route path="user-study" element={<UserStudyPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
        {/* old URLs from the previous version */}
        <Route path="chatbot-comparison" element={<Navigate to="/comparison" replace />} />
        <Route path="health-qa-comparison" element={<Navigate to="/comparison" replace />} />
        <Route path="analysis" element={<Navigate to="/model-evaluation" replace />} />
        <Route path="experiments" element={<Navigate to="/model-evaluation" replace />} />
      </Route>
      <Route element={<PublicLayout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
