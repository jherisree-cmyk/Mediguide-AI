// Lightweight SVG charts for the admin dashboard (no chart library).
// Design rules (dataviz guidelines): thin marks, recessive grid, direct value labels,
// hover tooltips (<title>), every chart also available as a table, one axis only,
// urgency colours identical to the app's badges and always paired with a text label.

const INK2 = "#52514e";
const MUTED = "#898781";
const GRID = "#e1e0d9";
export const SERIES = "#2a78d6";
export const LEVEL_COLORS = { EMERGENCY: "#b42323", URGENT: "#c98500", ROUTINE: "#1c5cab" };

function ChartFrame({ title, rows, columns, children }) {
  return (
    <figure className="chart card">
      <figcaption className="chart-title">{title}</figcaption>
      {children}
      <details className="chart-table">
        <summary>Show as table</summary>
        <table>
          <thead><tr>{columns.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
          <tbody>{rows.map((r) => <tr key={r[0]}>{r.map((v, i) => <td key={i}>{v}</td>)}</tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}

/** Horizontal bars. data: [{label, value, color?}]; value "<5" = suppressed small group. */
export function BarChart({ title, data, valueLabel = "Count" }) {
  const numeric = data.map((d) => (typeof d.value === "number" ? d.value : 0));
  const max = Math.max(1, ...numeric);
  const rowH = 34;
  const labelW = 180;
  const width = 480;   // close to the rendered width, so 13px text stays ~13px
  const plotW = width - labelW - 44;
  const height = data.length * rowH + 8;
  return (
    <ChartFrame title={title} columns={["", valueLabel]} rows={data.map((d) => [d.label, d.value])}>
      {data.length === 0 ? <p className="muted">No data yet.</p> : (
        <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={title}>
          {[0.25, 0.5, 0.75, 1].map((f) => (
            <line key={f} x1={labelW + plotW * f} x2={labelW + plotW * f} y1={0} y2={height} stroke={GRID} strokeWidth="1" />
          ))}
          <line x1={labelW} x2={labelW} y1={0} y2={height} stroke="#c3c2b7" strokeWidth="1" />
          {data.map((d, i) => {
            const y = i * rowH + 6;
            const suppressed = typeof d.value !== "number";
            const w = suppressed ? 0 : Math.max(2, (d.value / max) * plotW);
            return (
              <g key={d.label}>
                <title>{`${d.label}: ${d.value}`}</title>
                <text x={labelW - 8} y={y + 15} textAnchor="end" fontSize="13" fill={INK2}>
                  {d.label.length > 24 ? `${d.label.slice(0, 23)}…` : d.label}
                </text>
                <rect x={labelW} y={y} width={w} height={rowH - 14} rx="4" fill={d.color || SERIES} />
                <text x={labelW + w + 6} y={y + 15} fontSize="13" fill={INK2}>{suppressed ? "<5" : d.value}</text>
              </g>
            );
          })}
        </svg>
      )}
    </ChartFrame>
  );
}

/** Daily counts as a line with markers. data: [{day: "YYYY-MM-DD", value}] */
export function LineChart({ title, data }) {
  const width = 480;
  const height = 210;
  const pad = { l: 36, r: 12, t: 12, b: 28 };
  const max = Math.max(1, ...data.map((d) => d.value));
  const x = (i) => pad.l + (data.length <= 1 ? (width - pad.l - pad.r) / 2 : (i / (data.length - 1)) * (width - pad.l - pad.r));
  const y = (v) => pad.t + (1 - v / max) * (height - pad.t - pad.b);
  const ticks = [0, Math.ceil(max / 2), max];
  return (
    <ChartFrame title={title} columns={["Day", "Assessments"]} rows={data.map((d) => [d.day, d.value])}>
      {data.length === 0 ? <p className="muted">No data yet.</p> : (
        <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={title}>
          {ticks.map((tk) => (
            <g key={tk}>
              <line x1={pad.l} x2={width - pad.r} y1={y(tk)} y2={y(tk)} stroke={GRID} strokeWidth="1" />
              <text x={pad.l - 6} y={y(tk) + 4} textAnchor="end" fontSize="12" fill={MUTED}>{tk}</text>
            </g>
          ))}
          <polyline fill="none" stroke={SERIES} strokeWidth="2"
                    points={data.map((d, i) => `${x(i)},${y(d.value)}`).join(" ")} />
          {data.map((d, i) => (
            <g key={d.day}>
              <title>{`${d.day}: ${d.value}`}</title>
              <circle cx={x(i)} cy={y(d.value)} r="4.5" fill={SERIES} stroke="#fcfcfb" strokeWidth="2" />
              <circle cx={x(i)} cy={y(d.value)} r="12" fill="transparent" />
            </g>
          ))}
          {[0, data.length - 1].filter((v, i, a) => a.indexOf(v) === i).map((i) => (
            <text key={i} x={x(i)} y={height - 8} fontSize="12" fill={MUTED}
                  textAnchor={data.length === 1 ? "middle" : i === 0 ? "start" : "end"}>{data[i].day.slice(5)}</text>
          ))}
        </svg>
      )}
    </ChartFrame>
  );
}
