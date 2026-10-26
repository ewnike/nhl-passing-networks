#!/usr/bin/env python
"""Step 5: directed weighted pass networks, centralities, and team structure features.

Reads the canonical tables and writes to data/processed (git ignored):
    network_player_match.parquet   one row per player per match per scope
    network_team_match.parquet     one row per team per match per scope
    network_edges.parquet          weighted edge list per team match per scope
    network_player_season.parquet  season aggregates per player per scope
and an aggregate table to outputs/tables:
    player_season_network_features.csv   (players with 450 or more minutes, open play)
"""

from __future__ import annotations

import argparse
import sys

from possnet.config import load_config
from possnet.network.pipeline import aggregate_player_season, compute_all
from possnet.paths import REPO_ROOT
from possnet.schema.frame import read_table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--season-id", type=int)
    args = parser.parse_args()

    cfg = load_config()
    cid = args.competition_id or cfg.statsbomb.competition_id
    sid = args.season_id or cfg.statsbomb.season_id
    src = cfg.paths.interim_dir / f"statsbomb_c{cid}_s{sid}"
    events = read_table(src / "events.parquet", "events")
    apps = read_table(src / "appearances.parquet", "appearances")

    player_match, team_match, edges = compute_all(events, apps)
    season = aggregate_player_season(player_match)

    out = cfg.paths.processed_dir / f"statsbomb_c{cid}_s{sid}"
    out.mkdir(parents=True, exist_ok=True)
    player_match.to_parquet(out / "network_player_match.parquet", index=False)
    team_match.to_parquet(out / "network_team_match.parquet", index=False)
    edges.to_parquet(out / "network_edges.parquet", index=False)
    season.to_parquet(out / "network_player_season.parquet", index=False)

    cfg.paths.tables_dir.mkdir(parents=True, exist_ok=True)
    table = season[(season["scope"] == "open_play") & (season["minutes"] >= 450)]
    table = table.sort_values("pagerank_per90", ascending=False)
    table.to_csv(cfg.paths.tables_dir / "player_season_network_features.csv", index=False)

    print(f"player match rows {len(player_match):,}; team match rows {len(team_match):,}; "
          f"edges {len(edges):,}; season rows {len(season):,}")
    print(f"Wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
