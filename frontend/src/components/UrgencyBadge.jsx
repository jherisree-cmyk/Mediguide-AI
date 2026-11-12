import { useTranslation } from "react-i18next";

// Urgency is ALWAYS shown as icon + text + colour (never colour alone), so it is readable
// for colour-blind users, on monochrome printouts and by screen readers.
const ICONS = {
  EMERGENCY: (
    <path d="M12 3 2 21h20L12 3Zm0 6v5m0 3.2v.1" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  ),
  URGENT: (
    <g fill="none" strokeWidth="2.2" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </g>
  ),
  ROUTINE: (
    <g fill="none" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M3.5 10h17M8 3v4m8-4v4m-7 9 2 2 4-4" />
    </g>
  ),
};

export default function UrgencyBadge({ level, text, large = false }) {
  const { t } = useTranslation();
  if (!level) return null;
  return (
    <div className={`badge badge-${level.toLowerCase()} ${large ? "badge-large" : ""}`} role="status">
      <svg className="badge-icon" viewBox="0 0 24 24" aria-hidden="true" stroke="currentColor">
        {ICONS[level]}
      </svg>
      <span>
        <strong className="badge-level">{t(`level.${level}`)}</strong>
        {text && <span className="badge-text">{text}</span>}
      </span>
    </div>
  );
}
