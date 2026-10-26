#!/usr/bin/env python
"""Step 10b: validate the canonical hockey tables against the data contract.

Writes outputs/hockey/tables/validation_report.csv (path from config/hockey.yaml) and exits
with status 1 if any error severity check fails.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from possnet.config import load_config
from possnet.paths import REPO_ROOT, repo_path
from possnet.schema.frame import read_table
from possnet.validate.checks import validate_tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/hockey.yaml", help="default: %(default)s")
    args = parser.parse_args()

    cfg = load_config(repo_path(args.config))
    if cfg.stathletes is None:
        parser.error(f"{args.config} has no 'stathletes' section")
    src = cfg.paths.interim_dir / f"stathletes_{cfg.stathletes.edition}"

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
