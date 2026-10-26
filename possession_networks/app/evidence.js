/* Evidence view: the step 8 model comparison as a forest plot, a picture of which minutes feed
   each test, and a binned look at a single feature against shot adjusted goals and xG.
   Wording, verdict rule and sentences live in evidence_text.js. This file draws and wires them.
   No statistic is computed here except the per window correlation and bins the explorer always had. */
(function () {
  "use strict";
  const App = window.App, $ = App.$, D = App.data, E = D.evidence, T = window.EvidenceText, esc = App.esc;
  const st = { target: "gd", base: "corsi", win: "full", feat: "pagerank_entropy_norm", bins: 8 };

  const STYLE = { net: ["var(--home)", "circle"], xt: ["var(--away)", "square"], both: ["var(--good)", "diamond"] };
  const WINS = T.WINDOWS, FEATS = T.FEATS;
  const rowsFor = () => E.comparisons.filter((c) => c.target === st.target && c.baseline === st.base);
  const tgt = () => T.TARGETS[st.target].phrase;
  const basePhrase = () => T.BASES[st.base].phrase;

  function marker(kind, x, y, color, title) {
    const t = title ? `<title>${esc(title)}</title>` : "";
    if (kind === "circle") return `<circle cx="${x}" cy="${y}" r="4.5" fill="${color}" stroke="var(--surface)" stroke-width="1.5">${t}</circle>`;
    if (kind === "square") return `<rect x="${x - 4}" y="${y - 4}" width="8" height="8" fill="${color}" stroke="var(--surface)" stroke-width="1.5">${t}</rect>`;
    return `<path d="M${x} ${y - 5.5}L${x + 5.5} ${y}L${x} ${y + 5.5}L${x - 5.5} ${y}Z" fill="${color}" stroke="var(--surface)" stroke-width="1.5">${t}</path>`;
  }
  const miniMarker = (shape, color) => `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">${marker(shape, 7, 7, color, "")}</svg>`;

  /* ---------- forest ---------- */
  function renderForest() {
    const W = 920, left = 290, right = 165, top = 34, hh = 30, rh = 46;
    const all = rowsFor();
    const lo = Math.min(-0.04, ...all.map((c) => c.ci_low)), hi = Math.max(0.1, ...all.map((c) => c.ci_high));
    const x = (v) => left + ((v - lo) / (hi - lo)) * (W - left - right);
    let yy = top;
    const lay = T.ROWS.map((r) => { const h = r.length === 1 ? hh : rh; const o = { y: yy, h }; yy += h; return o; });
    const H = yy + 34, xv = W - right + 10;
    let anyEdge = false;

    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Forest plot of the change in share explained for every setting. The same numbers are in the table below the chart.">`;
    const step = hi - lo > 0.25 ? 0.05 : 0.02;
    for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + 1e-9; k++) {
      const v = k * step;
      s += `<line x1="${x(v)}" x2="${x(v)}" y1="${top - 8}" y2="${H - 28}" stroke="var(--line)"/><text x="${x(v)}" y="${H - 12}" text-anchor="middle">${T.plain(Math.round(v * 1000) / 1000, 2)}</text>`;
    }
    s += `<line x1="${x(0)}" x2="${x(0)}" y1="${top - 8}" y2="${H - 28}" stroke="var(--muted)" stroke-width="1.4"/>`;
    s += `<text x="${x(0) - 6}" y="16" text-anchor="end">worse</text><text x="${x(0) + 6}" y="16">better</text>`;
    s += `<text class="strong" x="${xv + 14}" y="16">Change</text><text class="strong" x="${xv + 62}" y="16">Verdict</text>`;

    T.ROWS.forEach((r, i) => {
      const { y, h } = lay[i], mid = y + h / 2;
      if (r.length === 1) { s += `<text class="hdr" x="0" y="${mid + 4}">${esc(r[0])}</text>`; return; }
      s += `<line x1="0" x2="${W}" y1="${y}" y2="${y}" stroke="var(--line)" opacity=".6"/>`;
      s += `<text class="strong" x="12" y="${mid - 1}">${esc(r[2])}</text><text class="sub" x="12" y="${mid + 12}">${esc(r[3])}</text>`;
      T.KINDS.forEach((kd, k) => {
        const d = T.find(E.comparisons, r[0], r[1], st.target, st.base, kd.key);
        if (!d) return;
        const [color, shape] = STYLE[kd.key], v = T.verdictOf(d), py = mid + (k - 1) * 12;
        if (v.edge) anyEdge = true;
        const tip = `${kd.name}${kd.tag ? " (" + kd.tag + ")" : ""}: change in share explained ${T.signed(d.delta_r2)} (95% range ${T.signed(d.ci_low)} to ${T.signed(d.ci_high)}). ` +
          `Share explained goes from ${T.plain(d.r2_base)} to ${T.plain(d.r2_new)}. ${v.label}${v.edge ? ", borderline" : ""}.`;
        s += `<line x1="${x(d.ci_low)}" x2="${x(d.ci_high)}" y1="${py}" y2="${py}" stroke="${color}" stroke-width="2" stroke-linecap="round"/>` + marker(shape, x(d.delta_r2), py, color, tip);
        s += marker(shape, xv + 4, py, color, "") +
          `<text class="vnum" x="${xv + 14}" y="${py + 4}">${T.signed(d.delta_r2)}</text>` +
          `<text class="v v-${v.key}" x="${xv + 62}" y="${py + 4}">${v.label}${v.edge ? "*" : ""}</text>`;
      });
    });
    s += "</svg>";
    $("#forest").innerHTML = s;
    $("#forestEdge").hidden = !anyEdge;
    $("#forestTakeaway").textContent = T.forestTakeaway(E.comparisons, st.target, st.base);
    $("#forestLegend").innerHTML = T.KINDS.map((kd) =>
      `<span class="lg2">${miniMarker(STYLE[kd.key][1], STYLE[kd.key][0])}${App.term(kd.term, kd.name)}${kd.tag ? `<small>${esc(kd.tag)}</small>` : ""}</span>`).join("");
    $("#forestCap").innerHTML = App.rich(`Each mark is the change in {{r2|R2}}, the share of ${tgt()} explained, when an {{extension|extension}} is added to the {{baseline|baseline}}. ` +
      "Right of zero is better, and a line that crosses zero is not clearly better. " +
      "Method: {{ridge|ridge regression}}, scored {{oof|out of fold}} with {{gcv|grouped cross validation}}, intervals from a {{boot|bootstrap}} over matches.");
    renderTable();
  }

  function renderTable() {
    const cell = (d) => {
      if (!d) return "<td></td>";
      const v = T.verdictOf(d);
      return `<td><span class="num">${T.signed(d.delta_r2)}</span><span class="rng">${T.signed(d.ci_low)} to ${T.signed(d.ci_high)}</span>` +
        `<span class="badge ${v.key}">${v.label}${v.edge ? " (borderline)" : ""}</span></td>`;
    };
    let h = `<caption class="hint">Change in R2 (share of ${esc(tgt())} explained) with its 95% range. Baseline here is ${esc(basePhrase())}.</caption>` +
      `<thead><tr><th scope="col">Setting</th><th scope="col">Baseline share explained</th>${T.KINDS.map((k) => `<th scope="col">${esc(k.name)}</th>`).join("")}</tr></thead><tbody>`;
    for (const r of T.ROWS) {
      if (r.length === 1) { h += `<tr class="grp"><th colspan="5" scope="colgroup">${esc(r[0])}</th></tr>`; continue; }
      const ds = T.KINDS.map((k) => T.find(E.comparisons, r[0], r[1], st.target, st.base, k.key));
      const b = ds.find(Boolean);
      h += `<tr><th scope="row">${esc(r[2])}<small>${esc(r[3])}</small></th><td class="num">${b ? T.plain(b.r2_base) : ""}</td>${ds.map(cell).join("")}</tr>`;
    }
    $("#forestTable").innerHTML = h + "</tbody>";
  }

  /* ---------- windows ---------- */
  const featDesc = (u) => u === "tied" ? "only the minutes while the score is level" :
    u[0] === 0 && u[1] === 1 ? "the whole match" : u[1] === 0.5 ? "the first half" : "the second half";

  function renderWindow() {
    const w = WINS[st.win], W = 920, left = 150, right = 20, x = (u) => left + u * (W - left - right), H = 120;
    const band = (u, lane, color, label) => {
      const y = 22 + lane * 38;
      let s = `<text x="0" y="${y + 17}" class="strong">${label}</text>`;
      if (u === "tied") {
        s += `<rect x="${x(0)}" y="${y}" width="${x(1) - x(0)}" height="24" rx="4" fill="url(#hatch)" stroke="${color}" stroke-dasharray="3 3"/>` +
             `<text x="${x(0.5)}" y="${y + 16}" text-anchor="middle" class="strong">only while the score is level</text>`;
      } else {
        s += `<rect x="${x(u[0])}" y="${y}" width="${x(u[1]) - x(u[0])}" height="24" rx="4" fill="${color}" opacity=".85"/>`;
      }
      return s;
    };
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Features come from ${featDesc(w.feat)}. Goals are counted from ${featDesc(w.goal)}."><defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="none"/><line x1="0" y1="0" x2="0" y2="7" stroke="var(--home)" stroke-width="3" opacity=".5"/></pattern></defs>`;
    s += `<line x1="${x(0.5)}" x2="${x(0.5)}" y1="12" y2="${H - 28}" stroke="var(--muted)" stroke-dasharray="3 3"/>`;
    s += band(w.feat, 0, "var(--home)", "Features from") + band(w.goal, 1, "var(--away)", "Goals counted from");
    s += `<text x="${x(0)}" y="${H - 10}">kickoff</text><text x="${x(0.5)}" y="${H - 10}" text-anchor="middle">half time</text><text x="${x(1)}" y="${H - 10}" text-anchor="end">full time</text></svg>`;
    $("#winDiagram").innerHTML = s + `<p class="hint" style="margin-top:6px">${esc(w.text)}</p>`;

    $("#winTakeaway").textContent = T.windowTakeaway(E.comparisons, st.win, st.target, st.base);

    const ds = T.KINDS.map((k) => T.winRow(E.comparisons, st.win, st.target, st.base, k.key));
    const base = ds.find(Boolean) ? ds.find(Boolean).r2_base : NaN;
    $("#winResult").innerHTML = T.KINDS.map((kd, i) => {
      const d = ds[i];
      if (!d) return "";
      const v = T.verdictOf(d);
      return `<div class="stat"><span class="k">${App.term(kd.term, kd.name)} added to ${esc(basePhrase())}</span>` +
        `<span class="big" style="color:${v.key === "gain" ? "var(--good)" : v.key === "loss" ? "var(--away)" : "var(--ink)"}">${T.signed(d.delta_r2)}</span>` +
        `<span class="badge ${v.key}">${v.label}${v.edge ? " (borderline)" : ""}</span>` +
        `<span class="ci">${App.term("boot", "95% range")} ${T.signed(d.ci_low)} to ${T.signed(d.ci_high)}</span>` +
        `<span class="ci">${App.term("r2", "Share explained")} ${T.plain(d.r2_base)} to ${T.plain(d.r2_new)}</span></div>`;
    }).join("") + `<p class="hint" style="grid-column:1/-1">${App.rich(`The baseline {{r2|share explained}} here is ${T.plain(base)}. Each change is scored {{oof|out of fold}}, on matches the model had not seen, so a bigger number means better predictions on new matches.`)}</p>`;

    renderStory();
    for (const b of $("#winSeg").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.v === st.win));
  }

  function renderStory() {
    const s = T.story(E.comparisons, st.target, st.base), el = $("#winStory");
    if (!s) { el.innerHTML = ""; return; }
    const cur = WINS[st.win].group;
    el.innerHTML =
      `<li${cur === 1 ? ' aria-current="step"' : ""}><span class="stepno">1</span><div class="body"><h4>${esc(s.one.title)}</h4><p>${esc(s.one.text)}</p>` +
        `<button type="button" class="btn ghost" data-win="full">Show the whole match test</button></div></li>` +
      `<li${cur === 2 ? ' aria-current="step"' : ""}><span class="stepno">2</span><div class="body"><h4>${esc(s.two.title)}</h4>${s.two.lines.map((l) => `<p>${esc(l)}</p>`).join("")}` +
        `<p class="hint">${esc(s.two.power)}</p><button type="button" class="btn ghost" data-win="h1_to_h2">Show half 1 to half 2</button></div></li>` +
      `<li class="reading"><span class="stepno">3</span><div class="body"><h4>${esc(s.three.title)}</h4><p>${esc(s.three.text)}</p></div></li>`;
  }

  /* ---------- relationship ---------- */
  function pearson(a, b) {
    const n = a.length; let ma = 0, mb = 0;
    for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; } ma /= n; mb /= n;
    let sab = 0, saa = 0, sbb = 0;
    for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; }
    return sab / Math.sqrt(saa * sbb);
  }
  function binned(win, feat, target, nb) {
    const wdat = E.windows[win], xs = wdat.feats[feat], ys = wdat[target];
    const pts = xs.map((x, i) => [x, ys[i]]).filter((p) => p[0] !== null).sort((a, b) => a[0] - b[0]);
    const out = [];
    for (let b = 0; b < nb; b++) {
      const seg = pts.slice(Math.floor((b * pts.length) / nb), Math.floor(((b + 1) * pts.length) / nb));
      const mx = seg.reduce((s, p) => s + p[0], 0) / seg.length, my = seg.reduce((s, p) => s + p[1], 0) / seg.length;
      const sd = Math.sqrt(seg.reduce((s, p) => s + (p[1] - my) ** 2, 0) / Math.max(1, seg.length - 1));
      out.push({ x: mx, y: my, se: sd / Math.sqrt(seg.length), n: seg.length });
    }
    return out;
  }
  function renderRel() {
    const W = 920, H = 330, l = 56, r = 20, t = 18, b = 44;
    const g = binned(st.win, st.feat, "res_gd", st.bins), xg = binned(st.win, st.feat, "res_xgd", st.bins);
    const xs = [...g, ...xg].map((p) => p.x), x0 = Math.min(...xs), x1 = Math.max(...xs);
    const ys = [...g, ...xg].flatMap((p) => [p.y - p.se, p.y + p.se]);
    const m = Math.max(0.3, Math.max(...ys.map(Math.abs))) * 1.1;
    const X = (v) => l + ((v - x0) / (x1 - x0 || 1)) * (W - l - r), Y = (v) => t + (1 - (v + m) / (2 * m)) * (H - t - b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Goals and xG left over after shots, by group of matches, for ${esc(FEATS[st.feat][0])}">`;
    for (let v = -Math.floor(m * 5) / 5; v <= m; v += 0.2) {
      s += `<line x1="${l}" x2="${W - r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${l - 8}" y="${Y(v) + 4}" text-anchor="end">${Math.abs(v) < 0.05 ? "0.0" : (v < 0 ? T.MINUS : "") + Math.abs(v).toFixed(1)}</text>`;
    }
    s += `<line x1="${l}" x2="${W - r}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--muted)" stroke-width="1.4"/>`;
    const series = [[g, "var(--home)", "Goals left over after shots", "circle"], [xg, "var(--away)", "xG left over after shots", "square"]];
    for (const [pts, color, name, shape] of series) {
      s += `<path d="${pts.map((p, i) => (i ? "L" : "M") + X(p.x) + " " + Y(p.y)).join("")}" fill="none" stroke="${color}" stroke-width="2"/>`;
      for (const p of pts) {
        s += `<line x1="${X(p.x)}" x2="${X(p.x)}" y1="${Y(p.y - p.se)}" y2="${Y(p.y + p.se)}" stroke="${color}" stroke-width="1.5" opacity=".6"/>` +
             marker(shape, X(p.x), Y(p.y), color, `${name}: ${p.y >= 0 ? "+" : T.MINUS}${Math.abs(p.y).toFixed(2)} per match (${p.n} matches)`);
      }
    }
    s += `<text x="${(l + W - r) / 2}" y="${H - 8}" text-anchor="middle" class="strong">${esc(FEATS[st.feat][0])}, home minus away (group averages)</text>`;
    s += `<text transform="translate(14 ${(t + H - b) / 2}) rotate(-90)" text-anchor="middle">goals per match left over after shots</text></svg>`;
    $("#relChart").innerHTML = s;

    $("#relLegend").innerHTML =
      `<span class="lg2">${miniMarker("circle", "var(--home)")}${App.term("residual", "Goals left over after shots")}</span>` +
      `<span class="lg2">${miniMarker("square", "var(--away)")}${App.term("xg", "xG")} left over after shots</span>`;
    $("#relFeatNote").textContent = `${FEATS[st.feat][0]}: ${FEATS[st.feat][1]} Home minus away is used, so a positive value means the home side is higher.`;

    const per = Object.keys(WINS).map((k) => {
      const w = E.windows[k], ok = w.feats[st.feat].map((v, i) => [v, w.res_gd[i], w.res_xgd[i]]).filter((p) => p[0] !== null);
      return { k, rg: pearson(ok.map((p) => p[0]), ok.map((p) => p[1])), rx: pearson(ok.map((p) => p[0]), ok.map((p) => p[2])) };
    });
    $("#relCorr").innerHTML = per.map((p) =>
      `<span class="chip"${p.k === st.win ? ' aria-current="true"' : ""}>${esc(WINS[p.k].label)}: goals r <b>${T.signed(p.rg, 2)}</b>, xG r <b>${T.signed(p.rx, 2)}</b></span>`).join("");
    $("#relCorrCap").innerHTML = App.rich("{{corr|Correlation (r)}} of the feature with what is left over after shots, for each choice of minutes. The chart shows the highlighted one, which follows the minutes chosen in the card above.");
    const cur = per.find((p) => p.k === st.win);
    $("#relTakeaway").textContent = T.relTakeaway(st.feat, st.win, cur.rg, cur.rx);

    const n = E.windows[st.win].n;
    $("#relNote").innerHTML =
      `<p>${App.rich(`{{residual|Left over after shots}} means this. For every match we first draw the best straight line from shot difference to the result. What the line misses is the part of the result that shots do not explain. Above zero means more than the shots suggest, below zero means fewer.`)}</p>` +
      "<ul>" + [
        `The straight line is fitted on all ${n} matches at once.`,
        "Any {{xt|xT}} feature here uses zone values fitted on the whole season.",
        "So nothing in this view is held out. It is exploratory, for spotting shapes and ideas, and it is not a test result. The held out results are in the first card.",
      ].map((t) => `<li>${App.rich(t)}</li>`).join("") + "</ul>";
  }

  function renderHow(id, key) {
    const h = T.HOWTO[key];
    $(`#${id} .howbody`).innerHTML = `<ol>${h.steps.map((x) => `<li>${App.rich(x)}</li>`).join("")}</ol><p class="example">${esc(h.example)}</p>`;
  }

  function renderAll() { renderForest(); renderWindow(); renderRel(); }

  function init() {
    $("#topTakeaway").textContent = T.topTakeaway(E.comparisons);
    $("#introText").innerHTML = App.rich(T.INTRO);
    $("#caveats").innerHTML = T.CAVEATS.map((c) => `<li>${esc(c)}</li>`).join("");
    renderHow("howForest", "forest"); renderHow("howWindow", "window"); renderHow("howRel", "rel");

    for (const [k, v] of Object.entries(T.TARGETS)) $("#evTarget").append(App.el("option", { value: k, text: v.option }));
    const base = $("#evBase");
    for (const [k, v] of Object.entries(T.BASES)) base.append(App.el("option", { value: k, text: v.label }));
    const feat = $("#relFeat");
    for (const [k, v] of Object.entries(FEATS)) feat.append(App.el("option", { value: k, text: v[0] }));
    feat.value = st.feat;

    const seg = $("#winSeg");
    for (const grp of [1, 2]) {
      const keys = Object.keys(WINS).filter((k) => WINS[k].group === grp);
      seg.insertAdjacentHTML("beforeend",
        `<div class="winpick-group"><span class="cap"><span class="stepno">${grp}</span>${esc(T.WINDOW_GROUPS[grp])}</span>` +
        `<div class="seg wrap" role="group" aria-label="${esc(T.WINDOW_GROUPS[grp])}">` +
        keys.map((k) => `<button type="button" data-v="${k}" aria-pressed="${k === st.win}" title="${esc(WINS[k].tech)}">${esc(WINS[k].label)}</button>`).join("") +
        "</div></div>");
    }
    $("#evTarget").addEventListener("change", (e) => { st.target = e.target.value; fixBase(); renderAll(); });
    base.addEventListener("change", (e) => { st.base = e.target.value; renderAll(); });
    feat.addEventListener("change", (e) => { st.feat = e.target.value; renderRel(); });
    $("#relBins").addEventListener("input", (e) => { st.bins = +e.target.value; $("#relBinsOut").textContent = e.target.value; renderRel(); });
    App.seg(seg, (v) => { st.win = v; renderWindow(); renderRel(); });
    $("#winStory").addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-win]");
      if (!b) return;
      const w = b.dataset.win;
      st.win = w; renderWindow(); renderRel();
      const again = $(`#winStory button[data-win="${w}"]`);
      if (again) again.focus();
    });
    fixBase(); renderAll();
  }
  function fixBase() {
    const base = $("#evBase");
    for (const o of base.options) o.disabled = st.target === "xgd" && o.value === "corsi_xg";
    if (st.target === "xgd" && st.base === "corsi_xg") { st.base = "corsi"; base.value = "corsi"; }
    base.value = st.base;
  }
  App.views.evidence = { init, draw: renderAll, show: renderAll };
})();
