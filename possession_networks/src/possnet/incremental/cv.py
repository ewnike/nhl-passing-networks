"""Grouped cross validation, fold safe xT features, and paired bootstrap comparisons.

Each match enters model fitting once, from the home perspective, because the away row is its
exact mirror (features and target change sign). Predictions for the away row are the negative
of the home prediction. Both team rows therefore always sit in the same fold by construction,
and the inner ridge penalty search (leave one out over matches) cannot see a mirror twin.
Scores use the uncentered ``R2 = 1 - SSE / sum(y^2)`` over matches, which equals the R2 of the
mirrored two row data (whose target mean is zero by construction).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from possnet.incremental.data import XtData

ALPHAS = tuple(np.logspace(-2, 3, 11))
CLIP_SD = 5.0     # standardized features are clipped so a tiny network cannot dominate a fit


def _clip(x: np.ndarray) -> np.ndarray:
    return np.clip(x, -CLIP_SD, CLIP_SD)


@dataclass(frozen=True)
class Model:
    name: str
    fixed: tuple[str, ...]
    xt: str | None = None     # key into the dict of XtData, or None


def make_splits(kind: str, kept: np.ndarray, seed: int, n_folds: int = 10, n_reps: int = 10
                ) -> list[list[tuple[np.ndarray, np.ndarray]]]:
    """Repetitions of (train_matches, test_matches) pairs. ``kept`` is sorted by date.

    * ``group``: shuffled K fold over matches, repeated ``n_reps`` times with derived seeds
    * ``date_blocks``: contiguous date blocks, one block held out at a time (stricter)
    * ``cross_half``: train on one half of the season, test on the other, both directions
    """
    if kind == "group":
        reps = []
        for r in range(n_reps):
            perm = np.random.default_rng([seed, r]).permutation(kept)
            reps.append([(np.setdiff1d(kept, f), f) for f in np.array_split(perm, n_folds)])
        return reps
    if kind == "date_blocks":
        blocks = np.array_split(kept, n_folds)
        return [[(np.setdiff1d(kept, b), b) for b in blocks]]
    if kind == "cross_half":
        a, b = np.array_split(kept, 2)
        return [[(a, b), (b, a)]]
    raise ValueError(kind)


def _fit_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> np.ndarray:
    model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          FunctionTransformer(_clip),
                          RidgeCV(alphas=ALPHAS, fit_intercept=True))
    return model.fit(x_train, y_train).predict(x_test)


def oof_errors(table: pd.DataFrame, target: str, models: list[Model],
               xt: dict[str, XtData], splits: list[list[tuple[np.ndarray, np.ndarray]]]
               ) -> dict[str, np.ndarray]:
    """Squared error per match per repetition, shape (n_reps, n_matches_all), NaN if unused.

    ``table`` rows follow the 2m, 2m+1 layout; home rows (even) carry the model fit.
    """
    home = table.iloc[::2]
    y = home[target].to_numpy(float)
    n_matches = len(home)
    out = {m.name: np.full((len(splits), n_matches), np.nan) for m in models}
    for r, folds in enumerate(splits):
        for train, test in folds:
            xt_feats = {key: data.features(train) for key, data in xt.items()}
            for m in models:
                cols = [home[list(m.fixed)].to_numpy(float)] if m.fixed else []
                if m.xt:
                    cols.append(xt_feats[m.xt][::2])
                x = np.column_stack(cols) if cols else np.zeros((n_matches, 0))
                if x.shape[1] == 0:
                    pred = np.full(len(test), y[train].mean())
                else:
                    pred = _fit_predict(x[train], y[train], x[test])
                out[m.name][r, test] = (y[test] - pred) ** 2
    return out


def r2_from_errors(err: np.ndarray, y: np.ndarray) -> float:
    """Uncentered R2 using per match errors averaged over repetitions."""
    per_match = np.nanmean(err, axis=0)
    ok = ~np.isnan(per_match)
    return float(1.0 - per_match[ok].sum() / (y[ok] ** 2).sum())


def paired_bootstrap(err_base: np.ndarray, err_new: np.ndarray, y: np.ndarray, seed: int,
                     n_boot: int = 2000) -> dict[str, float]:
    """Delta R2 (new minus base) with a percentile interval from resampling matches.

    Squared errors are averaged over repetitions first, so each match counts once. A positive
    delta means the new model predicts held out matches better.
    """
    b, n = np.nanmean(err_base, axis=0), np.nanmean(err_new, axis=0)
    ok = ~np.isnan(b)
    b, n, y2 = b[ok], n[ok], y[ok] ** 2
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(b), size=(n_boot, len(b)))
    delta = ((b[idx] - n[idx]).sum(axis=1)) / y2[idx].sum(axis=1)
    point = float((b - n).sum() / y2.sum())
    lo, hi = np.percentile(delta, [2.5, 97.5])
    return {"delta_r2": point, "ci_low": float(lo), "ci_high": float(hi),
            "p_not_better": float((delta <= 0).mean())}
