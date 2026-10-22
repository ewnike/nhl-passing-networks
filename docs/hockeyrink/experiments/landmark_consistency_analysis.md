HockeyRink Landmark Consistency Analysis

Project: NHL Puck Tracking & Passing Networks
Research area: Rink landmark detection, geometric consistency, and homography
Status: Active research
Last updated: 2026-10-22

⸻

1. Purpose

This document records experimental findings concerning the geometric consistency and accuracy of rink landmark predictions produced by the HockeyRink pose-estimation model.

The research objectives are to:

1. Evaluate landmark predictions on broadcast hockey footage.
2. Compare predicted landmarks with the project’s canonical 56-keypoint dictionary.
3. Identify geometric inconsistencies and model-localization errors.
4. Evaluate image-to-rink homography estimation.
5. Establish criteria for reliable rink calibration.
6. Document limitations and unresolved questions.

This document supplements docs/hockeyrink/hockeyrink_keypoints.md.

The canonical landmark dictionary and its physical coordinates are maintained separately.

⸻

2. Model and Coordinate Reference

Model

Property	Value
Model	HockeyRink.pt
Origin	Mehdi’s pretrained HockeyRink model (strong provenance evidence)
Architecture	Ultralytics YOLO Pose
Ultralytics version	8.3.214
Output keypoints	56
Keypoint shape	[56, 3]
Detection class	rink
Training image size	640

Model checkpoint:

local_artifacts/models/hockeyrink/HockeyRink.pt

SHA-256:

c604cde0e455916478d33d66f2d54e73c8b27a81ee5ab0aebb0bdaa3988b3e3d

Physical coordinate reference

The project uses the documented IIHF 60 m × 30 m rink geometry.

* Origin: Center ice (0, 0)
* X-axis: West to East
* Y-axis: South to North
* Units: Meters
* Landmark identifiers: KP-0 through KP-55

Reference: docs/hockeyrink/hockeyrink_keypoints.md

The documented semantic mapping is used for these experiments. Independent validation of landmark correspondence remains part of the research.

⸻

Experiment 01 — Single-Frame Homography

Date: 2026-10-22
Game: Swiss National League Finals — G01
Period: 1
Frame: frame_0010.jpg
Status: Initial homography calculated; independent geometric validation pending.

3. Research Question

Can Mehdi’s pretrained HockeyRink model provide sufficiently consistent landmark predictions to estimate a physically meaningful image-to-rink homography on Swiss National League broadcast footage?

4. Input Data

Video

Property	Value
Source	FloHockey
Resolution	1920 × 1080
Frame rate	25 FPS
Sample	First 60 seconds of Period 1
Sampling frequency	1 FPS
Frames extracted	60
Wide-angle frames	58
Close-up frames	2

The initial sample was visually inspected.

The broadcast camera predominantly showed elevated, wide-angle gameplay footage.

Frames frame_0053.jpg and frame_0054.jpg used close-up camera views.

All 60 sampled frames were manually identified as gameplay footage.

5. Methodology

The HockeyRink pose model was applied to the extracted frames.

For frame_0010.jpg, the model produced 56 indexed landmark predictions.

Eight landmarks exceeded the initial confidence threshold of 0.80.

Their predicted pixel coordinates were paired with physical rink coordinates from the project’s canonical landmark dictionary.

A rink-to-image homography was estimated using OpenCV RANSAC.

Parameters:

Parameter	Value
Confidence threshold	0.80
RANSAC reprojection threshold	5 pixels
Candidate landmarks	8
Estimation direction	Rink coordinates → image pixels
Final transformation	Image pixels → rink coordinates

The rink-to-image homography was inverted to obtain the image-to-rink transformation.

6. Numerical Results

Metric	Result
Candidate landmarks	8
RANSAC inliers	6
RANSAC outliers	2
Inlier percentage	75%
Mean inlier reprojection error	1.545 px
Median inlier reprojection error	1.703 px
Maximum inlier reprojection error	2.751 px

Landmark-level results

KP	Landmark	Confidence	Residual (px)	Classification
20	Western blue line / north boards	0.9999	1.912	Inlier
22	West neutral-zone north faceoff dot	0.9998	1.870	Inlier
23	West neutral-zone south faceoff dot	0.9996	23.651	Outlier
24	Center red line / north boards	0.9978	0.903	Inlier
25	Center-circle north intersection	1.0000	2.751	Inlier
26	Center-ice faceoff spot	1.0000	15.045	Outlier
27	Center-circle south intersection	0.9992	1.536	Inlier
32	East neutral-zone north faceoff dot	0.8566	0.299	Inlier

