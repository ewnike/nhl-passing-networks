"""Offline tests for the Stathletes downloader (no network access, synthetic CSV text only)."""

from __future__ import annotations

import json

import pytest

from possnet.config import load_config
from possnet.paths import repo_path
from possnet.sources import stathletes as st

BASE = "https://github.com/bigdatacup/Big-Data-Cup-2026/releases/download/Data"
GAME_A = "2025-10-11 Team A @ Team D"
GAME_B = "2025-10-17 Team F @ Team L"


def _csv(columns, rows):
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(str(row.get(c, "")) for c in columns))
    return ("\n".join(lines) + "\n").encode()


def _event_rows(home, away):
    base = {"Date": "2025-10-11", "Home_Team": home, "Away_Team": away, "Period": 1,
            "Clock": "19:50", "Home_Team_Skaters": 5, "Away_Team_Skaters": 5,
            "Home_Team_Goals": 0, "Away_Team_Goals": 0, "Team": home}
    return [
        {**base, "Player_Id": 77, "Event": "Play", "X_Coordinate": 10, "Y_Coordinate": 5,
         "Player_Id_2": 42, "X_Coordinate_2": 30, "Y_Coordinate_2": 6},
        {**base, "Player_Id": 42, "Event": "Play", "X_Coordinate": 30, "Y_Coordinate": 6,
         "Player_Id_2": "", "X_Coordinate_2": 50, "Y_Coordinate_2": 0},
        {**base, "Player_Id": 42, "Event": "Incomplete Play", "X_Coordinate": 50,
         "Y_Coordinate": 0, "Player_Id_2": 9, "X_Coordinate_2": 70, "Y_Coordinate_2": 1},
        {**base, "Player_Id": 42, "Event": "Shot", "X_Coordinate": 60, "Y_Coordinate": 2},
    ]


def _shift_rows(home, away):
    return [{"Date": "2025-10-11", "Home_Team": home, "Away_Team": away, "Team": home,
             "Player_Id": 77, "shift_number": 1, "period": 1, "start_clock": "20:00",
             "end_clock": "19:00", "shift_length": "01:00"}]


def _fake_release(games=(GAME_A,), tracking=False):
    camera = "Game,GoalieTeamOnRightSideOfRink1stPeriod\n" + "\n".join(
        f"{g},Away" for g in games)  # no trailing newline, as in the real file
    files = {st.CAMERA_INDEX: camera.encode()}
    for g in games:
        match = st._GAME_RE.match(g)
        away, home = match["away"], match["home"]
        game = st.Game(g, match["date"], away, home, "Away")
        files[game.asset("Events")] = _csv(st.EVENT_COLUMNS, _event_rows(home, away))
        files[game.asset("Shifts")] = _csv(st.SHIFT_COLUMNS, _shift_rows(home, away))
        if tracking:
            for p in (1, 2, 3):
                files[game.asset(f"Tracking_P{p}")] = _csv(st.TRACKING_COLUMNS, [{}])
    return files


class _FakeResponse:
    def __init__(self, status: int, payload: bytes, headers: dict | None = None) -> None:
        self.status_code, self._payload = status, payload
        self.headers = headers if headers is not None else {"Content-Length": str(len(payload))}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int):
        for i in range(0, len(self._payload), chunk_size):
            yield self._payload[i:i + chunk_size]

    def close(self) -> None:
        return None


class _FakeSession:
    def __init__(self, files: dict[str, bytes], bad_length: set[str] | None = None) -> None:
        self.files, self.calls, self.bad_length = files, [], bad_length or set()

    def get(self, url: str, stream: bool = False) -> _FakeResponse:
        self.calls.append(url)
        name = url.removeprefix(BASE + "/")
        if name not in self.files:
            return _FakeResponse(404, b"Not Found")
        payload = self.files[name]
        if name in self.bad_length:
            return _FakeResponse(200, payload[:-5], {"Content-Length": str(len(payload))})
        return _FakeResponse(200, payload)


