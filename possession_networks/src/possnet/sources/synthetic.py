"""Generate a synthetic league in StatsBomb open data JSON format.

The output has the same file layout and field names as the real cache, so the unchanged
adapter, validation, network, possession, and Markov code run on it end to end. It exists
so the repository can be run and tested without licensed data. The simulated football is
deliberately simple (a random walk of passes and carries with team strength effects) and
carries no information about any real match. All code here is original work.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

COMPETITION_ID, SEASON_ID = 9999, 1
TEAM_NAMES = ["Alder", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Ginkgo", "Hazel"]
# Home position of each of 11 slots in StatsBomb yards (attacking toward x = 120).
SLOTS = [("Goalkeeper", 8, 40), ("Left Center Back", 28, 12), ("Center Back", 25, 30),
         ("Center Back", 25, 50), ("Right Center Back", 28, 68),
         ("Left Center Midfield", 50, 15), ("Center Midfield", 48, 35),
         ("Center Midfield", 48, 45), ("Right Center Midfield", 50, 65),
         ("Left Center Forward", 80, 30), ("Right Center Forward", 80, 50)]
PERIOD_S = 2700.0


def _player(team_idx: int, slot: int) -> dict[str, Any]:
    return {"id": 1000 * (team_idx + 1) + slot, "name": f"{TEAM_NAMES[team_idx]} Player {slot}"}


class _Match:
    def __init__(self, match_id: int, home: int, away: int, strength: np.ndarray,
                 rng: np.random.Generator):
        self.mid, self.teams, self.s, self.rng = match_id, (home, away), strength, rng
        self.events: list[dict[str, Any]] = []
        self.possession = 0
        self.skip_inc = False
        self.last_team = home
        self.score = {home: 0, away: 0}
        self.active = {t: list(range(11)) for t in self.teams}  # slot -> player number
        self.pos = {t: dict(enumerate(SLOTS)) for t in self.teams}

    # ------------------------------------------------------------------ plumbing
    def emit(self, kind: str, team: int, period: int, t: float, poss_team: int,
             pattern: str = "Regular Play", **extra: Any) -> None:
        stamp = f"00:{int(t // 60):02d}:{t % 60:06.3f}"
        self.events.append({
            "id": f"{self.mid}-{len(self.events) + 1}", "index": len(self.events) + 1,
            "period": period, "timestamp": stamp, "type": {"name": kind},
            "team": {"id": team + 1, "name": TEAM_NAMES[team]},
            "possession": self.possession,
            "possession_team": {"id": poss_team + 1, "name": TEAM_NAMES[poss_team]},
            "play_pattern": {"name": pattern}, **extra})

    def who(self, team: int, slot: int) -> dict[str, Any]:
        p = _player(team, self.active[team][slot])
        return {"id": p["id"] + 0, "name": p["name"]}

    def where(self, team: int, slot: int) -> dict[str, str]:
        return {"name": SLOTS[slot][0]}

    # ------------------------------------------------------------------ actions
    def pass_to(self, team, period, t, holder, xy, pattern, kind=None, force_ok=False):
        rng = self.rng
        cands = [s for s in range(11) if s != holder]
        w = np.array([np.exp(-np.hypot(SLOTS[s][1] - SLOTS[holder][1],
                                       SLOTS[s][2] - SLOTS[holder][2]) / 22.0)
                      * (1.0 + 3.0 * max(SLOTS[s][1] - xy[0], 0) / 40.0) for s in cands])
        to = cands[rng.choice(len(cands), p=w / w.sum())]
        end = (float(np.clip(SLOTS[to][1] + rng.normal(0, 7), 1, 119)),
               float(np.clip(SLOTS[to][2] + rng.normal(0, 9), 1, 79)))
        dist = float(np.hypot(end[0] - xy[0], end[1] - xy[1]))
        p_ok = float(np.clip(0.93 - 0.003 * dist + 0.03 * self.s[team], 0.4, 0.97))
        ok = force_ok or rng.random() < p_ok
        body: dict[str, Any] = {"recipient": self.who(team, to), "end_location": list(end)}
        if kind:
            body["type"] = {"name": kind}
        out = None
        if not ok:
            out = "Out" if rng.random() < 0.3 else "Incomplete"
            body["outcome"] = {"name": out}
        self.emit("Pass", team, period, t, team, pattern, player=self.who(team, holder),
                  position=self.where(team, holder), location=[xy[0], xy[1]], **{"pass": body})
        return ok, out, to, end

    def play_possession(self, team: int, period: int, t: float, start_xy, holder: int,
                        pattern: str, kind: str | None, end_t: float):
        """Play one possession. Returns (t, next_team, next_xy, next_pattern, next_kind)."""
        rng = self.rng
        if self.skip_inc:
            self.skip_inc = False
        else:
            self.possession += 1
        self.last_team = team
        xy, first = start_xy, True
        while t < end_t:
            t += float(rng.uniform(2.0, 10.0))
            x = xy[0]
            if not first and x > 70 and rng.random() < min((x - 70) / 50.0 * 0.7, 0.5):
                dist = float(np.hypot(120 - x, 40 - xy[1]))
                xg = float(np.clip(1.2 * np.exp(-dist / 14.0), 0.01, 0.7))
                r = rng.random()
                if r < xg:
                    outcome = "Goal"
                elif r < xg + 0.3:
                    outcome = "Saved"
                elif r < xg + 0.55:
                    outcome = "Blocked"
                else:
                    outcome = "Off T"
                self.emit("Shot", team, period, t, team, pattern, player=self.who(team, holder),
                          position=self.where(team, holder), location=list(xy),
                          shot={"statsbomb_xg": round(xg, 4),
                                "end_location": [120.0, 40.0 + float(rng.normal(0, 4)), 1.0],
                                "outcome": {"name": outcome}, "type": {"name": "Open Play"}})
                other = 1 - self.teams.index(team)
                nxt = self.teams[other]
                if outcome == "Goal":
                    self.score[team] += 1
                    return t, nxt, (60.0, 40.0), "From Kick Off", "Kick Off"
                return t, nxt, (6.0, 40.0), "From Goal Kick", "Goal Kick"
            if not first and rng.random() < 0.3:  # carry forward
                end = (float(np.clip(xy[0] + rng.uniform(3, 15), 1, 119)),
                       float(np.clip(xy[1] + rng.normal(0, 4), 1, 79)))
                self.emit("Carry", team, period, t, team, pattern,
                          player=self.who(team, holder), position=self.where(team, holder),
                          location=list(xy), carry={"end_location": list(end)})
                xy = end
                t += float(rng.uniform(1.0, 4.0))
            ok, out, to, end = self.pass_to(team, period, t, holder, xy, pattern,
                                            kind if first else None)
            first = False
            if ok:
                xy, holder = end, to
                continue
            nxt = self.teams[1 - self.teams.index(team)]
            mirrored = (120 - end[0], 80 - end[1])
            if out == "Out":
                edge = (mirrored[0], 0.0 if rng.random() < 0.5 else 80.0)
                return t, nxt, edge, "From Throw In", "Throw-in"
            return t, nxt, mirrored, "Regular Play", None
        return t, team, xy, pattern, None

    # ------------------------------------------------------------------ match
    def run(self) -> tuple[list[dict], list[dict]]:
        home, away = self.teams
        for team in self.teams:
            lineup = [{"player": _player(team, i), "position": {"name": SLOTS[i][0]},
                       "jersey_number": i + 1} for i in range(11)]
            self.possession = 1
            self.emit("Starting XI", team, 1, 0.0, home, tactics={"lineup": lineup})
        sub_in = {t: _player(t, 11) for t in self.teams}
        kicking = home
        for period in (1, 2):
            if period == 2:
                self.possession += 1
            self.skip_inc = True
            self.emit("Half Start", home, period, 0.0, kicking)
            end_t = PERIOD_S + float(self.rng.uniform(60, 180))
            if period == 2:
                for team in self.teams:
                    off = self.active[team][9]
                    self.emit("Substitution", team, 2, 600.0, kicking,
                              player=_player(team, off), position={"name": SLOTS[9][0]},
                              substitution={"replacement": sub_in[team]})
                    self.active[team][9] = 11
            t, team, xy, pattern, kind = 0.0, kicking, (60.0, 40.0), "From Kick Off", "Kick Off"
            holder = 6
            while t < end_t:
                if kind in ("Goal Kick",):
                    holder = 0
                elif kind == "Throw-in":
                    holder = int(self.rng.integers(1, 9))
                elif kind is None:
                    holder = int(np.argmin([abs(SLOTS[s][1] - xy[0]) + abs(SLOTS[s][2] - xy[1])
                                            for s in range(11)]))
                else:
                    holder = 6
                t, team, xy, pattern, kind = self.play_possession(
                    team, period, t, xy, holder, pattern, kind, end_t)
            self.emit("Half End", home, period, end_t, self.last_team)
            kicking = away
        lineups = []
        for team in self.teams:
            roster = [{"player_id": _player(team, i)["id"], "player_name": _player(team, i)["name"],
                       "jersey_number": i + 1, "positions": []} for i in range(12)]
            lineups.append({"team_id": team + 1, "team_name": TEAM_NAMES[team], "lineup": roster})
        return self.events, lineups


def generate(out_root: Path, seed: int = 7, n_teams: int = 8) -> dict[str, Any]:
    """Write the synthetic cache under ``out_root`` and return a manifest dictionary."""
    rng = np.random.default_rng(seed)
    strength = rng.normal(0, 1, n_teams)
    cache = out_root / "synthetic"
    for sub in ("matches", "events", "lineups"):
        (cache / sub).mkdir(parents=True, exist_ok=True)
    (cache / f"matches/{COMPETITION_ID}").mkdir(parents=True, exist_ok=True)
    fixtures = [(h, a) for h in range(n_teams) for a in range(n_teams) if h != a]
    rng.shuffle(fixtures)
    matches, files = [], []
    start = date(2020, 1, 4)

    def write(rel: str, obj: Any) -> None:
        path = cache / rel
        data = json.dumps(obj, separators=(",", ":")).encode()
        path.write_bytes(data)
        files.append({"path": f"{cache.as_posix()}/{rel}",
                      "sha256": hashlib.sha256(data).hexdigest(),
                      "bytes": len(data), "synthetic": True})

    for i, (h, a) in enumerate(fixtures):
        mid = 90000 + i
        events, lineups = _Match(mid, h, a, strength, rng).run()
        goals = {h: 0, a: 0}
        for e in events:
            if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                goals[e["team"]["id"] - 1] += 1
        matches.append({
            "match_id": mid, "match_date": (start + timedelta(days=i // 4 * 7)).isoformat(),
            "competition": {"competition_id": COMPETITION_ID},
            "season": {"season_id": SEASON_ID, "season_name": "synthetic"},
            "competition_stage": {"name": "Regular Season"},
            "home_team": {"home_team_id": h + 1, "home_team_name": TEAM_NAMES[h]},
            "away_team": {"away_team_id": a + 1, "away_team_name": TEAM_NAMES[a]},
            "home_score": goals[h], "away_score": goals[a],
            "metadata": {"data_version": "synthetic"}})
        write(f"events/{mid}.json", events)
        write(f"lineups/{mid}.json", lineups)
    write(f"matches/{COMPETITION_ID}/{SEASON_ID}.json", matches)
    return {
        "source": "synthetic", "synthetic": True, "seed": seed,
        "competition": {"competition_id": COMPETITION_ID, "season_id": SEASON_ID,
                        "competition_name": "Synthetic League", "season_name": "synthetic"},
        "cache_dir": cache.as_posix(), "matches_listed": len(matches),
        "matches_available": len(matches),
        "license": {"agreement_url": None, "attribution": "Synthetic data, no license applies.",
                    "redistribution_allowed": True},
        "resolved_sha": "synthetic", "files": files, "failures": {},
    }
