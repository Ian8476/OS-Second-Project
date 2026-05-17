import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "@/features/auth/LoginPage";
import { CasesPage } from "@/features/cases/CasesPage";
import { CaseDetailPage } from "@/features/cases/CaseDetailPage";
import { CreateCasePage } from "@/features/cases/CreateCasePage";
import { MonitoringPage } from "@/features/monitoring/MonitoringPage";
import { Layout } from "@/app/Layout";
import { useAuth } from "@/features/auth/AuthProvider";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/cases" replace />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/new" element={<CreateCasePage />} />
        <Route path="cases/:id" element={<CaseDetailPage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
      </Route>
    </Routes>
  );
}
