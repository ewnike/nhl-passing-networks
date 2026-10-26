---

# Experiment 05 — Stage 5C: Homography Failure Analysis and Visual Geometric Validation

**Date:** 2026-10-26
**Game:** Swiss National League Finals — G01
**Period:** 1
**Dataset:** 60 broadcast frames sampled at 1 FPS
**Model:** HockeyRink.pt
**Confidence threshold:** 0.80
**RANSAC reprojection threshold:** 5.0 pixels
**Status:** Stage 5C completed — qualitative visual evaluation; independent geometric validation pending.

## 1. Research Objective

Evaluate the reliability of homographies estimated during Experiment 05 Stage 5B by examining unsuccessful frames, minimal RANSAC solutions, unusually high fitting residuals, and substantial disagreement among high-confidence landmark predictions.

The investigation distinguishes mathematical homography estimation from physically accurate rink calibration.

Unlike Experiment 04's dense 25-FPS sequence, Experiment 05 evaluates calibration coverage across a longer broadcast interval using 1-FPS sampling.

The sampled frames are not consecutive source-video frames and must not be interpreted as such when assessing temporal stability.

## 2. Stage 5B Baseline Results

| Measurement | Result |
|---|---:|
| Frames processed | 60 |
| Frames containing exactly one rink detection | 57 |
| Frames with at least four eligible landmarks | 52 |
| Successful homography estimates | 52 |
| Failed homography estimates | 8 |
| Overall estimation coverage | 86.7% |
| Success among eligible frames | 100% |
| Minimal four-inlier homographies | 3 |
| Mean inlier reprojection error | 1.535 px |
| Median frame mean reprojection error | 1.699 px |
| RANSAC inliers per successful frame | 4–11 |

All 52 frames containing at least four eligible landmarks produced homography estimates.

However, successful estimation does not establish geometric accuracy.

The 86.7% coverage figure represents mathematical estimation success under the selected thresholds, not independently validated calibration coverage.

## 3. Unsuccessful Homography Estimates

Eight frames did not produce homographies.

| Frame | Recorded failure reason | Visual classification |
|---|---|---|
| `frame_0000.jpg` | No exactly-one rink detection | Elevated, very wide arena view |
| `frame_0001.jpg` | No exactly-one rink detection | Elevated, very wide arena view |
| `frame_0002.jpg` | Fewer than four eligible landmarks | Spectator close-up |
| `frame_0003.jpg` | No exactly-one rink detection | Spectator close-up |
| `frame_0004.jpg` | Fewer than four eligible landmarks | Tight center-ice faceoff view |
| `frame_0005.jpg` | Fewer than four eligible landmarks | Tight center-ice faceoff view |
| `frame_0053.jpg` | Fewer than four eligible landmarks | Close-up of players battling along boards |
| `frame_0054.jpg` | Fewer than four eligible landmarks | Close-up of players battling along boards |

### 3.1 Elevated Arena Views

Frames 0000 and 0001 show extensive visible rink geometry from elevated arena perspectives.

Despite this visibility, the pretrained model did not produce exactly one rink detection.

These observations suggest a possible limitation in model robustness across camera viewpoints.

The precise cause remains undetermined.

### 3.2 Spectator Close-Ups

Frames 0002 and 0003 show spectators rather than gameplay.

These frames contain insufficient useful rink geometry for reliable calibration.

Their failure illustrates the need to distinguish non-gameplay camera views from gameplay views suitable for rink calibration.

### 3.3 Tight Center-Ice Views

Frames 0004 and 0005 show a center-ice faceoff.

Although rink markings are visible, fewer than four landmarks satisfied the confidence threshold.

The failures may reflect limited landmark coverage, model confidence, or both.

### 3.4 Player Close-Ups

Frames 0053 and 0054 show two players battling along the boards.

The tight camera framing limits visible rink geometry.

These frames may remain useful for player-detection or identification research even when homography estimation is unavailable.

## 4. Minimal Four-Inlier Homographies

Three frames produced homographies using exactly four RANSAC inliers.

| Frame | Candidate landmarks | RANSAC inliers | Mean inlier error |
|---|---:|---:|---:|
| `frame_0018.jpg` | 4 | 4 | 0.000 px |
| `frame_0019.jpg` | 5 | 4 | 0.000 px |
| `frame_0020.jpg` | 6 | 4 | 0.000 px |

Four nondegenerate point correspondences can determine a projective homography exactly.

Consequently, near-zero residuals are mathematically expected for minimal solutions and do not independently establish physical calibration accuracy.

These three frames should be flagged for additional review because the estimated transformations have limited correspondence redundancy.

