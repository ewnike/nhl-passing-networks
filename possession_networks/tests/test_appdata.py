"""The explorer data builder: shape, time handling and agreement with the networks."""

from __future__ import annotations

import json

import numpy as np
import pytest

from possnet.adapters.statsbomb import build_canonical
from possnet.appdata.build import (
    FEED_FIELDS,
    build_matches,
    build_zones,
    elapsed_seconds,
    write_data_js,
)
from possnet.incremental.experiments import CHAINS
from possnet.markov.zones import ZoneGrid
from possnet.network.build import edge_table, select_passes
from possnet.possession.sequences import ball_actions, build_possessions
from possnet.sources.synthetic import generate


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    root = tmp_path_factory.mktemp("appdata")
    return build_canonical(generate(root / "raw", seed=3, n_teams=6), root)


def test_second_half_clock_continues_after_first_half(tables):
    ev = tables["events"]
    t = elapsed_seconds(ev)
    for _, g in ev.assign(t=t).groupby("match_id"):
        p1, p2 = g[g["period"] == 1]["t"], g[g["period"] == 2]["t"]
        assert p1.max() <= p2.min() + 1e-6 or p2.empty


def test_match_entries_reconcile_with_events_and_networks(tables):
    teams, players, entries = build_matches(
        tables["matches"], tables["events"], tables["appearances"])
    assert len(entries) == len(tables["matches"]) and len(set(teams)) >= 6
    edges = edge_table(select_passes(tables["events"], "all"))
    per_match = edges.groupby("match_id")["weight"].sum()
    for e in entries:
        ev = e["ev"]
        n = len(ev["t"])
        assert all(len(ev[k]) == n for k in FEED_FIELDS)
        assert all(b > a for a, b in zip(ev["t"], ev["t"][1:], strict=False))
        assert all(0 <= i < len(players) for i in ev["f"])
        assert all(-1 <= i < len(players) for i in ev["r"])
        kinds = [k & 7 for k in ev["k"]]
        assert all(0 <= k <= 4 for k in kinds)
        # completed passes in the feed are the network's edges (self passes excluded)
        done = sum(1 for k, f, r in zip(kinds, ev["f"], ev["r"], strict=True)
                   if k == 0 and r >= 0 and r != f)
        assert done == per_match.get(e["id"], 0)
        # every ball segment has a positive duration
        assert all(u > 0 for k, u in zip(kinds, ev["u"], strict=True) if k <= 3)
        for side in "ha":
            assert all(0 <= p[0] < len(players) and 0 <= p[1] <= p[2] <= e["end"] + 1
                       and isinstance(p[3], str) for p in e["lu"][side])
        assert sum(1 for g in e["goals"] if g[1] == 0) == e["hs"]
        assert sum(1 for g in e["goals"] if g[1] == 1) == e["as"]


def test_zone_payload_matches_chain_and_writes_valid_js(tables, tmp_path):
    poss = build_possessions(tables["events"])
    actions = ball_actions(tables["events"], poss)
    grid = ZoneGrid(6, 4)
    zones = build_zones(actions, grid, [CHAINS["strict_open"]])["strict_open"]
    total = np.array(zones["goal"]) + np.array(zones["shot"]) + np.array(zones["turnover"])
    assert np.allclose(total, 1.0, atol=1e-3)
    assert len(zones["moves"]) == grid.n_zones
    out = tmp_path / "data.js"
    write_data_js({"x": [1, 2, 3]}, out)
    text = out.read_text()
    assert text.startswith("window.POSSNET = ")
    assert json.loads(text[len("window.POSSNET = "):].rstrip(";\n")) == {"x": [1, 2, 3]}
