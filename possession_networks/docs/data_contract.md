# Canonical event data contract

This file is generated from `src/possnet/schema/contract.py`. Do not edit it by hand. Run `python scripts/00_render_contract.py` after changing the contract.

Any new data source (hockey or otherwise) is supported by writing an adapter that produces these three tables and passes `scripts/03_validate.py`. Nothing downstream of the adapter may depend on a provider specific column.

## Coordinate convention

Coordinates are in METERS in the ACTING TEAM'S ATTACKING FRAME. The origin is the center of the playing surface, +x points toward the goal the acting team is attacking, and +y points to the acting team's left when facing +x. Every event is expressed from the perspective of the team that performed it, so a team always attacks toward +x regardless of period or starting end. Adapters for sources that give absolute rink coordinates must flip them per period and per team. Field dimensions are stored per match in the matches table.

## Table: matches

One row per match.

| Column | Type | Null allowed | Allowed values | Description |
|---|---|---|---|---|
| `source` | string | no |  | Data provider key, for example statsbomb. |
| `match_id` | string | no |  | Provider match id as text. Unique within a source. |
| `sport` | string | no | soccer, hockey | soccer or hockey. |
| `competition_id` | string | no |  | Provider competition id as text. |
| `competition_name` | string | no |  | Competition display name. |
| `season_id` | string | no |  | Provider season id as text. |
| `season_name` | string | no |  | Season display name, for example 2015/2016. |
| `match_date` | string | no |  | Local match date, ISO 8601 (YYYY-MM-DD). |
| `stage` | string | yes |  | Competition stage, for example Regular Season. |
| `home_team_id` | string | no |  | Home team id as text. |
| `home_team_name` | string | no |  | Home team name. |
| `away_team_id` | string | no |  | Away team id as text. |
| `away_team_name` | string | no |  | Away team name. |
| `home_score` | Int64 | yes |  | Final home score (nullable if unknown). |
| `away_score` | Int64 | yes |  | Final away score (nullable if unknown). |
| `regulation_periods` | Int64 | no |  | Periods in regulation: 2 soccer, 3 hockey. |
| `field_length_m` | float64 | no |  | Nominal playing surface length in meters. |
| `field_width_m` | float64 | no |  | Nominal playing surface width in meters. |
| `data_version` | string | yes |  | Provider data version string, if any. |

## Table: events

One row per event, sorted by `match_id`, `event_index`.

| Column | Type | Null allowed | Allowed values | Description |
|---|---|---|---|---|
| `source` | string | no |  | Data provider key. |
| `match_id` | string | no |  | Join key to matches. |
| `event_id` | string | no |  | Provider event id. Unique within a source. |
| `event_index` | Int64 | no |  | Order of the event within the match, strictly increasing, starting at 1. |
| `period` | Int64 | no |  | Period number: 1..2 (+ extra time 3..4), 5 = shootout. |
| `period_time_s` | float64 | no |  | Seconds elapsed since the start of the period. Always counts up. Adapters convert countdown clocks. |
| `game_time_s` | float64 | no |  | Provider game clock in seconds, counting up from the start of the match, using nominal period offsets (soccer: 0, 2700, 5400, 6300). Stoppage time runs past the nominal period end, so this clock can step backward at a period boundary. Use event_index for ordering. |
| `team_id` | string | no |  | Team performing the event. |
| `team_name` | string | no |  | Team name (denormalized for convenience). |
| `is_home` | boolean | no |  | True when team_id is the home team. |
| `player_id` | string | yes |  | Acting player. Null for team level events. |
| `player_name` | string | yes |  | Acting player name. |
| `position` | string | yes |  | Provider specific position at the time of the event. |
| `position_group` | string | yes | goalkeeper, defender, midfielder, forward | Canonical position group at the time of the event. |
| `event_type` | string | no | pass, shot, carry, reception, takeaway, giveaway, duel, clearance, block, goalkeeper, foul, stoppage, substitution, other | Canonical event type. |
| `event_subtype` | string | yes |  | Provider sub type (pass type, shot type, duel type), free text. |
| `is_dead_ball` | boolean | no |  | True when the event is the restart action itself, taken from a dead ball. Soccer: kick off, goal kick, throw in, corner, free kick, penalty. Hockey: the faceoff draw. Used to separate open play from restarts. |
| `outcome` | string | yes | complete, incomplete, out, offside, other, goal, saved, blocked, off_target, post, success, failure | Canonical outcome. Passes: complete, incomplete, out, offside, other. Shots: goal, saved, blocked, off_target, post, other. Other typed events: success or failure when the provider says so, else null. |
| `x_start` | float64 | yes |  | Start x in meters, acting team attacking frame. |
| `y_start` | float64 | yes |  | Start y in meters, acting team attacking frame. |
| `x_end` | float64 | yes |  | End x for passes, carries, shots. |
| `y_end` | float64 | yes |  | End y for passes, carries, shots. |
| `recipient_id` | string | yes |  | Intended pass recipient (passes only). |
| `recipient_name` | string | yes |  | Intended pass recipient name. |
| `possession_id` | Int64 | yes |  | Provider possession sequence number within the match. Hockey adapters must derive it (continuous control by one team). |
| `possession_team_id` | string | yes |  | Team that owns the possession sequence. |
| `play_pattern` | string | yes | open_play, set_piece, restart, other | How the possession began. |
| `xg` | float64 | yes |  | Provider expected goals for shots. Null if not provided. |
| `strength_state` | string | yes |  | Skater strength from the acting team view, for example 5v5. Hockey only; null for soccer. |

