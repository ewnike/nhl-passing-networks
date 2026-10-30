# Experiment 06D — Extended HockeyAI and BoT-SORT Tracking Evaluation

**Date:** 2026-10-29
**Game:** Swiss National League Finals — G01
**Period:** 1
**Experiment:** 06D
**Status:** Stages 6D1 and 6D2 completed; camera-cut-aware comparison pending.

## 1. Research Objective

Evaluate HockeyAI player detection and BoT-SORT tracking over a longer continuous broadcast recording containing multiple camera perspectives.

Extend the original 75-frame Experiment 06 baseline to 750 consecutive frames while preserving the original model, inference parameters, and tracker configuration.

Investigate the effects of abrupt broadcast camera transitions on track continuity, track initialization, and identity association.

## 2. Experimental Dataset

Source video:

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/periods/G01_P1.mp4`

Selected interval:

- Video start: 300.00 seconds
- Video end: 330.00 seconds
- Duration: 30 seconds
- Frame rate: 25 FPS
- Resolution: 1920 × 1080
- Extracted frames: 750
- Frame numbering: 0000–0749
- Sequential frame validation: PASSED

The selected interval contains active gameplay, consistent lighting, and two confirmed broadcast camera transitions.

## 3. Detection and Tracking Configuration

Model: `HockeyAI_model_weight.pt`

Framework: Ultralytics 8.3.214

Tracker: BoT-SORT

Configuration:

- Confidence threshold: 0.15
- Inference image size: 1280
- Processing device: CPU
- Tracked classes: goalie (3), player (4)
- Tracker persistence: enabled
- Global motion compensation: sparseOptFlow
- Appearance reidentification: disabled
- Track buffer: 30
- Camera-cut resets: disabled

The original BoT-SORT configuration was preserved.

Stage 6D2 independently reran detection and tracking rather than directly consuming saved Stage 6A detections.

## 4. Stage 6D1 — Camera-Cut Identification

A frame-to-frame HSV histogram comparison was performed across 749 consecutive transitions.

Two major discontinuities were identified and independently confirmed through visual inspection.

| Transition | Clip time | Histogram distance | Camera change |
|---|---:|---:|---|
| 0132 → 0133 | 5.32 s | 0.3017 | Wide → Close-up |
| 0270 → 0271 | 10.84 s | 0.3331 | Close-up → Wide |

The resulting camera segments are:

| Segment | Frames | Duration | View |
|---|---|---:|---|
| A | 0000–0132 | 5.32 s | Elevated wide-angle |
| B | 0133–0270 | 5.52 s | Ice-level close-up |
| C | 0271–0749 | 19.16 s | Elevated wide-angle |

These boundaries were established using numerical discontinuities and human visual confirmation.

The histogram analysis does not independently establish the absence of additional camera transitions.

## 5. Stage 6D2 — Full Broadcast Tracking Baseline

BoT-SORT processed all 750 frames while retaining tracker state across both camera cuts.

Results:

| Metric | Result |
|---|---:|
| Frames processed | 750 |
| Track observations | 6,482 |
| Unique track IDs | 86 |
| Mean observations per frame | 8.64 |
| Processing time | 171.52 seconds |
| Mean processing time per frame | 0.229 seconds |

The experiment completed without modifying the original source footage or previous tracking results.

### Longest Tracks

| Track ID | Observed frames | Span | Missing | Coverage |
|---|---:|---:|---:|---:|
| 196 | 478 | 478 | 0 | 1.000 |
| 199 | 478 | 478 | 0 | 1.000 |
| 201 | 464 | 478 | 14 | 0.971 |
| 195 | 451 | 478 | 27 | 0.944 |
| 192 | 449 | 478 | 29 | 0.939 |
| 285 | 265 | 271 | 6 | 0.978 |
| 310 | 230 | 230 | 0 | 1.000 |
| 275 | 218 | 225 | 7 | 0.969 |
| 198 | 207 | 208 | 1 | 0.995 |
| 278 | 195 | 226 | 31 | 0.863 |

Five of the longest tracks began at frame 0272, immediately after the second camera transition.

High observation coverage does not independently establish correct physical player identity.

## 6. Camera-Cut Tracking Behavior

### First Camera Cut: Frames 0132 → 0133

Frame 0132 contained eight tracked observations.

Frame 0133 contained zero tracked observations.

Frame 0134 contained three tracked observations with IDs 65, 66, and 67.

No IDs were shared between the last pre-cut frame and the first post-cut frame.

### Second Camera Cut: Frames 0270 → 0271

Frame 0270 contained five tracked observations.

Frame 0271 contained zero tracked observations.

Frame 0272 contained ten tracked observations with IDs 192–201.

These ten IDs remained present through frame 0276.

### Recovery Observation

In both transitions, tracked observations resumed in the second frame of the new camera view.

At 25 FPS, the interval between the first and second post-cut frames is 40 milliseconds.

This observation does not establish that BoT-SORT explicitly detected the camera cuts or reset its internal state.

## 7. Detection-Only Camera-Cut Diagnostic

Separate HockeyAI detection-only inference was performed on six selected frames.

| Frame | Player detections | Goalie detections | Total |
|---|---:|---:|---:|
| 0132 | 7 | 1 | 8 |
| 0133 | 2 | 1 | 3 |
| 0134 | 2 | 1 | 3 |
| 0270 | 6 | 1 | 7 |
| 0271 | 9 | 1 | 10 |
| 0272 | 9 | 1 | 10 |

The detector produced eligible player and goalie detections immediately after both camera transitions.

The absence of tracked observations in frames 0133 and 0271 therefore cannot be attributed simply to an inability of HockeyAI to detect eligible objects in separate inference.

However, the detection-only diagnostic was conducted independently of the original tracking run.

The exact internal tracker behavior responsible for the zero-observation frames remains undetermined.

## 8. Interpretation

The extended baseline demonstrates that default BoT-SORT can produce sustained track observations during continuous wide-angle gameplay.

Both confirmed camera transitions coincide with immediate loss of saved tracked observations and the subsequent appearance of new tracking identities.

The observed behavior is consistent with track-association disruption and subsequent initialization or confirmation of new tracks.

The precise internal mechanism has not yet been established.

The experiment does not establish that track IDs correspond consistently to physical players throughout their lifespans.

## 9. Limitations

1. Track coverage measures observation continuity, not verified identity accuracy.
2. Camera-cut detection was based on histogram differences and targeted human inspection.
3. Detection-only diagnostics were performed in a separate inference run.
4. No independently annotated ground-truth player identities were established for the full 750-frame sequence.
5. The experiment did not calculate IDF1, HOTA, or ground-truth identity-switch counts.
6. No appearance-based reidentification was enabled.
7. The baseline intentionally retained tracker state across camera cuts.
8. The experiment did not establish puck possession or passing events.

## 10. Reproducibility

Tracking script:

`scripts/hockeyai/run_g01_botsort_experiment_06d.py`

Input frames:

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/frames/P1_experiment_06d_300_330/`

