"""Map StatsBomb open data JSON to the canonical tables in possnet.schema.contract.

Source specification
--------------------
Field meanings follow StatsBomb's "Open Data Events" documentation, shipped in the
upstream repository under doc/ (https://github.com/hudl/open-data/tree/master/doc).
The pitch is nominally 120 by 80 yards with the origin at the top left corner and
the acting team attacking toward x = 120. All code in this module is original work
written for this project against that specification; no third party code is adapted.

Coordinate transform (yards, top left origin) to canonical (meters, center origin,
+y to the acting team's left):

    x_m = (x_yd - 60) * 0.9144
    y_m = (40 - y_yd) * 0.9144
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from possnet.schema.frame import coerce_frame

SOURCE = "statsbomb"
YARD_M = 0.9144
FIELD_LENGTH_M = 120 * YARD_M
FIELD_WIDTH_M = 80 * YARD_M

# Nominal game clock at the start of each period, in seconds.
NOMINAL_PERIOD_START_S = {1: 0.0, 2: 2700.0, 3: 5400.0, 4: 6300.0, 5: 7200.0}

TYPE_MAP = {
    "Pass": "pass", "Shot": "shot", "Carry": "carry", "Ball Receipt*": "reception",
    "Ball Recovery": "takeaway", "Interception": "takeaway",
    "Dispossessed": "giveaway", "Miscontrol": "giveaway",
    "Duel": "duel", "Dribble": "duel", "50/50": "duel", "Dribbled Past": "duel",
    "Clearance": "clearance", "Block": "block", "Goal Keeper": "goalkeeper",
    "Foul Committed": "foul", "Foul Won": "foul", "Bad Behaviour": "foul",
    "Half Start": "stoppage", "Half End": "stoppage",
    "Injury Stoppage": "stoppage", "Referee Ball-Drop": "stoppage",
    "Substitution": "substitution",
}
# Canonical types whose subtype falls back to the StatsBomb type name.
SUBTYPE_FALLBACK = {"takeaway", "giveaway", "foul", "stoppage", "other", "duel",
                    "goalkeeper", "substitution"}
# Keys under which StatsBomb nests an ``outcome`` for generic success/failure events.
GENERIC_OUTCOME_KEYS = ("duel", "dribble", "interception", "50_50")

# Restart actions taken from a dead ball, by nested type name.
DEAD_BALL_PASS_TYPES = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}
DEAD_BALL_SHOT_TYPES = {"Corner", "Free Kick", "Penalty"}

PASS_OUTCOME_MAP = {"Incomplete": "incomplete", "Out": "out", "Pass Offside": "offside"}
SHOT_OUTCOME_MAP = {
    "Goal": "goal", "Saved": "saved", "Saved Off Target": "saved", "Saved to Post": "saved",
    "Blocked": "blocked", "Off T": "off_target", "Wayward": "off_target", "Post": "post",
}
SUCCESS_NAMES = {"Won", "Success", "Success In Play", "Success Out", "Complete"}
FAILURE_NAMES = {"Lost", "Lost In Play", "Lost Out", "Incomplete", "Nutmegged"}

PLAY_PATTERN_MAP = {
    "Regular Play": "open_play", "From Counter": "open_play",
    "From Corner": "set_piece", "From Free Kick": "set_piece",
    "From Throw In": "restart", "From Goal Kick": "restart",
    "From Keeper": "restart", "From Kick Off": "restart",
}


# ---------------------------------------------------------------- small helpers
def _name(node: dict[str, Any] | None) -> str | None:
    return None if not node else node.get("name")


def _id_text(node: dict[str, Any] | None) -> str | None:
    return None if not node or node.get("id") is None else str(node["id"])


def _to_canonical_xy(location: list[float] | None) -> tuple[float, float]:
    if not location or len(location) < 2:
        return math.nan, math.nan
    return (location[0] - 60.0) * YARD_M, (40.0 - location[1]) * YARD_M


def _timestamp_seconds(ts: str) -> float:
    hours, minutes, seconds = ts.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def position_group(position: str | None) -> str | None:
    """Canonical position group from a StatsBomb position name."""
    if not position:
        return None
    if "Goalkeeper" in position:
        return "goalkeeper"
    if "Back" in position:  # Center Back, Right Wing Back, ...
        return "defender"
    if "Midfield" in position:
        return "midfielder"
    if any(k in position for k in ("Wing", "Forward", "Striker")):
        return "forward"
    return None


def _outcome(e: dict[str, Any], canonical_type: str) -> str | None:
    if canonical_type == "pass":
        name = _name(e.get("pass", {}).get("outcome"))
        return "complete" if name is None else PASS_OUTCOME_MAP.get(name, "other")
    if canonical_type == "shot":
        name = _name(e.get("shot", {}).get("outcome"))
        return None if name is None else SHOT_OUTCOME_MAP.get(name, "other")
    for key in GENERIC_OUTCOME_KEYS:
        name = _name(e.get(key, {}).get("outcome")) if isinstance(e.get(key), dict) else None
        if name in SUCCESS_NAMES:
            return "success"
        if name in FAILURE_NAMES:
            return "failure"
    return None


def _subtype(e: dict[str, Any], sb_type: str, canonical_type: str) -> str | None:
    nested_key = {"Pass": "pass", "Shot": "shot", "Duel": "duel", "Goal Keeper": "goalkeeper"}.get(
        sb_type
    )
    if nested_key and isinstance(e.get(nested_key), dict):
        nested = _name(e[nested_key].get("type"))
        if nested:
            return nested
    return sb_type if canonical_type in SUBTYPE_FALLBACK else None


def _is_dead_ball(e: dict[str, Any], canonical_type: str) -> bool:
    if canonical_type == "pass":
        return _name(e.get("pass", {}).get("type")) in DEAD_BALL_PASS_TYPES
    if canonical_type == "shot":
        return _name(e.get("shot", {}).get("type")) in DEAD_BALL_SHOT_TYPES
    return False


def _end_location(e: dict[str, Any], canonical_type: str) -> list[float] | None:
    key = {"pass": "pass", "carry": "carry", "shot": "shot"}.get(canonical_type)
    if key and isinstance(e.get(key), dict):
        return e[key].get("end_location")
    return None


# ----------------------------------------------------------------------- events
def events_to_frame(events: list[dict[str, Any]], match_id: int, home_team_id: int) -> pd.DataFrame:
    """Convert one match's raw StatsBomb events to the canonical events schema."""
    rows: list[dict[str, Any]] = []
    for e in events:
        sb_type = e["type"]["name"]
        ctype = TYPE_MAP.get(sb_type, "other")
        period = int(e["period"])
        period_time = _timestamp_seconds(e["timestamp"])
        x0, y0 = _to_canonical_xy(e.get("location"))
        x1, y1 = _to_canonical_xy(_end_location(e, ctype))
        recipient = e.get("pass", {}).get("recipient") if ctype == "pass" else None
        position = _name(e.get("position"))
        team_id = e["team"]["id"]
        rows.append({
            "source": SOURCE,
            "match_id": str(match_id),
            "event_id": e["id"],
            "event_index": e["index"],
            "period": period,
            "period_time_s": period_time,
            "game_time_s": NOMINAL_PERIOD_START_S[period] + period_time,
            "team_id": str(team_id),
            "team_name": e["team"]["name"],
            "is_home": team_id == home_team_id,
            "player_id": _id_text(e.get("player")),
            "player_name": _name(e.get("player")),
            "position": position,
            "position_group": position_group(position),
            "event_type": ctype,
            "event_subtype": _subtype(e, sb_type, ctype),
            "is_dead_ball": _is_dead_ball(e, ctype),
            "outcome": _outcome(e, ctype),
            "x_start": x0, "y_start": y0, "x_end": x1, "y_end": y1,
            "recipient_id": _id_text(recipient),
            "recipient_name": _name(recipient),
            "possession_id": e.get("possession"),
            "possession_team_id": _id_text(e.get("possession_team")),
            "play_pattern": PLAY_PATTERN_MAP.get(_name(e.get("play_pattern")) or "", "other"),
            "xg": e.get("shot", {}).get("statsbomb_xg") if ctype == "shot" else None,
            "strength_state": None,
        })
    frame = pd.DataFrame(rows)
    frame = frame.sort_values("event_index", kind="stable")
    return coerce_frame(frame, "events")


