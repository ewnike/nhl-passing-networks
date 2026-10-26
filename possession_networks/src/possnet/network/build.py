"""Build directed, weighted pass networks per team per match from canonical events.

A node is a player. A directed edge i -> j carries the number of COMPLETED passes from
player i to player j in that match. Two scopes are supported:

* ``open_play``: dead ball restarts (throw ins, goal kicks, corners, free kicks, kick
  offs) are excluded. This is the default analysis because restarts reflect the rules
  of play, not how a team moves the ball.
* ``all``: every completed pass. Used as a sensitivity check.
"""

from __future__ import annotations

from collections.abc import Iterator

import networkx as nx
import pandas as pd

SCOPES = ("open_play", "all")
EDGE_COLUMNS = ["match_id", "team_id", "player_id", "recipient_id", "weight"]


def select_passes(events: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Completed passes with a known recipient, restricted to the requested scope."""
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, got {scope!r}")
    mask = (
        (events["event_type"] == "pass")
        & (events["outcome"] == "complete")
        & events["recipient_id"].notna()
        & events["player_id"].notna()
        & (events["recipient_id"] != events["player_id"])
    )
    if scope == "open_play":
        mask &= ~events["is_dead_ball"].astype(bool)
    return events.loc[mask]


def edge_table(passes: pd.DataFrame) -> pd.DataFrame:
    """Aggregate passes to one weighted edge per (match, team, passer, recipient)."""
    edges = (
        passes.groupby(["match_id", "team_id", "player_id", "recipient_id"], observed=True)
        .size()
        .rename("weight")
        .reset_index()
    )
    return edges[EDGE_COLUMNS]


def to_graph(edges: pd.DataFrame) -> nx.DiGraph:
    """Directed weighted graph from the edge rows of a single team match."""
    graph = nx.DiGraph()
    for row in edges.itertuples(index=False):
        graph.add_edge(str(row.player_id), str(row.recipient_id), weight=float(row.weight))
    return graph


def iter_team_match_graphs(edges: pd.DataFrame) -> Iterator[tuple[tuple[str, str], nx.DiGraph]]:
    """Yield ((match_id, team_id), graph) for every team match in the edge table."""
    for key, group in edges.groupby(["match_id", "team_id"], sort=True, observed=True):
        yield (str(key[0]), str(key[1])), to_graph(group)