Generated results:

`local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_06/stage_6d/full_broadcast_baseline/`

Key artifacts:

- `tracks.json`
- `track_observations.csv`
- `track_summary.csv`
- `tracking_metadata.json`
- `botsort_config.yaml`
- `annotated_frames/`

The baseline artifacts should be preserved unchanged before subsequent tracking experiments.

## 11. Next Research Step

Conduct Experiment 06D3 using explicit tracker resets at the confirmed camera transitions.

Compare the reset-aware experiment against the preserved Stage 6D2 baseline.

Maintain identical detection settings and tracker configuration.

Evaluate observation continuity, track fragmentation, and camera-boundary behavior.

Use separate track-ID namespaces across tracker resets.

Independent visual identity validation remains necessary before claiming improvements in player identity accuracy.

**Stage 6D1: COMPLETE**

**Stage 6D2: COMPLETE**

**Stage 6D3: PLANNED**

**Physical player identity accuracy: NOT YET ESTABLISHED**

---

## 12. AWS S3 Archival and Integrity Verification

**Archive date:** 2026-10-29
**Experiment:** G01 — Experiment 06D2
**Archive status:** COMPLETE — SHA-256 VERIFIED

### 12.1 Research Objective

Preserve the original Experiment 06D2 tracking outputs in AWS S3 before conducting additional experiments involving camera-cut-aware tracking, tracker configuration changes, or appearance-based reidentification.

