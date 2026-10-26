"""Unit tests for the StatsBomb adapter."""

from __future__ import annotations

import math

import pytest

from possnet.adapters.statsbomb import YARD_M, position_group
from possnet.schema import contract as c


def test_columns_and_order_match_contract(tables):
    for name, frame in tables.items():
        assert list(frame.columns) == c.column_names(name)


def test_coordinate_transform_center_and_corners(tables):
    ev = tables["events"].set_index("event_index")
    # Pass 4 starts at StatsBomb (60, 40) = center of the pitch.
    assert ev.loc[4, "x_start"] == pytest.approx(0.0)
    assert ev.loc[4, "y_start"] == pytest.approx(0.0)
    # End (70, 30): 10 yards toward goal, 10 yards to the attacker's RIGHT => y negative.
    assert ev.loc[4, "x_end"] == pytest.approx(10 * YARD_M)
    assert ev.loc[4, "y_end"] == pytest.approx(10 * YARD_M)  # 40 - 30 = +10 => left
    # Pass 11 (AWAY) at y=60 (StatsBomb) is on the attacker's right => negative y.
    assert ev.loc[11, "y_start"] == pytest.approx(-20 * YARD_M)
    # Shot end at the goal line.
    assert ev.loc[6, "x_end"] == pytest.approx(60 * YARD_M)


def test_events_without_location_are_nan(tables):
    ev = tables["events"].set_index("event_index")
    assert math.isnan(ev.loc[1, "x_start"])


def test_outcomes_and_types(tables):
    ev = tables["events"].set_index("event_index")
    assert ev.loc[4, "outcome"] == "complete"
    assert ev.loc[11, "outcome"] == "incomplete"
    assert ev.loc[6, "outcome"] == "goal"
    assert ev.loc[6, "xg"] == pytest.approx(0.3)
    assert ev.loc[5, "event_type"] == "reception"
    assert ev.loc[3, "event_type"] == "stoppage"
    assert ev.loc[4, "recipient_id"] == "102"


def test_clocks(tables):
    ev = tables["events"].set_index("event_index")
    assert ev.loc[9, "period_time_s"] == pytest.approx(600.0)
    assert ev.loc[9, "game_time_s"] == pytest.approx(2700.0 + 600.0)


@pytest.mark.parametrize("name,expected", [
    ("Goalkeeper", "goalkeeper"), ("Right Wing Back", "defender"),
    ("Center Back", "defender"), ("Left Defensive Midfield", "midfielder"),
    ("Center Attacking Midfield", "midfielder"), ("Right Wing", "forward"),
    ("Secondary Striker", "forward"), (None, None),
])
def test_position_group(name, expected):
    assert position_group(name) == expected


def test_appearance_minutes_use_events_not_lineup_stints(tables):
    app = tables["appearances"].set_index("player_id")
    # Real duration: 46:00 + 47:00 = 93 minutes.
    assert app.loc["101", "minutes_played"] == pytest.approx(93.0)
    # Away player 11 substituted off at 46:00 + 10:00 = 56 minutes.
    assert app.loc["211", "minutes_played"] == pytest.approx(56.0)
    # Substitute entered at 56:00, plays 37 minutes.
    assert app.loc["299", "minutes_played"] == pytest.approx(37.0)
    assert not bool(app.loc["299", "started"])
    # Away player 10 sent off at 46:00 + 20:00 = 66 minutes.
    assert app.loc["210", "minutes_played"] == pytest.approx(66.0)
    assert int(tables["appearances"].query("started and team_id == '1'").shape[0]) == 11


def test_dead_ball_flag(tables):
    ev = tables["events"].set_index("event_index")
    assert not bool(ev.loc[4, "is_dead_ball"])  # open play pass
    assert not bool(ev.loc[6, "is_dead_ball"])  # open play shot
    assert ev["is_dead_ball"].dtype.name == "boolean"


def test_dead_ball_flag_for_restart_types():
    from possnet.adapters.statsbomb import _is_dead_ball

    assert _is_dead_ball({"pass": {"type": {"name": "Throw-in"}}}, "pass")
    assert _is_dead_ball({"pass": {"type": {"name": "Goal Kick"}}}, "pass")
    assert not _is_dead_ball({"pass": {"type": {"name": "Recovery"}}}, "pass")
    assert not _is_dead_ball({"pass": {}}, "pass")
    assert _is_dead_ball({"shot": {"type": {"name": "Penalty"}}}, "shot")
    assert not _is_dead_ball({"shot": {"type": {"name": "Open Play"}}}, "shot")
    assert not _is_dead_ball({}, "carry")
