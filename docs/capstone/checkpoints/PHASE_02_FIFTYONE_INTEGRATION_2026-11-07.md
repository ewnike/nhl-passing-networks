# Phase 02 — FiftyOne Integration Checkpoint
Date: 2026-11-07
Project: NHL Puck Tracking & Passing Networks

## Status

G01 Experiment 07E5 video-identity integration completed.
Initial representative visual validation: PASS.

## Integrated Dataset

Dataset: swiss_nl_g01_video_identity_integrated_07e5_v1

- Video samples: 1
- Video frames: 750
- Frame rate: 25 FPS
- Resolution: 1920 x 1080
- Annotated frames: 261
- Player observations: 330
- Verified observations: 124
- Unverified observations: 206
- Identity-conflicted detections: 10

Video SHA-256:
4ac8237557aded0e1c7131f24582690b20469c52ee3114d97fa650a90acaceb7

Original source datasets and video files were not modified.

## Visual Validation

FiftyOne successfully displayed:
- Correctly positioned player bounding boxes.
- Human-verified player identities.
- Unverified observations.
- Annotations at multiple video timestamps.

Representative visual checks passed.

This does not establish exhaustive annotation accuracy or complete
player-detection coverage.

## Known Tracking Conflict

Track: E4_A:55

FiftyOne frame 629:
- Julien Sprunger #86, verified.

FiftyOne frame 692:
- Sven Jung #90, verified.
- Julien Sprunger #86 separately appears under E4_A:178.
- Beni Waidacher #25 appears under E4_A:159.

The precise tracking identity-switch frame remains undetermined.

Track identifiers must not be treated as verified player identities.

## Five-Player Pilot Inventory

Source dataset:
swiss_nl_g01_identity_review_consolidated_v1

Player | Verified observations | Initial target
--- | ---: | ---:
Marcus Sörensen #9 | 0 | 30
Julien Sprunger #86 | 13 | 30
Samuel Walser #23 | 3 | 30
Nathan Marchon #97 | 0 | 30
Reto Berra #20 | 27 | 30
TOTAL | 43 | 150

These counts represent verified observations, not necessarily
independent or training-approved images.

## Research Architecture

Maintain three independent, versioned research assets:

1. Verified Identity Database
2. Training Dataset
3. Model Registry

FiftyOne is the primary interface for teammate video review,
player identification, training-image selection, and evaluation.

Python/PyTorch handles model training.

Human verification does not automatically modify trained models.
Track IDs do not establish player identity.

## Next Starting Task

Build the G01 Player Verification and Training-Crop Review Workflow.

Implementation priorities:

1. Inspect FiftyOne 1.8.1 annotation and review capabilities.
2. Generate representative candidate observations without requiring
   teammates to review every video frame.
3. Establish player identity verification fields.
4. Establish review status and uncertainty handling.
5. Establish image-quality and training-approval fields.
6. Preserve track-switch and provenance information.
7. Implement versioned annotation export and validation.
8. Write teammate instructions and assignment procedures.

## Sunday Objective — November 8, 2026

Aim to deliver:
- A functioning teammate review pilot.
- Written annotation and quality-control procedures.
- Clearly defined five-player pilot assignments.
- A controlled submission and validation process.

Do not assume local FiftyOne automatically provides shared
multi-user collaboration.

## Preservation Notes

The integrated FiftyOne dataset is persistent in the local database.

Git preservation of scripts and this checkpoint does not constitute
a backup of the FiftyOne MongoDB dataset.

A separate validated dataset export and AWS S3 preservation
procedure remains necessary.

## Resume Instructions

Begin by reviewing this checkpoint.

Do not rerun integration or recreate existing datasets.

Preserve original observations, source video, and experiment artifacts.

Use incremental, validated changes.

Do not blanket-stage the Git worktree.
