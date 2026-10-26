"""Tests for pass network construction and metrics (synthetic graphs, hand checkable)."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from possnet.network.build import edge_table, select_passes, to_graph
from possnet.network.metrics import (
    add_per90,
    gini,
    hits_scores,
    hits_svd,
    player_measures,
    team_measures,
)


def _passes(rows):
    """rows: (passer, recipient, outcome, is_dead_ball)"""
    return pd.DataFrame(
        [{"match_id": "m1", "team_id": "t1", "event_type": "pass", "player_id": a,
          "recipient_id": b, "outcome": o, "is_dead_ball": d} for a, b, o, d in rows]
    )


def test_select_passes_filters_scope_outcome_and_self_passes():
    ev = _passes([
        ("a", "b", "complete", False),
        ("a", "b", "incomplete", False),
        ("a", "c", "complete", True),   # throw in or similar
        ("a", "a", "complete", False),  # self pass is dropped
        ("b", None, "complete", False),  # no recipient is dropped
    ])
    assert len(select_passes(ev, "open_play")) == 1
    assert len(select_passes(ev, "all")) == 2
    with pytest.raises(ValueError):
        select_passes(ev, "nope")


def test_edge_table_and_graph_weights():
    ev = _passes([("a", "b", "complete", False)] * 3 + [("b", "a", "complete", False)])
    graph = to_graph(edge_table(select_passes(ev, "all")))
    assert graph["a"]["b"]["weight"] == 3.0
    assert graph["b"]["a"]["weight"] == 1.0


def _line_graph():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=4.0)
    g.add_edge("b", "c", weight=4.0)
    g.add_edge("c", "b", weight=2.0)
    g.add_edge("b", "a", weight=2.0)
    return g


def test_player_measures_by_hand():
    m = player_measures(_line_graph()).set_index("player_id")
    assert m.loc["b", "in_strength"] == 6.0 and m.loc["b", "out_strength"] == 6.0
    assert m.loc["b", "strength"] == 12.0
    assert m.loc["b", "in_degree"] == 2
    # b sits on the only a<->c routes, so it has all the betweenness.
    assert m.loc["b", "betweenness"] > 0 and m.loc[["a", "c"], "betweenness"].eq(0).all()
    assert m["pagerank"].sum() == pytest.approx(1.0)
    assert m["pagerank"].idxmax() == "b"


def test_hits_power_iteration_matches_exact_svd_on_random_graphs():
    rng = np.random.default_rng(7)
    for _ in range(20):
        n = int(rng.integers(5, 12))
        g = nx.DiGraph()
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < 0.6:
                    g.add_edge(f"p{i}", f"p{j}", weight=float(rng.integers(1, 15)))
        h1, a1 = hits_scores(g)
        h2, a2 = hits_svd(g)
        assert all(h1[k] == pytest.approx(h2[k], abs=1e-6) for k in h1)
        assert all(a1[k] == pytest.approx(a2[k], abs=1e-6) for k in a1)


def test_gini_extremes():
    assert gini(np.array([5, 5, 5, 5])) == pytest.approx(0.0)
    assert gini(np.array([0, 0, 0, 10])) == pytest.approx(0.75)
    assert gini(np.array([])) == 0.0


def test_team_measures_reciprocity():
    g = nx.DiGraph()
    for a, b in (("a", "b"), ("b", "c"), ("c", "a")):
        g.add_edge(a, b, weight=3.0)
        g.add_edge(b, a, weight=3.0) if (a, b) == ("a", "b") else None
    players = player_measures(g)
    tm = team_measures(g, players)
    assert tm["n_active"] == 3 and tm["n_edges"] == 4
    assert tm["total_weight"] == 12.0
    assert tm["reciprocity"] == pytest.approx(6.0 / 12.0)
    assert 0.0 <= tm["algebraic_connectivity"] <= 2.0


def test_team_measures_small_graph_returns_nans_not_errors():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    tm = team_measures(g, player_measures(g))
    assert tm["n_active"] == 2 and np.isnan(tm["reciprocity"])


def test_per90_scales_extensive_only_and_handles_zero_minutes():
    frame = pd.DataFrame({
        "minutes_played": [45.0, 90.0, 0.0],
        "in_strength": [10.0, 10.0, 0.0], "out_strength": [10.0, 10.0, 0.0],
        "strength": [20.0, 20.0, 0.0], "betweenness": [0.1, 0.1, 0.0],
        "pagerank": [0.1, 0.1, 0.0], "hub": [0.1, 0.1, 0.0], "authority": [0.1, 0.1, 0.0],
        "clustering": [0.3, 0.3, 0.0],
    })
    out = add_per90(frame)
    assert out.loc[0, "strength_per90"] == pytest.approx(40.0)
    assert out.loc[1, "strength_per90"] == pytest.approx(20.0)
    assert np.isnan(out.loc[2, "strength_per90"])
    assert "clustering_per90" not in out.columns
