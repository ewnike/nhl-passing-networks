"""
Phase 02 — G01 Commentary Transcription Pilot

Transcribes the 30-second audio-enabled video pilot.
Preserves timestamped transcript segments and metadata.

Does not modify original video or FiftyOne datasets.
"""

import csv
import hashlib
import json
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "experiment_07/phase_02_fiftyone_video_pilot"
)

VIDEO = ROOT / "G01_P1_330_360_with_audio.mp4"

OUTPUT = ROOT / "commentary_transcription_v1"

SOURCE_START_SECONDS = 330.0

MODEL_NAME = "small"


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def main():

    print("PHASE 02 — COMMENTARY TRANSCRIPTION PILOT")
    print("=" * 75)

    if not VIDEO.is_file():
        raise FileNotFoundError(VIDEO)

    if OUTPUT.exists():
        raise RuntimeError(f"Refusing overwrite: {OUTPUT}")

    model = WhisperModel(
        MODEL_NAME,
        device="cpu",
        compute_type="int8",
    )

    # ------------------------------------------------------------
    # LOAD AUDIO — BYPASS PYAV
    # ------------------------------------------------------------

    AUDIO = ROOT / "G01_P1_330_360_audio.wav"

    if not AUDIO.is_file():
        raise FileNotFoundError(AUDIO)

    with wave.open(str(AUDIO), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()

        if channels != 1 or sample_rate != 16000 or sample_width != 2:
            raise RuntimeError("Expected mono, 16 kHz, 16-bit PCM WAV")

        audio_bytes = wav.readframes(wav.getnframes())

    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # ------------------------------------------------------------
    # TRANSCRIBE AUDIO
    # ------------------------------------------------------------

    segments, info = model.transcribe(
        audio,
        beam_size=5,
        vad_filter=True,
    )

    rows = []

    for index, segment in enumerate(segments, start=1):
        start = float(segment.start)
        end = float(segment.end)

        rows.append(
            {
                "segment_id": index,
                "clip_start_seconds": round(start, 3),
                "clip_end_seconds": round(end, 3),
                "source_start_seconds": round(SOURCE_START_SECONDS + start, 3),
                "source_end_seconds": round(SOURCE_START_SECONDS + end, 3),
                "text": segment.text.strip(),
                "language": info.language,
            }
        )

    if not rows:
        raise RuntimeError("No transcription segments detected")

    OUTPUT.mkdir(parents=True, exist_ok=False)

    CSV_PATH = OUTPUT / "transcript_segments.csv"
    JSON_PATH = OUTPUT / "transcript_manifest.json"

    with CSV_PATH.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "phase": "02",
        "operation": "commentary_transcription",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_video": str(VIDEO),
        "source_video_sha256": sha256(VIDEO),
        "model": MODEL_NAME,
        "device": "cpu",
        "compute_type": "int8",
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "segments": len(rows),
        "transcript_csv": str(CSV_PATH),
        "transcript_csv_sha256": sha256(CSV_PATH),
        "original_artifacts_modified": False,
    }

    with JSON_PATH.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print()
    print("TRANSCRIPTION")
    print("-" * 75)

    for row in rows:
        print(
            f"{row['source_start_seconds']:7.2f}–"
            f"{row['source_end_seconds']:7.2f} | "
            f"{row['text']}"
        )

    print()
    print("SUMMARY")
    print("=" * 75)
    print("Detected language:", info.language)
    print("Segments:", len(rows))
    print("CSV:", CSV_PATH)
    print("Manifest:", JSON_PATH)
    print("Manifest SHA-256:", sha256(JSON_PATH))
    print("Status: PASS")


if __name__ == "__main__":
    main()
