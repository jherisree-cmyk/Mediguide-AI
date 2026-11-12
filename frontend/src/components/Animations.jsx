// Decorative, health-themed animations. All are aria-hidden (no meaning for screen readers)
// and are switched off by CSS when the user's device asks for reduced motion.

/** A heartbeat (ECG) line that keeps drawing itself across the hero. */
export function HeartbeatLine() {
  const beat = "l20 0 l6 -10 l6 20 l8 -52 l8 74 l7 -38 l5 6 l20 0";
  const path = `M0 60 l40 0 ${beat} l60 0 ${beat} l60 0 ${beat} l60 0 ${beat} l40 0`;
  return (
    <svg className="heartbeat" viewBox="0 0 800 120" preserveAspectRatio="none" aria-hidden="true">
      <path className="heartbeat-trace" d={path} />
      <path className="heartbeat-glow" d={path} />
    </svg>
  );
}