### Visual Observation — Frame 0018

The projected blue line approximately follows the visible painted blue line near the northern boards.

However, divergence becomes apparent toward the lower portion of the image.

The projected center-circle geometry also shows approximate agreement with visible markings.

**Assessment:** Provisionally plausible geometric alignment, but not independently validated.

## 5. Frames With Elevated Fitting Residuals

The ten highest mean inlier reprojection errors were:

| Frame | Mean error (px) | RANSAC inliers | Candidates |
|---|---:|---:|---:|
| 0039 | 2.344 | 11 | 19 |
| 0050 | 2.322 | 9 | 14 |
| 0031 | 2.300 | 10 | 19 |
| 0037 | 2.297 | 10 | 19 |
| 0016 | 2.193 | 8 | 12 |
| 0013 | 2.012 | 9 | 19 |
| 0052 | 1.999 | 10 | 19 |
| 0036 | 1.941 | 10 | 19 |
| 0028 | 1.920 | 7 | 15 |
| 0059 | 1.913 | 10 | 18 |

Frame 0039 was selected for additional visual evaluation because it had the highest mean inlier fitting residual.

## 6. Frame 0039 — Offensive-Zone Geometric Evaluation

**Frame:** `frame_0039.jpg`
**Candidates:** 19
**RANSAC inliers:** 11
**Mean inlier error:** 2.344 pixels

### Initial Visualization

The first overlay projected the center red line, blue lines, and center faceoff circle.

Most projected geometry appeared outside the visible image.

This initially raised concerns about the estimated homography.

However, frame 0039 primarily shows offensive-zone gameplay.

The initial overlay therefore did not include enough relevant rink geometry to evaluate the visible playing area.

### Improved Offensive-Zone Overlay

A second visualization projected the eastern offensive-zone geometry using the saved homography.

The projected markings included:

- Eastern goal line at \(x=+26.00\) meters.
- Eastern offensive-zone faceoff circles centered at \((20.00,+7.00)\) and \((20.00,-7.00)\) meters.
- Faceoff-circle radius of 4.50 meters.
- Corresponding faceoff dots.
- Eastern blue line at \(x=+7.65\) meters.

The script initially projected both eastern and western offensive-zone geometry.

Western-zone projections appeared largely outside the visible playing area and were subsequently removed from the visualization.

### Visual Findings

**Upper faceoff circle:** The projected circle approximately follows the painted faceoff-circle geometry, with visible alignment differences.

**Lower faceoff circle:** The projected circle approximately follows the corresponding painted marking, although displacement is visible along portions of its circumference.

**Goal line:** The projected line passes near the net but does not consistently coincide with the visible painted goal line.

These observations indicate partial geometric agreement.

### Interpretation

The improved visualization demonstrates that the original neutral-zone-only overlay was insufficient for evaluating frame 0039.

The offensive-zone projection provides more relevant geometric evidence.

However, visible discrepancies remain, particularly along the projected goal line.

**Frame 0039 classification: Partially aligned homography; independent geometric validation required.**

The 2.344-pixel mean inlier residual cannot be interpreted as the homography's physical calibration error.

## 7. Frame 0041 — High RANSAC Outlier Count

**Frame:** `frame_0041.jpg`

| Measurement | Value |
|---|---:|
| High-confidence landmark candidates | 23 |
| RANSAC inliers | 7 |
| RANSAC outliers | 16 |
| Inlier acceptance rate | 30.4% |

Frame 0041 contained the largest number of high-confidence landmark candidates in the 60-frame pilot.

Nevertheless, RANSAC rejected 16 of the 23 candidates.

The projected blue line showed approximate alignment near the northern boards but diverged from the painted marking toward the southern portion of the image.

The projected center-circle geometry also showed visible displacement.

### Interpretation

High model confidence does not necessarily imply agreement with a single projective transformation.

Possible explanations include inaccurate landmark localization, incorrect physical correspondences, limited geometric conditioning, or competing landmark configurations.

The current evidence does not establish which explanation dominates.

**Frame 0041 classification: Substantial landmark disagreement; geometric review required.**

## 8. Principal Findings

Stage 5C established the following:

1. The 60-frame pilot produced 52 successful homography estimates, corresponding to 86.7% estimation coverage.
2. The eight unsuccessful frames occurred across several identifiable broadcast-view categories.
3. Elevated arena views can fail detection despite substantial visible rink geometry.
4. Spectator and player close-ups may lack sufficient geometry for calibration.
5. Three minimal four-inlier solutions produced near-zero residuals without independently established geometric accuracy.
6. Frame 0041 demonstrated substantial disagreement among high-confidence landmark candidates.
7. Frame 0039 demonstrated that visualization must include rink geometry relevant to the camera's current field of view.
8. Qualitative overlays revealed alignment discrepancies that cannot be characterized using RANSAC fitting residuals alone.

