import { useTranslation } from "react-i18next";

// Large, unmissable emergency call-to-action with tap-to-call links (work on phones).
export default function EmergencyBanner({ nextStep }) {
  const { t } = useTranslation();
  return (
    <section className="emergency-banner" aria-labelledby="emergency-title">
      <h2 id="emergency-title">{t("result.emergencyBanner")}</h2>
      <p>{nextStep}</p>
      <div className="call-buttons">
        <a className="btn btn-call" href="tel:112">{t("result.call112")}</a>
        <a className="btn btn-call" href="tel:108">{t("result.call108")}</a>
      </div>
    </section>
  );
}
