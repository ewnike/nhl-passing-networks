#!/usr/bin/env python
"""Step 4a: validate the canonical tables against the data contract.

Writes outputs/tables/validation_report.csv and exits with status 1 if any
error severity check fails.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from possnet.config import load_config
from possnet.paths import REPO_ROOT
from possnet.schema.frame import read_table
from possnet.validate.checks import validate_tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--season-id", type=int)
    args = parser.parse_args()

    cfg = load_config()
    cid = args.competition_id or cfg.statsbomb.competition_id
    sid = args.season_id or cfg.statsbomb.season_id
    src = cfg.paths.interim_dir / f"statsbomb_c{cid}_s{sid}"

    report = validate_tables(
        read_table(src / "matches.parquet", "matches"),
        read_table(src / "events.parquet", "events"),
        read_table(src / "appearances.parquet", "appearances"),
    )
    frame = report.to_frame()
    cfg.paths.tables_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.paths.tables_dir / "validation_report.csv"
    frame.to_csv(out, index=False)

    with pd.option_context("display.max_colwidth", 80, "display.width", 200,
                           "display.max_rows", 200):
        print(frame.to_string(index=False))
    print()
    print(report.summary())
    print(f"Report written to {out.relative_to(REPO_ROOT)}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
