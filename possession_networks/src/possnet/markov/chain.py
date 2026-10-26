"""Absorbing Markov chain over pitch zones.

States: ``n_zones`` transient zones, then three absorbing states ``goal``, ``shot`` (a shot
that did not score), and ``turnover``. Each sequence contributes a path through the zones
where the ball actions start, ending in an absorbing state:

* the path is cut at the first shot, which ends it as ``goal`` or ``shot``;
* a sequence with no shot ends in ``goal`` (own goal), ``turnover``, or is censored, as
  labeled by the chosen scheme. Censored sequences keep their zone to zone moves but add
  no terminal transition, so unknown endings do not bias the chain toward any outcome.

Absorption probabilities solve ``(I - Q) B = R`` where ``Q`` holds transient to transient
move probabilities and ``R`` transient to absorbing. ``B[z, goal]`` is the expected threat
of zone ``z``: the probability that possession from ``z`` ends in a goal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from possnet.markov.zones import ZoneGrid

ABSORBING = ("goal", "shot", "turnover")
SEQ_KEYS = ["match_id", "possession_id", "segment"]


@dataclass(frozen=True)
class ChainSpec:
    scheme: str          # "strict" or "broad"
    open_play_only: bool  # drop sequences that start from a dead ball restart

    @property
    def name(self) -> str:
        return f"{self.scheme}_{'open' if self.open_play_only else 'all'}"


def build_transitions(actions: pd.DataFrame, grid: ZoneGrid, spec: ChainSpec) -> pd.DataFrame:
    """Transition list (``src`` zone, ``dst`` state index) from ball actions."""
    acts = actions
    if spec.open_play_only:
        acts = acts[~acts["starts_dead_ball"]]
    acts = acts[SEQ_KEYS + ["event_type", "outcome", "x_start", "y_start",
                            "outcome_strict", "outcome_broad"]].copy()
    for col in ("event_type", "outcome", "outcome_strict", "outcome_broad"):
        acts[col] = acts[col].astype(object)
    for col in ("x_start", "y_start"):
        acts[col] = acts[col].astype(float)
    acts["zone"] = grid.zone_of(acts["x_start"], acts["y_start"])
    acts["is_shot"] = (acts["event_type"] == "shot").astype(int)
    acts = acts[acts["zone"] >= 0]
    g = acts.groupby(SEQ_KEYS, sort=False)
    # keep actions up to and including the first shot
    prior_shots = g["is_shot"].cumsum() - acts["is_shot"]
    acts = acts[prior_shots == 0]
    g = acts.groupby(SEQ_KEYS, sort=False)
    nxt_zone = g["zone"].shift(-1)

    n = grid.n_zones
    move = nxt_zone.notna()
    moves = pd.DataFrame({"src": acts.loc[move, "zone"].to_numpy(),
                          "dst": nxt_zone[move].astype(int).to_numpy()})

    last = acts[~move]
    label = last[f"outcome_{spec.scheme}"]
    dst = np.select(
        [(last["is_shot"] == 1) & (last["outcome"] == "goal"), last["is_shot"] == 1,
         label == "goal", label == "turnover"],
        [n, n + 1, n, n + 2], default=-1)
    ends = pd.DataFrame({"src": last["zone"].to_numpy(), "dst": dst})
    ends = ends[ends["dst"] >= 0]
    return pd.concat([moves, ends], ignore_index=True)


def count_matrix(transitions: pd.DataFrame, n_zones: int) -> np.ndarray:
    """(n_zones, n_zones + 3) transition counts."""
    width = n_zones + len(ABSORBING)
    flat = transitions["src"].to_numpy() * width + transitions["dst"].to_numpy()
    return np.bincount(flat, minlength=n_zones * width).reshape(n_zones, width).astype(float)


def absorption(counts: np.ndarray) -> np.ndarray:
    """Absorption probabilities (n_zones, 3) for goal, shot, turnover from a count matrix."""
    n = counts.shape[0]
    totals = counts.sum(axis=1, keepdims=True)
    probs = np.divide(counts, totals, out=np.zeros_like(counts), where=totals > 0)
    q, r = probs[:, :n], probs[:, n:]
    a = np.eye(n) - q
    try:
        return np.linalg.solve(a, r)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(a, r, rcond=None)[0]


def fit_chain(actions: pd.DataFrame, grid: ZoneGrid, spec: ChainSpec) -> pd.DataFrame:
    """Per zone table: visits, absorption probabilities, and the share of visits that move."""
    counts = count_matrix(build_transitions(actions, grid, spec), grid.n_zones)
    b = absorption(counts)
    centers = grid.centers()
    table = pd.DataFrame({
        "config": spec.name, "zone": np.arange(grid.n_zones),
        "x": centers[:, 0], "y": centers[:, 1],
        "visits": counts.sum(axis=1),
        "p_goal": b[:, 0], "p_shot": b[:, 1], "p_turnover": b[:, 2],
    })
    table["p_attempt"] = table["p_goal"] + table["p_shot"]
    return table
