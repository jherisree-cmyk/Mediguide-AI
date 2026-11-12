import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { LANGUAGES } from "../i18n";

export default function Profile() {
  const { t, i18n } = useTranslation();
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    display_name: user.display_name || "", age_years: user.age_years ?? "", sex: user.sex || "", language: user.language,
  });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setMsg("");
    setError("");
    try {
      const updated = await api.updateProfile({
        display_name: form.display_name || null,
        age_years: form.age_years === "" ? null : Number(form.age_years),
        sex: form.sex || null,
        language: form.language,
      });
      setUser(updated);
      i18n.changeLanguage(updated.language);
      setMsg(t("profile.saved"));
    } catch (err) {
      setError(err.message);
    }
  };

  const deleteAccount = async () => {
    if (!window.confirm(t("profile.confirmDeleteAccount"))) return;
    await api.deleteAccount();
    setUser(null);
    navigate("/");
  };

  return (
    <div className="narrow">
      <h1>{t("profile.title")}</h1>
      <p className="muted">{user.email}</p>
      <p>{t("profile.why")}</p>
      <form onSubmit={save} className="form">
        <label>{t("profile.name")}<input maxLength={50} value={form.display_name} onChange={set("display_name")} /></label>
        <label>{t("profile.age")}<input type="number" min={0} max={120} step="any" value={form.age_years} onChange={set("age_years")} /></label>
        <fieldset className="question">
          <legend>{t("profile.sex")}</legend>
          <div className="options options-inline">
            {[["F", t("profile.female")], ["M", t("profile.male")], ["", t("profile.notSay")]].map(([v, label]) => (
              <label key={v || "none"} className="option">
                <input type="radio" name="sex" value={v} checked={form.sex === v} onChange={set("sex")} /> {label}
              </label>
            ))}
          </div>
        </fieldset>
        <label>{t("profile.language")}
          <select value={form.language} onChange={set("language")}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
        </label>
        {msg && <p className="success" role="status">{msg}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary">{t("profile.save")}</button>
      </form>
      <p className="muted small">{t("profile.privacy")}</p>
      <section className="danger-zone">
        <button type="button" className="btn btn-danger" onClick={deleteAccount}>{t("profile.danger")}</button>
      </section>
    </div>
  );
}
