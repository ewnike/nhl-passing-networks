#!/usr/bin/env python3

"""
Experiment 04 — Stage 2: Temporal Homography Estimation

Estimate independent rink-to-image homographies for:
    frame_0009.jpg
    frame_0010.jpg
    frame_0011.jpg

Compare:
    A: Original Experiment 01 landmark subset
    B: All eligible high-confidence landmarks

Uses saved HockeyRink predictions.
Does not rerun neural network inference.
Does not modify Experiment 01 artifacts.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

DETECTIONS = BASE / "rink_keypoint_pilot/detections.json"

OUTPUT_DIR = BASE / "homography_experiment_04/stage_2"

BASELINE_JSON = BASE / "homography_experiment_01/homography.json"

FRAMES = [
    "frame_0009.jpg",
    "frame_0010.jpg",
    "frame_0011.jpg",
]

CONFIDENCE_THRESHOLD = 0.80
RANSAC_THRESHOLD = 5.0

# Original Experiment 01 landmark subset.
ORIGINAL_IDS = {20, 22, 23, 24, 25, 26, 27, 32}

# Canonical IIHF physical coordinates for the union of
# high-confidence landmarks observed in these three frames.
#
# Source: docs/hockeyrink/hockeyrink_keypoints.md

RINK_POINTS = {
    20: (-7.65, 15.00),
    22: (-6.00, 7.00),
    23: (-6.00, -7.00),
    24: (0.00, 15.00),
    25: (0.00, 4.50),
    26: (0.00, 0.00),
    27: (0.00, -4.50),
    32: (6.00, 7.00),
    33: (6.00, -7.00),
    34: (7.65, 15.00),
}


def project(points, H):

    points = np.asarray(
        points,
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(
        points,
        H,
    ).reshape(-1, 2)


def fit_homography(points):

    rink = np.asarray(
        [p["rink"] for p in points],
        dtype=np.float64,
    )

    image = np.asarray(
        [p["image"] for p in points],
        dtype=np.float64,
    )

    if len(points) < 4:
        raise RuntimeError("Insufficient landmarks for homography.")

    H, mask = cv2.findHomography(
        rink,
        image,
        method=cv2.RANSAC,
        ransacReprojThreshold=RANSAC_THRESHOLD,
    )

    if H is None or mask is None:
        raise RuntimeError("Homography estimation failed.")

    inliers = mask.ravel().astype(bool)

    if int(inliers.sum()) < 4:
        raise RuntimeError("Insufficient RANSAC inliers.")

    H_inverse = np.linalg.inv(H)
    H_inverse /= H_inverse[2, 2]

    projected = project(rink, H)

    residuals = np.linalg.norm(
        projected - image,
        axis=1,
    )

    return H, H_inverse, inliers, residuals


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DETECTIONS.open() as f:
        detections = json.load(f)

    with BASELINE_JSON.open() as f:
        baseline = json.load(f)

    records = {record["frame"]: record for record in detections}

    results = []
    residual_rows = []

    for frame in FRAMES:
        record = records[frame]

        if record["detections"] != 1:
            raise RuntimeError(f"{frame}: expected one rink detection.")

        predictions = record["keypoints"][0]["points"]

        for strategy in ("A_fixed", "B_all"):
            selected = []

            for point in predictions:
                kp = point["index"]
                confidence = float(point["confidence"])

                if confidence < CONFIDENCE_THRESHOLD:
                    continue

                if kp not in RINK_POINTS:
                    continue

                if strategy == "A_fixed" and kp not in ORIGINAL_IDS:
                    continue

                selected.append(
                    {
                        "kp": kp,
                        "confidence": confidence,
                        "rink": RINK_POINTS[kp],
                        "image": (
                            float(point["x"]),
                            float(point["y"]),
                        ),
                    }
                )

            H, H_inverse, inliers, residuals = fit_homography(selected)

            inlier_residuals = residuals[inliers]

            result = {
                "frame": frame,
                "strategy": strategy,
                "candidate_landmarks": len(selected),
                "ransac_inliers": int(inliers.sum()),
                "ransac_outliers": int((~inliers).sum()),
                "inlier_ids": [
                    selected[i]["kp"] for i in range(len(selected)) if inliers[i]
                ],
                "outlier_ids": [
                    selected[i]["kp"] for i in range(len(selected)) if not inliers[i]
                ],
                "mean_inlier_error_px": float(inlier_residuals.mean()),
                "median_inlier_error_px": float(np.median(inlier_residuals)),
                "max_inlier_error_px": float(inlier_residuals.max()),
                "H_rink_to_image": H.tolist(),
                "H_image_to_rink": H_inverse.tolist(),
            }

            results.append(result)

            for i, point in enumerate(selected):
                residual_rows.append(
                    {
                        "frame": frame,
                        "strategy": strategy,
                        "kp": point["kp"],
                        "confidence": point["confidence"],
                        "inlier": bool(inliers[i]),
                        "residual_px": float(residuals[i]),
                    }
                )

            print(
                f"{frame} {strategy}: "
                f"{len(selected)} candidates, "
                f"{inliers.sum()} inliers, "
                f"mean error={inlier_residuals.mean():.3f}px"
            )

    output_json = OUTPUT_DIR / "temporal_homographies.json"

    with output_json.open("w") as f:
        json.dump(results, f, indent=2)

    output_csv = OUTPUT_DIR / "temporal_landmark_residuals.csv"

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(residual_rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(residual_rows)

    print("\nOutputs:")
    print(output_json)
    print(output_csv)

    # Compare the newly estimated frame-0010 homography
    # against the original Experiment 01 baseline.
    #
    # RANSAC may select different samples, so compare
    # projected reference locations rather than requiring
    # identical matrix coefficients.

    original_H = np.asarray(
        baseline["H_rink_to_image"],
        dtype=np.float64,
    )

    current = next(
        r
        for r in results
        if r["frame"] == "frame_0010.jpg" and r["strategy"] == "A_fixed"
    )

    current_H = np.asarray(
        current["H_rink_to_image"],
        dtype=np.float64,
    )

    reference = np.asarray(
        [
            [-7.65, 15.0],
            [-6.0, 7.0],
            [0.0, 0.0],
            [0.0, 15.0],
            [6.0, 7.0],
        ]
    )

    original_projection = project(reference, original_H)
    current_projection = project(reference, current_H)

    difference = np.linalg.norm(
        current_projection - original_projection,
        axis=1,
    )

    print("\nEXPERIMENT 01 BASELINE REPRODUCTION")
    print("-----------------------------------")
    print(f"Mean projection difference: {difference.mean():.6f}px")
    print(f"Maximum projection difference: {difference.max():.6f}px")


if __name__ == "__main__":
    main()
