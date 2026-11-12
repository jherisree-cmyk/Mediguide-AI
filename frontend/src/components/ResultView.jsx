import { useTranslation } from "react-i18next";
import CareActions, { symptomDetails } from "./CareActions";
import EmergencyBanner from "./EmergencyBanner";
import UrgencyBadge from "./UrgencyBadge";

function SymptomDetails({ s }) {
  const { t } = useTranslation();
  const parts = symptomDetails(t, s);
  return parts.length ? <span className="muted"> ({parts.join(", ")})</span> : null;
}

/** Full assessment result. The text comes from the backend's reviewed templates in `result.display_language`. */
export default function ResultView({ result, description }) {
  const { t } = useTranslation();
  const emergency = result.level === "EMERGENCY";
  const shown = result.symptoms.filter((s) => s.kind !== "context" || s.id === "pregnant");

  return (
    <article className="result" aria-live="polite">
      {emergency && <EmergencyBanner nextStep={result.next_step} />}
      <UrgencyBadge level={result.level} text={result.level_text} large />
      {!emergency && <p className="next-step"><strong>{result.next_step}</strong></p>}
      <CareActions result={result} description={description} />
      {result.notes?.map((n) => <p key={n} className="note">{n}</p>)}
      {result.support && <p className="support">{result.support}</p>}

      {result.safety_net?.items?.length > 0 && (
        <section className="safety-net" aria-labelledby="sn-title">
          <h2 id="sn-title">{result.safety_net.title}</h2>
          <ul>{result.safety_net.items.map((i) => <li key={i}>{i}</li>)}</ul>
        </section>
      )}

      {shown.length > 0 && (
        <section>
          <h2>{t("result.symptoms")}</h2>
          <ul className="symptom-list">
            {shown.map((s) => <li key={s.id}>{s.label}<SymptomDetails s={s} /></li>)}
          </ul>
        </section>
      )}
      {result.denied?.length > 0 && (
        <section>
          <h2>{t("result.denied")}</h2>
          <p>{result.denied.join(", ")}</p>
        </section>
      )}
      {result.corrections?.length > 0 && (
        <p className="muted">{t("result.corrected")}: {result.corrections.map(([a, b]) => `"${a}" → "${b}"`).join(", ")}</p>
      )}

      {result.warnings?.length > 0 && (
        <section>
          <h2>{t("result.warnings")}</h2>
          {result.warnings.map((w) => (
            <details key={w.rule} className={`warning warning-${w.level.toLowerCase()}`} open={w.level === "EMERGENCY"}>
              <summary><span className="tag">{t(`level.${w.level}`)}</span> {w.title}</summary>
              {w.because_of?.length > 0 && <p>{t("result.because")}: {w.because_of.join(", ")}</p>}
              <p className="quote"><span className="muted">{t("result.quote")} (English): </span>“{w.guidance_quote_en}”</p>
              <p className="muted">
                {t("result.source")}:{" "}
                {w.sources.map((s, i) => (
                  <span key={s.url}>{i > 0 && " · "}<a href={s.url} target="_blank" rel="noreferrer">{s.publisher}: {s.title}</a></span>
                ))}
              </p>
            </details>
          ))}
        </section>
      )}

      {result.model_path?.length > 0 && (
        <section>
          <h2>{t("result.modelPath")}</h2>
          <ol className="model-path">{result.model_path.map((p, i) => <li key={i}>{p}</li>)}</ol>
          <p className="muted small">{t("result.modelHint")}</p>
        </section>
      )}

      {result.self_care_info && <p className="self-care">{result.self_care_info}</p>}

      <footer className="result-footer">
        <p><strong>{t("result.notDiagnosis")}</strong> {result.disclaimer}</p>
        <p className="muted small">{result.prototype_notice}</p>
      </footer>
    </article>
  );
}
