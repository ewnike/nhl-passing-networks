"""End to end run on a tiny synthetic league: generate, adapt, validate, build, fit."""

from __future__ import annotations

import numpy as np
import pytest

from possnet.adapters.statsbomb import build_canonical
from possnet.markov.chain import ChainSpec, fit_chain
from possnet.markov.value import player_match_values, player_season_values, value_actions
from possnet.markov.zones import ZoneGrid
from possnet.network.pipeline import aggregate_player_season, compute_all
from possnet.possession.checks import validate_possessions
from possnet.possession.sequences import ball_actions, build_possessions
from possnet.sources.synthetic import generate
from possnet.validate.checks import validate_tables


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    root = tmp_path_factory.mktemp("sample")
    manifest = generate(root / "raw", seed=3, n_teams=6)
    return build_canonical(manifest, root)


def test_sample_generation_is_deterministic(tmp_path):
    a = generate(tmp_path / "a", seed=5, n_teams=3)
    b = generate(tmp_path / "b", seed=5, n_teams=3)
    assert [f["sha256"] for f in a["files"]] == [f["sha256"] for f in b["files"]]


def test_sample_passes_every_validation_check(sample):
    report = validate_tables(sample["matches"], sample["events"], sample["appearances"])
    assert report.ok, report.to_frame().query("not passed and severity == 'error'")


def test_sample_networks_possessions_and_chain(sample):
    ev, app = sample["events"], sample["appearances"]
    player_match, team_match, _ = compute_all(ev, app)
    assert len(aggregate_player_season(player_match)) > 0 and len(team_match) > 0

    poss = build_possessions(ev)
    assert validate_possessions(poss, ev, sample["matches"]).ok

    acts = ball_actions(ev, poss)
    grid = ZoneGrid(6, 4)
    zones = fit_chain(acts, grid, ChainSpec("broad", False))
    assert zones[["p_goal", "p_shot", "p_turnover"]].sum(axis=1).between(0.99, 1.01).all()
    centers = zones.assign(col=np.floor((zones["x"] + 54.9) / 18.3))
    by_col = centers.groupby("col")["p_attempt"].mean()
    assert by_col.iloc[-1] > by_col.iloc[0]          # value rises toward the attacked goal
    values = value_actions(acts, grid, zones)
    season = player_season_values(player_match_values(values), app)
    assert season["xt_goal_per90"].notna().all()
