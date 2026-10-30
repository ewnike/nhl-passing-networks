#!/usr/bin/env python3

"""
Experiment 06D2 — AWS S3 SHA-256 Integrity Verification

Compare every archived S3 object against the local
SHA-256 manifest.

Read-only:
- No S3 objects modified
- No local experiment files modified
- No files downloaded to disk
- No model inference
"""

import hashlib
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

BUCKET = "ewnike-nhl-passing-networks-2026"

PREFIX = (
    "experiments/swiss_nl_2026_finals/"
    "G01/experiment_06/stage_6d2/"
    "full_broadcast_baseline/"
)

MANIFEST = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_06/stage_6d/"
    "stage_6d2_sha256_manifest.txt"
)


def load_manifest():
    """Read expected SHA-256 hashes."""

    if not MANIFEST.is_file():
        raise FileNotFoundError(MANIFEST)

    expected = {}

    for line in MANIFEST.read_text().splitlines():
        if not line.strip():
            continue

        digest, filename = line.split("  ", 1)

        if filename in expected:
            raise ValueError(f"Duplicate manifest entry: {filename}")

        expected[filename] = digest.lower()

    return expected


def hash_s3_object(s3, key):
    """Stream an S3 object and calculate SHA-256."""

    response = s3.get_object(
        Bucket=BUCKET,
        Key=key,
    )

    sha256 = hashlib.sha256()

    body = response["Body"]

    try:
        for chunk in body.iter_chunks(chunk_size=1024 * 1024):
            if chunk:
                sha256.update(chunk)
    finally:
        body.close()

    return sha256.hexdigest()


def main():

    expected = load_manifest()

    s3 = boto3.client("s3")

    print("\nEXPERIMENT 06D2 — S3 INTEGRITY VERIFICATION")
    print("-" * 70)

    print("Bucket:", BUCKET)
    print("Manifest entries:", len(expected))

    # Inventory every object under the archive prefix.
    remote_files = set()

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=PREFIX,
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            relative = key[len(PREFIX) :]

            if relative:
                remote_files.add(relative)

    expected_files = set(expected)

    missing = expected_files - remote_files
    unexpected = remote_files - expected_files

    if missing or unexpected:
        print("\nARCHIVE INVENTORY MISMATCH")

        for filename in sorted(missing):
            print("MISSING:", filename)

        for filename in sorted(unexpected):
            print("UNEXPECTED:", filename)

        raise RuntimeError("S3 inventory does not match manifest")

    print("Remote object count:", len(remote_files))
    print("Inventory match: PASS")

    verified = 0
    failures = []

    for index, filename in enumerate(sorted(expected), start=1):
        key = PREFIX + filename

        try:
            actual = hash_s3_object(s3, key)

            if actual == expected[filename]:
                verified += 1
            else:
                failures.append(filename)
                print("CHECKSUM MISMATCH:", filename)

        except ClientError as error:
            failures.append(filename)
            print("S3 READ ERROR:", filename, error)

        if index % 50 == 0 or index == len(expected):
            print(f"Verified {index}/{len(expected)} objects")

    print("\nVERIFICATION SUMMARY")
    print("-" * 70)

    print("Expected objects:", len(expected))
    print("Verified objects:", verified)
    print("Failed objects:", len(failures))

    if failures:
        print("\nFAILED FILES:")

        for filename in failures:
            print(filename)

        raise RuntimeError("S3 integrity verification FAILED")

    print("\nS3 SHA-256 INTEGRITY: PASS")
    print("All archived objects match the local manifest.")
    print("No S3 objects modified.")
    print("No local experiment files modified.")


if __name__ == "__main__":
    main()
