import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LANGUAGES } from "../i18n";
import { useTheme } from "../theme";
import MedicalBackground from "./MedicalBackground";

export default function Layout() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const mainRef = useRef(null);
  const { theme, toggle } = useTheme();

  // Move keyboard/screen-reader focus to the new page content when the path CHANGES, but not
  // on first load, so the first Tab still reaches the skip link (found by the browser test).
  // Comparing paths (not a "first run" flag) also survives React StrictMode's double effects.
  const lastPath = useRef(location.pathname);
  useEffect(() => {
    if (lastPath.current === location.pathname) return;
    lastPath.current = location.pathname;
    mainRef.current?.focus();
  }, [location.pathname]);

  const doLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <>
      <MedicalBackground theme={theme} />
      <a href="#main" className="skip-link">{t("nav.skip")}</a>
      <header className="site-header">
        <Link to="/" className="brand" aria-label={t("app.name")}>
          <span className="brand-mark" aria-hidden="true">+</span> {t("app.name")}
        </Link>
        <nav aria-label="Main">
          <NavLink to="/assess">{t("nav.assess")}</NavLink>
          {user && <NavLink to="/history">{t("nav.history")}</NavLink>}
          {user && <NavLink to="/profile">{t("nav.profile")}</NavLink>}
          {user?.is_admin && <NavLink to="/admin">{t("nav.admin")}</NavLink>}
          {user ? (
            <button type="button" className="link-button" onClick={doLogout}>{t("nav.logout")}</button>
          ) : (
            <NavLink to="/login">{t("nav.login")}</NavLink>
          )}
        </nav>
        <button type="button" className="theme-toggle" onClick={toggle} aria-pressed={theme === "dark"}
                title={theme === "dark" ? t("nav.themeLight") : t("nav.themeDark")}>
          <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
          <span className="sr-only">{t("nav.themeDark")}</span>
        </button>
        <label className="lang-select">
          <span className="sr-only">{t("nav.language")}</span>
          <select value={i18n.language} onChange={(e) => i18n.changeLanguage(e.target.value)}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
        </label>
      </header>
      <div className="emergency-strip" role="note">{t("welcome.emergencyNow")}</div>
      <main id="main" ref={mainRef} tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <p>{t("welcome.doesNotTitle")}: {t("welcome.doesNot", { returnObjects: true }).join(" · ")}.</p>
        <p className="muted small">MediGuide AI · educational prototype · not clinically validated</p>
      </footer>
    </>
  );
}
