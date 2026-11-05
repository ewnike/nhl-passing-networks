"""
Experiment 07G — Grey Jersey Enhancement Pilot

Compare original Fribourg player crops against three
preprocessing methods.

Read-only inputs. Never overwrites previous experiments.
"""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_07")

SOURCES = {
    "07E2": ROOT / "identity_reference/appearance_crops",
    "07E5": ROOT / "stage_07e4/identity_reference/appearance_crops",
    "07E8": ROOT / "stage_07e7/identity_reference/appearance_crops",
}

OUTPUT = ROOT / "grey_jersey_recognition_07g"
IMAGE_DIR = OUTPUT / "enhanced_images"

MAX_IMAGES = 24


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clahe(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    enhanced = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(4, 4),
    ).apply(l)

    return cv2.cvtColor(
        cv2.merge((enhanced, a, b)),
        cv2.COLOR_LAB2BGR,
    )


def sharpen(image):
    blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
    return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)


def denoise(image):
    return cv2.fastNlMeansDenoisingColored(image, None, 4, 4, 7, 21)


def main():

    print("EXPERIMENT 07G — GREY JERSEY ENHANCEMENT")
    print("=" * 75)

    if OUTPUT.exists():
        raise RuntimeError(f"Refusing overwrite: {OUTPUT}")

    records = []

    for stage, directory in SOURCES.items():
        manifest = directory / "appearance_reference_manifest.json"

        data = json.loads(manifest.read_text())

        for row in data:
            if row["team"] != "FRI":
                continue

            path = directory / row["filename"]

            if not path.is_file():
                raise FileNotFoundError(path)

            records.append(
                {
                    "stage": stage,
                    "player_id": row["player_id"],
                    "player_name": row["player_name"],
                    "jersey_number": row["jersey_number"],
                    "path": path,
                    "frame_index": row["frame_index"],
                    "track_uid": row["track_uid"],
                }
            )

    print("Available verified FRI crops:", len(records))

    # Deterministic selection across different players.
    selected = []
    counts = Counter()

    for row in sorted(
        records,
        key=lambda x: (
            str(x["player_id"]),
            x["stage"],
            int(x["frame_index"]),
        ),
    ):
        if counts[row["player_id"]] >= 3:
            continue

        selected.append(row)
        counts[row["player_id"]] += 1

        if len(selected) >= MAX_IMAGES:
            break

    IMAGE_DIR.mkdir(parents=True, exist_ok=False)

    manifest_rows = []
    tiles = []

    for index, row in enumerate(selected):
        image = cv2.imread(str(row["path"]))

        if image is None:
            raise RuntimeError(f"Cannot decode: {row['path']}")

        enhanced = clahe(image)

        variants = {
            "original": image,
            "clahe": enhanced,
            "clahe_sharpen": sharpen(enhanced),
            "clahe_denoise": denoise(enhanced),
        }

        tile_images = []

        for method, variant in variants.items():
            filename = f"{index:03d}_{row['stage']}_{row['player_id']}_{method}.png"

            path = IMAGE_DIR / filename

            if not cv2.imwrite(str(path), variant):
                raise RuntimeError(f"Write failed: {path}")

            manifest_rows.append(
                {
                    "source_stage": row["stage"],
                    "player_id": row["player_id"],
                    "player_name": row["player_name"],
                    "jersey_number": row["jersey_number"],
                    "frame_index": row["frame_index"],
                    "track_uid": row["track_uid"],
                    "method": method,
                    "source_path": str(row["path"]),
                    "source_sha256": sha256(row["path"]),
                    "output_path": str(path),
                    "output_sha256": sha256(path),
                }
            )

            rgb = cv2.cvtColor(variant, cv2.COLOR_BGR2RGB)

            pil = Image.fromarray(rgb)
            pil.thumbnail((240, 220))

            canvas = Image.new("RGB", (260, 260), "white")

            x = (260 - pil.width) // 2
            y = 10

            canvas.paste(pil, (x, y))

            draw = ImageDraw.Draw(canvas)

            draw.text(
                (10, 235),
                method,
                fill="black",
            )

            tile_images.append(canvas)

        tiles.append((row, tile_images))

    # Contact sheet: four processing variants per player.
    sheet = Image.new(
        "RGB",
        (4 * 260, len(tiles) * 290),
        "white",
    )

    draw = ImageDraw.Draw(sheet)

    for row_index, (row, images) in enumerate(tiles):
        y = row_index * 290

        draw.text(
            (10, y),
            f"{row['player_name']} "
            f"#{row['jersey_number']} "
            f"| {row['stage']} "
            f"| frame {row['frame_index']}",
            fill="black",
        )

        for col, tile in enumerate(images):
            sheet.paste(
                tile,
                (col * 260, y + 25),
            )

    sheet_path = OUTPUT / "grey_jersey_comparison.jpg"
    sheet.save(sheet_path, quality=95)

    csv_path = OUTPUT / "enhancement_manifest.csv"

    with csv_path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(manifest_rows[0]),
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary = {
        "experiment": "07G",
        "phase": "grey_jersey_enhancement_pilot",
        "selected_crops": len(selected),
        "players": len(counts),
        "methods": list(variants),
        "comparison_sheet": str(sheet_path),
        "comparison_sheet_sha256": sha256(sheet_path),
        "manifest": str(csv_path),
        "manifest_sha256": sha256(csv_path),
        "original_artifacts_modified": False,
    }

    summary_path = OUTPUT / "experiment_summary.json"

    with summary_path.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    print()
    print("EXPERIMENT 07G — SUMMARY")
    print("=" * 75)
    print("Images:", len(selected))
    print("Players:", len(counts))
    print("Variants:", len(manifest_rows))
    print("Contact sheet:", sheet_path)
    print("Summary SHA-256:", sha256(summary_path))
    print("Status: PASS")


if __name__ == "__main__":
    main()
