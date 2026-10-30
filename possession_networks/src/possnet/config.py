"""Load the project configuration from config/project.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from possnet.paths import CONFIG_PATH, repo_path


@dataclass(frozen=True)
class StatsBombConfig:
    repo: str
    ref: str
    competition_id: int
    season_id: int
    fetch_lineups: bool = True
    fetch_three_sixty: bool = False
    workers: int = 6
    timeout_s: int = 60


@dataclass(frozen=True)
class StathletesConfig:
    """Stathletes Big Data Cup release (hockey). See possnet.sources.stathletes."""

    repo: str
    release_tag: str
    edition: str
    fetch_tracking: bool = False
    workers: int = 4
    timeout_s: int = 120


@dataclass(frozen=True)
class Paths:
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    manifest_dir: Path
    figures_dir: Path
    tables_dir: Path


@dataclass(frozen=True)
class ModelingConfig:
    """Settings for the step 8 incremental value test. Every random draw derives from seed."""

    seed: int = 20261006
    n_folds: int = 10
    n_reps: int = 10
    n_boot: int = 2000
    primary_chain: str = "strict_open"
    primary_scope: str = "open_play"
    min_seq_len_grid: tuple[int, ...] = (1, 3, 5)


@dataclass(frozen=True)
class Config:
    """``statsbomb`` is None in a config that only describes the hockey source, and
    ``stathletes`` is None in the soccer config. ``source`` says which one is active."""

    source: str
    statsbomb: StatsBombConfig | None
    paths: Paths
    modeling: ModelingConfig = ModelingConfig()
    stathletes: StathletesConfig | None = None


def load_config(path: Path | None = None) -> Config:
    """Read the YAML config and resolve all directories against the repo root.

    The file is ``path`` if given, else the ``POSSNET_CONFIG`` environment variable (a path
    relative to the repo root, used for the synthetic sample), else config/project.yaml.
    """
    env = os.environ.get("POSSNET_CONFIG")
    chosen = path or (repo_path(env) if env else CONFIG_PATH)
    raw: dict[str, Any] = yaml.safe_load(chosen.read_text())
    sb = StatsBombConfig(**raw["statsbomb"]) if "statsbomb" in raw else None
    sa = StathletesConfig(**raw["stathletes"]) if "stathletes" in raw else None
    paths = Paths(**{k: repo_path(v) for k, v in raw["paths"].items()})
    mod = dict(raw.get("modeling", {}))
    if "min_seq_len_grid" in mod:
        mod["min_seq_len_grid"] = tuple(mod["min_seq_len_grid"])
    return Config(source=raw["source"], statsbomb=sb, paths=paths,
                  modeling=ModelingConfig(**mod), stathletes=sa)
