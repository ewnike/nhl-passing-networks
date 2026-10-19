"""Possession sequences and outcome labels from canonical events.

A sequence is the provider's possession (``possession_id`` within a match) split wherever
control passes between teams. Control is read from ball actions (pass, carry, shot): a new
sequence starts when the team performing ball actions changes. This is needed because the
provider's possession id can span a contested exchange. In the 2015/16 Premier League data
91 shots (15 goals) are taken by a team other than the provider's possession team, so
labeling by provider possession alone would hand those shots to the wrong team. Sequences
with no ball action by their own team are dropped. Because a provider can also log a
trailing event after the next possession has started, rows are grouped by id and never
assumed to be contiguous runs.

Outcome logic (applied in this order, ``outcome_detail``):

    goal                         possession team scored (shot goal or own goal credited to it)
    shot                         at least one shot by the possession team, no goal
    period_end                   last possession of the period
    dead_ball_opponent_restart   next possession is the opponent's and starts from a dead
                                 ball (ball out of play, foul, offside)
    turnover_live                next possession is the opponent's and starts in live play
    dead_ball_own_restart        next possession is the same team's, from a dead ball
    live_continuation            next possession is the same team's, in live play

Two label schemes are then derived, so downstream work can test both:

* ``outcome_strict``  turnover = turnover_live only. Anything that is neither a shot, a
                      goal, nor a live turnover is ``censored`` (not usable as an outcome).
* ``outcome_broad``   turnover = turnover_live plus dead_ball_opponent_restart. Dead ball
                      losses count as losing the ball. Own restarts, continuations, and
                      period ends are ``censored``.

``starts_dead_ball`` (first pass or shot of the possession is a restart action) lets
analysis include or exclude possessions that began from set pieces.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OUTCOME_DETAILS = (
    "goal", "shot", "period_end", "dead_ball_opponent_restart", "turnover_live",
    "dead_ball_own_restart", "live_continuation",
)
STRICT_LABELS = ("goal", "shot", "turnover", "censored")
BROAD_LABELS = ("goal", "shot", "turnover", "censored")

OWN_GOAL_SUBTYPE = "Own Goal For"


def _first_valid(series: pd.Series):
    valid = series.dropna()
    return valid.iloc[0] if len(valid) else np.nan


def _assign_segments(ev: pd.DataFrame) -> pd.DataFrame:
    """Add ``segment`` and ``seg_team`` columns: split provider possessions at control changes."""
    keys = ["match_id", "possession_id"]
    is_ball = ev["event_type"].isin(["pass", "carry", "shot"])
    controller = ev["team_id"].where(is_ball)
    controller = controller.groupby([ev["match_id"], ev["possession_id"]]).ffill()
    ev["seg_team"] = controller.fillna(ev["possession_team_id"])
    previous = ev.groupby(keys)["seg_team"].shift()
    changed = previous.notna() & (previous != ev["seg_team"])
    ev["segment"] = changed.astype(int).groupby([ev["match_id"], ev["possession_id"]]).cumsum()
    return ev


def build_possessions(events: pd.DataFrame) -> pd.DataFrame:
    """One row per sequence (regulation and extra time) with features and outcome labels."""
    ev = events[events["possession_id"].notna() & (events["period"] <= 4)].copy()
    ev["possession_id"] = ev["possession_id"].astype("int64")
    ev = ev.sort_values(["match_id", "possession_id", "event_index"], kind="stable")
    ev = _assign_segments(ev)

    ev["is_team_event"] = ev["team_id"] == ev["seg_team"]
    ev["is_team_shot"] = ev["is_team_event"] & (ev["event_type"] == "shot")
    ev["is_team_pass"] = ev["is_team_event"] & (ev["event_type"] == "pass")
    ev["is_team_ball"] = ev["is_team_event"] & ev["event_type"].isin(["pass", "carry", "shot"])
    ev["is_team_goal"] = (
        (ev["is_team_shot"] & (ev["outcome"] == "goal"))
        | (ev["is_team_event"] & (ev["event_subtype"] == OWN_GOAL_SUBTYPE))
    )
    ev["xg_team"] = ev["xg"].where(ev["is_team_shot"])
    ev["x_last"] = ev["x_end"].fillna(ev["x_start"])
    ev["y_last"] = ev["y_end"].fillna(ev["y_start"])
    ev["is_start_action"] = ev["is_team_event"] & ev["event_type"].isin(["pass", "shot"])

    team_ev = ev[ev["is_team_event"]]
    keys = ["match_id", "possession_id", "segment"]
    grp = ev.groupby(keys, sort=True)
    tgrp = team_ev.groupby(keys, sort=True)

    out = grp.agg(
        team_id=("seg_team", "first"),
        period=("period", "first"),
        start_event_index=("event_index", "min"),
        end_event_index=("event_index", "max"),
        start_time_s=("period_time_s", "min"),
        end_time_s=("period_time_s", "max"),
        n_events=("event_id", "size"),
        n_shots=("is_team_shot", "sum"),
        n_ball_actions=("is_team_ball", "sum"),
        xg_sum=("xg_team", "sum"),
        has_goal=("is_team_goal", "any"),
        first_play_pattern=("play_pattern", "first"),
    )
    out["n_segments_in_possession"] = out.groupby(level=[0, 1])["team_id"].transform("size")
    out = out[out["n_ball_actions"] > 0]  # phantom segments: no ball action by their own team
    out["n_passes"] = tgrp["is_team_pass"].sum()
    out["n_complete_passes"] = team_ev[team_ev["is_team_pass"] & (team_ev["outcome"] == "complete")
                                       ].groupby(keys).size()
    out["n_players"] = tgrp["player_id"].nunique()
    for col in ("n_passes", "n_complete_passes", "n_players"):
        out[col] = out[col].fillna(0).astype(int)
    out["start_x"] = tgrp["x_start"].agg(_first_valid)
    out["start_y"] = tgrp["y_start"].agg(_first_valid)
    out["end_x"] = tgrp["x_last"].agg(lambda s: s.dropna().iloc[-1] if s.notna().any() else np.nan)
    out["end_y"] = tgrp["y_last"].agg(lambda s: s.dropna().iloc[-1] if s.notna().any() else np.nan)
    out["max_x"] = tgrp["x_last"].max()
    first_action = ev[ev["is_start_action"]].groupby(keys)["is_dead_ball"].first()
    out["starts_dead_ball"] = first_action.reindex(out.index).fillna(False).astype(bool)
    out["duration_s"] = (out["end_time_s"] - out["start_time_s"]).clip(lower=0)
    out = out.reset_index()
    out["n_shots"] = out["n_shots"].astype(int)
    out["n_ball_actions"] = out["n_ball_actions"].astype(int)
    out["xg_sum"] = out["xg_sum"].astype(float)
    out["has_goal"] = out["has_goal"].astype(bool)
    return _label_outcomes(out)


def _label_outcomes(poss: pd.DataFrame) -> pd.DataFrame:
    poss = poss.sort_values(["match_id", "possession_id", "segment"], kind="stable")
    poss = poss.reset_index(drop=True)
    nxt = poss.groupby("match_id")[["team_id", "period", "starts_dead_ball"]].shift(-1)
    poss["next_team_id"] = nxt["team_id"]
    poss["next_starts_dead_ball"] = nxt["starts_dead_ball"]

    last_of_period = nxt["period"].isna() | (nxt["period"] != poss["period"])
    opponent_next = nxt["team_id"].notna() & (nxt["team_id"] != poss["team_id"])
    next_dead = nxt["starts_dead_ball"].fillna(False).astype(bool)

    detail = np.select(
        [
            poss["has_goal"],
            poss["n_shots"] > 0,
            last_of_period,
            opponent_next & next_dead,
            opponent_next & ~next_dead,
            ~opponent_next & next_dead,
        ],
        ["goal", "shot", "period_end", "dead_ball_opponent_restart", "turnover_live",
         "dead_ball_own_restart"],
        default="live_continuation",
    )
    poss["outcome_detail"] = detail
    poss["outcome_strict"] = np.select(
        [detail == "goal", detail == "shot", detail == "turnover_live"],
        ["goal", "shot", "turnover"], default="censored")
    poss["outcome_broad"] = np.select(
        [detail == "goal", detail == "shot",
         np.isin(detail, ["turnover_live", "dead_ball_opponent_restart"])],
        ["goal", "shot", "turnover"], default="censored")
    return poss


def outcome_summary(poss: pd.DataFrame) -> pd.DataFrame:
    """Counts and shares of outcomes by scheme and by how the possession started."""
    rows = []
    for scheme in ("outcome_strict", "outcome_broad"):
        for starts_dead, g in poss.groupby("starts_dead_ball"):
            counts = g[scheme].value_counts()
            for label, n in counts.items():
                rows.append({
                    "scheme": scheme.replace("outcome_", ""),
                    "start": "dead_ball" if starts_dead else "open_play",
                    "outcome": label, "possessions": int(n),
                    "share_of_start_type": n / len(g),
                })
    return pd.DataFrame(rows)


def ball_actions(events: pd.DataFrame, possessions: pd.DataFrame) -> pd.DataFrame:
    """Ball actions (pass, carry, shot) of the controlling team, tagged with their sequence.

    Uses the same segmentation as :func:`build_possessions`, so every row belongs to exactly
    one row of ``possessions`` (key: match_id, possession_id, segment). Rows are ordered by
    sequence and event index and carry the sequence labels and ``starts_dead_ball``.
    """
    ev = events[events["possession_id"].notna() & (events["period"] <= 4)].copy()
    ev["possession_id"] = ev["possession_id"].astype("int64")
    ev = ev.sort_values(["match_id", "possession_id", "event_index"], kind="stable")
    ev = _assign_segments(ev)
    keep = ev["event_type"].isin(["pass", "carry", "shot"]) & (ev["team_id"] == ev["seg_team"])
    cols = ["match_id", "possession_id", "segment", "event_index", "event_id", "team_id",
            "player_id", "event_type", "outcome", "is_dead_ball", "x_start", "y_start",
            "x_end", "y_end", "period", "period_time_s"]
    acts = ev.loc[keep, cols]
    labels = possessions[["match_id", "possession_id", "segment", "starts_dead_ball",
                          "n_shots", "outcome_strict", "outcome_broad"]]
    acts = acts.merge(labels, on=["match_id", "possession_id", "segment"], how="inner")
    return acts.sort_values(["match_id", "possession_id", "segment", "event_index"],
                            kind="stable").reset_index(drop=True)
