#!/usr/bin/env python3
"""
Experiment 07B — Verified Player Appearance Extraction

Extract player crops using human-verified identity observations
and existing Stage 6D3 tracking bounding boxes.

Read-only with respect to original frames and tracking data.
Refuses to overwrite existing output files.
"""

import csv
import json
from pathlib import Path

from PIL import Image


BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "frames/P1_experiment_06d_300_330"
)

TRACKING = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_06/stage_6d/"
    "camera_cut_aware_baseline/"
    "track_observations.csv"
)

IDENTITIES = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_07/identity_reference/"
    "verified_player_observations.csv"
)

OUTPUT = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_07/identity_reference/"
    "appearance_crops"
)


def main():

    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {OUTPUT}")

    with IDENTITIES.open(newline="") as file:
        verified = list(csv.DictReader(file))

    with TRACKING.open(newline="") as file:
        observations = {
            (int(row["frame_index"]), row["track_uid"]): row
            for row in csv.DictReader(file)
        }

    # Validate every input before creating output.
    planned = []
    names = set()

    for identity in verified:
        frame = int(identity["frame_index"])
        uid = identity["track_uid"]

        if identity["verification_method"] != "human_visual_review":
            raise ValueError(f"Unverified identity: frame={frame}, track={uid}")

        key = (frame, uid)

        if key not in observations:
            raise ValueError(f"Missing tracking observation: {key}")

        image_path = BASE / f"frame_{frame:04d}.jpg"

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        row = observations[key]

        bbox = [float(row[k]) for k in ("x1", "y1", "x2", "y2")]

        with Image.open(image_path) as image:
            width, height = image.size

        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(width, int(bbox[2] + 1))
        y2 = min(height, int(bbox[3] + 1))

        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"Invalid bounding box: {key}")

        filename = (
            f"{identity['game_id']}_"
            f"{identity['team']}_"
            f"{identity['jersey_number']}_"
            f"frame_{frame:04d}_"
            f"{uid.replace(':', '-')}.png"
        )

        if filename in names:
            raise ValueError(f"Duplicate output filename: {filename}")

        names.add(filename)

        planned.append(
            {
                "source_image": str(image_path),
                "filename": filename,
                "frame_index": frame,
                "track_uid": uid,
                "team": identity["team"],
                "jersey_number": identity["jersey_number"],
                "bbox_original": bbox,
                "bbox_crop": [x1, y1, x2, y2],
                "verification_method": identity["verification_method"],
            }
        )

    OUTPUT.mkdir(parents=True)

    for item in planned:
        with Image.open(item["source_image"]) as image:
            crop = image.convert("RGB").crop(tuple(item["bbox_crop"]))

        crop.save(OUTPUT / item["filename"])

        print(f"Saved: {item['filename']} ({crop.width}x{crop.height})")

    manifest = OUTPUT / "appearance_reference_manifest.json"

    manifest.write_text(json.dumps(planned, indent=2) + "\n")

    print("\nEXPERIMENT 07B — APPEARANCE EXTRACTION")
    print("-" * 60)
    print("Verified observations:", len(verified))
    print("Crops generated:", len(planned))
    print("Manifest:", manifest)
    print("Original frames unchanged.")
    print("Stage 6D3 tracking data unchanged.")


if __name__ == "__main__":
    main()
