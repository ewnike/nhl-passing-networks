"""Tests for the Stathletes adapter, using small synthetic games (no licensed data)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from possnet.adapters import stathletes as ad
from possnet.sources import stathletes as st
from possnet.validate.checks import validate_tables

FT = 0.3048
# Away is listed as defending the right side in period 1, so Team D (home) attacks +x.
GAME = st.Game("2025-10-11 Team A @ Team D", "2025-10-11", "Team A", "Team D", "Away")
HOME, AWAY = "Team D", "Team A"


def _row(period, clock, team, event, pid=None, x=0.0, y=0.0, d1=None, d2=None, p2=None,
         x2=None, y2=None, home_sk=5, away_sk=5):
    return {
        "Date": "2025-10-11", "Home_Team": HOME, "Away_Team": AWAY, "Period": period,
        "Clock": clock, "Home_Team_Skaters": home_sk, "Away_Team_Skaters": away_sk,
        "Home_Team_Goals": 0, "Away_Team_Goals": 0, "Team": team, "Player_Id": pid,
        "Event": event, "X_Coordinate": x, "Y_Coordinate": y, "Detail_1": d1, "Detail_2": d2,
        "Detail_3": 0, "Detail_4": 0, "Player_Id_2": p2, "X_Coordinate_2": x2,
        "Y_Coordinate_2": y2,
    }


def _read(rows, tmp_path, columns=st.EVENT_COLUMNS):
    path = tmp_path / "x.csv"
    pd.DataFrame(rows, columns=list(columns)).to_csv(path, index=False)
    return st.read_csv_text(path)


def _events(tmp_path, rows=None):
    rows = rows or _period_one_rows()
    return ad.events_to_frame(_read(rows, tmp_path), GAME)


def _period_one_rows():
    return [
        _row(1, "20:00", HOME, "Faceoff Win", "77", 0, 0.5, d1="Backhand", p2="63"),
        _row(1, "19:57", HOME, "Play", "77", 10, 5, d1="Direct", p2="42", x2=30, y2=6),
        _row(1, "19:55", AWAY, "Puck Recovery", "5", -50, 10),
        _row(1, "19:54", AWAY, "Play", "5", -50, 10, d1="Indirect", p2="29", x2=-70, y2=0),
        _row(1, "19:52", AWAY, "Shot", "29", -70, 0, d1="Wristshot", d2="Blocked"),
        _row(1, "19:50", AWAY, "Play", "29", -60, 5, d1="Direct", p2=None, x2=-40, y2=5),
        _row(1, "19:48", HOME, "Penalty Taken", "42", -30, 5, d1="Hooking", p2="5"),
        _row(1, "19:40", HOME, "Incomplete Play", "42", 20, 5, d1="Direct", p2="88",
             x2=40, y2=0, home_sk=5, away_sk=4),
        _row(1, "19:39", HOME, "Dump In/Out", "88", 40, 0, d1="Lost", home_sk=5, away_sk=4),
        _row(1, "19:30", AWAY, "Goal", "5", -80, 3, d1="Snapshot", d2="On Net",
             home_sk=5, away_sk=4),
        _row(1, "19:29", HOME, "Zone Entry", "88", 25, -3, d1="Carried", p2="52"),
        _row(1, "19:28", HOME, "Shot", "88", 60, 2, d1="Slapshot", d2="On Net"),
        _row(1, "19:27", HOME, "Shot", "88", 60, 2, d1="Slapshot", d2="Missed"),
        _row(1, "19:20", HOME, "Mystery Event", "88", 0, 0),
    ]


# ----------------------------------------------------------------------- frames
@pytest.mark.parametrize("side, period, home, away", [
    ("Away", 1, 1, -1), ("Away", 2, -1, 1), ("Away", 3, 1, -1),
    ("Home", 1, -1, 1), ("Home", 2, 1, -1), ("Home", 3, -1, 1),
    ("Away", 4, 1, 1), ("Home", 4, 1, 1),  # overtime is already in the acting team frame
])
def test_attack_sign_rule(side, period, home, away):
    got = ad.attack_sign([period, period], [True, False], side)
    assert got.tolist() == [home, away]


def test_clock_and_period_lengths():
    clock = pd.Series(["20:00", "19:57", "00:00", "05:00", "04:59"])
    assert ad.clock_seconds(clock).tolist() == [1200, 1197, 0, 300, 299]
    period = pd.Series([1, 1, 1, 4, 4])
    lengths = ad.period_lengths(period, ad.clock_seconds(clock))
    assert lengths == {1: 1200.0, 4: 300.0}
    long_ot = ad.period_lengths(pd.Series([4, 4]), pd.Series([1200, 800]))
    assert long_ot == {4: 1200.0}  # a 20 minute overtime is not mistaken for a 5 minute one


def test_time_conversion(tmp_path):
    rows = [_row(1, "20:00", HOME, "Faceoff Win", "77"), _row(1, "19:57", HOME, "Play", "77",
            p2="42", x2=1, y2=1),
            _row(2, "10:00", HOME, "Puck Recovery", "42"),
            _row(4, "05:00", HOME, "Faceoff Win", "77"),
            _row(4, "04:59", HOME, "Puck Recovery", "42")]
    ev = _events(tmp_path, rows)
    assert ev["period_time_s"].tolist() == [0.0, 3.0, 600.0, 0.0, 1.0]
    assert ev["game_time_s"].tolist() == [0.0, 3.0, 1800.0, 3600.0, 3601.0]
    assert ev["event_index"].tolist() == [1, 2, 3, 4, 5]
    assert ev["event_id"].is_unique


def test_coordinates_use_the_acting_team_frame(tmp_path):
    rows = [
        _row(1, "19:57", HOME, "Play", "77", 10, 5, p2="42", x2=30, y2=6),    # home attacks +x
        _row(1, "19:50", AWAY, "Play", "5", -50, 10, p2="29", x2=-70, y2=-4),  # away attacks -x
        _row(2, "10:00", HOME, "Play", "77", 10, 5, p2="42", x2=30, y2=6),     # sides swap
        _row(4, "04:00", AWAY, "Play", "5", 50, 10, p2="29", x2=70, y2=-4),    # overtime as is
    ]
    ev = _events(tmp_path, rows)
    got = ev[["x_start", "y_start", "x_end", "y_end"]].to_numpy()
    expected = np.array([
        [10, 5, 30, 6],
        [50, -10, 70, 4],     # rotated 180 degrees: both axes negated
        [-10, -5, -30, -6],
        [50, 10, 70, -4],
    ]) * FT
    assert np.allclose(got, expected)


def test_event_mapping(tmp_path):
    ev = _events(tmp_path).set_index("event_index")
    assert ev.loc[1, ["event_type", "event_subtype", "outcome"]].tolist() == [
        "duel", "Faceoff Win", "success"]
    assert bool(ev.loc[1, "is_dead_ball"]) and not ev["is_dead_ball"].iloc[1:].any()
    assert ev.loc[2, ["event_type", "event_subtype", "outcome", "recipient_id"]].tolist() == [
        "pass", "Direct", "complete", "Team D:42"]
    assert ev.loc[3, "event_type"] == "takeaway"
    assert ev.loc[5, ["event_type", "event_subtype", "outcome"]].tolist() == [
        "shot", "Wristshot", "blocked"]
    assert pd.isna(ev.loc[5, "x_end"])            # shots have a release point only
    assert pd.isna(ev.loc[6, "recipient_id"]) and ev.loc[6, "outcome"] == "complete"
    assert ev.loc[7, ["event_type", "event_subtype"]].tolist() == ["foul", "Hooking"]
    assert ev.loc[8, ["outcome", "recipient_id"]].tolist() == ["incomplete", "Team D:88"]
    assert ev.loc[9, ["event_type", "outcome"]].tolist() == ["clearance", "failure"]
    assert ev.loc[10, ["event_type", "outcome"]].tolist() == ["shot", "goal"]
    assert ev.loc[11, ["event_type", "event_subtype"]].tolist() == ["other", "Zone Entry Carried"]
    assert pd.isna(ev.loc[11, "recipient_id"])    # the targeted defender is not a recipient
    assert [ev.loc[12, "outcome"], ev.loc[13, "outcome"]] == ["saved", "off_target"]
    assert ev.loc[14, ["event_type", "event_subtype"]].tolist() == ["other", "Mystery Event"]


def test_player_ids_labels_and_missing_ids(tmp_path):
    rows = [_row(1, "19:00", HOME, "Play", "77", p2="Go", x2=1, y2=1),
            _row(1, "18:59", HOME, "Play", None, p2="42", x2=1, y2=1),
            _row(1, "18:58", HOME, "Puck Recovery", "Go")]
    ev = _events(tmp_path, rows)
    assert ev["player_id"].tolist()[0] == "Team D:77"
    assert ev["recipient_id"].tolist()[0] == "Team D:Go"
    assert pd.isna(ev["player_id"].iloc[1]) and pd.isna(ev["player_name"].iloc[1])
    assert ev["player_name"].tolist()[0] == "Team D #77"
    assert ev["player_name"].iloc[2] == "Team D goalie"
    assert ev["position_group"].iloc[2] == "goalkeeper" and pd.isna(ev["position_group"].iloc[0])


def test_strength_state_is_from_the_acting_team_view(tmp_path):
    rows = [_row(1, "19:00", HOME, "Puck Recovery", "77", home_sk=5, away_sk=4),
            _row(1, "18:59", AWAY, "Puck Recovery", "5", home_sk=5, away_sk=4),
            _row(1, "18:58", AWAY, "Puck Recovery", "5", home_sk=6, away_sk=5)]
    assert _events(tmp_path, rows)["strength_state"].tolist() == ["5v4", "4v5", "5v6"]


def test_possession_rules(tmp_path):
    ev = _events(tmp_path)
    by_index = ev.set_index("event_index")
    pid = by_index["possession_id"]
    assert pid[1] == pid[2] == 1                  # faceoff, then home pass: one possession
    assert by_index.loc[1, "play_pattern"] == "restart"
    assert pid[3] == pid[4] == pid[5] == 2        # team change starts a possession
    assert pid[6] == 3                            # the shot ended the previous one
    assert pid[7] == pid[6]                       # a penalty carries the running possession
    assert pid[8] == 4                            # home team again
    assert pid[9] == 4 and pid[10] == 5
    assert pid[11] == 6                           # after a goal, a new possession
    assert by_index.loc[6, "play_pattern"] == "open_play"
    # the possession team never changes inside a possession
    assert (ev.groupby("possession_id")["possession_team_id"].nunique() == 1).all()


def test_a_dump_that_gives_up_the_puck_ends_the_possession(tmp_path):
    rows = [_row(1, "19:00", HOME, "Dump In/Out", "88", 40, 0, d1="Lost"),
            _row(1, "18:58", HOME, "Puck Recovery", "77", 60, 0),   # same team, new possession
            _row(1, "18:55", HOME, "Dump In/Out", "88", 40, 0, d1="Retained"),
            _row(1, "18:54", HOME, "Puck Recovery", "77", 60, 0)]   # retained: same possession
    assert _events(tmp_path, rows)["possession_id"].tolist() == [1, 2, 2, 2]


def test_periods_start_new_possessions(tmp_path):
    rows = [_row(1, "00:30", HOME, "Puck Recovery", "77"), _row(2, "20:00", HOME, "Puck Recovery",
            "77")]
    ev = _events(tmp_path, rows)
    assert ev["possession_id"].tolist() == [1, 2]


# ------------------------------------------------------- appearances and matches
SHIFT_COLUMNS = st.SHIFT_COLUMNS


def _shift(team, pid, period, start, end, n=1):
    return {"Date": "2025-10-11", "Home_Team": HOME, "Away_Team": AWAY, "Team": team,
            "Player_Id": pid, "shift_number": n, "period": period, "start_clock": start,
            "end_clock": end, "shift_length": "00:00"}


def test_appearances_from_shifts(tmp_path):
    rows = [_shift(HOME, "77", 1, "20:00", "19:00"), _shift(HOME, "77", 1, "10:00", "09:30", 2),
            _shift(HOME, "Go", 1, "20:00", "00:00"), _shift(AWAY, "5", 1, "15:00", "14:00"),
            _shift(AWAY, "5", 2, "20:00", "19:30", 2)]
    app = ad.appearances_from_shifts(_read(rows, tmp_path, SHIFT_COLUMNS), GAME)
    got = app.set_index("player_id")
    assert got.loc["Team D:77", "minutes_played"] == pytest.approx(1.5)
    assert bool(got.loc["Team D:77", "started"]) and not bool(got.loc["Team A:5", "started"])
    assert got.loc["Team D:Go", "position_group"] == "goalkeeper"
    assert got.loc["Team D:77", "jersey_number"] == 77
    assert pd.isna(got.loc["Team D:Go", "jersey_number"])
    assert got.loc["Team A:5", "minutes_played"] == pytest.approx(1.5)  # shifts in two periods


def test_overtime_shift_clocks_are_clamped(tmp_path):
    rows = [_shift(HOME, "Go", 4, "20:00", "00:00")]
    app = ad.appearances_from_shifts(_read(rows, tmp_path, SHIFT_COLUMNS), GAME, {4: 300.0})
    assert app["minutes_played"].iloc[0] == pytest.approx(5.0)


def test_a_shift_that_ends_after_it_starts_is_rejected(tmp_path):
    rows = [_shift(HOME, "77", 1, "10:00", "11:00")]
    with pytest.raises(ValueError, match="ends after it starts"):
        ad.appearances_from_shifts(_read(rows, tmp_path, SHIFT_COLUMNS), GAME)


def test_final_scores_are_goal_counts(tmp_path):
    ev = _events(tmp_path)
    match = ad.matches_to_frame([GAME], ev).iloc[0]
    assert (match["home_score"], match["away_score"]) == (0, 1)
    assert match["sport"] == "hockey" and match["regulation_periods"] == 3
    assert match["field_length_m"] == pytest.approx(200 * FT)


# --------------------------------------------------------------------- validator
def _synthetic_tables(tmp_path):
    ev = _events(tmp_path)
    home = ["77", "42", "88", "63", "8", "Go"]
    away = ["5", "29", "48", "52", "92", "Go"]
    shifts = [_shift(HOME, p, 1, "20:00", "00:00") for p in home]
    shifts += [_shift(AWAY, p, 1, "20:00", "00:00") for p in away]
    app = ad.appearances_from_shifts(_read(shifts, tmp_path, SHIFT_COLUMNS), GAME)
    return ad.matches_to_frame([GAME], ev), ev, app


def test_validator_has_no_errors_on_clean_hockey_data(tmp_path):
    matches, ev, app = _synthetic_tables(tmp_path)
    report = validate_tables(matches, ev, app)
    frame = report.to_frame().set_index("name")
    assert report.ok, frame[~frame.passed].to_string()
    # shots have no end location in hockey, which must not be an error
    assert frame.loc["events.end_types_have_end", "passed"]
    # the pass with no recorded receiver is a warning, not an error
    warn = frame.loc["passes.complete_have_recipient_hockey"]
    assert warn["severity"] == "warn" and warn["n_failing"] == 1


def test_validator_catches_hockey_faults(tmp_path):
    matches, ev, app = _synthetic_tables(tmp_path)
    bad = ev.copy()
    bad.loc[bad.event_index == 2, "x_start"] = 500.0
    assert not validate_tables(matches, bad, app).ok
    wrong_score = matches.assign(home_score=5)
    assert not validate_tables(wrong_score, ev, app).ok
    too_long = app.assign(minutes_played=app["minutes_played"] * 3)
    assert not validate_tables(matches, ev, too_long).ok


def test_soccer_shots_still_need_an_end_location(tables):
    ev = tables["events"].copy()
    ev.loc[ev.event_type == "shot", "x_end"] = np.nan
    report = validate_tables(tables["matches"], ev, tables["appearances"])
    assert not report.to_frame().set_index("name").loc["events.end_types_have_end", "passed"]


def test_direction_report_flags_a_wrong_flip(tmp_path):
    ev = _events(tmp_path)
    assert ad.attack_direction_report(ev)["ok"].all()
    flipped = ev.assign(x_start=-ev["x_start"])
    assert not ad.attack_direction_report(flipped)["ok"].any()


# ------------------------------------------------------------------ orchestrator
def test_build_canonical_end_to_end(tmp_path):
    cache = tmp_path / "raw" / "bdc_test"
    cache.mkdir(parents=True)
    rows = _period_one_rows()
    pd.DataFrame(rows, columns=list(st.EVENT_COLUMNS)).to_csv(cache / GAME.asset("Events"),
                                                              index=False)
    shifts = [_shift(HOME, p, 1, "20:00", "00:00") for p in ("77", "42", "88", "63", "8", "Go")]
    shifts += [_shift(AWAY, p, 1, "20:00", "00:00") for p in ("5", "29", "48", "52", "92", "Go")]
    pd.DataFrame(shifts, columns=list(SHIFT_COLUMNS)).to_csv(cache / GAME.asset("Shifts"),
                                                             index=False)
    manifest = {
        "cache_dir": "raw/bdc_test",
        "games": [{**{k: getattr(GAME, k) for k in (
            "name", "date", "away_team", "home_team", "goalie_team_on_right_p1")}}],
    }
    tables = ad.build_canonical(json.loads(json.dumps(manifest)), tmp_path)
    assert {k: len(v) for k, v in tables.items()} == {"matches": 1, "events": 14,
                                                      "appearances": 12}
    assert validate_tables(tables["matches"], tables["events"], tables["appearances"]).ok
