/* Zones view: the 12 x 8 zone values, a ball drop animation driven by the real season
   transition counts, and a pass value calculator. */
(function () {
  "use strict";
  const App = window.App, $ = App.$, D = App.data, f = App.fmt;
  const [NX, NY] = D.meta.grid, N = NX * NY;
  const st = { chain: D.meta.primary_chain, layer: "goal", mode: "drop", sel: 5 * NY + 3, from: null, to: null, hover: -1 };
  let tally = { goal: 0, shot: 0, turnover: 0, n: 0 }, balls = [], bursts = [], last = 0, v = null;
  const rand = App.rng(7);
  const els = {};

  const Z = () => D.zones[st.chain];
  const center = (z) => { const ix = Math.floor(z / NY), iy = z % NY; return [(ix + 0.5) * D.meta.pitch[0] / NX - D.meta.pitch[0] / 2, (iy + 0.5) * D.meta.pitch[1] / NY - D.meta.pitch[1] / 2]; };
  const value = (z, layer = st.layer) => (layer === "attempt" ? Z().goal[z] + Z().shot[z] : Z()[layer][z]);

  function step(z) {
    const moves = Z().moves[z];
    let total = 0; for (const [, c] of moves) total += c;
    let r = rand() * total;
    for (const [dst, c] of moves) { r -= c; if (r <= 0) return dst; }
    return moves[moves.length - 1][0];
  }
  const OUT = ["goal", "shot", "turnover"];

  function simulate(n) {
    for (let k = 0; k < n; k++) {
      let z = st.sel, guard = 0;
      while (z < N && guard++ < 500) z = step(z);
      tally[OUT[z - N] || "turnover"]++; tally.n++;
    }
    renderTally();
  }
  function drop(n) {
    for (let k = 0; k < n; k++) balls.push({ z: st.sel, next: null, u: 1, delay: k * 0.18, hops: 0 });
  }

  function draw() {
    const { ctx, w, h } = App.fit(els.canvas);
    v = App.drawPitch(ctx, w, h);
    const L = v.L, W = v.W, cw = L / NX * v.s, ch = W / NY * v.s;
    const base = App.css("--home");
    const vals = Array.from({ length: N }, (_, z) => value(z)), mx = Math.max(...vals);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "11px " + getComputedStyle(document.body).fontFamily;
    for (let z = 0; z < N; z++) {
      const [x, y] = center(z), px = v.X(x) - cw / 2, py = v.Y(y) - ch / 2;
      ctx.fillStyle = App.rgba(base, 0.05 + 0.82 * Math.pow(vals[z] / mx, 0.8));
      ctx.fillRect(px + 0.5, py + 0.5, cw - 1, ch - 1);
      if (cw > 46) {
        ctx.fillStyle = vals[z] / mx > 0.55 ? "#fff" : App.css("--muted");
        ctx.fillText((vals[z] * 100).toFixed(vals[z] < 0.1 ? 1 : 0) + "%", px + cw / 2, py + ch / 2);
      }
    }
    outline(ctx, st.sel, App.css("--ink"), 2, cw, ch);
    if (st.mode === "pass" && st.from !== null) outline(ctx, st.from, App.css("--away"), 2.5, cw, ch);
    if (st.mode === "pass" && st.to !== null) outline(ctx, st.to, App.css("--good"), 2.5, cw, ch);
    if (st.hover >= 0) outline(ctx, st.hover, App.css("--muted"), 1.2, cw, ch);
    if (st.mode === "pass" && st.from !== null && st.to !== null) arrow(ctx, st.from, st.to);
    for (const b of balls) drawBall(ctx, b);
    for (const bu of bursts) drawBurst(ctx, bu);
  }
  function outline(ctx, z, color, lw, cw, ch) {
    const [x, y] = center(z);
    ctx.strokeStyle = color; ctx.lineWidth = lw;
    ctx.strokeRect(v.X(x) - cw / 2 + 1, v.Y(y) - ch / 2 + 1, cw - 2, ch - 2);
  }
  function arrow(ctx, a, b) {
    const [ax, ay] = center(a), [bx, by] = center(b);
    const x0 = v.X(ax), y0 = v.Y(ay), x1 = v.X(bx), y1 = v.Y(by), ang = Math.atan2(y1 - y0, x1 - x0);
    ctx.strokeStyle = App.css("--ink"); ctx.fillStyle = App.css("--ink"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 - 10 * Math.cos(ang - 0.4), y1 - 10 * Math.sin(ang - 0.4));
    ctx.lineTo(x1 - 10 * Math.cos(ang + 0.4), y1 - 10 * Math.sin(ang + 0.4)); ctx.closePath(); ctx.fill();
  }
  function ballPos(b) {
    const [x0, y0] = center(b.z), [x1, y1] = b.next === null ? [x0, y0] : center(b.next);
    const u = b.u, e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
    return [v.X(x0 + (x1 - x0) * e), v.Y(y0 + (y1 - y0) * e) - Math.sin(Math.PI * e) * 10];
  }
  function drawBall(ctx, b) {
    if (b.delay > 0) return;
    const [px, py] = ballPos(b);
    ctx.fillStyle = App.css("--ink"); ctx.strokeStyle = App.css("--surface"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
  function drawBurst(ctx, b) {
    const k = b.age / 0.9;
    ctx.globalAlpha = Math.max(0, 1 - k);
    const col = b.kind === "goal" ? App.css("--good") : b.kind === "shot" ? App.css("--home") : App.css("--away");
    ctx.strokeStyle = col; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(b.x, b.y, 6 + 26 * k, 0, Math.PI * 2); ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function frame(ts) {
    const dt = Math.min(0.05, (ts - last) / 1000 || 0); last = ts;
    if (App.current === "zones") {
      for (const b of balls) {
        if (b.delay > 0) { b.delay -= dt; continue; }
        b.u += dt / 0.3;
        if (b.u >= 1) {
          if (b.next !== null) { b.z = b.next; }
          const nxt = step(b.z);
          if (nxt >= N) { b.done = nxt; } else { b.next = nxt; b.u = 0; b.hops++; }
        }
      }
      for (const b of balls) if (b.done !== undefined && !b.counted) {
        b.counted = true;
        const kind = OUT[b.done - N], [px, py] = ballPos(b);
        tally[kind]++; tally.n++;
        bursts.push({ x: px, y: py, kind, age: 0 });
        renderTally();
      }
      balls = balls.filter((b) => b.done === undefined);
      for (const bu of bursts) bu.age += dt;
      bursts = bursts.filter((bu) => bu.age < 0.9);
      if (v) draw();
    }
    requestAnimationFrame(frame);
  }

  function renderTally() {
    const z = st.sel, exact = { goal: Z().goal[z], shot: Z().shot[z], turnover: Z().turnover[z] };
    const names = { goal: "Goal", shot: "Shot", turnover: "Turnover" };
    els.tally.innerHTML = OUT.map((k) => {
      const share = tally.n ? tally[k] / tally.n : 0;
      return `<div class="tallybar"><span>${names[k]}</span><div class="track"><div class="fill" style="width:${share * 100}%"></div>` +
        `<div class="mk" style="left:${exact[k] * 100}%" title="Exact value ${f.pct(exact[k])}"></div></div><span class="pct">${f.pct(share, 0)}</span></div>`;
    }).join("") + `<p class="hint">${tally.n} balls dropped from the outlined zone. The black tick is the exact chain answer (${f.pct(exact.goal)} goal, ${f.pct(exact.shot)} shot, ${f.pct(exact.turnover)} turnover).</p>`;
  }
  function renderPassValue() {
    if (st.from === null || st.to === null) {
      els.pass.innerHTML = "Choose Value a pass, then click a start zone and an end zone."; return;
    }
    const dg = value(st.to, "goal") - value(st.from, "goal"), da = value(st.to, "attempt") - value(st.from, "attempt");
    els.pass.innerHTML = `A completed pass between these zones changes the chance of a goal by <b>${dg >= 0 ? "+" : "−"}${Math.abs(dg * 100).toFixed(2)} points</b> ` +
      `and the chance of a shot by <b>${da >= 0 ? "+" : "−"}${Math.abs(da * 100).toFixed(1)} points</b>. ` +
      `A failed pass from the start zone costs <b>−${(value(st.from, "goal") * 100).toFixed(2)} points</b> of goal chance.`;
  }
  function renderLeaders() {
    els.leaders.innerHTML = (D.leaders[st.chain] || []).map((p) => `<li>${p.name}<span>${p.xt.toFixed(3)}</span></li>`).join("");
  }
  function hint() {
    els.hint.textContent = st.mode === "drop"
      ? "Click a zone to set the start, then drop balls. Each ball hops the way real possessions did."
      : "Click a start zone, then an end zone, to see what a pass between them is worth.";
  }

  function zoneAt(ev) {
    const r = els.canvas.getBoundingClientRect();
    const x = v.invX(ev.clientX - r.left), y = v.invY(ev.clientY - r.top), [L, W] = D.meta.pitch;
    if (Math.abs(x) > L / 2 || Math.abs(y) > W / 2) return -1;
    return Math.floor((x + L / 2) / L * NX) * NY + Math.floor((y + W / 2) / W * NY);
  }

  function init() {
    Object.assign(els, { canvas: $("#zoneCanvas"), tip: $("#zoneTip"), tally: $("#tally"), pass: $("#passValue"), leaders: $("#leaders"), hint: $("#zoneHint") });
    const chainSel = $("#chainSel");
    for (const c of D.meta.chains) chainSel.append(App.el("option", { value: c, text: c.replace("_", " ").replace("open", "open play only").replace("all", "all sequences") }));
    chainSel.value = st.chain;
    chainSel.addEventListener("change", (e) => { st.chain = e.target.value; tally = { goal: 0, shot: 0, turnover: 0, n: 0 }; balls = []; renderTally(); renderLeaders(); renderPassValue(); });
    $("#layerSel").addEventListener("change", (e) => { st.layer = e.target.value; });
    App.seg($("#zoneMode"), (m) => { st.mode = m; st.from = st.to = null; renderPassValue(); hint(); });
    $("#drop1").addEventListener("click", () => drop(1));
    $("#drop10").addEventListener("click", () => drop(10));
    $("#drop2000").addEventListener("click", () => simulate(2000));
    $("#clearBalls").addEventListener("click", () => { tally = { goal: 0, shot: 0, turnover: 0, n: 0 }; balls = []; renderTally(); });
    els.canvas.addEventListener("click", (e) => {
      const z = zoneAt(e); if (z < 0) return;
      if (st.mode === "drop") { st.sel = z; tally = { goal: 0, shot: 0, turnover: 0, n: 0 }; renderTally(); }
      else if (st.from === null || st.to !== null) { st.from = z; st.to = null; renderPassValue(); }
      else { st.to = z; renderPassValue(); }
    });
    els.canvas.addEventListener("pointermove", (e) => {
      const z = zoneAt(e); st.hover = z;
      if (z < 0) { els.tip.hidden = true; return; }
      const mv = Z().moves[z]; let tot = 0; for (const [, c] of mv) tot += c;
      const top = mv.filter(([d]) => d < N).sort((a, b) => b[1] - a[1])[0];
      els.tip.innerHTML = `<b>Zone ${z}</b><div class="row"><span>Goal</span><span>${f.pct(Z().goal[z], 2)}</span></div>` +
        `<div class="row"><span>Shot</span><span>${f.pct(Z().shot[z], 1)}</span></div>` +
        `<div class="row"><span>Turnover</span><span>${f.pct(Z().turnover[z], 1)}</span></div>` +
        `<div class="row"><span>Actions started here</span><span>${Z().visits[z].toLocaleString()}</span></div>` +
        (top ? `<div class="row"><span>Most common next zone</span><span>${f.pct(top[1] / tot, 0)}</span></div>` : "");
      const r = els.canvas.getBoundingClientRect();
      els.tip.hidden = false;
      els.tip.style.left = Math.min(e.clientX - r.left + 14, r.width - 250) + "px";
      els.tip.style.top = Math.max(6, e.clientY - r.top - 20) + "px";
    });
    els.canvas.addEventListener("pointerleave", () => { st.hover = -1; els.tip.hidden = true; });
    renderTally(); renderLeaders(); renderPassValue(); hint();
    requestAnimationFrame(frame);
  }
  App.views.zones = { init, draw: () => v && draw(), show() { draw(); } };
})();
