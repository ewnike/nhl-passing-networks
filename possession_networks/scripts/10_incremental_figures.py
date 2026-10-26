#!/usr/bin/env python
"""Step 8 figures from the tables written by 09_incremental_value.py.

    outputs/figures/incremental_forest.png   delta R2 with 95% intervals, every setting
    outputs/figures/incremental_ladder.png   out of fold R2 of each baseline and extension
"""

from __future__ import annotations

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from possnet.config import load_config
from possnet.viz.pitch import GRID, INK, MUTED, add_attribution, save_figure, style_axes

COLORS = {"net": "#2a78d6", "xt": "#eb6834", "both": "#1baf7a"}
MARKERS = {"net": "o", "xt": "s", "both": "D"}
LABELS = {"net": "+ network features", "xt": "+ xT features", "both": "+ both"}
ORDER = [("primary", "primary"), ("cv", "date_blocks"), ("cv", "cross_half"),
         ("cv", "within_half_1"), ("cv", "within_half_2"), ("scope", "all_passes"),
         ("minutes", "full_strength_only"), ("min_seq_len", "3"), ("min_seq_len", "5"),
         ("chain", "strict_all"), ("chain", "broad_open"), ("chain", "broad_all"),
         ("window", "h1_to_h1"), ("window", "h2_to_h2"), ("window", "tied_to_full"),
         ("window", "h1_to_h2"), ("leakage", "xT fit on all matches (leaky)")]
NICE = {"primary": "Primary: whole match, grouped CV", "date_blocks": "CV: date blocks",
        "cross_half": "CV: train one half, test other", "within_half_1": "Within season half 1",
        "within_half_2": "Within season half 2", "all_passes": "Network from all passes",
        "full_strength_only": "Drop matches with a dismissal", "3": "Sequences of 3+ actions",
        "5": "Sequences of 5+ actions", "strict_all": "xT chain: strict, all",
        "broad_open": "xT chain: broad, open play", "broad_all": "xT chain: broad, all",
        "h1_to_h1": "Window: half 1 to half 1", "h2_to_h2": "Window: half 2 to half 2",
        "tied_to_full": "Window: level score to full time",
        "h1_to_h2": "Window: half 1 to half 2 (disjoint)",
        "xT fit on all matches (leaky)": "Leak demo: xT fit on all matches"}


def forest(comp: pd.DataFrame, baseline: str, target: str, path) -> None:
    d = comp[(comp["baseline"] == baseline) & (comp["target"] == target)]
    fig, ax = plt.subplots(figsize=(9, 7.2))
    for i, key in enumerate(ORDER):
        row = d[(d["axis"] == key[0]) & (d["value"] == key[1])]
        for j, added in enumerate(("net", "xt", "both")):
            r = row[row["added"] == added]
            if r.empty:
                continue
            y = i + (j - 1) * 0.22
            r = r.iloc[0]
            ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=COLORS[added], lw=1.6,
                    solid_capstyle="round")
            ax.plot(r["delta_r2"], y, MARKERS[added], color=COLORS[added], ms=6,
                    mec="white", mew=1.0, label=LABELS[added] if i == 0 else None)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(range(len(ORDER)), [NICE[k[1]] for k in ORDER])
    ax.invert_yaxis()
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    style_axes(ax)
    ax.set_xlabel(f"Change in out of fold R2 over the {baseline.replace('_', ' ')} baseline "
                  "(95% paired bootstrap interval over matches)", fontsize=9, color=INK)
    fig.legend(frameon=False, loc="lower left", fontsize=9, ncol=3,
               bbox_to_anchor=(0.02, -0.01))
    name = "goal difference" if target == "gd" else "xG difference"
    fig.suptitle(f"Network gains are large on the same events and vanish on disjoint events\n"
                 f"Target: {name}, baseline: shots only (Corsi style), Premier League 2015/16",
                 fontsize=11, color=INK, x=0.01, ha="left")
    add_attribution(fig)
    save_figure(fig, path)


