#!/usr/bin/env python
"""Draw an example pair of pass networks for one match (default: Chelsea v Arsenal, 2015/16).

Used to eyeball the network construction. Node size is open play PageRank, edge width is
completed open play pass count (edges with fewer than 3 passes are hidden), node labels
are shirt numbers.
"""

from __future__ import annotations

import argparse
import sys

import matplotlib.pyplot as plt
import pandas as pd

from possnet.config import load_config
from possnet.schema.frame import read_table
from possnet.viz.network_plot import average_positions, plot_pass_network
from possnet.viz.pitch import INK, add_attribution, save_figure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", default="3754217")
    args = parser.parse_args()

    cfg = load_config()
    cid, sid = cfg.statsbomb.competition_id, cfg.statsbomb.season_id
    interim = cfg.paths.interim_dir / f"statsbomb_c{cid}_s{sid}"
    processed = cfg.paths.processed_dir / f"statsbomb_c{cid}_s{sid}"
    events = read_table(interim / "events.parquet", "events")
    matches = read_table(interim / "matches.parquet", "matches")
    apps = read_table(interim / "appearances.parquet", "appearances")
    edges = pd.read_parquet(processed / "network_edges.parquet")
    players = pd.read_parquet(processed / "network_player_match.parquet")

    match = matches[matches["match_id"] == args.match_id].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    for ax, side in zip(axes, ("home", "away"), strict=True):
        team_id, team_name = match[f"{side}_team_id"], match[f"{side}_team_name"]
        e = edges[(edges.scope == "open_play") & (edges.match_id == args.match_id)
                  & (edges.team_id == team_id)]
        pos = average_positions(events, args.match_id, team_id)
        p = players[(players.scope == "open_play") & (players.match_id == args.match_id)
                    & (players.team_id == team_id)].set_index("player_id")
        a = apps[(apps.match_id == args.match_id) & (apps.team_id == team_id)
                 ].set_index("player_id")
        plot_pass_network(ax, e, pos, p["pagerank"], a["jersey_number"],
                          title=f"{team_name} ({side})")
    fig.suptitle(
        f"Open play pass networks: {match.home_team_name} {match.home_score} to "
        f"{match.away_score} {match.away_team_name}, {match.match_date}",
        x=0.01, ha="left", color=INK, fontsize=13)
    fig.text(0.01, 0.02, "Node size: PageRank. Edge width: completed passes (3 or more). "
             "Attacking left to right.", fontsize=8, color="#6b7280")
    add_attribution(fig)
    out = cfg.paths.figures_dir / "example_pass_network.png"
    save_figure(fig, out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
