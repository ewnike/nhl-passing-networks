// Tests the Evidence wording against the real step 8 rows. Run: node app/tests_js/run_evidence_text.js
const fs = require("fs"), path = require("path"), assert = require("assert");
const T = require("../evidence_text.js");
const root = path.resolve(__dirname, "..", "..");

// The same rounding that comparisons_payload applies before the rows reach the app.
const lines = fs.readFileSync(path.join(root, "outputs", "tables", "incremental_comparisons.csv"), "utf8").trim().split("\n");
const head = lines[0].split(",");
const comps = lines.slice(1).map((l) => {
  const o = {}; l.split(",").forEach((v, i) => (o[head[i]] = v));
  for (const k of ["r2_base", "r2_new", "delta_r2", "ci_low", "ci_high"]) o[k] = Math.round(+o[k] * 1e4) / 1e4;
  return o;
});
assert.strictEqual(comps.length, 357);

let checks = 0;
const ok = (c, m) => { assert.ok(c, m); checks++; };
const eq = (a, b, m) => { assert.strictEqual(a, b, m); checks++; };
const strip = (s) => s.replace(/\{\{[a-z0-9]+\|([^}]+)\}\}/g, "$1");

// 1. The verdict depends only on whether the interval excludes zero.
for (const d of comps) {
  const v = T.verdictOf(d);
  eq(v.key, d.ci_low > 0 ? "gain" : d.ci_high < 0 ? "loss" : "none", `${d.axis}/${d.value}`);
  eq(T.verdictOf({ ...d, delta_r2: 99, r2_new: 99 }).key, v.key, "the point estimate must not matter");
}
const get = (axis, value, tgt, base, added) => T.find(comps, axis, value, tgt, base, added);
eq(T.verdictOf(get("primary", "primary", "gd", "corsi", "net")).label, "Clear gain");
eq(T.verdictOf(get("window", "h1_to_h2", "gd", "corsi", "net")).label, "No clear gain");
eq(T.verdictOf(get("window", "h2_to_h2", "xgd", "corsi_sot", "net")).label, "Clear loss");
const tiedBoth = T.verdictOf(get("window", "tied_to_full", "gd", "corsi", "both"));
ok(tiedBoth.key === "gain" && tiedBoth.edge, "interval starts at +0.0002, a borderline gain");
ok(!T.verdictOf(get("primary", "primary", "gd", "corsi", "net")).edge);

// 2. The forest sentence counts match an independent count.
for (const tgt of ["gd", "xgd"]) for (const base of Object.keys(T.BASES)) {
  const rows = comps.filter((c) => c.target === tgt && c.baseline === base);
  if (!rows.length) continue;
  const s = T.forestTakeaway(comps, tgt, base);
  for (const kind of ["net", "xt", "both"]) {
    const n = rows.filter((c) => c.added === kind && c.ci_low > 0).length;
    ok(s.includes(` ${n} `) || s.includes(` ${n},`) || s.includes(` ${n};`) || s.includes(` ${n}.`), `${tgt}/${base}/${kind} count ${n} in: ${s}`);
  }
  ok(s.includes(`of ${rows.filter((c) => c.added === "net").length} settings`));
}
ok(T.forestTakeaway(comps, "gd", "corsi").includes("14 of 17 settings, pass value (xT) in 13, and both together in 15"));

// 3. Every window sentence carries the exact signed numbers of the three rows.
for (const tgt of ["gd", "xgd"]) for (const base of Object.keys(T.BASES)) {
  if (tgt === "xgd" && base === "corsi_xg") continue;
  for (const win of Object.keys(T.WINDOWS)) {
    const s = T.windowTakeaway(comps, win, tgt, base);
    for (const k of ["net", "xt", "both"]) ok(s.includes(T.signed(T.winRow(comps, win, tgt, base, k).delta_r2)), `${win}/${tgt}/${base}/${k}: ${s}`);
    ok(T.story(comps, tgt, base) !== null);
  }
}
ok(T.windowTakeaway(comps, "h1_to_h2", "gd", "corsi").includes("adds no clear gain for goal difference over shots (−0.007)"));
ok(T.lowPowerNote(comps, "gd", "corsi").includes("+0.021") && T.lowPowerNote(comps, "gd", "corsi").includes("0.032"));

