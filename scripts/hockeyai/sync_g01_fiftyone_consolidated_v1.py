#!/usr/bin/env python3
"""Build an immutable-source, consolidated G01 FiftyOne identity review dataset.

Run from repository root:
  python scripts/hockeyai/sync_g01_fiftyone_consolidated_v1.py --dry-run
  python scripts/hockeyai/sync_g01_fiftyone_consolidated_v1.py --create

Existing FiftyOne datasets and Experiment 07 files are never modified.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

DATASET_NAME = "swiss_nl_g01_identity_review_consolidated_v1"
STAGES = {
    "07E2": ("swiss_nl_g01_experiment_07e2_identity_review", "identity_reference/appearance_crops"),
    "07E5": ("swiss_nl_g01_experiment_07e5_identity_review", "stage_07e4/identity_reference/appearance_crops"),
    "07E8": ("swiss_nl_g01_experiment_07e8_identity_review", "stage_07e7/identity_reference/appearance_crops"),
}
EXPECTED = {"candidates": 1320, "verified": 301, "matched": 296, "unmatched": 5}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def absolute_path(repo, path):
    p = Path(path).expanduser()
    return p.resolve() if p.is_absolute() else (repo / p).resolve()


def get_sample(sample, field):
    return sample[field] if field in sample.field_names else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--create", action="store_true")
    args = parser.parse_args()

    import fiftyone as fo

    repo = Path.cwd().resolve()
    root = repo / "local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_07"
    roster_path = root / "identity_reference/g01_official_player_dictionary.csv"
    import csv
    if not roster_path.is_file():
        raise FileNotFoundError(roster_path)
    with roster_path.open(newline="", encoding="utf-8-sig") as stream:
        roster_rows = list(csv.DictReader(stream))
    team_ids = {101151: "HCD", 103138: "FRI"}
    roster = {}
    for r in roster_rows:
        key = (team_ids[int(r["team_id"])], int(r["jersey_number"]))
        if key in roster:
            raise RuntimeError(f"Duplicate roster key {key}")
        roster[key] = r

    if fo.dataset_exists(DATASET_NAME):
        existing = fo.load_dataset(DATASET_NAME)
        print(f"Dataset already exists: {DATASET_NAME}; samples={len(existing)}")
        print("No changes made. To rebuild, use a new versioned dataset name after review.")
        return

    stage_inputs = []
    verified_lookup = {}
    unmatched = []
    matched = []
    candidate_count = 0
    source_fingerprints = {str(roster_path.relative_to(repo)): sha256(roster_path)}
    errors = []
    seen_verified = set()

    print("PHASE 02 — CONSOLIDATED FIFTYONE PREFLIGHT")
    print("=" * 72)
    for stage, (name, relative_dir) in STAGES.items():
        source = fo.load_dataset(name)
        manifest_path = root / relative_dir / "appearance_reference_manifest.json"
        crop_dir = manifest_path.parent
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        records = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise RuntimeError(f"Expected list manifest: {manifest_path}")
        source_fingerprints[str(manifest_path.relative_to(repo))] = sha256(manifest_path)
        candidate_count += len(source)

        lookup = defaultdict(list)
        for sample in source:
            key = (int(sample["frame_index"]), str(sample["track_uid"]))
            lookup[key].append(sample)
            if not Path(sample.filepath).is_file():
                errors.append(f"Missing candidate image: {sample.filepath}")
        stage_matches = 0
        stage_unmatched = 0
        for record in records:
            key = (int(record["frame_index"]), str(record["track_uid"]))
            identity_key = (stage, *key)
            if identity_key in seen_verified:
                errors.append(f"Duplicate verified manifest key: {identity_key}")
                continue
            seen_verified.add(identity_key)
            roster_key = (str(record["team"]), int(record["jersey_number"]))
            official = roster.get(roster_key)
            if official is None or str(official["player_id"]) != str(record["player_id"]):
                errors.append(f"Roster mismatch: {identity_key} / {roster_key}")
            crop_path = crop_dir / record["filename"]
            if not crop_path.is_file():
                errors.append(f"Missing verified crop: {crop_path}")
            choices = lookup.get(key, [])
            if len(choices) > 1:
                errors.append(f"Ambiguous candidate match: {identity_key}")
            elif len(choices) == 1:
                sample = choices[0]
                # Match the underlying detection geometry as well as frame and track.
                original = record.get("bbox_original")
                candidate_bbox = get_sample(sample, "bbox_original")
                if original is not None and candidate_bbox is not None:
                    if len(original) != 4 or len(candidate_bbox) != 4 or max(abs(float(a)-float(b)) for a,b in zip(original,candidate_bbox)) > 3.0:
                        errors.append(f"Bounding-box mismatch: {identity_key}")
                matched.append((stage, str(sample.id), record, crop_path))
                stage_matches += 1
            else:
                unmatched.append((stage, record, crop_path))
                stage_unmatched += 1
        stage_inputs.append((stage, source))
        print(f"{stage}: candidates={len(source)}, verified={len(records)}, matched={stage_matches}, unmatched={stage_unmatched}")

    print(f"TOTAL: candidates={candidate_count}, verified={len(seen_verified)}, matched={len(matched)}, unmatched={len(unmatched)}")
    for label, actual in (("candidates", candidate_count), ("verified", len(seen_verified)), ("matched", len(matched)), ("unmatched", len(unmatched))):
        if actual != EXPECTED[label]:
            errors.append(f"Unexpected {label}: {actual} != {EXPECTED[label]}")
    if errors:
        print("PREFLIGHT FAILED; no dataset created:")
        for error in errors[:30]:
            print(" -", error)
        raise SystemExit(2)
    print("Preflight: PASS")
    if args.dry_run:
        print("DRY RUN COMPLETE — no changes made")
        return

    # A new dataset is the only persistent object written. Original datasets are read-only.
    target = None
    try:
        target = fo.Dataset(DATASET_NAME)
        target.persistent = True
        target.info.update({
            "purpose": "G01 identity review; original source datasets preserved",
            "source_datasets": [name for name, _ in STAGES.values()],
            "source_sha256": source_fingerprints,
            "verified_manifest_records": len(seen_verified),
            "verified_matched": len(matched),
            "verified_unmatched_imported": len(unmatched),
            "identity_review_schema_version": "1",
        })
        target.save()
        source_id_to_target = {}
        for stage, source in stage_inputs:
            batch = []
            ids = []
            for sample in source:
                clone = fo.Sample(filepath=sample.filepath)
                for field in ("game_id", "frame_index", "track_uid", "camera_segment", "source_image", "bbox_original", "video_time_seconds"):
                    v = get_sample(sample, field)
                    if v is not None:
                        clone[field] = v
                clone["source_stage"] = stage
                clone["source_dataset"] = source.name
                clone["source_sample_id"] = str(sample.id)
                clone["identity_status"] = "unverified"
                clone["verified_player_id"] = None
                clone["verified_player_name"] = None
                clone["verified_team"] = None
                clone["verified_jersey_number"] = None
                clone["verified_crop_path"] = None
                clone["verification_method"] = None
                clone["identity_source_manifest"] = None
                clone["identity_source_record_key"] = None
                batch.append(clone)
                ids.append(str(sample.id))
            inserted = target.add_samples(batch, progress=False)
            for old_id, new_id in zip(ids, inserted):
                source_id_to_target[(stage, old_id)] = new_id
            print(f"Copied {len(batch)} candidates from {stage}")

        def annotate(sample, stage, record, crop_path):
            sample["identity_status"] = "verified"
            sample["verified_player_id"] = str(record["player_id"])
            sample["verified_player_name"] = str(record["player_name"])
            sample["verified_team"] = str(record["team"])
            sample["verified_jersey_number"] = int(record["jersey_number"])
            sample["verified_crop_path"] = str(crop_path.resolve())
            sample["verification_method"] = str(record["verification_method"])
            sample["identity_source_manifest"] = str((root / STAGES[stage][1] / "appearance_reference_manifest.json").resolve())
            sample["identity_source_record_key"] = f"{stage}|{record['frame_index']}|{record['track_uid']}"
            sample.save()

        for stage, old_id, record, crop_path in matched:
            new_id = source_id_to_target[(stage, old_id)]
            annotate(target[new_id], stage, record, crop_path)

        for stage, record, crop_path in unmatched:
            extra = fo.Sample(filepath=str(crop_path.resolve()))
            extra["game_id"] = "G01"
            extra["frame_index"] = int(record["frame_index"])
            extra["track_uid"] = str(record["track_uid"])
            extra["source_image"] = str(absolute_path(repo, record["source_image"]))
            extra["bbox_original"] = record.get("bbox_original")
            extra["source_stage"] = stage
            extra["source_dataset"] = None
            extra["source_sample_id"] = None
            extra["imported_verified_only"] = True
            target.add_sample(extra)
            annotate(extra, stage, record, crop_path)

        counts = Counter(target.values("identity_status"))
        if len(target) != 1325 or counts.get("verified") != 301 or counts.get("unverified") != 1024:
            raise RuntimeError(f"Post-write count mismatch: samples={len(target)}, statuses={counts}")
        target.save()
        print("=" * 72)
        print(f"Dataset: {DATASET_NAME}")
        print(f"Samples: {len(target)} | Verified: {counts['verified']} | Unverified: {counts['unverified']}")
        print("Status: PASS — original datasets and files unchanged")
    except Exception:
        if target is not None and fo.dataset_exists(DATASET_NAME):
            fo.delete_dataset(DATASET_NAME)
            print("Rolled back incomplete new dataset")
        raise


if __name__ == "__main__":
    main()
