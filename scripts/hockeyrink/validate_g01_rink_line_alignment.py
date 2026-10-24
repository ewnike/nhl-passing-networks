#!/usr/bin/env python3

"""
Experiment 04 — Stage 3B
Independent Painted Rink-Line Alignment Validation

Compares Strategy A and Strategy B homographies against
15 manually annotated painted-line center points.

No model inference.
No homography refitting.
No modification of previous experiment artifacts.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

STAGE_3 = BASE / "homography_experiment_04/stage_3"

ANNOTATIONS = STAGE_3 / "manual_validation/painted_line_points.csv"

HOMOGRAPHIES = BASE / "homography_experiment_04/stage_2" / "temporal_homographies.json"

OUTPUT_DIR = STAGE_3 / "manual_validation"

FRAME = "frame_0011.jpg"

LINE_COORDINATES = {
    "western_blue": -7.65,
    "center_red": 0.0,
    "eastern_blue": 7.65,
}


def project_line(H, rink_x):
    """Project two physical endpoints of a rink line."""

    rink_points = np.array(
        [
            [rink_x, -15.0],
            [rink_x, 15.0],
        ],
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    projected = cv2.perspectiveTransform(
        rink_points,
        H,
    ).reshape(-1, 2)

    return projected[0], projected[1]


def point_to_line_distance(point, a, b):
    """
    Perpendicular distance from image point to
    the infinite line passing through a and b.
    """

    point = np.asarray(point, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    direction = b - a

    length = np.linalg.norm(direction)

    if length < 1e-9:
        raise ValueError("Degenerate projected line.")

    # Two-dimensional cross-product magnitude.
    numerator = abs(direction[0] * (point[1] - a[1]) - direction[1] * (point[0] - a[0]))

    return float(numerator / length)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with HOMOGRAPHIES.open() as f:
        results = json.load(f)

    matrices = {
        result["strategy"]: np.asarray(
            result["H_rink_to_image"],
            dtype=np.float64,
        )
        for result in results
        if result["frame"] == FRAME
    }

    required = {"A_fixed", "B_all"}

    if not required.issubset(matrices):
        raise RuntimeError("Missing frame-0011 homography strategies.")

    with ANNOTATIONS.open(newline="") as f:
        annotations = list(csv.DictReader(f))

    if not annotations:
        raise RuntimeError("No annotations found.")

    rows = []
    grouped = defaultdict(list)

    for annotation in annotations:
        line_name = annotation["line_name"]

        if line_name not in LINE_COORDINATES:
            raise ValueError(f"Unknown rink line: {line_name}")

        rink_x = LINE_COORDINATES[line_name]

        point = (
            float(annotation["image_x_px"]),
            float(annotation["image_y_px"]),
        )

        for strategy, H in matrices.items():
            a, b = project_line(H, rink_x)

            distance = point_to_line_distance(
                point,
                a,
                b,
            )

            rows.append(
                {
                    "strategy": strategy,
                    "line_name": line_name,
                    "rink_x_m": rink_x,
                    "image_x_px": point[0],
                    "image_y_px": point[1],
                    "distance_px": distance,
                }
            )

            grouped[(strategy, line_name)].append(distance)

    output_csv = OUTPUT_DIR / "line_alignment_residuals.csv"

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nEXPERIMENT 04 — INDEPENDENT LINE VALIDATION")
    print("-" * 75)

    for strategy in ("A_fixed", "B_all"):
        all_distances = []

        print(f"\n{strategy}")

        for line_name in LINE_COORDINATES:
            distances = grouped[(strategy, line_name)]

            all_distances.extend(distances)

            print(
                f"  {line_name:16s} "
                f"mean={np.mean(distances):8.3f}px "
                f"max={np.max(distances):8.3f}px"
            )

        print(
            f"\n  OVERALL: "
            f"mean={np.mean(all_distances):.3f}px "
            f"median={np.median(all_distances):.3f}px "
            f"max={np.max(all_distances):.3f}px"
        )

    print(f"\nSaved: {output_csv}")
    print(f"Total measurements: {len(rows)}")


if __name__ == "__main__":
    main()