## 9. Methodological Limitations

This investigation was qualitative and exploratory.

The following limitations remain:

- No independent painted-line residual measurements were collected for the Experiment 05 frames.
- Successful homography estimation does not guarantee physically accurate rink coordinates.
- RANSAC inlier residuals measure agreement with selected model predictions, not independent ground truth.
- The 1-FPS pilot is unsuitable for assessing consecutive-source-frame temporal stability.
- Camera-view categories were assigned through visual inspection rather than an independently validated classifier.
- The 60-frame pilot represents a limited sample from one game.
- No quantitative acceptance threshold has yet been established for downstream player-coordinate projection.

## 10. Reproducibility

### Input Data

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/rink_keypoint_pilot/detections.json`

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/frames/P1_pilot/`

### Canonical Coordinate Reference

`data/reference/hockeyrink_56_landmarks_iihf.json`

### Analysis Scripts

`scripts/hockeyrink/evaluate_pilot_homographies.py`

`scripts/hockeyrink/visualize_g01_pilot_homographies.py`

`scripts/hockeyrink/visualize_g01_offensive_zone_homography.py`

### Generated Results

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_05/pilot_homographies.json`

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_05/pilot_homography_summary.csv`

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_05/pilot_review_contact_sheet.jpg`

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_05/visual_validation/pilot_homography_review.jpg`

`local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_05/visual_validation/frame_0039_offensive_zone_overlay.jpg`

## 11. Stage 5C Conclusion

Experiment 05 Stage 5C identified meaningful differences between homography estimation success and apparent geometric accuracy.

The analysis demonstrated that calibration failures can arise from different broadcast-view conditions, while successful homographies may still exhibit spatial misalignment.

These results support developing a calibration-quality assessment process that incorporates camera-view suitability, landmark coverage, RANSAC consistency, and independent geometric validation.

**Stage 5C status: COMPLETE — Qualitative visual evaluation.**

**Independent physical calibration accuracy: NOT YET ESTABLISHED.**

**Experiment 05 final synthesis and documentation: PENDING.**

---

# Experiment 05 — Stage 5D: Final Synthesis and Research Conclusions

**Date completed:** 2026-10-26
**Game:** Swiss National League Finals — G01
**Dataset:** 60 frames sampled at 1 FPS
**Status:** COMPLETE — Exploratory pilot-sequence calibration evaluation

## 12. Experiment Objectives and Outcomes

Experiment 05 evaluated the coverage and reliability of HockeyRink homography estimation across a 60-frame broadcast pilot.

The experiment extended the investigation beyond Experiment 04's 75 consecutive frames sampled at 25 FPS.

The principal objective was to evaluate calibration availability across different broadcast views, rather than continuous frame-to-frame geometric stability.

The experiment addressed four questions:

1. How frequently does HockeyRink produce sufficient landmark predictions for homography estimation?
2. How frequently can RANSAC estimate a homography from those predictions?
3. Which broadcast-view conditions prevent successful estimation?
4. Do successful homographies necessarily produce plausible projected rink geometry?

## 13. Consolidated Experimental Results

| Measurement | Result |
|---|---:|
| Total frames | 60 |
| Frames with exactly one rink detection | 57 |
| Frames with at least four eligible landmarks | 52 |
| Successful homographies | 52 |
| Failed homographies | 8 |
| Homography estimation coverage | 86.7% |
| Success among eligible frames | 100% |
| Minimal four-inlier solutions | 3 |
| Mean inlier reprojection error | 1.535 px |
| Median frame mean reprojection error | 1.699 px |
| Minimum RANSAC inliers | 4 |
| Maximum RANSAC inliers | 11 |

The estimator produced a homography for every frame containing at least four eligible landmarks.

However, estimation success does not establish physical calibration accuracy.

## 14. Calibration Availability Versus Calibration Accuracy

Experiment 05 identified three distinct levels of calibration assessment.

### 14.1 Landmark Availability

The model must identify enough usable rink landmarks to support homography estimation.

Eight frames did not satisfy the requirements for successful estimation.

### 14.2 Mathematical Estimation

Given sufficient correspondences, RANSAC can estimate a projective transformation.

Fifty-two frames produced homographies under the selected confidence and reprojection thresholds.

### 14.3 Physical Geometric Accuracy

A mathematically successful homography must still agree with independently observed rink geometry.

