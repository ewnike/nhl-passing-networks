#!/usr/bin/env python
"""Step 11b (explorer, hockey): build app/data_hockey.js from the Stathletes canonical tables.

Run after step 2b. The soccer build writes its own file (data_soccer.js), and the page has a
sport switch in the header. The output holds game level rows derived from
licensed data, so it is git ignored and meant for your own machine only.
"""

from __future__ import annotations

import sys

from possnet.appdata.build import write_data_js
from possnet.appdata.hockey import build_hockey_matches, hockey_meta
from possnet.config import load_config
from possnet.paths import REPO_ROOT, repo_path
from possnet.schema.frame import read_table


def main() -> int:
    cfg = load_config(repo_path("config/hockey.yaml"))
    tag = f"stathletes_{cfg.stathletes.edition}"
    interim = cfg.paths.interim_dir / tag
    events = read_table(interim / "events.parquet", "events")
    appearances = read_table(interim / "appearances.parquet", "appearances")
    matches = read_table(interim / "matches.parquet", "matches")

    teams, players, entries = build_hockey_matches(matches, events, appearances)
    print(f"{len(entries)} games, {len(teams)} teams, {len(players)} players")
    first = matches.iloc[0]
    payload = {
        "meta": hockey_meta(float(first["field_length_m"]), float(first["field_width_m"]),
                            len(entries)),
        "teams": teams, "players": players, "matches": entries,
        "zones": {}, "leaders": {}, "evidence": {"comparisons": [], "windows": {}},
    }
    out = REPO_ROOT / "app" / "data_hockey.js"
    size = write_data_js(payload, out)
    print(f"Wrote {out.relative_to(REPO_ROOT)} ({size / 1e6:.1f} MB). Open app/index.html.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
