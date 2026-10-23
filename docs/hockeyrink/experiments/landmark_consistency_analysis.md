# HockeyRink Landmark Consistency Analysis

**Project:** NHL Puck Tracking & Passing Networks  
**Research area:** Rink landmark detection, geometric consistency, and homography  
**Status:** Active research  
**Last updated:** 2026-10-22

---

## 1. Purpose

This document records experimental findings concerning the geometric consistency and accuracy of rink landmark predictions produced by the HockeyRink pose-estimation model.

Research objectives:

1. Evaluate landmark predictions on broadcast hockey footage.
2. Compare predicted landmarks with the project's canonical 56-keypoint dictionary.
3. Identify geometric inconsistencies and model-localization errors.
4. Evaluate image-to-rink homography estimation.
5. Establish criteria for reliable rink calibration.
6. Document limitations and unresolved questions.

This document supplements [`docs/hockeyrink/hockeyrink_keypoints.md`](../hockeyrink_keypoints.md). The canonical landmark dictionary and its physical coordinates are maintained separately.

## 2. Model and Coordinate Reference

| Property | Value |
|---|---|
| Checkpoint | `local_artifacts/models/hockeyrink/HockeyRink.pt` |
| Provenance | Strong evidence of Mehdi's pretrained checkpoint; training configuration references `/home/mehdihou/D1/YOLO-Train/Train/config_pose.yaml` |
| Architecture | Ultralytics YOLO Pose |
| Ultralytics version | `8.3.214` |
| Keypoint shape | `[56, 3]` |
| Class | `rink` |
| Recorded training image size | `640` |
| SHA-256 | `c604cde0e455916478d33d66f2d54e73c8b27a81ee5ab0aebb0bdaa3988b3e3d` |

**Physical coordinate convention:** IIHF 60 m × 30 m rink, center ice at `(0, 0)`; X increases west to east, Y increases south to north; units are meters. The project's documented KP-0–KP-55 semantic mapping is used, but its correctness must still be assessed against the source model convention and observed rink geometry.

---

## 3. Experiment 01 — Single-Frame Homography

**Date:** 2026-10-22  
**Game:** Swiss National League Finals, G01  
**Period:** 1  
**Frame:** `frame_0010.jpg`  
**Status:** **Provisional** — estimated successfully; independent physical alignment validation pending.

### 3.1 Research question

Can the pretrained HockeyRink model provide sufficiently consistent landmark predictions to estimate a physically meaningful image-to-rink homography on Swiss National League broadcast footage?

### 3.2 Input data

| Property | Value |
|---|---|
| Source | FloHockey |
| Video | `G01_P1.mp4` |
| Resolution | 1920 × 1080 |
| Frame rate | 25 FPS |
| Pilot sample | First 60 seconds, sampled at 1 FPS |
| Frames | 60 |
| Manually assessed wide-angle frames | 58 |
| Manually assessed close-ups | `frame_0053.jpg`, `frame_0054.jpg` |
| Manual gameplay assessment | All 60 sampled frames appeared to show gameplay footage |

The camera view is predominantly elevated and wide-angle. The first pilot was initially described as showing the eastern offensive end, but `frame_0010.jpg` visibly includes center ice and neutral-zone landmarks; camera coverage varies with play.

### 3.3 Method

1. Run `HockeyRink.pt` pose inference and retain all 56 predicted keypoints per detected rink.
2. Select predictions at confidence ≥ `0.80` for the single-frame experiment.
3. Associate selected keypoint indices with physical coordinates documented in the project landmark dictionary.
4. Fit **rink-to-image** homography with OpenCV RANSAC, using a **5-pixel** reprojection threshold.
5. Invert the fitted matrix to obtain the **image-to-rink** transformation.
6. Record RANSAC classifications, pixel residuals, matrices, and an annotated overlay.

The 5-pixel RANSAC threshold is measured in **image pixels**, not meters.

### 3.4 Aggregate results

| Metric | Result |
|---|---:|
| Candidate landmarks | 8 |
| RANSAC inliers | 6 |
| RANSAC outliers | 2 |
| Inlier share | 75% |
| Mean inlier reprojection error | 1.545 px |
| Median inlier reprojection error | 1.703 px |
| Maximum inlier reprojection error | 2.751 px |

### 3.5 Landmark-level results

