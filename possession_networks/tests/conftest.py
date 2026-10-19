"""Synthetic StatsBomb style match used by the unit tests (no licensed data involved)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from possnet.adapters.statsbomb import (
    appearances_from_events,
    events_to_frame,
    matches_to_frame,
    period_durations,
)

HOME, AWAY = 1, 2
MATCH_ID = 9001


def _ev(index: int, kind: str, team: int, period: int, ts: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": f"ev-{index}", "index": index, "period": period, "timestamp": ts,
        "type": {"name": kind}, "team": {"id": team, "name": f"T{team}"},
        "possession": extra.pop("possession", 1),
        "possession_team": {"id": extra.pop("possession_team", team), "name": "x"},
        "play_pattern": {"name": "Regular Play"}, **extra,
    }


def _player(team: int, n: int) -> dict[str, Any]:
    return {"id": team * 100 + n, "name": f"P{team}_{n}"}


def synthetic_raw() -> tuple[list[dict], list[dict], dict]:
    xi = {t: [{"player": _player(t, n), "position": {"name": "Center Midfield"},
               "jersey_number": n} for n in range(1, 12)] for t in (HOME, AWAY)}
    events = [
        _ev(1, "Starting XI", HOME, 1, "00:00:00.000", tactics={"lineup": xi[HOME]}),
        _ev(2, "Starting XI", AWAY, 1, "00:00:00.000", possession_team=HOME,
            tactics={"lineup": xi[AWAY]}),
        _ev(3, "Half Start", HOME, 1, "00:00:00.000"),
        _ev(4, "Pass", HOME, 1, "00:00:05.000", player=_player(HOME, 1),
            position={"name": "Center Midfield"}, location=[60.0, 40.0],
            **{"pass": {"recipient": _player(HOME, 2), "end_location": [70.0, 30.0]}}),
        _ev(5, "Ball Receipt*", HOME, 1, "00:00:06.000", player=_player(HOME, 2),
            position={"name": "Center Midfield"}, location=[70.0, 30.0]),
        _ev(6, "Shot", HOME, 1, "00:10:00.000", possession=2, player=_player(HOME, 2),
            position={"name": "Center Midfield"}, location=[105.0, 40.0],
            shot={"statsbomb_xg": 0.3, "end_location": [120.0, 40.0, 1.0],
                  "outcome": {"name": "Goal"}, "type": {"name": "Open Play"}}),
        _ev(7, "Half End", HOME, 1, "00:46:00.000"),
        _ev(8, "Half Start", HOME, 2, "00:00:00.000"),
        _ev(9, "Substitution", AWAY, 2, "00:10:00.000", possession=3, possession_team=AWAY,
            player=_player(AWAY, 11), position={"name": "Center Midfield"},
            substitution={"replacement": {"id": 299, "name": "Sub"}}),
        _ev(10, "Foul Committed", AWAY, 2, "00:20:00.000", possession=3,
            player=_player(AWAY, 10), position={"name": "Center Midfield"},
            location=[40.0, 40.0], foul_committed={"card": {"name": "Red Card"}}),
        _ev(11, "Pass", AWAY, 2, "00:30:00.000", possession=4, player=_player(AWAY, 1),
            position={"name": "Center Midfield"}, location=[30.0, 60.0],
            **{"pass": {"recipient": _player(AWAY, 2), "end_location": [40.0, 50.0],
                        "outcome": {"name": "Incomplete"}}}),
        _ev(12, "Half End", HOME, 2, "00:47:00.000", possession=4, possession_team=AWAY),
    ]
    lineups = [
        {"team_id": t, "team_name": f"T{t}", "lineup": [
            {"player_id": _player(t, n)["id"], "player_name": _player(t, n)["name"],
             "jersey_number": n, "positions": []} for n in range(1, 12)]}
        for t in (HOME, AWAY)
    ]
    lineups[1]["lineup"].append(
        {"player_id": 299, "player_name": "Sub", "jersey_number": 12, "positions": []})
    match = {
        "match_id": MATCH_ID, "match_date": "2020-01-01",
        "competition": {"competition_id": 1}, "season": {"season_id": 2, "season_name": "S"},
        "competition_stage": {"name": "Regular Season"},
        "home_team": {"home_team_id": HOME, "home_team_name": f"T{HOME}"},
        "away_team": {"away_team_id": AWAY, "away_team_name": f"T{AWAY}"},
        "home_score": 1, "away_score": 0, "metadata": {"data_version": "test"},
    }
    return events, lineups, match


@pytest.fixture()
def tables() -> dict[str, pd.DataFrame]:
    raw, lineups, match = synthetic_raw()
    ev = events_to_frame(raw, MATCH_ID, HOME)
    return {
        "matches": matches_to_frame([match], "Test League"),
        "events": ev,
        "appearances": appearances_from_events(raw, lineups, MATCH_ID, period_durations(ev)),
    }
