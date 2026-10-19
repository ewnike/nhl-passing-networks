"""Build the team match modelling table and the fold safe xT machinery.

Row layout
----------
Matches are sorted by date then id. Match ``m`` owns rows ``2m`` (home perspective) and
``2m + 1`` (away perspective). The away row is the exact mirror of the home row: every
feature difference and the target change sign. ``opp = row ^ 1`` finds the opponent row.

Why xT is special
-----------------
The xT value of a zone is estimated from outcomes (goals and shots). If those outcomes include
the test match, the feature has seen the answer. So xT features are not precomputed. For each
team match we store a coefficient vector ``c`` over zones such that its xT sum is ``c . V``
(a successful pass or carry adds +1 at its end zone and -1 at its start zone, a failed pass
adds -1 at its start zone). ``V`` is refit inside every training fold from per match
transition counts, then ``c . V`` is evaluated for all rows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from possnet.markov.chain import SEQ_KEYS, ChainSpec, absorption, build_transitions, count_matrix
from possnet.markov.zones import ZoneGrid

NET_STRUCT = ("density", "reciprocity", "strength_gini", "pagerank_gini",
              "pagerank_entropy_norm", "top3_pagerank_share", "betweenness_max",
              "clustering_mean", "algebraic_connectivity", "mean_degree", "hub_max",
              "authority_max")
VOLUME = "passes_per90"


def sorted_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Order matches by date and id and return the home perspective skeleton."""
    m = matches.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    return m


def goals_by_period(events: pd.DataFrame) -> pd.DataFrame:
    """Goals credited to each team per period: scored shots plus own goals for the team."""
    shot_goal = (events["event_type"] == "shot") & (events["outcome"].astype(object) == "goal")
    own = events["event_subtype"].astype(object) == "Own Goal For"
    g = events[shot_goal | own]
    return g.groupby(["match_id", "team_id", "period"]).size().rename("goals").reset_index()


