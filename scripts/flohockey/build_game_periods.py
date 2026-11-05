#!/usr/bin/env python3
"""Build preliminary, segment-aligned period MP4s from local FloHockey TS files.

Original TS files are never modified. Upload to S3 is deliberately separate.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")
SEGMENT_RE = re.compile(r"^segment-.*_1_(\d+)\.ts$")


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--execute", action="store_true", help="Actually build MP4s (default: dry run)"
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    root = args.root
    metadata = root / "metadata" / "period_boundaries.json"
    segments_dir = root / "segments"
    output_dir = root / "periods"
    if not metadata.is_file():
        parser.error(f"Missing metadata: {metadata}")
    if not segments_dir.is_dir():
        parser.error(f"Missing segments directory: {segments_dir}")
    data = json.loads(metadata.read_text())
    if not isinstance(data.get("periods"), dict):
        parser.error("Metadata must contain a periods object")

    found = {}
    for path in segments_dir.glob("*.ts"):
        match = SEGMENT_RE.fullmatch(path.name)
        if match:
            seq = int(match.group(1))
            found.setdefault(seq, []).append(path)

    jobs = []
    errors = []
    for period, bounds in sorted(data["periods"].items(), key=lambda kv: int(kv[0])):
        start, end = bounds["start_segment"], bounds["end_segment"]
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            errors.append(f"P{period}: invalid segment range {start}..{end}")
            continue
        missing = [n for n in range(start, end + 1) if n not in found]
        ambiguous = [n for n in range(start, end + 1) if len(found.get(n, [])) > 1]
        if missing or ambiguous:
            errors.append(
                f"P{period}: missing={missing[:20]} (total {len(missing)}), ambiguous={ambiguous[:20]} (total {len(ambiguous)})"
            )
            continue
        paths = [found[n][0].resolve() for n in range(start, end + 1)]
        output = output_dir / f"{data.get('game_id', 'G01')}_P{period}.mp4"
        jobs.append((period, paths, output))
        print(
            f"P{period}: segments {start}–{end} ({len(paths)} files), output={output}"
        )
        print(
            f"  Visual refs: {bounds.get('start_frame_reference', 'not set')} → {bounds.get('end_frame_reference', 'not set')}"
        )

    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    if not args.execute:
        print("\nDRY RUN: no files written. Add --execute to build MP4s.")
        return 0
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("ffmpeg and ffprobe must be installed and available on PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    game_id = data["game_id"]

    for period, paths, output in jobs:
        if output.exists() and not args.overwrite:
            print(
                f"ERROR: {output} already exists; use --overwrite to replace it",
                file=sys.stderr,
            )
            return 1
        list_path = output_dir / f".{game_id}_P{period}_concat.txt"
        # FFmpeg concat demuxer expects single-quoted paths, with embedded quotes escaped.
        list_path.write_text(
            "ffconcat version 1.0\n"
            + "".join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in paths)
        )
        temp_output = output_dir / f".{game_id}_P{period}_building.mp4"
        temp_output.unlink(missing_ok=True)
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            str(temp_output),
        ]
        print(f"Building P{period}...", flush=True)
        result = run(cmd)
        if result.returncode:
            print(result.stderr[-5000:], file=sys.stderr)
            print(
                f"ERROR: P{period} failed. Original TS files unchanged.",
                file=sys.stderr,
            )
            return 1
        probe = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size",
                "-of",
                "json",
                str(temp_output),
            ]
        )
        try:
            info = json.loads(probe.stdout)["format"]
            duration = float(info["duration"])
            size = int(info["size"])
            if probe.returncode or duration <= 0 or size <= 0:
                raise ValueError("Invalid MP4 duration/size")
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: P{period} ffprobe validation failed: {exc}", file=sys.stderr)
            return 1
        temp_output.replace(output)
        print(f"OK P{period}: {duration:.2f}s, {size / 1e9:.2f} GB, {output}")
        if result.stderr.strip():
            print(
                "  FFmpeg warnings (review if playback has issues):",
                result.stderr[-600:],
            )
    print(
        "\nBuilt all preliminary period MP4s. Visually inspect start/end and internal playback before S3 upload."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
