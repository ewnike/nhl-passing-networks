#!/usr/bin/env python
"""Step 10b: convert the cached Stathletes files into the canonical Parquet tables.

Output (git ignored): data/interim/stathletes_<edition>/
    matches.parquet, events.parquet, appearances.parquet, build_info.json

Also checks the attack direction of every team and period (shots and zone entries must
happen at positive x in the canonical frame) and stops if a period with enough events fails.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from possnet.adapters.stathletes import attack_direction_report, build_canonical, write_build_info
from possnet.config import load_config
from possnet.paths import REPO_ROOT, repo_path
from possnet.sources.stathletes import load_manifest

ADAPTER_VERSION = "0.1.0"
MIN_EVENTS_ERROR = 20   # a period with at least this many shots and entries must face +x
MIN_EVENTS_WARN = 5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/hockey.yaml", help="default: %(default)s")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(repo_path(args.config))
    if cfg.stathletes is None:
        parser.error(f"{args.config} has no 'stathletes' section")
    edition = cfg.stathletes.edition
    manifest = load_manifest(cfg.paths.manifest_dir, edition)

    tables = build_canonical(manifest, REPO_ROOT)
    report = attack_direction_report(tables["events"])
    wrong = report[~report["ok"]]
    hard = wrong[wrong["n_events"] >= MIN_EVENTS_ERROR]
    soft = wrong[(wrong["n_events"] >= MIN_EVENTS_WARN) & (wrong["n_events"] < MIN_EVENTS_ERROR)]
    if len(soft):
        print("Direction warnings (few events, check by eye):")
        print(soft.to_string(index=False))
    if len(hard):
        print("Attack direction is wrong for these periods, so the coordinate flip is "
              "not trustworthy:")
        print(hard.to_string(index=False))
        return 1

    out_dir = cfg.paths.interim_dir / f"stathletes_{edition}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_parquet(out_dir / f"{name}.parquet", index=False)
    info = {
        "adapter": "stathletes",
        "adapter_version": ADAPTER_VERSION,
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_manifest_pulled_at_utc": manifest["pulled_at_utc"],
        "rows": {name: len(frame) for name, frame in tables.items()},
        "direction_periods_checked": int(len(report)),
        "direction_periods_flagged": int(len(wrong)),
    }
    write_build_info(out_dir / "build_info.json", info)
    print(f"Wrote canonical tables to {out_dir.relative_to(REPO_ROOT)}: {info['rows']}")
    print(f"Attack direction checked for {len(report)} team periods, {len(wrong)} flagged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
