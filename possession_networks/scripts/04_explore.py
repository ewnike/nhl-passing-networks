#!/usr/bin/env python
"""Step 4b: exploratory tables and figures from the canonical tables.

Writes CSV and JSON summaries to outputs/tables and three figures to outputs/figures.
These are exploratory; the three original visualizations required by the capstone are
built later from the network and value results.
"""

from __future__ import annotations

import argparse
import json
import sys

from possnet.config import load_config
from possnet.explore import eda
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
    matches = read_table(src / "matches.parquet", "matches")
    events = read_table(src / "events.parquet", "events")
    apps = read_table(src / "appearances.parquet", "appearances")

    tables, figures = cfg.paths.tables_dir, cfg.paths.figures_dir
    tables.mkdir(parents=True, exist_ok=True)

    facts = eda.key_facts(matches, events, apps)
    (tables / "eda_key_facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    counts = eda.event_counts(events)
    counts.to_csv(tables / "eda_event_counts.csv", index=False)
    eda.missingness(events).to_csv(tables / "eda_missingness.csv", index=False)
    team_matches = eda.team_match_summary(events)
    team_matches.to_csv(tables / "eda_team_match_summary.csv", index=False)
    poss = eda.possession_summary(events)
    poss.to_csv(tables / "eda_possession_summary.csv", index=False)
    eda.player_minutes_summary(apps).to_csv(tables / "eda_player_minutes.csv", index=False)

    eda.fig_event_mix(counts, figures / "eda_event_mix.png")
    eda.fig_pass_density(events, figures / "eda_pass_density.png")
    eda.fig_passes_per_team_match(team_matches, figures / "eda_passes_per_team_match.png")

    print(json.dumps(facts, indent=2))
    print(f"Possessions: {len(poss):,}; median passes per possession "
          f"{poss['n_passes'].median():.0f}; share with a shot {poss['has_shot'].mean():.1%}")
    print(f"Tables in {tables.relative_to(REPO_ROOT)}, figures in {figures.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