| KP | Landmark | Confidence | Residual (px) | RANSAC |
|---:|---|---:|---:|---|
| 20 | Western blue line / north boards | 0.9999 | 1.912 | Inlier |
| 22 | West neutral-zone north faceoff dot | 0.9998 | 1.870 | Inlier |
| 23 | West neutral-zone south faceoff dot | 0.9996 | 23.651 | **Outlier** |
| 24 | Center red line / north boards | 0.9978 | 0.903 | Inlier |
| 25 | Center-circle north intersection | 1.0000 | 2.751 | Inlier |
| 26 | Center-ice faceoff spot | 1.0000 | 15.045 | **Outlier** |
| 27 | Center-circle south intersection | 0.9992 | 1.536 | Inlier |
| 32 | East neutral-zone north faceoff dot | 0.8566 | 0.299 | Inlier |

Confidence values in the table are rounded; the raw predictions are retained in `detections.json`.

### 3.6 Visual observations and interpretation

#### KP-23 — West neutral-zone south faceoff dot

- **Observation:** In the saved overlay, the model prediction appears down and left of the painted faceoff dot. The homography-projected cross appears closer to the marking.
- **Interpretation:** Possible model-localization error, despite high confidence.
- **Status:** **Requires investigation.** A manual reference location has not yet been measured.

#### KP-26 — Center-ice faceoff spot

- **Observation:** The predicted point and homography-projected cross are separated by approximately 15 pixels. A large center-ice advertisement complicates visual identification of the exact spot.
- **Interpretation:** Could reflect localization error, point-definition ambiguity, or limitations of the fitted homography. Current evidence does not identify the cause.
- **Status:** **Unresolved.**

#### Six accepted landmarks

- **Observation:** KP-20, KP-22, KP-24, KP-25, KP-27, and KP-32 appear broadly aligned with expected rink markings in the inspected overlay.
- **Interpretation:** Their predictions are mutually consistent with the fitted planar transformation.
- **Status:** **Provisional** until independently measured against painted geometry.

### 3.7 Findings

1. **High confidence is not a guarantee of geometric consistency.** KP-23 and KP-26 both have confidence above 0.999 yet were rejected by RANSAC.
2. **A candidate homography is feasible.** Six of eight candidates form a consensus with mean inlier fitting error of 1.545 pixels.
3. **Inlier fitting error is not independent calibration accuracy.** These residuals measure agreement with points used in fitting, not absolute error in meters.
4. **Camera motion must be handled temporally.** A transformation estimated for one frame cannot be assumed valid after camera pan, tilt, or zoom.
5. **Landmark semantics remain consequential.** An incorrect KP-to-rink-coordinate correspondence can yield misleading calibration even when the fit looks numerically strong.

### 3.8 Limitations

- Single-frame experiment; no temporal stability assessment yet.
- No manually measured independent ground-truth pixel coordinates.
- No validated physical positioning error in meters.
- No held-out geometry overlay assessment yet.
- No tested robustness across close-ups, zooms, camera transitions, or other rink regions.
- Several accepted landmarks lie along the center red line; spatial distribution and numerical stability warrant further examination.
- Goal-crease coordinate audit remains separate and is not resolved by this neutral-zone experiment.

### 3.9 Reproducibility and artifacts

**Experiment script:** `scripts/hockeyrink/evaluate_g01_homography.py`

**Experiment outputs:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/`

| Artifact | Contents |
|---|---|
| `homography.json` | Fitted matrices, parameters, inlier mask, and landmark measurements |
| `landmark_residuals.csv` | Per-landmark confidence, observed/projected positions, and residuals |
| `homography_overlay.jpg` | Saved annotated broadcast frame for visual assessment |

**Upstream inference:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/rink_keypoint_pilot/detections.json`

