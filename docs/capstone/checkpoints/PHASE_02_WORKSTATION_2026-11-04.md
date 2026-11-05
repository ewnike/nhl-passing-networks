# NHL Capstone — Phase 02 Research Workstation Checkpoint

Date: 2026-11-04
Status: Active development

## Capstone Scope

The capstone has three required capabilities:

1. Player detection, tracking, and identification.
2. Passing-attempt recognition and annotation.
3. Descriptive player-level and spatial passing networks.

Predictive passing-lane optimization and pass-success probabilities
are reserved for future research.

## Governing Principle

Build one reusable data infrastructure supporting multiple experiments.

Do not create separate incompatible annotation datasets for each model.

## Primary Player Identification Architecture

YOLO detection
→ BoT-SORT tracking
→ Triplet-loss-trained Re-ID
→ Jersey-number recognition
→ Temporal identity reconciliation
→ Hockey-specific lineup and spatial constraints

## Experiment Status

### Experiment 07D

Original ResNet-18 cosine-similarity baseline preserved.

### Experiment 07F

Expanded ResNet-18 evaluation completed.

Track-disjoint Top-1: 28.22%
Track-disjoint Top-3: 53.37%

Evaluation remains exploratory because tracks are not necessarily
independent game sequences.

### Experiment 07G

Grey-jersey enhancement pilot completed.

24 original Fribourg crops.
96 comparison images.
9 players represented.

Basic contrast enhancement did not demonstrate a consistent
qualitative improvement in jersey-number readability.

### Identity Milestone

440 verified observations.
41 of 44 roster identities verified.
8 candidate observations.
Zero normalization issues in the final consolidated audit.

## FiftyOne Infrastructure

Consolidated dataset:

swiss_nl_g01_identity_review_consolidated_v1

Samples: 1325
Verified: 301
Unverified: 1024

Original FiftyOne datasets remain unchanged.

Video datasets:

swiss_nl_g01_video_review_pilot_v1
swiss_nl_g01_video_review_audio_v1

G01 Period 1, 330–360 seconds.

Video: 750 frames at 25 FPS.
Audio-enabled pilot: H.264 video and AAC audio.

Video playback and commentary confirmed working.

## Whisper Transcription

Model: faster-whisper small
Device: CPU
Compute type: INT8
Language: English

Five timestamped commentary segments successfully transcribed.

The pilot uses extracted 16 kHz mono PCM audio supplied
as a NumPy array to avoid a PyAV compatibility issue.

Raw transcripts and manifests are preserved separately.

## Hockey Research Workstation

Planned integrated capabilities:

- Video playback with optional audio.
- Player detection and track review.
- Identity verification.
- Approximately 30 diverse player crops per participating player.
- Commentary transcription and optional human dictation.
- Passing-attempt annotation.
- Pixel-coordinate annotation.
- Rink landmark association.
- Structured data export.
- SHA-256 integrity validation.

## Probabilistic Lineup Inference

Proposed research extension within player identification:

Use official roster information, shift timing, line combinations,
manpower state, spatial positioning, appearance embeddings,
and verified identity anchors to constrain player assignments.

Official shift-level availability has not yet been confirmed.

Do not assume total time on ice provides exact shift intervals.

## Next Engineering Milestone

Import existing 07E5 player detections, track identifiers,
and verified identities into the working G01 video dataset.

Acceptance criteria:

1. Video plays correctly.
2. Player bounding boxes display at the correct frames.
3. Verified identities display with official SIHF IDs.
4. Original detection and annotation artifacts remain unchanged.
5. Source-frame and clip-frame mappings are validated.

## Subsequent Milestones

1. Timestamped review notes.
2. Passing-event annotation.
3. Pixel-coordinate marking.
4. FiftyOne teammate workflow.
5. G02 acquisition pilot.
6. Expansion toward approximately 8,800 verified player crops.
7. Triplet-loss Re-ID training and evaluation.

## Research Integrity

Preserve original Experiment 07D, 07F, and 07G outputs.

Do not silently overwrite annotations or manifests.

Maintain verified, candidate, and model-predicted identities
as distinct evidence categories.

Keep source-video timestamps separate from official game-clock time.