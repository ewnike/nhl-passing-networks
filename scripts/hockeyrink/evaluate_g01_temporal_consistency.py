#!/usr/bin/env python3

"""
Experiment 04 — Temporal Homography Consistency

Stage 1:
Measure landmark displacement and confidence changes across
three sampled frames.

Uses saved HockeyRink predictions. No new inference.
"""

import csv
import json
from pathlib import Path

import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

PREDICTIONS = BASE / "rink_keypoint_pilot/detections.json"

OUTPUT_DIR = BASE / "homography_experiment_04"

FRAMES = [
    "frame_0009.jpg",
    "frame_0010.jpg",
    "frame_0011.jpg",
]

CONFIDENCE_THRESHOLD = 0.80


def load_predictions():

    with PREDICTIONS.open() as f:
        records = json.load(f)

    selected = {}

    for record in records:
        frame = record.get("frame")

        if frame not in FRAMES:
            continue

        points = record["keypoints"][0]["points"]

        selected[frame] = {point["index"]: point for point in points}

    missing = set(FRAMES) - set(selected)

    if missing:
        raise RuntimeError(f"Missing predictions: {sorted(missing)}")

    return selected


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    predictions = load_predictions()

    print("\nEXPERIMENT 04 — TEMPORAL CONSISTENCY")
    print("-" * 65)

    high_confidence_sets = {}

    for frame in FRAMES:
        points = predictions[frame]

        high_confidence = {
            kp
            for kp, point in points.items()
            if point["confidence"] >= CONFIDENCE_THRESHOLD
        }

        high_confidence_sets[frame] = high_confidence

        print(f"{frame}: {len(high_confidence)} high-confidence landmarks")

    common = set.intersection(*high_confidence_sets.values())

    print("\nCommon high-confidence landmarks:", sorted(common))

    rows = []

    for frame_a, frame_b in zip(
        FRAMES[:-1],
        FRAMES[1:],
    ):
        print(f"\n{frame_a} → {frame_b}")

        for kp in sorted(common):
            p0 = predictions[frame_a][kp]
            p1 = predictions[frame_b][kp]

            dx = p1["x"] - p0["x"]
            dy = p1["y"] - p0["y"]

            distance = float(np.hypot(dx, dy))

            confidence_change = p1["confidence"] - p0["confidence"]

            rows.append(
                {
                    "frame_a": frame_a,
                    "frame_b": frame_b,
                    "kp": kp,
                    "dx_px": float(dx),
                    "dy_px": float(dy),
                    "displacement_px": distance,
                    "confidence_a": p0["confidence"],
                    "confidence_b": p1["confidence"],
                    "confidence_change": confidence_change,
                }
            )

            print(
                f"KP-{kp:02d}: "
                f"dx={dx:+8.2f}px "
                f"dy={dy:+8.2f}px "
                f"distance={distance:8.2f}px"
            )

    output_csv = OUTPUT_DIR / "landmark_temporal_displacements.csv"

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {output_csv}")
    print(f"Total measurements: {len(rows)}")


if __name__ == "__main__":
    main()