def _puller(tmp_path, monkeypatch, files, **kwargs):
    monkeypatch.setattr(st, "REPO_ROOT", tmp_path)
    puller = st.StathletesPuller(
        "bigdatacup/Big-Data-Cup-2026", "Data", "bdc_test",
        tmp_path / "raw", tmp_path / "man", workers=1,
    )
    puller.session = _FakeSession(files, **kwargs)
    return puller


# ------------------------------------------------------------------ game names
def test_asset_names_use_dots_for_spaces():
    g = st.parse_camera_index(f"Game,GoalieTeamOnRightSideOfRink1stPeriod\n{GAME_A},Away\n")[0]
    assert g.asset("Events") == "2025-10-11.Team.A.@.Team.D.Events.csv"
    assert g.asset("Tracking_P2") == "2025-10-11.Team.A.@.Team.D.Tracking_P2.csv"
    assert g.game_id == "2025-10-11_TeamA_at_TeamD"
    assert (g.away_team, g.home_team) == ("Team A", "Team D")


def test_camera_index_without_trailing_newline_and_with_bom():
    text = "﻿Game,GoalieTeamOnRightSideOfRink1stPeriod\n" f"{GAME_B},Home\n{GAME_A},Away"
    games = st.parse_camera_index(text)
    assert [g.date for g in games] == ["2025-10-11", "2025-10-17"]
    assert games[1].goalie_team_on_right_p1 == "Home"


@pytest.mark.parametrize("text, message", [
    ("Game,Other\nx,y\n", "missing columns"),
    ("Game,GoalieTeamOnRightSideOfRink1stPeriod\nnot a game,Away\n", "Cannot parse"),
    (f"Game,GoalieTeamOnRightSideOfRink1stPeriod\n{GAME_A},Left\n", "unexpected orientation"),
    (f"Game,GoalieTeamOnRightSideOfRink1stPeriod\n{GAME_A},Away\n{GAME_A},Home\n", "twice"),
    ("Game,GoalieTeamOnRightSideOfRink1stPeriod\n", "lists no games"),
])
def test_bad_camera_index_is_rejected(text, message):
    with pytest.raises(ValueError, match=message):
        st.parse_camera_index(text)


# ----------------------------------------------------------------------- pulls
def test_pull_writes_manifest_and_caches(tmp_path, monkeypatch):
    puller = _puller(tmp_path, monkeypatch, _fake_release((GAME_A, GAME_B)))
    manifest = puller.pull()
    assert manifest["games_listed"] == manifest["games_pulled"] == 2
    assert manifest["license"]["redistribution_allowed"] is False
    assert len(manifest["files"]) == 1 + 2 * 2  # camera index plus events and shifts per game
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])
    first = manifest["games"][0]
    assert first["game_id"] == "2025-10-11_TeamA_at_TeamD"
    assert (first["event_rows"], first["shift_rows"]) == (4, 1)
    assert first["tracking_periods"] == []
    assert (tmp_path / "man" / "stathletes_bdc_test.json").exists()
    # cached files land where the project already looks for them
    assert (tmp_path / "raw" / "bdc_test" / "2025-10-11.Team.A.@.Team.D.Events.csv").exists()


def test_second_pull_uses_cache(tmp_path, monkeypatch):
    puller = _puller(tmp_path, monkeypatch, _fake_release())
    puller.pull()
    first_calls = len(puller.session.calls)
    manifest = puller.pull()
    assert len(puller.session.calls) == first_calls
    assert manifest["changed_since_previous_manifest"] == []


def test_max_games_limits_the_pull(tmp_path, monkeypatch):
    puller = _puller(tmp_path, monkeypatch, _fake_release((GAME_A, GAME_B)))
    manifest = puller.pull(max_games=1)
    assert (manifest["games_listed"], manifest["games_pulled"]) == (2, 1)
    assert len(manifest["files"]) == 3


def test_changed_upstream_file_is_reported(tmp_path, monkeypatch):
    files = _fake_release()
    puller = _puller(tmp_path, monkeypatch, files)
    puller.pull()
    events = st.Game(GAME_A, "2025-10-11", "Team A", "Team D", "Away").asset("Events")
    files[events] = files[events] + b",,,,,,,,,,,,,,,,,,,,\n"
    manifest = puller.pull(force=True)
    assert [p.rsplit("/", 1)[-1] for p in manifest["changed_since_previous_manifest"]] == [events]


