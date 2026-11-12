import { useEffect, useRef } from "react";

/*
 * Full-screen animated background (decorative, aria-hidden):
 *   - aurora: large soft colour clouds drifting slowly
 *   - "neural network" of nodes and medical crosses, with signals travelling along the links
 *     (a nod to the NLP + machine-learning core of the app); nodes reach towards the mouse
 *   - a DNA double helix turning on each side (wide screens only)
 *   - an ECG heartbeat trace sweeping along the bottom of the screen
 *
 * Performance and safety: one canvas, pixel ratio capped, node count scales with screen size,
 * the loop pauses when the tab is hidden, and with "reduce motion" a single still frame is drawn.
 * Nothing flashes: every brightness change is slow and small.
 */

const PALETTES = {
  light: {
    aurora: ["rgba(42,120,214,0.20)", "rgba(27,175,122,0.17)", "rgba(120,90,220,0.11)"],
    node: "42,120,214", node2: "20,138,98", link: "42,120,214", pulse: "20,170,120",
    ecg: "180,35,35", helix: "42,120,214", grid: "42,120,214",
  },
  dark: {
    aurora: ["rgba(42,120,214,0.30)", "rgba(27,175,122,0.22)", "rgba(130,90,230,0.20)"],
    node: "120,180,255", node2: "80,220,160", link: "110,170,250", pulse: "120,255,200",
    ecg: "255,110,110", helix: "110,170,250", grid: "110,170,250",
  },
};

// one heartbeat as (x, y) offsets, x in "beat units", y as a fraction of the amplitude
const BEAT = [[0, 0], [10, 0], [13, -0.12], [16, 0.08], [18, 0], [21, 0.15], [24, -1], [27, 0.55], [30, 0],
  [36, 0], [40, -0.22], [46, 0], [70, 0]];
const BEAT_LEN = 70;

function ecgY(u) { // u = position along the trace in beat units
  const p = ((u % BEAT_LEN) + BEAT_LEN) % BEAT_LEN;
  for (let i = 1; i < BEAT.length; i++) {
    const [x1, y1] = BEAT[i - 1], [x2, y2] = BEAT[i];
    if (p <= x2) return y1 + ((p - x1) / (x2 - x1 || 1)) * (y2 - y1);
  }
  return 0;
}

