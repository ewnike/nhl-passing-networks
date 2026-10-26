"""Experiment definitions for the step 8 incremental value test."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from possnet.config import ModelingConfig
from possnet.incremental.cv import (
    Model,
    make_splits,
    oof_errors,
    paired_bootstrap,
    r2_from_errors,
)
from possnet.incremental.data import (
    NET_STRUCT,
    VOLUME,
    XtData,
    build_model_table,
    build_xt_data,
    team_rows,
)
from possnet.markov.chain import ChainSpec
from possnet.markov.zones import ZoneGrid
from possnet.network.pipeline import compute_scope

BASELINES = {
    "corsi": ("shots",),
    "corsi_sot": ("shots", "sot"),
    "corsi_xg": ("shots", "xg"),
    "corsi_vol": ("shots", VOLUME),
}
TARGETS = ("gd", "xgd")
VARIANTS = ("net", "xt", "both")
CHAINS = {ChainSpec(s, o).name: ChainSpec(s, o) for s in ("strict", "broad")
          for o in (True, False)}


@dataclass
class Setting:
    """One cell of the sensitivity grid. Defaults are the primary analysis."""

    axis: str = "primary"
    value: str = "primary"
    scope: str = "open_play"
    full_strength_only: bool = False
    min_seq_len: int = 1
    chain: str = "strict_open"
    window: str = "full"          # key of WINDOWS: which events feed features and the target
    cv: str = "group"
    half: int | None = None       # restrict to the first (0) or second (1) half of the season
    leaky_xt: bool = False


WINDOWS = {            # name -> (feature selector, target selector); None means the whole match
    "full": (None, None),
    "h1_to_h1": (1, 1),          # selectors that are ints mean a period
    "h2_to_h2": (2, 2),
    "h1_to_h2": (1, 2),
    "tied_to_full": ("tied", None),   # features only from events while the score is level
}


def tied_mask(events: pd.DataFrame, matches: pd.DataFrame) -> pd.Series:
    """True for events that happen while the score is level (state before the event)."""
    ev = events[["match_id", "event_index", "team_id", "event_type", "outcome",
                 "event_subtype"]].copy()
    ev["period_order"] = np.arange(len(ev))
    ev = ev.sort_values(["match_id", "event_index"])
    scored = (((ev["event_type"] == "shot") & (ev["outcome"].astype(object) == "goal"))
              | (ev["event_subtype"].astype(object) == "Own Goal For"))
    home = ev["match_id"].map(dict(zip(matches["match_id"], matches["home_team_id"],
                                       strict=True)))
    sign = np.where(ev["team_id"] == home, 1, -1) * scored.to_numpy()
    ev["sign"] = sign
    cum = ev.groupby("match_id")["sign"].cumsum() - ev["sign"]     # before this event
    level = (cum == 0).sort_index()
    return level.reindex(events.index)


def select_events(frame: pd.DataFrame, selector, tied: pd.Series | None) -> pd.DataFrame | None:
    if selector is None:
        return None
    if selector == "tied":
        return frame[tied.loc[frame.index].to_numpy()]
    return frame[frame["period"] == selector]


@dataclass
class Context:
    cfg: ModelingConfig
    matches: pd.DataFrame
    events: pd.DataFrame
    appearances: pd.DataFrame
    network_team: pd.DataFrame
    network_player: pd.DataFrame
    actions: pd.DataFrame
    grid: ZoneGrid
    _tied: pd.Series | None = None
    _tables: dict = field(default_factory=dict)
    _rows: dict = field(default_factory=dict)
    _xt: dict = field(default_factory=dict)

    def table(self, window: str, scope: str) -> pd.DataFrame:
        """Differenced model table for a window and pass scope (built on first use)."""
        key = (window, scope)
        if key not in self._tables:
            fsel, tsel = WINDOWS[window]
            ev_f = self.select(self.events, fsel)
            ev_t = self.select(self.events, tsel)
            if ev_f is None:
                team, player = self.network_team, self.network_player
            else:
                player, team, _ = compute_scope(ev_f, self.appearances, scope)
            rows = team_rows(self.matches, self.events, self.appearances, team, player, scope,
                             ev_f, ev_t)
            self._rows[key] = rows
            self._tables[key] = build_model_table(rows)
        return self._tables[key]

    def select(self, frame: pd.DataFrame, selector):
        """Subset of events or ball actions picked by a window selector (None keeps all)."""
        if selector == "tied" and self._tied is None:
            self._tied = tied_mask(self.events, self.matches)
        if selector == "tied" and "event_index" in frame and frame is not self.events:
            keys = pd.MultiIndex.from_arrays([self.events["match_id"],
                                              self.events["event_index"]])
            flag = pd.Series(self._tied.to_numpy(), index=keys)
            flag = flag[~flag.index.duplicated()]
            ok = flag.reindex(pd.MultiIndex.from_arrays(
                [frame["match_id"], frame["event_index"]])).fillna(False).to_numpy()
            return frame[ok.astype(bool)]
        return select_events(frame, selector, self._tied)

    @property
    def rows(self) -> pd.DataFrame:
        """Row index (match order and team ids), identical for every window and scope."""
        self.table("full", "open_play")
        return self._rows[("full", "open_play")]

    def xt(self, chain: str, min_len: int, leaky: bool, window: str = "full") -> XtData:
        key = (chain, min_len, window)
        if key not in self._xt:
            fsel = WINDOWS[window][0]
            fa = None if fsel is None else self.select(self.actions, fsel)
            self._xt[key] = build_xt_data(self.actions, self.rows, CHAINS[chain], self.grid,
                                          min_len, fa)
        data = self._xt[key]
        return replace(data, fit_on_all=True) if leaky else data


def make_context(cfg: ModelingConfig, matches, events, appearances, network_team,
                 network_player, actions, grid: ZoneGrid) -> Context:
    return Context(cfg, matches, events, appearances, network_team, network_player, actions,
                   grid)


def build_models(target: str, chain_key: str) -> list[Model]:
    models = [Model("home_only", ())]
    for name, cols in BASELINES.items():
        if target == "xgd" and "xg" in cols:
            continue          # xG is the target itself, so it cannot be a feature
        net = NET_STRUCT + (() if VOLUME in cols else (VOLUME,))
        models += [Model(name, cols), Model(f"{name}+net", cols + net),
                   Model(f"{name}+xt", cols, chain_key),
                   Model(f"{name}+both", cols + net, chain_key)]
    full_net = (VOLUME, *NET_STRUCT)
    models += [Model("net_only", full_net), Model("xt_only", (), chain_key),
               Model("net_xt_only", full_net, chain_key)]
    return models


def run_setting(ctx: Context, s: Setting) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (comparisons, model_scores) for one setting, over both targets."""
    cfg = ctx.cfg
    table = ctx.table(s.window, s.scope)
    home = table.iloc[::2]
    keep = np.ones(len(home), bool)
    if s.full_strength_only:
        keep &= home["full_strength"].to_numpy()
    kept = np.flatnonzero(keep)                  # match positions, already in date order
    if s.half is not None:
        kept = np.array_split(kept, 2)[s.half]
    splits = make_splits(s.cv, kept, cfg.seed, cfg.n_folds, cfg.n_reps)
    xt = {"chain": ctx.xt(s.chain, s.min_seq_len, s.leaky_xt, s.window)}

    comparisons, scores = [], []
    for target in TARGETS:
        y = home[target].to_numpy(float)
        models = [Model(m.name, m.fixed, "chain" if m.xt else None)
                  for m in build_models(target, s.chain)]
        errs = oof_errors(table, target, models, xt, splits)
        for m in models:
            scores.append({"axis": s.axis, "value": s.value, "target": target,
                           "model": m.name, "r2": r2_from_errors(errs[m.name], y),
                           "rmse": float(np.sqrt(np.nanmean(errs[m.name]))),
                           "n_matches": len(kept)})
        for base in BASELINES:
            if base + "+net" not in errs:
                continue
            for var in VARIANTS:
                res = paired_bootstrap(errs[base], errs[f"{base}+{var}"], y, cfg.seed + 1,
                                       cfg.n_boot)
                comparisons.append({"axis": s.axis, "value": s.value, "target": target,
                                    "baseline": base, "added": var,
                                    "r2_base": r2_from_errors(errs[base], y),
                                    "r2_new": r2_from_errors(errs[f"{base}+{var}"], y),
                                    **res, "n_matches": len(kept)})
    return pd.DataFrame(comparisons), pd.DataFrame(scores)


def sensitivity_grid(cfg: ModelingConfig) -> list[Setting]:
    """Primary analysis plus one at a time changes. Chosen before seeing any results."""
    grid = [Setting()]
    grid += [Setting("cv", cv, cv=cv) for cv in ("date_blocks", "cross_half")]
    grid += [Setting("cv", f"within_half_{h + 1}", half=h) for h in (0, 1)]
    grid += [Setting("scope", "all_passes", scope="all")]
    grid += [Setting("minutes", "full_strength_only", full_strength_only=True)]
    grid += [Setting("min_seq_len", str(k), min_seq_len=k) for k in cfg.min_seq_len_grid
             if k != 1]
    grid += [Setting("chain", name, chain=name) for name in CHAINS if name != cfg.primary_chain]
    grid += [Setting("window", w, window=w)
             for w in ("h1_to_h1", "h2_to_h2", "h1_to_h2", "tied_to_full")]
    grid += [Setting("leakage", "xT fit on all matches (leaky)", leaky_xt=True)]
    for g in grid:
        if g.axis != "chain" and g.chain == "strict_open":
            g.chain = cfg.primary_chain
        if g.scope == "open_play" and g.axis != "scope":
            g.scope = cfg.primary_scope
    return grid