def team_rows(matches: pd.DataFrame, events: pd.DataFrame, appearances: pd.DataFrame,
              network_team: pd.DataFrame, network_player: pd.DataFrame, scope: str,
              feature_events: pd.DataFrame | None = None,
              target_events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Two rows per match with raw (not yet differenced) own side quantities.

    Features (shots, shots on target, xG) come from ``feature_events`` and the targets from
    ``target_events``; ``None`` means every event. The network tables passed in must already be
    built from the same feature events.
    """
    m = sorted_matches(matches)
    ev_f = events if feature_events is None else feature_events
    ev_t = events if target_events is None else target_events
    shots = ev_f[ev_f["event_type"] == "shot"].copy()
    shots["on_target"] = shots["outcome"].astype(object).isin(["goal", "saved"])
    by_team = shots.groupby(["match_id", "team_id"]).agg(
        shots=("event_id", "size"), sot=("on_target", "sum"), xg=("xg", "sum")).reset_index()
    shots_t = ev_t[ev_t["event_type"] == "shot"]
    xg_t = shots_t.groupby(["match_id", "team_id"])["xg"].sum().rename("target_xg").reset_index()
    goals = goals_by_period(ev_t).groupby(["match_id", "team_id"])["goals"].sum().reset_index()
    minutes = appearances.groupby(["match_id", "team_id"])["minutes_played"].sum().rename(
        "team_minutes").reset_index()

    net = network_team[network_team["scope"] == scope].copy()
    pl = network_player[(network_player["scope"] == scope) & network_player["in_network"]]
    agg = pl.groupby(["match_id", "team_id"]).agg(
        mean_degree=("in_degree", "mean"), hub_max=("hub", "max"),
        authority_max=("authority", "max")).reset_index()
    net = net.merge(agg, on=["match_id", "team_id"], how="left")
    net = net.rename(columns={"total_weight_per90": VOLUME})

    rows = []
    for pos, r in m.iterrows():
        for side, team, opp in ((1, r["home_team_id"], r["away_team_id"]),
                                (-1, r["away_team_id"], r["home_team_id"])):
            rows.append({"match_pos": pos, "match_id": r["match_id"], "date": r["match_date"],
                         "team_id": team, "opp_id": opp, "side": side})
    df = pd.DataFrame(rows)
    for tbl in (by_team, xg_t, goals, minutes, net):
        df = df.merge(tbl, on=["match_id", "team_id"], how="left")
    df[["shots", "sot", "xg", "target_xg", "goals"]] = df[
        ["shots", "sot", "xg", "target_xg", "goals"]].fillna(0.0)
    return df


def differenced(rows: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Own minus opponent for ``cols`` (rows must follow the 2m, 2m+1 layout)."""
    own = rows[cols].to_numpy(dtype=float)
    return pd.DataFrame(own - own[np.arange(len(rows)) ^ 1], columns=cols, index=rows.index)


def build_model_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Differenced features and both targets, one row per team match."""
    base = differenced(rows, ["shots", "sot", "xg", VOLUME, *NET_STRUCT])
    base["is_home"] = rows["side"].to_numpy(dtype=float)
    goals = differenced(rows, ["goals", "target_xg"])
    base["gd"] = goals["goals"].to_numpy()
    base["xgd"] = goals["target_xg"].to_numpy()
    base["match_pos"] = rows["match_pos"].to_numpy()
    base["match_id"] = rows["match_id"].to_numpy()
    full = (rows["team_minutes"] >= 11 * rows["match_minutes"] - 0.5).to_numpy()
    base["full_strength"] = full & full[np.arange(len(rows)) ^ 1]
    return base


# ------------------------------------------------------------------------ xT parts
@dataclass
class XtData:
    """Per match transition counts and per team match zone coefficients for one setting."""

    spec: ChainSpec
    grid: ZoneGrid
    counts: np.ndarray      # (n_matches, n_zones, n_zones + 3)
    coef: np.ndarray        # (n_rows, n_zones)
    fit_on_all: bool = False  # leakage demonstration only: V sees every match, test included

    def zone_values(self, train_matches: np.ndarray) -> np.ndarray:
        """(n_zones, 2) goal and attempt probabilities from the training matches only."""
        used = self.counts if self.fit_on_all else self.counts[train_matches]
        b = absorption(used.sum(axis=0))
        return np.column_stack([b[:, 0], b[:, 0] + b[:, 1]])

    def features(self, train_matches: np.ndarray) -> np.ndarray:
        """(n_rows, 2) own minus opponent xT sums (goal, attempt) with V from train only."""
        x = self.coef @ self.zone_values(train_matches)
        return x - x[np.arange(len(x)) ^ 1]


def length_filter(actions: pd.DataFrame, min_len: int) -> pd.DataFrame:
    """Drop ball actions from sequences with fewer than ``min_len`` ball actions."""
    if min_len <= 1:
        return actions
    size = actions.groupby(SEQ_KEYS, sort=False)["event_type"].transform("size")
    return actions[size >= min_len]


def coefficient_matrix(actions: pd.DataFrame, rows: pd.DataFrame, grid: ZoneGrid
                       ) -> np.ndarray:
    """Zone coefficient vectors for the live pass and carry actions of every team match."""
    acts = actions[~actions["is_dead_ball"].fillna(False).astype(bool)]
    acts = acts[acts["event_type"].isin(["pass", "carry"])].copy()
    for col in ("x_start", "y_start", "x_end", "y_end"):
        acts[col] = acts[col].astype(float)
    kind = acts["event_type"].astype(object)
    failed = ((kind == "pass") & (acts["outcome"].astype(object) != "complete")).to_numpy()
    z0 = grid.zone_of(acts["x_start"], acts["y_start"])
    z1 = grid.zone_of(acts["x_end"], acts["y_end"])
    ok = (z0 >= 0) & (failed | (z1 >= 0))
    acts, z0, z1, failed = acts[ok], z0[ok], z1[ok], failed[ok]
    index = pd.MultiIndex.from_arrays([rows["match_id"], rows["team_id"]])
    pos = index.get_indexer(pd.MultiIndex.from_arrays([acts["match_id"], acts["team_id"]]))
    if (pos < 0).any():
        raise ValueError("ball actions belong to a team match that is not in the table")
    coef = np.zeros((len(rows), grid.n_zones))
    np.add.at(coef, (pos, z0), -1.0)
    np.add.at(coef, (pos[~failed], z1[~failed]), 1.0)
    return coef


def build_xt_data(actions: pd.DataFrame, rows: pd.DataFrame, spec: ChainSpec, grid: ZoneGrid,
                  min_len: int = 1, feature_actions: pd.DataFrame | None = None) -> XtData:
    """Per match counts and coefficients for one chain configuration and length filter.

    The chain is always fit on whole matches of the training set. ``feature_actions`` (a subset
    of ``actions``) only limits which actions of a match feed that match's own xT features.
    """
    acts = length_filter(actions, min_len)
    n_matches = int(rows["match_pos"].max()) + 1
    counts = np.zeros((n_matches, grid.n_zones, grid.n_zones + 3))
    pos_of = dict(zip(rows["match_id"], rows["match_pos"], strict=True))
    for match_id, g in acts.groupby("match_id", sort=False):
        counts[pos_of[match_id]] = count_matrix(build_transitions(g, grid, spec), grid.n_zones)
    fa = acts if feature_actions is None else length_filter(feature_actions, min_len)
    return XtData(spec, grid, counts, coefficient_matrix(fa, rows, grid))