## Table: appearances

One row per player per match, including unused substitutes.

| Column | Type | Null allowed | Allowed values | Description |
|---|---|---|---|---|
| `source` | string | no |  | Data provider key. |
| `match_id` | string | no |  | Join key to matches. |
| `team_id` | string | no |  | Team id. |
| `player_id` | string | no |  | Player id. |
| `player_name` | string | no |  | Player name. |
| `jersey_number` | Int64 | yes |  | Shirt number. |
| `primary_position` | string | yes |  | Provider position most often recorded on the player's events in the match (null if the player has no events). |
| `position_group` | string | yes | goalkeeper, defender, midfielder, forward | Canonical group of the primary position. |
| `started` | boolean | no |  | True if in the starting lineup. |
| `minutes_played` | float64 | no |  | Minutes on the surface by real elapsed time, including stoppage time. Hockey: time on ice in minutes. |

## Semantic rules checked by the validator

* event_id is unique within a source; (match_id, event_index) is unique and event_index increases by exactly one within a match.
* period never decreases as event_index increases.
* Every events.match_id exists in matches; every team_id is the home or away team of that match; is_home agrees with team_id.
* pass, shot, carry, reception events have x_start and y_start; pass, carry, shot events have x_end and y_end.
* Located coordinates lie within the playing surface (a 1 meter tolerance is allowed).
* A complete pass has a recipient_id, the recipient belongs to the passing team, and the recipient differs from the passer.
* possession_team_id is constant within a (match_id, possession_id).
* Every non null player_id in events has an appearances row for that match and team.
* minutes_played is between 0 and the match duration, and team totals are close to 11 players times the match duration (soccer), allowing for red cards.
* Goals: shot events with outcome goal plus own goals credited to a team equal the final score. Own goals are stored as event_type other with event_subtype 'Own Goal For' (credited to the benefiting team).

## Notes for a hockey adapter

* Coordinates: convert feet to meters, center the origin at center ice, and flip x and y per team and period so the acting team always attacks toward +x.
* Clock: provider clocks often count down from 20:00. Set period_time_s = 1200 minus the remaining time, and game_time_s = 1200 * (period - 1) + period_time_s.
* Possession: if the provider has no possession id, derive it as maximal runs of consecutive events where one team controls the puck, broken by turnovers, stoppages, shots, and faceoffs.
* Event types: faceoff and puck battle events map to duel or stoppage; takeaways and giveaways map directly; zone entries and exits map to carry or pass with a subtype.
* position_group: hockey uses goalkeeper, defender, forward (midfielder is unused).
* strength_state: fill from the on ice skater counts so network features can be restricted to 5v5.
* appearances.minutes_played holds time on ice. Network centralities are normalized by it, so TOI must be computed from shift data, not game counts.
