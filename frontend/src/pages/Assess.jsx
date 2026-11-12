import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAssessment } from "../context/AssessmentContext";
import { useAuth } from "../context/AuthContext";
import LiveDetection from "../components/LiveDetection";
import { VoiceInput } from "../components/Speech";
import { LANGUAGES } from "../i18n";

const EXAMPLES = {
  en: ["I have had a severe headache for two days and I feel dizzy", "Fever and cough since yesterday, no chest pain"],
  te: ["నాకు రెండు రోజులుగా జ్వరం, దగ్గు ఉన్నాయి", "కడుపు నొప్పి, వాంతులు అవుతున్నాయి"],
  hi: ["मुझे दो दिन से बुखार और खांसी है", "पेट में दर्द है और उल्टी हो रही है"],
};

export default function Assess() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { draft, setDraft, setCurrent } = useAssessment();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {  // pre-fill age from the profile once
    if (user?.age_years != null && draft.age === "") setDraft((d) => ({ ...d, age: String(user.age_years) }));
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k) => (e) => setDraft({ ...draft, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (draft.text.trim().length < 2) return setError(t("assess.tooShort"));
    setBusy(true);
    setError("");
    try {
      const res = await api.assess({
        text: draft.text.trim(),
        lang: draft.lang || null,
        display_lang: i18n.language,
        age_years: draft.age === "" ? null : Number(draft.age),
        save: Boolean(user && draft.save),
      });
      setCurrent(res);
      navigate(res.status === "needs_followup" ? "/assess/questions" : "/assess/result");
    } catch (err) {
      setError(err.message || t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <h1>{t("assess.title")}</h1>
      <form onSubmit={submit} className="form">
        <label htmlFor="symptoms">{t("assess.label")}</label>
        <textarea id="symptoms" rows={5} maxLength={2000} value={draft.text} onChange={set("text")}
                  placeholder={t("assess.placeholder")} lang={draft.lang || undefined} />
        <VoiceInput lang={draft.lang || i18n.language}
                    onText={(said) => setDraft((d) => ({ ...d, text: d.text.trim() ? `${d.text.trim()} ${said}` : said }))} />
        <LiveDetection text={draft.text} lang={draft.lang} age={draft.age} />
        <div className="examples">
          <span className="muted">{t("assess.examples")}:</span>
          {(EXAMPLES[i18n.language] || EXAMPLES.en).map((ex) => (
            <button type="button" key={ex} className="chip" onClick={() => setDraft({ ...draft, text: ex })}>{ex}</button>
          ))}
        </div>
        <div className="row">
          <label>{t("assess.inputLang")}
            <select value={draft.lang} onChange={set("lang")}>
              <option value="">{t("assess.auto")}</option>
              {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
          </label>
          <label>{t("assess.age")}
            <input type="number" min={0} max={120} step="any" inputMode="decimal" value={draft.age} onChange={set("age")} aria-describedby="age-hint" />
            <span id="age-hint" className="hint">{t("assess.ageHint")}</span>
          </label>
        </div>
        {user ? (
          <label className="option"><input type="checkbox" checked={draft.save} onChange={set("save")} /> {t("assess.save")}</label>
        ) : (
          <p className="muted"><Link to="/login">{t("assess.saveLogin")}</Link></p>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary btn-large" disabled={busy}>{busy ? t("assess.checking") : t("assess.submit")}</button>
      </form>
    </div>
  );
}
