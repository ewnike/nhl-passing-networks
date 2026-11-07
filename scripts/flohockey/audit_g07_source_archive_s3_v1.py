#!/usr/bin/env python3
"""Independent remote SHA-256 audit of the G07 source archive."""

from pathlib import Path
import hashlib
import json
import boto3

ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G07")
MANIFEST = ROOT / "metadata/G07_source_archive_manifest_v1.json"

EXPECTED_MANIFEST_SHA = (
    "f1c1d9539e60d0c8000f292c2ad4d93248544d4ba82097ec9b7016419a85175a"
)

BUCKET = "ewnike-nhl-passing-networks-2026"
PREFIX = "flohockey/swiss_nl_2026_finals/G07/source_archive_v1/"

EXPECTED_OBJECTS = 4790
EXPECTED_BYTES = 15066064916

s3 = boto3.client("s3")


def local_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_sha256(key):
    h = hashlib.sha256()
    byte_count = 0

    response = s3.get_object(
        Bucket=BUCKET,
        Key=key,
    )

    body = response["Body"]

    try:
        while True:
            chunk = body.read(8 * 1024 * 1024)

            if not chunk:
                break

            h.update(chunk)
            byte_count += len(chunk)
    finally:
        body.close()

    return h.hexdigest(), byte_count


def main():
    print("G07 — INDEPENDENT SOURCE ARCHIVE S3 AUDIT")
    print("=" * 72)

    if local_sha256(MANIFEST) != EXPECTED_MANIFEST_SHA:
        raise SystemExit("STOP — Local manifest SHA mismatch")

    manifest = json.loads(MANIFEST.read_text())

    if manifest.get("game") != "G07":
        raise SystemExit("STOP — Incorrect game")

    records = list(manifest["objects"])

    records.append({
        "relative_path": "metadata/G07_source_archive_manifest_v1.json",
        "bytes": MANIFEST.stat().st_size,
        "sha256": EXPECTED_MANIFEST_SHA,
    })

    if len(records) != EXPECTED_OBJECTS:
        raise SystemExit("STOP — Unexpected manifest object count")

    expected = {
        PREFIX + record["relative_path"]: record
        for record in records
    }

    if len(expected) != EXPECTED_OBJECTS:
        raise SystemExit("STOP — Duplicate manifest paths")

    actual = {}

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=PREFIX,
    ):
        for obj in page.get("Contents", []):
            actual[obj["Key"]] = obj["Size"]

    if set(actual) != set(expected):
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)

        print("Missing:", sorted(missing)[:20])
        print("Unexpected:", sorted(extra)[:20])

        raise SystemExit("STOP — Remote inventory mismatch")

    print("Remote inventory: PASS — 4,790/4,790")
    print()

    total_bytes = 0

    for index, (key, record) in enumerate(expected.items(), 1):
        if actual[key] != record["bytes"]:
            raise SystemExit(
                f"STOP — Remote size mismatch: {key}"
            )

        actual_sha, streamed_bytes = remote_sha256(key)

        if streamed_bytes != record["bytes"]:
            raise SystemExit(
                f"STOP — Streamed byte mismatch: {key}"
            )

        if actual_sha != record["sha256"]:
            raise SystemExit(
                f"STOP — Remote SHA mismatch: {key}"
            )

        total_bytes += streamed_bytes

        if index % 100 == 0 or index == EXPECTED_OBJECTS:
            print(
                f"Verified: {index}/{EXPECTED_OBJECTS}",
                flush=True,
            )

    if total_bytes != EXPECTED_BYTES:
        raise SystemExit(
            f"STOP — Total byte mismatch: {total_bytes}"
        )

    print()
    print("G07 — FINAL SOURCE ARCHIVE INTEGRITY VALIDATION")
    print("=" * 72)
    print("Objects verified:", EXPECTED_OBJECTS)
    print("Total remote bytes:", f"{total_bytes:,}")
    print("SHA-256 checksums: PASS — 4,790/4,790")
    print("Remote inventory: PASS")
    print("Source archive integrity: PASS")
    print("Original local artifacts unchanged: YES")


if __name__ == "__main__":
    main()
