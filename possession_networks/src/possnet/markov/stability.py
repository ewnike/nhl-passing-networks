"""Stability and cross configuration comparison for the Markov chain and player values."""

from __future__ import annotations

import numpy as np
import pandas as pd

from possnet.markov.chain import ChainSpec, fit_chain
from possnet.markov.value import player_match_values, player_season_values, value_actions
from possnet.markov.zones import ZoneGrid


def split_halves(match_ids: np.ndarray, seed: int = 0) -> tuple[set, set]:
    """Random split of matches into two halves (seeded)."""
    rng = np.random.default_rng(seed)
    ids = np.array(sorted(match_ids))
    rng.shuffle(ids)
    cut = len(ids) // 2
    return set(ids[:cut]), set(ids[cut:])


def split_half_stability(actions: pd.DataFrame, appearances: pd.DataFrame, grid: ZoneGrid,
                         spec: ChainSpec, full_zone_table: pd.DataFrame,
                         min_minutes: float = 450.0, seed: int = 0) -> dict:
    """Correlate zone values and player per 90 values between two random halves of matches.

    Zone values refit the chain on each half. Player values hold the full season chain fixed,
    so they measure how reliably a player's action mix is measured, not chain noise.
    """
    a_ids, b_ids = split_halves(actions["match_id"].unique(), seed)
    halves = []
    for ids in (a_ids, b_ids):
        sub = actions[actions["match_id"].isin(ids)]
        halves.append((sub, fit_chain(sub, grid, spec),
                       appearances[appearances["match_id"].isin(ids)]))
    zone_rows = {}
    for name, col in (("goal", "p_goal"), ("attempt", "p_attempt")):
        zone_rows[f"zone_{name}_spearman"] = float(
            halves[0][1][col].corr(halves[1][1][col], method="spearman"))
    players = []
    for sub, _, app in halves:
        acts = value_actions(sub, grid, full_zone_table)
        players.append(player_season_values(player_match_values(acts), app,
                                            min_minutes=min_minutes / 2).set_index("player_id"))
    both = players[0].join(players[1], lsuffix="_a", rsuffix="_b", how="inner")
    out = {"config": spec.name, **zone_rows, "players_compared": len(both)}
    for name in ("goal", "attempt"):
        out[f"player_xt_{name}_per90_spearman"] = float(
            both[f"xt_{name}_per90_a"].corr(both[f"xt_{name}_per90_b"], method="spearman"))
    return out


def compare_configs(zone_tables: dict[str, pd.DataFrame],
                    player_tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pairwise Spearman correlations of zone and player values across configurations."""
    rows = []
    names = list(zone_tables)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            row = {"config_a": a, "config_b": b}
            for col in ("p_goal", "p_attempt"):
                row[f"zone_{col}_spearman"] = float(
                    zone_tables[a][col].corr(zone_tables[b][col], method="spearman"))
            pa = player_tables[a].set_index("player_id")
            pb = player_tables[b].set_index("player_id")
            for name in ("goal", "attempt"):
                col = f"xt_{name}_per90"
                row[f"player_{col}_spearman"] = float(
                    pa[col].corr(pb[col].reindex(pa.index), method="spearman"))
            rows.append(row)
    return pd.DataFrame(rows)
