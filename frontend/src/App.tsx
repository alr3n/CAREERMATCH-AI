import { lazy, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/States";
import { useAuth } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { LandingPage } from "./pages/LandingPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const EvaluationPage = lazy(() => import("./pages/EvaluationPage").then((m) => ({ default: m.EvaluationPage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then((m) => ({ default: m.HistoryPage })));
const JobDetailPage = lazy(() => import("./pages/JobDetailPage").then((m) => ({ default: m.JobDetailPage })));
const JobsPage = lazy(() => import("./pages/JobsPage").then((m) => ({ default: m.JobsPage })));
const MatchDetailPage = lazy(() => import("./pages/MatchDetailPage").then((m) => ({ default: m.MatchDetailPage })));
const MatchesPage = lazy(() => import("./pages/MatchesPage").then((m) => ({ default: m.MatchesPage })));
const OverviewPage = lazy(() => import("./pages/OverviewPage").then((m) => ({ default: m.OverviewPage })));
const PreferencesPage = lazy(() => import("./pages/PreferencesPage").then((m) => ({ default: m.PreferencesPage })));
const ResumePage = lazy(() => import("./pages/ResumePage").then((m) => ({ default: m.ResumePage })));
const SavedPage = lazy(() => import("./pages/SavedPage").then((m) => ({ default: m.SavedPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage })));
const SkillsPage = lazy(() => import("./pages/SkillsPage").then((m) => ({ default: m.SkillsPage })));

function RequireAuth({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  const location = useLocation();
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (loading) return <LoadingState label="Loading your account…" />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="resume" element={<ResumePage />} />
        <Route path="preferences" element={<PreferencesPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="matches" element={<MatchesPage />} />
        <Route path="matches/:matchId" element={<MatchDetailPage />} />
        <Route path="skills" element={<SkillsPage />} />
        <Route path="saved" element={<SavedPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
