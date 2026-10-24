#!/usr/bin/env python3

"""
Experiment 04 — Stage 4A
Dense HockeyRink Landmark Stability

Analyze 75 consecutive frames at 25 FPS.

Uses previously saved predictions.
Does not rerun model inference.
"""

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "homography_experiment_04/stage_4"
)

INPUT = BASE / "detections.json"

OUTPUT = BASE / "dense_landmark_stability.csv"

CONFIDENCE_THRESHOLD = 0.80
FPS = 25.0


def main():

    with INPUT.open() as f:
        records = json.load(f)

    if len(records) != 75:
        raise RuntimeError(f"Expected 75 records, found {len(records)}")

    rows = []
    previous = None
    counts = []

    for frame_index, record in enumerate(records):
        if record["detections"] != 1:
            raise RuntimeError(f"Unexpected detection count: {record['frame']}")

        points = {p["index"]: p for p in record["keypoints"][0]["points"]}

        eligible = {
            kp for kp, p in points.items() if p["confidence"] >= CONFIDENCE_THRESHOLD
        }

        counts.append(len(eligible))

        for kp, point in points.items():
            confidence = float(point["confidence"])

            dx = None
            dy = None
            displacement = None

            if previous is not None and kp in previous:
                old = previous[kp]

                # Measure motion only when the landmark is
                # high-confidence in both consecutive frames.
                if (
                    confidence >= CONFIDENCE_THRESHOLD
                    and old["confidence"] >= CONFIDENCE_THRESHOLD
                ):
                    dx = float(point["x"] - old["x"])
                    dy = float(point["y"] - old["y"])

                    displacement = float(np.hypot(dx, dy))

            rows.append(
                {
                    "frame": record["frame"],
                    "frame_index": frame_index,
                    "video_time_seconds": 9.0 + frame_index / FPS,
                    "kp": kp,
                    "confidence": confidence,
                    "above_threshold": confidence >= CONFIDENCE_THRESHOLD,
                    "dx_px": dx,
                    "dy_px": dy,
                    "displacement_px": displacement,
                }
            )

        previous = points

    with OUTPUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nEXPERIMENT 04 — DENSE LANDMARK STABILITY")
    print("-" * 65)

    print("Frames:", len(records))
    print("Keypoint records:", len(rows))

    print("High-confidence landmarks per frame:")

    print("  Minimum:", min(counts))
    print("  Maximum:", max(counts))
    print("  Mean:", round(float(np.mean(counts)), 3))

    print("\nMost common landmark counts:")

    for count, frequency in Counter(counts).most_common(10):
        print(f"  {count} landmarks: {frequency} frames")

    valid = [r["displacement_px"] for r in rows if r["displacement_px"] is not None]

    print("\nConsecutive-frame landmark displacement:")

    print("  Measurements:", len(valid))
    print("  Mean:", round(float(np.mean(valid)), 3), "px")
    print("  Median:", round(float(np.median(valid)), 3), "px")
    print("  Maximum:", round(float(np.max(valid)), 3), "px")

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
