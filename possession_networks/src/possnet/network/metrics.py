"""Centrality and structure measures for weighted directed pass networks.

Conventions
-----------
* Edge weight = completed pass count. For shortest path measures the distance of an edge
  is ``1 / weight`` so that heavily used links are "short".
* Betweenness is normalized by networkx's directed convention, 1 / ((n-1)(n-2)).
* PageRank (alpha 0.85) uses pass counts as weights. Mass flows along passes, so high
  PageRank means a player receives play from well connected players.
* HITS hubs are players who pass to good receivers; authorities are players who receive
  from good passers. networkx's power iteration is used, with an exact SVD fallback if it
  does not converge.
* Clustering is the weighted directed coefficient of Fagiolo (2007) as implemented by
  networkx.clustering.

Minutes normalization
---------------------
Volume style measures grow with time on the pitch. For these a ``_per90`` version is
``value * 90 / minutes_played``. Intensive measures (clustering, partner counts) are not
rescaled. Rescaling is a linear approximation, so downstream analysis also applies a
minimum minutes filter and tests sensitivity to it.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

EXTENSIVE = ("in_strength", "out_strength", "strength", "betweenness", "pagerank", "hub",
             "authority")
INTENSIVE = ("in_degree", "out_degree", "clustering")
PLAYER_FEATURES = EXTENSIVE + INTENSIVE


# ------------------------------------------------------------------------ helpers
def gini(values: np.ndarray) -> float:
    """Gini coefficient of non negative values (0 = equal, near 1 = concentrated)."""
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    total = x.sum()
    if n == 0 or total <= 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * (index * x).sum() / (n * total)) - (n + 1) / n)


def hits_svd(graph: nx.DiGraph) -> tuple[dict[str, float], dict[str, float]]:
    """Exact HITS from the principal singular vectors of the weighted adjacency matrix."""
    nodes = list(graph)
    adjacency = nx.to_numpy_array(graph, nodelist=nodes, weight="weight")
    u, _, vt = np.linalg.svd(adjacency)
    hubs, auths = np.abs(u[:, 0]), np.abs(vt[0, :])
    hubs, auths = hubs / hubs.sum(), auths / auths.sum()
    return dict(zip(nodes, hubs, strict=True)), dict(zip(nodes, auths, strict=True))


def hits_scores(graph: nx.DiGraph) -> tuple[dict[str, float], dict[str, float]]:
    """HITS hubs and authorities, each normalized to sum to one."""
    try:
        hubs, auths = nx.hits(graph, max_iter=1000, tol=1e-10, normalized=True)
        return hubs, auths
    except nx.PowerIterationFailedConvergence:
        return hits_svd(graph)


# ----------------------------------------------------------------- player measures
def player_measures(graph: nx.DiGraph) -> pd.DataFrame:
    """One row per node with the raw (not minutes normalized) network measures."""
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=["player_id", *PLAYER_FEATURES])
    distance_graph = graph.copy()
    for _, _, data in distance_graph.edges(data=True):
        data["distance"] = 1.0 / data["weight"]
    betweenness = nx.betweenness_centrality(distance_graph, weight="distance", normalized=True)
    pagerank = nx.pagerank(graph, alpha=0.85, weight="weight")
    hubs, auths = hits_scores(graph)
    clustering = nx.clustering(graph, weight="weight")
    rows = []
    for node in graph.nodes:
        in_s = graph.in_degree(node, weight="weight")
        out_s = graph.out_degree(node, weight="weight")
        rows.append({
            "player_id": node,
            "in_strength": in_s,
            "out_strength": out_s,
            "strength": in_s + out_s,
            "in_degree": graph.in_degree(node),
            "out_degree": graph.out_degree(node),
            "betweenness": betweenness[node],
            "pagerank": pagerank[node],
            "hub": hubs[node],
            "authority": auths[node],
            "clustering": clustering[node],
        })
    return pd.DataFrame(rows)


def add_per90(frame: pd.DataFrame, minutes_col: str = "minutes_played") -> pd.DataFrame:
    """Add ``<measure>_per90`` columns for the extensive measures."""
    out = frame.copy()
    minutes = out[minutes_col].where(out[minutes_col] > 0)
    for col in EXTENSIVE:
        out[f"{col}_per90"] = out[col] * 90.0 / minutes
    return out


# ------------------------------------------------------------------- team measures
def team_measures(graph: nx.DiGraph, players: pd.DataFrame) -> dict[str, Any]:
    """Whole network summary for one team match (``players`` from player_measures)."""
    n = graph.number_of_nodes()
    total = float(sum(d["weight"] for _, _, d in graph.edges(data=True)))
    out: dict[str, Any] = {
        "n_active": n,
        "n_edges": graph.number_of_edges(),
        "total_weight": total,
        "density": graph.number_of_edges() / (n * (n - 1)) if n > 1 else 0.0,
        "reciprocity": math.nan, "strength_gini": math.nan, "pagerank_gini": math.nan,
        "pagerank_entropy_norm": math.nan, "top3_pagerank_share": math.nan,
        "betweenness_max": math.nan, "clustering_mean": math.nan,
        "algebraic_connectivity": math.nan,
    }
    if n < 3 or total == 0:
        return out
    reciprocated = sum(
        min(d["weight"], graph[v][u]["weight"])
        for u, v, d in graph.edges(data=True) if graph.has_edge(v, u)
    )
    pr = players["pagerank"].to_numpy()
    out["reciprocity"] = reciprocated / total
    out["strength_gini"] = gini(players["strength"].to_numpy())
    out["pagerank_gini"] = gini(pr)
    out["pagerank_entropy_norm"] = float(-(pr[pr > 0] * np.log(pr[pr > 0])).sum() / math.log(n))
    out["top3_pagerank_share"] = float(np.sort(pr)[-3:].sum())
    out["betweenness_max"] = float(players["betweenness"].max())
    out["clustering_mean"] = float(players["clustering"].mean())
    out["algebraic_connectivity"] = _algebraic_connectivity(graph)
    return out


def _algebraic_connectivity(graph: nx.DiGraph) -> float:
    """Second smallest eigenvalue of the normalized Laplacian of the symmetrized network."""
    nodes = list(graph)
    adjacency = nx.to_numpy_array(graph, nodelist=nodes, weight="weight")
    sym = adjacency + adjacency.T
    degree = sym.sum(axis=1)
    if (degree == 0).any():
        return 0.0
    inv_sqrt = np.diag(1.0 / np.sqrt(degree))
    laplacian = np.eye(len(nodes)) - inv_sqrt @ sym @ inv_sqrt
    return float(np.sort(np.linalg.eigvalsh(laplacian))[1])
