#!/usr/bin/env python
"""Step 2: pull and cache StatsBomb open data for the configured competition season.

Examples
--------
    python scripts/01_pull_data.py --list                 # show available competition seasons
    python scripts/01_pull_data.py                        # pull what config/project.yaml names
    python scripts/01_pull_data.py --max-matches 10       # quick smoke test
    python scripts/01_pull_data.py --competition-id 37 --season-id 4   # WSL 2018/2019
"""

from __future__ import annotations

import argparse
import logging
import sys

from possnet.config import load_config
from possnet.sources.statsbomb import StatsBombPuller, list_competitions


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--season-id", type=int)
    parser.add_argument("--ref", help="branch, tag, or commit SHA (default: from config)")
    parser.add_argument("--max-matches", type=int, help="limit for smoke tests")
    parser.add_argument("--force", action="store_true", help="redownload cached files")
    parser.add_argument("--list", action="store_true", help="list competition seasons and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    sb = cfg.statsbomb
    puller = StatsBombPuller(
        repo=sb.repo, ref=args.ref or sb.ref, raw_dir=cfg.paths.raw_dir,
        manifest_dir=cfg.paths.manifest_dir, workers=sb.workers, timeout_s=sb.timeout_s,
    )

    if args.list:
        rows = sorted(
            list_competitions(puller),
            key=lambda c: (c["competition_name"], c["season_name"]),
        )
        print(f"{'competition_id':>14} {'season_id':>9}  competition / season")
        for c in rows:
            print(f"{c['competition_id']:>14} {c['season_id']:>9}  "
                  f"{c['competition_name']} {c['season_name']} ({c['country_name']})")
        return 0

    manifest = puller.pull_competition_season(
        competition_id=args.competition_id or sb.competition_id,
        season_id=args.season_id or sb.season_id,
        fetch_lineups=sb.fetch_lineups,
        fetch_three_sixty=sb.fetch_three_sixty,
        max_matches=args.max_matches,
        force=args.force,
    )
    total_mb = sum(f["bytes"] for f in manifest["files"]) / 1e6
    print(f"Cached {len(manifest['files'])} files ({total_mb:,.0f} MB) at {manifest['cache_dir']}")
    print(f"Resolved commit: {manifest['resolved_sha']}")
    print("Reminder: this data is licensed. Do not commit or share the raw files; "
          "see DATA_ACCESS.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
