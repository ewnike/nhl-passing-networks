#!/usr/bin/env python3
"""
Experiment 07D — ResNet-18 Player Appearance Embedding Baseline

Extract 512-dimensional appearance embeddings from verified player
crops and calculate pairwise cosine similarities.

Development-set feasibility experiment, not identity accuracy evaluation.

Original images, tracking data, and identity records are read-only.
Refuses to overwrite existing experiment outputs.
"""

import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from torchvision.models import ResNet18_Weights, resnet18

ROOT = Path(
    "local_artifacts/hockeyai_test/"
    "swiss_nl_2026_finals/G01/"
    "experiment_07/identity_reference"
)

CROPS = ROOT / "appearance_crops"

MANIFEST = CROPS / "appearance_reference_manifest.json"

OUTPUT = ROOT.parent / "embedding_baseline"

WEIGHTS = ResNet18_Weights.IMAGENET1K_V1


def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def verify_cosine_math():
    """Verify normalized dot-product calculations."""

    a = np.array([3.0, 4.0])
    b = np.array([4.0, -3.0])
    c = np.array([6.0, 8.0])

    def similarity(x, y):
        return np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))

    assert np.isclose(similarity(a, b), 0.0)
    assert np.isclose(similarity(a, c), 1.0)
    assert np.isclose(similarity(a, -c), -1.0)

    print("Cosine similarity mathematical checks: PASS")


def main():
    from PIL import Image

    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite experiment output: {OUTPUT}")

    verify_cosine_math()

    records = json.loads(MANIFEST.read_text())

    if not records:
        raise ValueError("Appearance manifest is empty.")

    keys = [(int(r["frame_index"]), r["track_uid"]) for r in records]

    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate observations in manifest.")

    paths = []

    for record in records:
        path = CROPS / record["filename"]

        if not path.is_file():
            raise FileNotFoundError(path)

        if not record.get("player_id"):
            raise ValueError(f"Missing player_id: {record['filename']}")

        paths.append(path)

    # CPU for deterministic, portable baseline behavior.
    device = torch.device("cpu")

    torch.manual_seed(7)

    model = resnet18(weights=WEIGHTS)

    # Remove the ImageNet classification layer.
    model.fc = torch.nn.Identity()

    model.eval()
    model.to(device)

    preprocess = WEIGHTS.transforms()

    vectors = []

    with torch.inference_mode():
        for record, path in zip(records, paths):
            with Image.open(path) as image:
                tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)

            embedding = model(tensor).squeeze(0).cpu().numpy()

            if embedding.shape != (512,):
                raise ValueError(f"Unexpected embedding shape: {embedding.shape}")

            if not np.all(np.isfinite(embedding)):
                raise ValueError(f"Non-finite embedding: {path}")

            vectors.append(embedding)

            print(f"Embedded: {record['filename']} | player_id={record['player_id']}")

    embeddings = np.stack(vectors).astype(np.float32)

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)

    if np.any(norms <= 0):
        raise ValueError("Zero-length embedding detected.")

    normalized = embeddings / norms

    # Cosine similarity equals the dot product of unit vectors.
    similarity = normalized @ normalized.T

    if not np.allclose(similarity, similarity.T, atol=1e-6):
        raise ValueError("Similarity matrix is not symmetric.")

    if not np.allclose(np.diag(similarity), 1.0, atol=1e-6):
        raise ValueError("Similarity matrix diagonal is invalid.")

    labels = [
        f"{r['player_name']}\n{r['frame_index']} / {r['track_uid']}" for r in records
    ]

    pairs = []

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            same_player = records[i]["player_id"] == records[j]["player_id"]

            pairs.append(
                {
                    "image_a": records[i]["filename"],
                    "image_b": records[j]["filename"],
                    "player_a": records[i]["player_id"],
                    "player_b": records[j]["player_id"],
                    "same_player": same_player,
                    "cosine_similarity": float(similarity[i, j]),
                }
            )

    same = [p["cosine_similarity"] for p in pairs if p["same_player"]]

    different = [p["cosine_similarity"] for p in pairs if not p["same_player"]]

    OUTPUT.mkdir(parents=True)

    np.save(OUTPUT / "embeddings.npy", embeddings)

    np.save(OUTPUT / "normalized_embeddings.npy", normalized)

    with (OUTPUT / "cosine_similarity.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["image"] + [r["filename"] for r in records])

        for i, record in enumerate(records):
            writer.writerow([record["filename"]] + [float(x) for x in similarity[i]])

    with (OUTPUT / "pairwise_comparisons.csv").open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "image_a",
                "image_b",
                "player_a",
                "player_b",
                "same_player",
                "cosine_similarity",
            ],
        )
        writer.writeheader()
        writer.writerows(pairs)

    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(similarity, vmin=-1, vmax=1, cmap="coolwarm")

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))

    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    ax.set_yticklabels(labels, fontsize=8)

    for i in range(len(records)):
        for j in range(len(records)):
            ax.text(
                j, i, f"{similarity[i, j]:.3f}", ha="center", va="center", fontsize=9
            )

    ax.set_title("Experiment 07D — ResNet-18 Appearance Cosine Similarity")

    fig.colorbar(image, ax=ax, label="Cosine similarity")

    fig.tight_layout()

    fig.savefig(OUTPUT / "similarity_heatmap.png", dpi=180)

    plt.close(fig)

    metadata = {
        "experiment": "07D",
        "model": "ResNet-18",
        "weights": WEIGHTS.name,
        "embedding_dimension": 512,
        "device": str(device),
        "torch_version": torch.__version__,
        "input_manifest": str(MANIFEST),
        "input_manifest_sha256": sha256(MANIFEST),
        "input_images": [
            {
                "filename": r["filename"],
                "player_id": r["player_id"],
                "sha256": sha256(path),
            }
            for r, path in zip(records, paths)
        ],
        "observations": len(records),
        "unique_players": len({r["player_id"] for r in records}),
        "same_player_pairs": len(same),
        "different_player_pairs": len(different),
        "mean_same_player_similarity": (float(np.mean(same)) if same else None),
        "mean_different_player_similarity": (
            float(np.mean(different)) if different else None
        ),
        "evaluation_status": "development_smoke_test",
    }

    (OUTPUT / "experiment_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )

    print("\nEXPERIMENT 07D — RESULTS")
    print("-" * 65)

    print("Embeddings:", embeddings.shape)
    print("Same-player pairs:", len(same))
    print("Different-player pairs:", len(different))

    if same:
        print("Mean same-player similarity:", round(float(np.mean(same)), 4))

    if different:
        print("Mean different-player similarity:", round(float(np.mean(different)), 4))

    print("\nSaved:", OUTPUT)
    print("Original experimental data unchanged.")


if __name__ == "__main__":
    main()
