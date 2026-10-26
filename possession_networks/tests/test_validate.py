"""The validator must pass clean data and catch deliberately injected faults."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from possnet.validate.checks import validate_tables


def _failed(report, name: str) -> bool:
    frame = report.to_frame().set_index("name")
    return not bool(frame.loc[name, "passed"])


def _run(tables, **overrides):
    t = {k: v.copy() for k, v in tables.items()}
    t.update(overrides)
    return validate_tables(t["matches"], t["events"], t["appearances"])


def test_clean_synthetic_data_has_no_errors(tables):
    report = _run(tables)
    errors = report.to_frame().query("severity == 'error' and not passed")
    assert report.ok, errors.to_string()


def test_catches_out_of_bounds_coordinates(tables):
    ev = tables["events"].copy()
    ev.loc[ev.event_type == "pass", "x_start"] = 500.0
    assert _failed(_run(tables, events=ev), "events.coordinates_within_surface")


def test_catches_missing_pass_end(tables):
    ev = tables["events"].copy()
    ev.loc[ev.event_type == "pass", "x_end"] = np.nan
    assert _failed(_run(tables, events=ev), "events.end_types_have_end")


def test_catches_complete_pass_without_recipient(tables):
    ev = tables["events"].copy()
    ev.loc[(ev.event_type == "pass") & (ev.outcome == "complete"), "recipient_id"] = pd.NA
    assert _failed(_run(tables, events=ev), "passes.complete_have_recipient")


def test_catches_recipient_on_other_team(tables):
    ev = tables["events"].copy()
    mask = (ev.event_type == "pass") & (ev.outcome == "complete")
    ev.loc[mask, "recipient_id"] = "201"
    assert _failed(_run(tables, events=ev), "passes.recipient_on_passing_team")


def test_catches_duplicate_event_ids(tables):
    ev = tables["events"].copy()
    ev.loc[1, "event_id"] = ev.loc[0, "event_id"]
    assert _failed(_run(tables, events=ev), "events.event_id_unique")


def test_catches_goal_score_mismatch(tables):
    m = tables["matches"].copy()
    m["home_score"] = 3
    assert _failed(_run(tables, matches=m), "matches.goals_match_score")


def test_catches_possession_team_conflict(tables):
    ev = tables["events"].copy()
    idx = ev.index[ev.possession_id == 1][:2]
    ev.loc[idx[0], "possession_team_id"] = "1"
    ev.loc[idx[1], "possession_team_id"] = "2"
    assert _failed(_run(tables, events=ev), "possession.team_constant")


def test_catches_minutes_above_duration(tables):
    app = tables["appearances"].copy()
    app.loc[0, "minutes_played"] = 500.0
    assert _failed(_run(tables, appearances=app), "appearances.minutes_in_range")


def test_catches_bad_enum_value(tables):
    ev = tables["events"].copy()
    ev.loc[0, "event_type"] = "banana"
    assert _failed(_run(tables, events=ev), "events.allowed_values")


def test_catches_missing_contract_column(tables):
    ev = tables["events"].drop(columns=["period"])
    report = _run(tables, events=ev)
    assert not report.ok
    assert _failed(report, "events.columns_present")


def test_catches_event_for_player_without_appearance(tables):
    app = tables["appearances"]
    app = app[app.player_id != "101"]
    assert _failed(_run(tables, appearances=app), "events.player_has_appearance")


@pytest.mark.parametrize("col", ["match_id", "team_id", "event_type"])
def test_catches_nulls_in_required_columns(tables, col):
    ev = tables["events"].copy()
    ev.loc[0, col] = pd.NA
    assert _failed(_run(tables, events=ev), "events.non_nullable_columns")
