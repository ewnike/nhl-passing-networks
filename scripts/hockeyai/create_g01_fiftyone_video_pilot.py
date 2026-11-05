"""
Phase 02 — G01 FiftyOne Video Review Pilot

Creates a 30-second video clip from G01 Period 1
and registers it in a separate persistent FiftyOne dataset.

Original video and existing datasets remain unchanged.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import fiftyone as fo

ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

SOURCE = ROOT / "periods/G01_P1.mp4"

OUTPUT = ROOT / "experiment_07/phase_02_fiftyone_video_pilot"

CLIP = OUTPUT / "G01_P1_330_360.mp4"

MANIFEST = OUTPUT / "video_pilot_manifest.json"

DATASET_NAME = "swiss_nl_g01_video_review_pilot_v1"

START_SECONDS = 330
DURATION_SECONDS = 30


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def main():

    print("PHASE 02 — G01 FIFTYONE VIDEO PILOT")
    print("=" * 75)

    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    if OUTPUT.exists():
        raise RuntimeError(f"Refusing overwrite: {OUTPUT}")

    if fo.dataset_exists(DATASET_NAME):
        raise RuntimeError(f"Dataset already exists: {DATASET_NAME}")

    cap = cv2.VideoCapture(str(SOURCE))

    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    cap.release()

    start_frame = round(START_SECONDS * fps)
    end_frame = round((START_SECONDS + DURATION_SECONDS) * fps)

    if end_frame > total_frames:
        raise RuntimeError("Clip exceeds source duration")

    OUTPUT.mkdir(parents=True, exist_ok=False)

    # Re-encode to ensure predictable playback.
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        str(START_SECONDS),
        "-i",
        str(SOURCE),
        "-t",
        str(DURATION_SECONDS),
        "-map",
        "0:v:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(CLIP),
    ]

    subprocess.run(command, check=True)

    if not CLIP.is_file():
        raise RuntimeError("Clip extraction failed")

    clip_cap = cv2.VideoCapture(str(CLIP))

    if not clip_cap.isOpened():
        raise RuntimeError("Cannot decode extracted clip")

    clip_frames = int(clip_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    clip_fps = clip_cap.get(cv2.CAP_PROP_FPS)

    clip_cap.release()

    if clip_frames == 0:
        raise RuntimeError("Extracted clip has no frames")

    dataset = fo.Dataset(DATASET_NAME)
    dataset.persistent = True

    sample = fo.Sample(filepath=str(CLIP.resolve()))

    sample["game_id"] = "G01"
    sample["period"] = 1
    sample["source_video"] = str(SOURCE.resolve())
    sample["source_start_seconds"] = START_SECONDS
    sample["source_end_seconds"] = START_SECONDS + DURATION_SECONDS
    sample["source_start_frame"] = start_frame
    sample["source_end_frame_exclusive"] = end_frame
    sample["source_fps"] = fps
    sample["clip_fps"] = clip_fps
    sample["clip_frames"] = clip_frames
    sample["review_status"] = "unreviewed"

    dataset.add_sample(sample)

    manifest = {
        "phase": "02",
        "experiment": "G01_FIFTYONE_VIDEO_PILOT",
        "dataset_name": DATASET_NAME,
        "source_video": str(SOURCE),
        "source_video_sha256": sha256(SOURCE),
        "clip": str(CLIP),
        "clip_sha256": sha256(CLIP),
        "source_start_seconds": START_SECONDS,
        "source_end_seconds": START_SECONDS + DURATION_SECONDS,
        "source_start_frame": start_frame,
        "source_end_frame_exclusive": end_frame,
        "source_fps": fps,
        "clip_fps": clip_fps,
        "clip_frames": clip_frames,
        "original_artifacts_modified": False,
    }

    with MANIFEST.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print("Dataset:", dataset.name)
    print("Samples:", len(dataset))
    print("Clip frames:", clip_frames)
    print("Clip:", CLIP)
    print("Manifest:", MANIFEST)
    print("Manifest SHA-256:", sha256(MANIFEST))
    print("Status: PASS")


if __name__ == "__main__":
    main()
