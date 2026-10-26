"""Compute network features for every team match and aggregate them to players and seasons."""

from __future__ import annotations

import pandas as pd

from possnet.network.build import SCOPES, edge_table, iter_team_match_graphs, select_passes
from possnet.network.metrics import (
    EXTENSIVE,
    PLAYER_FEATURES,
    add_per90,
    player_measures,
    team_measures,
)
from possnet.validate.checks import match_durations_s


def compute_scope(
    events: pd.DataFrame, appearances: pd.DataFrame, scope: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (player_match, team_match, edges) for one pass scope."""
    edges = edge_table(select_passes(events, scope))
    player_rows: list[pd.DataFrame] = []
    team_rows: list[dict] = []
    for (match_id, team_id), graph in iter_team_match_graphs(edges):
        measures = player_measures(graph)
        measures.insert(0, "team_id", team_id)
        measures.insert(0, "match_id", match_id)
        player_rows.append(measures)
        team_rows.append({"match_id": match_id, "team_id": team_id,
                          **team_measures(graph, measures)})

    network = pd.concat(player_rows, ignore_index=True)
    network["in_network"] = True
    base = appearances.loc[appearances["minutes_played"] > 0,
                           ["match_id", "team_id", "player_id", "player_name",
                            "position_group", "started", "minutes_played"]]
    merged = base.merge(network, on=["match_id", "team_id", "player_id"], how="outer",
                        indicator=True)
    stray = int((merged["_merge"] == "right_only").sum())
    if stray:
        raise ValueError(f"{stray} network nodes have no appearance with minutes; "
                         "check the appearances table")
    merged = merged.drop(columns="_merge")
    merged["in_network"] = merged["in_network"].fillna(False).astype(bool)
    merged[list(PLAYER_FEATURES)] = merged[list(PLAYER_FEATURES)].fillna(0.0)
    merged = add_per90(merged)
    merged.insert(0, "scope", scope)

    team = pd.DataFrame(team_rows)
    duration = (match_durations_s(events) / 60.0).rename("match_minutes")
    team = team.merge(duration, left_on="match_id", right_index=True, how="left")
    team["total_weight_per90"] = team["total_weight"] * 90.0 / team["match_minutes"]
    team.insert(0, "scope", scope)
    edges = edges.assign(scope=scope)
    return merged, team, edges


def compute_all(
    events: pd.DataFrame, appearances: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute both scopes and stack them."""
    parts = [compute_scope(events, appearances, scope) for scope in SCOPES]
    return tuple(pd.concat([p[i] for p in parts], ignore_index=True) for i in range(3))


def aggregate_player_season(player_match: pd.DataFrame) -> pd.DataFrame:
    """Season level player features per scope.

    Extensive measures use the ratio of sums: ``90 * sum(raw) / sum(minutes)``, which equals
    the minutes weighted mean of the per match per90 values. Intensive measures are
    minutes weighted means.
    """
    rows = []
    for (scope, player_id), g in player_match.groupby(["scope", "player_id"], sort=False):
        minutes = g["minutes_played"].sum()
        by_team = g.groupby("team_id")["minutes_played"].sum()
        top_group = (g.dropna(subset=["position_group"])
                     .groupby("position_group")["minutes_played"].sum())
        row = {
            "scope": scope,
            "player_id": player_id,
            "player_name": g["player_name"].iloc[0],
            "team_id": by_team.idxmax(),
            "position_group": top_group.idxmax() if len(top_group) else None,
            "matches": g["match_id"].nunique(),
            "minutes": minutes,
        }
        for col in EXTENSIVE:
            row[f"{col}_per90"] = 90.0 * g[col].sum() / minutes if minutes > 0 else float("nan")
        for col in ("in_degree", "out_degree", "clustering"):
            weighted = (g[col] * g["minutes_played"]).sum()
            row[col] = weighted / minutes if minutes > 0 else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)
