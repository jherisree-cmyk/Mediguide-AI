import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Admin from "./pages/Admin";
import Assess from "./pages/Assess";
import FollowUp from "./pages/FollowUp";
import History from "./pages/History";
import HistoryDetail from "./pages/HistoryDetail";
import LanguagePage from "./pages/LanguagePage";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import Result from "./pages/Result";
import Welcome from "./pages/Welcome";

function RequireAuth({ children, admin = false }) {
  const { user, ready } = useAuth();
  const { t } = useTranslation();
  if (!ready) return <p>{t("common.loading")}</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && !user.is_admin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Welcome />} />
        <Route path="language" element={<LanguagePage />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="assess" element={<Assess />} />
        <Route path="assess/questions" element={<FollowUp />} />
        <Route path="assess/result" element={<Result />} />
        <Route path="history" element={<RequireAuth><History /></RequireAuth>} />
        <Route path="history/:id" element={<RequireAuth><HistoryDetail /></RequireAuth>} />
        <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
        <Route path="admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
