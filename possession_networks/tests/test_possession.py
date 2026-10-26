"""Tests for possession sequence construction and outcome labels."""

from __future__ import annotations

import numpy as np
import pandas as pd

from possnet.possession.checks import validate_possessions
from possnet.possession.sequences import build_possessions

X, Y = "X", "Y"


class _Builder:
    """Tiny helper that writes canonical looking event rows in order."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, team, kind, poss, poss_team, *, outcome=None, dead=False, sub=None,
            period=1, xg=np.nan):
        i = len(self.rows) + 1
        self.rows.append({
            "match_id": "m", "event_id": f"e{i}", "event_index": i, "period": period,
            "period_time_s": float(i), "team_id": team, "player_id": f"{team}{i % 3}",
            "event_type": kind, "event_subtype": sub, "outcome": outcome, "is_dead_ball": dead,
            "possession_id": poss, "possession_team_id": poss_team, "play_pattern": "open_play",
            "x_start": 0.0, "y_start": 0.0, "x_end": 5.0, "y_end": 0.0, "xg": xg,
        })
        return self

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _labels(poss: pd.DataFrame) -> list[tuple[str, str, str]]:
    return list(zip(poss.team_id, poss.outcome_detail, poss.outcome_strict, strict=True))


def test_live_turnover_then_shot_then_period_end():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="incomplete")        # X loses the ball
    b.add(Y, "pass", 2, Y, outcome="complete")
    b.add(Y, "shot", 2, Y, outcome="saved", xg=0.2)
    poss = build_possessions(b.frame())
    assert _labels(poss) == [(X, "turnover_live", "turnover"), (Y, "shot", "shot")]
    assert poss.loc[1, "xg_sum"] == 0.2


def test_dead_ball_opponent_restart_differs_between_schemes():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="out")
    b.add(Y, "pass", 2, Y, outcome="complete", dead=True, sub="Throw-in")  # Y throw in
    b.add(Y, "pass", 2, Y, outcome="complete")
    poss = build_possessions(b.frame())
    first = poss.iloc[0]
    assert first.outcome_detail == "dead_ball_opponent_restart"
    assert first.outcome_strict == "censored" and first.outcome_broad == "turnover"
    assert bool(poss.iloc[1].starts_dead_ball)


def test_own_restart_is_censored_in_both_schemes():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="out")
    b.add(X, "pass", 2, X, outcome="complete", dead=True, sub="Throw-in")
    b.add(X, "pass", 2, X, outcome="complete")
    first = build_possessions(b.frame()).iloc[0]
    assert first.outcome_detail == "dead_ball_own_restart"
    assert first.outcome_strict == "censored" and first.outcome_broad == "censored"


def test_goal_beats_everything_and_counts_own_goal():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="complete")
    b.add(X, "shot", 1, X, outcome="goal", xg=0.5)
    b.add(Y, "pass", 2, Y, outcome="complete")
    b.add(Y, "other", 2, Y, sub="Own Goal For")
    poss = build_possessions(b.frame())
    assert poss.loc[0, "outcome_detail"] == "goal"
    assert poss.loc[1, "outcome_detail"] == "goal"
    assert poss["has_goal"].sum() == 2


def test_contested_provider_possession_is_split_and_shot_goes_to_shooter():
    """Provider labels one possession X, but Y carries and shoots inside it."""
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="incomplete")
    b.add(Y, "carry", 1, X)
    b.add(Y, "shot", 1, X, outcome="goal", xg=0.3)
    b.add(X, "pass", 1, X, outcome="complete")
    poss = build_possessions(b.frame())
    assert list(poss.team_id) == [X, Y, X]
    assert poss.loc[1, "n_shots"] == 1 and poss.loc[1, "has_goal"]
    assert poss.loc[0, "n_shots"] == 0 and poss.loc[2, "n_shots"] == 0
    assert (poss["n_segments_in_possession"] == 3).all()


def test_segments_without_own_ball_actions_are_dropped():
    b = _Builder()
    b.add(X, "other", 1, X, sub="Pressure")  # no ball action
    b.add(Y, "pass", 2, Y, outcome="complete")
    poss = build_possessions(b.frame())
    assert list(poss.team_id) == [Y]


def test_last_sequence_of_each_period_is_period_end():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="complete", period=1)
    b.add(Y, "pass", 2, Y, outcome="complete", period=2)
    poss = build_possessions(b.frame())
    assert list(poss.outcome_detail) == ["period_end", "period_end"]


def test_shootout_period_is_excluded():
    b = _Builder()
    b.add(X, "shot", 1, X, outcome="goal", period=5)
    assert build_possessions(b.frame()).empty


def test_validation_reconciles_shots_and_goals():
    b = _Builder()
    b.add(X, "pass", 1, X, outcome="incomplete")
    b.add(Y, "shot", 1, X, outcome="goal", xg=0.3)  # shooter is not the provider team
    events = b.frame()
    poss = build_possessions(events)
    matches = pd.DataFrame([{"match_id": "m", "home_team_id": X, "away_team_id": Y,
                             "home_score": 0, "away_score": 1}])
    report = validate_possessions(poss, events, matches)
    assert report.ok, report.to_frame().to_string()
