"""Map the Stathletes Big Data Cup 2026 files to the canonical tables in possnet.schema.contract.

Source specification
--------------------
Field meanings follow the competition README (https://github.com/bigdatacup/Big-Data-Cup-2026)
and the checks recorded in ``docs/decisions.md`` D22 and D23. All code in this module is
original work written for this project.

What the source gives, and how it is mapped
-------------------------------------------
* Coordinates are in feet, centered on the middle of the ice (x from minus 100 to 100, y from
  minus 42.5 to 42.5), with +x to the right and +y up on the camera view. Canonical
  coordinates are meters in the acting team's attacking frame, so a team attacking toward
  minus x has x and y both negated (a 180 degree rotation keeps the left and right sides
  of the team correct).
* Periods 1 to 3 are in the camera frame. The team defending the right side in period 1 is
  given in camera_orientations.csv, and sides swap every period. Overtime coordinates are
  already in the acting team's own frame (verified, see D23), so no flip is applied there.
* Player ids in the files are jersey numbers. The canonical player id is
  ``<team>:<jersey>`` (for example ``Team A:77``), and ``Team A:Go`` is that team's goalie.
* The source has no possession id, no player positions, and no goals as shots without a
  separate Goal event. Possessions are derived here (see ``assign_possessions``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from possnet.schema import contract as c
from possnet.schema.frame import coerce_frame
from possnet.sources.stathletes import Game, games_from_manifest, read_csv_text

SOURCE = "stathletes"
FOOT_M = 0.3048
FIELD_LENGTH_M = 200 * FOOT_M
FIELD_WIDTH_M = 85 * FOOT_M
REGULATION_PERIODS = 3
GOALIE_ID = "Go"

COMPETITION_ID = "bdc"
COMPETITION_NAME = "Stathletes Big Data Cup 2026"
SEASON_ID = "2025_26"
SEASON_NAME = "2025/2026"

TYPE_MAP = {
    "Play": "pass", "Incomplete Play": "pass",
    "Shot": "shot", "Goal": "shot",
    "Puck Recovery": "takeaway", "Takeaway": "takeaway",
    "Dump In/Out": "clearance",
    "Zone Entry": "other",
    "Faceoff Win": "duel",
    "Penalty Taken": "foul",
}
PASS_EVENTS = ("Play", "Incomplete Play")
SHOT_OUTCOME = {"On Net": "saved", "Missed": "off_target", "Blocked": "blocked"}
DUMP_OUTCOME = {"Retained": "success", "Lost": "failure"}
# Events whose Detail_1 is the useful subtype (pass kind, shot type, infraction).
DETAIL_SUBTYPE_EVENTS = ("Play", "Incomplete Play", "Shot", "Goal", "Penalty Taken")


# ---------------------------------------------------------------------- helpers
def clock_seconds(clock: pd.Series) -> pd.Series:
    """Convert an ``mm:ss`` clock column to whole seconds."""
    parts = clock.astype(str).str.split(":", expand=True)
    return parts[0].astype(int) * 60 + parts[1].astype(int)


def attack_sign(period: Any, is_home: Any, goalie_team_on_right_p1: str) -> np.ndarray:
    """+1 where the acting team attacks toward +x in the source frame, else minus 1.

    Periods 1 to 3: the home team attacks +x in period 1 exactly when the Away team defends
    the right side, and sides swap every period. Later periods (overtime) are already in the
    acting team's frame, so the sign is +1 for everyone.
    """
    period = np.asarray(period)
    is_home = np.asarray(is_home, dtype=bool)
    first = 1 if goalie_team_on_right_p1 == "Away" else -1
    home_dir = first * np.where((period - 1) % 2 == 0, 1, -1)
    sign = np.where(is_home, home_dir, -home_dir)
    return np.where(period > REGULATION_PERIODS, 1, sign)


def _label(team: pd.Series, jersey: pd.Series) -> pd.Series:
    """Readable player name: ``Team A #77`` or ``Team A goalie``. Missing if no jersey."""
    name = team + " #" + jersey
    return name.mask(jersey == GOALIE_ID, team + " goalie")


