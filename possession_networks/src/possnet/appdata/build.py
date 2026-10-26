"""Assemble everything the local explorer needs into one JavaScript data file.

The app is a static page. It never reads parquet or the network, so this module turns the
processed tables into ``app/data.js`` (``window.POSSNET = {...}``). The file holds match level
rows derived from licensed data and is git ignored: build it locally, do not share it.

Layout of the payload
---------------------
meta        season label, pitch size, grid size, chain names, data version
teams       team names (index = id used elsewhere)
players     player names (index = id used in pass arrays)
matches     one entry per match in date order: ``ev`` (time ordered ball and touch feed for both
            teams, see FEED_FIELDS), ``lu`` (who was on the pitch and when), shots and goals
zones       per chain configuration: absorption probabilities and sparse transitions
leaders     top players by xT per 90 for each chain configuration
evidence    step 8 comparison rows plus per window arrays for the relationship explorer
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

FEED_FIELDS = ("t", "k", "f", "r", "x0", "y0", "x1", "y1", "u")
# Feed kinds (low 3 bits of ``k``). Bit 3 is the side (0 home, 1 away), bit 4 a dead ball
# restart, bit 5 a goal. ``u`` is how long the ball segment lasts, in tenths of a second.
K_PASS, K_MISS, K_CARRY, K_SHOT, K_TOUCH = 0, 1, 2, 3, 4
TOUCH_TYPES = ("duel", "takeaway", "clearance", "giveaway", "foul", "block", "goalkeeper")
FEED_TYPES = ("pass", "carry", "shot", *TOUCH_TYPES)
MIN_CARRY_M = 3.0
# Nominal spot for each StatsBomb position name, meters in the team's attacking frame (+x toward the
# goal attacked, +y toward the team's left). A textbook shape for legibility, not a measurement.
SLOTS = {
    "Goalkeeper": (-48, 0),
    "Right Back": (-28, -26), "Right Center Back": (-35, -9), "Center Back": (-35, 0),
    "Left Center Back": (-35, 9), "Left Back": (-28, 26),
    "Right Wing Back": (-12, -30), "Left Wing Back": (-12, 30),
    "Right Defensive Midfield": (-14, -10), "Center Defensive Midfield": (-14, 0),
    "Left Defensive Midfield": (-14, 10),
    "Right Center Midfield": (-2, -12), "Center Midfield": (-2, 0),
    "Left Center Midfield": (-2, 12),
    "Right Midfield": (4, -28), "Left Midfield": (4, 28),
    "Right Attacking Midfield": (14, -14), "Center Attacking Midfield": (14, 0),
    "Left Attacking Midfield": (14, 14),
    "Right Wing": (28, -27), "Left Wing": (28, 27),
    "Right Center Forward": (30, -9), "Center Forward": (32, 0), "Left Center Forward": (30, 9),
}


def elapsed_seconds(events: pd.DataFrame) -> pd.Series:
    """Real elapsed seconds: period 2 clocks restart at 2700, so shift them after period 1."""
    p1_end = events[events["period"] == 1].groupby("match_id")["game_time_s"].max()
    shift = events["match_id"].map(p1_end) - 2700.0
    t = events["game_time_s"].astype(float)
    return t.where(events["period"] != 2, t + shift)


def _int(series: pd.Series, scale: float = 1.0) -> list[int]:
    return np.rint(series.to_numpy(float) * scale).astype(int).tolist()


def _flight_tenths(ev: pd.DataFrame) -> np.ndarray:
    """Length of each ball segment in tenths of a second.

    Completed passes last until the recipient's logged reception (within 10 s). Other passes,
    carries and shots use the distance at a typical speed, or the gap to the same player's next
    action for carries. These are visual durations: the source logs no ball tracking.
    """
    n = len(ev)
    length = np.hypot(ev["x_end"].to_numpy(float) - ev["x_start"].to_numpy(float),
                      ev["y_end"].to_numpy(float) - ev["y_start"].to_numpy(float))
    dur = np.full(n, np.nan)
    kind = ev["event_type"].to_numpy(object)
    dur[kind == "pass"] = np.clip(length[kind == "pass"] / 15.0, 0.6, 3.5)
    dur[kind == "shot"] = np.clip(length[kind == "shot"] / 22.0, 0.4, 1.5)
    t = ev["t"].to_numpy(float)
    nxt = ev.groupby(["match_id", "player_id"], sort=False)["t"].shift(-1).to_numpy(float)
    carry = kind == "carry"
    dur[carry] = np.clip(np.nan_to_num(nxt[carry] - t[carry], nan=2.0), 0.5, 8.0)
    is_complete = (ev["outcome"] == "complete").fillna(False).to_numpy(bool)
    done = (kind == "pass") & is_complete
    left = pd.DataFrame({"i": np.flatnonzero(done), "match_id": ev["match_id"].to_numpy()[done],
                         "key": ev["recipient_id"].to_numpy(object)[done],
                         "t": t[done]})
    rec = ev[ev["event_type"] == "reception"]
    right = pd.DataFrame({"match_id": rec["match_id"].to_numpy(),
                          "key": rec["player_id"].to_numpy(object),
                          "land": rec["t"].to_numpy(float), "t": rec["t"].to_numpy(float)})
    left, right = left.dropna(subset=["key"]), right.dropna(subset=["key"])
    for frame in (left, right):
        frame["key"], frame["match_id"] = frame["key"].astype(str), frame["match_id"].astype(str)
    got = pd.merge_asof(left.sort_values("t"), right.sort_values("t"), on="t",
                        by=["match_id", "key"], direction="forward", tolerance=10.0)
    ok = got["land"].notna()
    dur[got.loc[ok, "i"].to_numpy()] = np.clip(got.loc[ok, "land"] - got.loc[ok, "t"], 0.3, 6.0)
    return np.rint(np.nan_to_num(dur, nan=0.0) * 10).astype(int)


def _spread(t10: np.ndarray, gap: int = 1) -> np.ndarray:
    """Make times strictly increasing by at least ``gap`` tenths so every segment can animate."""
    out = np.empty_like(t10)
    prev = -10**9
    for i, v in enumerate(t10.tolist()):
        prev = max(v, prev + gap)
        out[i] = prev
    return out


def build_feed(ev: pd.DataFrame, home_team_id, pidx: dict) -> dict:
    """Ball and touch feed for one match, both teams, in time order (own team frame)."""
    cols = {k: [] for k in FEED_FIELDS}
    if ev.empty:
        return cols
    kind = ev["event_type"].to_numpy(object)
    k = np.full(len(ev), K_TOUCH)
    complete = (ev["outcome"] == "complete").fillna(False).to_numpy(bool)
    k[kind == "pass"] = np.where(complete[kind == "pass"], K_PASS, K_MISS)
    k[kind == "carry"], k[kind == "shot"] = K_CARRY, K_SHOT
    side = (ev["team_id"].to_numpy() != home_team_id).astype(int)
    goal = (kind == "shot") & (ev["outcome"] == "goal").fillna(False).to_numpy(bool)
    dead = ev["is_dead_ball"].astype(bool).to_numpy().astype(int)
    k = k | (side << 3) | (dead << 4) | (goal.astype(int) << 5)
    t10 = _spread(np.rint(ev["t"].to_numpy(float) * 10).astype(int))
    rec = ev["recipient_id"].astype(object)
    cols["t"] = t10.tolist()
    cols["k"] = k.tolist()
    cols["f"] = [pidx[str(x)] for x in ev["player_id"]]
    cols["r"] = [pidx.get(str(x), -1) if not pd.isna(x) else -1 for x in rec]
    ends = np.isin(kind, ("pass", "carry", "shot"))
    x1 = np.where(ends, ev["x_end"].to_numpy(float), ev["x_start"].to_numpy(float))
    y1 = np.where(ends, ev["y_end"].to_numpy(float), ev["y_start"].to_numpy(float))
    cols["x0"], cols["y0"] = _int(ev["x_start"]), _int(ev["y_start"])
    cols["x1"], cols["y1"] = np.rint(x1).astype(int).tolist(), np.rint(y1).astype(int).tolist()
    cols["u"] = ev["u"].astype(int).tolist()
    return cols


def build_matches(matches: pd.DataFrame, events: pd.DataFrame,
                  appearances: pd.DataFrame) -> tuple[list, list, list]:
    """Return (teams, players, match entries)."""
    ev = events.copy()
    ev["t"] = elapsed_seconds(ev)
    teams = sorted(set(matches["home_team_name"]) | set(matches["away_team_name"]))
    team_idx = {n: i for i, n in enumerate(teams)}

    names = pd.concat([ev[["player_id", "player_name"]].rename(columns={}),
                       ev[["recipient_id", "recipient_name"]].set_axis(
                           ["player_id", "player_name"], axis=1)]).dropna().drop_duplicates(
        "player_id")
    players = names["player_name"].astype(str).tolist()
    pidx = dict(zip(names["player_id"].astype(str), range(len(names)), strict=True))

    ev = ev.sort_values(["match_id", "event_index"], kind="stable").reset_index(drop=True)
    ev["u"] = _flight_tenths(ev)
    feed_mask = (ev["event_type"].isin(FEED_TYPES) & ev["player_id"].notna()
                 & ev["x_start"].notna() & ev["y_start"].notna())
    shots_len = np.hypot(ev["x_end"] - ev["x_start"], ev["y_end"] - ev["y_start"])
    feed_mask &= ~((ev["event_type"] == "carry") & (shots_len < MIN_CARRY_M))
    feed_mask &= ~(ev["event_type"].isin(("pass", "shot")) & ev["x_end"].isna())
    feed_by = {k: g for k, g in ev[feed_mask].groupby("match_id")}
    modal = (ev.dropna(subset=["position"]).groupby(["match_id", "player_id", "position"]).size()
             .rename("n").reset_index().sort_values("n").drop_duplicates(["match_id", "player_id"],
                                                                          keep="last"))
    modal_pos = {(str(m), str(p)): str(q) for m, p, q in zip(
        modal["match_id"], modal["player_id"], modal["position"], strict=True)}
    app_by = {k: g for k, g in appearances[appearances["minutes_played"] > 0].groupby("match_id")}
    shots = ev[ev["event_type"] == "shot"]
    goals = ev[((ev["event_type"] == "shot") & (ev["outcome"].astype(object) == "goal"))
               | (ev["event_subtype"].astype(object) == "Own Goal For")]
    p1_end = ev[ev["period"] == 1].groupby("match_id")["t"].max()
    end = ev.groupby("match_id")["t"].max()
    shot_by = {k: g for k, g in shots.groupby("match_id")}
    goal_by = {k: g for k, g in goals.groupby("match_id")}

    out = []
    for r in matches.sort_values(["match_date", "match_id"]).itertuples(index=False):
        mid = r.match_id
        entry = {"id": str(mid), "date": str(r.match_date),
                 "h": team_idx[r.home_team_name], "a": team_idx[r.away_team_name],
                 "hs": int(r.home_score), "as": int(r.away_score),
                 "ht": round(float(p1_end[mid]), 1), "end": round(float(end[mid]), 1)}
        fm = feed_by.get(mid)
        entry["ev"] = build_feed(fm, r.home_team_id, pidx) if fm is not None else build_feed(
            ev.iloc[0:0], r.home_team_id, pidx)
        lineup = {"h": [], "a": []}
        for a in app_by.get(mid, pd.DataFrame()).itertuples(index=False):
            key = str(a.player_id)
            if key not in pidx:
                continue
            mins = float(a.minutes_played) * 60.0
            on = 0.0 if a.started else max(0.0, float(end[mid]) - mins)
            off = min(float(end[mid]), on + mins) if a.started else float(end[mid])
            side = "h" if a.team_id == r.home_team_id else "a"
            lineup[side].append([pidx[key], int(round(on)), int(round(off)),
                                 modal_pos.get((str(mid), key), "")])
        entry["lu"] = lineup
        sg = shot_by.get(mid)
        entry["shots"] = [] if sg is None else [
            [int(t), 0 if tid == r.home_team_id else 1, round(float(xg), 3),
             int(o == "goal")]
            for t, tid, xg, o in zip(sg["t"], sg["team_id"], sg["xg"].fillna(0),
                                     sg["outcome"].astype(object), strict=True)]
        gg = goal_by.get(mid)
        entry["goals"] = [] if gg is None else [
            [int(t), 0 if tid == r.home_team_id else 1, "" if pd.isna(n) else str(n)]
            for t, tid, n in zip(gg["t"], gg["team_id"], gg["player_name"], strict=True)]
        out.append(entry)
    return teams, players, out


def build_zones(actions: pd.DataFrame, grid, specs) -> dict:
    """Absorption values and sparse season transition counts for each chain configuration."""
    from possnet.markov.chain import build_transitions, count_matrix, fit_chain

    zones = {}
    for spec in specs:
        table = fit_chain(actions, grid, spec)
        counts = count_matrix(build_transitions(actions, grid, spec), grid.n_zones)
        sparse = []
        for z in range(grid.n_zones):
            nz = np.flatnonzero(counts[z])
            sparse.append([[int(j), int(counts[z, j])] for j in nz])
        zones[spec.name] = {
            "goal": table["p_goal"].round(5).tolist(), "shot": table["p_shot"].round(5).tolist(),
            "turnover": table["p_turnover"].round(5).tolist(),
            "visits": table["visits"].astype(int).tolist(), "moves": sparse}
    return zones


def build_leaders(xt_player_season: pd.DataFrame, top: int = 12) -> dict:
    out = {}
    for config, g in xt_player_season.groupby("config"):
        g = g.sort_values("xt_goal_per90", ascending=False).head(top)
        out[config] = [{"name": str(n), "xt": round(float(v), 3), "min": int(m)}
                       for n, v, m in zip(g["player_name"], g["xt_goal_per90"],
                                          g["minutes"], strict=True)]
    return out


def evidence_windows(ctx, chain: str, windows: dict[str, str]) -> dict:
    """Home perspective feature arrays per window, with shot adjusted goal residuals."""
    from possnet.incremental.data import NET_STRUCT, VOLUME

    out = {}
    for key, label in windows.items():
        table = ctx.table(key, "open_play")
        home = table.iloc[::2].reset_index(drop=True)
        xt = ctx.xt(chain, 1, True, key).features(np.arange(len(home)))[::2]
        feats = {c: home[c].to_numpy(float) for c in (VOLUME, *NET_STRUCT)}
        feats["xt_goal"], feats["xt_attempt"] = xt[:, 0], xt[:, 1]
        shots = home["shots"].to_numpy(float)
        design = np.column_stack([np.ones(len(shots)), shots])
        res = {}
        for tgt in ("gd", "xgd"):
            y = home[tgt].to_numpy(float)
            beta = np.linalg.lstsq(design, y, rcond=None)[0]
            res[tgt] = y - design @ beta
        out[key] = {
            "label": label, "n": int(len(home)),
            "shots": np.round(shots, 2).tolist(),
            "gd": home["gd"].round(3).tolist(), "xgd": home["xgd"].round(3).tolist(),
            "res_gd": np.round(res["gd"], 3).tolist(), "res_xgd": np.round(res["xgd"], 3).tolist(),
            "feats": {k: [None if np.isnan(x) else round(float(x), 4) for x in v]
                      for k, v in feats.items()},
        }
    return out


def comparisons_payload(comparisons: pd.DataFrame) -> list[dict]:
    cols = ["axis", "value", "target", "baseline", "added", "r2_base", "r2_new", "delta_r2",
            "ci_low", "ci_high", "n_matches"]
    d = comparisons[cols].copy()
    for c in ("r2_base", "r2_new", "delta_r2", "ci_low", "ci_high"):
        d[c] = d[c].round(4)
    return d.to_dict("records")


def write_data_js(payload: dict, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "window.POSSNET = " + json.dumps(payload, separators=(",", ":"), allow_nan=False) + ";\n"
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))