7. Visual Assessment

The homography overlay was inspected against the original broadcast frame.

KP-23 — West neutral-zone south faceoff dot

Observation:

The model prediction appears displaced down and left relative to the painted faceoff dot.

The homography-projected position appears closer to the physical marking.

Interpretation:

This is a candidate model-localization error.

The prediction has high confidence despite a 23.651-pixel disagreement with the fitted homography.

Status: Suspected localization error; manual coordinate validation pending.

KP-26 — Center-ice faceoff spot

Observation:

The model prediction and homography projection differ by approximately 15 pixels.

The center-ice marking is partially obscured by the large PostFinance advertisement.

Interpretation:

The discrepancy could result from landmark localization uncertainty, geometric fitting error, or ambiguity in the visual definition of the center point.

The available evidence does not establish which location is physically correct.

Status: Unresolved.

Accepted landmarks

KP-20, KP-22, KP-24, KP-25, KP-27, and KP-32 appear visually consistent with recognizable rink markings.

Their low reprojection residuals indicate that they form a mutually consistent geometric solution.

However, independent measurement of physical alignment has not yet been completed.

8. Principal Findings

Finding 01 — Model confidence does not guarantee geometric consistency

KP-23 and KP-26 both received confidence scores greater than 0.999.

Nevertheless, their reprojection residuals were 23.651 and 15.045 pixels, respectively.

This demonstrates that high model confidence does not necessarily imply agreement with a homography fitted to other landmarks.

Finding 02 — Six landmarks support a consistent homography

Six of eight candidate landmarks were accepted by RANSAC.

Their mean reprojection residual was 1.545 pixels.

This establishes that a mathematically consistent transformation can be estimated from the selected predictions.

It does not independently establish physical rink-coordinate accuracy.

Finding 03 — Landmark identity and geometry require continued validation

The experiment relies on the documented mapping between HockeyRink keypoint indices and physical IIHF rink coordinates.

Any incorrect landmark identity or coordinate convention could affect the estimated transformation.

Finding 04 — Camera movement requires temporal calibration

Broadcast camera panning, tilting, and zooming can change the image-to-rink transformation between frames.

A single-frame homography cannot automatically be applied throughout a moving-camera sequence.

Temporal consistency must therefore be evaluated.

9. Limitations

This experiment evaluates one frame.

The following have not yet been established:

* Independent landmark localization accuracy.
* Physical rink-coordinate error in meters.
* Homography stability across consecutive frames.
* Accuracy near image boundaries.
* Robustness during camera panning or zooming.
* Reliability during close-up camera views.
* Performance across different rink regions.
* Generalization across games and venues.

The reported reprojection errors are in-sample fitting measurements.

They should not be interpreted as independent estimates of player or puck positioning accuracy.

10. Experiment Artifacts

Experiment script:

scripts/hockeyrink/evaluate_g01_homography.py

Results directory:

local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/

Artifact	Purpose
homography.json	Transformation matrices, configuration, and results
landmark_residuals.csv	Per-landmark measurements
homography_overlay.jpg	Visual comparison of predictions and reprojections

Source inference results:

local_artifacts/flohockey/swiss_nl_2026_finals/G01/rink_keypoint_pilot/detections.json

11. Next Experiments

Experiment 02 — Projected Rink Geometry

Project known rink geometry onto frame_0010.jpg using the estimated homography.

Evaluate alignment with painted rink markings, including features not used as RANSAC inliers.

Experiment 03 — Temporal Consistency

Compare landmark predictions and homographies across frames 0009, 0010, and 0011.

Evaluate camera movement, landmark stability, and changes in geometric consistency.

Experiment 04 — Pilot-Sequence Evaluation

Extend homography estimation and validation to the complete 60-frame Period 1 pilot.

Measure success rates, reprojection residuals, and failure cases.

⸻

12. Research Status

Experiment 01 conclusion:

A candidate image-to-rink homography was successfully estimated using six geometrically consistent HockeyRink landmark predictions.

The experiment provides encouraging initial evidence for transferring Mehdi’s pretrained model to Swiss National League broadcast footage.

Two high-confidence predictions were rejected by RANSAC, demonstrating the importance of geometric validation.

The transformation remains provisional pending independent physical alignment and temporal stability testing.