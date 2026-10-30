#!/usr/bin/env python3

"""
Experiment 06 — Stage 6B
HockeyAI + BoT-SORT Player Tracking Baseline

Tracks player and goalie detections across 75 consecutive
G01 broadcast frames using Ultralytics BoT-SORT.

Does not modify source images, model weights,
Stage 6A detections, or Experiment 04/05 artifacts.

Outputs:
    tracks.json
    track_observations.csv
    track_summary.csv
    tracking_metadata.json
    annotated_frames/
"""

import csv
import json
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import ultralytics
from ultralytics import YOLO

BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

MODEL = Path("local_artifacts/models/hockeyai/HockeyAI_model_weight.pt")

# FRAMES = BASE / "frames/P1_dense_09_12"
FRAMES = BASE / "frames/P1_experiment_06d_300_330"


OUTPUT = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_06/stage_6d/full_broadcast_baseline"
)

FPS = 25.0
CONFIDENCE = 0.15
IMAGE_SIZE = 1280
DEVICE = "cpu"

TRACKED_CLASSES = [3, 4]

TRACKER = Path(ultralytics.__file__).parent / "cfg/trackers/botsort.yaml"

CAMERA_CUTS = [
    {
        "from_frame": 132,
        "to_frame": 133,
        "clip_time_seconds": 5.32,
        "video_time_seconds": 305.32,
        "transition": "wide_to_close",
    },
    {
        "from_frame": 270,
        "to_frame": 271,
        "clip_time_seconds": 10.84,
        "video_time_seconds": 310.84,
        "transition": "close_to_wide",
    },
]


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main():

    if not MODEL.is_file():
        raise FileNotFoundError(MODEL)

    if not TRACKER.is_file():
        raise FileNotFoundError(TRACKER)

    frames = sorted(FRAMES.glob("frame_*.jpg"))

    if len(frames) != 750:
        raise RuntimeError(f"Expected 750 frames, found {len(frames)}")
    numbers = [int(path.stem.split("_")[-1]) for path in frames]

    if numbers != list(range(750)):
        raise RuntimeError("Frame sequence is incomplete or unordered")

    if OUTPUT.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUTPUT}\n"
            "Use a new output directory for another run."
        )

    OUTPUT.mkdir(parents=True)
    annotated_dir = OUTPUT / "annotated_frames"
    annotated_dir.mkdir()

    shutil.copy2(
        TRACKER,
        OUTPUT / "botsort_config.yaml",
    )

    model = YOLO(str(MODEL))

    frame_records = []
    observations = []
    tracks = defaultdict(list)

    start = time.perf_counter()

    print("\nEXPERIMENT 06 — STAGE 6D2")
    # print("BOt-SORT PLAYER TRACKING")
    print("BoT-SORT PLAYER TRACKING")
    print("-" * 65)

    for frame_index, frame_path in enumerate(frames):
        image = cv2.imread(str(frame_path))

        if image is None:
            raise RuntimeError(f"Cannot read {frame_path}")

        result = model.track(
            source=image,
            persist=True,
            tracker=str(TRACKER),
            classes=TRACKED_CLASSES,
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            device=DEVICE,
            save=False,
            verbose=False,
        )[0]

        frame_detections = []

        boxes = result.boxes

        if boxes is not None and boxes.id is not None:
            for box in boxes:
                track_id = int(box.id.item())
                class_id = int(box.cls.item())
                confidence = float(box.conf.item())

                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]

                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                observation = {
                    "frame": frame_path.name,
                    "frame_index": frame_index,
                    "time_seconds": frame_index / FPS,
                    "track_id": track_id,
                    "class_id": class_id,
                    "class_name": model.names[class_id],
                    "confidence": confidence,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "center_x": center_x,
                    "center_y": center_y,
                    "bottom_center_x": center_x,
                    "bottom_center_y": y2,
                }

                frame_detections.append(observation)
                observations.append(observation)
                tracks[track_id].append(observation)

        frame_records.append(
            {
                "frame": frame_path.name,
                "frame_index": frame_index,
                "time_seconds": frame_index / FPS,
                "tracks": frame_detections,
            }
        )

        annotated = result.plot()

        output_path = annotated_dir / frame_path.name

        if not cv2.imwrite(str(output_path), annotated):
            raise RuntimeError(f"Cannot save {output_path}")

        print(
            # f"[{frame_index + 1:02d}/75] "
            f"[{frame_index + 1:03d}/{len(frames)}] "
            f"{frame_path.name}: "
            f"{len(frame_detections)} active observations"
        )

    elapsed = time.perf_counter() - start

    track_summaries = []

    for track_id, items in sorted(tracks.items()):
        observed_frames = sorted({item["frame_index"] for item in items})

        first = observed_frames[0]
        last = observed_frames[-1]

        span = last - first + 1
        missing = span - len(observed_frames)

        classes = Counter(item["class_name"] for item in items)

        track_summaries.append(
            {
                "track_id": track_id,
                "first_frame": first,
                "last_frame": last,
                "span_frames": span,
                "observed_frames": len(observed_frames),
                "missing_frames": missing,
                "coverage_ratio": len(observed_frames) / span,
                "classes": ",".join(sorted(classes)),
            }
        )

    OUTPUT.joinpath("tracks.json").write_text(
        json.dumps(frame_records, indent=2) + "\n"
    )

    write_csv(
        OUTPUT / "track_observations.csv",
        observations,
        [
            "frame",
            "frame_index",
            "time_seconds",
            "track_id",
            "class_id",
            "class_name",
            "confidence",
            "x1",
            "y1",
            "x2",
            "y2",
            "center_x",
            "center_y",
            "bottom_center_x",
            "bottom_center_y",
        ],
    )

    write_csv(
        OUTPUT / "track_summary.csv",
        track_summaries,
        [
            "track_id",
            "first_frame",
            "last_frame",
            "span_frames",
            "observed_frames",
            "missing_frames",
            "coverage_ratio",
            "classes",
        ],
    )

    metadata = {
        "experiment": "06",
        "stage": "6D2",
        "ultralytics_version": ultralytics.__version__,
        "model": str(MODEL),
        "tracker": "botsort",
        "tracker_config": "botsort_config.yaml",
        "tracked_classes": TRACKED_CLASSES,
        "confidence_threshold": CONFIDENCE,
        "image_size": IMAGE_SIZE,
        "fps": FPS,
        "device": DEVICE,
        "frames_processed": len(frames),
        "total_track_observations": len(observations),
        "unique_track_ids": len(tracks),
        "elapsed_seconds": elapsed,
        "camera_cuts": CAMERA_CUTS,
        "camera_cut_resets": False,
        "source_video_start_seconds": 300.0,
        "source_video_end_seconds": 330.0,
    }

    OUTPUT.joinpath("tracking_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )

    print("\nEXPERIMENT 06 — STAGE 6D2 SUMMARY")
    print("-" * 65)

    print("Frames processed:", len(frames))
    print("Track observations:", len(observations))
    print("Unique track IDs:", len(tracks))
    print("Elapsed seconds:", f"{elapsed:.2f}")

    if track_summaries:
        print("\nLongest tracks:")

        longest = sorted(
            track_summaries,
            key=lambda row: row["observed_frames"],
            reverse=True,
        )[:10]

        for row in longest:
            print(
                f"Track {row['track_id']:3d}: "
                f"observed={row['observed_frames']:2d}, "
                f"span={row['span_frames']:2d}, "
                f"missing={row['missing_frames']:2d}, "
                f"coverage={row['coverage_ratio']:.3f}"
            )

    print("\nSaved:", OUTPUT)
    print("Original source frames unchanged.")
    print("Stage 6D2 detections unchanged.")


if __name__ == "__main__":
    main()
