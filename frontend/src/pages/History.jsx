import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api";
import UrgencyBadge from "../components/UrgencyBadge";

export default function History() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  const load = () => api.history().then(setItems).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    if (!window.confirm(t("history.confirmDelete"))) return;
    await api.deleteHistoryItem(id);
    load();
  };
  const removeAll = async () => {
    if (!window.confirm(t("history.confirmDeleteAll"))) return;
    await api.deleteHistory();
    load();
  };

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!items) return <p>{t("common.loading")}</p>;
  return (
    <div className="narrow">
      <h1>{t("history.title")}</h1>
      {items.length === 0 ? <p>{t("history.empty")}</p> : (
        <>
          <ul className="history-list">
            {items.map((it) => (
              <li key={it.id} className="card history-item">
                <div className="history-head">
                  <UrgencyBadge level={it.level} />
                  <time dateTime={it.created_at}>{new Date(it.created_at).toLocaleString(i18n.language)}</time>
                </div>
                <p className="history-text">“{it.text}”</p>
                {it.symptoms.length > 0 && <p className="muted">{it.symptoms.join(", ")}</p>}
                <div className="actions">
                  <Link className="btn" to={`/history/${it.id}`}>{t("history.view")}</Link>
                  <button type="button" className="btn btn-danger-outline" onClick={() => remove(it.id)}>{t("history.delete")}</button>
                </div>
              </li>
            ))}
          </ul>
          <button type="button" className="btn btn-danger" onClick={removeAll}>{t("history.deleteAll")}</button>
        </>
      )}
    </div>
  );
}
