#!/usr/bin/env python3
"""G05 original 1080p HLS TS acquisition; resumable, non-overwriting."""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G05")
PLAYLIST = ROOT / "metadata/playlists/G05_1080p.m3u8"
REGISTRATION = ROOT / "metadata/G05_playlist_registration_v1.json"
OUT = ROOT / "source_segments/1080p"
RECEIPTS = ROOT / "metadata/acquisition_1080p/receipts"
FAILURES = ROOT / "metadata/acquisition_1080p/failures"
BASE = "https://d17cyqyz9yhmep.cloudfront.net/streams/355877/a/8000/chunklist_vo_1777224672000_1777236803350.m3u8"
PLAYLIST_SHA = "4b59293945546c3aec199d7ee7abb6434d3a62adc3361ead5c171d4ba3ee344d"
REGISTRATION_SHA = "afbc5b674e7625eb453838cca007b9f60d5257b6dcc30694912aa46640736ce2"
KNOWN_SHA = {
    164: "77f45b4cf5ded283873880119e29b6b21363f2518133cf3d98331d09dc1f865b",
    1126: "f2b0986631b39b29d4a3c86087d34c8045babb02ab8be72b0de9a1b227967ec5",
    2185: "2c73b80905b36c7576c315f05f505583bf220790dd8a66a6f847ea9482786145",
}


def sha_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_inventory():
    for path, expected in [(PLAYLIST, PLAYLIST_SHA), (REGISTRATION, REGISTRATION_SHA)]:
        if not path.is_file() or sha_file(path) != expected:
            raise RuntimeError(f"Missing/changed registered file: {path}")
    registration = json.loads(REGISTRATION.read_text())
    if (
        registration.get("game_id") != "G05"
        or registration.get("expected_segments") != 2022
    ):
        raise RuntimeError("Registration mismatch")
    entries = []
    for line in PLAYLIST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.search(r"_(\d+)\.ts(?:\?.*)?$", line)
        if not match:
            raise RuntimeError(f"Unexpected media reference: {line}")
        seq = int(match.group(1))
        filename = urllib.parse.urlsplit(line).path.rsplit("/", 1)[-1]
        if not re.fullmatch(r"segment-1777212156834_1_\d+\.ts", filename):
            raise RuntimeError(f"Unexpected filename: {filename}")
        entries.append((seq, filename, urllib.parse.urljoin(BASE, line)))
    if [s for s, _, _ in entries] != list(range(164, 2186)):
        raise RuntimeError("Sequence inventory mismatch")
    return entries


def receipt_valid(seq, filename):
    dest = OUT / filename
    receipt = RECEIPTS / f"{seq}.json"
    if not dest.exists() and not receipt.exists():
        return False
    if not dest.is_file() or not receipt.is_file():
        raise RuntimeError(
            f"Partial or unverified artifact for {seq}; do not overwrite: {dest}"
        )
    data = json.loads(receipt.read_text())
    if (
        data.get("sequence") != seq
        or data.get("filename") != filename
        or data.get("bytes") != dest.stat().st_size
        or data.get("sha256") != sha_file(dest)
    ):
        raise RuntimeError(f"Existing artifact integrity mismatch for {seq}")
    if seq in KNOWN_SHA and data["sha256"] != KNOWN_SHA[seq]:
        raise RuntimeError(f"Known reference checksum mismatch for {seq}")
    return True


def exclusive_publish(temp, destination):
    # Atomic create-if-absent on the same filesystem; never replaces a file.
    os.link(temp, destination)


def download_one(entry, retries):
    seq, filename, url = entry
    dest = OUT / filename
    receipt = RECEIPTS / f"{seq}.json"
    if receipt_valid(seq, filename):
        return seq, "SKIP verified", ""
    for attempt in range(1, retries + 1):
        tmp_path = None
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError(f"Unexpected HTTP {response.status}")
                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{seq}.", suffix=".part", dir=OUT
                )
                tmp_path = Path(temp_name)
                h = hashlib.sha256()
                count = 0
                with os.fdopen(fd, "wb") as f:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        f.write(block)
                        h.update(block)
                        count += len(block)
                    f.flush()
                    os.fsync(f.fileno())
            if count == 0 or count % 188 != 0:
                raise RuntimeError(f"Empty or non-TS-aligned payload: {count} bytes")
            with tmp_path.open("rb") as f:
                if f.read(1) != b"\x47":
                    raise RuntimeError("MPEG-TS sync byte missing")
            digest = h.hexdigest()
            if seq in KNOWN_SHA and digest != KNOWN_SHA[seq]:
                raise RuntimeError("Previously observed SHA-256 differs")
            exclusive_publish(tmp_path, dest)
            metadata = {
                "game_id": "G05",
                "sequence": seq,
                "filename": filename,
                "rendition": "1080p",
                "source_url": url,
                "bytes": count,
                "sha256": digest,
                "playlist_sha256": PLAYLIST_SHA,
            }
            fd, receipt_temp_name = tempfile.mkstemp(
                prefix=f".{seq}.", suffix=".json.part", dir=RECEIPTS
            )
            receipt_temp = Path(receipt_temp_name)
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(metadata, f, sort_keys=True, indent=2)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                exclusive_publish(receipt_temp, receipt)
            finally:
                receipt_temp.unlink(missing_ok=True)
            (FAILURES / f"{seq}.json").unlink(missing_ok=True)
            return seq, "PASS", f"{count:,} bytes"
        except urllib.error.HTTPError as exc:
            err = f"HTTP {exc.code}"
            if exc.code in (401, 403, 404):
                break
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            # Any partially published file is deliberately left for manual review.
            if dest.exists() or receipt.exists():
                break
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
        if attempt < retries:
            time.sleep(min(attempt * 2, 8))
    failure = {"sequence": seq, "filename": filename, "source_url": url, "error": err}
    failure_path = FAILURES / f"{seq}.json"
    if not failure_path.exists():
        with failure_path.open("x") as f:
            json.dump(failure, f, indent=2)
            f.write("\n")
    return seq, "FAIL", err


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process first N sequence entries; 0 means all",
    )
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 7))
    parser.add_argument("--retries", type=int, default=3, choices=range(1, 7))
    args = parser.parse_args()
    entries = load_inventory()
    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    selected = entries[: args.limit] if args.limit else entries
    print(
        f"G05: registered inventory PASS; total={len(entries)}; selected={len(selected)}; workers={args.workers}",
        flush=True,
    )
    print(f"Output: {OUT}", flush=True)
    if args.dry_run:
        print("DRY RUN: no files created or downloaded")
        return
    for directory in (OUT, RECEIPTS, FAILURES):
        directory.mkdir(parents=True, exist_ok=True)
    # Verify existing receipts before submitting any network downloads.
    for seq, filename, _ in selected:
        receipt_valid(seq, filename)
    counts = {"PASS": 0, "SKIP verified": 0, "FAIL": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_one, entry, args.retries) for entry in selected]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            seq, status, detail = future.result()
            counts[status] += 1
            print(f"[{index}/{len(selected)}] {seq}: {status} {detail}", flush=True)
    print("RESULT:", counts, flush=True)
    if counts["FAIL"]:
        raise SystemExit(
            "Incomplete acquisition: inspect failure receipts; rerun safely after review"
        )


if __name__ == "__main__":
    main()
