import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { LANGUAGES } from "../i18n";

export default function LanguagePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="narrow">
      <h1>{t("lang.title")}</h1>
      <p>{t("lang.hint")}</p>
      <div className="lang-buttons lang-buttons-large">
        {LANGUAGES.map((l) => (
          <button key={l.code} type="button" lang={l.code} className="btn btn-lang"
                  onClick={() => { i18n.changeLanguage(l.code); navigate("/assess"); }}>{l.name}</button>
        ))}
      </div>
    </div>
  );
}
