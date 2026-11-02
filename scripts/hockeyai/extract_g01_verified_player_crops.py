#!/usr/bin/env python3
"""
Experiment 07C — Incremental Verified Player Appearance Extraction

Extract human-verified player crops using Stage 6D3 tracking boxes.

Features:
- Official SIHF player identity lookup
- Incremental extraction
- Existing crop protection
- Manifest consistency checks
- Dry-run validation
- Atomic manifest replacement

Original frames, tracking observations, and identity CSVs
are never modified.

Run from the nhl-passing-networks repository root.
"""

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path("local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01")

BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "frames/P1_experiment_06d_300_330"
)

TRACKING = (
    ROOT / "experiment_06/stage_6d/camera_cut_aware_baseline/track_observations.csv"
)

REFERENCE = ROOT / "experiment_07/identity_reference"

IDENTITIES = REFERENCE / "verified_player_observations.csv"

ROSTER = REFERENCE / "g01_official_player_dictionary.csv"

OUTPUT = REFERENCE / "appearance_crops"

MANIFEST = OUTPUT / "appearance_reference_manifest.json"

TEAM_SIDE = {
    "HCD": "home",
    "FRI": "away",
}


def read_csv(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def identity_key(item):
    return (
        int(item["frame_index"]),
        item["track_uid"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing files",
    )
    args = parser.parse_args()

    verified = read_csv(IDENTITIES)
    tracking_rows = read_csv(TRACKING)
    roster_rows = read_csv(ROSTER)

    if not verified:
        raise ValueError("No verified observations found.")

    if not roster_rows:
        raise ValueError("Official player dictionary is empty.")

    tracking = {}

    for row in tracking_rows:
        key = identity_key(row)

        if key in tracking:
            raise ValueError(f"Duplicate tracking observation: {key}")

        tracking[key] = row

    roster = {}

    for player in roster_rows:
        key = (
            player["team_side"],
            str(player["jersey_number"]).strip(),
        )

        if key in roster:
            raise ValueError(f"Duplicate roster identity: {key}")

        roster[key] = player

    existing = []

    if MANIFEST.exists():
        with MANIFEST.open() as file:
            existing = json.load(file)

        if not isinstance(existing, list):
            raise ValueError("Manifest must be a JSON list.")

    elif OUTPUT.exists() and any(OUTPUT.glob("*.png")):
        raise ValueError("Existing crops found without a manifest.")

    existing_by_key = {}
    existing_names = set()

    for item in existing:
        key = identity_key(item)
        filename = item["filename"]

        if key in existing_by_key:
            raise ValueError(f"Duplicate manifest observation: {key}")

        if filename in existing_names:
            raise ValueError(f"Duplicate manifest filename: {filename}")

        existing_by_key[key] = item
        existing_names.add(filename)

        if not (OUTPUT / filename).is_file():
            raise FileNotFoundError(f"Manifest crop missing: {filename}")

    planned = []
    seen = set()

    for identity in verified:
        key = identity_key(identity)

        if key in seen:
            raise ValueError(f"Duplicate verified observation: {key}")

        seen.add(key)

        frame, uid = key

        if identity["verification_method"] != "human_visual_review":
            raise ValueError(f"Unverified identity: {key}")

        team = identity["team"]
        jersey = identity["jersey_number"]

        roster_key = (
            TEAM_SIDE[team],
            jersey,
        )

        player = roster.get(roster_key)

        if player is None:
            raise ValueError(f"No official roster match: {roster_key}")

        if key not in tracking:
            raise ValueError(f"Missing tracking observation: {key}")

        image_path = BASE / f"frame_{frame:04d}.jpg"

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        row = tracking[key]

        bbox = [float(row[column]) for column in ("x1", "y1", "x2", "y2")]

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
            f"{team}_{jersey}_"
            f"frame_{frame:04d}_"
            f"{uid.replace(':', '-')}.png"
        )

        item = {
            "source_image": str(image_path),
            "filename": filename,
            "frame_index": frame,
            "track_uid": uid,
            "team": team,
            "jersey_number": jersey,
            "bbox_original": bbox,
            "bbox_crop": [x1, y1, x2, y2],
            "verification_method": identity["verification_method"],
            "player_id": str(player["player_id"]),
            "player_name": player["player_name"],
        }

        if key in existing_by_key:
            previous = existing_by_key[key]

            for field in (
                "filename",
                "team",
                "jersey_number",
                "bbox_original",
                "bbox_crop",
                "source_image",
                "verification_method",
            ):
                if previous[field] != item[field]:
                    raise ValueError(f"Manifest conflict: {key}, field={field}")

            if "player_id" in previous:
                if previous["player_id"] != item["player_id"]:
                    raise ValueError(f"Player identity conflict: {key}")

            print(f"EXISTS: {filename} | player_id={item['player_id']}")

        else:
            if filename in existing_names:
                raise ValueError(f"Filename collision: {filename}")

            if (OUTPUT / filename).exists():
                raise FileExistsError(f"Unregistered crop already exists: {filename}")

            planned.append(item)

            print(
                f"NEW: {filename} "
                f"| {item['player_name']} "
                f"| player_id={item['player_id']}"
            )

    # Refuse to silently discard existing manifest records.
    missing_verified = set(existing_by_key) - seen

    if missing_verified:
        raise ValueError(
            "Existing manifest records absent from verified CSV: "
            f"{sorted(missing_verified)}"
        )

    # Build updated manifest using the current verified observations.
    updated = []

    planned_by_key = {identity_key(item): item for item in planned}

    for identity in verified:
        key = identity_key(identity)

        if key in planned_by_key:
            updated.append(planned_by_key[key])
        else:
            previous = dict(existing_by_key[key])

            player = roster[
                (
                    TEAM_SIDE[identity["team"]],
                    identity["jersey_number"],
                )
            ]

            previous["player_id"] = str(player["player_id"])
            previous["player_name"] = player["player_name"]

            updated.append(previous)

    print("\nEXPERIMENT 07C — APPEARANCE EXTRACTION")
    print("-" * 60)
    print("Verified observations:", len(verified))
    print("Existing crops:", len(existing))
    print("New crops planned:", len(planned))
    print("Updated manifest records:", len(updated))

    if args.dry_run:
        print("\nDRY RUN COMPLETE — No files modified.")
        return

    OUTPUT.mkdir(parents=True, exist_ok=True)

    created = []

    try:
        for item in planned:
            destination = OUTPUT / item["filename"]

            with Image.open(item["source_image"]) as image:
                crop = image.convert("RGB").crop(tuple(item["bbox_crop"]))

            # Exclusive creation: never overwrite an existing crop.
            with destination.open("xb") as file:
                crop.save(file, format="PNG")

            created.append(destination)

            print(f"Saved: {item['filename']} ({crop.width}x{crop.height})")

        # Write manifest to a temporary file first.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=OUTPUT,
            prefix=".appearance_manifest_",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)

            json.dump(updated, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, MANIFEST)

    except Exception:
        # Roll back only crops created by this run.
        for path in created:
            path.unlink(missing_ok=True)

        raise

    print("\nExtraction complete.")
    print("New crops generated:", len(created))
    print("Manifest:", MANIFEST)
    print("Original frames unchanged.")
    print("Stage 6D3 tracking data unchanged.")


if __name__ == "__main__":
    main()
