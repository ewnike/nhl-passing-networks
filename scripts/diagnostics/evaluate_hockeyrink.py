"""Evaluate HockeyRink landmark confidence on sampled video frames."""

from pathlib import Path

import cv2
from ultralytics import YOLO


VIDEO_PATH = Path("local_artifacts/videos/beta/clip_001_wide.mp4")
MODEL_PATH = Path("local_artifacts/models/hockeyrink/HockeyRink.pt")


def read_frame(
    capture: cv2.VideoCapture,
    frame_number: int,
):
    """Read a specific frame from an open video capture."""
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    success, frame = capture.read()

    if not success:
        raise RuntimeError(f"Could not read frame {frame_number}")

    return frame


def analyze_frame(
    model: YOLO,
    frame,
    frame_number: int,
) -> dict[str, int | float]:
    """Run HockeyRink on one frame and summarize landmark confidence."""
    results = model(
        frame,
        imgsz=1920,
        verbose=False,
    )

    result = results[0]

    if len(result.boxes) == 0:
        return {
            "frame": frame_number,
            "rink_conf": 0.0,
            "kp_025": 0,
            "kp_050": 0,
            "kp_075": 0,
            "max_kp_conf": 0.0,
        }

    rink_conf = float(result.boxes.conf[0].item())

    if result.keypoints is None or result.keypoints.conf is None:
        return {
            "frame": frame_number,
            "rink_conf": rink_conf,
            "kp_025": 0,
            "kp_050": 0,
            "kp_075": 0,
            "max_kp_conf": 0.0,
        }

    confidences = result.keypoints.conf[0]

    return {
        "frame": frame_number,
        "rink_conf": rink_conf,
        "kp_025": int((confidences >= 0.25).sum().item()),
        "kp_050": int((confidences >= 0.50).sum().item()),
        "kp_075": int((confidences >= 0.75).sum().item()),
        "max_kp_conf": float(confidences.max().item()),
    }


def main() -> None:
    """Evaluate HockeyRink on one frame per second."""
    print(f"Video exists: {VIDEO_PATH.exists()}")
    print(f"Model exists: {MODEL_PATH.exists()}")

    model = YOLO(str(MODEL_PATH))

    capture = cv2.VideoCapture(str(VIDEO_PATH))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration_seconds = frame_count / fps

    sample_seconds = range(6)
    sample_frames = [int(second * fps) for second in sample_seconds]

    print(f"FPS: {fps}")
    print(f"Frame count: {frame_count}")
    print(f"Resolution: {width}x{height}")
    print(f"Duration: {duration_seconds:.2f} seconds")
    print(f"Sample frames: {sample_frames}")

    diagnostics = []

    for frame_number in sample_frames:
        frame = read_frame(capture, frame_number)
        diagnostic = analyze_frame(model, frame, frame_number)
        diagnostics.append(diagnostic)

    capture.release()

    print()
    print(
        f"{'Frame':>5} {'Rink':>7} {'>=.25':>6} {'>=.50':>6} {'>=.75':>6} {'Max KP':>7}"
    )

    for diagnostic in diagnostics:
        print(
            f"{diagnostic['frame']:>5} "
            f"{diagnostic['rink_conf']:>7.3f} "
            f"{diagnostic['kp_025']:>6} "
            f"{diagnostic['kp_050']:>6} "
            f"{diagnostic['kp_075']:>6} "
            f"{diagnostic['max_kp_conf']:>7.3f}"
        )


if __name__ == "__main__":
    main()