Visual overlays revealed that some estimated transformations exhibited partial alignment and spatial discrepancies.

Independent quantitative geometric validation was not performed across the full pilot.

Therefore, the proportion of frames meeting a physically meaningful calibration-accuracy threshold remains unknown.

## 15. Principal Scientific Findings

**Finding 1 — Calibration availability depends on broadcast view.**

The unsuccessful frames included elevated arena views, spectator close-ups, tightly framed faceoffs, and player close-ups.

These represent different causes of insufficient calibration information.

**Finding 2 — Landmark confidence and geometric consistency are distinct.**

Frame 0041 contained 23 high-confidence candidates, but only seven were accepted as RANSAC inliers.

This demonstrates that high model confidence does not guarantee consistency with the estimated transformation.

**Finding 3 — Minimal solutions require additional validation.**

Frames 0018–0020 produced homographies supported by exactly four RANSAC inliers.

Their near-zero fitting residuals do not establish independent geometric accuracy.

**Finding 4 — Visualization must match the visible rink region.**

Frame 0039 initially appeared difficult to evaluate using neutral-zone geometry.

Projecting the eastern offensive-zone faceoff circles and goal line revealed partial alignment with the painted markings.

This demonstrates the importance of evaluating the portion of rink geometry actually visible in the broadcast frame.

**Finding 5 — Reprojection residuals are insufficient as standalone calibration-quality metrics.**

Low residuals measure agreement with selected predicted landmarks.

They do not independently establish agreement with physical rink markings.

## 16. Relationship to Experiment 04

Experiments 04 and 05 investigated complementary calibration questions.

| Characteristic | Experiment 04 | Experiment 05 |
|---|---|---|
| Dataset | 75 consecutive frames | 60 sampled frames |
| Sampling rate | 25 FPS | 1 FPS |
| Primary objective | Temporal geometric consistency | Calibration coverage |
| Homography estimates | 75/75 | 52/60 |
| Main diagnostic | RANSAC membership continuity | View-dependent estimation availability |
| Independent dense-sequence accuracy | Not established | Not applicable |
| Independent pilot-wide accuracy | Not applicable | Not established |

Experiment 04 identified associations between RANSAC inlier-set continuity and projected geometric variation.

Experiment 05 identified limitations in homography estimation across different broadcast views.

Together, the experiments provide a foundation for developing calibration-quality monitoring and selective use of rink-coordinate transformations.

## 17. Implications for Player and Puck Tracking

The next phase of the project will investigate player detection, bounding boxes, and multi-object tracking.

Calibration and detection should remain separate components of the processing pipeline.

A player may be detectable even when the frame lacks sufficient rink geometry for homography estimation.

Likewise, a mathematically successful homography should not automatically be accepted for converting player positions into physical rink coordinates.

Future tracking records should preserve:

- Frame identifier and source timestamp.
- Detection bounding box and confidence.
- Persistent tracking identifier, where available.
- Homography availability and calibration-quality status.
- Image-space player position.
- Physical rink coordinates only when calibration is considered sufficiently reliable.

Player tracking should initially be evaluated in image space, independently of rink-coordinate calibration.

The skate-contact location, rather than the bounding-box center, should be used as the initial approximation of a player's position on the ice plane.

## 18. Remaining Research Requirements

The following investigations remain open:

1. Independent painted-line validation across representative broadcast frames.
2. Quantitative geometric acceptance criteria for homographies.
3. Calibration robustness under camera transitions and close-ups.
4. Geometric conditioning of landmark configurations.
5. Reliable player and puck localization.
6. Multi-object tracking and persistent player identity.
7. Integration of tracking coordinates with passing-event annotations.
8. Validation of downstream spatial measurements.

These requirements do not prevent beginning player-detection experiments.

They should remain explicit limitations when using estimated rink coordinates.

## 19. Final Research Conclusion

Experiment 05 demonstrated that HockeyRink and RANSAC can estimate homographies for a substantial proportion of frames in the original G01 broadcast pilot.

The observed 86.7% estimation coverage is encouraging but does not establish equivalent calibration accuracy.

The investigation identified view-dependent failures, minimal correspondence configurations, substantial landmark disagreement, and partial geometric misalignment in selected successful homographies.

Together with Experiment 04, these results support a modular computer-vision pipeline that separates object detection, tracking, rink calibration, and event interpretation.

**Experiment 05: COMPLETE — Exploratory calibration coverage evaluation.**

**Stages 5A–5D: COMPLETE.**

**Independent physical calibration accuracy: NOT YET ESTABLISHED.**

**Next research phase: Player Detection and Multi-Object Tracking.**