def _team_player_id(team: pd.Series, jersey: pd.Series) -> pd.Series:
    return team.str.cat(jersey, sep=":")  # missing where the jersey is missing


def period_lengths(period: pd.Series, remaining: pd.Series) -> dict[int, float]:
    """Length in seconds of each period present: 1200 s in regulation.

    Overtime counts down from 5:00 in the regular season. If a longer overtime clock is ever
    seen the period is taken as 1200 s.
    """
    longest = remaining.groupby(period).max()
    return {
        int(p): (
            c.HOCKEY_REGULATION_PERIOD_S if p <= REGULATION_PERIODS
            or longest[p] > c.HOCKEY_OVERTIME_PERIOD_S else c.HOCKEY_OVERTIME_PERIOD_S
        )
        for p in longest.index
    }


# ----------------------------------------------------------------------- events
def events_to_frame(raw: pd.DataFrame, game: Game) -> pd.DataFrame:
    """Convert one game's raw events (all columns as text) to the canonical events schema."""
    df = raw.reset_index(drop=True)
    event = df["Event"]
    period = pd.to_numeric(df["Period"]).astype(int)
    remaining = clock_seconds(df["Clock"])
    length = period.map(period_lengths(period, remaining)).astype(float)
    period_time = length - remaining

    team = df["Team"]
    is_home = team == game.home_team
    sign = attack_sign(period.to_numpy(), is_home.to_numpy(), game.goalie_team_on_right_p1)

    def to_m(col: str) -> pd.Series:
        return pd.to_numeric(df[col]) * FOOT_M * sign

    is_pass = event.isin(PASS_EVENTS)
    x_end = to_m("X_Coordinate_2").where(is_pass)
    y_end = to_m("Y_Coordinate_2").where(is_pass)

    detail1 = df["Detail_1"]
    subtype = event.copy()
    use_detail = event.isin(DETAIL_SUBTYPE_EVENTS)
    subtype[use_detail] = detail1[use_detail]
    entry = event == "Zone Entry"
    subtype[entry] = "Zone Entry " + detail1[entry].fillna("Unknown")

    outcome = pd.Series(pd.NA, index=df.index, dtype="object")
    outcome[event == "Play"] = "complete"
    outcome[event == "Incomplete Play"] = "incomplete"
    shots = event == "Shot"
    outcome[shots] = df.loc[shots, "Detail_2"].map(SHOT_OUTCOME).fillna("other")
    outcome[event == "Goal"] = "goal"
    dumps = event == "Dump In/Out"
    outcome[dumps] = detail1[dumps].map(DUMP_OUTCOME)
    outcome[event == "Faceoff Win"] = "success"

    jersey = df["Player_Id"]
    recipient_jersey = df["Player_Id_2"].where(is_pass)
    home_sk = pd.to_numeric(df["Home_Team_Skaters"])
    away_sk = pd.to_numeric(df["Away_Team_Skaters"])
    own = home_sk.where(is_home, away_sk).astype("Int64").astype("string")
    opp = away_sk.where(is_home, home_sk).astype("Int64").astype("string")
    strength = (own + "v" + opp).astype(object)

    frame = pd.DataFrame({
        "source": SOURCE,
        "match_id": game.game_id,
        "period": period,
        "period_time_s": period_time.astype(float),
        "game_time_s": c.HOCKEY_REGULATION_PERIOD_S * (period - 1) + period_time,
        "team_id": team,
        "team_name": team,
        "is_home": is_home,
        "player_id": _team_player_id(team, jersey),
        "player_name": _label(team, jersey),
        "position": pd.NA,
        "position_group": jersey.eq(GOALIE_ID).map({True: "goalkeeper", False: pd.NA}),
        "event_type": event.map(TYPE_MAP).fillna("other"),
        "event_subtype": subtype,
        "is_dead_ball": event.eq("Faceoff Win"),
        "outcome": outcome,
        "x_start": to_m("X_Coordinate"), "y_start": to_m("Y_Coordinate"),
        "x_end": x_end, "y_end": y_end,
        "recipient_id": _team_player_id(team, recipient_jersey),
        "recipient_name": _label(team, recipient_jersey),
        "possession_id": pd.NA, "possession_team_id": pd.NA, "play_pattern": pd.NA,
        "xg": np.nan,
        "strength_state": strength,
    })
    # The file is already in time order (checked on all 10 games). The stable sort keeps file
    # order for events in the same second, which the source gives no other way to order.
    frame = frame.sort_values(["period", "period_time_s"], kind="stable").reset_index(drop=True)
    frame["event_index"] = np.arange(1, len(frame) + 1)
    frame["event_id"] = game.game_id + ":" + frame["event_index"].astype(str)
    poss = assign_possessions(frame)
    frame["possession_id"] = poss["possession_id"]
    frame["possession_team_id"] = poss["possession_team_id"]
    frame["play_pattern"] = poss["play_pattern"]
    return coerce_frame(frame, "events")