def test_missing_columns_are_rejected_and_nothing_is_cached(tmp_path, monkeypatch):
    files = _fake_release()
    events = st.Game(GAME_A, "2025-10-11", "Team A", "Team D", "Away").asset("Events")
    files[events] = b"Date,Home_Team\n2025-10-11,Team D\n"
    puller = _puller(tmp_path, monkeypatch, files)
    with pytest.raises(RuntimeError, match="failed to download"):
        puller.pull()
    manifest = json.loads((tmp_path / "man" / "stathletes_bdc_test.json").read_text())
    assert "missing expected columns" in manifest["failures"][events]
    cache = tmp_path / "raw" / "bdc_test"
    assert not (cache / events).exists()
    assert not list(cache.glob("*.part"))


def test_truncated_download_is_rejected(tmp_path, monkeypatch):
    files = _fake_release()
    shifts = st.Game(GAME_A, "2025-10-11", "Team A", "Team D", "Away").asset("Shifts")
    puller = _puller(tmp_path, monkeypatch, files, bad_length={shifts})
    with pytest.raises(RuntimeError, match="failed to download"):
        puller.pull()
    manifest = json.loads((tmp_path / "man" / "stathletes_bdc_test.json").read_text())
    assert "Truncated" in manifest["failures"][shifts]
    assert not (tmp_path / "raw" / "bdc_test" / shifts).exists()


def test_missing_required_asset_fails_but_missing_overtime_tracking_does_not(
    tmp_path, monkeypatch
):
    puller = _puller(tmp_path, monkeypatch, _fake_release(tracking=True))
    manifest = puller.pull(fetch_tracking=True)
    assert manifest["games"][0]["tracking_periods"] == [1, 2, 3]  # P4 and P5 404 quietly
    assert len(manifest["files"]) == 1 + 2 + 3

    files = _fake_release(tracking=True)
    del files[st.Game(GAME_A, "2025-10-11", "Team A", "Team D", "Away").asset("Tracking_P2")]
    puller = _puller(tmp_path / "other", monkeypatch, files)
    with pytest.raises(RuntimeError, match="failed to download"):
        puller.pull(fetch_tracking=True)


# ------------------------------------------------------------------- inventory
def test_inventory_counts_passes_and_missing_ids(tmp_path, monkeypatch):
    puller = _puller(tmp_path, monkeypatch, _fake_release())
    manifest = puller.pull()
    table = st.inventory(puller.cache_root, st.games_from_manifest(manifest))
    row = table.iloc[0]
    assert row["event_rows"] == 4
    assert row["pass_attempts"] == 3
    assert row["pass_complete"] == 2
    assert row["complete_no_passer"] == 0
    assert row["complete_no_receiver"] == 1
    assert row["max_period"] == 1


def test_read_csv_text_keeps_ids_as_text(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("Player_Id,Player_Id_2\n77,\nGo,5\n")
    frame = st.read_csv_text(path)
    assert frame["Player_Id"].tolist() == ["77", "Go"]
    assert frame["Player_Id_2"].isna().tolist() == [True, False]


# ---------------------------------------------------------------------- config
def test_hockey_config_loads_without_a_statsbomb_section():
    cfg = load_config(repo_path("config/hockey.yaml"))
    assert cfg.source == "stathletes"
    assert cfg.statsbomb is None
    assert cfg.stathletes is not None and cfg.stathletes.edition == "bdc_2026"
    assert cfg.paths.raw_dir.as_posix().endswith("data/raw/stathletes")
    assert "hockey" in cfg.paths.tables_dir.as_posix()  # never overwrites soccer outputs


def test_soccer_config_is_unchanged():
    cfg = load_config(repo_path("config/project.yaml"))
    assert cfg.source == "statsbomb"
    assert cfg.statsbomb is not None and cfg.statsbomb.competition_id == 2
    assert cfg.stathletes is None
