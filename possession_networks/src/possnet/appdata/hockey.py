"""Explorer payload for hockey (Stathletes Big Data Cup).

The soccer builder in ``build.py`` assumes StatsBomb details: positions for lineup layouts,
reception events for pass flight times, a halftime and xG. Hockey data has none of these, so
this module builds the same ``matches`` structure the app already reads, with hockey rules:

* time is continuous game time (three 20 minute periods, then 5 minute overtime), already in
  ``game_time_s`` in the canonical table
* shots carry no end location, so the ball is drawn flying to the middle of the net attacked
* flight times come from distance only
* nothing is "assigned" to a position, so the app uses average touch positions
* there is no xG; shot rows carry 0.0 and ``meta.has_xg`` is false

The payload shape is otherwise identical, so the Networks view runs unchanged on it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from possnet.appdata.build import build_feed

FEED_TYPES = ("pass", "shot", "takeaway", "clearance", "duel", "foul", "other")
PERIOD_S = 1200
PASS_SPEED_MS = 18.0
SHOT_SPEED_MS = 28.0


def hockey_meta(field_length_m: float, field_width_m: float, n_games: int) -> dict:
    """Payload ``meta`` for hockey. Soccer only fields are present but empty.

    All wording the Networks view shows for hockey lives in ``text`` here, so the app code holds
    no hockey sentences and the soccer wording is untouched.
    """
    return {
        "sport": "hockey", "season": "2025/26", "source": "Stathletes Big Data Cup 2026",
        "unit": "games",
        "credit": "Data: Stathletes Big Data Cup 2026, teams anonymized. Licensed for your own "
                  "use only; do not share this page or its data.",
        "pitch": [round(field_length_m, 3), round(field_width_m, 3)],
        "tabs": ["networks"], "has_xg": False, "has_positions": False,
        "window_s": 300, "tick_s": 300, "window_label": "Last 5 min", "start_label": "From start",
        "break_labels": ["P2", "P3", "OT"], "period_labels": ["P1", "P2", "P3", "OT"],
        "n_games": n_games,
        "text": {
            "title": "Possnet Explorer, hockey",
            "start_pill": "Puck drop",
            "how": {
                "live": "Each colored dot is a player, placed where the game log last saw him and "
                        "sliding to where he next acts, so positions are estimates between events. "
                        "The puck follows every logged pass and shot. A dashed line with a cross "
                        "is a pass that missed. Fading dots have not been involved for a while.",
                "net": "Dots are players, placed at the average spot of his logged events. A line "
                       "is every pass between two players. Watch a pulse travel along a link: "
                       "when it lands, the line gets thicker. Dot size shows the measure you "
                       "pick, which is recomputed after every pass. Each team is drawn attacking "
                       "to the right.",
            },
            "legend": {
                "live": '<span><i class="lg dot"></i>Player</span>'
                        '<span><i class="lg ring"></i>Opponent</span>'
                        '<span><i class="lg ball"></i>Puck</span>'
                        '<span><i class="lg ln"></i>Pass</span>'
                        '<span><i class="lg dash"></i>Missed pass</span>',
            },
            "tl_hint": "Drag the timeline or press play. Pass by pass skips idle time so every "
                       "action gets the same screen time; real time runs the clock. Goals ring "
                       "the axis and shots tick it, with the team in view above. Dashed lines "
                       "mark the periods.",
            "minw_hint": "Measures use every pass. The slider only hides thin lines. Goalies "
                         "appear as players.",
        },
        # harmless placeholders so scripts for the soccer only tabs can load
        "grid": [1, 1], "chains": [], "primary_chain": "", "slots": {},
    }


def _flight_tenths(ev: pd.DataFrame) -> np.ndarray:
    length = np.hypot(ev["x_end"].to_numpy(float) - ev["x_start"].to_numpy(float),
                      ev["y_end"].to_numpy(float) - ev["y_start"].to_numpy(float))
    kind = ev["event_type"].to_numpy(object)
    dur = np.zeros(len(ev))
    p, s = kind == "pass", kind == "shot"
    dur[p] = np.clip(length[p] / PASS_SPEED_MS, 0.4, 2.5)
    dur[s] = np.clip(length[s] / SHOT_SPEED_MS, 0.3, 1.2)
    return np.rint(np.nan_to_num(dur) * 10).astype(int)


def _period_starts(events: pd.DataFrame) -> dict:
    """Start second of each period after the first, per match (the end of the previous one)."""
    out = {}
    for mid, g in events.groupby("match_id"):
        periods = sorted(int(p) for p in g["period"].dropna().unique())
        starts = []
        for p in periods[1:]:
            starts.append(float(g.loc[g["period"] == p, "game_time_s"].min()))
        out[mid] = starts
    return out


def build_hockey_matches(matches: pd.DataFrame, events: pd.DataFrame,
                         appearances: pd.DataFrame) -> tuple[list, list, list]:
    """Return (teams, players, match entries), the same shape ``build_matches`` returns."""
    ev = events.copy()
    ev["t"] = ev["game_time_s"].astype(float)
    teams = sorted(set(matches["home_team_name"]) | set(matches["away_team_name"]))
    team_idx = {n: i for i, n in enumerate(teams)}

    names = pd.concat([
        ev[["player_id", "player_name"]],
        ev[["recipient_id", "recipient_name"]].set_axis(["player_id", "player_name"], axis=1),
    ]).dropna().drop_duplicates("player_id").sort_values("player_id")
    players = names["player_name"].astype(str).tolist()
    pidx = dict(zip(names["player_id"].astype(str), range(len(names)), strict=True))

    ev = ev.sort_values(["match_id", "event_index"], kind="stable").reset_index(drop=True)
    length_x = matches.set_index("match_id")["field_length_m"]
    # a shot flies from where it was taken to the middle of the net being attacked
    shot = ev["event_type"] == "shot"
    ev.loc[shot, "x_end"] = ev.loc[shot, "match_id"].map(length_x).astype(float) / 2.0
    ev.loc[shot, "y_end"] = 0.0
    ev["u"] = _flight_tenths(ev)
    feed_mask = (ev["event_type"].isin(FEED_TYPES) & ev["player_id"].notna()
                 & ev["x_start"].notna() & ev["y_start"].notna())
    feed_mask &= ~((ev["event_type"] == "pass") & ev["x_end"].isna())
    feed_by = {k: g for k, g in ev[feed_mask].groupby("match_id")}
    app_by = {k: g for k, g in appearances[appearances["minutes_played"] > 0].groupby("match_id")}
    shots = ev[shot]
    goals = shots[shots["outcome"].astype(object) == "goal"]
    end = ev.groupby("match_id")["t"].max()
    starts = _period_starts(ev)
    shot_by = {k: g for k, g in shots.groupby("match_id")}
    goal_by = {k: g for k, g in goals.groupby("match_id")}

    out = []
    for r in matches.sort_values(["match_date", "match_id"]).itertuples(index=False):
        mid = r.match_id
        pb = [round(s, 1) for s in starts.get(mid, [])]
        entry = {"id": str(mid), "date": str(r.match_date),
                 "h": team_idx[r.home_team_name], "a": team_idx[r.away_team_name],
                 "hs": int(r.home_score), "as": int(r.away_score),
                 "ht": pb[0] if pb else PERIOD_S, "pb": pb, "end": round(float(end[mid]), 1)}
        fm = feed_by.get(mid)
        entry["ev"] = build_feed(fm if fm is not None else ev.iloc[0:0], r.home_team_id, pidx)
        lineup = {"h": [], "a": []}
        for a in app_by.get(mid, pd.DataFrame()).itertuples(index=False):
            key = str(a.player_id)
            if key not in pidx:
                continue
            side = "h" if a.team_id == r.home_team_id else "a"
            lineup[side].append([pidx[key], 0, int(round(float(end[mid]))), ""])
        entry["lu"] = lineup
        sg = shot_by.get(mid)
        entry["shots"] = [] if sg is None else [
            [int(t), 0 if tid == r.home_team_id else 1, 0.0, int(o == "goal")]
            for t, tid, o in zip(sg["t"], sg["team_id"], sg["outcome"].astype(object),
                                 strict=True)]
        gg = goal_by.get(mid)
        entry["goals"] = [] if gg is None else [
            [int(t), 0 if tid == r.home_team_id else 1, "" if pd.isna(n) else str(n)]
            for t, tid, n in zip(gg["t"], gg["team_id"], gg["player_name"], strict=True)]
        out.append(entry)
    return teams, players, out