def period_durations(events: pd.DataFrame) -> dict[int, float]:
    """Real elapsed seconds per period, taken as the last event time in the period."""
    return events.groupby("period")["period_time_s"].max().astype(float).to_dict()


# ------------------------------------------------------------------ appearances
RED_CARDS = {"Red Card", "Second Yellow"}


def _real_event_seconds(e: dict[str, Any], durations: dict[int, float]) -> float:
    """Real elapsed match seconds at an event (previous period durations plus its timestamp)."""
    period = int(e["period"])
    before = sum(d for p, d in durations.items() if p < period)
    return before + _timestamp_seconds(e["timestamp"])


def appearances_from_events(
    raw_events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    match_id: int,
    durations: dict[int, float],
) -> pd.DataFrame:
    """Build appearances with real minutes played for one match.

    Minutes come from the event stream (Starting XI, Substitution, and red card events),
    not from the lineup file's ``positions`` stints. In the lineup file, period labels on
    tactical shift stints are inconsistent and red carded players can be listed until the
    final whistle (for example match 3754217, Arsenal). The lineup file is used only for
    the roster, names, and jersey numbers.
    """
    total = sum(d for p, d in durations.items() if p <= 4)
    on: dict[tuple[int, int], float] = {}
    off: dict[tuple[int, int], float] = {}
    started: set[tuple[int, int]] = set()
    positions: dict[tuple[int, int], dict[str, int]] = {}

    for e in raw_events:
        if int(e["period"]) > 4:
            continue
        kind = e["type"]["name"]
        team = e["team"]["id"]
        if kind == "Starting XI":
            for entry in e["tactics"]["lineup"]:
                key = (team, entry["player"]["id"])
                on[key] = 0.0
                started.add(key)
            continue
        when = _real_event_seconds(e, durations)
        if kind == "Substitution":
            off.setdefault((team, e["player"]["id"]), when)
            on.setdefault((team, e["substitution"]["replacement"]["id"]), when)
        card = (e.get("foul_committed") or {}).get("card") or \
            (e.get("bad_behaviour") or {}).get("card")
        if card and card.get("name") in RED_CARDS and e.get("player"):
            off.setdefault((team, e["player"]["id"]), when)
        pos = _name(e.get("position"))
        if pos and e.get("player"):
            counts = positions.setdefault((team, e["player"]["id"]), {})
            counts[pos] = counts.get(pos, 0) + 1

    rows: list[dict[str, Any]] = []
    for team in lineups:
        for player in team["lineup"]:
            key = (team["team_id"], player["player_id"])
            minutes = 0.0
            if key in on:
                end = min(off.get(key, total), total)
                minutes = max(end - on[key], 0.0) / 60.0
            counts = positions.get(key)
            primary = max(counts, key=counts.get) if counts else None
            rows.append({
                "source": SOURCE,
                "match_id": str(match_id),
                "team_id": str(team["team_id"]),
                "player_id": str(player["player_id"]),
                "player_name": player["player_name"],
                "jersey_number": player.get("jersey_number"),
                "primary_position": primary,
                "position_group": position_group(primary),
                "started": key in started,
                "minutes_played": minutes,
            })
    return coerce_frame(pd.DataFrame(rows), "appearances")


