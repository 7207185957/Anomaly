import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { IncidentsPage } from "./pages/IncidentsPage";
import { AlertsPage } from "./pages/AlertsPage";
import { RcaPage } from "./pages/RcaPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/incidents" replace />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/rca" element={<RcaPage />} />
        <Route path="*" element={<Navigate to="/incidents" replace />} />
      </Routes>
    </AppShell>
  );
}

