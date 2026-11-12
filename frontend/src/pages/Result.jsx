import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router-dom";
import ResultView from "../components/ResultView";
import { useAssessment } from "../context/AssessmentContext";

export default function Result() {
  const { t } = useTranslation();
  const { current, setCurrent, draft, setDraft } = useAssessment();
  const navigate = useNavigate();
  if (!current || current.status !== "complete") return <Navigate to="/assess" replace />;

  const restart = () => {
    setCurrent(null);
    setDraft((d) => ({ ...d, text: "", save: false }));
    navigate("/assess");
  };

  return (
    <div className="narrow">
      <h1>{t("result.title")}</h1>
      <ResultView result={current} description={draft.text.trim()} />
      <div className="actions no-print">
        <button type="button" className="btn btn-primary" onClick={restart}>{t("result.newAssessment")}</button>
        {current.saved && <Link className="btn" to="/history">{t("result.toHistory")}</Link>}
        <button type="button" className="btn" onClick={() => window.print()}>{t("result.printable")}</button>
      </div>
    </div>
  );
}
