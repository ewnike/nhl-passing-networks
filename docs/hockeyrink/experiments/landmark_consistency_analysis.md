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

### Experiment 03 — Landmark Localization and Homography Sensitivity

Evaluate the sensitivity of the Experiment 01 homography to landmark
selection, particularly KP-23 and KP-26.

Compare the baseline six-inlier homography with alternative
transformations that include the rejected landmarks.

**Status:** Completed; findings documented separately below.

### Experiment 04 — Temporal Homography Consistency

Compare frames `0009`, `0010`, and `0011` using previously saved
HockeyRink predictions.

Examine:

- Landmark pixel displacement between frames.
- Changes in landmark confidence.
- Changes in RANSAC inlier membership.
- Variation in estimated homography matrices.
- Stability of projected physical rink geometry.

**Status:** Planned.

### Experiment 05 — Full Pilot-Sequence Evaluation

Extend homography estimation and validation to the complete
60-frame Period 1 pilot.

Measure homography success rates, reprojection residuals,
temporal stability, and failure cases.

**Status:** Planned.

---

# Experiment 03 — Landmark Localization and Homography Sensitivity

**Date:** 2026-10-23  
**Game:** Swiss National League Finals — G01  
**Period:** 1  
**Frame:** `frame_0010.jpg`  
**Status:** PROVISIONAL — Sensitivity demonstrated; physical accuracy unresolved.

## Research Question

How sensitive is the estimated rink-to-image homography to changes
in landmark selection, particularly the inclusion of KP-23 and KP-26?

Can alternative landmark selections improve the geometric alignment
between the projected rink and the painted rink markings?

## Experimental Methodology

Four homography configurations were evaluated using the same
broadcast frame.

| Configuration | Landmark Selection | Estimation Method |
|---|---|---|
| A — Baseline | Six original RANSAC inliers | Original Experiment 01 homography |
| B — Include KP-23 | Baseline + KP-23 | Ordinary homography fitting |
| C — Include KP-26 | Baseline + KP-26 | Ordinary homography fitting |
| D — All eight | All eight candidate landmarks | Ordinary homography fitting |

The original Experiment 01 homography was preserved without
modification.

Alternative homographies were calculated using OpenCV's
`cv2.findHomography()` without RANSAC.

This allowed the previously rejected landmarks to influence
the fitted transformations.

No additional HockeyRink model inference was performed.

## Homography Fitting Results

| Configuration | Landmarks | Mean Error (px) | Median Error (px) | Maximum Error (px) |
|---|---:|---:|---:|---:|
| A — Baseline | 6 | 1.545 | 1.703 | 2.751 |
| B — Include KP-23 | 7 | 3.120 | 3.453 | 4.803 |
| C — Include KP-26 | 7 | 3.914 | 2.562 | 10.217 |
| D — All eight | 8 | 4.585 | 4.424 | 10.727 |

### Observation 03.1 — Fitting Error

The baseline homography produced a mean reprojection error
of 1.545 pixels on its six selected inliers.

Including KP-23 increased the mean fitting error to 3.120 pixels.

Including KP-26 increased the mean fitting error to 3.914 pixels.

Including both landmarks produced a mean fitting error
of 4.585 pixels.

These results demonstrate increased fitting disagreement when
the previously rejected landmarks are included.

However, the fitting sets contain different numbers of landmarks.

Therefore, these measurements cannot independently establish
which homography is physically most accurate.

## Transformation Sensitivity Analysis

To evaluate how landmark selection affects the resulting
transformation, seven fixed physical rink locations were projected
through all four homographies.

The following coordinates were evaluated:

| Reference | X (m) | Y (m) | Description |
|---|---:|---:|---|
| KP-21 | -7.65 | -15.00 | Western blue line, south boards |
| KP-20 | -7.65 | +15.00 | Western blue line, north boards |
| KP-30 | 0.00 | -15.00 | Center red line, south boards |
| KP-26 | 0.00 | 0.00 | Center-ice faceoff spot |
| KP-24 | 0.00 | +15.00 | Center red line, north boards |
| KP-35 | +7.65 | -15.00 | Eastern blue line, south boards |
| KP-34 | +7.65 | +15.00 | Eastern blue line, north boards |

For each alternative homography, the projected pixel coordinates
were compared with those produced by the baseline homography.

Euclidean displacement was calculated using:

\[
d_i =
\sqrt{
(x_{i,\mathrm{alternative}} - x_{i,\mathrm{baseline}})^2
+
(y_{i,\mathrm{alternative}} - y_{i,\mathrm{baseline}})^2
}
\]

