"""Canonical data contract for event data (soccer now, hockey later).

This module is the single source of truth. The validator, the adapters, and the
generated document docs/data_contract.md are all driven by the definitions here.

Three tables are defined:

* ``matches``      one row per match
* ``events``       one row per on ball or administrative event
* ``appearances``  one row per player per match, with minutes played

Coordinate convention (important for hockey)
--------------------------------------------
Coordinates are in METERS in the ACTING TEAM'S ATTACKING FRAME:

* origin at the center of the playing surface
* +x points toward the goal the acting team is attacking
* +y points to the acting team's left when facing +x

Every event is expressed from the perspective of the team that performed it, so a
team always attacks toward +x regardless of period or which end it started on.
Adapters for sources that give absolute rink coordinates must flip them per period
and per team. Field dimensions are stored per match in ``matches``.
"""

from __future__ import annotations

from dataclasses import dataclass

COORDINATE_CONVENTION = (
    "Coordinates are in METERS in the ACTING TEAM'S ATTACKING FRAME. The origin is the "
    "center of the playing surface, +x points toward the goal the acting team is "
    "attacking, and +y points to the acting team's left when facing +x. Every event is "
    "expressed from the perspective of the team that performed it, so a team always "
    "attacks toward +x regardless of period or starting end. Adapters for sources that "
    "give absolute rink coordinates must flip them per period and per team. Field "
    "dimensions are stored per match in the matches table."
)

# ----------------------------------------------------------------- vocabularies
EVENT_TYPES: tuple[str, ...] = (
    "pass", "shot", "carry", "reception", "takeaway", "giveaway", "duel",
    "clearance", "block", "goalkeeper", "foul", "stoppage", "substitution", "other",
)
PASS_OUTCOMES = ("complete", "incomplete", "out", "offside", "other")
SHOT_OUTCOMES = ("goal", "saved", "blocked", "off_target", "post", "other")
GENERIC_OUTCOMES = ("success", "failure")
OUTCOMES: tuple[str, ...] = tuple(dict.fromkeys(PASS_OUTCOMES + SHOT_OUTCOMES + GENERIC_OUTCOMES))
PLAY_PATTERNS = ("open_play", "set_piece", "restart", "other")
POSITION_GROUPS = ("goalkeeper", "defender", "midfielder", "forward")
SPORTS = ("soccer", "hockey")

# Event types that must carry a start location.
LOCATED_EVENT_TYPES = ("pass", "shot", "carry", "reception")
# Event types that must carry an end location.
END_LOCATED_EVENT_TYPES = ("pass", "carry", "shot")
# The same, by sport. Hockey shots are logged at the release point only, so in hockey
# only passes carry an end location.
END_LOCATED_BY_SPORT: dict[str, tuple[str, ...]] = {
    "soccer": END_LOCATED_EVENT_TYPES,
    "hockey": ("pass",),
}
# Players on the playing surface for one team at a time (hockey: five skaters and a goalie).
ON_SURFACE_PER_TEAM: dict[str, int] = {"soccer": 11, "hockey": 6}
# Hockey period lengths in seconds. Overtime is five minutes in the regular season.
HOCKEY_REGULATION_PERIOD_S = 1200.0
HOCKEY_OVERTIME_PERIOD_S = 300.0


@dataclass(frozen=True)
class Column:
    """One column of a canonical table."""

    name: str
    dtype: str  # pandas dtype string: "string", "Int64", "float64", "boolean"
    nullable: bool
    description: str
    allowed: tuple[str, ...] | None = None


