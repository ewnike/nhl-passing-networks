#!/usr/bin/env python
"""Step 3: convert cached StatsBomb JSON into the canonical Parquet tables.

Output (git ignored): data/interim/statsbomb_c<competition>_s<season>/
    matches.parquet, events.parquet, appearances.parquet, build_info.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime

from possnet.adapters.statsbomb import build_canonical
from possnet.config import load_config
from possnet.paths import REPO_ROOT
from possnet.sources.statsbomb import load_manifest

ADAPTER_VERSION = "0.1.0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--season-id", type=int)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    cid = args.competition_id or cfg.statsbomb.competition_id
    sid = args.season_id or cfg.statsbomb.season_id
    manifest = load_manifest(cfg.paths.manifest_dir, cid, sid)

    tables = build_canonical(manifest, REPO_ROOT)
    out_dir = cfg.paths.interim_dir / f"statsbomb_c{cid}_s{sid}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_parquet(out_dir / f"{name}.parquet", index=False)

    info = {
        "adapter": "statsbomb",
        "adapter_version": ADAPTER_VERSION,
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_resolved_sha": manifest["resolved_sha"],
        "rows": {name: len(frame) for name, frame in tables.items()},
    }
    (out_dir / "build_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote canonical tables to {out_dir.relative_to(REPO_ROOT)}: {info['rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
