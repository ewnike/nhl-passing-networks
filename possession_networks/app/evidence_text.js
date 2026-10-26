/* Evidence wording: plain language labels, glossary, the verdict rule and the live takeaway
   sentences. Pure functions with no DOM access, so Node can test them against the real
   comparison rows (app/tests_js/run_evidence_text.js). Nothing here changes a statistic: every
   number is read from the comparison rows that scripts/11_build_app_data.py already writes.
   House rule for strings: no em dashes, en dashes or hyphens in on screen text. The only
   dash like character allowed is the true minus sign (U+2212) inside signed numbers. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EvidenceText = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  const MINUS = "−";
  const signed = (v, d = 3) => (v >= 0 ? "+" : MINUS) + Math.abs(v).toFixed(d);
  const plain = (v, d = 3) => (v < 0 ? MINUS : "") + Math.abs(v).toFixed(d);

  /* ---------- the verdict rule: only the 95 percent interval decides ---------- */
  const EDGE = 0.0005; // an interval end this close to zero is flagged as borderline
  const VERDICTS = {
    gain: { label: "Clear gain", noun: "a clear gain", verb: "adds a clear gain", verbPl: "add a clear gain" },
    none: { label: "No clear gain", noun: "no clear gain", verb: "adds no clear gain", verbPl: "add no clear gain" },
    loss: { label: "Clear loss", noun: "a clear loss", verb: "shows a clear loss", verbPl: "show a clear loss" },
  };
  function verdictOf(d) {
    const lo = d.ci_low, hi = d.ci_high;
    const key = lo > 0 ? "gain" : hi < 0 ? "loss" : "none";
    return Object.assign({ key, edge: Math.min(Math.abs(lo), Math.abs(hi)) < EDGE }, VERDICTS[key]);
  }

  /* ---------- plain names ---------- */
  const TARGETS = {
    gd: { label: "Goal difference", phrase: "goal difference", option: "Goal difference" },
    xgd: { label: "xG difference", phrase: "xG difference", option: "xG difference (chance quality)" },
  };
  const BASES = {
    corsi: { label: "Shots", phrase: "shots" },
    corsi_sot: { label: "Shots and shots on target", phrase: "shots and shots on target" },
    corsi_xg: { label: "Shots and chance quality (xG)", phrase: "shots and xG" },
    corsi_vol: { label: "Shots and pass volume", phrase: "shots and pass volume" },
  };
  /* name is the plain label, tag is the small technical label, term links to the glossary. */
  const KINDS = [
    { key: "net", name: "Passing network shape", short: "Network shape", tag: "network features", term: "netfeat" },
    { key: "xt", name: "Pass value", short: "Pass value", tag: "xT", term: "xt" },
    { key: "both", name: "Both together", short: "Both together", tag: "", term: "extension" },
  ];
  const KIND_PHRASE = { net: "passing network shape", xt: "pass value", both: "both together" };

  /* Forest rows. A string group header has no data; a row is [axis, value, main, sub]. */
  const ROWS = [
    ["Main test, features and goals from the same minutes"],
    ["primary", "primary", "Whole match", "grouped folds by match"],
    ["Different ways to split the data"],
    ["cv", "date_blocks", "Test on blocks of dates", "folds are date blocks"],
    ["cv", "cross_half", "Train on one half, test on the other", "halves of the season"],
    ["cv", "within_half_1", "First half of the season only", "fitted and tested inside that half"],
    ["cv", "within_half_2", "Second half of the season only", "fitted and tested inside that half"],
    ["Different ways to build the features"],
    ["scope", "all_passes", "Network from all passes", "includes set piece passes"],
    ["minutes", "full_strength_only", "Drop matches with a sending off", "full strength matches only"],
    ["min_seq_len", "3", "Pass value, sequences of 3 or more actions", "xT, minimum sequence length 3"],
    ["min_seq_len", "5", "Pass value, sequences of 5 or more actions", "xT, minimum sequence length 5"],
    ["chain", "strict_all", "Pass value: strict, all possessions", "xT chain, strict turnovers"],
    ["chain", "broad_open", "Pass value: broad, open play only", "xT chain, broad turnovers"],
    ["chain", "broad_all", "Pass value: broad, all possessions", "xT chain, broad turnovers"],
    ["Which minutes feed the features"],
    ["window", "h1_to_h1", "First half features, first half goals", "window: half 1 to half 1"],
    ["window", "h2_to_h2", "Second half features, second half goals", "window: half 2 to half 2"],
    ["window", "tied_to_full", "Level score features, full time goals", "window: level score to full time"],
    ["window", "h1_to_h2", "First half features, second half goals", "window: half 1 to half 2"],
    ["Check for peeking at test matches (leakage)"],
    ["leakage", "xT fit on all matches (leaky)", "Pass value map fit on every match", "deliberately leaky version"],
  ];

  /* The five minute windows, in story order. group 1 shares minutes, group 2 does not. */
  const WINDOWS = {
    full: {
      label: "Whole match", group: 1, key: ["primary", "primary"], feat: [0, 1], goal: [0, 1],
      tech: "window: whole match",
      sentence: "Taking features and goals from the same whole match",
      text: "Features and goals come from the same 90 minutes. Teams change how they pass when they lead or trail, so the score can shape the features.",
    },
    h1_to_h1: {
      label: "First half only", group: 1, key: ["window", "h1_to_h1"], feat: [0, 0.5], goal: [0, 0.5],
      tech: "window: half 1 to half 1",
      sentence: "Taking features and goals both from the first half",
      text: "Same minutes again, but only the first half. Fewer passes and fewer goals make the numbers noisier.",
    },
    h2_to_h2: {
      label: "Second half only", group: 1, key: ["window", "h2_to_h2"], feat: [0.5, 1], goal: [0.5, 1],
      tech: "window: half 2 to half 2",
      sentence: "Taking features and goals both from the second half",
      text: "Second half only. By then the first half has set the score, so teams may be playing to a result.",
    },
    tied_to_full: {
      label: "Level score to full time", group: 2, key: ["window", "tied_to_full"], feat: "tied", goal: [0, 1],
      tech: "window: level score to full time",
      sentence: "Taking features only from the minutes when the score was level and goals from the whole match",
      text: "Features use only the minutes while the score was level, which removes most score effects. Goals still count the whole match.",
    },
    h1_to_h2: {
      label: "Half 1 to half 2", group: 2, key: ["window", "h1_to_h2"], feat: [0, 0.5], goal: [0.5, 1],
      tech: "window: half 1 to half 2",
      sentence: "Taking features from the first half and goals from the second half",
      text: "Features and goals use different minutes, so this is the closest thing here to a forecast.",
    },
  };
  const WINDOW_GROUPS = { 1: "Same minutes", 2: "Different minutes" };

  const FEATS = {
    pagerank_entropy_norm: ["PageRank spread", "How evenly the ball flows through the team. Higher means more even."],
    reciprocity: ["Reciprocity", "Share of passes that are returned between the same pair of players."],
    density: ["Density", "Share of possible player pairs that exchanged passes."],
    strength_gini: ["Pass concentration", "How unevenly passing is spread across players. Higher means a few players dominate."],
    pagerank_gini: ["PageRank concentration", "How unevenly PageRank is spread across players."],
    top3_pagerank_share: ["Top 3 PageRank share", "Share of PageRank held by the three most central players."],
    betweenness_max: ["Max betweenness", "How much the most important connector sits on shortest passing routes."],
    clustering_mean: ["Clustering", "How often a player's partners also pass to each other."],
    algebraic_connectivity: ["Connectivity", "How hard the passing network is to split into two groups."],
    mean_degree: ["Passing partners per player", "Average number of teammates a player exchanged passes with."],
    hub_max: ["Top hub score", "HITS hub score of the best distributor."],
    authority_max: ["Top authority score", "HITS authority score of the best target."],
    passes_per90: ["Completed passes per 90", "Pass volume, scaled to 90 minutes."],
    xt_goal: ["xT, goal value", "Zone value gained by passes and carries, measured in goal probability."],
    xt_attempt: ["xT, shot value", "Zone value gained, measured in probability of a shot."],
  };

  /* ---------- glossary: short is the tooltip, long is the drawer entry ---------- */
  const GLOSSARY_ORDER = ["r2", "oof", "ridge", "gcv", "boot", "baseline", "extension", "xt", "window", "residual",
    "score", "verdict", "xg", "corr", "netfeat"];
  const GLOSSARY = {
    r2: {
      name: "R2 (share explained)",
      short: "The share of the match to match differences in the result that a model accounts for. 0 means no better than always guessing the average.",
      long: "R2 is the share of the match to match variation in the result that a model's predictions account for. If shots alone give an R2 of 0.09, shots account for about 9 percent of why some teams win by more goals than others. Scored on matches the model did not see, it can fall below zero when the predictions are worse than guessing the average. The charts show the change in R2 when features are added, so +0.10 means ten more points out of 100 explained.",
    },
    oof: {
      name: "Out of fold",
      short: "Scored on matches the model was not fitted on.",
      long: "The matches are split into folds. Each fold takes a turn as the test set while the model is fitted on the other folds, and the score uses only the predictions for the fold that was held out. This stops a model from looking good just because it memorized the matches it is scored on. The whole procedure is repeated 10 times with different splits.",
    },
    ridge: {
      name: "Ridge regression",
      short: "A straight line style model that shrinks its weights so it does not overreact to noise.",
      long: "Ridge regression fits a weighted sum of the features to the result, with a penalty that shrinks the weights toward zero. The penalty strength is chosen by leave one out checks inside each training fold, never by looking at the test matches. It is a linear model, so any pattern that is not a straight line effect is not tested here.",
    },
    gcv: {
      name: "Grouped cross validation",
      short: "Held out folds that keep each match whole.",
      long: "Cross validation splits the matches into folds and tests each fold in turn. Grouped means a match is never split: both teams' rows from one match always land in the same fold, so the model cannot learn from one side of a match and then be tested on the other side. The main test uses 10 folds, repeated 10 times.",
    },
    boot: {
      name: "Bootstrap interval (95%)",
      short: "A range of plausible gains found by resampling matches 2,000 times.",
      long: "To see how much a gain could move by chance, the matches are resampled with replacement 2,000 times and the gain is recomputed each time, using the same resample for the baseline and the extended model. The middle 95 percent of those gains is the interval. Resampling matches does not account for each team playing 38 of them, so the intervals are somewhat optimistic about team level effects.",
    },
    baseline: {
      name: "Baseline",
      short: "The simpler model that new features are compared against.",
      long: "The starting point. Here it is a model that predicts the result from the shot difference, and in some versions shots on target, xG or pass volume as well. Each gain on the charts is how much better the predictions get when new features are added on top of this baseline.",
    },
    extension: {
      name: "Extension",
      short: "A set of features added on top of the baseline.",
      long: "There are three: passing network features, xT features, and both together. Each extension model contains everything in the baseline plus the new features, so any gain is credited to the new features only.",
    },
    xt: {
      name: "xT (expected threat)",
      short: "A value for each part of the pitch: how often a possession that passes through it ends in a goal.",
      long: "The pitch is cut into a 12 by 8 grid. From this season's possessions we estimate, for each zone, the chance that a possession ends in a goal, or in a shot. A pass or carry earns the gain in zone value between where it starts and where it ends, and a failed pass is charged the value it lost. A team's xT features add this up over a match. The zone values come from a simple chain of zone to zone moves, so xT is a model of territory and chance creation, not a measure of skill. In the held out tests the zone values are refitted inside each training fold.",
    },
    window: {
      name: "Window",
      short: "Which minutes of the match the features, and the goals, are taken from.",
      long: "Each test chooses the minutes used to build the features and the minutes used to count goals. The main test uses the whole match for both. Other tests use one half, only the minutes while the score was level, or features from half 1 against goals from half 2 so that the two do not overlap.",
    },
    residual: {
      name: "Residual (left over after shots)",
      short: "What is left of the result after removing what shots explain.",
      long: "A residual is the part a simple model gets wrong. Here a straight line from shot difference to the result is fitted on all matches. A match above the line had more goals than its shots predicted, a match below it had fewer. The relationship explorer plots these leftovers against passing features. Because the line and the xT zone values are fitted on every match of the season, that view is exploratory and is not a held out result.",
    },
    score: {
      name: "Score effect",
      short: "Teams change how they pass depending on whether they lead or trail.",
      long: "A team that is ahead may sit back and a team that is behind may push forward, and their passing changes with it. If that happens, the scoreboard leaks into the passing features, and the features can seem to explain goals only because the goals shaped the passing. The pattern in this study is consistent with a score effect, since the gain shows up for goals but not for xG and fades when features come from different minutes than the goals. That is a reading that fits the data. It is not proven by the data.",
    },
    verdict: {
      name: "Clear gain and No clear gain",
      short: "Clear gain means the whole 95% interval is above zero.",
      long: "The verdict looks only at the 95% interval of the change. Clear gain: the whole interval is above zero. Clear loss: the whole interval is below zero. No clear gain: the interval crosses zero, so the data cannot separate the extra features from no help at all, which is not proof that they add nothing. When the deciding end of an interval is within 0.0005 of zero the verdict is marked borderline. Seventeen settings are shown without a correction for looking at many, so one clear result is weaker evidence than it looks.",
    },
    xg: {
      name: "xG (expected goals)",
      short: "The chance quality of shots: the probability that each shot becomes a goal.",
      long: "StatsBomb gives every shot a probability of scoring based on where and how it was taken. Adding these up gives expected goals. xG difference is a steadier measure of the chances a team created than goals, which depend more on luck.",
    },
    corr: {
      name: "Correlation (r)",
      short: "How closely two numbers move together, from " + MINUS + "1 to +1. Near 0 means no link.",
      long: "A correlation near 0 means no straight line link. A positive value means that when one number is higher the other tends to be higher, a negative value means the reverse. It describes association only and says nothing about cause. Here r compares a passing feature (home minus away) with what is left over after shots.",
    },
    netfeat: {
      name: "Network features",
      short: "Measures of how passes connect players, built from completed passes.",
      long: "Players are points and completed passes are lines between them. Features such as density, reciprocity, how concentrated the passing is, PageRank spread and connectivity describe the shape of that web, together with pass volume. Each feature is taken as own team minus opponent.",
    },
  };

  /* ---------- fixed text blocks ---------- */
  /* Strings with {{key|label}} tokens are rendered by App.rich, which turns each token into a glossary term. */
  const INTRO = "Each model tries to guess the goal difference for one team in one match, which is goals scored minus goals conceded. The starting point (the {{baseline|baseline}}) uses only the shot difference. The other models add how the passes connect players ({{netfeat|network features}}), how far the passes move the ball into dangerous zones ({{xt|xT}}), or both. Every score is measured on matches the model was not fitted on ({{oof|out of fold}}), so it cannot simply memorize them.";
  const CAVEATS = [
    "One season, 380 matches, so small differences are easy to over read.",
    "Features and goals come from the same match. This is an association, not a forecast.",
    "Nothing here shows that passing structure causes goals.",
    "The half 1 to half 2 test has low power, so small gains cannot be ruled out.",
    "The 17 settings are variations on one analysis of the same matches, shown without a correction for looking at many.",
  ];
  const HOWTO = {
    forest: {
      steps: [
        "Each row is one way of running the test. The three marks show the gain from adding passing network shape (blue circle), pass value (orange square) or both (green diamond).",
        "The zero line means no better than the baseline. A mark to its right means better predictions on matches the model had not seen. The line through a mark is the {{boot|95% range}}, found by resampling matches.",
        "The number is the change in {{r2|R2}}, the share of goal difference explained, so +0.10 means ten more points out of 100. If the whole line is right of zero the verdict is Clear gain. If it crosses zero the data cannot tell the gain from none.",
      ],
      example: "Soccer example: two teams each take 12 shots in a match, so shots alone predict the same result for both. One team moved the ball through many different players and the other played mostly long balls. Network features give the model something to tell those two matches apart. A blue mark at +0.10 would mean that, across all matches, this extra information explained ten more points out of 100 of the goal difference.",
    },
    window: {
      steps: [
        "Pick a test (a {{window|window}}). The blue bar shows which minutes build the features and the orange bar shows which minutes count the goals.",
        "When the bars overlap, the passing and the goals come from the same moments, so the passing can reflect the score. When they do not overlap, the test is closer to a forecast.",
        "Read the three tiles from left to right: the change, its {{boot|95% range}}, and the {{verdict|verdict}}. The story below the tiles puts the tests in order.",
      ],
      example: "Soccer example: a team that scores early and then protects a 1 to 0 lead may pass sideways among its defenders. The scoreline shapes its passing, and the same scoreline is part of the goal difference we want to explain. Taking features from half 1 and goals from half 2 breaks that link.",
    },
    rel: {
      steps: [
        "Each match is placed by the home team value minus the away team value on the chosen feature. Matches are then sorted into equal sized groups. A dot is the group average of what is {{residual|left over after shots}}, and the thin line is one standard error.",
        "Zero means the result was about what shots predicted. A line that slopes up or down suggests the feature goes with the result beyond shots. A flat line near zero means it adds nothing beyond shots.",
        "This view is exploratory. The straight line and the xT zone values are fitted on every match of the season, so it is not a held out test.",
      ],
      example: "Soccer example: suppose a group of matches where the home side's PageRank spread was much higher than the away side's has a dot at +0.4 goals. In those matches the home side scored 0.4 goals per match more than its shot difference predicted. That describes the data. It does not say the passing caused the goals.",
    },
  };

  /* ---------- helpers on the comparison rows ---------- */
  const keyOf = (w) => WINDOWS[w].key;
  function find(comps, axis, value, target, base, added) {
    return comps.find((c) => c.axis === axis && c.value === value && c.target === target &&
      c.baseline === base && c.added === added) || null;
  }
  const winRow = (comps, win, target, base, added) => find(comps, keyOf(win)[0], keyOf(win)[1], target, base, added);
  const note = (d) => `${signed(d.delta_r2)}${verdictOf(d).edge ? ", borderline" : ""}`;
  const noteV = (d) => { const v = verdictOf(d); return `${signed(d.delta_r2)}, ${v.label.toLowerCase()}${v.edge ? ", borderline" : ""}`; };

  /* One sentence about every setting for the chosen target and baseline. */
  function forestTakeaway(comps, target, base) {
    const rows = comps.filter((c) => c.target === target && c.baseline === base);
    if (!rows.length) return "There are no results for this combination.";
    const per = { net: [], xt: [], both: [] };
    for (const r of rows) if (per[r.added]) per[r.added].push(r);
    const n = per.net.length;
    const cnt = (k) => per[k].filter((r) => verdictOf(r).key === "gain").length;
    const a = cnt("net"), b = cnt("xt"), c = cnt("both");
    let tail = "";
    const notClear = rows.filter((r) => verdictOf(r).key !== "gain");
    if (notClear.length && notClear.every((r) => r.axis === "window")) {
      tail += "; every setting without a clear gain is a test that limits which minutes are used";
    }
    const losses = rows.filter((r) => verdictOf(r).key === "loss");
    if (losses.length) tail += `; ${losses.length === 1 ? "one setting shows" : losses.length + " settings show"} a clear loss`;
    return `Beyond ${BASES[base].phrase}, passing network shape gives a clear gain for ${TARGETS[target].phrase} in ${a} of ${n} settings, ` +
      `pass value (xT) in ${b}, and both together in ${c}${tail}.`;
  }

  /* One sentence for the chosen window, with the real numbers for all three feature sets. */
  function windowTakeaway(comps, win, target, base) {
    const parts = KINDS.map((k) => {
      const d = winRow(comps, win, target, base, k.key);
      if (!d) return null;
      const v = verdictOf(d);
      return { k, d, v };
    });
    if (parts.some((p) => !p)) return "There are no results for this combination.";
    const [n, x, bo] = parts;
    return `${WINDOWS[win].sentence}, passing network shape ${n.v.verb} for ${TARGETS[target].phrase} over ${BASES[base].phrase} (${note(n.d)}), ` +
      `pass value ${x.v.verb} (${note(x.d)}), and both together ${bo.v.verbPl} (${note(bo.d)}).`;
  }

  /* Low power note for the disjoint half test, built from the numbers on screen. */
  function lowPowerNote(comps, target, base) {
    const ds = KINDS.map((k) => winRow(comps, "h1_to_h2", target, base, k.key)).filter(Boolean);
    if (!ds.length) return "";
    const top = Math.max(...ds.map((d) => d.ci_high)), r2 = ds[0].r2_base;
    return `Low power: the baseline explains ${r2 < 0.1 ? "only " : ""}${plain(r2)} of second half ${TARGETS[target].phrase}, ` +
      `and the upper ends of these three intervals are at most ${signed(top)}. A gain above that is unlikely, but smaller gains cannot be excluded.`;
  }

  /* The three step story for the windows card. */
  function story(comps, target, base) {
    const get = (win, tgt = target, b = base) => KINDS.map((k) => winRow(comps, win, tgt, b, k.key));
    const fmt = (ds) => ds.map((d, i) => {
      const v = verdictOf(d);
      return `${KIND_PHRASE[KINDS[i].key]} ${signed(d.delta_r2)} (${v.label.toLowerCase()}${v.edge ? ", borderline" : ""})`;
    });
    const tgtP = TARGETS[target].phrase;

    const full = get("full"), h12 = get("h1_to_h2"), tied = get("tied_to_full");
    const ok = (ds) => ds.every(Boolean);
    if (!ok(full) || !ok(h12) || !ok(tied)) return null;
    const gains = (ds) => ds.filter((d) => verdictOf(d).key === "gain").length;

    const one = {
      title: gains(full) === 3 ? "Same match: the gain is clear" :
        gains(full) === 0 ? "Same match: no clear gain" : "Same match: a clear gain for some feature sets",
      text: `With features and goals from the same match, the change in the share of ${tgtP} explained is: ${fmt(full).join(", ")}.`,
    };
    const faded = gains(full) > 0 && gains(h12) === 0;
    const two = {
      title: faded ? "Different minutes: the gain fades" :
        gains(full) === 0 ? "Different minutes: no clear gain either" : "Different minutes: part of the gain remains",
      lines: [
        `Features from the first half against goals in the second half: ${fmt(h12).join(", ")}.`,
        `Features from level score minutes only against full time goals: ${fmt(tied).join(", ")}.`,
      ],
      power: lowPowerNote(comps, target, base),
    };

    /* The score effect check always uses shots as the baseline so the pattern is comparable. */
    const g = (win, tgt) => winRow(comps, win, tgt, "corsi", "net");
    const gFull = g("full", "gd"), xFull = g("full", "xgd"), gH12 = g("h1_to_h2", "gd"), gTied = g("tied_to_full", "gd");
    let three;
    if (gFull && xFull && gH12 && gTied &&
        verdictOf(gFull).key === "gain" && verdictOf(xFull).key !== "gain" &&
        verdictOf(gH12).key !== "gain" && verdictOf(gTied).key !== "gain") {
      three = {
        title: "One possible reading: a score effect",
        text: "Teams that lead or trail change how they pass, so the scoreboard may be written into the passing features. " +
          "That would fit three things in this data. Over shots, network shape helps with goal difference (" + noteV(gFull) + ") " +
          "but not with xG difference (" + noteV(xFull) + "). It fades when features come from the other half (" + noteV(gH12) + "). " +
          "And it is smaller when only level score minutes are used (" + noteV(gTied) + "). " +
          "This is consistent with the data, not proven by it, and it does not show that passing structure causes goals.",
      };
    } else {
      three = {
        title: "One possible reading: a score effect",
        text: "Teams that lead or trail change how they pass, which is called a score effect. In this run the numbers do not show the full pattern " +
          "that a score effect would predict, so treat this reading as untested.",
      };
    }
    return { one, two, three };
  }

  /* The sentence at the very top of the tab, checked against the data before it is used. */
  function topTakeaway(comps) {
    const need = [winRow(comps, "full", "gd", "corsi", "net"), winRow(comps, "full", "gd", "corsi", "both"),
      winRow(comps, "h1_to_h2", "gd", "corsi", "net"), winRow(comps, "h1_to_h2", "gd", "corsi", "both")];
    if (need.every(Boolean) && verdictOf(need[0]).key === "gain" && verdictOf(need[1]).key === "gain" &&
        verdictOf(need[2]).key !== "gain" && verdictOf(need[3]).key !== "gain") {
      return "Within the same match, how a team's passes connect its players lines up with goal difference beyond what shots explain, " +
        "but that link disappears when the passing and the goals come from different halves, so this is one season of association and not a forecast.";
    }
    return "This tab compares models that predict match goal difference with and without passing structure. " +
      "The cards below show how large each gain is and how sure we can be.";
  }

  /* The sentence for the relationship card, from the correlations on screen. */
  function relTakeaway(feat, win, rg, rx) {
    const phrase = (r, more, less, same) => r <= -0.1 ? `${less} (r ${signed(r, 2)})` : r >= 0.1 ? `${more} (r ${signed(r, 2)})` : `${same} (r ${signed(r, 2)})`;
    const g = phrase(rg, "more goals than their shots predict", "fewer goals than their shots predict", "about the goals their shots predict");
    const x = phrase(rx, "more chance quality than their shots predict", "less chance quality than their shots predict", "about the chance quality their shots predict");
    return `${WINDOWS[win].sentence}, matches where the home side is higher on ${FEATS[feat][0]} than the away side tend to have ${g} and ${x}. ` +
      "This is exploratory and describes association only.";
  }

  return { MINUS, signed, plain, EDGE, VERDICTS, verdictOf, TARGETS, BASES, KINDS, KIND_PHRASE, ROWS, WINDOWS, WINDOW_GROUPS,
    FEATS, GLOSSARY, GLOSSARY_ORDER, INTRO, CAVEATS, HOWTO, find, winRow, forestTakeaway, windowTakeaway, lowPowerNote,
    story, topTakeaway, relTakeaway };
});