# ---------------------------------------------------------------------- matches
MATCHES_COLUMNS: tuple[Column, ...] = (
    Column("source", "string", False, "Data provider key, for example statsbomb."),
    Column("match_id", "string", False, "Provider match id as text. Unique within a source."),
    Column("sport", "string", False, "soccer or hockey.", SPORTS),
    Column("competition_id", "string", False, "Provider competition id as text."),
    Column("competition_name", "string", False, "Competition display name."),
    Column("season_id", "string", False, "Provider season id as text."),
    Column("season_name", "string", False, "Season display name, for example 2015/2016."),
    Column("match_date", "string", False, "Local match date, ISO 8601 (YYYY-MM-DD)."),
    Column("stage", "string", True, "Competition stage, for example Regular Season."),
    Column("home_team_id", "string", False, "Home team id as text."),
    Column("home_team_name", "string", False, "Home team name."),
    Column("away_team_id", "string", False, "Away team id as text."),
    Column("away_team_name", "string", False, "Away team name."),
    Column("home_score", "Int64", True, "Final home score (nullable if unknown)."),
    Column("away_score", "Int64", True, "Final away score (nullable if unknown)."),
    Column("regulation_periods", "Int64", False, "Periods in regulation: 2 soccer, 3 hockey."),
    Column("field_length_m", "float64", False, "Nominal playing surface length in meters."),
    Column("field_width_m", "float64", False, "Nominal playing surface width in meters."),
    Column("data_version", "string", True, "Provider data version string, if any."),
)

# ----------------------------------------------------------------------- events
EVENTS_COLUMNS: tuple[Column, ...] = (
    Column("source", "string", False, "Data provider key."),
    Column("match_id", "string", False, "Join key to matches."),
    Column("event_id", "string", False, "Provider event id. Unique within a source."),
    Column("event_index", "Int64", False,
           "Order of the event within the match, strictly increasing, starting at 1."),
    Column("period", "Int64", False, "Period number: 1..2 (+ extra time 3..4), 5 = shootout."),
    Column("period_time_s", "float64", False,
           "Seconds elapsed since the start of the period. Always counts up. "
           "Adapters convert countdown clocks."),
    Column("game_time_s", "float64", False,
           "Provider game clock in seconds, counting up from the start of the match, "
           "using nominal period offsets (soccer: 0, 2700, 5400, 6300). Stoppage time "
           "runs past the nominal period end, so this clock can step backward at a "
           "period boundary. Use event_index for ordering."),
    Column("team_id", "string", False, "Team performing the event."),
    Column("team_name", "string", False, "Team name (denormalized for convenience)."),
    Column("is_home", "boolean", False, "True when team_id is the home team."),
    Column("player_id", "string", True, "Acting player. Null for team level events."),
    Column("player_name", "string", True, "Acting player name."),
    Column("position", "string", True, "Provider specific position at the time of the event."),
    Column("position_group", "string", True,
           "Canonical position group at the time of the event.", POSITION_GROUPS),
    Column("event_type", "string", False, "Canonical event type.", EVENT_TYPES),
    Column("event_subtype", "string", True,
           "Provider sub type (pass type, shot type, duel type), free text."),
    Column("is_dead_ball", "boolean", False,
           "True when the event is the restart action itself, taken from a dead ball. "
           "Soccer: kick off, goal kick, throw in, corner, free kick, penalty. "
           "Hockey: the faceoff draw. Used to separate open play from restarts."),
    Column("outcome", "string", True,
           "Canonical outcome. Passes: complete, incomplete, out, offside, other. "
           "Shots: goal, saved, blocked, off_target, post, other. "
           "Other typed events: success or failure when the provider says so, else null.",
           OUTCOMES),
    Column("x_start", "float64", True, "Start x in meters, acting team attacking frame."),
    Column("y_start", "float64", True, "Start y in meters, acting team attacking frame."),
    Column("x_end", "float64", True, "End x for passes, carries, shots."),
    Column("y_end", "float64", True, "End y for passes, carries, shots."),
    Column("recipient_id", "string", True, "Intended pass recipient (passes only)."),
    Column("recipient_name", "string", True, "Intended pass recipient name."),
    Column("possession_id", "Int64", True,
           "Provider possession sequence number within the match. "
           "Hockey adapters must derive it (continuous control by one team)."),
    Column("possession_team_id", "string", True, "Team that owns the possession sequence."),
    Column("play_pattern", "string", True, "How the possession began.", PLAY_PATTERNS),
    Column("xg", "float64", True, "Provider expected goals for shots. Null if not provided."),
    Column("strength_state", "string", True,
           "Skater strength from the acting team view, for example 5v5. Hockey only; "
           "null for soccer."),
)