# ---------------------------------------------------------------------- matches
def matches_to_frame(matches: list[dict[str, Any]], competition_name: str) -> pd.DataFrame:
    rows = []
    for m in matches:
        rows.append({
            "source": SOURCE,
            "match_id": str(m["match_id"]),
            "sport": "soccer",
            "competition_id": str(m["competition"]["competition_id"]),
            "competition_name": competition_name,
            "season_id": str(m["season"]["season_id"]),
            "season_name": m["season"]["season_name"],
            "match_date": m["match_date"],
            "stage": _name(m.get("competition_stage")),
            "home_team_id": str(m["home_team"]["home_team_id"]),
            "home_team_name": m["home_team"]["home_team_name"],
            "away_team_id": str(m["away_team"]["away_team_id"]),
            "away_team_name": m["away_team"]["away_team_name"],
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "regulation_periods": 2,
            "field_length_m": FIELD_LENGTH_M,
            "field_width_m": FIELD_WIDTH_M,
            "data_version": (m.get("metadata") or {}).get("data_version"),
        })
    return coerce_frame(pd.DataFrame(rows), "matches")


# ------------------------------------------------------------------ orchestrator
def build_canonical(manifest: dict[str, Any], repo_root: Path) -> dict[str, pd.DataFrame]:
    """Build all three canonical tables from the cache described by a pull manifest.

    Only matches whose events file is listed in the manifest are included, so a smoke
    test pull (``--max-matches``) yields a consistent small dataset.
    """
    cache = repo_root / manifest["cache_dir"]
    comp = manifest["competition"]
    matches_json = json.loads(
        (cache / f"matches/{comp['competition_id']}/{comp['season_id']}.json").read_text("utf-8")
    )
    have_events = {Path(f["path"]).stem for f in manifest["files"] if "/events/" in f["path"]}
    matches_json = [m for m in matches_json if str(m["match_id"]) in have_events]
    matches_json.sort(key=lambda m: (m["match_date"], m["match_id"]))

    events_parts: list[pd.DataFrame] = []
    appearance_parts: list[pd.DataFrame] = []
    for m in matches_json:
        mid = m["match_id"]
        raw_events = json.loads((cache / f"events/{mid}.json").read_text("utf-8"))
        ev = events_to_frame(raw_events, mid, m["home_team"]["home_team_id"])
        events_parts.append(ev)
        lineup_path = cache / f"lineups/{mid}.json"
        if lineup_path.exists():
            lineups = json.loads(lineup_path.read_text("utf-8"))
            appearance_parts.append(
                appearances_from_events(raw_events, lineups, mid, period_durations(ev))
            )

    return {
        "matches": matches_to_frame(matches_json, comp["competition_name"]),
        "events": pd.concat(events_parts, ignore_index=True),
        "appearances": pd.concat(appearance_parts, ignore_index=True),
    }
