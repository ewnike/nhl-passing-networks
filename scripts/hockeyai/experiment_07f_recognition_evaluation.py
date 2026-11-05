#!/usr/bin/env python3
"""Experiment 07F: frozen ResNet-18 + cosine-similarity player Re-ID baseline.

Read-only inputs. Creates a new output directory and refuses overwrites.
Track-disjoint results are exploratory: tracks may overlap in source time.
Temporal holdout uses P1 300-360s as gallery and 360-390s as queries.
"""

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from torchvision.models import ResNet18_Weights, resnet18

STAGES = {
    "07E2": "experiment_07/identity_reference/appearance_crops",
    "07E5": "experiment_07/stage_07e4/identity_reference/appearance_crops",
    "07E8": "experiment_07/stage_07e7/identity_reference/appearance_crops",
}
WEIGHTS = ResNet18_Weights.IMAGENET1K_V1


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_write(path, rows, fields):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def choose_path(directory, record):
    name = Path(record["filename"]).name
    candidate = directory / name
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing verified crop: {candidate}")
    return candidate


def load_records(root):
    records = []
    for stage, relative in STAGES.items():
        directory = root / relative
        manifest = directory / "appearance_reference_manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Expected list manifest: {manifest}")
        for item in data:
            if item.get("verification_method") != "human_visual_review":
                raise ValueError(
                    f"Unverified crop in {manifest}: {item.get('filename')}"
                )
            path = choose_path(directory, item)
            # The three stage-specific source directories cover contiguous P1 windows.
            offset = {"07E2": 300, "07E5": 330, "07E8": 360}[stage]
            time = item.get("video_time_seconds")
            if time is None:
                time = offset + int(item["frame_index"]) / 25.0
            time = float(time)
            if not offset - 0.5 <= time <= offset + 30.5:
                raise ValueError(f"Unexpected time {time}: {path}")
            records.append(
                {
                    "stage": stage,
                    "path": path,
                    "filename": path.name,
                    "player_id": str(item["player_id"]),
                    "player_name": str(item["player_name"]),
                    "team": str(item["team"]),
                    "track": f"{stage}:{item['track_uid']}",
                    "time": time,
                }
            )
    if len(records) != 301:
        raise ValueError(f"Expected 301 verified crops, found {len(records)}")
    return records


def embeddings_for(records, device, batch_size):
    torch.manual_seed(7)
    model = resnet18(weights=WEIGHTS)
    model.fc = torch.nn.Identity()
    model.eval().to(device)
    transform = WEIGHTS.transforms()
    vectors = []
    with torch.inference_mode():
        for start in range(0, len(records), batch_size):
            batch = []
            for rec in records[start : start + batch_size]:
                with Image.open(rec["path"]) as image:
                    batch.append(transform(image.convert("RGB")))
            output = model(torch.stack(batch).to(device)).cpu().numpy()
            vectors.append(output)
            print(f"Embedded {min(start + batch_size, len(records))}/{len(records)}")
    arr = np.concatenate(vectors).astype(np.float32)
    if arr.shape != (len(records), 512) or not np.isfinite(arr).all():
        raise RuntimeError("Invalid embedding array")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    if np.any(norms < 1e-10):
        raise RuntimeError("Zero-norm embedding")
    return arr / norms


def track_split(records):
    by_player = defaultdict(lambda: defaultdict(list))
    for i, rec in enumerate(records):
        by_player[rec["player_id"]][rec["track"]].append(i)
    gallery, query = [], []
    for player, tracks in sorted(by_player.items()):
        if len(tracks) < 2:
            continue
        # Largest track as gallery; all other tracks as queries.
        ordered = sorted(tracks.items(), key=lambda x: (-len(x[1]), x[0]))
        gallery.extend(ordered[0][1])
        for _, idxs in ordered[1:]:
            query.extend(idxs)
    return sorted(gallery), sorted(query)


def temporal_split(records):
    gallery = [i for i, r in enumerate(records) if r["time"] < 360]
    query = [i for i, r in enumerate(records) if r["time"] >= 360]
    known = {records[i]["player_id"] for i in gallery}
    query = [i for i in query if records[i]["player_id"] in known]
    return gallery, query