Establish an independently verifiable baseline that can be restored and compared against subsequent experimental results.

### 12.2 Archive Location

**AWS S3 bucket:**

`ewnike-nhl-passing-networks-2026`

**Archive prefix:**

`experiments/swiss_nl_2026_finals/G01/experiment_06/stage_6d2/full_broadcast_baseline/`

The archive preserves the original Stage 6D2 output directory structure.

### 12.3 Archived Artifacts

The archive contains 755 objects:

- 750 annotated tracking frames.
- `tracks.json`
- `track_observations.csv`
- `track_summary.csv`
- `tracking_metadata.json`
- `botsort_config.yaml`

**Total archived size:** 391,755,263 bytes (approximately 373.6 MiB).

The original source footage, model weights, and local experimental outputs were not modified during archival.

The experiment's Python implementation and research documentation are preserved separately in Git.

### 12.4 SHA-256 Manifest

A SHA-256 checksum manifest was generated for all 755 local baseline files.

**Local manifest:**

`local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_06/stage_6d/stage_6d2_sha256_manifest.txt`

**S3 manifest:**

`experiments/swiss_nl_2026_finals/G01/experiment_06/stage_6d2/stage_6d2_sha256_manifest.txt`

The manifest contains 755 entries, each associating a relative file path with its SHA-256 digest.

The manifest is stored outside the baseline archive prefix so that the verified 755-object inventory remains unchanged.

### 12.5 Integrity Verification Procedure

The following verification steps were performed:

1. Uploaded the baseline directory to AWS S3.
2. Compared local file counts against the S3 object inventory.
3. Confirmed that a subsequent AWS CLI synchronization dry run reported no pending transfers.
4. Generated SHA-256 checksums for the 755 local files.
5. Performed local checksum verification.
6. Independently streamed all 755 archived S3 objects and recalculated their SHA-256 checksums.
7. Compared every remote checksum against the local manifest.
8. Uploaded the checksum manifest separately to S3.

Remote verification was performed using:

`scripts/aws/verify_experiment_06d2_s3.py`

The verification procedure did not modify the archived S3 objects or the local experimental files.

### 12.6 Verification Results

| Verification metric | Result |
|---|---:|
| Expected baseline objects | 755 |
| S3 baseline objects | 755 |
| Inventory comparison | PASS |
| SHA-256 checksums verified | 755 |
| SHA-256 mismatches | 0 |
| Missing S3 objects | 0 |
| Unexpected S3 objects | 0 |
| Remote SHA-256 integrity | PASS |
| Checksum manifest uploaded | YES |

**Verification conclusion:**

All 755 archived S3 objects matched the SHA-256 fingerprints recorded in the local manifest at the time of verification.

This establishes byte-for-byte integrity of the archived Experiment 06D2 baseline relative to the checksum manifest.

### 12.7 Preservation Limitations

Successful checksum verification establishes the integrity of the archived objects at the time of testing.

It does not independently establish permanent immutability, future availability, or protection against accidental deletion.

Long-term archival protection depends on the AWS S3 bucket's versioning, access controls, retention policies, and backup configuration.

These controls were not evaluated as part of this verification.

### 12.8 Research Status

**Experiment 06D2 tracking baseline: COMPLETE**

**GitHub code and documentation preservation: COMPLETE**

**AWS S3 baseline upload: COMPLETE**

**Remote SHA-256 integrity verification: PASS**

**SHA-256 manifest archival: COMPLETE**

**Experiment 06D3 camera-cut-aware tracking comparison: PENDING**

The preserved Experiment 06D2 baseline will serve as the reference for subsequent tracking experiments.