export default function MedicalBackground({ theme = "light" }) {
  const canvasRef = useRef(null);
  const themeRef = useRef(theme);
  themeRef.current = theme;

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext?.("2d");
    if (!ctx) return undefined; // e.g. the test environment
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, dpr = 1, nodes = [], pulses = [], raf = 0, last = performance.now(), t = 0, spawn = 0;
    const mouse = { x: -9999, y: -9999 };

    const build = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      w = window.innerWidth; h = window.innerHeight;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.max(28, Math.min(110, Math.round((w * h) / 12500)));
      nodes = Array.from({ length: count }, (_, i) => ({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 18, vy: (Math.random() - 0.5) * 18,   // px per second
        r: 1.6 + Math.random() * 2.2, cross: i % 6 === 0, alt: i % 3 === 0,
        phase: Math.random() * Math.PI * 2, spin: (Math.random() - 0.5) * 0.6,
      }));
      pulses = [];
    };

    const LINK = () => Math.min(170, Math.max(120, w / 9));

    const drawCross = (x, y, s, rot, color) => {
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.fillStyle = color;
      const a = s * 0.34;
      ctx.beginPath();
      if (ctx.roundRect) { ctx.roundRect(-a / 2, -s / 2, a, s, a / 3); ctx.roundRect(-s / 2, -a / 2, s, a, a / 3); }
      else { ctx.rect(-a / 2, -s / 2, a, s); ctx.rect(-s / 2, -a / 2, s, a); }
      ctx.fill(); ctx.restore();
    };

    const frame = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now; t += dt;
      const P = PALETTES[themeRef.current] || PALETTES.light;
      const dark = themeRef.current === "dark";
      ctx.clearRect(0, 0, w, h);

      // 1. aurora clouds
      ctx.globalCompositeOperation = dark ? "lighter" : "source-over";
      const clouds = [
        [0.2 + 0.12 * Math.sin(t * 0.07), 0.25 + 0.1 * Math.cos(t * 0.09), 0.55],
        [0.8 + 0.1 * Math.cos(t * 0.06), 0.3 + 0.14 * Math.sin(t * 0.08), 0.5],
        [0.5 + 0.2 * Math.sin(t * 0.05 + 1), 0.85 + 0.06 * Math.cos(t * 0.07), 0.6],
      ];
      clouds.forEach(([cx, cy, rr], i) => {
        const R = Math.max(w, h) * rr;
        const g = ctx.createRadialGradient(cx * w, cy * h, 0, cx * w, cy * h, R);
        g.addColorStop(0, P.aurora[i]); g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
      });
      ctx.globalCompositeOperation = "source-over";

      // 2. DNA helices on both sides (only where they sit beside, not behind, the content)
      if (w >= 1180) {
        [[64, 1], [w - 64, -1]].forEach(([hx, dir]) => {
          const amp = 26, step = 16;
          for (let y = -step; y < h + step; y += step) {
            const a = (y / 46) + t * 0.9 * dir;
            const x1 = hx + Math.sin(a) * amp, x2 = hx - Math.sin(a) * amp;
            const depth = (Math.cos(a) + 1) / 2;
            ctx.strokeStyle = `rgba(${P.helix},${0.05 + 0.07 * depth})`; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
            ctx.fillStyle = `rgba(${P.helix},${0.18 + 0.3 * depth})`;
            ctx.beginPath(); ctx.arc(x1, y, 2 + 1.6 * depth, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = `rgba(${P.node2},${0.18 + 0.3 * (1 - depth)})`;
            ctx.beginPath(); ctx.arc(x2, y, 2 + 1.6 * (1 - depth), 0, Math.PI * 2); ctx.fill();
          }
        });
      }

      // 3. network: move nodes, gently push away from the mouse
      for (const n of nodes) {
        const dx = n.x - mouse.x, dy = n.y - mouse.y, d2 = dx * dx + dy * dy;
        if (d2 < 140 * 140 && d2 > 1) { const f = (1 - Math.sqrt(d2) / 140) * 40 * dt; n.x += (dx / Math.sqrt(d2)) * f; n.y += (dy / Math.sqrt(d2)) * f; }
        n.x += n.vx * dt; n.y += n.vy * dt; n.phase += dt * 1.2;
        if (n.x < -20) n.x = w + 20; if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h + 20; if (n.y > h + 20) n.y = -20;
      }
      const L = LINK(), L2 = L * L, links = [];
      ctx.lineWidth = 1;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
          if (d2 < L2) {
            const k = 1 - Math.sqrt(d2) / L;
            ctx.strokeStyle = `rgba(${P.link},${(dark ? 0.36 : 0.3) * k})`;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
            links.push([i, j]);
          }
        }
        const mx = a.x - mouse.x, my = a.y - mouse.y, md = Math.sqrt(mx * mx + my * my);
        if (md < 200) {
          ctx.strokeStyle = `rgba(${P.pulse},${0.45 * (1 - md / 200)})`;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
        }
      }
      for (const n of nodes) {
        const glow = 0.55 + 0.25 * Math.sin(n.phase);
        if (n.cross) drawCross(n.x, n.y, 11 + n.r * 2, n.phase * n.spin, `rgba(${P.node2},${0.35 * glow + 0.15})`);
        else {
          ctx.fillStyle = `rgba(${n.alt ? P.node2 : P.node},${0.5 * glow + 0.3})`;
          ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
        }
      }

      // 4. signals travelling along the links
      spawn += dt;
      if (spawn > 0.12 && links.length && pulses.length < 40) {
        spawn = 0;
        const [i, j] = links[(Math.random() * links.length) | 0];
        pulses.push(Math.random() < 0.5 ? { a: i, b: j, p: 0 } : { a: j, b: i, p: 0 });
      }
      pulses = pulses.filter((q) => q.p < 1);
      for (const q of pulses) {
        q.p += dt * 0.9;
        const A = nodes[q.a], B = nodes[q.b];
        const x = A.x + (B.x - A.x) * q.p, y = A.y + (B.y - A.y) * q.p;
        const g = ctx.createRadialGradient(x, y, 0, x, y, 9);
        g.addColorStop(0, `rgba(${P.pulse},0.9)`); g.addColorStop(1, `rgba(${P.pulse},0)`);
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.fill();
      }

      // 5. ECG monitor sweeping along the bottom of the screen
      const base = h - Math.min(70, h * 0.09), amp = Math.min(46, h * 0.06), scale = Math.max(2.2, w / 420);
      const head = (t * 190) % (w + 260);                   // sweep position in px
      ctx.lineJoin = "round"; ctx.lineCap = "round";
      const seg = 3;
      for (let x = Math.max(0, head - 520); x < Math.min(w, head); x += seg) {
        const fade = 1 - (head - x) / 520;                   // bright at the head, fading tail
        ctx.strokeStyle = `rgba(${P.ecg},${(dark ? 0.75 : 0.5) * fade * fade})`;
        ctx.lineWidth = 1.2 + 1.3 * fade;
        ctx.beginPath();
        ctx.moveTo(x, base + ecgY(x / scale) * amp);
        ctx.lineTo(x + seg, base + ecgY((x + seg) / scale) * amp);
        ctx.stroke();
      }
      if (head < w) {
        const hy = base + ecgY(head / scale) * amp;
        const g = ctx.createRadialGradient(head, hy, 0, head, hy, 14);
        g.addColorStop(0, `rgba(${P.ecg},0.85)`); g.addColorStop(1, `rgba(${P.ecg},0)`);
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(head, hy, 14, 0, Math.PI * 2); ctx.fill();
      }

      if (!reduce && !document.hidden) raf = requestAnimationFrame(frame);
    };

    const start = () => { cancelAnimationFrame(raf); last = performance.now(); raf = requestAnimationFrame(frame); };
    const onResize = () => { build(); if (reduce) frame(performance.now()); };
    const onMove = (e) => { mouse.x = e.clientX; mouse.y = e.clientY; };
    const onLeave = () => { mouse.x = -9999; mouse.y = -9999; };
    const onVisible = () => { if (!document.hidden && !reduce) start(); };

    build();
    if (reduce) { t = 3; frame(performance.now()); } else start();
    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  return <canvas ref={canvasRef} className="medical-bg" aria-hidden="true" />;
}
