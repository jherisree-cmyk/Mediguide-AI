import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) return setError(t("auth.passwordHint"));
    setBusy(true);
    setError("");
    try {
      await register(form.email, form.password, form.name);
      navigate("/profile");
    } catch (err) {
      setError(err.message || t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <h1>{t("auth.registerTitle")}</h1>
      <p className="muted">{t("auth.why")}</p>
      <form onSubmit={submit} className="form">
        <label>{t("auth.name")}<input autoComplete="name" maxLength={50} value={form.name} onChange={set("name")} /></label>
        <label>{t("auth.email")}<input type="email" autoComplete="email" required value={form.email} onChange={set("email")} /></label>
        <label>{t("auth.password")}
          <input type="password" autoComplete="new-password" minLength={8} required value={form.password} onChange={set("password")} aria-describedby="pw-hint" />
          <span id="pw-hint" className="hint">{t("auth.passwordHint")}</span>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>{t("auth.register")}</button>
      </form>
      <p><Link to="/login">{t("auth.haveAccount")}</Link></p>
    </div>
  );
}
