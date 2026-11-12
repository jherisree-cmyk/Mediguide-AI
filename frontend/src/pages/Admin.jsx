import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { BarChart, LEVEL_COLORS, LineChart } from "../components/Charts";

const LEVEL_ORDER = ["EMERGENCY", "URGENT", "ROUTINE"];
const LANG_NAMES = { en: "English", te: "తెలుగు (Telugu)", hi: "हिंदी (Hindi)" };
const pct = (v) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "–");

function StatTile({ label, value, note }) {
  return (
    <div className="stat-tile card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {note && <span className="muted small">{note}</span>}
    </div>
  );
}

function ModelTable({ title, m }) {
  if (!m) return null;
  return (
    <div className="card">
      <h3>{title}</h3>
      <table className="metrics">
        <thead><tr><th scope="col">Class</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th><th scope="col">Visits</th></tr></thead>
        <tbody>
          {LEVEL_ORDER.map((c) => (
            <tr key={c}>
              <th scope="row">{c}</th>
              <td>{m.per_class[c].precision.toFixed(3)}</td>
              <td>{m.per_class[c].recall.toFixed(3)}</td>
              <td>{m.per_class[c]["f1-score"].toFixed(3)}</td>
              <td>{m.per_class[c].support}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="small">
        Macro-F1 {m.macro_f1.toFixed(3)} · accuracy {m.accuracy.toFixed(3)} ·
        nurse emergencies given ≥ Urgent {pct(m.emergency_to_at_least_urgent)} · under-triage {pct(m.under_triage_rate)}
      </p>
    </div>
  );
}

export default function Admin() {
  const { t } = useTranslation();
  const [s, setS] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.adminStats().then(setS).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!s) return <p>{t("common.loading")}</p>;

  const levels = LEVEL_ORDER.filter((l) => l in s.levels)
    .map((l) => ({ label: t(`level.${l}`), value: s.levels[l], color: LEVEL_COLORS[l] }));
  const langs = Object.entries(s.languages).map(([k, v]) => ({ label: LANG_NAMES[k] || k, value: v }));
  const symptoms = s.top_symptoms.map((x) => ({ label: x.label, value: x.count }));
  const daily = Object.entries(s.daily_last_30_days).map(([day, value]) => ({ day, value }));
  // "rule=URGENT / model=ROUTINE" -> "URGENT → ROUTINE" (rule level → model level)
  const ruleVsModel = Object.entries(s.rule_vs_model).map(([k, v]) => ({
    label: k.replace("rule=", "").replace(" / model=", " → "), value: v }));

  return (
    <div className="admin">
      <h1>{t("nav.admin")}: usage and model overview</h1>
      <p className="note">{s.privacy_note} No names, emails or symptom descriptions are available here.</p>

      <div className="stat-row">
        <StatTile label="Completed assessments" value={s.total_assessments} />
        <StatTile label="Needed follow-up questions" value={pct(s.followup_rate)} />
        <StatTile label="Model" value={s.model.version} note={`trained ${s.model.trained}`} />
        <StatTile label="Urgent threshold" value={s.model.thresholds.t_urgent_or_higher}
                  note={`emergency flag ≥ ${s.model.thresholds.t_emergency}`} />
      </div>

      <div className="chart-grid">
        <BarChart title="Urgency recommendations" data={levels} />
        <BarChart title="Input language" data={langs} />
        <BarChart title="Most reported symptoms (top 15)" data={symptoms} />
        <LineChart title="Assessments per day (last 30 days)" data={daily} />
        <BarChart title="Rule level → model level ('none' = no rule fired)" data={ruleVsModel} />
      </div>

      <h2>Model evaluation (NHAMCS 2022 test set, evaluated once)</h2>
      <p className="note"><strong>{s.model.status}.</strong> These are retrospective results against US emergency-department
        nurse triage. They are not evidence of clinical safety in real use.</p>
      <div className="chart-grid">
        <ModelTable title="App policy: rules + depth-6 Decision Tree (model capped at Urgent)" m={s.model.test_2022_app_policy} />
        <ModelTable title="Comparison: Random Forest (best model, not used by the app)" m={s.model.test_2022_random_forest} />
      </div>
    </div>
  );
}
