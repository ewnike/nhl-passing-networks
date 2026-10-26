#!/usr/bin/env python3

"""
Experiment 05 — Stage 5C
Offensive-Zone Homography Visual Validation

Project verified IIHF offensive-zone geometry onto
frame_0039.jpg using the saved Experiment 05 homography.

No inference.
No homography refitting.
Original artifacts remain unchanged.
"""

import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

RESULTS = BASE / "homography_experiment_05/pilot_homographies.json"

FRAME = BASE / "frames/P1_pilot/frame_0039.jpg"

OUTPUT = (
    BASE
    / "homography_experiment_05"
    / "visual_validation"
    / "frame_0039_offensive_zone_overlay.jpg"
)

REFERENCE = Path("data/reference/hockeyrink_56_landmarks_iihf.json")

# OpenCV BGR colors.
EAST_COLOR = (0, 255, 0)  # Green
WEST_COLOR = (255, 255, 0)  # Cyan
DOT_COLOR = (0, 255, 255)  # Yellow


def project(points, H):
    points = np.asarray(
        points,
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(
        points,
        H,
    ).reshape(-1, 2)


def draw_line(image, H, start, end, color):
    projected = project([start, end], H)

    if not np.isfinite(projected).all():
        return

    p1, p2 = np.round(projected).astype(np.int32)

    cv2.line(
        image,
        tuple(p1),
        tuple(p2),
        color,
        3,
        cv2.LINE_AA,
    )


def draw_circle(image, H, center, radius, color):
    theta = np.linspace(
        0,
        2 * np.pi,
        181,
    )

    points = np.column_stack(
        [
            center[0] + radius * np.cos(theta),
            center[1] + radius * np.sin(theta),
        ]
    )

    projected = project(points, H)

    if not np.isfinite(projected).all():
        return

    polygon = np.round(projected).astype(np.int32)

    cv2.polylines(
        image,
        [polygon],
        True,
        color,
        3,
        cv2.LINE_AA,
    )


def draw_dot(image, H, coordinate, color):
    projected = project([coordinate], H)

    if not np.isfinite(projected).all():
        return

    x, y = np.round(projected[0]).astype(int)

    cv2.circle(
        image,
        (x, y),
        7,
        color,
        -1,
    )


def draw_zone(image, H, side):
    if side == "east":
        sign = 1
        color = EAST_COLOR
    else:
        sign = -1
        color = WEST_COLOR

    goal_x = sign * 26.0
    blue_x = sign * 7.65
    faceoff_x = sign * 20.0

    # Goal line.
    draw_line(
        image,
        H,
        (goal_x, -15.0),
        (goal_x, 15.0),
        color,
    )

    # Blue line.
    draw_line(
        image,
        H,
        (blue_x, -15.0),
        (blue_x, 15.0),
        color,
    )

    # Offensive-zone faceoff circles.
    for y in (-7.0, 7.0):
        draw_circle(
            image,
            H,
            (faceoff_x, y),
            4.5,
            color,
        )

        draw_dot(
            image,
            H,
            (faceoff_x, y),
            DOT_COLOR,
        )


def main():
    records = json.loads(RESULTS.read_text())

    record = next(r for r in records if r["frame"] == "frame_0039.jpg")

    if record["status"] != "success":
        raise RuntimeError("Frame 0039 has no successful homography.")

    H = np.asarray(
        record["H_rink_to_image"],
        dtype=np.float64,
    )

    image = cv2.imread(str(FRAME))

    if image is None:
        raise FileNotFoundError(FRAME)

    draw_zone(image, H, "east")
    # draw_zone(image, H, "west")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not cv2.imwrite(
        str(OUTPUT),
        image,
    ):
        raise RuntimeError(f"Failed to save {OUTPUT}")

    print("\nEXPERIMENT 05 — OFFENSIVE-ZONE OVERLAY")
    print("-" * 60)
    print("Frame: frame_0039.jpg")
    print("Green: Eastern offensive zone")
    print("Cyan: Western offensive zone")
    print("Yellow: Faceoff dots")
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
