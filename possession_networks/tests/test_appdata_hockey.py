"""Hockey explorer payload: time, shots without end points, jersey names, shape of the meta."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from possnet.appdata.build import FEED_FIELDS, write_data_js
from possnet.appdata.hockey import build_hockey_matches, hockey_meta

M = "g1"
HOME, AWAY = "Team D", "Team A"


def _tables():
    def row(i, period, t, team, kind, pid, x, y, x2=None, y2=None, rec=None, out=None, dead=False):
        home = team == HOME
        return {"match_id": M, "event_index": i, "period": period, "game_time_s": t,
                "team_id": team, "is_home": home, "player_id": pid,
                "player_name": None if pid is None else pid.replace(":", " #"),
                "event_type": kind, "outcome": out, "x_start": x, "y_start": y,
                "x_end": x2, "y_end": y2, "recipient_id": rec,
                "recipient_name": None if rec is None else rec.replace(":", " #"),
                "is_dead_ball": dead}
    ev = pd.DataFrame([
        row(1, 1, 0.0, HOME, "duel", f"{HOME}:77", 0, 0, dead=True),
        row(2, 1, 5.0, HOME, "pass", f"{HOME}:77", 10, 5, 30, 6, f"{HOME}:42", "complete"),
        row(3, 1, 9.0, HOME, "pass", f"{HOME}:42", 30, 6, 50, 0, None, "incomplete"),
        row(4, 1, 12.0, AWAY, "takeaway", f"{AWAY}:5", -50, 0),
        row(5, 1, 20.0, HOME, "shot", f"{HOME}:42", 40, 3, None, None, None, "goal"),
        row(6, 2, 1210.0, AWAY, "shot", f"{AWAY}:5", 30, -2, None, None, None, "saved"),
        row(7, 3, 2410.0, AWAY, "pass", f"{AWAY}:5", 0, 0, 5, 5, f"{AWAY}:29", "complete"),
        row(8, 4, 3605.0, HOME, "shot", f"{HOME}:77", 25, 0, None, None, None, "goal"),
    ])
    matches = pd.DataFrame([{
        "match_id": M, "match_date": "2025-10-11", "home_team_id": HOME, "home_team_name": HOME,
        "away_team_id": AWAY, "away_team_name": AWAY, "home_score": 2, "away_score": 0,
        "field_length_m": 60.96, "field_width_m": 25.908}])
    app = pd.DataFrame([
        {"match_id": M, "team_id": HOME, "player_id": f"{HOME}:77", "minutes_played": 20.0},
        {"match_id": M, "team_id": AWAY, "player_id": f"{AWAY}:5", "minutes_played": 15.0},
        {"match_id": M, "team_id": AWAY, "player_id": f"{AWAY}:99", "minutes_played": 0.0},
    ])
    return matches, ev, app


def test_entry_uses_continuous_game_time_and_period_breaks():
    teams, players, entries = build_hockey_matches(*_tables())
    e = entries[0]
    assert teams == [AWAY, HOME]
    assert e["pb"] == [1210.0, 2410.0, 3605.0]
    assert e["ht"] == 1210.0 and e["end"] == 3605.0
    assert (e["hs"], e["as"]) == (2, 0)
    assert players[0].startswith("Team A")


def test_feed_fields_are_aligned_and_ordered():
    _, _, entries = build_hockey_matches(*_tables())
    ev = entries[0]["ev"]
    assert set(ev) == set(FEED_FIELDS)
    assert len({len(v) for v in ev.values()}) == 1
    assert all(b > a for a, b in zip(ev["t"], ev["t"][1:], strict=False))


def test_pass_without_end_is_dropped_and_shots_fly_to_the_net():
    matches, ev, app = _tables()
    ev.loc[ev["event_index"] == 7, "x_end"] = np.nan
    _, _, entries = build_hockey_matches(matches, ev, app)
    feed = entries[0]["ev"]
    assert len(feed["t"]) == 7
    shot = [i for i, k in enumerate(feed["k"]) if k & 7 == 3][0]
    assert (feed["x1"][shot], feed["y1"][shot]) == (30, 0)     # half the 60.96 m rink, rounded
    assert feed["u"][shot] > 0


def test_goals_shots_and_sides():
    _, _, entries = build_hockey_matches(*_tables())
    e = entries[0]
    assert [g[1] for g in e["goals"]] == [0, 0]
    assert [s[1] for s in e["shots"]] == [0, 1, 0]
    assert all(s[2] == 0.0 for s in e["shots"])
    goal_flags = [(k >> 5) & 1 for k in e["ev"]["k"] if k & 7 == 3]
    assert goal_flags == [1, 0, 1]


def test_complete_and_missed_passes_use_the_pass_kinds():
    _, players, entries = build_hockey_matches(*_tables())
    ev = entries[0]["ev"]
    kinds = [k & 7 for k in ev["k"]]
    assert kinds.count(0) == 2 and kinds.count(1) == 1
    first = kinds.index(0)
    assert players[ev["r"][first]] == "Team D #42"


def test_lineup_has_players_with_minutes_only():
    _, players, entries = build_hockey_matches(*_tables())
    lu = entries[0]["lu"]
    assert [players[p[0]] for p in lu["h"]] == ["Team D #77"]
    assert [players[p[0]] for p in lu["a"]] == ["Team A #5"]


def test_meta_and_payload_serialize(tmp_path):
    meta = hockey_meta(60.96, 25.908, 1)
    assert meta["sport"] == "hockey" and meta["tabs"] == ["networks"] and not meta["has_xg"]
    _, players, entries = build_hockey_matches(*_tables())
    payload = {"meta": meta, "teams": [AWAY, HOME], "players": players, "matches": entries,
               "zones": {}, "leaders": {}, "evidence": {"comparisons": [], "windows": {}}}
    out = tmp_path / "data.js"
    assert write_data_js(payload, out) > 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("window.POSSNET = ")
    assert json.loads(text[len("window.POSSNET = "):-2])["meta"]["pitch"] == pytest.approx(
        [60.96, 25.908])


def test_hockey_text_replaces_every_soccer_sentence_the_networks_view_uses():
    text = hockey_meta(60.96, 25.908, 1)["text"]
    assert {"how", "legend", "start_pill", "tl_hint", "minw_hint"} <= set(text)
    assert set(text["how"]) == {"live", "net"}
    assert "carry" not in text["legend"]["live"].lower() and "xg" not in json.dumps(text).lower()
    assert "Layout" not in json.dumps(text) and "assigned" not in text["how"]["net"]


def test_soccer_meta_names_its_sport_and_writes_its_own_file():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "scripts" / "11_build_app_data.py"
    assert "data_soccer.js" in src.read_text(encoding="utf-8")
    hockey = src.parent / "11b_build_app_data_hockey.py"
    assert "data_hockey.js" in hockey.read_text(encoding="utf-8")