def ladder(scores: pd.DataFrame, path) -> None:
    d = scores[(scores["axis"] == "primary")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=False)
    bases = ["corsi", "corsi_sot", "corsi_xg", "corsi_vol"]
    names = {"corsi": "Shots", "corsi_sot": "Shots +\non target", "corsi_xg": "Shots +\nxG",
             "corsi_vol": "Shots +\npass volume"}
    for ax, target in zip(axes, ("gd", "xgd"), strict=True):
        t = d[d["target"] == target].set_index("model")["r2"]
        present = [b for b in bases if b in t.index]
        x = np.arange(len(present))
        width = 0.2
        series = [("", "baseline", "#9ca3af"), ("+net", "+ network", COLORS["net"]),
                  ("+xt", "+ xT", COLORS["xt"]), ("+both", "+ both", COLORS["both"])]
        for k, (suffix, label, color) in enumerate(series):
            vals = [t[b + suffix] for b in present]
            ax.bar(x + (k - 1.5) * (width + 0.02), vals, width, color=color, label=label)
        ax.axhline(t["home_only"], color=MUTED, lw=1, ls="--")
        ax.set_xticks(x, [names[b] for b in present], fontsize=9)
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        style_axes(ax)
        ax.set_title("Goal difference" if target == "gd" else "xG difference", loc="left",
                     fontsize=10, color=INK)
    axes[0].set_ylabel("Out of fold R2 (whole match features)", fontsize=9, color=INK)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.subplots_adjust(bottom=0.24, wspace=0.18)
    fig.text(0.01, 0.07, "Dashed line: home advantage only. Same match features and target, so "
             "read these as association, not forecast.", fontsize=8, color=MUTED)
    add_attribution(fig)
    save_figure(fig, path)


def _cell(r) -> str:
    return f"{r['delta_r2']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]"


def markdown_tables(comp: pd.DataFrame, scores: pd.DataFrame) -> str:
    """Headline results as markdown: primary setting, then the window comparison."""
    out = ["Primary setting: whole match features, grouped 10 fold CV repeated 10 times, "
           "strict open xT chain, open play networks. Cells are the change in out of fold R2 "
           "with a 95% paired bootstrap interval over matches.\n",
           "| Target | Baseline | Baseline R2 | + network | + xT | + both |",
           "|---|---|---|---|---|---|"]
    prim = comp[comp["axis"] == "primary"]
    for target in ("gd", "xgd"):
        for base in ("corsi", "corsi_sot", "corsi_xg", "corsi_vol"):
            d = prim[(prim["target"] == target) & (prim["baseline"] == base)].set_index("added")
            if d.empty:
                continue
            out.append(f"| {target} | {base} | {d['r2_base'].iloc[0]:.3f} | {_cell(d.loc['net'])} "
                       f"| {_cell(d.loc['xt'])} | {_cell(d.loc['both'])} |")
    out += ["", "Same events versus disjoint events (target goal difference, baseline corsi):\n",
            "| Window (features to target) | Baseline R2 | + network | + xT | + both |",
            "|---|---|---|---|---|"]
    for key in (("primary", "primary"), ("window", "h1_to_h1"), ("window", "h2_to_h2"),
                ("window", "tied_to_full"), ("window", "h1_to_h2")):
        d = comp[(comp["axis"] == key[0]) & (comp["value"] == key[1])
                 & (comp["target"] == "gd") & (comp["baseline"] == "corsi")].set_index("added")
        out.append(f"| {NICE[key[1]]} | {d['r2_base'].iloc[0]:.3f} | {_cell(d.loc['net'])} "
                   f"| {_cell(d.loc['xt'])} | {_cell(d.loc['both'])} |")
    return "\n".join(out) + "\n"


def main() -> int:
    cfg = load_config()
    tables, figs = cfg.paths.tables_dir, cfg.paths.figures_dir
    comp = pd.read_csv(tables / "incremental_comparisons.csv")
    scores = pd.read_csv(tables / "incremental_model_scores.csv")
    forest(comp, "corsi", "gd", figs / "incremental_forest.png")
    ladder(scores, figs / "incremental_ladder.png")
    (tables / "incremental_headline.md").write_text(markdown_tables(comp, scores))
    print(f"Wrote figures to {figs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