---

## 13. Stage 6D3 — Camera-Cut-Aware Tracking Comparison

**Date:** 2026-10-29
**Status:** Quantitative evaluation complete; physical player identity validation pending.

### 13.1 Research Objective

Evaluate whether initializing independent BoT-SORT tracking sessions at confirmed broadcast camera cuts improves immediate tracking-observation availability without materially changing tracking outputs during continuous-camera segments.

Compare the preserved Stage 6D2 persistent-tracker baseline against Stage 6D3 using identical source frames, HockeyAI model weights, inference parameters, and BoT-SORT configuration.

### 13.2 Experimental Configuration

Both experiments processed the same 750 consecutive frames from G01 Period 1, corresponding to video time 300–330 seconds.

| Parameter | Stage 6D2 | Stage 6D3 |
|---|---|---|
| Frames | 750 | 750 |
| Model | HockeyAI | HockeyAI |
| Tracker | BoT-SORT | BoT-SORT |
| Confidence threshold | 0.15 | 0.15 |
| Image size | 1280 | 1280 |
| Device | CPU | CPU |
| Appearance ReID | Disabled | Disabled |
| Tracker persistence | Entire sequence | Within camera segments |
| Camera-cut resets | Disabled | Enabled |

Stage 6D3 created independent YOLO/BoT-SORT tracking sessions at frames 0000, 0133, and 0271.

The camera segments were:

- Segment A: frames 0000–0132
- Segment B: frames 0133–0270
- Segment C: frames 0271–0749

Segment-qualified track identifiers were introduced to prevent numerical track-ID collisions across independent sessions.

### 13.3 Tracking Results

| Metric | Stage 6D2 | Stage 6D3 | Difference |
|---|---:|---:|---:|
| Frames processed | 750 | 750 | 0 |
| Track observations | 6,482 | 6,495 | +13 |
| Unique track identities | 86 | 86 | 0 |
| Processing time | 171.52 s | 168.06 s | −3.46 s |
| Longest track | 478 frames | 479 frames | +1 |

The reset-aware experiment produced 13 additional observations, representing approximately 0.20% more observations than the persistent baseline.

Runtime differences were not evaluated through repeated trials and should not be interpreted as evidence of improved processing efficiency.

### 13.4 Camera-Cut Recovery

Frame-level comparison established that all 13 additional observations occurred at the two confirmed camera-cut frames.

| Camera-cut frame | Stage 6D2 | Stage 6D3 | Difference |
|---|---:|---:|---:|
| 0133 | 0 | 3 | +3 |
| 0271 | 0 | 10 | +10 |
| **Total** | **0** | **13** | **+13** |

No differences in observation counts were found across the remaining 748 frames.

The results demonstrate that independent tracking-session initialization eliminated the immediate post-cut observation gaps observed in Stage 6D2.

### 13.5 Bounding-Box Agreement

A read-only spatial comparison was performed using the saved tracking CSV files from both experiments.

The diagnostic excluded camera-cut frames 0133 and 0271.

Bounding boxes were matched within each frame using class-constrained, one-to-one assignment based on Intersection over Union (IoU).

A minimum IoU threshold of 0.50 was required for a valid match.

Results:

| Metric | Result |
|---|---:|
| Frames evaluated | 748 |
| Matched bounding-box pairs | 6,482 |
| Unmatched observations | 0 |
| Frames with unmatched observations | 0 |
| Mean matched IoU | 0.999909 |
| Median matched IoU | 1.000000 |
| Minimum matched IoU | 0.974613 |

All observations outside the two camera-cut frames were successfully matched.

The mean matched IoU was approximately 0.9999, indicating near-identical bounding-box geometry between the two experiments.

These results establish strong spatial agreement but do not independently establish track-ID correspondence or physical player identity accuracy.

### 13.6 Interpretation

The comparison supports the conclusion that initializing independent tracking sessions at confirmed camera cuts can eliminate immediate post-cut observation gaps.

In this experiment, the reset-aware implementation recovered 13 observations without changing per-frame observation counts elsewhere.

