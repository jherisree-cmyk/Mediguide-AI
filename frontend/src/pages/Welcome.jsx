import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { HeartbeatLine } from "../components/Animations";
import { LANGUAGES } from "../i18n";

export default function Welcome() {
  const { t, i18n } = useTranslation();
  return (
    <div className="welcome">
      <section className="hero">
        <p className="eyebrow">{t("app.tagline")}</p>
        <h1>{t("welcome.title")}</h1>
        <p className="lead">{t("welcome.intro")}</p>
        <div className="lang-buttons" role="group" aria-label={t("lang.title")}>
          {LANGUAGES.map((l) => (
            <button key={l.code} type="button" lang={l.code} aria-pressed={i18n.language === l.code}
                    className={`btn btn-lang ${i18n.language === l.code ? "active" : ""}`}
                    onClick={() => i18n.changeLanguage(l.code)}>{l.name}</button>
          ))}
        </div>
        <Link to="/assess" className="btn btn-primary btn-large">{t("welcome.start")}</Link>
        <p className="muted">{t("welcome.noAccount")}</p>
        <HeartbeatLine />
      </section>
      <section className="two-col">
        <div className="card">
          <h2>{t("welcome.doesTitle")}</h2>
          <ul className="check-list">{t("welcome.does", { returnObjects: true }).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
        <div className="card">
          <h2>{t("welcome.doesNotTitle")}</h2>
          <ul className="cross-list">{t("welcome.doesNot", { returnObjects: true }).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      </section>
    </div>
  );
}
