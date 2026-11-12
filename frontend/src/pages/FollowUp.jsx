import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api";
import QuestionForm from "../components/QuestionForm";
import UrgencyBadge from "../components/UrgencyBadge";
import { useAssessment } from "../context/AssessmentContext";

export default function FollowUp() {
  const { t } = useTranslation();
  const { current, setCurrent } = useAssessment();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // A completed assessment belongs on the result page. (Bug found by a test: redirecting it to
  // /assess sent users back to the start right after they answered the questions.)
  if (current?.status === "complete") return <Navigate to="/assess/result" replace />;
  if (!current || current.status !== "needs_followup") return <Navigate to="/assess" replace />;
  const understood = current.symptoms.filter((s) => s.kind !== "context").map((s) => s.label);

  const submit = async (answers) => {
    setBusy(true);
    setError("");
    try {
      const res = await api.answer(current.id, answers, current.followup_token);
      setCurrent(res);
      navigate("/assess/result");
    } catch (err) {
      setError(err.status === 404 ? `${t("common.error")}: ${err.message}` : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <h1>{t("followup.title")}</h1>
      {current.preliminary_level && <UrgencyBadge level={current.preliminary_level} />}
      {/* Symptom confirmation: the user sees what we understood and can correct it */}
      <section className="understood" aria-labelledby="understood-title">
        <h2 id="understood-title">{t("followup.understood")}</h2>
        {understood.length ? (
          <ul className="chips">{understood.map((u) => <li key={u} className="chip chip-static">{u}</li>)}</ul>
        ) : (
          <p>{t("followup.nothingUnderstood")}</p>
        )}
        {current.denied?.length > 0 && <p className="muted">✕ {current.denied.join(", ")}</p>}
        <Link to="/assess">{t("followup.edit")}</Link>
      </section>
      <p>{t("followup.intro")}</p>
      {error && <p className="error" role="alert">{error} <Link to="/assess">{t("followup.edit")}</Link></p>}
      <QuestionForm questions={current.questions} lang={current.display_language} onSubmit={submit} busy={busy} />
    </div>
  );
}
