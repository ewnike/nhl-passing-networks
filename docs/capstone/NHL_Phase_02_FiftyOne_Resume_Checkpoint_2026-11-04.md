# NHL Puck Tracking & Passing Networks — Resume Checkpoint

**Date:** 2026-11-04
**Status:** Planning checkpoint; implementation not yet started
**Next work:** Phase 02 — FiftyOne video review and teammate annotation workflow

## Capstone scope and architecture

The capstone aims to (1) detect, track, and identify hockey players, (2) recognize passing attempts and associate participants when observable, and (3) construct descriptive player-level and spatial passing networks. Prediction of optimal passing lanes, counterfactual pass probabilities, and best-pass recommendations is **out of scope** for this capstone and reserved for a future project.

Primary experimental identity architecture: **YOLO/HockeyAI detection → BoT-SORT tracking → supervised triplet-loss Re-ID (initially ResNet-18) → complementary jersey-number recognition → constrained temporal identity fusion**. Use cosine similarity for embedding comparisons; investigate same-team hard-negative sampling and verified-identity clamping. OSNet is a comparison candidate. Walk-back training and generative Markov methods are optional research, not prerequisites.

**Governing principle:** One coherent, reusable data infrastructure supporting multiple experiments. Do not collect separate, incompatible annotations for each model.

The working capstone proposal is stored by the user in `docs/capstone/` in the local repository.

## Preserved research results

- Experiment 07D: original five-image ResNet-18 cosine-similarity feasibility baseline; preserve unchanged.
- Experiment 07E12: **440 verified identity observations**, 8 candidates, 41/44 verified roster identities, 0 normalization issues and 0 duplicate observation keys under the audit's namespace-safe deduplication convention. Legacy frame provenance still merits care.
- Experiment 07F: preserve unchanged. Exploratory track-disjoint Top-1 **28.22%**, Top-3 **53.37%**; temporal holdout Top-1 **12.5%** on only 16 queries and 2 query identities. Original verified appearance crops: **301** across **22** players; 16 have multiple track IDs. These crops cover about 90 seconds of P1 footage, so track separation is not proof of independent shifts.
- Experiment 07G Phase 1: 24 verified FRI crops from 9 players; 4 variants each (original, CLAHE, CLAHE+sharpening, CLAHE+denoising), 96 images. Initial qualitative review did not show consistent recovery of unreadable numbers. Preserve outputs at `local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_07/grey_jersey_recognition_07g/`; summary SHA-256 `6609deba7d0466fbe2578692cac905e3b6d18427205b155d6a00c71ba30149c3`.
- Experiment 07G Phase 2: **multi-frame jersey-number recognition** is the selected next recognition study. Initial guideline: about **30 diverse frames per player**, ideally 3–5 distinct tracklets, spanning rear/front/three-quarter/side and difficult unreadable views. Preserve readable identity anchors and uncertain frames distinctly; avoid redundant adjacent frames.

## Phase 02 — FiftyOne implementation plan

**Goal:** A teammate can select a game/period, review footage and player detections/tracklets, verify identities, and export validated crops and manifests **without writing Python heredocs**.

### Initial G01 pilot

Start with five FRI players, aiming for ~30 useful frames each (150 total as a planning target):

| Player | Jersey | Target |
|---|---:|---:|
| Marcus Sörensen | 9 | 30 |
| Julien Sprunger | 86 | 30 |
| Samuel Walser | 23 | 30 |
| Nathan Marchon | 97 | 30 |
| Reto Berra | 20 | 30 |

Prefer varied orientation, number visibility, blur/occlusion, and independent tracklets. These same records should support 07G number recognition and 07H triplet-loss Re-ID. Verified player identity and visible/readable jersey number are **different labels**.

### Workflow

1. Inventory existing FiftyOne datasets, scripts, and existing Experiment 07 detection/tracking/extraction/registration utilities; reuse working code.
2. Confirm the installed FiftyOne version's native video/frame navigation, annotation, and export capabilities before choosing UI extensions.
3. Import or reference G01 video without duplicating original source files; link detections, tracks, and known verified evidence.
4. Define common annotation fields: game, period, canonical source frame/time, source video, track ID, team, SIHF player ID, jersey number, orientation, number visibility/readability, blur, occlusion, verification status/method, bbox, provenance, and SHA-256.
5. Pilot review: open a period, jump to known frames, inspect one tracklet, confirm one identity, preserve evidence, export and validate.
6. Package CLI/app workflow and teammate instructions. Do not assume a local FiftyOne App is a multi-user collaborative service.
7. Test the process on G02 before scaling to the remaining six games. Plan least-privilege S3 access separately; preserve original source objects and experiment checkpoints.

### Definition of done for Phase 02 pilot

- G01 video and relevant frames are navigable in FiftyOne.
- Existing detections/tracklets and known identity evidence are inspectable.
- At least one end-to-end human-reviewed identity can be exported as a crop plus machine-readable annotation, with verified roster mapping and source provenance.
- Validation catches missing files, duplicates, invalid IDs, and checksum mismatches.
- A teammate can follow documented steps without manually editing Python scripts.
- Original 07D/07F/07G artifacts remain unchanged.

## When resuming after LSEG work

**First action:** Run a read-only inventory of existing FiftyOne-related scripts and datasets in the local `nhl-passing-networks` repository, then create a minimal G01 video-review pilot. Do not restart reconnaissance or change the established architecture. User will return after completing LSEG work; no background execution was scheduled.
