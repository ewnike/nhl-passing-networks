/* Shared helpers: DOM shortcuts, theme, canvas sizing and the pitch drawing. */
(function () {
  "use strict";
  const App = (window.App = { views: {}, current: null });
  const data = (App.data = window.POSSNET);
  const $ = (s, r = document) => r.querySelector(s);
  App.$ = $;

  App.css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  App.rgba = (hex, a) => {
    const h = hex.replace("#", "");
    const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
    const v = parseInt(n, 16);
    return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
  };

  App.store = {
    get(k, d) { try { const v = localStorage.getItem("possnet." + k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("possnet." + k, v); } catch (e) { /* storage unavailable */ } },
  };

  /* Size a canvas to its CSS box at device resolution and return a drawing context. */
  App.fit = (canvas) => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  };

  /* Pitch coordinates are meters from the centre, +x toward the goal being attacked and +y
     toward the acting team's left, which is the top of the screen when attacking rightward. */
  App.pitchView = (w, h) => {
    const [L, Wd] = data.meta.pitch;
    const pad = 16;
    const s = Math.min((w - 2 * pad) / L, (h - 2 * pad) / Wd);
    return { s, L, W: Wd, X: (x) => w / 2 + x * s, Y: (y) => h / 2 - y * s,
             invX: (px) => (px - w / 2) / s, invY: (py) => (h / 2 - py) / s };
  };

  App.drawPitch = (ctx, w, h) => {
    const v = App.pitchView(w, h);
    ctx.fillStyle = App.css("--pitch");
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = App.css("--pitch-line");
    ctx.lineWidth = 1.2;
    const yd = 0.9144, { X, Y, s, L, W } = v;
    const rect = (x0, y0, x1, y1) => ctx.strokeRect(X(x0), Y(y1), (x1 - x0) * s, (y1 - y0) * s);
    rect(-L / 2, -W / 2, L / 2, W / 2);
    ctx.beginPath(); ctx.moveTo(X(0), Y(-W / 2)); ctx.lineTo(X(0), Y(W / 2)); ctx.stroke();
    ctx.beginPath(); ctx.arc(X(0), Y(0), 10 * yd * s, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(X(0), Y(0), 2, 0, Math.PI * 2); ctx.fillStyle = App.css("--pitch-line"); ctx.fill();
    for (const sign of [-1, 1]) {
      const gx = sign * L / 2;
      rect(Math.min(gx, gx - sign * 18 * yd), -22 * yd, Math.max(gx, gx - sign * 18 * yd), 22 * yd);
      rect(Math.min(gx, gx - sign * 6 * yd), -10 * yd, Math.max(gx, gx - sign * 6 * yd), 10 * yd);
      rect(Math.min(gx, gx + sign * 2), -4 * yd, Math.max(gx, gx + sign * 2), 4 * yd);
      const px = gx - sign * 12 * yd;
      ctx.beginPath(); ctx.arc(X(px), Y(0), 2, 0, Math.PI * 2); ctx.fill();
      const a = Math.acos((18 - 12) / 10);
      ctx.beginPath();
      if (sign === 1) ctx.arc(X(px), Y(0), 10 * yd * s, Math.PI - a, Math.PI + a);
      else ctx.arc(X(px), Y(0), 10 * yd * s, -a, a);
      ctx.stroke();
    }
    return v;
  };

  App.fmt = {
    pct: (v, d = 1) => (v * 100).toFixed(d) + "%",
    n: (v, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : "n/a"),
    signed: (v, d = 3) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d),
    date: (s) => new Date(s + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" }),
    min: (t) => Math.floor(t / 60) + "′",
  };

  const PARTICLES = new Set(["da", "de", "dos", "del", "van", "von", "di", "le", "la", "al", "bin", "ter", "der", "den"]);
  App.shortName = (full) => {
    const tokens = String(full).split(/\s+/).filter(Boolean);
    const core = tokens.filter((t) => !PARTICLES.has(t.toLowerCase()));
    if (core.length <= 2) return core[core.length - 1] || full;
    return core[1];
  };

  App.el = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "text") e.textContent = v; else e.setAttribute(k, v);
    }
    for (const kid of kids) e.append(kid);
    return e;
  };

  /* Segmented control helper: buttons with data-v, one pressed. */
  App.seg = (root, onChange) => {
    root.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-v]");
      if (!b) return;
      for (const x of root.querySelectorAll("button")) x.setAttribute("aria-pressed", String(x === b));
      onChange(b.dataset.v);
    });
  };
  App.setSeg = (root, v) => {
    for (const x of root.querySelectorAll("button")) x.setAttribute("aria-pressed", String(x.dataset.v === v));
  };

  /* Seeded generator so dropped balls are repeatable. */
  App.rng = (seed) => () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  App.redraw = () => { const v = App.views[App.current]; if (v && v.draw) v.draw(); };
})();