def assign_possessions(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive possession ids, because the source has none.

    A possession is a run of events in which one team controls the puck. A new possession
    starts at a faceoff, at a change of acting team, after a shot or goal, after a dump that
    gave the puck up, and at the start of a period. Penalties are not puck events, so they
    carry the possession that is running. ``play_pattern`` is ``restart`` for a possession
    that begins at a faceoff and ``open_play`` otherwise. This is a first definition meant
    to be reviewed against the step 6 sequence logic, not a settled one.
    """
    ids: list[Any] = []
    teams: list[Any] = []
    patterns: list[Any] = []
    pid = 0
    cur_team: str | None = None
    cur_pattern = "open_play"
    break_next = True
    last_period: int | None = None
    for period, team, etype, subtype, outcome in zip(
        frame["period"], frame["team_id"], frame["event_type"],
        frame["event_subtype"], frame["outcome"], strict=True,
    ):
        if etype == "foul":
            ids.append(pid if cur_team is not None else pd.NA)
            teams.append(cur_team if cur_team is not None else pd.NA)
            patterns.append(cur_pattern if cur_team is not None else pd.NA)
            continue
        faceoff = subtype == "Faceoff Win"
        if break_next or team != cur_team or faceoff or period != last_period:
            pid += 1
            cur_team = team
            cur_pattern = "restart" if faceoff else "open_play"
        ids.append(pid)
        teams.append(cur_team)
        patterns.append(cur_pattern)
        break_next = etype == "shot" or (etype == "clearance" and outcome == "failure")
        last_period = period
    return pd.DataFrame({
        "possession_id": ids, "possession_team_id": teams, "play_pattern": patterns,
    }, index=frame.index)


def attack_direction_report(events: pd.DataFrame) -> pd.DataFrame:
    """Per match, period and team: mean x of shots and zone entries in the canonical frame.

    In the acting team's attacking frame these events happen at positive x. A team and period
    with a negative mean means the coordinate flip is wrong for that period.
    """
    entries = events["event_subtype"].fillna("").str.startswith("Zone Entry")
    sel = events[(events["event_type"] == "shot") | entries]
    report = sel.groupby(["match_id", "period", "team_id"]).agg(
        n_events=("x_start", "size"), mean_x_m=("x_start", "mean")
    ).reset_index()
    report["ok"] = report["mean_x_m"] > 0
    return report


# ------------------------------------------------------------------ appearances
def appearances_from_shifts(
    raw: pd.DataFrame, game: Game, lengths: dict[int, float] | None = None
) -> pd.DataFrame:
    """One row per player per game with time on ice in minutes, from the shift file.

    A goalie is listed as ``Go`` and is one player per team in this source, so a goalie
    change within a game cannot be told apart. ``lengths`` maps period to its real length
    in seconds (from ``period_lengths``). Shift clocks are clamped to it, because the source
    logs some overtime shifts as starting at 20:00 although overtime is five minutes
    (the goalies in Team H at Team K, 2025-11-16, would otherwise have 80 minutes).
    """
    s = raw.copy()
    cap = pd.to_numeric(s["period"]).astype(int).map(lengths or {}).fillna(np.inf)
    start = np.minimum(clock_seconds(s["start_clock"]), cap)
    end = np.minimum(clock_seconds(s["end_clock"]), cap)
    s["seconds"] = start - end
    if (s["seconds"] < 0).any():
        raise ValueError(f"{game.name}: a shift ends after it starts")
    s["opening"] = (s["period"] == "1") & (s["start_clock"] == "20:00")
    grouped = s.groupby(["Team", "Player_Id"]).agg(
        seconds=("seconds", "sum"), started=("opening", "any")
    ).reset_index()
    team, jersey = grouped["Team"], grouped["Player_Id"]
    goalie = jersey == GOALIE_ID
    out = pd.DataFrame({
        "source": SOURCE,
        "match_id": game.game_id,
        "team_id": team,
        "player_id": _team_player_id(team, jersey),
        "player_name": _label(team, jersey),
        "jersey_number": pd.to_numeric(jersey, errors="coerce"),
        "primary_position": goalie.map({True: "Goalie", False: pd.NA}),
        "position_group": goalie.map({True: "goalkeeper", False: pd.NA}),
        "started": grouped["started"],
        "minutes_played": grouped["seconds"] / 60.0,
    })
    return coerce_frame(out, "appearances")


# ---------------------------------------------------------------------- matches
def matches_to_frame(games: list[Game], events: pd.DataFrame) -> pd.DataFrame:
    """One row per game. Final scores are the count of Goal events for each team."""
    goals = events[(events["event_type"] == "shot") & (events["outcome"] == "goal")]
    counts = goals.groupby(["match_id", "team_id"]).size()
    rows = []
    for g in games:
        rows.append({
            "source": SOURCE,
            "match_id": g.game_id,
            "sport": "hockey",
            "competition_id": COMPETITION_ID,
            "competition_name": COMPETITION_NAME,
            "season_id": SEASON_ID,
            "season_name": SEASON_NAME,
            "match_date": g.date,
            "stage": None,
            "home_team_id": g.home_team,
            "home_team_name": g.home_team,
            "away_team_id": g.away_team,
            "away_team_name": g.away_team,
            "home_score": int(counts.get((g.game_id, g.home_team), 0)),
            "away_score": int(counts.get((g.game_id, g.away_team), 0)),
            "regulation_periods": REGULATION_PERIODS,
            "field_length_m": FIELD_LENGTH_M,
            "field_width_m": FIELD_WIDTH_M,
            "data_version": "bdc_2026",
        })
    return coerce_frame(pd.DataFrame(rows), "matches")


# ------------------------------------------------------------------ orchestrator
def build_canonical(manifest: dict[str, Any], repo_root: Path) -> dict[str, pd.DataFrame]:
    """Build all three canonical tables from the cache described by a pull manifest."""
    cache = repo_root / manifest["cache_dir"]
    games = games_from_manifest(manifest)
    event_parts: list[pd.DataFrame] = []
    appearance_parts: list[pd.DataFrame] = []
    for g in games:
        raw_events = read_csv_text(cache / g.asset("Events"))
        event_parts.append(events_to_frame(raw_events, g))
        lengths = period_lengths(
            pd.to_numeric(raw_events["Period"]).astype(int), clock_seconds(raw_events["Clock"])
        )
        appearance_parts.append(
            appearances_from_shifts(read_csv_text(cache / g.asset("Shifts")), g, lengths)
        )
    events = pd.concat(event_parts, ignore_index=True)
    return {
        "matches": matches_to_frame(games, events),
        "events": events,
        "appearances": pd.concat(appearance_parts, ignore_index=True),
    }


def write_build_info(path: Path, info: dict[str, Any]) -> None:
    path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
