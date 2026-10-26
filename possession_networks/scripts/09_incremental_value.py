#!/usr/bin/env python
"""Step 8: incremental value of network and xT features over Corsi style baselines.

Predicts team match goal difference (and xG difference) with ridge regression. The primary
analysis and every one at a time sensitivity check are defined in
``possnet.incremental.experiments.sensitivity_grid`` and fixed before results are inspected.
All randomness derives from ``modeling.seed`` in config/project.yaml.

Writes (tables are small aggregates, safe to commit):
    outputs/tables/incremental_comparisons.csv   delta R2 with paired bootstrap intervals
    outputs/tables/incremental_model_scores.csv  out of fold R2 and RMSE of every model
"""

from __future__ import annotations

import sys
import time

import pandas as pd

from possnet.config import load_config
from possnet.incremental.experiments import make_context, run_setting, sensitivity_grid
from possnet.markov.zones import ZoneGrid
from possnet.paths import REPO_ROOT
from possnet.possession.sequences import ball_actions
from possnet.schema.frame import read_table


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
    ctx = make_context(
        cfg.modeling, matches, events, appearances,
        pd.read_parquet(processed / "network_team_match.parquet"),
        pd.read_parquet(processed / "network_player_match.parquet"),
        actions, ZoneGrid(12, 8))

    comparisons, scores = [], []
    settings = sensitivity_grid(cfg.modeling)
    for i, setting in enumerate(settings, 1):
        t0 = time.time()
        comp, sc = run_setting(ctx, setting)
        comparisons.append(comp)
        scores.append(sc)
        print(f"[{i}/{len(settings)}] {setting.axis}: {setting.value} ({time.time() - t0:.0f}s)",
              flush=True)

    tables = cfg.paths.tables_dir
    tables.mkdir(parents=True, exist_ok=True)
    pd.concat(comparisons, ignore_index=True).to_csv(
        tables / "incremental_comparisons.csv", index=False)
    pd.concat(scores, ignore_index=True).to_csv(tables / "incremental_model_scores.csv",
                                                index=False)
    print(f"Wrote tables to {tables.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
