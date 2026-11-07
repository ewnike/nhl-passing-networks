#!/usr/bin/env python3
"""Phase 02 — G01 video/identity integration preflight.

Read-only validation of Experiment 07E5 observations against
the existing audio-enabled FiftyOne video pilot.
"""

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib

import cv2
import fiftyone as fo

SOURCE_DATASET = "swiss_nl_g01_identity_review_consolidated_v1"
VIDEO_DATASET = "swiss_nl_g01_video_review_audio_v1"
TARGET_DATASET = "swiss_nl_g01_video_identity_integrated_07e5_v1"

EXPECTED_OBSERVATIONS = 330
EXPECTED_VERIFIED = 124
EXPECTED_UNVERIFIED = 206
EXPECTED_FRAMES = 750
EXPECTED_FPS = 25.0
EXPECTED_SIZE = (1920, 1080)


def sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args()

    print("PHASE 02 — G01 VIDEO IDENTITY INTEGRATION PREFLIGHT")
    print("=" * 72)

    if fo.dataset_exists(TARGET_DATASET):
        raise SystemExit(
            f"STOP — Target dataset already exists: {TARGET_DATASET}"
        )

    identity = fo.load_dataset(SOURCE_DATASET)
    video_dataset = fo.load_dataset(VIDEO_DATASET)

    if len(video_dataset) != 1:
        raise SystemExit("STOP — Expected one video sample")

    video = video_dataset.first()

    if not Path(video.filepath).is_file():
        raise SystemExit("STOP — Video file missing")

    cap = cv2.VideoCapture(video.filepath)

    if not cap.isOpened():
        raise SystemExit("STOP — Cannot open video")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    cap.release()

    if (width, height) != EXPECTED_SIZE:
        raise SystemExit("STOP — Video dimensions mismatch")

    if abs(fps - EXPECTED_FPS) > 0.001:
        raise SystemExit("STOP — Video FPS mismatch")

    if frames != EXPECTED_FRAMES:
        raise SystemExit("STOP — Video frame count mismatch")

    records = [
        sample for sample in identity
        if sample["source_stage"] == "07E5"
    ]

    if len(records) != EXPECTED_OBSERVATIONS:
        raise SystemExit("STOP — Observation count mismatch")

    statuses = Counter(
        sample["identity_status"] for sample in records
    )

    if statuses != {
        "verified": EXPECTED_VERIFIED,
        "unverified": EXPECTED_UNVERIFIED,
    }:
        raise SystemExit(f"STOP — Status mismatch: {statuses}")

    seen = set()
    verified_tracks = defaultdict(set)
    missing = []
    invalid = []

    for sample in records:
        frame = sample["frame_index"]
        track = sample["track_uid"]
        key = (frame, track)

        if key in seen:
            raise SystemExit(f"STOP — Duplicate key: {key}")

        seen.add(key)

        if not isinstance(frame, int) or not 0 <= frame < frames:
            invalid.append(("frame", key))

        timestamp = sample["video_time_seconds"]
        expected_time = 330 + frame / fps

        if timestamp is None or abs(timestamp - expected_time) > 0.001:
            invalid.append(("timestamp", key))

        bbox = sample["bbox_original"]

        if (
            bbox is None
            or len(bbox) != 4
            or not (
                0 <= bbox[0] < bbox[2] <= width
                and 0 <= bbox[1] < bbox[3] <= height
            )
        ):
            invalid.append(("bbox", key))

        if not Path(sample["source_image"]).is_file():
            missing.append(sample["source_image"])

        if sample["identity_status"] == "verified":
            if not sample["verified_player_id"]:
                invalid.append(("missing_player_id", key))
            verified_tracks[track].add(sample["verified_player_id"])

    if missing or invalid:
        print("Missing source images:", len(missing))
        print("Invalid observations:", len(invalid))
        for item in invalid[:10]:
            print("INVALID:", item)
        raise SystemExit("STOP — Integration preflight failed")

    conflicts = {
        track: sorted(ids)
        for track, ids in verified_tracks.items()
        if len(ids) > 1
    }

    expected_conflict = {
        "E4_A:55": ["121606", "152416"]
    }

    if conflicts != expected_conflict:
        raise SystemExit(
            f"STOP — Unexpected identity conflicts: {conflicts}"
        )

    print("Source dataset:", SOURCE_DATASET)
    print("Video dataset:", VIDEO_DATASET)
    print("Target dataset:", TARGET_DATASET)
    print()
    print("Video:", Path(video.filepath).name)
    print("Video dimensions:", width, "x", height)
    print("Video FPS:", fps)
    print("Video frames:", frames)
    print()
    print("Observations:", len(records))
    print("Verified:", statuses["verified"])
    print("Unverified:", statuses["unverified"])
    print("Unique frame/track keys:", len(seen))
    print("Identity conflicts:", conflicts)
    print()
    print("Video SHA-256:", sha256(video.filepath))
    print("Original datasets modified: NO")
    print("Persistent dataset created: NO")
    print("Status: PASS — READY FOR PROTECTED INTEGRATION")


if __name__ == "__main__":
    main()
