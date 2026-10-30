/* Networks view.

   Two ways to watch one match, both driven by the same clock:

   Live play     The ball travels along every logged pass, carry and shot. Players are drawn where
                 the event log last saw them and glide to the place of their next logged action.
                 The pass line grows with the ball. Opposing players can be switched on, but their
                 positions are approximate: the open data has no tracking, only ball events.

   Network       Players sit at fixed average positions. Each completed pass sends a pulse along its
                 link; the link is counted when the pulse lands, so every line is the sum of passes
                 you watched. Node size shows the chosen centrality measure.

   Time can run pass by pass (idle time skipped, every action gets the same screen time) or in
   real time at a chosen speed. Everything drawn is a function of the clock st.t. */
(function () {
  "use strict";
  const App = window.App, $ = App.$, D = App.data, M = D.matches, TEAMS = D.teams, PL = D.players;
  const f = App.fmt;
  const META = D.meta, TXT = META.text || {};   // per sport settings, see sport_ui.js
  const WINDOW_S = META.window_s || 900;         // seconds shown by the "last 15 min" network
  const BLEND = 0.5;            // share of the assigned spot in the blended layout
  const MIN_GAP = 7;            // meters kept between two dots of the same team
  const TRAIL = 5;              // how many earlier actions stay faintly on the pitch
  const MOVE_S = 1.8;           // game seconds a player takes to reach the place of his next action
  const WALL = { ball: 0.9, shot: 0.7, rest: 0.18 };   // screen seconds per action at normal pace
  const st = { mi: 0, side: "h", t: 0, playing: false, rate: { type: "pbp", v: 1 }, view: "live",
               opp: true, layout: "blend", mode: "cum", minW: 1, metric: "strength", open: true, team: "all",
               until: null };
  let P = null, graphs = null, graphKey = "", nodes = new Map(), last = 0, hover = null, hits = [];
  let stepping = false, feedKey = "", scoreKey = "", clockKey = "";
  const cache = new Map();
  const els = {};

  const lower = (a, v) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < v) lo = m + 1; else hi = m; } return lo; };
  const upper = (a, v) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] <= v) lo = m + 1; else hi = m; } return lo; };
  const match = () => M[st.mi];
  const color = (side) => App.css(side === "h" ? "--home" : "--away");
  const other = (side) => (side === "h" ? "a" : "h");
  const sideOf = (i) => (i === 0 ? "h" : "a");
  const win = () => ({ t0: st.view === "net" && st.mode === "win" ? Math.max(0, st.t - WINDOW_S) : 0, t1: st.t });
  const smooth = (u) => u * u * (3 - 2 * u);

  /* ---------- per match preparation ---------- */
  function prep(mi) {
    if (cache.has(mi)) return cache.get(mi);
    const m = M[mi], e = m.ev, n = e.t.length;
    const T = new Float64Array(n), kind = new Int8Array(n), side = new Uint8Array(n);
    const dead = new Uint8Array(n), goal = new Uint8Array(n), FL = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const k = e.k[i];
      T[i] = e.t[i] / 10; kind[i] = k & 7; side[i] = (k >> 3) & 1; dead[i] = (k >> 4) & 1; goal[i] = (k >> 5) & 1;
    }
    const B = [];
    for (let i = 0; i < n; i++) if (kind[i] <= 3) B.push(i);
    for (let j = 0; j < B.length; j++) {
      const i = B[j], gap = (j + 1 < B.length ? T[B[j + 1]] : m.end) - T[i];
      FL[i] = Math.max(0.15, Math.min(e.u[i] / 10 || 1, gap - 0.05));
    }
    const Tb = Float64Array.from(B, (i) => T[i]);

    // Where each player was last seen: one entry per logged action, plus the landing of passes
    // and the end of carries.
    const raw = new Map();
    const add = (pid, s, t, x, y) => {
      let o = raw.get(pid);
      if (!o) { o = { side: s, e: [] }; raw.set(pid, o); }
      o.e.push([t, x, y]);
    };
    for (let i = 0; i < n; i++) {
      const k = kind[i], s = side[i];
      add(e.f[i], s, T[i], e.x0[i], e.y0[i]);
      if (k === 0 && e.r[i] >= 0) add(e.r[i], s, T[i] + FL[i], e.x1[i], e.y1[i]);
      else if (k === 2) add(e.f[i], s, T[i] + FL[i], e.x1[i], e.y1[i]);
    }
    const tracks = new Map();
    for (const [pid, o] of raw) {
      o.e.sort((a, b) => a[0] - b[0]);
      tracks.set(pid, { side: o.side, t: Float64Array.from(o.e, (z) => z[0]),
                        x: Float64Array.from(o.e, (z) => z[1]), y: Float64Array.from(o.e, (z) => z[2]) });
    }
    const span = new Map(), role = new Map();
    for (const s of ["h", "a"]) for (const [pid, on, off, pos] of m.lu[s]) { span.set(pid, [on, off]); role.set(pid, pos); }

    // Completed passes per side, ordered by landing time, and average positions for the network.
    const passes = { h: [], a: [] }, sum = new Map();
    for (let i = 0; i < n; i++) {
      if (kind[i] !== 0 || e.r[i] < 0 || e.r[i] === e.f[i]) continue;
      passes[side[i] ? "a" : "h"].push({ tl: T[i] + FL[i], f: e.f[i], r: e.r[i], d: dead[i], i });
      for (const [pid, x, y] of [[e.f[i], e.x0[i], e.y0[i]], [e.r[i], e.x1[i], e.y1[i]]]) {
        const z = sum.get(pid) || [0, 0, 0]; z[0] += x; z[1] += y; z[2] += 1; sum.set(pid, z);
      }
    }
    const pl = {};
    for (const s of ["h", "a"]) {
      passes[s].sort((a, b) => a.tl - b.tl);
      pl[s] = { tl: Float64Array.from(passes[s], (z) => z.tl), list: passes[s] };
    }
    const anchor = new Map();
    for (const [pid, z] of sum) anchor.set(pid, [z[0] / z[2], z[1] / z[2]]);
    const goals = [];
    for (let i = 0; i < n; i++) if (kind[i] === 3 && goal[i]) goals.push(i);
    const out = { m, n, e, T, kind, side, dead, goal, FL, B, Tb, tracks, span, role, pl, anchor, goals, layouts: {} };
    cache.set(mi, out);
    return out;
  }

  /* Network node positions for the chosen layout: the average of where the player touched the ball
     (actual), the textbook spot for his assigned position (assigned), or a mix of the two (blend).
     Assigned and blended spots are nudged apart when two players of a team sit too close, which
     separates a substitute from the player he replaced. */
  function layoutFor(mode) {
    if (P.layouts[mode]) return P.layouts[mode];
    const pos = new Map();
    for (const [pid, real] of P.anchor) {
      const sg = P.tracks.has(pid) && P.tracks.get(pid).side === 1 ? 1 : 0;
      const slot = D.meta.slots[P.role.get(pid)];
      if (mode === "actual" || !slot) pos.set(pid, [real[0], real[1], sg]);
      else if (mode === "assigned") pos.set(pid, [slot[0], slot[1], sg]);
      else pos.set(pid, [slot[0] * BLEND + real[0] * (1 - BLEND), slot[1] * BLEND + real[1] * (1 - BLEND), sg]);
    }
    if (mode !== "actual") {
      const ids = [...pos.keys()];
      for (let it = 0; it < 40; it++) {
        for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
          const a = pos.get(ids[i]), b = pos.get(ids[j]);
          if (a[2] !== b[2]) continue;
          let dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy);
          if (d >= MIN_GAP) continue;
          if (d < 0.01) { dx = 1; dy = 0; d = 1; }
          const push = (MIN_GAP - d) / 2 / d;
          a[0] -= dx * push; a[1] -= dy * push; b[0] += dx * push; b[1] += dy * push;
        }
      }
    }
    P.layouts[mode] = pos;
    return pos;
  }
  const anchorOf = (pid) => layoutFor(st.layout).get(pid);

  /* ---------- clock ---------- */
  const slotAt = (t) => upper(P.Tb, t) - 1;
  function slotInfo(j) {
    const i = P.B[j], t0 = P.T[i], t1 = j + 1 < P.B.length ? P.T[P.B[j + 1]] : match().end;
    const G = Math.max(1e-6, t1 - t0), F = Math.min(P.FL[i], G);
    const wf = P.kind[i] === 3 ? WALL.shot : WALL.ball, wr = G - F > 0.3 ? WALL.rest : 0.03;
    return { i, t0, t1, G, F, wf, wr };
  }
  /* Pass by pass time: each action spends wf on screen while the ball moves, then a short rest
     that covers the gap to the next action, however long it was. */
  function advancePbp(t, wall) {
    let rem = wall;
    while (rem > 0) {
      const j = slotAt(t);
      if (j < 0) { if (!P.B.length) return match().end; t = P.Tb[0]; continue; }
      const s = slotInfo(j);
      const w = t < s.t0 + s.F ? ((t - s.t0) / s.F) * s.wf : s.wf + ((t - s.t0 - s.F) / Math.max(1e-6, s.G - s.F)) * s.wr;
      const total = s.wf + s.wr, nw = w + rem;
      if (nw >= total - 1e-9) { rem = nw - total; t = s.t1 + 1e-6; if (j + 1 >= P.B.length) return match().end; continue; }
      rem = 0;
      t = nw < s.wf ? s.t0 + (nw / s.wf) * s.F : s.t0 + s.F + ((nw - s.wf) / s.wr) * (s.G - s.F);
    }
    return t;
  }
  function advance(dt) {
    const r = st.rate;
    st.t = r.type === "rt" ? st.t + dt * r.v : advancePbp(st.t, dt * r.v);
    if (st.until !== null && st.t >= st.until) { st.t = st.until; st.until = null; st.playing = false; updatePlay(); }
    if (st.t >= match().end) { st.t = match().end; st.playing = false; updatePlay(); }
  }
  function stepAction(dir) {
    const j = Math.max(0, slotAt(st.t));
    if (dir < 0) {
      const k = Math.max(0, j - 1), i = P.B[k];
      st.t = P.T[i] + P.FL[i]; st.until = null; st.playing = false; updatePlay();
      return;
    }
    const s = slotInfo(j);
    const mid = slotAt(st.t) >= 0 && st.t < s.t0 + s.F - 1e-6;
    const k = mid ? j : Math.min(P.B.length - 1, slotAt(st.t) < 0 ? 0 : j + 1);
    const q = slotInfo(k);
    if (st.t < q.t0) st.t = q.t0;
    st.until = q.t0 + q.F; st.playing = true; stepping = true; updatePlay();
  }

  /* ---------- networks ---------- */
  function build(side, t0, t1) {
    const pl = P.pl[side], lo = lower(pl.tl, t0), hi = upper(pl.tl, t1);
    const idx = new Map(), ids = [];
    const get = (pid) => { if (!idx.has(pid)) { idx.set(pid, ids.length); ids.push(pid); } return idx.get(pid); };
    const pairs = [];
    for (let k = lo; k < hi; k++) {
      const p = pl.list[k];
      if (st.open && p.d) continue;
      pairs.push([get(p.f), get(p.r)]);
    }
    const n = ids.length;
    const W = Array.from({ length: n }, () => new Array(n).fill(0));
    for (const [a, b] of pairs) W[a][b] += 1;
    const pos = ids.map((pid) => anchorOf(pid) || [0, 0]);
    return { ids, W, pos, an: n ? Metrics.analyze(W) : null, n, passes: pairs.length };
  }

  function count(side, t0, t1) {
    const out = { shots: 0, xg: 0 }, idx = side === "h" ? 0 : 1;
    for (const s of match().shots) if (s[0] >= t0 && s[0] <= t1 && s[1] === idx) { out.shots++; out.xg += s[2]; }
    return out;
  }

  function refresh(force) {
    const { t0, t1 } = win();
    const key = [st.mi, st.view, st.open, st.mode, upper(P.pl.h.tl, t1), upper(P.pl.a.tl, t1),
                 lower(P.pl.h.tl, t0), lower(P.pl.a.tl, t0), Math.round(t1 / 30)].join("|");
    if (!force && key === graphKey) return;
    graphKey = key;
    graphs = { h: build("h", t0, t1), a: build("a", t0, t1), t0, t1 };
    syncNodes();
    renderReadout();
  }

  function syncNodes() {
    const g = graphs[st.side], seen = new Set();
    const vals = g.n ? g.an[st.metric] : [];
    const mx = Math.max(1e-9, ...vals);
    g.ids.forEach((pid, i) => {
      seen.add(pid);
      let nd = nodes.get(pid);
      if (!nd) { nd = { x: g.pos[i][0], y: g.pos[i][1], r: 0, a: 0 }; nodes.set(pid, nd); }
      nd.tx = g.pos[i][0]; nd.ty = g.pos[i][1];
      nd.tr = 5 + 17 * Math.sqrt(Math.max(0, vals[i]) / mx); nd.ta = 1; nd.i = i;
    });
    for (const [pid, nd] of nodes) if (!seen.has(pid)) { nd.ta = 0; nd.tr = 0; nd.i = -1; }
  }

  function edgesVisible() {
    const g = graphs[st.side], out = [];
    let top = 0;
    for (let a = 0; a < g.n; a++) for (let b = 0; b < g.n; b++) if (a !== b && g.W[a][b] > top) top = g.W[a][b];
    const cut = Math.min(st.minW, top);
    for (let a = 0; a < g.n; a++) for (let b = 0; b < g.n; b++) {
      if (a !== b && g.W[a][b] >= cut && g.W[a][b] > 0) out.push({ a, b, w: g.W[a][b] });
    }
    return out;
  }

  /* ---------- geometry ---------- */
  const flip = (s) => (sideOf(s) === st.side ? 1 : -1);      // other team is drawn rotated 180 degrees
  function curve(p, q, bend) {
    const mx = (p.x + q.x) / 2, my = (p.y + q.y) / 2, dx = q.x - p.x, dy = q.y - p.y;
    const len = Math.hypot(dx, dy) || 1;
    return { cx: mx + (dy / len) * len * bend, cy: my - (dx / len) * len * bend };
  }
  const bez = (p, c, q, u) => ({
    x: (1 - u) * (1 - u) * p.x + 2 * (1 - u) * u * c.cx + u * u * q.x,
    y: (1 - u) * (1 - u) * p.y + 2 * (1 - u) * u * c.cy + u * u * q.y });

  /* Where a player is at time t: at the place of his last logged action, moving to the place of
     the next one during the final MOVE_S seconds before it. */
  function playerAt(tr, t) {
    const n = tr.t.length;
    const j = upper(tr.t, t) - 1;
    if (j < 0) return { x: tr.x[0], y: tr.y[0], age: 1e9 };
    if (j >= n - 1) return { x: tr.x[j], y: tr.y[j], age: t - tr.t[j] };
    const dur = Math.min(MOVE_S, tr.t[j + 1] - tr.t[j]), start = tr.t[j + 1] - dur;
    if (t <= start || dur <= 0) return { x: tr.x[j], y: tr.y[j], age: t - tr.t[j] };
    const s = smooth(Math.min(1, (t - start) / dur));
    return { x: tr.x[j] + (tr.x[j + 1] - tr.x[j]) * s, y: tr.y[j] + (tr.y[j + 1] - tr.y[j]) * s, age: t - tr.t[j] };
  }
  function onPitch(pid, tr, t) {
    const sp = P.span.get(pid);
    if (sp) return t >= sp[0] - 1 && t <= sp[1] + 1;
    return t >= tr.t[0] - 5 && t <= tr.t[tr.t.length - 1] + 5;
  }

  /* The ball: a point moving along the current action, resting at its end until the next one. */
  function ballAt(t) {
    const j = slotAt(t);
    if (j < 0) return { x: 0, y: 0, j, u: 1, out: false, kind: -1 };
    const i = P.B[j], u = Math.min(1, Math.max(0, (t - P.T[i]) / P.FL[i])), s = flip(P.side[i]);
    const x0 = P.e.x0[i] * s, y0 = P.e.y0[i] * s, x1 = P.e.x1[i] * s, y1 = P.e.y1[i] * s;
    const q = u * (2 - u);
    const nx = j + 1 < P.B.length ? P.B[j + 1] : -1;
    return { x: x0 + (x1 - x0) * q, y: y0 + (y1 - y0) * q, j, i, u, q, kind: P.kind[i],
             out: u >= 1 && nx >= 0 && P.dead[nx] === 1 };
  }

  /* ---------- drawing: live play ---------- */
  function arrowHead(ctx, x0, y0, x1, y1, size) {
    const a = Math.atan2(y1 - y0, x1 - x0);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 - size * Math.cos(a - 0.45), y1 - size * Math.sin(a - 0.45));
    ctx.lineTo(x1 - size * Math.cos(a + 0.45), y1 - size * Math.sin(a + 0.45));
    ctx.closePath(); ctx.fill();
  }

  function drawTrails(ctx, v, ball) {
    if (ball.j < 0) return;
    for (let jj = Math.max(0, ball.j - TRAIL); jj <= ball.j; jj++) {
      const i = P.B[jj], head = jj === ball.j, age = ball.j - jj;
      const s = flip(P.side[i]), col = color(sideOf(P.side[i]));
      const x0 = P.e.x0[i] * s, y0 = P.e.y0[i] * s, x1 = P.e.x1[i] * s, y1 = P.e.y1[i] * s;
      const q = head ? ball.q : 1;
      const ax = v.X(x0), ay = v.Y(y0), bx = v.X(x0 + (x1 - x0) * q), by = v.Y(y0 + (y1 - y0) * q);
      if (Math.hypot(bx - ax, by - ay) < 1) continue;
      const alpha = head ? 0.95 : 0.55 * (1 - age / (TRAIL + 1));
      const k = P.kind[i];
      ctx.strokeStyle = App.rgba(col, alpha); ctx.fillStyle = App.rgba(col, alpha);
      ctx.lineWidth = k === 3 ? 3.2 : head ? 2.8 : 2;
      ctx.setLineDash(k === 1 ? [6, 5] : k === 2 ? [2, 5] : []);
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
      ctx.setLineDash([]);
      if (k !== 2 && Math.hypot(bx - ax, by - ay) > 14) arrowHead(ctx, ax, ay, bx, by, 8);
      if (k === 1 && q >= 1) {         // a pass that did not find a teammate
        ctx.beginPath(); ctx.moveTo(bx - 4, by - 4); ctx.lineTo(bx + 4, by + 4); ctx.moveTo(bx + 4, by - 4); ctx.lineTo(bx - 4, by + 4); ctx.stroke();
      }
    }
  }

  function drawPlayers(ctx, v, t, ball) {
    const surface = App.css("--surface"), ink = App.css("--ink");
    const rp = Math.max(6, Math.min(11, v.s * 1.1));
    const holder = ball.j >= 0 && ball.u >= 1 ? (ball.kind === 0 ? P.e.r[ball.i] : ball.kind === 2 ? P.e.f[ball.i] : -1) : -1;
    const list = [];
    for (const [pid, tr] of P.tracks) {
      const s = sideOf(tr.side), mine = s === st.side;
      if (!mine && !st.opp) continue;
      if (!onPitch(pid, tr, t)) continue;
      const p = playerAt(tr, t), sg = mine ? 1 : -1;
      list.push({ pid, mine, s, x: p.x * sg, y: p.y * sg, age: p.age });
    }
    list.sort((a, b) => Number(a.mine) - Number(b.mine));
    ctx.font = "600 11px " + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    hits = [];
    for (const q of list) {
      const px = v.X(q.x), py = v.Y(q.y), col = color(q.s);
      const fade = Math.max(0.4, 1 - q.age / 90);
      hits.push({ pid: q.pid, mine: q.mine, x: px, y: py, r: rp, age: q.age });
      if (q.mine) {
        ctx.globalAlpha = fade;
        ctx.fillStyle = App.rgba(col, 0.9); ctx.strokeStyle = surface; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(px, py, rp, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.globalAlpha = 1;
      } else {
        ctx.globalAlpha = fade;
        ctx.fillStyle = App.rgba(col, 0.16); ctx.strokeStyle = App.rgba(col, 0.95); ctx.lineWidth = 1.8;
        ctx.beginPath(); ctx.arc(px, py, rp * 0.9, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.globalAlpha = 1;
      }
      if (q.pid === holder || hover === q.pid) {
        ctx.strokeStyle = ink; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(px, py, rp + 3, 0, Math.PI * 2); ctx.stroke();
      }
      if (q.mine || hover === q.pid) {
        const name = App.shortName(PL[q.pid]);
        ctx.lineWidth = 3.5; ctx.strokeStyle = App.rgba(surface, 0.9);
        ctx.strokeText(name, px, py + rp + 9);
        ctx.fillStyle = ink; ctx.fillText(name, px, py + rp + 9);
      }
    }
  }

  function drawBall(ctx, v, ball) {
    const px = v.X(ball.x), py = v.Y(ball.y), r = Math.max(4.5, Math.min(7, v.s * 0.75));
    ctx.globalAlpha = ball.out ? 0.4 : 1;
    ctx.fillStyle = "rgba(0,0,0,.18)";
    ctx.beginPath(); ctx.ellipse(px + 1.5, py + 2.5, r, r * 0.6, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#16201b"; ctx.lineWidth = 1.8;
    ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#16201b";
    ctx.beginPath(); ctx.arc(px, py, r * 0.38, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawBanner(ctx, w, ball) {
    for (const gi of P.goals) {
      if (P.T[gi] > st.t || ball.j < 0) continue;
      const j = P.B.indexOf(gi);
      if (ball.j > j + 1) continue;
      const s = sideOf(P.side[gi]), name = PL[P.e.f[gi]];
      ctx.font = "700 20px " + getComputedStyle(document.body).fontFamily;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      const msg = "GOAL  " + App.shortName(name) + "  (" + TEAMS[s === "h" ? match().h : match().a] + ")";
      ctx.lineWidth = 6; ctx.strokeStyle = App.rgba(App.css("--surface"), 0.92); ctx.strokeText(msg, w / 2, 34);
      ctx.fillStyle = color(s); ctx.fillText(msg, w / 2, 34);
    }
  }

  function drawLive(ctx, w, h, v) {
    const ball = ballAt(st.t);
    drawTrails(ctx, v, ball);
    drawPlayers(ctx, v, st.t, ball);
    if (ball.j >= 0) drawBall(ctx, v, ball);
    drawBanner(ctx, w, ball);
  }

  /* ---------- drawing: network ---------- */
  function drawNetwork(ctx, w, h, v) {
    const g = graphs[st.side], col = color(st.side);
    const toPx = (nd) => ({ x: v.X(nd.x), y: v.Y(nd.y) });
    const edges = edgesVisible();
    const maxW = Math.max(1, ...edges.map((e) => e.w));
    ctx.lineCap = "round";
    for (const e of edges) {
      const na = nodes.get(g.ids[e.a]), nb = nodes.get(g.ids[e.b]);
      if (!na || !nb) continue;
      const p = toPx(na), q = toPx(nb), c = curve(p, q, 0.12), k = e.w / maxW;
      ctx.strokeStyle = App.rgba(col, 0.16 + 0.5 * k);
      ctx.lineWidth = 0.8 + 4.2 * k;
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.quadraticCurveTo(c.cx, c.cy, q.x, q.y); ctx.stroke();
    }
    // the two most recent landed passes glow, and the pass in flight draws itself along its link
    const pl = P.pl[st.side], landed = upper(pl.tl, st.t) - 1;
    const link = (pid, pid2) => {
      const A = anchorOf(pid), B = anchorOf(pid2);
      if (!A || !B) return null;
      const p = { x: v.X(A[0]), y: v.Y(A[1]) }, q = { x: v.X(B[0]), y: v.Y(B[1]) };
      return { p, q, c: curve(p, q, 0.12) };
    };
    const trace = (L, u) => {
      ctx.beginPath(); ctx.moveTo(L.p.x, L.p.y);
      for (let s = 1; s <= 24; s++) { const z = bez(L.p, L.c, L.q, (u * s) / 24); ctx.lineTo(z.x, z.y); }
      ctx.stroke();
    };
    for (let k = 0; k < 2; k++) {
      const idx = landed - k;
      if (idx < 0 || (st.open && pl.list[idx].d)) continue;
      const L = link(pl.list[idx].f, pl.list[idx].r);
      if (!L) continue;
      ctx.strokeStyle = App.rgba(col, k === 0 ? 0.95 : 0.55); ctx.lineWidth = k === 0 ? 3.4 : 2.6;
      trace(L, 1);
    }
    const ball = ballAt(st.t);
    if (ball.j >= 0 && ball.kind === 0 && sideOf(P.side[ball.i]) === st.side && ball.u < 1 && !(st.open && P.dead[ball.i])) {
      const L = link(P.e.f[ball.i], P.e.r[ball.i]);
      if (L) {
        ctx.strokeStyle = App.rgba(col, 0.95); ctx.lineWidth = 3.4; trace(L, ball.q);
        const z = bez(L.p, L.c, L.q, ball.q);
        ctx.fillStyle = "#fff"; ctx.strokeStyle = "#16201b"; ctx.lineWidth = 1.8;
        ctx.beginPath(); ctx.arc(z.x, z.y, 5.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        for (const pid of [P.e.f[ball.i], P.e.r[ball.i]]) {
          if (nodes.has(pid) && nodes.get(pid).a > 0.5) continue;
          const A = anchorOf(pid); if (!A) continue;
          ctx.strokeStyle = App.rgba(col, 0.8); ctx.setLineDash([3, 3]); ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.arc(v.X(A[0]), v.Y(A[1]), 7, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
        }
      }
    }
    const surface = App.css("--surface");
    ctx.font = "600 11px " + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    hits = [];
    const order = [...nodes.entries()].sort((a, b) => b[1].r - a[1].r);
    for (const [id, nd] of order) {
      if (nd.a < 0.02) continue;
      const px = v.X(nd.x), py = v.Y(nd.y);
      ctx.globalAlpha = nd.a;
      ctx.fillStyle = App.rgba(col, 0.82); ctx.strokeStyle = surface; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(px, py, Math.max(nd.r, 0.1), 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      if (hover === id) { ctx.strokeStyle = App.css("--ink"); ctx.lineWidth = 1.5; ctx.stroke(); }
      if (nd.r > 6 && nd.ta > 0) {
        const name = App.shortName(PL[id]);
        ctx.lineWidth = 3.5; ctx.strokeStyle = App.rgba(surface, 0.9);
        ctx.strokeText(name, px, py + nd.r + 9);
        ctx.fillStyle = App.css("--ink"); ctx.fillText(name, px, py + nd.r + 9);
      }
      ctx.globalAlpha = 1;
      if (nd.ta > 0) hits.push({ pid: id, mine: true, x: px, y: py, r: nd.r, net: true });
    }
  }

  function draw() {
    if (!P || !graphs) return;
    const { ctx, w, h } = App.fit(els.canvas);
    const v = App.drawPitch(ctx, w, h);
    if (st.view === "live") drawLive(ctx, w, h, v); else drawNetwork(ctx, w, h, v);
    drawTimeline();
    renderFeed();
    renderClock();
  }

  /* ---------- timeline ---------- */
  const TL = { l: 14, r: 14 };
  const tx = (t, w) => TL.l + (t / match().end) * (w - TL.l - TL.r);
  function drawTimeline() {
    const { ctx, w, h } = App.fit(els.tl);
    const m = match();
    ctx.clearRect(0, 0, w, h);
    const mid = h / 2 + 4, ink = App.css("--ink"), muted = App.css("--muted"), line = App.css("--line");
    const mine = st.side === "h" ? 0 : 1;
    const cMine = color(st.side), cOpp = color(other(st.side));
    ctx.font = "11px " + getComputedStyle(document.body).fontFamily;
    ctx.textBaseline = "alphabetic";
    if (st.view === "net" && st.mode === "win") {
      const { t0, t1 } = win();
      ctx.fillStyle = App.rgba(App.css("--home"), 0.1);
      ctx.fillRect(tx(t0, w), 6, tx(t1, w) - tx(t0, w), h - 12);
    }
    ctx.strokeStyle = line; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(TL.l, mid); ctx.lineTo(w - TL.r, mid); ctx.stroke();
    ctx.setLineDash([3, 3]);
    const breaks = m.pb || [m.ht], names = META.break_labels || ["HT"];
    for (const b of breaks) { ctx.beginPath(); ctx.moveTo(tx(b, w), 8); ctx.lineTo(tx(b, w), h - 8); ctx.stroke(); }
    ctx.setLineDash([]);
    ctx.fillStyle = muted; ctx.textAlign = "center";
    breaks.forEach((b, q) => ctx.fillText(names[q] || "", tx(b, w), h - 1));
    for (let s = 0; s <= m.end; s += META.tick_s || 900) { ctx.fillText(Math.round(s / 60) + "′", tx(s, w), 11); }
    for (const s of m.shots) {
      const own = s[1] === mine, len = META.has_xg === false ? 14 : 5 + 28 * Math.sqrt(s[2]), x = tx(s[0], w);
      ctx.strokeStyle = App.rgba(own ? cMine : cOpp, 0.7); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x, mid); ctx.lineTo(x, mid + (own ? -len : len)); ctx.stroke();
    }
    for (const g of m.goals) {
      const own = g[1] === mine, x = tx(g[0], w);
      ctx.fillStyle = own ? cMine : cOpp; ctx.strokeStyle = App.css("--surface"); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, mid, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    const x = tx(st.t, w);
    ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x, 14); ctx.lineTo(x, h - 12); ctx.stroke();
    ctx.fillStyle = ink; ctx.beginPath(); ctx.arc(x, 14, 4, 0, Math.PI * 2); ctx.fill();
    els.tl.setAttribute("aria-valuenow", String(Math.round((st.t / m.end) * 100)));
  }

  function tlTime(ev) {
    const r = els.tl.getBoundingClientRect();
    const u = (ev.clientX - r.left - TL.l) / (r.width - TL.l - TL.r);
    return Math.max(0, Math.min(1, u)) * match().end;
  }

  /* ---------- readout ---------- */
  const cmpRow = (label, a, b) => `<tr><td class="l">${label}</td><td class="v mine" style="color:var(--home)">${a}</td><td class="v theirs">${b}</td></tr>`;
  const code = (name) => name.replace(/[^A-Za-z ]/g, "").split(" ").map((w, i, a) => (a.length > 1 ? w[0] : w.slice(0, 3))).join("").slice(0, 3).toUpperCase();
  const mmss = (t) => Math.floor(t / 60) + ":" + String(Math.floor(t % 60)).padStart(2, "0");

  function renderScore() {
    const m = match();
    const gh = m.goals.filter((g) => g[0] <= st.t && g[1] === 0).length;
    const ga = m.goals.filter((g) => g[0] <= st.t && g[1] === 1).length;
    const key = st.mi + ":" + gh + ":" + ga;
    if (key === scoreKey) return;
    scoreKey = key;
    els.score.innerHTML =
      `<div class="team"><span class="dot" style="background:var(--home)"></span>${TEAMS[m.h]}<span class="tag">home</span></div>` +
      `<div class="goals">${gh}:${ga}</div>` +
      `<div class="team away">${TEAMS[m.a]}<span class="dot" style="background:var(--away);margin:0 0 0 6px"></span><span class="tag">away</span></div>`;
  }

  function renderReadout() {
    const m = match(), { t0, t1 } = graphs;
    const ch = count("h", t0, t1), ca = count("a", t0, t1);
    const head = `<tr><td class="l"></td><td class="v mine" style="color:var(--home)">${code(TEAMS[m.h])}</td><td class="v theirs">${code(TEAMS[m.a])}</td></tr>`;
    els.cmp.innerHTML = head + cmpRow("Shots", ch.shots, ca.shots) +
      (META.has_xg === false ? "" : cmpRow("xG", ch.xg.toFixed(2), ca.xg.toFixed(2))) +
      cmpRow("Passes in network", graphs.h.passes, graphs.a.passes);
    const th = graphs.h.an ? graphs.h.an.team : null, ta = graphs.a.an ? graphs.a.an.team : null;
    const row = (label, key, fn) => cmpRow(label, th ? fn(th[key]) : "n/a", ta ? fn(ta[key]) : "n/a");
    els.net.innerHTML = head +
      row("Density", "density", (x) => x.toFixed(2)) + row("Reciprocity", "reciprocity", (x) => x.toFixed(2)) +
      row("PageRank spread", "pagerankEntropy", (x) => x.toFixed(2)) +
      row("Top 3 PageRank share", "top3Pagerank", (x) => x.toFixed(2)) +
      row("Clustering", "clusteringMean", (x) => x.toFixed(2)) +
      row("Max betweenness", "betweennessMax", (x) => x.toFixed(2));
  }

  function actionText(i) {
    const e = P.e, k = P.kind[i], len = Math.round(Math.hypot(e.x1[i] - e.x0[i], e.y1[i] - e.y0[i]));
    const a = App.shortName(PL[e.f[i]]);
    if (k === 0) return `<b>${a}</b> passes to <b>${App.shortName(PL[e.r[i]])}</b> <span>${len} m</span>`;
    if (k === 1) return `<b>${a}</b> pass goes astray <span>${len} m</span>`;
    if (k === 2) return `<b>${a}</b> carries the ball <span>${len} m</span>`;
    const s = match().shots.find((z) => Math.abs(z[0] - P.T[i]) < 3 && z[1] === P.side[i]);
    if (META.has_xg === false) return P.goal[i] ? `<b>${a}</b> scores` : `<b>${a}</b> shoots`;
    return P.goal[i] ? `<b>${a}</b> scores <span>xG ${s ? s[2].toFixed(2) : ""}</span>` : `<b>${a}</b> shoots <span>xG ${s ? s[2].toFixed(2) : ""}</span>`;
  }
  function renderFeed() {
    const j = slotAt(st.t), key = st.mi + ":" + j + ":" + st.side;
    if (key === feedKey) return;
    feedKey = key;
    const rows = [];
    for (let q = j; q >= Math.max(0, j - 7); q--) {
      const i = P.B[q], s = sideOf(P.side[i]);
      rows.push(`<li class="${q === j ? "now" : ""}"><i style="background:${color(s)}"></i><em>${mmss(P.T[i])}</em><p>${actionText(i)}</p></li>`);
    }
    els.feed.innerHTML = rows.join("");
    if (j >= 0) {
      const s = sideOf(P.side[P.B[j]]);
      els.poss.innerHTML = `<i style="background:${color(s)}"></i>${TEAMS[s === "h" ? match().h : match().a]} on the ball`;
    } else els.poss.textContent = TXT.start_pill || "Kick off";
  }
  function renderClock() {
    renderScore();
    const pb = match().pb || [];
    const lab = META.period_labels ? META.period_labels[pb.filter((b) => st.t >= b).length] + "  " : "";
    const txt = `${lab}${mmss(st.t)} of ${mmss(match().end)}`;
    if (txt !== clockKey) { clockKey = txt; els.clock.textContent = txt; }
  }

  /* ---------- explanations ---------- */
  const HOW = {
    live: "Each colored dot is a player, placed where the match log last saw him and sliding to where he next acts, so positions are estimates between touches. The white ball follows every logged pass, carry and shot. The line grows with the ball; a dashed line with a cross is a pass that missed. Fading dots have not been involved for a while.",
    net: "Dots are players, placed by the Layout setting: assigned spots from the lineup, a blend of those and where he actually touched the ball, or his actual average position. A line is every pass between two players. Watch a pulse travel along a link: when it lands, the line gets thicker. Dot size shows the measure you pick, which is recomputed after every pass.",
  };
  const LEGEND = {
    live: `<span><i class="lg dot"></i>Player</span><span><i class="lg ring"></i>Opponent</span><span><i class="lg ball"></i>Ball</span><span><i class="lg ln"></i>Pass</span><span><i class="lg dash"></i>Missed pass</span><span><i class="lg dots"></i>Carry</span>`,
    net: `<span><i class="lg dot"></i>Player, sized by measure</span><span><i class="lg ln"></i>Line width = passes so far</span><span><i class="lg ball"></i>Pass in flight</span>`,
  };
  Object.assign(HOW, TXT.how || {});
  Object.assign(LEGEND, TXT.legend || {});
  function setView(v) {
    st.view = v;
    for (const n of document.querySelectorAll("[data-for]")) n.hidden = n.dataset.for !== v;
    els.how.textContent = HOW[v];
    els.legend.innerHTML = LEGEND[v];
    refresh(true); draw();
  }

  /* ---------- controls ---------- */
  function fillMatches() {
    const sel = els.match; sel.innerHTML = "";
    M.forEach((m, i) => {
      if (st.team !== "all" && TEAMS[m.h] !== st.team && TEAMS[m.a] !== st.team) return;
      sel.append(App.el("option", { value: i, text: `${f.date(m.date)}  ${TEAMS[m.h]} ${m.hs}:${m.as} ${TEAMS[m.a]}` }));
    });
    sel.value = String(st.mi);
    if (sel.value !== String(st.mi) && sel.options.length) { st.mi = +sel.options[0].value; sel.value = String(st.mi); }
  }
  function fillSides() {
    const m = match(), seg = els.sideSeg;
    seg.innerHTML = "";
    for (const [v, idx] of [["h", m.h], ["a", m.a]]) {
      const b = App.el("button", { "data-v": v, "aria-pressed": String(st.side === v), text: TEAMS[idx], title: TEAMS[idx] });
      b.style.borderBottom = `3px solid ${color(v)}`;
      seg.append(b);
    }
  }
  function selectMatch(i) {
    st.mi = i; P = prep(i);
    const g = match().goals.map((z) => z[0]);
    st.t = g.length ? Math.max(0, Math.min(...g) - 25) : 600;
    st.playing = false; st.until = null; updatePlay();
    fillSides(); nodes = new Map(); feedKey = ""; scoreKey = "";
    refresh(true); draw();
    els.tl.setAttribute("aria-valuemax", "100");
  }
  function updatePlay() {
    $("#playIcon").setAttribute("d", st.playing ? "M5 3.5h3.5v13H5zM11.5 3.5H15v13h-3.5z" : "M6 3.5v13l11-6.5z");
  }
  function frame(ts) {
    const dt = Math.min(0.05, (ts - last) / 1000 || 0); last = ts;
    if (App.current === "networks" && graphs) {
      if (st.playing) {
        if (stepping && st.rate.type === "rt") { const keep = st.rate; st.rate = { type: "pbp", v: 1 }; advance(dt); st.rate = keep; } else advance(dt);
        if (!st.playing) stepping = false;
      }
      refresh(false);
      const k = 1 - Math.exp(-dt * 9);
      for (const nd of nodes.values()) {
        nd.r += (nd.tr - nd.r) * k; nd.a += (nd.ta - nd.a) * k;
        if (nd.tx !== undefined) { nd.x += (nd.tx - nd.x) * k; nd.y += (nd.ty - nd.y) * k; }
      }
      for (const [id, nd] of nodes) if (nd.ta === 0 && nd.a < 0.02) nodes.delete(id);
      draw();
    }
    requestAnimationFrame(frame);
  }

  function showTip(ev) {
    const r = els.canvas.getBoundingClientRect(), px = ev.clientX - r.left, py = ev.clientY - r.top;
    let best = null, bd = 1e9;
    for (const h of hits) { const d = Math.hypot(h.x - px, h.y - py); if (d < Math.max(h.r + 5, 13) && d < bd) { best = h; bd = d; } }
    hover = best ? best.pid : null;
    if (!best) { els.tip.hidden = true; return; }
    const g = graphs[st.side], i = g.ids.indexOf(best.pid), an = g.an;
    let html = `<b>${PL[best.pid]}</b>`;
    if (!best.mine) {
      html += `<div class="row"><span>Position</span><span>estimated</span></div><div class="row"><span>Last action</span><span>${Math.round(best.age)} s ago</span></div>`;
    } else if (i >= 0 && an) {
      const rank = (arr) => 1 + arr.filter((v) => v > arr[i] + 1e-12).length;
      html += `<div class="row"><span>Passes made</span><span>${an.outStrength[i]}</span></div>` +
        `<div class="row"><span>Passes received</span><span>${an.inStrength[i]}</span></div>` +
        `<div class="row"><span>PageRank</span><span>${f.pct(an.pagerank[i])} (rank ${rank(an.pagerank)})</span></div>` +
        `<div class="row"><span>Betweenness</span><span>${an.betweenness[i].toFixed(3)} (rank ${rank(an.betweenness)})</span></div>` +
        `<div class="row"><span>Hub / authority</span><span>${an.hub[i].toFixed(2)} / ${an.authority[i].toFixed(2)}</span></div>` +
        `<div class="row"><span>Clustering</span><span>${an.clustering[i].toFixed(2)}</span></div>`;
    } else html += `<div class="row"><span>No completed passes yet</span><span></span></div>`;
    els.tip.innerHTML = html;
    els.tip.hidden = false;
    const wrap = els.canvas.parentElement.getBoundingClientRect();
    els.tip.style.left = Math.min(px + 14, wrap.width - 250) + "px";
    els.tip.style.top = Math.max(6, py - 20) + "px";
  }

  function init() {
    Object.assign(els, {
      canvas: $("#netCanvas"), tl: $("#tlCanvas"), tip: $("#netTip"), team: $("#teamSel"), match: $("#matchSel"),
      sideSeg: $("#sideSeg"), score: $("#score"), cmp: $("#cmpTable"), net: $("#netTable"), clock: $("#clock"),
      feed: $("#feed"), poss: $("#poss"), how: $("#how"), legend: $("#legend") });
    els.team.append(App.el("option", { value: "all", text: "All teams" }));
    for (const t of TEAMS) els.team.append(App.el("option", { value: t, text: t }));
    st.mi = Math.max(0, M.findIndex((m) => m.id === "3754078"));
    fillMatches();
    els.team.addEventListener("change", () => { st.team = els.team.value; fillMatches(); selectMatch(+els.match.value); });
    els.match.addEventListener("change", () => selectMatch(+els.match.value));
    App.seg(els.sideSeg, (v) => { st.side = v; nodes = new Map(); feedKey = ""; refresh(true); });
    App.seg($("#viewSeg"), (v) => setView(v));
    App.seg($("#layoutSeg"), (v) => { st.layout = v; refresh(true); });
    App.seg($("#scopeSeg"), (v) => { st.open = v === "open"; refresh(true); });
    App.seg($("#modeSeg"), (v) => { st.mode = v; refresh(true); });
    $("#metricSel").addEventListener("change", (e) => { st.metric = e.target.value; syncNodes(); });
    $("#minW").addEventListener("input", (e) => { st.minW = +e.target.value; $("#minWOut").textContent = e.target.value; });
    $("#opp").addEventListener("change", (e) => { st.opp = e.target.checked; });
    $("#speed").addEventListener("change", (e) => {
      const [type, v] = e.target.value.split(":"); st.rate = { type, v: +v };
    });
    $("#play").addEventListener("click", () => {
      if (!st.playing && st.t >= match().end - 1) st.t = 0;
      stepping = false; st.until = null; st.playing = !st.playing; updatePlay();
    });
    $("#stepBack").addEventListener("click", () => stepAction(-1));
    $("#stepFwd").addEventListener("click", () => stepAction(1));
    let drag = false;
    els.tl.addEventListener("pointerdown", (e) => { drag = true; els.tl.setPointerCapture(e.pointerId); st.t = tlTime(e); st.playing = false; st.until = null; updatePlay(); });
    els.tl.addEventListener("pointermove", (e) => { if (drag) st.t = tlTime(e); });
    els.tl.addEventListener("pointerup", () => { drag = false; });
    els.tl.addEventListener("keydown", (e) => {
      const step = e.shiftKey ? 300 : 60;
      if (e.key === "ArrowLeft") st.t = Math.max(0, st.t - step);
      else if (e.key === "ArrowRight") st.t = Math.min(match().end, st.t + step);
      else if (e.key === "Home") st.t = 0; else if (e.key === "End") st.t = match().end; else return;
      e.preventDefault();
    });
    els.canvas.addEventListener("pointermove", showTip);
    els.canvas.addEventListener("pointerleave", () => { hover = null; els.tip.hidden = true; });
    window.addEventListener("keydown", (e) => {
      if (App.current !== "networks" || /SELECT|INPUT|BUTTON/.test(document.activeElement.tagName)) return;
      if (e.code === "Space") { e.preventDefault(); $("#play").click(); }
      else if (e.key === ",") stepAction(-1); else if (e.key === ".") stepAction(1);
    });
    selectMatch(st.mi);
    setView("live");
    requestAnimationFrame(frame);
  }

  App.views.networks = { init, draw, show() { if (P) { refresh(true); draw(); } } };
})();
