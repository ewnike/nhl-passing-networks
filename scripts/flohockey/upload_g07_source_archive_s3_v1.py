#!/usr/bin/env python3
"""Protected, resumable G07 original-source S3 archival."""

from pathlib import Path
import hashlib
import json
import boto3
from botocore.exceptions import ClientError

ROOT = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G07")
MANIFEST = ROOT / "metadata/G07_source_archive_manifest_v1.json"

EXPECTED_MANIFEST_SHA = (
    "f1c1d9539e60d0c8000f292c2ad4d93248544d4ba82097ec9b7016419a85175a"
)

BUCKET = "ewnike-nhl-passing-networks-2026"
PREFIX = "flohockey/swiss_nl_2026_finals/G07/source_archive_v1/"

PART_SIZE = 64 * 1024 * 1024

s3 = boto3.client("s3")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_head(key):
    try:
        return s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError as exc:
        status = exc.response["ResponseMetadata"]["HTTPStatusCode"]
        if status == 404:
            return None
        raise


def verify_existing(key, record):
    head = remote_head(key)
    if head is None:
        return False

    if head["ContentLength"] != record["bytes"]:
        raise RuntimeError(f"STOP — Existing size mismatch: {key}")

    if head.get("Metadata", {}).get("sha256") != record["sha256"]:
        raise RuntimeError(f"STOP — Existing SHA metadata mismatch: {key}")

    return True


def upload_small(path, key, record):
    with path.open("rb") as f:
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=f,
            IfNoneMatch="*",
            Metadata={"sha256": record["sha256"]},
        )


def upload_multipart(path, key, record):
    upload_id = None
    completed = False

    try:
        response = s3.create_multipart_upload(
            Bucket=BUCKET,
            Key=key,
            Metadata={"sha256": record["sha256"]},
        )

        upload_id = response["UploadId"]
        parts = []

        with path.open("rb") as f:
            part_number = 1

            while True:
                data = f.read(PART_SIZE)
                if not data:
                    break

                result = s3.upload_part(
                    Bucket=BUCKET,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=data,
                )

                parts.append({
                    "PartNumber": part_number,
                    "ETag": result["ETag"],
                })

                part_number += 1

        s3.complete_multipart_upload(
            Bucket=BUCKET,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
            IfNoneMatch="*",
        )

        completed = True

    finally:
        if upload_id and not completed:
            try:
                s3.abort_multipart_upload(
                    Bucket=BUCKET,
                    Key=key,
                    UploadId=upload_id,
                )
            except ClientError:
                print(f"WARNING — Could not abort: {key}")


def main():
    print("G07 — ORIGINAL SOURCE ARCHIVE S3 UPLOAD")
    print("=" * 72)

    if sha256(MANIFEST) != EXPECTED_MANIFEST_SHA:
        raise SystemExit("STOP — Source manifest SHA mismatch")

    manifest = json.loads(MANIFEST.read_text())

    records = list(manifest["objects"])

    records.append({
        "relative_path": "metadata/G07_source_archive_manifest_v1.json",
        "bytes": MANIFEST.stat().st_size,
        "sha256": EXPECTED_MANIFEST_SHA,
    })

    if len(records) != 4790:
        raise SystemExit("STOP — Expected 4,790 archive objects")

    uploaded = 0
    skipped = 0

    for index, record in enumerate(records, 1):
        relative = record["relative_path"]
        path = ROOT / relative
        key = PREFIX + relative

        if not path.is_file():
            raise SystemExit(f"STOP — Missing local file: {relative}")

        if path.stat().st_size != record["bytes"]:
            raise SystemExit(f"STOP — Local size mismatch: {relative}")

        if verify_existing(key, record):
            skipped += 1
        else:
            if sha256(path) != record["sha256"]:
                raise SystemExit(
                    f"STOP — Local SHA mismatch: {relative}"
                )

            if record["bytes"] <= PART_SIZE:
                upload_small(path, key, record)
            else:
                upload_multipart(path, key, record)

            if not verify_existing(key, record):
                raise RuntimeError(
                    f"STOP — Post-upload verification failed: {relative}"
                )

            uploaded += 1

        if index % 100 == 0 or index == len(records):
            print(
                f"Processed: {index}/{len(records)} | "
                f"Uploaded: {uploaded} | Skipped: {skipped}",
                flush=True,
            )

    print()
    print("G07 — SOURCE ARCHIVE UPLOAD COMPLETE")
    print("=" * 72)
    print("Objects processed:", len(records))
    print("Newly uploaded:", uploaded)
    print("Previously present:", skipped)
    print("Status: UPLOAD PASS")
    print("Next: independent remote SHA-256 audit")


if __name__ == "__main__":
    main()
