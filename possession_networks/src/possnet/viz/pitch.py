"""Pitch drawing and figure helpers in canonical coordinates (meters, center origin)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Rectangle

from possnet.paths import repo_path

YD = 0.9144
HALF_L = 60 * YD
HALF_W = 40 * YD

INK = "#1f2937"
MUTED = "#6b7280"
GRID = "#e5e7eb"
ACCENT = "#2a6fdb"

LOGO_PATH = repo_path("docs/assets/statsbomb_logo.png")
CREDIT_TEXT = "Data: StatsBomb open data"


def draw_pitch(ax: Axes, line_color: str = MUTED, lw: float = 1.0) -> Axes:
    """Draw a pitch with the attacking direction left to right (+x)."""
    kw = {"edgecolor": line_color, "facecolor": "none", "linewidth": lw}
    ax.add_patch(Rectangle((-HALF_L, -HALF_W), 2 * HALF_L, 2 * HALF_W, **kw))
    ax.plot([0, 0], [-HALF_W, HALF_W], color=line_color, lw=lw)
    ax.add_patch(Arc((0, 0), 20 * YD, 20 * YD, theta1=0, theta2=360, color=line_color, lw=lw))
    for sign in (-1, 1):
        # 18 yard penalty area (44 yards wide) and 6 yard box (20 yards wide)
        ax.add_patch(Rectangle((sign * HALF_L - (18 * YD if sign > 0 else 0), -22 * YD),
                               18 * YD, 44 * YD, **kw))
        ax.add_patch(Rectangle((sign * HALF_L - (6 * YD if sign > 0 else 0), -10 * YD),
                               6 * YD, 20 * YD, **kw))
    ax.set_xlim(-HALF_L - 2, HALF_L + 2)
    ax.set_ylim(-HALF_W - 2, HALF_W + 2)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def style_axes(ax: Axes) -> Axes:
    """Recessive axes: no top or right spines, light grid on the value axis."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return ax


def add_attribution(fig: Figure) -> None:
    """StatsBomb's terms require their logo on published analysis.

    If docs/assets/statsbomb_logo.png exists (download it from the StatsBomb media
    pack, which this repo does not redistribute) it is placed bottom right; otherwise
    a text credit is used so draft figures are never unattributed.
    """
    if LOGO_PATH.exists():
        logo = plt.imread(LOGO_PATH)
        axl = fig.add_axes([0.86, 0.005, 0.12, 0.07], anchor="SE")
        axl.imshow(logo)
        axl.axis("off")
    else:
        fig.text(0.99, 0.01, CREDIT_TEXT, ha="right", va="bottom", fontsize=8, color=MUTED)


def save_figure(fig: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
