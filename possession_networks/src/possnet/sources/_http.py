"""Download helpers shared by every provider module in this package.

Nothing here knows about a specific provider. The StatsBomb and Stathletes pullers both
use the same retrying session, atomic file writes, and hashing.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "possnet-capstone/0.1 (academic research)"


@dataclass(frozen=True)
class CachedFile:
    """One file in a raw cache, as listed in a pull manifest."""

    path: str  # relative to the repository root, POSIX style
    url: str
    sha256: str
    bytes: int


def make_session(timeout_s: int) -> requests.Session:
    """A requests session that retries transient failures and applies a default timeout."""
    session = requests.Session()
    retry = Retry(
        total=5, backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    session.request = _with_timeout(session.request, timeout_s)  # type: ignore[method-assign]
    return session


def _with_timeout(fn: Any, timeout_s: int) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", timeout_s)
        return fn(*args, **kwargs)

    return wrapper


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(dest: Path, payload: bytes) -> None:
    """Write bytes to ``dest`` so a crash never leaves a half written file behind."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp_name, dest)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
