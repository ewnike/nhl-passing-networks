"""Download and cache the Stathletes Big Data Cup 2026 hockey files.

Design notes
------------
* The files are assets of a GitHub release (tag ``Data``) on bigdatacup/Big-Data-Cup-2026.
  GitHub replaces spaces in asset names with dots, so the game
  "2025-10-11 Team A @ Team D" is published as ``2025-10-11.Team.A.@.Team.D.Events.csv``.
* Listing release assets needs the GitHub API, which is rate limited and not required here.
  The game list is read from ``camera_orientations.csv`` instead: it has one row per game and
  it is also the only place that says which way each team shoots in period 1.
* A release tag is not a commit, so assets can be replaced without notice. Every file is
  hashed in a manifest under data/manifests, and a repeat pull reports any file whose hash
  changed since the last manifest.
* Licensed data is never committed. See DATA_ACCESS.md.

What a game consists of (verified October 2026)
    <game>.Events.csv        one row per event, 21 columns, coordinates in feet
    <game>.Shifts.csv        one row per player shift, goalies are listed with Player_Id "Go"
    <game>.Tracking_P<n>.csv player and puck tracking per period (large, optional)
    camera_orientations.csv  one row per game, see :class:`Game`

Player ids in these files are jersey numbers, not stable identifiers, and team names are
anonymised (Team A to Team L). A player is therefore only identified by team plus jersey
number, and two teams can share a jersey number in the same game.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from possnet.paths import REPO_ROOT
from possnet.sources._http import CachedFile, make_session, sha256_file

LOG = logging.getLogger(__name__)

SOURCE = "stathletes"
LEGAL_URL = "https://github.com/bigdatacup/Big-Data-Cup-2026/blob/main/legal.md"
TERMS_SUMMARY = (
    "Stathletes Public Data User Agreement: research produced from the data may be shared "
    "publicly provided it is not used for profit. The agreement text says nothing about "
    "redistributing the data itself, so the raw files are treated as not redistributable."
)

CAMERA_INDEX = "camera_orientations.csv"
CAMERA_COLUMNS = ("Game", "GoalieTeamOnRightSideOfRink1stPeriod")

EVENT_COLUMNS = (
    "Date", "Home_Team", "Away_Team", "Period", "Clock",
    "Home_Team_Skaters", "Away_Team_Skaters", "Home_Team_Goals", "Away_Team_Goals",
    "Team", "Player_Id", "Event", "X_Coordinate", "Y_Coordinate",
    "Detail_1", "Detail_2", "Detail_3", "Detail_4",
    "Player_Id_2", "X_Coordinate_2", "Y_Coordinate_2",
)
# The published README names a team_name column; the files use Team plus Home_Team and Away_Team.
SHIFT_COLUMNS = (
    "Date", "Home_Team", "Away_Team", "Team", "Player_Id", "shift_number",
    "period", "start_clock", "end_clock", "shift_length",
)
TRACKING_COLUMNS = (
    "Image Id", "Period", "Game Clock", "Player or Puck", "Team", "Player Id",
    "Player Jersey Number", "Rink Location X (Feet)", "Rink Location Y (Feet)",
    "Rink Location Z (Feet)", "Goal Score",
)

PASS_EVENTS = ("Play", "Incomplete Play")
# Regulation is three periods. Tracking files exist per period; overtime periods are optional.
REGULATION_TRACKING_PERIODS = 3
MAX_TRACKING_PERIOD = 5

_GAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<away>.+) @ (?P<home>.+)$")


# ------------------------------------------------------------------------- games
@dataclass(frozen=True)
class Game:
    """One row of camera_orientations.csv.

    ``name`` is the source's own game name, "<date> <away> @ <home>".
    ``goalie_team_on_right_p1`` is "Home" or "Away": the team defending the right side of
    the camera's frame in period 1. Event coordinates are in that camera frame, so this is
    what decides which way each team attacks. Checked against shot locations in all 10
    games of the 2026 release: the home team attacks +x in period 1 exactly when this is
    "Away", and sides swap every period (overtime is not yet verified).
    """

    name: str
    date: str
    away_team: str
    home_team: str
    goalie_team_on_right_p1: str

    @property
    def game_id(self) -> str:
        """Stable id used downstream, for example ``2025-10-11_TeamA_at_TeamD``."""
        return f"{self.date}_{self.away_team}_at_{self.home_team}".replace(" ", "")

    def asset(self, kind: str) -> str:
        """Release asset file name, for kind ``Events``, ``Shifts`` or ``Tracking_P1``."""
        return f"{self.name.replace(' ', '.')}.{kind}.csv"


def parse_camera_index(text: str) -> list[Game]:
    """Parse camera_orientations.csv into games, sorted by date then name."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    missing = [c for c in CAMERA_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"{CAMERA_INDEX} is missing columns {missing}; found {reader.fieldnames}")
    games: dict[str, Game] = {}
    for row in reader:
        name = (row["Game"] or "").strip()
        if not name:
            continue
        match = _GAME_RE.match(name)
        if match is None:
            raise ValueError(f"Cannot parse game name {name!r} as '<date> <away> @ <home>'")
        side = (row["GoalieTeamOnRightSideOfRink1stPeriod"] or "").strip()
        if side not in ("Home", "Away"):
            raise ValueError(f"Game {name!r}: unexpected orientation value {side!r}")
        if name in games:
            raise ValueError(f"Game {name!r} appears twice in {CAMERA_INDEX}")
        games[name] = Game(
            name=name, date=match["date"], away_team=match["away"].strip(),
            home_team=match["home"].strip(), goalie_team_on_right_p1=side,
        )
    if not games:
        raise ValueError(f"{CAMERA_INDEX} lists no games")
    return sorted(games.values(), key=lambda g: (g.date, g.name))