These measurements quantify transformation sensitivity,
not independent physical accuracy.

## Transformation Displacement Results

| Configuration | Mean Displacement (px) | Maximum Displacement (px) |
|---|---:|---:|
| A — Baseline | 0.000 | 0.000 |
| B — Include KP-23 | 20.381 | 82.599 |
| C — Include KP-26 | 29.116 | 85.542 |
| D — All eight | 25.479 | 104.243 |

### Observation 03.2 — Maximum Transformation Displacement

All three alternative homographies produced their maximum
measured displacement at:

**Physical rink coordinate: (-7.65, -15.00) meters**

This corresponds to KP-21:

`western_blue_line_south_board_intersection`

The largest displacement was 104.243 pixels, observed when
all eight candidate landmarks were included.

The baseline's maximum displacement is zero by definition,
so its reported maximum location is not meaningful.

### Observation 03.3 — Spatial Distribution of Sensitivity

The greatest measured transformation displacement occurred
at the western blue-line intersection with the south boards.

This location was not included among the eight original
high-confidence candidate landmarks.

The original KP-21 model prediction had a confidence
of approximately 0.245, below the 0.80 threshold.

This may indicate that insufficient reliable landmark coverage
contributes to transformation sensitivity in that region.

However, the experiment does not establish a causal relationship
between KP-21 exclusion and the observed displacement.

### Observation 03.4 — Visual Versus Numerical Assessment

The four projected rink geometries appeared relatively similar
during initial visual inspection.

However, quantitative analysis revealed maximum differences
exceeding 80 pixels for each alternative transformation.

The largest measured displacement exceeded 100 pixels.

This demonstrates that visual inspection of overlapping
homography projections can conceal substantial differences
at particular rink locations.

## Interpretation

Experiment 03 demonstrates that landmark selection materially
influences the estimated rink-to-image transformation.

The greatest sensitivity among the seven tested locations
occurred near the western blue line and south boards.

Potential contributing factors include:

- Uneven spatial distribution of reliable landmarks.
- Landmark localization errors.
- Geometric leverage of particular correspondences.
- Insufficient constraints near the camera-side boards.
- Differences between predicted landmarks and physical rink geometry.

These explanations remain hypotheses.

The results do not establish that the baseline homography
is physically more accurate than the alternatives.

## Relationship to Experiment 02

Experiment 02 identified visible discrepancies between
projected rink geometry and painted rink markings.

These discrepancies appeared more pronounced toward
the near-camera portion of the image.

Experiment 03 provides additional evidence that projected
rink geometry is sensitive to landmark selection in this region.

However, transformation disagreement does not directly measure
the error relative to the actual painted markings.

Independent geometric validation remains necessary.

## Experimental Limitations

1. Only one broadcast frame was evaluated.
2. Only eight candidate landmarks were available.
3. Seven fixed physical reference locations were tested.
4. Displacement was measured in image pixels.
5. No independently annotated ground-truth landmarks were used.
6. Alternative homographies used different fitting sets.
7. Temporal stability was not evaluated.
8. Maximum displacement was measured only among the seven
   selected reference locations.

## Experiment Artifacts

**Python script:**

`scripts/hockeyrink/evaluate_g01_homography_sensitivity.py`

**Results directory:**

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_03/`

**Generated artifacts:**

- `A_baseline.jpg`
- `B_with_KP23.jpg`
- `C_with_KP26.jpg`
- `D_all_eight.jpg`
- `combined_comparison.jpg`
- `sensitivity_results.csv`
- `homography_matrices.json`

The transformation-displacement calculation was performed
using an ad hoc Python command.

The calculation should be incorporated into the permanent
experiment script to ensure reproducibility.

## Experiment 03 Conclusion

The experiment demonstrates substantial sensitivity of the
estimated homography to landmark selection.

Including KP-23 and KP-26 produced measurable changes in
the projected rink geometry.

The largest measured displacement was:

**104.243 pixels at KP-21 (-7.65, -15.00 meters).**

This result highlights the importance of spatial landmark
coverage and independent geometric validation.

The original six-inlier homography remains our experimental
baseline.

It should not yet be considered a fully validated physical
rink calibration.

**Final experimental status: PROVISIONAL**

## Next Research Actions

1. Incorporate transformation-displacement calculations into
   the permanent Experiment 03 Python script.
2. Save individual reference-point displacements to CSV.
3. Evaluate independent projected-versus-painted rink alignment.
4. Investigate spatial landmark coverage and geometric leverage.
5. Proceed to Experiment 04 — Temporal Homography Consistency.