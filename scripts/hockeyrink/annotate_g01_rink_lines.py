#!/usr/bin/env python3

"""
Experiment 04 — Stage 3B

Manual annotation of painted rink-line locations.

Click points along the center of each painted line.

Controls:
    1 = Western blue line
    2 = Center red line
    3 = Eastern blue line
    U = Undo last point
    S = Save annotations
    Q = Quit

Coordinates are recorded in original image pixels.
"""

import csv
from pathlib import Path

import cv2

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

IMAGE_PATH = BASE / "frames/P1_pilot/frame_0011.jpg"

OUTPUT_PATH = (
    BASE
    / "homography_experiment_04/stage_3/manual_validation"
    / "painted_line_points.csv"
)

LINES = {
    ord("1"): ("western_blue", -7.65),
    ord("2"): ("center_red", 0.0),
    ord("3"): ("eastern_blue", 7.65),
}

current_line = LINES[ord("1")]

points = []

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise FileNotFoundError(IMAGE_PATH)


def redraw():
    display = image.copy()

    for point in points:
        cv2.circle(
            display,
            (point["image_x_px"], point["image_y_px"]),
            5,
            (0, 255, 255),
            -1,
        )

    label = f"Selected: {current_line[0]} | Points: {len(points)}"

    cv2.putText(
        display,
        label,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )

    cv2.imshow("Rink Line Annotation", display)


def mouse_callback(event, x, y, flags, userdata):

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append(
            {
                "line_name": current_line[0],
                "rink_x_m": current_line[1],
                "image_x_px": x,
                "image_y_px": y,
            }
        )

        redraw()


def save_points():

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "line_name",
                "rink_x_m",
                "image_x_px",
                "image_y_px",
            ],
        )

        writer.writeheader()
        writer.writerows(points)

    print(f"Saved {len(points)} points to {OUTPUT_PATH}")


cv2.namedWindow("Rink Line Annotation", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Rink Line Annotation", mouse_callback)

redraw()

while True:
    key = cv2.waitKey(0) & 0xFF

    if key in LINES:
        current_line = LINES[key]
        redraw()

    elif key == ord("u"):
        if points:
            points.pop()
            redraw()

    elif key == ord("s"):
        save_points()

    elif key == ord("q"):
        break

cv2.destroyAllWindows()