**Source frame:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/frames/P1_pilot/frame_0010.jpg`

The numerical files and image are currently referenced as **local artifacts**; their Git/S3 preservation status has not been established in this document.

---

## 4. Planned Follow-up Experiments

---

# Experiment 02 — Projected Rink Geometry Validation

**Date:** 2026-10-22  
**Game:** Swiss National League Finals — G01  
**Period:** 1  
**Frame:** `frame_0010.jpg`  
**Status:** PROVISIONAL — Visual validation completed; quantitative alignment pending.

## Research Question

Does the homography estimated in Experiment 01 accurately project
known IIHF rink geometry onto the corresponding broadcast image?

## Methodology

The rink-to-image homography calculated in Experiment 01 was reused
without modification.

The following IIHF rink features were projected onto the original
broadcast frame:

- Western blue line: X = -7.65 m
- Center red line: X = 0.00 m
- Eastern blue line: X = +7.65 m
- Center faceoff circle: radius = 4.50 m
- Four neutral-zone faceoff spots: (±6.00 m, ±7.00 m)

No additional YOLO inference or homography estimation was performed.

## Visual Observations

### Observation 02.1 — Western Blue Line

The projected western blue line appears displaced to the left of
the painted blue line.

The displacement appears to increase toward the near-camera side
of the image.

**Assessment:** Visible alignment discrepancy.

### Observation 02.2 — Center Red Line

The projected center red line follows the approximate direction
of the painted center line.

However, the projected line appears displaced leftward toward
the lower portion of the image.

**Assessment:** Visible alignment discrepancy.

### Observation 02.3 — Center Faceoff Circle

The projected center faceoff circle approximately follows the
upper boundary of the painted circle.

The projected lower boundary extends beyond the painted circle.

**Assessment:** Projected circle size or perspective differs
from the visible marking.

### Observation 02.4 — Neutral-Zone Faceoff Spots

FO-1 and FO-3 appear reasonably aligned with their painted
faceoff spots.

FO-2, corresponding to KP-23, appears displaced down and left
relative to the painted spot.

This is consistent with the discrepancy observed during
Experiment 01.

**Assessment:** Mixed alignment quality.

### Observation 02.5 — Apparent Rink Tilt

During visual inspection, the rink geometry appeared to exhibit
a downward tilt.

The projected rink markings and actual painted markings appear
to have different perspective orientations.

The apparent discrepancy is more noticeable toward the
near-camera side of the image.

**Assessment:** Possible perspective-alignment discrepancy.

This observation does not establish that the physical rink
surface is tilted.

## Interpretation

The Experiment 01 homography produced a mean RANSAC inlier
reprojection error of 1.545 pixels.

However, Experiment 02 demonstrates that a low inlier
reprojection error does not necessarily guarantee accurate
alignment with the visible rink markings.

The observed discrepancies may be associated with:

- Landmark localization errors.
- Insufficient spatial distribution of reliable landmarks.
- Sensitivity to the selected RANSAC inlier set.
- Differences between predicted landmarks and physical markings.
- Camera perspective or lens-distortion effects.

These remain hypotheses rather than confirmed causes.

## Experiment Artifacts

**Script:**

`scripts/hockeyrink/project_g01_rink_geometry.py`

**Results directory:**

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_02/`

**Files:**

- `projected_rink_geometry.jpg`
- `geometry_projection_metadata.json`

**Source homography:**

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/homography.json`

## Preliminary Conclusion

The estimated homography captures several important features
of the broadcast rink geometry.

However, visible alignment discrepancies remain, particularly
along the western blue line, center red line, and center circle.

The transformation should not yet be treated as a validated
physical rink calibration.

**Experiment status: PROVISIONAL**

## Next Research Actions

1. Quantify projected-versus-painted line displacement.
2. Investigate the influence of KP-23 and KP-26.
3. Evaluate alternative landmark subsets.
4. Compare homographies across neighboring frames.
5. Preserve the original Experiment 01 homography as the baseline.

### Experiment 03 — Temporal Consistency

Compare frames `0009`, `0010`, and `0011` using already saved predictions. Examine landmark motion, confidence, RANSAC membership, and variation in the estimated homography.

### Experiment 04 — Full 60-Frame Pilot

Evaluate the complete pilot sequence, reporting fit success, inlier counts, residual distributions, camera-view failure cases, and temporal stability.

---

## 5. Research Status and Update Convention

**Current conclusion:** A mathematically consistent **candidate** image-to-rink transformation has been computed for one Swiss National League frame. Independent physical alignment and temporal validation remain pending.

For future experiments, append a dated section that distinguishes:

- **Measurement:** Values directly produced by scripts or manual annotation.
- **Observation:** What is visibly present in saved evidence.
- **Interpretation:** Proposed explanation, clearly marked as provisional when unverified.
- **Decision:** Whether the finding is confirmed, provisional, rejected, or requires investigation.
- **Next test:** Specific procedure capable of resolving the uncertainty.

Do not overwrite earlier findings silently; record revisions and their evidence.
