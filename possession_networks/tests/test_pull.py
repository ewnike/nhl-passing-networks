"""Offline tests for the downloader (no network access is used)."""

from __future__ import annotations

import json

import pytest

from possnet.sources import statsbomb as sb

SHA = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"


def test_resolve_ref_passes_through_full_sha():
    assert sb.resolve_ref("hudl/open-data", SHA) == SHA


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.content = payload

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files, self.calls = files, []

    def get(self, url: str) -> _FakeResponse:
        self.calls.append(url)
        key = url.split("/data/", 1)[1]
        return _FakeResponse(self.files[key])


def _make_puller(tmp_path, files):
    puller = sb.StatsBombPuller("hudl/open-data", SHA, tmp_path / "raw", tmp_path / "man")
    puller.session = _FakeSession(files)
    return puller


def _fake_files():
    comps = [{"competition_id": 1, "season_id": 2, "country_name": "X",
              "competition_name": "L", "season_name": "S", "competition_gender": "male"}]
    matches = [{"match_id": 7, "match_date": "2020-01-01", "match_status": "available"},
               {"match_id": 8, "match_date": "2020-01-02", "match_status": "scheduled"}]
    return {
        "competitions.json": json.dumps(comps).encode(),
        "matches/1/2.json": json.dumps(matches).encode(),
        "events/7.json": b"[{}]",
        "lineups/7.json": b"[{}]",
    }


def test_pull_writes_manifest_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "REPO_ROOT", tmp_path)
    puller = _make_puller(tmp_path, _fake_files())
    manifest = puller.pull_competition_season(1, 2)
    assert manifest["resolved_sha"] == SHA
    assert manifest["matches_available"] == 1  # the scheduled match is skipped
    assert manifest["license"]["redistribution_allowed"] is False
    paths = {f["path"] for f in manifest["files"]}
    assert any(p.endswith("events/7.json") for p in paths)
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])
    assert (tmp_path / "man" / "statsbomb_c1_s2.json").exists()


def test_second_pull_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "REPO_ROOT", tmp_path)
    puller = _make_puller(tmp_path, _fake_files())
    puller.pull_competition_season(1, 2)
    first_calls = len(puller.session.calls)
    puller.pull_competition_season(1, 2)
    assert len(puller.session.calls) == first_calls


def test_unknown_competition_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "REPO_ROOT", tmp_path)
    puller = _make_puller(tmp_path, _fake_files())
    with pytest.raises(ValueError, match="not in competitions.json"):
        puller.pull_competition_season(99, 99)


def test_truncated_payload_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "REPO_ROOT", tmp_path)
    files = _fake_files()
    files["events/7.json"] = b'[{"id": 1'
    puller = _make_puller(tmp_path, files)
    with pytest.raises(RuntimeError, match="failed to download"):
        puller.pull_competition_season(1, 2)
