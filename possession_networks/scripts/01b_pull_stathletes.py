#!/usr/bin/env python
"""Step 10a: pull and cache the Stathletes Big Data Cup hockey files, then summarise them.

Examples
--------
    python scripts/01b_pull_stathletes.py --list            # games in the release
    python scripts/01b_pull_stathletes.py --max-games 2     # quick smoke test
    python scripts/01b_pull_stathletes.py                   # events and shifts, every game
    python scripts/01b_pull_stathletes.py --tracking        # also the per period tracking files
    python scripts/01b_pull_stathletes.py --summary         # inventory of what is cached
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from possnet.config import load_config
from possnet.paths import repo_path
from possnet.sources.stathletes import (
    StathletesPuller,
    games_from_manifest,
    inventory,
    load_manifest,
)


def _print_inventory(puller: StathletesPuller, games: list) -> None:
    table = inventory(puller.cache_root, games)
    totals = table.drop(columns=["game_id", "max_period"]).sum()
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(table.to_string(index=False))
    print(
        f"\nTotal: {len(table)} games, {int(totals['event_rows']):,} events, "
        f"{int(totals['pass_attempts']):,} pass attempts "
        f"({int(totals['pass_complete']):,} complete), "
        f"{int(totals['complete_no_passer']):,} complete passes without a passer id, "
        f"{int(totals['complete_no_receiver']):,} without a receiver id."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--config", default="config/hockey.yaml", help="default: %(default)s")
    parser.add_argument("--max-games", type=int, help="limit for smoke tests")
    parser.add_argument("--tracking", action="store_true", help="also fetch tracking files")
    parser.add_argument("--force", action="store_true", help="redownload cached files")
    parser.add_argument("--list", action="store_true", help="list games and exit")
    parser.add_argument("--summary", action="store_true", help="summarise the cache and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(repo_path(args.config))
    sa = cfg.stathletes
    if sa is None:
        parser.error(f"{args.config} has no 'stathletes' section")
    puller = StathletesPuller(
        repo=sa.repo, release_tag=sa.release_tag, edition=sa.edition,
        raw_dir=cfg.paths.raw_dir, manifest_dir=cfg.paths.manifest_dir,
        workers=sa.workers, timeout_s=sa.timeout_s,
    )

    if args.list:
        print(f"{'game_id':<28} {'goalie team on right, period 1'}")
        for g in puller.games():
            print(f"{g.game_id:<28} {g.goalie_team_on_right_p1}")
        return 0

    if args.summary:
        manifest = load_manifest(cfg.paths.manifest_dir, sa.edition)
        _print_inventory(puller, games_from_manifest(manifest))
        return 0

    manifest = puller.pull(
        fetch_tracking=args.tracking or sa.fetch_tracking,
        max_games=args.max_games,
        force=args.force,
    )
    total_mb = sum(f["bytes"] for f in manifest["files"]) / 1e6
    print(f"Cached {len(manifest['files'])} files ({total_mb:,.1f} MB) at {manifest['cache_dir']}")
    print(f"Games pulled: {manifest['games_pulled']} of {manifest['games_listed']}\n")
    _print_inventory(puller, games_from_manifest(manifest))
    print(f"\nManifest: {Path(puller.manifest_path).relative_to(repo_path('.'))}")
    print("Reminder: this data is licensed. Do not commit or share the raw files; "
          "see DATA_ACCESS.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
