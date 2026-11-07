#!/usr/bin/env python3
"""Create a versioned G01 FiftyOne video/identity integration dataset.

Existing datasets and source files are read-only.
"""

from collections import Counter, defaultdict
from pathlib import Path
import hashlib

import cv2
import fiftyone as fo

SOURCE_DATASET = "swiss_nl_g01_identity_review_consolidated_v1"
VIDEO_DATASET = "swiss_nl_g01_video_review_audio_v1"
TARGET_DATASET = "swiss_nl_g01_video_identity_integrated_07e5_v1"

EXPECTED_VIDEO_SHA = (
    "4ac8237557aded0e1c7131f24582690b20469c52ee3114d97fa650a90acaceb7"
)

EXPECTED_CONFLICT = {
    "E4_A:55": ["121606", "152416"]
}

WIDTH = 1920
HEIGHT = 1080
FPS = 25.0
FRAMES = 750


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    print("PHASE 02 — G01 VIDEO IDENTITY INTEGRATION")
    print("=" * 72)

    if fo.dataset_exists(TARGET_DATASET):
        raise SystemExit(
            f"STOP — Dataset already exists: {TARGET_DATASET}"
        )

    identity = fo.load_dataset(SOURCE_DATASET)
    video_dataset = fo.load_dataset(VIDEO_DATASET)

    if len(video_dataset) != 1:
        raise SystemExit("STOP — Expected one source video sample")

    source_video = video_dataset.first()
    video_path = Path(source_video.filepath)

    if sha256(video_path) != EXPECTED_VIDEO_SHA:
        raise SystemExit("STOP — Source video SHA mismatch")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit("STOP — Cannot open source video")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if (width, height, frames) != (WIDTH, HEIGHT, FRAMES):
        raise SystemExit("STOP — Video geometry mismatch")

    if abs(fps - FPS) > 0.001:
        raise SystemExit("STOP — Video FPS mismatch")

    records = [
        s for s in identity
        if s["source_stage"] == "07E5"
    ]

    statuses = Counter(s["identity_status"] for s in records)

    if len(records) != 330 or statuses != {
        "verified": 124,
        "unverified": 206,
    }:
        raise SystemExit("STOP — Observation counts mismatch")

    keys = set()
    track_ids = defaultdict(set)
    by_frame = defaultdict(list)

    for s in records:
        frame = int(s["frame_index"])
        track = str(s["track_uid"])
        key = (frame, track)

        if key in keys:
            raise SystemExit(f"STOP — Duplicate key: {key}")
        keys.add(key)

        if not 0 <= frame < FRAMES:
            raise SystemExit(f"STOP — Invalid frame: {frame}")

        timestamp = s["video_time_seconds"]
        if timestamp is None or abs(timestamp - (330 + frame / FPS)) > 0.001:
            raise SystemExit(f"STOP — Timestamp mismatch: {key}")

        box = s["bbox_original"]
        if box is None or len(box) != 4:
            raise SystemExit(f"STOP — Invalid box: {key}")

        x1, y1, x2, y2 = map(float, box)
        if not (0 <= x1 < x2 <= WIDTH and 0 <= y1 < y2 <= HEIGHT):
            raise SystemExit(f"STOP — Box outside video: {key}")

        if not Path(s["source_image"]).is_file():
            raise SystemExit(f"STOP — Missing source image: {key}")

        if s["identity_status"] == "verified":
            if not s["verified_player_id"]:
                raise SystemExit(f"STOP — Missing verified ID: {key}")
            track_ids[track].add(str(s["verified_player_id"]))

        by_frame[frame].append(s)

    conflicts = {
        track: sorted(ids)
        for track, ids in track_ids.items()
        if len(ids) > 1
    }

    if conflicts != EXPECTED_CONFLICT:
        raise SystemExit(f"STOP — Unexpected conflicts: {conflicts}")

    print("Preflight: PASS")
    print("Observations:", len(records))
    print("Annotated frames:", len(by_frame))
    print("Known identity conflicts:", conflicts)

    # Create only after all source validation has passed.
    target = fo.Dataset(TARGET_DATASET)
    target.persistent = True

    sample = fo.Sample(filepath=str(video_path.resolve()))

    sample["game_id"] = "G01"
    sample["period"] = 1
    sample["source_start_seconds"] = 330.0
    sample["source_end_seconds"] = 360.0
    sample["source_start_frame"] = 8250
    sample["source_end_frame_exclusive"] = 9000
    sample["source_fps"] = FPS
    sample["review_status"] = "integration_pilot"
    sample["identity_source_dataset"] = SOURCE_DATASET
    sample["identity_source_stage"] = "07E5"
    sample["identity_conflicted_tracks"] = sorted(conflicts)
    sample["video_sha256"] = EXPECTED_VIDEO_SHA

    target.add_sample(sample)

    # FiftyOne video frame numbers are one-based.
    for frame_index in sorted(by_frame):
        detections = []

        for s in sorted(
            by_frame[frame_index],
            key=lambda item: str(item["track_uid"])
        ):
            x1, y1, x2, y2 = map(float, s["bbox_original"])

            normalized_box = [
                x1 / WIDTH,
                y1 / HEIGHT,
                (x2 - x1) / WIDTH,
                (y2 - y1) / HEIGHT,
            ]

            verified = s["identity_status"] == "verified"
            track = str(s["track_uid"])

            if verified:
                label = (
                    f"{s['verified_player_name']} "
                    f"#{s['verified_jersey_number']}"
                )
            else:
                label = "Unverified"

            detection = fo.Detection(
                label=label,
                bounding_box=normalized_box,
                index=track,
                track_uid=track,
                identity_status=s["identity_status"],
                verified_player_id=(
                    str(s["verified_player_id"]) if verified else None
                ),
                verified_player_name=(
                    str(s["verified_player_name"]) if verified else None
                ),
                verified_team=(
                    str(s["verified_team"]) if verified else None
                ),
                verified_jersey_number=(
                    int(s["verified_jersey_number"]) if verified else None
                ),
                identity_conflict=(track in conflicts),
                source_stage="07E5",
                source_frame_index=frame_index,
                source_time_seconds=float(s["video_time_seconds"]),
                source_sample_id=str(s.id),
                source_image=str(s["source_image"]),
                bbox_original=list(s["bbox_original"]),
            )

            detections.append(detection)

        sample.frames[frame_index + 1] = fo.Frame(
            player_detections=fo.Detections(
                detections=detections
            )
        )

    sample.save()

    target.info.update({
        "source_identity_dataset": SOURCE_DATASET,
        "source_video_dataset": VIDEO_DATASET,
        "source_stage": "07E5",
        "video_sha256": EXPECTED_VIDEO_SHA,
        "expected_observations": 330,
        "expected_verified": 124,
        "expected_unverified": 206,
        "identity_conflicts": conflicts,
        "frame_numbering": "FiftyOne one-based; source clip zero-based",
    })
    target.save()

    # Independently inspect the persisted annotations.
    reloaded = fo.load_dataset(TARGET_DATASET)
    restored = reloaded.first()

    annotated_frames = 0
    total = 0
    verified_total = 0
    conflict_total = 0

    for frame_number, frame in restored.frames.items():
        if frame.player_detections is None:
            continue

        annotated_frames += 1

        for detection in frame.player_detections.detections:
            total += 1

            if detection.identity_status == "verified":
                verified_total += 1

            if detection.identity_conflict:
                conflict_total += 1

    if (
        total != 330
        or verified_total != 124
        or annotated_frames != 261
    ):
        raise RuntimeError(
            "STOP — Post-import validation mismatch: "
            f"frames={annotated_frames}, "
            f"observations={total}, "
            f"verified={verified_total}"
        )

    print()
    print("G01 FIFTYONE INTEGRATION VALIDATION")
    print("=" * 72)
    print("Dataset:", TARGET_DATASET)
    print("Video samples:", len(reloaded))
    print("Annotated frames:", annotated_frames)
    print("Detections:", total)
    print("Verified identities:", verified_total)
    print("Unverified observations:", total - verified_total)
    print("Identity-conflicted detections:", conflict_total)
    print("Original datasets unchanged: YES")
    print("Status: PASS — INTEGRATED DATASET CREATED")


if __name__ == "__main__":
    main()