# ------------------------------------------------------------------ appearances
APPEARANCES_COLUMNS: tuple[Column, ...] = (
    Column("source", "string", False, "Data provider key."),
    Column("match_id", "string", False, "Join key to matches."),
    Column("team_id", "string", False, "Team id."),
    Column("player_id", "string", False, "Player id."),
    Column("player_name", "string", False, "Player name."),
    Column("jersey_number", "Int64", True, "Shirt number."),
    Column("primary_position", "string", True,
           "Provider position most often recorded on the player's events in the match "
           "(null if the player has no events)."),
    Column("position_group", "string", True, "Canonical group of the primary position.",
           POSITION_GROUPS),
    Column("started", "boolean", False, "True if in the starting lineup."),
    Column("minutes_played", "float64", False,
           "Minutes on the surface by real elapsed time, including stoppage time. "
           "Hockey: time on ice in minutes."),
)

TABLES: dict[str, tuple[Column, ...]] = {
    "matches": MATCHES_COLUMNS,
    "events": EVENTS_COLUMNS,
    "appearances": APPEARANCES_COLUMNS,
}


def column_names(table: str) -> list[str]:
    return [c.name for c in TABLES[table]]


# Semantic rules enforced by possnet.validate.checks, documented for adapter authors.
RULES: tuple[str, ...] = (
    "event_id is unique within a source; (match_id, event_index) is unique and "
    "event_index increases by exactly one within a match.",
    "period never decreases as event_index increases.",
    "Every events.match_id exists in matches; every team_id is the home or away team of "
    "that match; is_home agrees with team_id.",
    "pass, shot, carry, reception events have x_start and y_start; pass, carry, shot "
    "events have x_end and y_end. Hockey shots are logged at the release point only, so in "
    "hockey only passes need an end location.",
    "Located coordinates lie within the playing surface (a 1 meter tolerance is allowed).",
    "A complete pass has a recipient_id, the recipient belongs to the passing team, and "
    "the recipient differs from the passer. The hockey source has complete passes with no "
    "recorded receiver, so for hockey a missing recipient is a warning, not an error.",
    "possession_team_id is constant within a (match_id, possession_id).",
    "Every non null player_id in events has an appearances row for that match and team.",
    "minutes_played is between 0 and the match duration, and team totals are close to "
    "11 players times the match duration (soccer), allowing for red cards. Hockey: six on "
    "the ice (five skaters and a goalie) against nominal period lengths; a team playing "
    "short handed has less.",
    "Goals: shot events with outcome goal plus own goals credited to a team equal the "
    "final score. Own goals are stored as event_type other with event_subtype "
    "'Own Goal For' (credited to the benefiting team).",
)

HOCKEY_MAPPING_NOTES: tuple[str, ...] = (
    "Coordinates: convert feet to meters, center the origin at center ice, and flip x "
    "and y per team and period so the acting team always attacks toward +x.",
    "Clock: provider clocks often count down from 20:00. Set period_time_s = 1200 minus "
    "the remaining time, and game_time_s = 1200 * (period - 1) + period_time_s.",
    "Possession: if the provider has no possession id, derive it as maximal runs of "
    "consecutive events where one team controls the puck, broken by turnovers, "
    "stoppages, shots, and faceoffs.",
    "Event types: faceoff and puck battle events map to duel or stoppage; takeaways and "
    "giveaways map directly; zone entries and exits map to carry or pass with a "
    "subtype.",
    "position_group: hockey uses goalkeeper, defender, forward (midfielder is unused).",
    "strength_state: fill from the on ice skater counts so network features can be "
    "restricted to 5v5.",
    "appearances.minutes_played holds time on ice. Network centralities are normalized "
    "by it, so TOI must be computed from shift data, not game counts.",
)
