#!/usr/bin/env python
"""Step 7: zone grid Markov chains and expected threat style action values.

Runs four configurations (outcome scheme strict or broad, crossed with open play only or
all sequences) and writes:
    data/processed/<source>/markov_team_match_<config>.parquet   (git ignored)
    outputs/tables/markov_zone_values.csv         per zone absorption probabilities
    outputs/tables/xt_player_season.csv           per player season values, every config
    outputs/tables/markov_stability.csv           split half reliability
    outputs/tables/markov_config_comparison.csv   cross configuration agreement
    outputs/figures/markov_zone_value.png         zone goal probability, four configs
"""

from __future__ import annotations

import argparse
import sys

import matplotlib.pyplot as plt
import pandas as pd

from possnet.config import load_config
from possnet.markov.chain import ChainSpec, fit_chain
from possnet.markov.stability import compare_configs, split_half_stability
from possnet.markov.value import (
    player_match_values,
    player_season_values,
    team_match_values,
    value_actions,
)
from possnet.markov.zones import ZoneGrid
from possnet.paths import REPO_ROOT
from possnet.possession.sequences import ball_actions
from possnet.schema.frame import read_table
from possnet.viz.pitch import INK, MUTED, add_attribution, draw_pitch, save_figure

SPECS = [ChainSpec(s, o) for s in ("strict", "broad") for o in (True, False)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--season-id", type=int)
    parser.add_argument("--nx", type=int, default=12)
    parser.add_argument("--ny", type=int, default=8)
    parser.add_argument("--min-minutes", type=float, default=900.0)
    args = parser.parse_args()

    cfg = load_config()
    cid = args.competition_id or cfg.statsbomb.competition_id
    sid = args.season_id or cfg.statsbomb.season_id
    tag = f"statsbomb_c{cid}_s{sid}"
    events = read_table(cfg.paths.interim_dir / tag / "events.parquet", "events")
    appearances = read_table(cfg.paths.interim_dir / tag / "appearances.parquet", "appearances")
    poss = pd.read_parquet(cfg.paths.processed_dir / tag / "possessions.parquet")
    actions = ball_actions(events, poss)
    grid = ZoneGrid(args.nx, args.ny)
    print(f"{len(actions):,} ball actions in {len(poss):,} sequences; "
          f"grid {grid.nx} x {grid.ny}")

    zone_tables, player_tables, stability, season_rows = {}, {}, [], []
    out_dir = cfg.paths.processed_dir / tag
    for spec in SPECS:
        zones = fit_chain(actions, grid, spec)
        acts = value_actions(actions, grid, zones)
        pm = player_match_values(acts)
        players = player_season_values(pm, appearances, min_minutes=args.min_minutes)
        team_match_values(acts).assign(config=spec.name).to_parquet(
            out_dir / f"markov_team_match_{spec.name}.parquet", index=False)
        zone_tables[spec.name] = zones
        player_tables[spec.name] = players.assign(config=spec.name)
        stability.append(split_half_stability(actions, appearances, grid, spec, zones,
                                              min_minutes=args.min_minutes))
        season_rows.append(players.assign(config=spec.name))

    tables = cfg.paths.tables_dir
    tables.mkdir(parents=True, exist_ok=True)
    pd.concat(zone_tables.values(), ignore_index=True).to_csv(
        tables / "markov_zone_values.csv", index=False)
    pd.concat(season_rows, ignore_index=True).to_csv(tables / "xt_player_season.csv", index=False)
    stab = pd.DataFrame(stability)
    stab.to_csv(tables / "markov_stability.csv", index=False)
    comp = compare_configs(zone_tables, player_tables)
    comp.to_csv(tables / "markov_config_comparison.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    vmax = max(t["p_goal"].max() for t in zone_tables.values())
    for ax, (name, t) in zip(axes.ravel(), zone_tables.items(), strict=True):
        draw_pitch(ax)
        im = ax.imshow(grid.to_matrix(t["p_goal"]), origin="lower", cmap="Blues", vmin=0,
                       vmax=vmax, alpha=0.9, zorder=0,
                       extent=(-grid.length / 2, grid.length / 2, -grid.width / 2, grid.width / 2))
        ax.set_title(name.replace("_", ", "), fontsize=10, color=INK, loc="left")
    fig.colorbar(im, ax=axes, shrink=0.7, label="probability the sequence ends in a goal")
    fig.suptitle("Premier League 2015/16: zone value by chain configuration (attacking left "
                 "to right)", fontsize=11, color=INK)
    fig.text(0.01, 0.01, "Open play only drops sequences that start from a dead ball.",
             fontsize=8, color=MUTED)
    add_attribution(fig)
    save_figure(fig, cfg.paths.figures_dir / "markov_zone_value.png")

    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print(stab.round(3).to_string(index=False))
        print(comp.round(3).to_string(index=False))
        for name, t in player_tables.items():
            top = t.sort_values("xt_goal_per90", ascending=False).head(8)
            print(name, list(zip(top["player_name"], top["xt_goal_per90"].round(3), strict=True)))
    print(f"Wrote tables to {tables.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
