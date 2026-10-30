#!/usr/bin/env python
"""Step 11 (explorer): build app/data_soccer.js for the local explorer app.

Run after steps 2 to 9. The output holds match level rows derived from licensed data, so it
is git ignored and meant for your own machine only. Then open app/index.html in a browser.
"""

from __future__ import annotations

import sys

import pandas as pd

from possnet.appdata.build import (
    SLOTS,
    build_leaders,
    build_matches,
    build_zones,
    comparisons_payload,
    evidence_windows,
    write_data_js,
)
from possnet.config import load_config
from possnet.incremental.experiments import CHAINS, make_context
from possnet.markov.zones import ZoneGrid
from possnet.paths import REPO_ROOT
from possnet.possession.sequences import ball_actions
from possnet.schema.frame import read_table

WINDOWS = {
    "full": "Whole match",
    "h1_to_h1": "Half 1 features, half 1 goals",
    "h2_to_h2": "Half 2 features, half 2 goals",
    "tied_to_full": "Level score features, full time goals",
    "h1_to_h2": "Half 1 features, half 2 goals",
}


def main() -> int:
    cfg = load_config()
    sb = cfg.statsbomb
    tag = f"statsbomb_c{sb.competition_id}_s{sb.season_id}"
    interim, processed = cfg.paths.interim_dir / tag, cfg.paths.processed_dir / tag
    events = read_table(interim / "events.parquet", "events")
    appearances = read_table(interim / "appearances.parquet", "appearances")
    matches = read_table(interim / "matches.parquet", "matches")
    poss = pd.read_parquet(processed / "possessions.parquet")
    actions = ball_actions(events, poss)
    grid = ZoneGrid(12, 8)

    teams, players, match_entries = build_matches(matches, events, appearances)
    print(f"{len(match_entries)} matches, {len(teams)} teams, {len(players)} players")
    zones = build_zones(actions, grid, list(CHAINS.values()))
    xt = pd.read_csv(cfg.paths.tables_dir / "xt_player_season.csv")
    comps = pd.read_csv(cfg.paths.tables_dir / "incremental_comparisons.csv")

    ctx = make_context(
        cfg.modeling, matches, events, appearances,
        pd.read_parquet(processed / "network_team_match.parquet"),
        pd.read_parquet(processed / "network_player_match.parquet"), actions, grid)
    evidence = {"comparisons": comparisons_payload(comps),
                "windows": evidence_windows(ctx, cfg.modeling.primary_chain, WINDOWS)}

    payload = {
        "meta": {"sport": "soccer", "season": "Premier League 2015/16", "source": "StatsBomb open data",
                 "pitch": [round(grid.length, 3), round(grid.width, 3)],
                 "grid": [grid.nx, grid.ny], "chains": list(CHAINS),
                 "primary_chain": cfg.modeling.primary_chain,
                 "slots": {k: list(v) for k, v in SLOTS.items()}},
        "teams": teams, "players": players, "matches": match_entries, "zones": zones,
        "leaders": build_leaders(xt), "evidence": evidence,
    }
    out = REPO_ROOT / "app" / "data_soccer.js"
    size = write_data_js(payload, out)
    print(f"Wrote {out.relative_to(REPO_ROOT)} ({size / 1e6:.1f} MB). Open app/index.html.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
