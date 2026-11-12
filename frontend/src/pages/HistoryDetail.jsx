import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import ResultView from "../components/ResultView";

export default function HistoryDetail() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.historyItem(id).then(setItem).catch((e) => setError(e.message)); }, [id]);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!item) return <p>{t("common.loading")}</p>;
  return (
    <div className="narrow">
      <p><Link to="/history">← {t("history.back")}</Link></p>
      <h1>{new Date(item.created_at).toLocaleString(i18n.language)}</h1>
      <p><strong>{t("history.description")}:</strong> “{item.text}”</p>
      <ResultView result={item.result} description={item.text} />
    </div>
  );
}
