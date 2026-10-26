"""Tests for the zone grid, the absorbing chain, and action values (hand checkable)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from possnet.markov.chain import ChainSpec, absorption, build_transitions, count_matrix, fit_chain
from possnet.markov.value import player_match_values, value_actions
from possnet.markov.zones import ZoneGrid

GRID = ZoneGrid(nx=2, ny=1)  # zone 0 = own half, zone 1 = attacking half
LEFT, RIGHT = -20.0, 20.0


def _actions(rows):
    """rows: (poss, kind, x, outcome, strict, broad); one sequence per poss id."""
    recs = []
    for i, (poss, kind, x, outcome, strict, broad) in enumerate(rows):
        recs.append({"match_id": 1, "possession_id": poss, "segment": 0, "event_index": i,
                     "team_id": 1, "player_id": 10 + poss, "event_type": kind,
                     "outcome": outcome, "is_dead_ball": False, "starts_dead_ball": False,
                     "x_start": x, "y_start": 0.0, "x_end": x, "y_end": 0.0,
                     "outcome_strict": strict, "outcome_broad": broad})
    return pd.DataFrame(recs)


def test_zone_of_clips_and_flags_missing():
    z = ZoneGrid(12, 8)
    assert z.zone_of([-100, 100, np.nan], [0, 0, 0]).tolist() == [4, 11 * 8 + 4, -1]
    assert len(z.centers()) == 96 and z.to_matrix(np.arange(96)).shape == (8, 12)


def test_absorption_by_hand():
    counts = np.zeros((2, 5))
    counts[0, 1] = 1
    counts[0, 4] = 1   # zone 0: half to zone 1, half to turnover
    counts[1, 2] = 1
    counts[1, 3] = 1   # zone 1: half goal, half shot
    b = absorption(counts)
    assert b[1].tolist() == pytest.approx([0.5, 0.5, 0.0])
    assert b[0].tolist() == pytest.approx([0.25, 0.25, 0.5])
    assert b.sum(axis=1) == pytest.approx([1.0, 1.0])


def test_transitions_truncate_at_first_shot_and_drop_censored_endings():
    acts = _actions([
        (1, "pass", LEFT, "complete", "goal", "goal"),
        (1, "shot", RIGHT, "goal", "goal", "goal"),
        (1, "shot", RIGHT, "saved", "goal", "goal"),     # after first shot, ignored
        (2, "pass", LEFT, "complete", "censored", "turnover"),
        (3, "pass", RIGHT, "incomplete", "turnover", "turnover"),
    ])
    n = GRID.n_zones
    strict = build_transitions(acts, GRID, ChainSpec("strict", False))
    pairs = list(zip(strict["src"], strict["dst"], strict=True))
    assert (0, 1) in pairs and (1, n) in pairs and (1, n + 2) in pairs
    assert (0, n + 2) not in pairs                      # censored under strict
    broad = build_transitions(acts, GRID, ChainSpec("broad", False))
    assert (0, n + 2) in list(zip(broad["src"], broad["dst"], strict=True))
    assert len(strict) == 3 and len(broad) == 4
    assert count_matrix(strict, n).sum() == 3


def test_open_play_only_drops_dead_ball_sequences():
    acts = _actions([(1, "pass", LEFT, "complete", "turnover", "turnover")])
    acts["starts_dead_ball"] = True
    assert len(build_transitions(acts, GRID, ChainSpec("strict", True))) == 0
    assert len(build_transitions(acts, GRID, ChainSpec("strict", False))) == 1


def test_fit_chain_values_rise_toward_goal_and_values_sum_to_gain():
    acts = _actions([
        (1, "pass", LEFT, "complete", "goal", "goal"), (1, "shot", RIGHT, "goal", "goal", "goal"),
        (2, "pass", LEFT, "complete", "turnover", "turnover"),
        (3, "pass", RIGHT, "complete", "turnover", "turnover"),
    ])
    zones = fit_chain(acts, GRID, ChainSpec("strict", False))
    assert zones.loc[1, "p_goal"] > zones.loc[0, "p_goal"]
    forward = acts.iloc[[0]].assign(x_end=RIGHT)
    vals = value_actions(forward, GRID, zones)
    expected = zones.loc[1, "p_goal"] - zones.loc[0, "p_goal"]
    assert vals["xt_goal"].iloc[0] == pytest.approx(expected)
    failed = acts.iloc[[0]].assign(outcome="incomplete")
    assert value_actions(failed, GRID, zones)["xt_goal"].iloc[0] == pytest.approx(
        -zones.loc[0, "p_goal"])
    pm = player_match_values(value_actions(forward, GRID, zones))
    assert pm["xt_goal_pass"].iloc[0] == pytest.approx(expected)


def test_dead_ball_actions_are_not_valued():
    acts = _actions([(1, "pass", LEFT, "complete", "goal", "goal")])
    acts["is_dead_ball"] = True
    zones = fit_chain(_actions([(1, "pass", LEFT, "complete", "goal", "goal")]), GRID,
                      ChainSpec("strict", False))
    assert value_actions(acts, GRID, zones).empty
