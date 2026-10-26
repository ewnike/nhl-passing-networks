#!/usr/bin/env python
"""Generate the synthetic sample league (deterministic, seeded) under sample_data/raw.

Then run the pipeline on it with:  make sample
"""

from __future__ import annotations

import argparse
import json
import sys

from possnet.paths import REPO_ROOT, repo_path
from possnet.sources.synthetic import COMPETITION_ID, SEASON_ID, generate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--teams", type=int, default=8)
    args = parser.parse_args()
    manifest = generate(repo_path("sample_data/raw"), seed=args.seed, n_teams=args.teams)
    for f in manifest["files"]:
        f["path"] = str((REPO_ROOT / f["path"]).relative_to(REPO_ROOT)) \
            if (REPO_ROOT / f["path"]).is_absolute() else f["path"]
    manifest["cache_dir"] = "sample_data/raw/synthetic"
    out = repo_path("sample_data/manifests")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"statsbomb_c{COMPETITION_ID}_s{SEASON_ID}.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    n = manifest["matches_available"]
    print(f"Wrote {n} synthetic matches and {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
