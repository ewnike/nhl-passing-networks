#!/usr/bin/env python3

"""
Experiment 04 — Stage 4C
Dense Temporal Homography Stability

Compare projected physical rink locations across
75 consecutive independently estimated homographies.

No model inference.
No homography refitting.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "homography_experiment_04/stage_4"
)

INPUT = BASE / "dense_homographies.json"

OUTPUT = BASE / "dense_homography_temporal_displacements.csv"

REFERENCE_POINTS = {
    20: (-7.65, 15.0),
    21: (-7.65, -15.0),
    24: (0.0, 15.0),
    26: (0.0, 0.0),
    30: (0.0, -15.0),
    34: (7.65, 15.0),
    35: (7.65, -15.0),
}


def project(H, points):

    array = np.asarray(
        points,
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(
        array,
        H,
    ).reshape(-1, 2)


def main():

    with INPUT.open() as f:
        records = json.load(f)

    successful = [r for r in records if r["status"] == "success"]

    if len(successful) != 75:
        raise RuntimeError("Expected 75 successful homographies.")

    kp_ids = list(REFERENCE_POINTS)

    rink = np.asarray(
        [REFERENCE_POINTS[kp] for kp in kp_ids],
        dtype=np.float64,
    )

    rows = []
    summaries = []

    previous = None

    for record in successful:
        frame = record["frame"]

        H = np.asarray(
            record["H_rink_to_image"],
            dtype=np.float64,
        )

        projected = project(H, rink)

        if previous is not None:
            displacement = np.linalg.norm(
                projected - previous["projected"],
                axis=1,
            )

            for index, kp in enumerate(kp_ids):
                rows.append(
                    {
                        "frame": frame,
                        "previous_frame": previous["frame"],
                        "kp": kp,
                        "rink_x_m": rink[index, 0],
                        "rink_y_m": rink[index, 1],
                        "displacement_px": float(displacement[index]),
                    }
                )

            summaries.append(
                {
                    "frame": frame,
                    "mean_displacement_px": float(displacement.mean()),
                    "median_displacement_px": float(np.median(displacement)),
                    "max_displacement_px": float(displacement.max()),
                }
            )

        previous = {
            "frame": frame,
            "projected": projected,
        }

    with OUTPUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nEXPERIMENT 04 — DENSE HOMOGRAPHY STABILITY")
    print("-" * 65)

    print("Frame transitions:", len(summaries))
    print("Reference points:", len(kp_ids))
    print("Total measurements:", len(rows))

    mean_values = [s["mean_displacement_px"] for s in summaries]

    max_values = [s["max_displacement_px"] for s in summaries]

    print("\nMean frame-transition displacement:", f"{np.mean(mean_values):.3f} px")

    print("Median frame-transition displacement:", f"{np.median(mean_values):.3f} px")

    print("Maximum observed displacement:", f"{np.max(max_values):.3f} px")

    print("\nLargest frame transitions:")

    for item in sorted(
        summaries,
        key=lambda s: s["max_displacement_px"],
        reverse=True,
    )[:10]:
        print(
            f"{item['frame']}: "
            f"mean={item['mean_displacement_px']:.2f}px "
            f"max={item['max_displacement_px']:.2f}px"
        )

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
