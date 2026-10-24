#!/usr/bin/env python3

"""
Experiment 04 — Stage 3

Visual comparison of frame-0011 homographies.

Green: Strategy A (fixed landmark subset)
Magenta: Strategy B (expanded landmark subset)

Uses saved Experiment 04 matrices.
No model inference.
"""

import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

RESULTS = BASE / "homography_experiment_04/stage_2" / "temporal_homographies.json"

FRAME = BASE / "frames/P1_pilot/frame_0011.jpg"

OUTPUT_DIR = BASE / "homography_experiment_04/stage_3"

COLORS = {
    "A_fixed": (0, 255, 0),
    "B_all": (255, 0, 255),
}


def project(points, H):
    points = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(points, H).reshape(-1, 2)


def draw_geometry(image, H, color):

    # Western blue, center red, eastern blue.
    for x in (-7.65, 0.0, 7.65):
        points = np.array(
            [
                [x, -15.0],
                [x, 15.0],
            ]
        )

        projected = project(points, H)

        if not np.isfinite(projected).all():
            continue

        p1, p2 = np.round(projected).astype(np.int32)

        cv2.line(
            image,
            tuple(p1),
            tuple(p2),
            color,
            2,
            cv2.LINE_AA,
        )

    # Center faceoff circle.
    theta = np.linspace(0, 2 * np.pi, 181)

    circle = np.column_stack(
        [
            4.5 * np.cos(theta),
            4.5 * np.sin(theta),
        ]
    )

    projected = project(circle, H)

    if np.isfinite(projected).all():
        cv2.polylines(
            image,
            [np.round(projected).astype(np.int32)],
            True,
            color,
            2,
            cv2.LINE_AA,
        )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS.open() as f:
        results = json.load(f)

    image = cv2.imread(str(FRAME))

    if image is None:
        raise RuntimeError(f"Cannot load frame: {FRAME}")

    selected = {
        r["strategy"]: np.asarray(
            r["H_rink_to_image"],
            dtype=np.float64,
        )
        for r in results
        if r["frame"] == "frame_0011.jpg"
    }

    for strategy in COLORS:
        if strategy not in selected:
            raise RuntimeError(f"Missing strategy: {strategy}")

    for strategy, H in selected.items():
        annotated = image.copy()

        draw_geometry(
            annotated,
            H,
            COLORS[strategy],
        )

        cv2.imwrite(
            str(OUTPUT_DIR / f"{strategy}_overlay.jpg"),
            annotated,
        )

    combined = image.copy()

    for strategy, H in selected.items():
        draw_geometry(
            combined,
            H,
            COLORS[strategy],
        )

    output = OUTPUT_DIR / "frame_0011_comparison.jpg"

    cv2.imwrite(str(output), combined)

    print(f"Created: {output}")


if __name__ == "__main__":
    main()