def _read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [c.strip() for c in next(csv.reader(handle), [])]


def _count_rows(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


# ----------------------------------------------------------------------- puller
class StathletesPuller:
    """Fetch the Big Data Cup release files into a cache and write a manifest."""

    def __init__(
        self,
        repo: str,
        release_tag: str,
        edition: str,
        raw_dir: Path,
        manifest_dir: Path,
        workers: int = 4,
        timeout_s: int = 120,
    ) -> None:
        self.repo = repo
        self.release_tag = release_tag
        self.edition = edition
        self.base_url = f"https://github.com/{repo}/releases/download/{release_tag}"
        self.cache_root = raw_dir / edition
        self.manifest_dir = manifest_dir
        self.workers = workers
        self.session = make_session(timeout_s)

    @property
    def manifest_path(self) -> Path:
        return self.manifest_dir / f"stathletes_{self.edition}.json"

    def local(self, asset: str) -> Path:
        return self.cache_root / asset

    # --------------------------------------------------------------- download
    def _fetch(
        self,
        asset: str,
        required_columns: tuple[str, ...],
        optional: bool = False,
        force: bool = False,
    ) -> CachedFile | None:
        """Make sure ``asset`` is cached and has the expected header; return its record.

        Returns None only for an ``optional`` asset the release does not have. The download
        streams to a temporary file, is checked (length, header), and only then moved into
        place, so a failed or partial download never leaves a file in the cache.
        """
        dest = self.local(asset)
        url = f"{self.base_url}/{asset}"
        if dest.exists() and dest.stat().st_size > 0 and not force:
            return self._record(dest, url)

        resp = self.session.get(url, stream=True)
        try:
            if optional and resp.status_code == 404:
                return None
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".part")
            tmp = Path(tmp_name)
            try:
                written = 0
                with os.fdopen(fd, "wb") as handle:
                    for chunk in resp.iter_content(1 << 20):
                        handle.write(chunk)
                        written += len(chunk)
                expected = resp.headers.get("Content-Length")
                compressed = bool(resp.headers.get("Content-Encoding"))
                if expected and not compressed and int(expected) != written:
                    raise ValueError(f"Truncated download of {url}: {written} of {expected} bytes")
                if written == 0:
                    raise ValueError(f"Empty download of {url}")
                header = _read_header(tmp)
                absent = [c for c in required_columns if c not in header]
                if absent:
                    raise ValueError(
                        f"{asset} is missing expected columns {absent}. The source schema may "
                        f"have changed; header found: {header}"
                    )
                os.replace(tmp, dest)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
        finally:
            resp.close()
        return self._record(dest, url)

    @staticmethod
    def _record(dest: Path, url: str) -> CachedFile:
        try:
            rel = dest.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = dest.as_posix()
        return CachedFile(path=rel, url=url, sha256=sha256_file(dest), bytes=dest.stat().st_size)

    def games(self) -> list[Game]:
        """The game list from the cached camera index (downloads it if needed)."""
        self._fetch(CAMERA_INDEX, CAMERA_COLUMNS)
        return parse_camera_index(self.local(CAMERA_INDEX).read_text(encoding="utf-8"))

    # ------------------------------------------------------------------- main
    def pull(
        self,
        fetch_tracking: bool = False,
        max_games: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Download the camera index plus every game's files and return the manifest dict."""
        previous = self._previous_hashes()
        camera = self._fetch(CAMERA_INDEX, CAMERA_COLUMNS, force=force)
        assert camera is not None
        files: list[CachedFile] = [camera]
        listed = parse_camera_index(self.local(CAMERA_INDEX).read_text(encoding="utf-8"))
        games = listed[:max_games] if max_games is not None else listed

        jobs: list[tuple[str, tuple[str, ...], bool]] = []
        for g in games:
            jobs.append((g.asset("Events"), EVENT_COLUMNS, False))
            jobs.append((g.asset("Shifts"), SHIFT_COLUMNS, False))
            if fetch_tracking:
                for period in range(1, MAX_TRACKING_PERIOD + 1):
                    jobs.append((
                        g.asset(f"Tracking_P{period}"), TRACKING_COLUMNS,
                        period > REGULATION_TRACKING_PERIODS,
                    ))

        failures: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {
                pool.submit(self._fetch, asset, cols, optional, force): asset
                for asset, cols, optional in jobs
            }
            for i, future in enumerate(as_completed(futures), start=1):
                asset = futures[future]
                try:
                    record = future.result()
                    if record is not None:
                        files.append(record)
                except Exception as exc:  # noqa: BLE001 - recorded and re-raised below
                    failures[asset] = repr(exc)
                    LOG.error("Failed %s: %s", asset, exc)
                if i % 10 == 0 or i == len(jobs):
                    LOG.info("Fetched %d / %d files", i, len(jobs))

        files.sort(key=lambda f: f.path)
        changed = sorted(
            f.path for f in files if f.path in previous and previous[f.path] != f.sha256
        )
        if changed:
            LOG.warning(
                "%d file(s) changed upstream since the last manifest: %s", len(changed), changed
            )

        manifest = {
            "source": "stathletes_big_data_cup",
            "edition": self.edition,
            "repo": self.repo,
            "release_tag": self.release_tag,
            "pulled_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "cache_dir": self._record_dir(self.cache_root),
            "games_listed": len(listed),
            "games_pulled": len(games),
            "tracking_fetched": fetch_tracking,
            "games": [self._game_entry(g, files) for g in games],
            "license": {
                "agreement_url": LEGAL_URL,
                "terms_summary": TERMS_SUMMARY,
                "redistribution_allowed": False,
            },
            "changed_since_previous_manifest": changed,
            "files": [asdict(f) for f in files],
            "failures": failures,
        }
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        LOG.info("Wrote manifest %s", self.manifest_path)
        if failures:
            raise RuntimeError(
                f"{len(failures)} files failed to download; see manifest. "
                "Rerun the pull to retry only the missing files."
            )
        return manifest

    def _game_entry(self, game: Game, files: list[CachedFile]) -> dict[str, Any]:
        have = {Path(f.path).name for f in files}
        entry: dict[str, Any] = {**asdict(game), "game_id": game.game_id}
        for key, kind in (("event_rows", "Events"), ("shift_rows", "Shifts")):
            asset = game.asset(kind)
            entry[key] = _count_rows(self.local(asset)) if asset in have else None
        entry["tracking_periods"] = [
            p for p in range(1, MAX_TRACKING_PERIOD + 1)
            if game.asset(f"Tracking_P{p}") in have
        ]
        return entry

    def _previous_hashes(self) -> dict[str, str]:
        if not self.manifest_path.exists():
            return {}
        try:
            old = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return {f["path"]: f["sha256"] for f in old.get("files", [])}
        except (ValueError, KeyError, TypeError):
            return {}

    @staticmethod
    def _record_dir(path: Path) -> str:
        try:
            return path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.as_posix()


# ---------------------------------------------------------------------- reading
def load_manifest(manifest_dir: Path, edition: str) -> dict[str, Any]:
    path = manifest_dir / f"stathletes_{edition}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/01b_pull_stathletes.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def games_from_manifest(manifest: dict[str, Any]) -> list[Game]:
    keys = ("name", "date", "away_team", "home_team", "goalie_team_on_right_p1")
    return [Game(**{k: g[k] for k in keys}) for g in manifest["games"]]


def read_csv_text(path: Path) -> pd.DataFrame:
    """Read a source CSV with every column as text and only empty cells as missing.

    Reading ids as text avoids numbers turning into floats ("77.0") when a column has blanks.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def inventory(cache_root: Path, games: list[Game]) -> pd.DataFrame:
    """One row per game with the counts that decide whether the data is usable."""
    rows: list[dict[str, Any]] = []
    for g in games:
        events = read_csv_text(cache_root / g.asset("Events"))
        shifts = read_csv_text(cache_root / g.asset("Shifts"))
        passes = events[events["Event"].isin(PASS_EVENTS)]
        complete = passes["Event"].eq("Play")
        rows.append({
            "game_id": g.game_id,
            "event_rows": len(events),
            "max_period": int(pd.to_numeric(events["Period"]).max()),
            "pass_attempts": len(passes),
            "pass_complete": int(complete.sum()),
            "complete_no_passer": int((complete & passes["Player_Id"].isna()).sum()),
            "complete_no_receiver": int((complete & passes["Player_Id_2"].isna()).sum()),
            "shift_rows": len(shifts),
        })
    return pd.DataFrame(rows)
