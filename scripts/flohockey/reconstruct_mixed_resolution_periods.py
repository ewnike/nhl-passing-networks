#!/usr/bin/env python3
"""G04 non-destructive, resumable mixed-resolution normalization and assembly."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_BOUNDARY_SHA = (
    "c577bdb3e18126b761b48e7860e36836a313bbd52ec88ba7b5f001128b5ed8e4"
)
EXPECTED_RECOVERY_SHA = (
    "8a43f77364186ae9b2d6f770bc5a66d0e865a803aa72f81d50f356210109a47d"
)
DIMENSIONS = {
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "540p": (960, 540),
    "480p": (854, 480),
    "360p": (640, 360),
    "270p": (480, 270),
}
SETTINGS = {
    "resolution": "1920x1080",
    "fps": 30,
    "video_codec": "libx264",
    "preset": "fast",
    "crf": 18,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "audio_rate": 48000,
    "segment_seconds": 6,
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(map(str, cmd[:5]))}\n{p.stderr[-2500:]}"
        )
    return p.stdout


def probe(path):
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ]
        )
    )


def streams(info):
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not v or not a:
        raise RuntimeError("Missing video or audio")
    return v, a


def check_media(path, duration=True):
    info = probe(path)
    v, a = streams(info)
    if (v["codec_name"], v.get("width"), v.get("height")) != ("h264", 1920, 1080) or a[
        "codec_name"
    ] != "aac":
        raise RuntimeError(f"Unexpected codecs or dimensions: {path}")
    if v.get("r_frame_rate") != "30/1":
        raise RuntimeError(f"Unexpected frame rate: {v.get('r_frame_rate')}")
    seconds = float(info["format"]["duration"])
    if duration and not 5.8 <= seconds <= 6.2:
        raise RuntimeError(f"Unexpected segment duration {seconds}: {path}")
    return seconds


def decode(path):
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-xerror",
            "-nostdin",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]
    )


def load(root):
    bp = root / "metadata/period_boundaries.json"
    rp = root / "metadata/G04_recovery_results_v1.json"
    if sha(bp) != EXPECTED_BOUNDARY_SHA or sha(rp) != EXPECTED_RECOVERY_SHA:
        raise RuntimeError("Input manifest SHA-256 mismatch")
    b = json.loads(bp.read_text())
    r = json.loads(rp.read_text())
    if (
        b.get("game_id") != "G04"
        or r.get("game_id") != "G04"
        or len(r["records"]) != 80
    ):
        raise RuntimeError("Invalid input manifests")
    recovered = {}
    for rec in r["records"]:
        n = int(rec["sequence"])
        path = root / rec["path"]
        if (
            n in recovered
            or not path.is_file()
            or path.stat().st_size != rec["bytes"]
            or sha(path) != rec["sha256"]
        ):
            raise RuntimeError(f"Invalid recovered segment {n}")
        recovered[n] = (path, rec["resolution"])
    original = {}
    for path in (root / "segments").glob("*.ts"):
        m = re.search(r"_(\d+)\.ts$", path.name)
        if m:
            n = int(m.group(1))
            if n in original:
                raise RuntimeError(f"Duplicate original segment {n}")
            original[n] = path
    jobs = []
    for period, bounds in b["periods"].items():
        for n in range(int(bounds["start_segment"]), int(bounds["end_segment"]) + 1):
            if n in original and n in recovered:
                raise RuntimeError(f"Ambiguous source {n}")
            if n in original:
                path, res = original[n], "1080p"
            elif n in recovered:
                path, res = recovered[n]
            else:
                raise RuntimeError(f"Missing source {n}")
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"Empty source {n}")
            jobs.append((period, n, path, res))
    if len(jobs) != 1045 or len({n for _, n, _, _ in jobs}) != 1045:
        raise RuntimeError("Expected 1045 unique selected segments")
    return jobs


def record_path(root, period, n):
    return root / "normalized" / period / f"G04_{period}_{n:04d}.mp4"


def receipt_path(path):
    return path.with_suffix(".json")


def validate_receipt(root, period, n, source, res, full_decode=False):
    dest = record_path(root, period, n)
    receipt = receipt_path(dest)
    if not dest.is_file() or not receipt.is_file():
        return False
    try:
        d = json.loads(receipt.read_text())
        if (
            d["sequence"],
            d["period"],
            d["source_path"],
            d["source_resolution"],
            d["settings"],
        ) != (n, period, str(source), res, SETTINGS):
            return False
        if d["source_size"] != source.stat().st_size or d["source_sha256"] != sha(
            source
        ):
            return False
        if d["output_size"] != dest.stat().st_size or d["output_sha256"] != sha(dest):
            return False
        check_media(dest)
        if full_decode:
            decode(dest)
        return True
    except (KeyError, ValueError, RuntimeError, OSError, json.JSONDecodeError):
        return False


def normalize(root, job):
    period, n, source, res = job
    dest = record_path(root, period, n)
    receipt = receipt_path(dest)
    if dest.exists() or receipt.exists():
        if validate_receipt(root, period, n, source, res):
            return "SKIP verified"
        raise RuntimeError(
            f"Unverified existing output/receipt; refusing overwrite: {dest}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Input video timestamps are reset; audio is padded/trimmed to the exact 6s grid.
    vf = "setpts=PTS-STARTPTS,fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,trim=duration=6,setpts=PTS-STARTPTS"
    af = "aresample=async=1:first_pts=0,apad,atrim=duration=6,asetpts=PTS-STARTPTS"
    with tempfile.TemporaryDirectory(prefix="g04_", dir=dest.parent) as td:
        tmp = Path(td) / "output.mp4"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-filter_complex",
            f"[0:v:0]{vf}[v];[0:a:0]{af}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
        run(cmd)
        seconds = check_media(tmp)
        decode(tmp)
        receipt_data = {
            "period": period,
            "sequence": n,
            "source_path": str(source),
            "source_resolution": res,
            "source_size": source.stat().st_size,
            "source_sha256": sha(source),
            "output_path": str(dest),
            "output_size": tmp.stat().st_size,
            "output_sha256": sha(tmp),
            "duration": seconds,
            "settings": SETTINGS,
        }
        # exclusive writes, never replace a completed file
        with open(dest, "xb") as out, open(tmp, "rb") as inp:
            for block in iter(lambda: inp.read(8 * 1024 * 1024), b""):
                out.write(block)
        with open(receipt, "x") as f:
            json.dump(receipt_data, f, indent=2)
            f.write("\n")
    return "PASS"


def assemble(root, jobs):
    by_period = {}
    for job in jobs:
        by_period.setdefault(job[0], []).append(job)
    for period, group in by_period.items():
        output = root / "periods" / f"G04_{period}.mp4"
        if output.exists():
            raise RuntimeError(f"Refusing overwrite: {output}")
        for p, n, s, r in group:
            if not validate_receipt(root, p, n, s, r):
                raise RuntimeError(f"Normalization not verified: {p} {n}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="g04_concat_", dir=output.parent) as td:
            td = Path(td)
            listing = td / "concat.txt"
            temp = td / "assembled.mp4"
            # Absolute paths and ffconcat escaping.
            listing.write_text(
                "ffconcat version 1.0\n"
                + "".join(
                    "file '"
                    + str(record_path(root, p, n).resolve()).replace("'", "'\\''")
                    + "'\n"
                    for p, n, _, _ in group
                )
            )
            run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(listing),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(temp),
                ]
            )
            seconds = check_media(temp, duration=False)
            expected = 6 * len(group)
            if abs(seconds - expected) > 2:
                raise RuntimeError(
                    f"{period}: duration {seconds} vs expected {expected}"
                )
            decode(temp)
            with open(output, "xb") as out, open(temp, "rb") as inp:
                for block in iter(lambda: inp.read(8 * 1024 * 1024), b""):
                    out.write(block)
            print(
                f"{period}: PASS {seconds:.2f}s, {output}, SHA-256 {sha(output)}",
                flush=True,
            )


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--root",
        type=Path,
        default=Path("local_artifacts/flohockey/swiss_nl_2026_finals/G04"),
    )
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--normalize", action="store_true")
    modes.add_argument("--assemble", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    if args.limit is not None and (not args.normalize or args.limit < 1):
        p.error("--limit requires --normalize and a positive integer")
    root = args.root
    jobs = load(root)
    print(
        f"G04: {len(jobs)} selected segments; mode={'dry-run' if args.dry_run else 'normalize' if args.normalize else 'assemble'}",
        flush=True,
    )
    if args.dry_run:
        for period in ("P1", "P2", "P3"):
            group = [j for j in jobs if j[0] == period]
            print(
                f"{period}: {len(group)} segments, {sum(j[3] != '1080p' for j in group)} recovered"
            )
        return
    if args.normalize:
        count = 0
        for job in jobs:
            if args.limit is not None and count >= args.limit:
                break
            count += 1
            try:
                status = normalize(root, job)
            except Exception as exc:
                print(f"FAILED {job[0]} {job[1]}: {exc}", file=sys.stderr)
                raise
            print(
                f"[{count}/{args.limit or len(jobs)}] {job[0]} {job[1]}: {status}",
                flush=True,
            )
        return
    assemble(root, jobs)


if __name__ == "__main__":
    main()
