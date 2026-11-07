#!/usr/bin/env python3
"""Generate G07 period-boundary inspection contact sheets."""

from pathlib import Path
from PIL import Image, ImageDraw
from decimal import Decimal
import hashlib
import io
import json
import math
import re
import subprocess

ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G07")

PLAN = ROOT / "metadata/G07_resolution_recovery_plan_v1.json"
PLAYLIST = ROOT / "metadata/G07_1080p_playlist.m3u8"

SOURCE = ROOT / "source_segments"
RECEIPTS_1080 = ROOT / "metadata/acquisition_1080p/receipts"
RECEIPTS_RECOVERY = ROOT / "metadata/recovery_v1/receipts"

OUTPUT = ROOT / "inspection/period_boundaries_v1"

EXPECTED_PLAN_SHA = (
    "17de74260d966847d8aeb6197b7e6b91601d5682f85f04da9fe4b0ffbecbf9d4"
)

EXPECTED_PLAYLIST_SHA = (
    "bd0bd66a2656b7c28e1fc056029cd4027d5145fb4f64ad7ce6d1bcb386a8d381"
)

BOUNDARIES = {
    "P1_start": 491,
    "P1_end": 826,
    "P2_start": 1005,
    "P2_end": 1317,
    "P3_start": 1495,
    "P3_end": 1880,
    "OT1_start": 2055,
    "OT1_end": 2145,
}

OFFSETS = (1, 3, 5)

THUMB_W = 480
THUMB_H = 270
LABEL_H = 55
COLUMNS = 3
PAD = 12


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


if sha256(PLAN) != EXPECTED_PLAN_SHA:
    raise RuntimeError("Recovery plan SHA mismatch")

if sha256(PLAYLIST) != EXPECTED_PLAYLIST_SHA:
    raise RuntimeError("Playlist SHA mismatch")

plan = json.loads(PLAN.read_text())

recovery = {
    int(record["sequence"]): record["selected"]["rendition"]
    for record in plan["records"]
}

segments = []
pending_duration = None

for line in PLAYLIST.read_text().splitlines():
    line = line.strip()

    if line.startswith("#EXTINF:"):
        pending_duration = Decimal(
            line.split(":", 1)[1].split(",", 1)[0]
        )

    elif line and not line.startswith("#"):
        match = re.search(r"_(\d+)\.ts$", line)

        if not match or pending_duration is None:
            raise RuntimeError("Invalid playlist segment")

        segments.append((int(match.group(1)), pending_duration))
        pending_duration = None

if [seq for seq, _ in segments] != list(range(323, 2711)):
    raise RuntimeError("Unexpected playlist sequence range")

starts = {}
elapsed = Decimal("0")

for seq, duration in segments:
    starts[seq] = elapsed
    elapsed += duration

if elapsed != Decimal("14316"):
    raise RuntimeError("Unexpected playlist duration")


def timestamp(seconds):
    total = float(seconds)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    remainder = total % 60

    return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"


def resolve(seq):
    rendition = recovery.get(seq, "1080p")

    if rendition == "1080p":
        receipt_path = RECEIPTS_1080 / f"{seq}.json"
    else:
        receipt_path = (
            RECEIPTS_RECOVERY / rendition / f"{seq}.json"
        )

    receipt = json.loads(receipt_path.read_text())

    if receipt["sequence"] != seq:
        raise RuntimeError(f"Receipt sequence mismatch: {seq}")

    if receipt["rendition"] != rendition:
        raise RuntimeError(f"Receipt rendition mismatch: {seq}")

    path = SOURCE / rendition / receipt["filename"]

    if sha256(path) != receipt["sha256"]:
        raise RuntimeError(f"Source SHA mismatch: {seq}")

    return path, rendition


def extract_frame(path, offset):
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-i", str(path),
        "-ss", str(offset),
        "-frames:v", "1",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        check=True,
    )

    if not result.stdout:
        raise RuntimeError("Frame extraction failed")

    return Image.open(
        io.BytesIO(result.stdout)
    ).convert("RGB")


def main():
    print("G07 — PERIOD BOUNDARY CONTACT SHEETS")
    print("=" * 72)

    for name in BOUNDARIES:
        destination = OUTPUT / f"G07_{name}_v1.jpg"

        if destination.exists():
            raise RuntimeError(
                f"STOP — Refusing overwrite: {destination}"
            )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    total_frames = 0

    for name, center in BOUNDARIES.items():
        samples = [
            (seq, offset)
            for seq in range(center - 5, center + 6)
            for offset in OFFSETS
        ]

        rows = math.ceil(len(samples) / COLUMNS)

        cell_w = THUMB_W + PAD
        cell_h = THUMB_H + LABEL_H + PAD

        sheet = Image.new(
            "RGB",
            (
                COLUMNS * cell_w + PAD,
                rows * cell_h + PAD,
            ),
            "white",
        )

        draw = ImageDraw.Draw(sheet)

        print(f"Generating {name}...", flush=True)

        for index, (seq, offset) in enumerate(samples):
            path, rendition = resolve(seq)

            frame = extract_frame(path, offset)
            frame.thumbnail((THUMB_W, THUMB_H))

            col = index % COLUMNS
            row = index // COLUMNS

            x = PAD + col * cell_w
            y = PAD + row * cell_h

            sheet.paste(frame, (x, y))

            playback = starts[seq] + Decimal(offset)

            draw.text(
                (x + 5, y + THUMB_H + 5),
                f"Seq {seq} +{offset}s | {timestamp(playback)}",
                fill="black",
            )

            draw.text(
                (x + 5, y + THUMB_H + 28),
                f"Source: {rendition}",
                fill="black",
            )

            total_frames += 1

        destination = OUTPUT / f"G07_{name}_v1.jpg"

        with destination.open("xb") as f:
            sheet.save(f, format="JPEG", quality=92)

        print("  Frames:", len(samples))
        print("  SHA-256:", sha256(destination))

    print()
    print("Total inspection frames:", total_frames)
    print("Contact sheets:", len(BOUNDARIES))
    print("Original artifacts unchanged: YES")
    print("Status: PASS — G07 BOUNDARY SHEETS CREATED")


if __name__ == "__main__":
    main()
