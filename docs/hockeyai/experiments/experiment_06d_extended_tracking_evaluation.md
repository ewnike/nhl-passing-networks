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