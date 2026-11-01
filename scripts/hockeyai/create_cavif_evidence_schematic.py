#!/usr/bin/env python3
"""Generate Figure 6D4-1 from documented experimental findings.

Run from the nhl-passing-networks repository root:
    python scripts/hockeyai/create_cavif_evidence_schematic.py

Requires matplotlib. Does not read or modify experiment artifacts.
Refuses to overwrite an existing figure.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUTPUT = Path(
    "docs/hockeyai/experiments/figures/experiment_06d4_evidence_to_proposition.png"
)

INK = "#17283a"
MUTED = "#526478"
BLUE = "#dceaf5"  # measured evidence
AMBER = "#fff0d2"  # human-review candidates
GREEN = "#dcefe7"  # proposed framework
BORDER = "#8193a4"


# def box(ax, x, y, w, h, heading, body, fill, fontsize=9):
#     ax.add_patch(
#         FancyBboxPatch(
#             (x, y),
#             w,
#             h,
#             boxstyle="round,pad=0.012,rounding_size=0.016",
#             linewidth=1.2,
#             edgecolor=BORDER,
#             facecolor=fill,
#         )
#     )
#     ax.text(
#         x + 0.018,
#         y + h - min(0.065, h * 0.45),
#         body,
#         va="top",
#         ha="left",
#         fontsize=fontsize,
#         linespacing=1.4,
#         color=INK,
#     )
#     ax.text(
#         x + 0.018,
#         y + h - 0.082,
#         body,
#         va="top",
#         ha="left",
#         fontsize=fontsize,
#         linespacing=1.4,
#         color=INK,
#     )


def box(ax, x, y, w, h, heading, body, fill, fontsize=9):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.016",
            linewidth=1.2,
            edgecolor=BORDER,
            facecolor=fill,
        )
    )

    # Heading — positioned near the top of the box
    ax.text(
        x + 0.018,
        y + h - 0.020,
        heading,
        va="top",
        ha="left",
        fontsize=fontsize + 1,
        fontweight="bold",
        color=INK,
    )

    # Explanation — positioned below the heading
    ax.text(
        x + 0.018,
        y + h - min(0.065, h * 0.65),
        body,
        va="top",
        ha="left",
        fontsize=fontsize,
        linespacing=1.4,
        color=INK,
    )


def arrow(ax, start, end):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.6,
            color=MUTED,
            connectionstyle="arc3,rad=0",
        )
    )


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing figure: {OUTPUT}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 11), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.04, 0.965, "FIGURE 6D4-1  |  CAVIF", fontsize=19, weight="bold", color=INK
    )
    ax.text(
        0.04,
        0.932,
        "Experimental evidence → proposed validation architecture → passing-event objective",
        fontsize=12,
        color=MUTED,
    )
    ax.text(
        0.04, 0.895, "EVIDENCE FROM EXPERIMENTS", fontsize=12, weight="bold", color=INK
    )

    box(
        ax,
        0.04,
        0.715,
        0.285,
        0.155,
        "06D2 vs 06D3 — measured",
        "750 frames; +13 observations at cuts\n6,482 matched boxes off cut frames\nMean matched IoU = 0.999909",
        BLUE,
    )
    box(
        ax,
        0.357,
        0.715,
        0.285,
        0.155,
        "06D4 — measured",
        "C:10 / C:142 overlap:\nIoU = 0.914 at frame 0579\nClass labels vary within tracks",
        BLUE,
    )
    box(
        ax,
        0.674,
        0.715,
        0.285,
        0.155,
        "06D4 — review candidates",
        "C:138: suspected off-ice detection\nFrame 0371: possible missed skaters\nBoth require ground-truth review",
        AMBER,
    )

    ax.text(
        0.04,
        0.678,
        "PROPOSED CAVIF COMPONENTS  (not yet validated)",
        fontsize=12,
        weight="bold",
        color=INK,
    )
    for x in (0.182, 0.5, 0.817):
        arrow(ax, (x, 0.713), (x, 0.656))

    box(
        ax,
        0.04,
        0.482,
        0.285,
        0.163,
        "Geometric plausibility",
        "Rink boundary and ice-plane checks\nCalibration uncertainty separately\nFlag suspicious locations",
        GREEN,
    )
    box(
        ax,
        0.357,
        0.482,
        0.285,
        0.163,
        "Temporal consistency",
        "Occlusion and track fragmentation\nCamera-cut handling\nPhysical identity reconciliation",
        GREEN,
    )
    box(
        ax,
        0.674,
        0.482,
        0.285,
        0.163,
        "Hockey context",
        "Verified manpower and team cues\nShift and movement continuity\nOrientation is weak evidence",
        GREEN,
    )

    for x in (0.182, 0.5, 0.817):
        arrow(ax, (x, 0.478), (0.5, 0.422))

    box(
        ax,
        0.21,
        0.305,
        0.58,
        0.106,
        "Evidence fusion + uncertainty moderation — proposed",
        "Rank candidate observations; preserve unknown states; flag for human review",
        GREEN,
        10,
    )
    arrow(ax, (0.5, 0.303), (0.5, 0.268))
    box(
        ax,
        0.21,
        0.172,
        0.58,
        0.087,
        "Probabilistic temporal inference — future work",
        "Candidate Markovian model; probabilities require calibration and testing",
        GREEN,
        10,
    )
    arrow(ax, (0.5, 0.17), (0.5, 0.134))
    box(
        ax,
        0.21,
        0.055,
        0.58,
        0.082,
        "Intended downstream outcome — not yet demonstrated",
        "Verified player identities → puck possession → passing events → networks",
        GREEN,
        10,
    )
    ax.text(
        0.04,
        0.008,
        "Blue = measured  |  Amber = human-review candidate  |  Green = proposed/future  •  No CAVIF accuracy claim",
        fontsize=9,
        color=MUTED,
    )
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"Saved: {OUTPUT}")
    print("Original experimental data unchanged.")


if __name__ == "__main__":
    main()
