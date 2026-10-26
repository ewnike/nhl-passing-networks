#!/usr/bin/env python3

"""
Experiment 04 — Stage 4D
Visible-Region Homography Stability

Compare all seven reference points against points whose
projections fall inside both consecutive video frames.

Uses saved homographies.
Does not rerun inference or modify earlier results.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import pearsonr, spearmanr

BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "homography_experiment_04/stage_4"
)

INPUT = BASE / "dense_homographies.json"

OUTPUT = BASE / "visible_region_stability.csv"

WIDTH = 1920
HEIGHT = 1080

REFERENCE = {
    20: (-7.65, 15.0),
    21: (-7.65, -15.0),
    24: (0.0, 15.0),
    26: (0.0, 0.0),
    30: (0.0, -15.0),
    34: (7.65, 15.0),
    35: (7.65, -15.0),
}


def project(H, points):
    array = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(array, H).reshape(-1, 2)


def inside_image(points):
    return (
        np.isfinite(points).all(axis=1)
        & (points[:, 0] >= 0)
        & (points[:, 0] < WIDTH)
        & (points[:, 1] >= 0)
        & (points[:, 1] < HEIGHT)
    )


def main():

    records = json.loads(INPUT.read_text())

    kp_ids = list(REFERENCE)

    rink = np.asarray([REFERENCE[kp] for kp in kp_ids], dtype=np.float64)

    rows = []

    for previous, current in zip(records[:-1], records[1:]):
        if previous["status"] != "success" or current["status"] != "success":
            continue

        H_prev = np.asarray(previous["H_rink_to_image"], dtype=np.float64)

        H_curr = np.asarray(current["H_rink_to_image"], dtype=np.float64)

        prev_points = project(H_prev, rink)
        curr_points = project(H_curr, rink)

        displacement = np.linalg.norm(curr_points - prev_points, axis=1)

        visible = inside_image(prev_points) & inside_image(curr_points)

        A = set(previous["inlier_ids"])
        B = set(current["inlier_ids"])

        union = A | B

        jaccard = len(A & B) / len(union) if union else np.nan

        all_distances = displacement[np.isfinite(displacement)]

        visible_distances = displacement[visible & np.isfinite(displacement)]

        rows.append(
            {
                "frame": current["frame"],
                "previous_frame": previous["frame"],
                "jaccard": float(jaccard),
                "all_count": len(all_distances),
                "visible_count": len(visible_distances),
                "all_mean_px": float(np.mean(all_distances)),
                "all_max_px": float(np.max(all_distances)),
                "visible_mean_px": (
                    float(np.mean(visible_distances))
                    if len(visible_distances)
                    else None
                ),
                "visible_max_px": (
                    float(np.max(visible_distances)) if len(visible_distances) else None
                ),
            }
        )

    with OUTPUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print("\nEXPERIMENT 04 — STAGE 4D")
    print("VISIBLE-REGION HOMOGRAPHY STABILITY")
    print("-" * 65)

    print("Transitions analyzed:", len(rows))

    print(
        "Visible points per transition:",
        f"min={min(r['visible_count'] for r in rows)}, "
        f"max={max(r['visible_count'] for r in rows)}",
    )

    for label, mean_key, max_key in [
        ("Full reference set", "all_mean_px", "all_max_px"),
        ("Image-bounded reference set", "visible_mean_px", "visible_max_px"),
    ]:
        valid = [
            r
            for r in rows
            if r[mean_key] is not None
            and r[max_key] is not None
            and np.isfinite(r["jaccard"])
        ]

        x = np.asarray([r["jaccard"] for r in valid])

        mean = np.asarray([r[mean_key] for r in valid])

        maximum = np.asarray([r[max_key] for r in valid])

        print(f"\n{label}")
        print("  Transitions:", len(valid))
        print("  Mean displacement:", f"{mean.mean():.3f} px")
        print("  Median transition mean:", f"{np.median(mean):.3f} px")
        print("  Maximum displacement:", f"{maximum.max():.3f} px")

        if len(valid) >= 3 and len(np.unique(x)) > 1:
            print("  Pearson (mean):", f"{pearsonr(x, mean).statistic:+.3f}")
            print("  Spearman (mean):", f"{spearmanr(x, mean).statistic:+.3f}")
            print("  Pearson (max):", f"{pearsonr(x, maximum).statistic:+.3f}")
            print("  Spearman (max):", f"{spearmanr(x, maximum).statistic:+.3f}")

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