def evaluate(label, records, emb, gallery, query, output):
    # Gallery centroids by identity, avoiding bias toward players with more crops.
    by_id = defaultdict(list)
    for i in gallery:
        by_id[records[i]["player_id"]].append(i)
    identities = sorted(by_id)
    if not identities or not query:
        return {
            "status": "insufficient_shared_identities",
            "gallery_images": len(gallery),
            "query_images": len(query),
            "identities": len(identities),
        }
    centers = np.stack([emb[by_id[p]].mean(axis=0) for p in identities])
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    scores = emb[query] @ centers.T
    results = []
    for k, qi in enumerate(query):
        r = records[qi]
        order = np.argsort(-scores[k], kind="stable")
        overall = [identities[j] for j in order]
        team_order = [
            identities[j]
            for j in order
            if records[by_id[identities[j]][0]]["team"] == r["team"]
        ]
        if not team_order:
            raise RuntimeError(f"No same-team gallery identity for {r['filename']}")
        results.append(
            {
                "query_file": r["filename"],
                "true_player_id": r["player_id"],
                "true_name": r["player_name"],
                "team": r["team"],
                "track": r["track"],
                "video_time_seconds": round(r["time"], 3),
                "predicted_id": overall[0],
                "predicted_same_team_id": team_order[0],
                "top1": int(r["player_id"] == overall[0]),
                "top3": int(r["player_id"] in overall[:3]),
                "within_team_top1": int(r["player_id"] == team_order[0]),
                "within_team_top3": int(r["player_id"] in team_order[:3]),
                "true_identity_score": float(
                    scores[k, identities.index(r["player_id"])]
                ),
                "best_score": float(scores[k, order[0]]),
            }
        )
    csv_write(output / f"{label}_results.csv", results, list(results[0]))
    summary = {
        "status": "completed",
        "gallery_images": len(gallery),
        "query_images": len(query),
        "gallery_identities": len(identities),
        "query_identities": len({records[i]["player_id"] for i in query}),
        "top1": float(np.mean([r["top1"] for r in results])),
        "top3": float(np.mean([r["top3"] for r in results])),
        "within_team_top1": float(np.mean([r["within_team_top1"] for r in results])),
        "within_team_top3": float(np.mean([r["within_team_top3"] for r in results])),
    }
    # Confusion matrix: identity rows and predicted identity columns.
    matrix = np.zeros((len(identities), len(identities)), dtype=int)
    lookup = {p: j for j, p in enumerate(identities)}
    for row in results:
        matrix[lookup[row["true_player_id"]], lookup[row["predicted_id"]]] += 1
    fig, ax = plt.subplots(
        figsize=(max(8, len(identities) * 0.48), max(7, len(identities) * 0.48))
    )
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(identities)), identities, rotation=90, fontsize=7)
    ax.set_yticks(range(len(identities)), identities, fontsize=7)
    ax.set_xlabel("Predicted SIHF ID")
    ax.set_ylabel("True SIHF ID")
    ax.set_title(f"{label} — identity confusion matrix")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(output / f"{label}_confusion_matrix.png", dpi=160)
    plt.close(fig)
    return summary


def similarity_diagnostics(records, emb, output):
    # Use all 301 crops; same/different scores are descriptive and correlated.
    sims = emb @ emb.T
    ids = np.array([r["player_id"] for r in records])
    teams = np.array([r["team"] for r in records])
    upper = np.triu_indices(len(records), k=1)
    values = sims[upper]
    same = ids[upper[0]] == ids[upper[1]]
    within_team = teams[upper[0]] == teams[upper[1]]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(values[same], bins=35, alpha=0.6, label="Same player")
    ax.hist(
        values[(~same) & within_team],
        bins=35,
        alpha=0.6,
        label="Different player, same team",
    )
    ax.hist(values[~within_team], bins=35, alpha=0.5, label="Different team")
    ax.set_xlabel("Cosine similarity")
    ax.set_ylabel("Pair count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "similarity_distributions.png", dpi=160)
    plt.close(fig)
    # Per-player centroid heatmap, more interpretable than 301x301 pixel grid.
    by_id = defaultdict(list)
    for i, pid in enumerate(ids):
        by_id[pid].append(i)
    keys = sorted(by_id)
    centroids = np.stack([emb[by_id[p]].mean(axis=0) for p in keys])
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
    cm = centroids @ centroids.T
    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(cm, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(keys)), keys, rotation=90, fontsize=7)
    ax.set_yticks(range(len(keys)), keys, fontsize=7)
    ax.set_title("07F — ResNet-18 identity-centroid cosine similarity")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(output / "similarity_heatmap.png", dpi=160)
    plt.close(fig)
    return {
        "same_player_mean": float(values[same].mean()) if same.any() else None,
        "different_player_same_team_mean": float(values[(~same) & within_team].mean())
        if ((~same) & within_team).any()
        else None,
        "different_team_mean": float(values[~within_team].mean())
        if (~within_team).any()
        else None,
        "pair_count": int(len(values)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01"),
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")
    output = args.output or args.root / "experiment_07/recognition_evaluation_07f"
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    records = load_records(args.root)
    # Ensure all inputs are accessible BEFORE creating outputs.
    for r in records:
        if not r["path"].is_file():
            raise FileNotFoundError(r["path"])
    device = torch.device("cpu")
    print("Model: ResNet-18, weights:", WEIGHTS.name, "| device:", device)
    embeddings = embeddings_for(records, device, args.batch_size)
    output.mkdir(parents=True, exist_ok=False)
    np.save(output / "normalized_embeddings.npy", embeddings)
    input_rows = [
        {k: str(v) for k, v in r.items()} | {"sha256": digest(r["path"])}
        for r in records
    ]
    csv_write(output / "input_inventory.csv", input_rows, list(input_rows[0]))
    track_gallery, track_query = track_split(records)
    temporal_gallery, temporal_query = temporal_split(records)
    # The 360-390s holdout has limited overlapping identities; report coverage explicitly.
    summary = {
        "experiment": "07F",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": "ResNet-18",
        "weights": WEIGHTS.name,
        "embedding_dimension": 512,
        "source_crops": len(records),
        "source_players": len({r["player_id"] for r in records}),
        "torch_version": torch.__version__,
        "track_disjoint": evaluate(
            "track_disjoint", records, embeddings, track_gallery, track_query, output
        ),
        "temporal_holdout": evaluate(
            "temporal_holdout",
            records,
            embeddings,
            temporal_gallery,
            temporal_query,
            output,
        ),
        "similarity": similarity_diagnostics(records, embeddings, output),
        "limitations": [
            "Track-disjoint evaluation is exploratory: distinct tracker IDs may overlap in time.",
            "Temporal holdout covers only P1 300-390s; not cross-game generalization.",
            "Images from the same video are temporally correlated; uncertainty intervals not reported.",
            "Only players with gallery representation can be evaluated.",
            "The original 07D artifacts were not modified.",
        ],
    }
    (output / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "experiment": "07F",
        "files": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "output_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("\nEXPERIMENT 07F — RESULTS")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ("track_disjoint", "temporal_holdout", "similarity")
            },
            indent=2,
        )
    )
    print("Output:", output)
    print("Status: PASS")


if __name__ == "__main__":
    main()
