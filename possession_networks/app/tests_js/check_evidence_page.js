// Opens the real app/index.html in headless Chromium against a fixture and checks the Evidence tab.
// Usage: node app/tests_js/check_evidence_page.js FIXTURE_DATA.js [SHOT_DIR]
// Needs Playwright (set PLAYWRIGHT_MODULE if it is not on the default path).
const fs = require("fs"), os = require("os"), path = require("path"), assert = require("assert");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const app = path.resolve(__dirname, "..");
const fixture = path.resolve(process.argv[2]);
const shots = process.argv[3] ? path.resolve(process.argv[3]) : null;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "evidence_page_"));
for (const f of ["index.html", "style.css", "metrics.js", "core.js", "evidence_text.js", "glossary.js", "evidence.js", "main.js"]) fs.copyFileSync(path.join(app, f), path.join(tmp, f));
fs.copyFileSync(fixture, path.join(tmp, "data.js"));
// The other two views need licensed match data, so they are replaced by empty stubs here.
for (const v of ["networks", "zones"]) fs.writeFileSync(path.join(tmp, v + ".js"), `window.App.views.${v} = { init() {}, show() {}, draw() {} };\n`);

let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };
const BAD = /[‐-―\-]/;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("request", (r) => ok(r.url().startsWith("file:"), "no network request: " + r.url()));
  await page.goto("file://" + path.join(tmp, "index.html") + "#evidence");
  await page.waitForSelector("#forest svg");

  const txt = (sel) => page.locator(sel).innerText();
  const visibleText = async () => page.evaluate(() => {
    const out = [];
    for (const root of [document.querySelector("#view-evidence"), document.querySelector("#glossary"), document.querySelector("#termTip")]) {
      out.push(root.textContent);
      for (const el of root.querySelectorAll("[title],[aria-label]")) out.push(el.getAttribute("title") || "", el.getAttribute("aria-label") || "");
    }
    return out.join("\n");
  });

  // Takeaways exist at the top of the tab and of each card.
  for (const id of ["#topTakeaway", "#forestTakeaway", "#winTakeaway", "#relTakeaway"]) ok((await txt(id)).length > 60, id);
  ok(/^Within the same match/.test(await txt("#topTakeaway")));
  ok((await txt("#forestTakeaway")).includes("14 of 17 settings"));

  // Forest: 17 data rows, 3 verdicts each, exact numbers shown, verdict colours present.
  eq(await page.locator("#forest text.v").count(), 51, "verdict count");
  eq(await page.locator("#forest text.vnum").count(), 51, "number count");
  ok((await txt("#forest")).includes("+0.167") && (await txt("#forest")).includes("Clear gain") && (await txt("#forest")).includes("No clear gain"));
  ok(await page.locator("#forestEdge").isVisible(), "borderline footnote shown when an asterisk is present");

  // How to read panels are collapsed by default and open from the keyboard.
  eq(await page.locator("details.howto[open]").count(), 0, "collapsed by default");
  eq(await page.locator("details.howto").count(), 3);
  await page.locator("#howForest summary").focus();
  await page.keyboard.press("Enter");
  ok(await page.locator("#howForest").evaluate((d) => d.open), "opens with Enter");
  ok((await txt("#howForest")).includes("Soccer example"));
  await page.keyboard.press("Enter");

  // The table has the same exact numbers.
  await page.locator("details.tablewrap summary").click();
  const tbl = await txt("#forestTable");
  ok(tbl.includes("+0.167") && tbl.includes("+0.103 to +0.234"), "table numbers and ranges");
  ok(tbl.includes("Clear gain") && tbl.includes("No clear gain") && tbl.includes("borderline"));

  // Dropdowns update the takeaway with real numbers.
  const before = await txt("#forestTakeaway");
  await page.selectOption("#evTarget", "xgd");
  const afterT = await txt("#forestTakeaway");
  ok(afterT !== before && afterT.includes("xG difference"), afterT);
  ok(await page.locator('#evBase option[value="corsi_xg"]').isDisabled(), "xG baseline disabled for xG target");
  await page.selectOption("#evBase", "corsi_sot");
  ok((await txt("#forestTakeaway")).includes("shots and shots on target") && (await txt("#forestTakeaway")).includes("a clear loss"));
  await page.selectOption("#evTarget", "gd");
  await page.selectOption("#evBase", "corsi");

  // Windows card: story order, live sentence, buttons.
  ok((await txt("#winTakeaway")).startsWith("Taking features and goals from the same whole match"));
  const order = await page.locator("#winStory li h4").allInnerTexts();
  eq(order.join("|"), "Same match: the gain is clear|Different minutes: the gain fades|One possible reading: a score effect");
  await page.locator('#winSeg button[data-v="h1_to_h2"]').click();
  ok((await txt("#winTakeaway")).includes("adds no clear gain for goal difference over shots (−0.007)"));
  eq(await page.locator('#winSeg button[aria-pressed="true"]').getAttribute("data-v"), "h1_to_h2");
  ok((await txt("#winResult")).includes("No clear gain") && (await txt("#winResult")).includes("95% range"));
  eq(await page.locator('#winStory li[aria-current="step"]').count(), 1);
  ok((await txt("#winStory")).includes("consistent with the data, not proven by it"));
  ok((await txt("#winStory")).includes("Low power"));
  await page.locator('#winStory button[data-win="full"]').click();
  eq(await page.locator('#winSeg button[aria-pressed="true"]').getAttribute("data-v"), "full");
  ok(await page.evaluate(() => document.activeElement.dataset.win === "full"), "focus kept after story button");

  // Relationship card: plain caveats are on screen and the card follows the chosen minutes.
  const rel = await page.locator("#cardRel").textContent();
  for (const must of ["Exploratory", "best straight line", "all 380 matches", "whole season", "not a test result"]) ok(rel.includes(must), must);
  const relBefore = await txt("#relTakeaway");
  await page.locator('#winSeg button[data-v="h2_to_h2"]').click();
  ok((await txt("#relTakeaway")) !== relBefore && (await txt("#relTakeaway")).startsWith("Taking features and goals both from the second half"));
  eq(await page.locator("#relCorr .chip[aria-current='true']").count(), 1);
  await page.selectOption("#relFeat", "density");
  ok((await txt("#relTakeaway")).includes("Density") && (await txt("#relFeatNote")).includes("Share of possible player pairs"));
  await page.locator('#winSeg button[data-v="h1_to_h1"]').click(); // has missing values
  await page.selectOption("#relFeat", "clustering_mean");
  ok(!(await txt("#relCorr")).includes("NaN") && !(await txt("#relTakeaway")).includes("NaN"));
  await page.locator('#winSeg button[data-v="full"]').click();
  await page.selectOption("#relFeat", "pagerank_entropy_norm");

  // Terms: keyboard focus shows a tooltip, Enter opens the drawer at that entry, Escape closes it.
  await page.locator("#forestLegend .term").first().focus();
  await page.waitForSelector("#termTip:not([hidden])");
  ok((await txt("#termTip")).includes("Network features"));
  await page.keyboard.press("Escape");
  ok(await page.locator("#termTip").isHidden(), "Escape hides tip");
  await page.locator("#forestLegend .term").nth(1).focus();
  await page.keyboard.press("Enter");
  await page.waitForSelector("#glossary[open]");
  ok(await page.evaluate(() => document.activeElement.textContent.startsWith("xT")), "drawer focuses the xT entry");
  eq(await page.locator("#glossaryList .gl").count(), 15);
  const gl = await txt("#glossaryList");
  for (const t of ["R2", "Out of fold", "Ridge", "Grouped cross validation", "Bootstrap interval", "Baseline", "Extension", "xT", "Window", "Residual", "Score effect"]) ok(gl.includes(t), t);
  await page.keyboard.press("Escape");
  ok(!(await page.locator("#glossary").evaluate((d) => d.open)), "drawer closes with Escape");
  ok(await page.evaluate(() => document.activeElement.classList.contains("term")), "focus returns to the term");
  await page.locator("#openGlossary").click();
  await page.waitForSelector("#glossary[open]");
  await page.locator("#glossaryClose").click();

  // Every visible string, tooltip and label obeys the dash rule (true minus U+2212 is allowed).
  for (const theme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: theme });
    await page.locator("details.howto summary").evaluateAll((s) => s.forEach((x) => (x.parentElement.open = true)));
    const all = await visibleText();
    ok(!BAD.test(all), "dash found: " + (all.match(/.{0,30}[‐-―\-].{0,30}/) || [""])[0]);
    for (const w of ["full", "h1_to_h1", "h2_to_h2", "tied_to_full", "h1_to_h2"]) {
      await page.locator(`#winSeg button[data-v="${w}"]`).click();
      ok(!BAD.test(await visibleText()), "dash in window " + w);
    }
    await page.locator('#winSeg button[data-v="full"]').click();
    if (shots) await page.screenshot({ path: path.join(shots, `evidence_${theme}.png`), fullPage: true });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // Small screen: the page itself must not scroll sideways, the forest scrolls inside its own box.
  await page.setViewportSize({ width: 390, height: 800 });
  await page.waitForTimeout(100);
  ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "no page level horizontal scroll at 390px");
  ok(await page.locator("#forest").evaluate((e) => e.scrollWidth > e.clientWidth), "forest scrolls inside its own region");
  if (shots) await page.screenshot({ path: path.join(shots, "evidence_mobile.png"), fullPage: true });

  ok(errors.length === 0, "console or page errors: " + errors.join(" | "));
  await browser.close();
  console.log(`ok, ${n} browser checks`);
})().catch((e) => { console.error(e); process.exit(1); });

function eq(a, b, m) { assert.strictEqual(a, b, m); n++; }
