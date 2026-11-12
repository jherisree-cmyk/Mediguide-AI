import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/assess");
    } catch (err) {
      setError(err.message || t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <h1>{t("auth.loginTitle")}</h1>
      <form onSubmit={submit} className="form">
        <label>{t("auth.email")}<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{t("auth.password")}<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>{t("auth.login")}</button>
      </form>
      <p><Link to="/register">{t("auth.noAccount")}</Link></p>
      <p className="muted">{t("auth.why")}</p>
    </div>
  );
}