Spatial agreement outside the camera-cut frames was exceptionally high.

The results support camera-cut-aware tracking initialization as a practical pipeline design choice for broadcast hockey footage.

However, the experiment does not establish improved physical player identity consistency or reduced identity-switch frequency.

### 13.7 Limitations

1. The comparison evaluated one 30-second broadcast interval containing two confirmed camera cuts.
2. Bounding-box matching does not establish physical player identity.
3. No ground-truth identity annotations were available for the full sequence.
4. Stage 6D3 used fresh YOLO model instances rather than directly resetting existing tracker objects.
5. Runtime differences were not evaluated through repeated trials.
6. Results may differ under other camera transitions, lighting conditions, and gameplay situations.
7. No puck-possession or passing-event accuracy was evaluated.

### 13.8 Reproducibility

**Stage 6D3 script:**

`scripts/hockeyai/run_g01_botsort_experiment_06d3.py`

**Stage 6D3 output directory:**

`local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_06/stage_6d/camera_cut_aware_baseline/`

Generated artifacts include:

- `tracks.json`
- `track_observations.csv`
- `track_summary.csv`
- `tracking_metadata.json`
- `botsort_config.yaml`
- `annotated_frames/`

The original Stage 6D2 baseline remains preserved separately and was not modified.

### 13.9 Research Status

**Stage 6D3 execution: COMPLETE**

**Camera-cut recovery comparison: COMPLETE**

**Bounding-box spatial agreement: VERIFIED**

**Physical player identity accuracy: NOT YET ESTABLISHED**

**Stage 6D3 archival preservation: PENDING**

**Stage 6D4 extended identity validation: PLANNED**

## 14. Stage 6D3 — AWS S3 Archival and Integrity Verification

**Archive date:** 2026-10-30
**Experiment:** G01 — Stage 6D3
**Status:** COMPLETE — SHA-256 VERIFIED

### 14.1 Archive Location

The camera-cut-aware BoT-SORT tracking baseline was archived in AWS S3 to preserve the original experimental outputs for reproducibility and comparison with Stage 6D2.

**S3 bucket:** `ewnike-nhl-passing-networks-2026`

**Archive prefix:**

`experiments/swiss_nl_2026_finals/G01/experiment_06/stage_6d3/camera_cut_aware_baseline/`

The archive contains **755 objects totaling 388,203,674 bytes**, including 750 annotated frames and five tracking, configuration, and metadata files.

### 14.2 SHA-256 Integrity Verification

A SHA-256 manifest was generated for all 755 local experimental files. Local checksum verification completed successfully.

All 755 archived S3 objects were subsequently retrieved through read-only streaming and independently hashed using SHA-256.

| Verification metric | Result |
|---|---:|
| Expected objects | 755 |
| Archived S3 objects | 755 |
| SHA-256 matches | 755 |
| Checksum failures | 0 |
| Inventory comparison | PASS |
| Remote integrity verification | **PASS** |

The verification established byte-for-byte agreement between the archived S3 objects and the checksums recorded in the local manifest at the time of testing.

No original experimental files or S3 objects were modified during verification.

### 14.3 Reproducibility and Preservation

**SHA-256 manifest:**

`experiments/swiss_nl_2026_finals/G01/experiment_06/stage_6d3/stage_6d3_sha256_manifest.txt`

**Verification script:**

`scripts/aws/verify_experiment_06d3_s3.py`

The manifest is stored outside the baseline archive prefix to preserve the verified 755-object inventory.

The Stage 6D3 archive is maintained separately from the previously verified Stage 6D2 persistent-tracking baseline.

Successful checksum verification establishes integrity at the time of testing but does not independently guarantee future availability or immutability.

### 14.4 Final Status

**Stage 6D3 experimental evaluation: COMPLETE**

**AWS S3 archival: COMPLETE**

**Local and remote SHA-256 verification: PASS — 755/755**

**Checksum manifest archival: COMPLETE**

**Stage 6D4 — Extended Player Identity Validation: NEXT**