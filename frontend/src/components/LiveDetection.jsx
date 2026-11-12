import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { LANGUAGES } from "../i18n";

/**
 * Shows, while the user types, which symptoms the NLP pipeline has recognised (and which were
 * negated). The backend endpoint is stateless: nothing is stored or counted.
 */
export default function LiveDetection({ text, lang, age }) {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const trimmed = text.trim();

  useEffect(() => {
    if (trimmed.length < 3) { setData(null); return undefined; }
    const ctrl = { cancelled: false };
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        const res = await api.preview({ text: trimmed, lang: lang || null, display_lang: i18n.language,
          age_years: age === "" || age == null ? null : Number(age) });
        if (!ctrl.cancelled) setData(res);
      } catch {
        if (!ctrl.cancelled) setData(null);   // the preview is optional; the main check still works
      } finally {
        if (!ctrl.cancelled) setBusy(false);
      }
    }, 550);
    return () => { ctrl.cancelled = true; clearTimeout(timer); };
  }, [trimmed, lang, age, i18n.language]);

  if (trimmed.length < 3) return null;
  const langName = LANGUAGES.find((l) => l.code === data?.input_language)?.name;
  const empty = data && data.symptoms.length === 0 && data.denied.length === 0;

  return (
    <section className={`live ${busy ? "live-busy" : ""}`} aria-labelledby="live-title">
      <div className="live-head">
        <h2 id="live-title"><span className="live-dot" aria-hidden="true" /> {t("live.title")}</h2>
        {langName && <span className="live-lang">{langName}</span>}
        {busy && <span className="muted small">{t("live.detecting")}</span>}
      </div>
      {data?.emergency_sign && (
        <p className="live-emergency" role="alert">{t("live.emergency", { button: t("assess.submit") })}</p>
      )}
      <div aria-live="polite">
        {empty && <p className="muted small">{t("live.none")}</p>}
        {data && !empty && (
          <ul className="chips live-chips">
            {data.symptoms.map((s) => (
              <li key={s.id} className={`chip chip-static chip-found ${s.kind === "context" ? "chip-context" : ""}`}>
                <span aria-hidden="true">✓</span> {s.label}{s.uncertain ? " ?" : ""}
              </li>
            ))}
            {data.denied.map((s) => (
              <li key={s.id} className="chip chip-static chip-denied">
                <span aria-hidden="true">✕</span> <s>{s.label}</s> <span className="sr-only">({t("live.notPresent")})</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="hint">{t("live.hint")}</p>
    </section>
  );
}