// 4. The story keeps its order and its caveat.
const st = T.story(comps, "gd", "corsi");
eq(st.one.title, "Same match: the gain is clear");
eq(st.two.title, "Different minutes: the gain fades");
ok(/consistent with the data, not proven by it/.test(st.three.text) && /does not show that passing structure causes goals/.test(st.three.text));
// If the data stop showing the pattern, step 3 must not claim it.
const altered = comps.map((c) => (c.axis === "window" && c.value === "h1_to_h2" && c.target === "gd" && c.baseline === "corsi" && c.added === "net" ? { ...c, ci_low: 0.05, ci_high: 0.1 } : c));
ok(/untested/.test(T.story(altered, "gd", "corsi").three.text));
ok(T.story(altered, "gd", "corsi").two.title !== "Different minutes: the gain fades");
ok(/^Within the same match/.test(T.topTakeaway(comps)) && /not a forecast/.test(T.topTakeaway(comps)));
ok(!/^Within the same match/.test(T.topTakeaway(altered)));

// 5. Relationship sentence follows the sign of r and stays exploratory.
ok(/fewer goals than their shots predict \(r −0\.23\)/.test(T.relTakeaway("pagerank_entropy_norm", "full", -0.23, -0.14)));
ok(/\(r \+0\.20\)/.test(T.relTakeaway("density", "full", 0.2, 0.2)), "a positive r keeps its plus sign");
ok(/about the goals their shots predict/.test(T.relTakeaway("density", "h1_to_h2", 0.03, -0.05)));
ok(/more chance quality/.test(T.relTakeaway("density", "full", 0.2, 0.2)));
ok(/exploratory/.test(T.relTakeaway("density", "full", 0.2, 0.2)));

// 6. The glossary has every required term and every token points at a real entry.
for (const k of ["r2", "oof", "ridge", "gcv", "boot", "baseline", "extension", "xt", "window", "residual", "score"]) {
  ok(T.GLOSSARY[k] && T.GLOSSARY_ORDER.includes(k), k);
}
for (const k of T.GLOSSARY_ORDER) ok(T.GLOSSARY[k] && T.GLOSSARY[k].short && T.GLOSSARY[k].long, k);
const everyText = [];
const walk = (v) => { if (typeof v === "string") everyText.push(v); else if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === "object") Object.values(v).forEach(walk); };
walk([T.GLOSSARY, T.INTRO, T.CAVEATS, T.HOWTO, T.ROWS, T.WINDOWS, T.WINDOW_GROUPS, T.TARGETS, T.BASES, T.KINDS, T.FEATS, T.VERDICTS]);
for (const s of everyText) for (const m of s.matchAll(/\{\{([a-z0-9]+)\|/g)) ok(T.GLOSSARY[m[1]], `token ${m[1]}`);
for (const k of ["gd", "xgd"]) for (const base of Object.keys(T.BASES)) for (const win of Object.keys(T.WINDOWS)) {
  everyText.push(T.forestTakeaway(comps, k, base), T.windowTakeaway(comps, win, k, base), T.lowPowerNote(comps, k, base));
  const s = T.story(comps, k, base); if (s) walk(s);
}
everyText.push(T.topTakeaway(comps), T.topTakeaway(altered));
for (const f of Object.keys(T.FEATS)) for (const w of Object.keys(T.WINDOWS)) everyText.push(T.relTakeaway(f, w, -0.2, 0.05));

// 7. House rule: no em dash, en dash or hyphen in any text, and no caveat words dropped.
for (const s of everyText) ok(!/[‐-―\-]/.test(strip(s)), `dash in: ${s}`);
const all = everyText.map(strip).join(" ");
for (const must of ["one season", "380 matches", "not a forecast", "low power", "Nothing here shows that passing structure causes goals"]) ok(all.includes(must), must);
ok(!/\b(proves|proved|caused by|because of)\b/i.test(all), "no causal claim wording");

console.log(`ok, ${checks} checks on ${comps.length} real rows and ${everyText.length} strings`);
