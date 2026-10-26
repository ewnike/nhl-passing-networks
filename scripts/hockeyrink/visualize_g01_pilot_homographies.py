#!/usr/bin/env python3

"""
Experiment 05 — Stage 5C
Pilot Homography Visual Validation

Project rink geometry onto selected G01 pilot frames.

Uses saved Experiment 05 homographies.
Does not rerun inference or refit homographies.

Outputs:
    frame_0018_overlay.jpg
    frame_0039_overlay.jpg
    frame_0041_overlay.jpg
    pilot_homography_review.jpg
"""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

RESULTS = BASE / "homography_experiment_05" / "pilot_homographies.json"

FRAMES = BASE / "frames/P1_pilot"

OUTPUT = BASE / "homography_experiment_05" / "visual_validation"

SELECTED = [
    "frame_0018.jpg",
    "frame_0039.jpg",
    "frame_0041.jpg",
]

# OpenCV uses BGR.
GREEN = (0, 255, 0)


def project(points, H):

    points = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(points, H).reshape(-1, 2)


def draw_geometry(image, H):

    # Blue lines and center red line.
    for x in (-7.65, 0.0, 7.65):
        points = np.asarray(
            [
                [x, -15.0],
                [x, 15.0],
            ],
            dtype=np.float64,
        )

        projected = project(points, H)

        if not np.isfinite(projected).all():
            continue

        p1, p2 = np.round(projected).astype(np.int32)

        cv2.line(image, tuple(p1), tuple(p2), GREEN, 3, cv2.LINE_AA)

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
            image, [np.round(projected).astype(np.int32)], True, GREEN, 3, cv2.LINE_AA
        )


def main():

    OUTPUT.mkdir(parents=True, exist_ok=True)

    records = json.loads(RESULTS.read_text())

    by_frame = {r["frame"]: r for r in records}

    images = []

    for frame_name in SELECTED:
        record = by_frame[frame_name]

        if record["status"] != "success":
            raise RuntimeError(f"No successful homography: {frame_name}")

        H = np.asarray(record["H_rink_to_image"], dtype=np.float64)

        frame_path = FRAMES / frame_name

        image = cv2.imread(str(frame_path))

        if image is None:
            raise RuntimeError(f"Cannot load: {frame_path}")

        draw_geometry(image, H)

        output_path = OUTPUT / frame_name.replace(".jpg", "_overlay.jpg")

        if not cv2.imwrite(str(output_path), image):
            raise RuntimeError(f"Failed to save: {output_path}")

        print("Created:", output_path)

        # Convert BGR to RGB for Pillow.
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        images.append((frame_name, Image.fromarray(rgb)))

    # Create a vertical comparison sheet.
    width = 960
    label_height = 45
    margin = 15

    resized = []

    for name, image in images:
        height = round(image.height * width / image.width)

        image = image.resize((width, height), Image.Resampling.LANCZOS)

        resized.append((name, image))

    total_height = (
        sum(image.height + label_height + margin for _, image in resized) + margin
    )

    sheet = Image.new("RGB", (width + 2 * margin, total_height), "white")

    draw = ImageDraw.Draw(sheet)

    y = margin

    for name, image in resized:
        draw.text((margin + 10, y + 10), name, fill="black")

        y += label_height

        sheet.paste(image, (margin, y))

        y += image.height + margin

    output_sheet = OUTPUT / "pilot_homography_review.jpg"

    sheet.save(output_sheet, quality=95)

    print("\nCreated:", output_sheet)


if __name__ == "__main__":
    main()
