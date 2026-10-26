"""Draw a pass network on a pitch: nodes at average pass origin, edges by pass count."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch

from possnet.viz.pitch import ACCENT, INK, MUTED, draw_pitch

EDGE = "#94a3b8"


def average_positions(events: pd.DataFrame, match_id: str, team_id: str) -> pd.DataFrame:
    """Mean start location of each player's passes in one team match (canonical meters)."""
    passes = events[(events["match_id"] == match_id) & (events["team_id"] == team_id)
                    & (events["event_type"] == "pass") & ~events["is_dead_ball"]
                    & events["x_start"].notna()]
    return passes.groupby("player_id")[["x_start", "y_start"]].mean().rename(
        columns={"x_start": "x", "y_start": "y"})


def plot_pass_network(
    ax: Axes,
    edges: pd.DataFrame,
    positions: pd.DataFrame,
    node_size: pd.Series,
    labels: pd.Series,
    min_weight: int = 3,
    title: str | None = None,
) -> Axes:
    """``edges``: player_id, recipient_id, weight. ``node_size``: value per player_id."""
    draw_pitch(ax, line_color="#cbd5e1")
    shown = edges[edges["weight"] >= min_weight]
    wmax = float(shown["weight"].max()) if len(shown) else 1.0
    for r in shown.itertuples(index=False):
        if r.player_id not in positions.index or r.recipient_id not in positions.index:
            continue
        a, b = positions.loc[r.player_id], positions.loc[r.recipient_id]
        arrow = FancyArrowPatch(
            (a.x, a.y), (b.x, b.y), connectionstyle="arc3,rad=0.12", arrowstyle="-|>",
            mutation_scale=7, linewidth=0.6 + 4.0 * r.weight / wmax, color=EDGE,
            alpha=0.35 + 0.5 * r.weight / wmax, shrinkA=9, shrinkB=9, zorder=2)
        ax.add_patch(arrow)
    size = node_size.reindex(positions.index).fillna(0.0).to_numpy()
    scaled = 160 + 520 * size / max(size.max(), 1e-9)
    ax.scatter(positions["x"], positions["y"], s=scaled, color=ACCENT, edgecolor="white",
               linewidth=1.5, zorder=3)
    for pid, row in positions.iterrows():
        ax.text(row["x"], row["y"], str(labels.get(pid, "")), ha="center", va="center",
                color="white", fontsize=8, fontweight="bold", zorder=4)
    if title:
        ax.set_title(title, loc="left", color=INK, fontsize=11)
    return ax


def legend_note(ax: Axes, text: str) -> None:
    ax.text(0.0, -0.02, text, transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color=MUTED)


__all__ = ["average_positions", "plot_pass_network", "legend_note", "plt", "np"]
