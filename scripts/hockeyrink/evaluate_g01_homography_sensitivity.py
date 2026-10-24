#!/usr/bin/env python3

"""
Experiment 03 — G01 Homography Sensitivity Analysis

Compares:
A: Original Experiment 01 homography
B: Baseline inliers + KP-23
C: Baseline inliers + KP-26
D: All eight landmarks

No YOLO inference.
No modification of existing experiment artifacts.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

INPUT_JSON = BASE / "homography_experiment_01/homography.json"
INPUT_FRAME = BASE / "frames/P1_pilot/frame_0010.jpg"
OUTPUT_DIR = BASE / "homography_experiment_03"

COLORS = {
    "A_baseline": (0, 255, 0),
    "B_with_KP23": (255, 0, 0),
    "C_with_KP26": (0, 0, 255),
    "D_all_eight": (255, 0, 255),
}


def project(points, H):
    points = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(points, H).reshape(-1, 2)


def draw_geometry(image, H, color):
    """Draw blue lines, center line, and center circle."""

    for x in (-7.65, 0.0, 7.65):
        endpoints = project([(x, -15.0), (x, 15.0)], H)

        endpoints = np.round(endpoints).astype(np.int32)

        cv2.line(
            image,
            tuple(endpoints[0]),
            tuple(endpoints[1]),
            color,
            2,
            cv2.LINE_AA,
        )

    angles = np.linspace(0, 2 * np.pi, 181)

    circle = np.column_stack(
        [
            4.5 * np.cos(angles),
            4.5 * np.sin(angles),
        ]
    )

    projected = project(circle, H)

    cv2.polylines(
        image,
        [np.round(projected).astype(np.int32)],
        True,
        color,
        2,
        cv2.LINE_AA,
    )


def fit_homography(landmarks):
    rink = np.array(
        [[p["rink_x"], p["rink_y"]] for p in landmarks],
        dtype=np.float64,
    )

    image = np.array(
        [[p["image_x"], p["image_y"]] for p in landmarks],
        dtype=np.float64,
    )

    H, _ = cv2.findHomography(rink, image, method=0)

    if H is None:
        raise RuntimeError("Homography fitting failed.")

    return H


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with INPUT_JSON.open() as f:
        experiment_01 = json.load(f)

    landmarks = experiment_01["landmarks"]

    baseline = [p for p in landmarks if p["inlier"]]

    kp23 = [p for p in landmarks if p["kp"] == 23]

    kp26 = [p for p in landmarks if p["kp"] == 26]

    if len(baseline) != 6 or len(kp23) != 1 or len(kp26) != 1:
        raise RuntimeError("Unexpected Experiment 01 landmark configuration.")

    experiments = {
        "A_baseline": baseline,
        "B_with_KP23": baseline + kp23,
        "C_with_KP26": baseline + kp26,
        "D_all_eight": landmarks,
    }

    homographies = {
        "A_baseline": np.asarray(
            experiment_01["H_rink_to_image"],
            dtype=np.float64,
        )
    }

    for name, selected in experiments.items():
        if name == "A_baseline":
            continue

        homographies[name] = fit_homography(selected)

    image = cv2.imread(str(INPUT_FRAME))

    if image is None:
        raise FileNotFoundError(INPUT_FRAME)

    rows = []
    matrices = {}

    for name, H in homographies.items():
        selected = experiments[name]

        rink_points = [(p["rink_x"], p["rink_y"]) for p in selected]

        observed = np.array([(p["image_x"], p["image_y"]) for p in selected])

        predicted = project(rink_points, H)

        errors = np.linalg.norm(
            predicted - observed,
            axis=1,
        )

        rows.append(
            {
                "experiment": name,
                "landmarks": len(selected),
                "mean_error_px": float(errors.mean()),
                "median_error_px": float(np.median(errors)),
                "max_error_px": float(errors.max()),
            }
        )

        matrices[name] = H.tolist()

        # Individual annotated overlay
        annotated = image.copy()

        draw_geometry(annotated, H, COLORS[name])

        cv2.imwrite(
            str(OUTPUT_DIR / f"{name}.jpg"),
            annotated,
        )

    # Combined comparison overlay
    combined = image.copy()

    for name, H in homographies.items():
        draw_geometry(combined, H, COLORS[name])

    cv2.imwrite(
        str(OUTPUT_DIR / "combined_comparison.jpg"),
        combined,
    )

    with (OUTPUT_DIR / "sensitivity_results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)

    with (OUTPUT_DIR / "homography_matrices.json").open("w") as f:
        json.dump(matrices, f, indent=2)

    # ---------------------------------------------------------
    # Transformation sensitivity at fixed rink reference points
    # ---------------------------------------------------------

    reference_points = np.array(
        [
            [-7.65, -15.0],  # KP-21
            [-7.65, 15.0],  # KP-20
            [0.00, -15.0],  # KP-30
            [0.00, 0.0],  # KP-26
            [0.00, 15.0],  # KP-24
            [7.65, -15.0],  # KP-35
            [7.65, 15.0],  # KP-34
        ],
        dtype=np.float64,
    )

    reference_ids = [21, 20, 30, 26, 24, 35, 34]

    baseline_projection = project(reference_points, homographies["A_baseline"])

    displacement_rows = []

    print("\nTRANSFORMATION SENSITIVITY")
    print("-" * 65)

    for name, H in homographies.items():
        projected = project(reference_points, H)

        displacements = np.linalg.norm(projected - baseline_projection, axis=1)

        for kp, point, distance in zip(reference_ids, reference_points, displacements):
            displacement_rows.append(
                {
                    "experiment": name,
                    "kp": kp,
                    "rink_x_m": float(point[0]),
                    "rink_y_m": float(point[1]),
                    "displacement_px": float(distance),
                }
            )

        max_index = int(np.argmax(displacements))

        print(
            f"{name:15s} "
            f"mean={displacements.mean():7.3f}px "
            f"max={displacements.max():7.3f}px "
            f"at KP-{reference_ids[max_index]}"
        )

    output_csv = OUTPUT_DIR / "transformation_displacements.csv"

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "experiment",
                "kp",
                "rink_x_m",
                "rink_y_m",
                "displacement_px",
            ],
        )

        writer.writeheader()
        writer.writerows(displacement_rows)

    print(f"\nSaved displacement measurements: {output_csv}")

    print("\nEXPERIMENT 03 — SENSITIVITY ANALYSIS")
    print("-----------------------------------")

    for row in rows:
        print(
            f"{row['experiment']}: "
            f"{row['landmarks']} landmarks, "
            f"mean={row['mean_error_px']:.3f}px, "
            f"max={row['max_error_px']:.3f}px"
        )

    print(f"\nResults: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
