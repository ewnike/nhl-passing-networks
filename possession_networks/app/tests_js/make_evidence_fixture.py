#!/usr/bin/env python
"""Write a small data.js fixture for testing the Evidence tab without licensed data.

The comparison rows are the real step 8 results from outputs/tables/incremental_comparisons.csv,
so every number the tab shows is the real one. The per window match arrays that feed the
relationship explorer are synthetic (seeded), since the real ones need the licensed events.
Usage: python app/tests_js/make_evidence_fixture.py OUT.js
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from possnet.appdata.build import comparisons_payload  # noqa: E402

WINDOWS = {"full": "Whole match", "h1_to_h1": "Half 1 features, half 1 goals",
           "h2_to_h2": "Half 2 features, half 2 goals", "tied_to_full": "Level score features, full time goals",
           "h1_to_h2": "Half 1 features, half 2 goals"}
FEATS = ["passes_per90", "pagerank_entropy_norm", "reciprocity", "density", "strength_gini", "pagerank_gini",
         "top3_pagerank_share", "betweenness_max", "clustering_mean", "algebraic_connectivity", "mean_degree",
         "hub_max", "authority_max", "xt_goal", "xt_attempt"]


def synthetic_windows(n: int = 380, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for key, label in WINDOWS.items():
        shots = rng.normal(0, 5, n)
        gd = 0.08 * shots + rng.normal(0, 1.3, n)
        xgd = 0.1 * shots + rng.normal(0, 0.6, n)
        feats = {f: rng.normal(0, 1, n) for f in FEATS}
        feats["pagerank_entropy_norm"] = -0.2 * gd + rng.normal(0, 1, n)  # a weak planted link
        design = np.column_stack([np.ones(n), shots])
        res = {}
        for name, y in (("gd", gd), ("xgd", xgd)):
            beta = np.linalg.lstsq(design, y, rcond=None)[0]
            res[name] = y - design @ beta
        lst = {k: [round(float(x), 4) for x in v] for k, v in feats.items()}
        if key == "h1_to_h1":  # exercise missing values, as short windows do
            lst["clustering_mean"][::17] = [None] * len(lst["clustering_mean"][::17])
        out[key] = {"label": label, "n": n, "shots": np.round(shots, 2).tolist(),
                    "gd": np.round(gd, 3).tolist(), "xgd": np.round(xgd, 3).tolist(),
                    "res_gd": np.round(res["gd"], 3).tolist(), "res_xgd": np.round(res["xgd"], 3).tolist(),
                    "feats": lst}
    return out


def main(out_path: str) -> int:
    comps = pd.read_csv(ROOT / "outputs" / "tables" / "incremental_comparisons.csv")
    payload = {
        "meta": {"season": "Premier League 2015/16", "source": "StatsBomb open data", "pitch": [105, 68],
                 "grid": [12, 8], "chains": [], "primary_chain": "strict_open", "slots": {}},
        "teams": [], "players": [], "matches": [], "zones": {}, "leaders": {},
        "evidence": {"comparisons": comparisons_payload(comps), "windows": synthetic_windows()},
    }
    Path(out_path).write_text("window.POSSNET = " + json.dumps(payload, separators=(",", ":"), allow_nan=False) + ";\n",
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
