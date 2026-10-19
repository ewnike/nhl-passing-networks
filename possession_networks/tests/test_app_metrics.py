"""The explorer's JavaScript network measures must agree with networkx."""

from __future__ import annotations

import json
import shutil
import subprocess

import networkx as nx
import numpy as np
import pytest

from possnet.network.metrics import gini, player_measures, team_measures
from possnet.paths import repo_path

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _random_graphs(seed: int = 11, count: int = 12) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    graphs = []
    for k in range(count):
        n = int(rng.integers(5, 15))
        density = rng.uniform(0.25, 0.9)
        w = rng.integers(1, 25, size=(n, n)).astype(float) * (rng.random((n, n)) < density)
        np.fill_diagonal(w, 0)
        w[0] = np.where(rng.random(n) < 0.5, w[0], 0) if k % 4 == 0 else w[0]
        graphs.append(w)
    return graphs


def test_js_measures_match_networkx(tmp_path):
    graphs = _random_graphs()
    path = tmp_path / "graphs.json"
    path.write_text(json.dumps([g.tolist() for g in graphs]))
    run = subprocess.run(["node", str(repo_path("app/tests_js/run_metrics.js")), str(path)],
                         capture_output=True, text=True, check=True)
    js = json.loads(run.stdout)
    for w, got in zip(graphs, js, strict=True):
        n = len(w)
        g = nx.DiGraph()
        g.add_nodes_from(str(i) for i in range(n))
        for i, j in zip(*np.nonzero(w), strict=True):
            g.add_edge(str(i), str(j), weight=float(w[i, j]))
        if g.number_of_edges() == 0:
            continue
        py = player_measures(g).set_index("player_id").loc[[str(i) for i in range(n)]]
        for key, col in (("pagerank", "pagerank"), ("betweenness", "betweenness"),
                         ("clustering", "clustering"), ("hub", "hub"),
                         ("authority", "authority"), ("strength", "strength")):
            assert np.allclose(got[key], py[col].to_numpy(), atol=2e-4), key
        tm = team_measures(g, player_measures(g))
        assert got["team"]["density"] == pytest.approx(tm["density"])
        assert got["team"]["reciprocity"] == pytest.approx(tm["reciprocity"])
        assert got["team"]["strengthGini"] == pytest.approx(
            gini(py["strength"].to_numpy()), abs=1e-9)
