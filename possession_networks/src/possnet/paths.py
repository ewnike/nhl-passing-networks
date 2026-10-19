"""Repository relative path helpers.

Every path in the project is derived from the repository root, which is found
from this file's location. Nothing is hard coded to a user's machine.
"""

from __future__ import annotations

from pathlib import Path

# src/possnet/paths.py -> parents[0]=possnet, [1]=src, [2]=repository root
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
CONFIG_PATH: Path = REPO_ROOT / "config" / "project.yaml"


def repo_path(relative: str | Path) -> Path:
    """Resolve a repository relative path to an absolute one."""
    return REPO_ROOT / Path(relative)
