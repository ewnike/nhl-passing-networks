"""Expected threat style action values from a fitted chain, aggregated to players and teams.

For a successful pass or carry from zone ``a`` to zone ``b`` the value is ``V(b) - V(a)``.
A failed pass is charged ``-V(a)``, the threat that was lost. Shots are not valued here
(the shot itself is the outcome the chain terminates in). Dead ball restarts (throw ins,
corners, free kicks, goal kicks) are excluded because a restart is not a skill of the
passer in the same sense. The value function ``V`` is either the goal probability
(``goal``) or the probability of any shot or goal (``attempt``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from possnet.markov.zones import ZoneGrid

VALUES = {"goal": "p_goal", "attempt": "p_attempt"}
PARTS = ("pass", "carry", "failed_pass")


def value_actions(actions: pd.DataFrame, grid: ZoneGrid, zone_table: pd.DataFrame
                  ) -> pd.DataFrame:
    """Live pass and carry rows with ``xt_goal`` and ``xt_attempt`` columns and ``part``."""
    acts = actions[~actions["is_dead_ball"].fillna(False).astype(bool)]
    acts = acts[acts["event_type"].isin(["pass", "carry"])].copy()
    for col in ("x_start", "y_start", "x_end", "y_end"):
        acts[col] = acts[col].astype(float)
    kind = acts["event_type"].astype(object)
    failed = ((kind == "pass") & (acts["outcome"].astype(object) != "complete")).to_numpy()
    acts["part"] = np.where(failed, "failed_pass", kind)
    z0 = grid.zone_of(acts["x_start"], acts["y_start"])
    z1 = grid.zone_of(acts["x_end"], acts["y_end"])
    ok = (z0 >= 0) & (failed | (z1 >= 0))
    acts, z0, z1, failed = acts[ok].copy(), z0[ok], z1[ok], failed[ok]
    for name, col in VALUES.items():
        v = zone_table[col].to_numpy()
        acts[f"xt_{name}"] = np.where(failed, -v[z0], v[np.where(failed, 0, z1)] - v[z0])
    return acts


def _sum_by(acts: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    wide = []
    for name in VALUES:
        col = f"xt_{name}"
        piv = acts.pivot_table(index=keys, columns="part", values=col, aggfunc="sum",
                               fill_value=0.0)
        piv = piv.reindex(columns=list(PARTS), fill_value=0.0)
        piv.columns = [f"xt_{name}_{p}" for p in piv.columns]
        piv[f"xt_{name}"] = piv.sum(axis=1)
        wide.append(piv)
    return pd.concat(wide, axis=1).reset_index()


def player_match_values(acts: pd.DataFrame) -> pd.DataFrame:
    return _sum_by(acts, ["match_id", "team_id", "player_id"])


def team_match_values(acts: pd.DataFrame) -> pd.DataFrame:
    return _sum_by(acts, ["match_id", "team_id"])


def player_season_values(player_match: pd.DataFrame, appearances: pd.DataFrame,
                         min_minutes: float = 0.0) -> pd.DataFrame:
    """Season totals and per 90 values (ratio of sums over minutes played)."""
    app = appearances.loc[appearances["minutes_played"] > 0,
                          ["match_id", "team_id", "player_id", "player_name",
                           "position_group", "minutes_played"]]
    merged = app.merge(player_match, on=["match_id", "team_id", "player_id"], how="left")
    value_cols = [c for c in player_match.columns if c.startswith("xt_")]
    merged[value_cols] = merged[value_cols].fillna(0.0)
    rows = []
    for player_id, g in merged.groupby("player_id", sort=False):
        minutes = g["minutes_played"].sum()
        if minutes < min_minutes:
            continue
        top = g.dropna(subset=["position_group"]).groupby("position_group")["minutes_played"].sum()
        row = {"player_id": player_id, "player_name": g["player_name"].iloc[0],
               "team_id": g.groupby("team_id")["minutes_played"].sum().idxmax(),
               "position_group": top.idxmax() if len(top) else None,
               "matches": g["match_id"].nunique(), "minutes": minutes}
        for col in value_cols:
            row[f"{col}_per90"] = 90.0 * g[col].sum() / minutes
        rows.append(row)
    return pd.DataFrame(rows)
