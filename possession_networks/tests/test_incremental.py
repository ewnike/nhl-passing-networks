"""Step 8 tests: layout, leakage guards, splits, bootstrap, and the xT identity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from possnet.adapters.statsbomb import build_canonical
from possnet.config import ModelingConfig
from possnet.incremental.cv import Model, make_splits, oof_errors, paired_bootstrap
from possnet.incremental.data import build_xt_data
from possnet.incremental.experiments import (
    CHAINS,
    Setting,
    make_context,
    run_setting,
    sensitivity_grid,
    tied_mask,
)
from possnet.markov.chain import fit_chain
from possnet.markov.value import team_match_values, value_actions
from possnet.markov.zones import ZoneGrid
from possnet.network.pipeline import compute_all
from possnet.possession.sequences import ball_actions, build_possessions
from possnet.sources.synthetic import generate

GRID = ZoneGrid(6, 4)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    root = tmp_path_factory.mktemp("inc")
    tables = build_canonical(generate(root / "raw", seed=3, n_teams=6), root)
    ev, app, matches = tables["events"], tables["appearances"], tables["matches"]
    player, team, _ = compute_all(ev, app)
    actions = ball_actions(ev, build_possessions(ev))
    cfg = ModelingConfig(n_folds=5, n_reps=2, n_boot=100)
    return make_context(cfg, matches, ev, app, team, player, actions, GRID)


def test_rows_are_exact_mirrors_and_goals_reconcile(ctx):
    table = ctx.table("full", "open_play")
    opp = np.arange(len(table)) ^ 1
    for col in ("shots", "sot", "xg", "gd", "xgd", "is_home", "density"):
        a = table[col].to_numpy(float)
        assert np.allclose(a, -a[opp], equal_nan=True), col
    assert (table["is_home"].to_numpy()[::2] == 1).all()
    final = ctx.matches.sort_values(["match_date", "match_id"])
    assert (table["gd"].to_numpy()[::2] == (final["home_score"] - final["away_score"])).all()


def test_xt_coefficients_reproduce_step7_values(ctx):
    spec = CHAINS["strict_open"]
    zones = fit_chain(ctx.actions, GRID, spec)
    reference = team_match_values(value_actions(ctx.actions, GRID, zones))
    data = build_xt_data(ctx.actions, ctx.rows, spec, GRID)
    ours = data.coef @ zones["p_goal"].to_numpy()
    key = pd.MultiIndex.from_arrays([ctx.rows["match_id"], ctx.rows["team_id"]])
    ref = reference.set_index(["match_id", "team_id"])["xt_goal"].reindex(key).fillna(0.0)
    assert np.allclose(ours, ref.to_numpy())
    # counts summed over all matches equal the whole season chain
    assert np.allclose(data.zone_values(np.arange(len(data.counts)))[:, 0], zones["p_goal"])


def test_zone_values_ignore_test_matches(ctx):
    data = ctx.xt("strict_open", 1, False)
    n = len(data.counts)
    train, test = np.arange(0, n - 5), np.arange(n - 5, n)
    base = data.zone_values(train)
    data.counts[test] += 1000.0          # corrupt the held out matches
    try:
        assert np.array_equal(base, data.zone_values(train))
        leaky = ctx.xt("strict_open", 1, True)
        assert not np.allclose(leaky.zone_values(train), base)
    finally:
        data.counts[test] -= 1000.0


@pytest.mark.parametrize("kind", ["group", "date_blocks", "cross_half"])
def test_splits_partition_matches_without_overlap(kind):
    kept = np.arange(40)
    for rep in make_splits(kind, kept, seed=1, n_folds=5, n_reps=3):
        tests = np.concatenate([t for _, t in rep])
        assert sorted(tests) == list(kept)
        for train, test in rep:
            assert not set(train) & set(test)


def test_date_blocks_are_contiguous_and_splits_are_seeded():
    kept = np.arange(40)
    (blocks,) = make_splits("date_blocks", kept, 1, 5)
    assert all(np.array_equal(t, np.arange(t[0], t[-1] + 1)) for _, t in blocks)
    a, b = make_splits("group", kept, 7, 5, 2), make_splits("group", kept, 7, 5, 2)
    assert all(np.array_equal(x[1], y[1]) for ra, rb in zip(a, b, strict=True)
               for x, y in zip(ra, rb, strict=True))


def test_noise_feature_does_not_help_and_signal_does():
    rng = np.random.default_rng(0)
    n = 300
    signal, noise = rng.normal(size=n), rng.normal(size=n)
    y = 1.5 * signal + rng.normal(size=n)
    home = pd.DataFrame({"signal": signal, "noise": noise, "y": y})
    table = home.loc[np.repeat(home.index, 2)].reset_index(drop=True)
    flip = np.tile([1.0, -1.0], n)
    for col in home:
        table[col] = table[col] * flip
    models = [Model("base", ("noise",)), Model("sig", ("noise", "signal")), Model("none", ())]
    splits = make_splits("group", np.arange(n), 3, 10, 3)
    err = oof_errors(table, "y", models, {}, splits)
    yy = home["y"].to_numpy()
    good = paired_bootstrap(err["base"], err["sig"], yy, 1, 500)
    assert good["ci_low"] > 0.2
    same = paired_bootstrap(err["base"], err["base"], yy, 1, 500)
    assert same["delta_r2"] == 0.0 and same["ci_low"] == 0.0 == same["ci_high"]


def test_tied_mask_flips_after_a_goal(ctx):
    mask = tied_mask(ctx.events, ctx.matches)
    ev = ctx.events.assign(tied=mask.to_numpy()).sort_values(["match_id", "event_index"])
    first = ev.groupby("match_id")["tied"].first()
    assert first.all()                                   # every match starts level
    scored = ev[(ev["event_type"] == "shot") & (ev["outcome"].astype(object) == "goal")]
    assert scored["tied"].any() or len(scored) == 0
    one = scored.groupby("match_id").head(1)
    after = ev.merge(one[["match_id", "event_index"]], on="match_id", suffixes=("", "_g"))
    after = after[after["event_index"] > after["event_index_g"]]
    # right after the first goal the score is not level unless an equalizer arrives
    assert (~after["tied"]).any()


def test_run_setting_and_grid_shape(ctx):
    comp, scores = run_setting(ctx, Setting())
    assert {"gd", "xgd"} == set(comp["target"])
    assert comp["ci_low"].le(comp["delta_r2"]).all() and comp["delta_r2"].le(
        comp["ci_high"]).all()
    assert not scores["model"].eq("corsi_xg").loc[scores["target"] == "xgd"].any()
    grid = sensitivity_grid(ModelingConfig())
    assert grid[0].axis == "primary" and len({(g.axis, g.value) for g in grid}) == len(grid)
