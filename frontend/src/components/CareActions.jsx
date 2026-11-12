import { useTranslation } from "react-i18next";
import { ReadAloud } from "./Speech";

/** Text such as "severe, 7/10, 2 days, started suddenly" for one symptom. */
export function symptomDetails(t, s) {
  const parts = [];
  if (s.severity) parts.push(t(`result.severity.${s.severity}`));
  if (s.pain_score !== null && s.pain_score !== undefined) parts.push(`${s.pain_score}/10`);
  if (s.duration_days) parts.push(s.duration_days < 1 ? t("result.day") : t("result.days", { count: Math.round(s.duration_days) }));
  if (s.onset) parts.push(t(`result.onset.${s.onset}`));
  if (s.uncertain) parts.push(t("result.uncertain"));
  return parts;
}

/** Plain-text summary a patient can show to a doctor (built in the browser; nothing is uploaded). */
export function buildSummary(t, result, description, date = new Date()) {
  const L = [];
  const line = (s = "") => L.push(s);
  line(t("summary.title"));
  line("=".repeat(48));
  line(`${t("summary.date")}: ${date.toLocaleString()}`);
  line(`${t("summary.urgency")}: ${t(`level.${result.level}`)} (${result.level_text})`);
  line(`${t("summary.nextStep")}: ${result.next_step}`);
  if (description) { line(); line(`${t("summary.description")}:`); line(`"${description}"`); }
  const shown = result.symptoms.filter((s) => s.kind !== "context" || s.id === "pregnant");
  if (shown.length) {
    line(); line(`${t("result.symptoms")}:`);
    shown.forEach((s) => { const d = symptomDetails(t, s); line(`  - ${s.label}${d.length ? ` (${d.join(", ")})` : ""}`); });
  }
  if (result.denied?.length) { line(); line(`${t("result.denied")}: ${result.denied.join(", ")}`); }
  if (result.warnings?.length) {
    line(); line(`${t("result.warnings")}:`);
    result.warnings.forEach((w) => {
      line(`  - [${t(`level.${w.level}`)}] ${w.title}`);
      if (w.sources?.length) line(`    ${t("result.source")}: ${w.sources.map((s) => `${s.publisher} (${s.url})`).join("; ")}`);
    });
  }
  if (result.model_path?.length) { line(); line(`${t("result.modelPath")}:`); result.model_path.forEach((p, i) => line(`  ${i + 1}. ${p}`)); }
  line(); line("-".repeat(48));
  line(t("summary.generated"));
  if (result.disclaimer) line(result.disclaimer);
  return L.join("\r\n");
}

const MAPS = { EMERGENCY: "emergency hospital near me", URGENT: "hospital near me", ROUTINE: "clinic near me" };

/** Read aloud, find care nearby, download a summary for the doctor. */
export default function CareActions({ result, description }) {
  const { t } = useTranslation();
  const lang = result.display_language || "en";
  const speech = [t(`level.${result.level}`), result.level_text, result.next_step,
    result.safety_net?.title, ...(result.safety_net?.items || [])].filter(Boolean).join(". ");
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(MAPS[result.level] || MAPS.URGENT)}`;

  const download = () => {
    // BOM so Windows Notepad shows Telugu/Hindi text correctly
    const blob = new Blob(["﻿", buildSummary(t, result, description)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mediguide-summary-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section className="care-actions no-print" aria-label={t("result.careActions")}>
      <ReadAloud lang={lang} text={speech} />
      <a className={`btn ${result.level === "ROUTINE" ? "" : "btn-care"}`} href={mapsUrl} target="_blank" rel="noreferrer">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
          <path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z" /><path d="M12 7v6M9 10h6" />
        </svg>
        {result.level === "ROUTINE" ? t("result.nearbyClinic") : t("result.nearby")}
        <span className="sr-only"> ({t("result.nearbyHint")})</span>
      </a>
      <button type="button" className="btn" onClick={download}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3v12M7 10l5 5 5-5M4 20h16" />
        </svg>
        {t("result.download")}
      </button>
    </section>
  );
}
