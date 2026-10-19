#!/usr/bin/env python
"""Step 6: possession sequences labeled by outcome under two schemes.

Writes data/processed/statsbomb_c<c>_s<s>/possessions.parquet (git ignored, one row per
possession) and aggregate tables to outputs/tables:
    possession_outcome_summary.csv   counts and shares by scheme and start type
    possession_validation.csv        reconciliation checks
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from possnet.config import load_config
from possnet.paths import REPO_ROOT
from possnet.possession.checks import validate_possessions
from possnet.possession.sequences import build_possessions, outcome_summary
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
    matches = read_table(src / "matches.parquet", "matches")

    poss = build_possessions(events)
    out = cfg.paths.processed_dir / f"statsbomb_c{cid}_s{sid}"
    out.mkdir(parents=True, exist_ok=True)
    poss.to_parquet(out / "possessions.parquet", index=False)

    summary = outcome_summary(poss)
    cfg.paths.tables_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(cfg.paths.tables_dir / "possession_outcome_summary.csv", index=False)
    report = validate_possessions(poss, events, matches)
    frame = report.to_frame()
    frame.to_csv(cfg.paths.tables_dir / "possession_validation.csv", index=False)

    with pd.option_context("display.width", 200, "display.max_colwidth", 70):
        print(frame.to_string(index=False))
        print()
        print(poss["outcome_detail"].value_counts().to_string())
        print()
        print(summary.pivot_table(index=["scheme", "outcome"], columns="start",
                                  values="possessions", fill_value=0).to_string())
    print(report.summary())
    print(f"Wrote {out.relative_to(REPO_ROOT)}/possessions.parquet ({len(poss):,} possessions)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
