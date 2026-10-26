"""Download and cache StatsBomb open data for one competition season.

Design notes
------------
* Data is fetched straight from the public GitHub repository over HTTPS. The
  statsbombpy package is not required; plain JSON files keep the raw layer
  byte identical to what StatsBomb publishes.
* The branch name is resolved to a commit SHA, and the cache directory is keyed
  by that SHA. A pinned SHA in config/project.yaml means every teammate
  analyses exactly the same files even if StatsBomb later corrects matches.
* Every file is hashed (SHA 256) and listed in a manifest under data/manifests.
  Manifests contain no StatsBomb data, so they can be committed.
* Licensed data is never committed. See DATA_ACCESS.md.

Folder layout in the upstream repository (verified October 2026):
    data/competitions.json
    data/matches/<competition_id>/<season_id>.json
    data/events/<match_id>.json
    data/lineups/<match_id>.json
    data/three-sixty/<match_id>.json   (only for some matches, optional)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from possnet.paths import REPO_ROOT

LOG = logging.getLogger(__name__)

LICENSE_URL = "https://github.com/hudl/open-data/blob/master/LICENSE.pdf"
RESOURCE_CENTRE_URL = "https://statsbomb.com/resource-centre/"
MEDIA_PACK_URL = "https://statsbomb.com/media-pack/"
ATTRIBUTION_TEXT = (
    "Data provided by StatsBomb (open data). "
    "StatsBomb attribution and logo required on any publication."
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class CachedFile:
    """One file in the raw cache."""

    path: str  # relative to the repository root, POSIX style
    url: str
    sha256: str
    bytes: int


def resolve_ref(repo: str, ref: str) -> str | None:
    """Return the commit SHA for a branch, tag, or SHA; None if it cannot be resolved.

    Tries ``git ls-remote`` first (no API rate limit), then the GitHub REST API.
    """
    if _SHA_RE.match(ref):
        return ref
    url = f"https://github.com/{repo}.git"
    for pattern in (f"refs/heads/{ref}", f"refs/tags/{ref}", ref):
        try:
            out = subprocess.run(
                ["git", "ls-remote", url, pattern],
                capture_output=True, text=True, timeout=60, check=False,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            out = ""
        if out:
            sha = out.split()[0]
            if _SHA_RE.match(sha):
                return sha
    try:
        resp = requests.get(f"https://api.github.com/repos/{repo}/commits/{ref}", timeout=30)
        sha = resp.json().get("sha", "")
        return sha if _SHA_RE.match(sha) else None
    except (requests.RequestException, ValueError):
        return None


def _session(timeout_s: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5, backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "possnet-capstone/0.1 (academic research)"
    session.request = _with_timeout(session.request, timeout_s)  # type: ignore[method-assign]
    return session


def _with_timeout(fn: Any, timeout_s: int) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", timeout_s)
        return fn(*args, **kwargs)

    return wrapper


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(dest: Path, payload: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp_name, dest)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


class StatsBombPuller:
    """Fetch one competition season into a SHA keyed cache and write a manifest."""

    def __init__(
        self,
        repo: str,
        ref: str,
        raw_dir: Path,
        manifest_dir: Path,
        workers: int = 6,
        timeout_s: int = 60,
    ) -> None:
        self.repo = repo
        self.requested_ref = ref
        self.sha = resolve_ref(repo, ref)
        if self.sha is None:
            LOG.warning(
                "Could not resolve %r to a commit SHA; falling back to the moving ref. "
                "The manifest will record resolved_sha as null.", ref,
            )
        self.fetch_ref = self.sha or ref
        self.base_url = f"https://raw.githubusercontent.com/{repo}/{self.fetch_ref}/data"
        self.cache_root = raw_dir / (self.sha[:12] if self.sha else f"unpinned_{ref}")
        self.manifest_dir = manifest_dir
        self.workers = workers
        self.session = _session(timeout_s)

    # ------------------------------------------------------------------ paths
    def local(self, rel: str) -> Path:
        return self.cache_root / rel

    # --------------------------------------------------------------- download
    def _ensure(self, rel: str, force: bool = False) -> CachedFile:
        """Make sure ``rel`` (for example ``events/123.json``) is cached; return its record."""
        dest = self.local(rel)
        url = f"{self.base_url}/{rel}"
        if dest.exists() and dest.stat().st_size > 0 and not force:
            return self._record(dest, url)
        resp = self.session.get(url)
        resp.raise_for_status()
        body = resp.content.strip()
        if not body or body[:1] not in (b"[", b"{") or body[-1:] not in (b"]", b"}"):
            raise ValueError(f"Unexpected payload for {url} ({len(body)} bytes)")
        _atomic_write(dest, resp.content)
        return self._record(dest, url)

    @staticmethod
    def _record(dest: Path, url: str) -> CachedFile:
        try:
            rel_to_repo = dest.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel_to_repo = dest.as_posix()
        return CachedFile(
            path=rel_to_repo, url=url, sha256=_sha256_file(dest), bytes=dest.stat().st_size
        )

    def _load_json(self, rel: str) -> Any:
        return json.loads(self.local(rel).read_text(encoding="utf-8"))

    # ------------------------------------------------------------------- main
    def pull_competition_season(
        self,
        competition_id: int,
        season_id: int,
        fetch_lineups: bool = True,
        fetch_three_sixty: bool = False,
        max_matches: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Download everything for one competition season and return the manifest dict."""
        files: list[CachedFile] = [self._ensure("competitions.json", force)]
        competitions = self._load_json("competitions.json")
        entry = next(
            (c for c in competitions
             if c["competition_id"] == competition_id and c["season_id"] == season_id),
            None,
        )
        if entry is None:
            raise ValueError(
                f"competition_id={competition_id}, season_id={season_id} is not in "
                "competitions.json. Run scripts/01_pull_data.py --list to see options."
            )

        matches_rel = f"matches/{competition_id}/{season_id}.json"
        files.append(self._ensure(matches_rel, force))
        matches = self._load_json(matches_rel)
        available = [m for m in matches if m.get("match_status") == "available"]
        available.sort(key=lambda m: (m["match_date"], m["match_id"]))
        if max_matches is not None:
            available = available[:max_matches]

        jobs: list[str] = []
        for m in available:
            mid = m["match_id"]
            jobs.append(f"events/{mid}.json")
            if fetch_lineups:
                jobs.append(f"lineups/{mid}.json")
            if fetch_three_sixty and m.get("match_status_360") == "available":
                jobs.append(f"three-sixty/{mid}.json")

        failures: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._ensure, rel, force): rel for rel in jobs}
            for i, future in enumerate(as_completed(futures), start=1):
                rel = futures[future]
                try:
                    files.append(future.result())
                except Exception as exc:  # noqa: BLE001 - recorded and re-raised below
                    failures[rel] = repr(exc)
                    LOG.error("Failed %s: %s", rel, exc)
                if i % 25 == 0 or i == len(jobs):
                    LOG.info("Fetched %d / %d files", i, len(jobs))

        files.sort(key=lambda f: f.path)
        manifest = {
            "source": "statsbomb_open_data",
            "repo": self.repo,
            "requested_ref": self.requested_ref,
            "resolved_sha": self.sha,
            "pulled_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "competition": {k: entry[k] for k in (
                "competition_id", "season_id", "country_name",
                "competition_name", "season_name", "competition_gender",
            )},
            "cache_dir": self._record_dir(self.cache_root),
            "matches_listed": len(matches),
            "matches_available": len(available),
            "license": {
                "agreement_url": LICENSE_URL,
                "resource_centre_url": RESOURCE_CENTRE_URL,
                "media_pack_url": MEDIA_PACK_URL,
                "attribution": ATTRIBUTION_TEXT,
                "redistribution_allowed": False,
            },
            "files": [asdict(f) for f in files],
            "failures": failures,
        }
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.manifest_dir / f"statsbomb_c{competition_id}_s{season_id}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        LOG.info("Wrote manifest %s", manifest_path)
        if failures:
            raise RuntimeError(
                f"{len(failures)} files failed to download; see manifest. "
                "Rerun the pull to retry only the missing files."
            )
        return manifest

    @staticmethod
    def _record_dir(path: Path) -> str:
        try:
            return path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.as_posix()


def list_competitions(puller: StatsBombPuller) -> list[dict[str, Any]]:
    """Return competitions.json entries (downloads the small index if needed)."""
    puller._ensure("competitions.json")
    return puller._load_json("competitions.json")


def load_manifest(manifest_dir: Path, competition_id: int, season_id: int) -> dict[str, Any]:
    path = manifest_dir / f"statsbomb_c{competition_id}_s{season_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/01_pull_data.py first.")
    return json.loads(path.read_text(encoding="utf-8"))
