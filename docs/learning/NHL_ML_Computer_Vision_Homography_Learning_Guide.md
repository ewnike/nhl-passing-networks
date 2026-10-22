# Learning Guide: Machine Learning, Computer Vision, and Homography in Our NHL Project

**Project:** NHL Puck Tracking & Passing Networks  
**Date:** 2026-10-22  
**Learning focus:** Connecting Python, machine learning, computer vision, RANSAC, and linear algebra to the G01 experiment

In fact, our NHL project brings together three related but distinct areas:

1. **Machine learning** — Predicting rink landmarks from video images.
2. **Computer vision** — Using those landmarks to understand the geometry of the rink.
3. **Linear algebra and statistical estimation** — Calculating the transformation between image coordinates and physical rink coordinates.

The distinction is that **we aren't training a model in our homography experiment. We're using predictions from an already-trained model to estimate a geometric transformation.**

Let's connect this directly to the Python code you've been running.

## 1. First, what are we predicting?

Our pipeline has two stages.

### Stage A — Mehdi's YOLO model predicts rink landmarks

```python
from ultralytics import YOLO

model = YOLO("local_artifacts/models/hockeyrink/HockeyRink.pt")
results = model.predict(source="frame_0010.jpg")
```

The model receives an image and predicts **56 indexed landmark locations**, along with confidence values. In our actual pilot script, the image is loaded from the G01 frames directory.

```python
keypoints.xy    # Predicted image coordinates in pixels
keypoints.conf  # Confidence for each predicted landmark
```

For example, **KP-26**, the center-ice faceoff spot:

```json
{
  "index": 26,
  "x": 1261.7585,
  "y": 487.2368,
  "confidence": 0.9999511
}
```

The prediction means: *the model estimates that KP-26 is at image pixel (1261.76, 487.24).* Its confidence is very high, but confidence alone does **not** establish that the point is accurately localized.

This is **inference**, not training. We are using an existing checkpoint rather than updating neural-network weights.

### Stage B — Homography estimates rink geometry

We already know where each named landmark belongs in physical rink coordinates, based on our documented IIHF 60 m × 30 m rink convention.

```python
H_rink_to_image, mask = cv2.findHomography(
    rink_points,
    image_points,
    method=cv2.RANSAC,
    ransacReprojThreshold=5.0,
)
```

This estimates a **3 × 3 homography matrix** that relates points on the rink plane to their positions in the broadcast image. RANSAC helps avoid letting inconsistent landmark correspondences dominate the estimate.

## 2. What do uppercase X, Y and lowercase x, y mean?

In a typical supervised machine-learning class:

- `X` often means the matrix of input features.
- `y` often means the known target values.
- `ŷ` (y-hat) means predicted targets.

For example, features about houses (`X`) might be used to predict their prices (`ŷ`).

**In this project's geometry notation, the letters have a different meaning:**

| Notation | Meaning | Units |
|---|---|---|
| `(x, y)` | Position in the video frame | Pixels |
| `(X, Y)` | Position on the physical rink | Meters |
| `H` | Homography transformation | Projective mapping |

For KP-26:

- Image prediction: `(x, y) = (1261.76 px, 487.24 px)`
- Known rink location: `(X, Y) = (0.00 m, 0.00 m)`

In homogeneous coordinates, the image-to-rink mapping is written:

\[
\begin{bmatrix} X \\ Y \\ 1 \end{bmatrix}
\sim
H_{\text{image-to-rink}}
\begin{bmatrix} x \\ y \\ 1 \end{bmatrix}
\]

The `~` means **equal up to a nonzero scale factor**. After applying the matrix, divide the first two transformed components by the third to obtain ordinary 2D coordinates.

Our script estimates **rink → image** first because its RANSAC threshold is specified in **image pixels**. It then inverts that matrix to obtain **image → rink**.

## 3. What is `mask`?

A **mask** is a collection of flags used to select observations. In NumPy, Boolean masks are common in data science and machine learning.

`cv2.findHomography` returns both a matrix and a RANSAC inlier mask:

```python
H_rink_to_image, mask = cv2.findHomography(...)
inliers = mask.ravel().astype(bool)
```

For our eight selected landmarks, the result was equivalent to:

```python
# Landmark order: 20, 22, 23, 24, 25, 26, 27, 32
mask = [1, 1, 0, 1, 1, 0, 1, 1]
inliers = [True, True, False, True, True, False, True, True]
```

- `1` / `True`: accepted as an **inlier** under the fitted geometric model.
- `0` / `False`: classified as an **outlier**.

```python
inlier_residuals = residuals[inliers]
```

This is **Boolean indexing**: it keeps only the residual values whose corresponding mask entry is `True`.

## 4. What is RANSAC doing?

**RANSAC** stands for *Random Sample Consensus*. It is a robust model-fitting technique.

Conceptually, it:

1. Samples a small subset of candidate point correspondences.
2. Estimates a possible homography.
3. Measures how well the other correspondences agree with it.
4. Counts correspondences within the specified error threshold.
5. Selects and refines a consensus solution.

Our script uses:

```python
ransacReprojThreshold=5.0  # Pixels, for rink-to-image estimation
```

This threshold is a criterion for geometric agreement, **not** a threshold on YOLO confidence.

### Actual G01 results

| KP | Landmark (short name) | Confidence | Residual (pixels) | RANSAC |
|---:|---|---:|---:|---|
| 20 | West blue line / north boards | 0.9999 | 1.912 | Inlier |
| 22 | West neutral-zone north dot | 0.9998 | 1.870 | Inlier |
| 23 | West neutral-zone south dot | 0.9996 | 23.651 | **Outlier** |
| 24 | Center red line / north boards | 0.9978 | 0.903 | Inlier |
| 25 | Center circle / north intersection | 1.0000 | 2.751 | Inlier |
| 26 | Center-ice faceoff spot | 1.0000 | 15.045 | **Outlier** |
| 27 | Center circle / south intersection | 0.9992 | 1.536 | Inlier |
| 32 | East neutral-zone north dot | 0.8566 | 0.299 | Inlier |

**Key lesson:** KP-23 and KP-26 had very high neural-network confidence but disagreed with the six-point geometric consensus. This does not, by itself, prove which of the model prediction or the fitted geometry is physically correct.

## 5. What error are we measuring?

For a landmark with observed model-predicted pixel location `(xᵢ, yᵢ)` and a location `(x̂ᵢ, ŷᵢ)` projected by the homography, the **reprojection residual** is:

\[
e_i = \sqrt{(x_i-\hat{x}_i)^2+(y_i-\hat{y}_i)^2}
\]

It is the distance between two points in the **image**, measured in **pixels**.

Our first experiment reported:

| Metric | Value |
|---|---:|
| Candidate landmarks | 8 |
| RANSAC inliers | 6 |
| RANSAC outliers | 2 |
| Mean **inlier** reprojection error | **1.545 px** |
| Median inlier error | 1.703 px |
| Maximum inlier error | 2.751 px |

The mean error describes the fit to **accepted model predictions**. It is **not** a measured accuracy in centimeters or meters, and it is not independent ground-truth validation. RANSAC's fitting procedure is also not identical to simply minimizing this reported mean residual.

## 6. Why does the camera matter?

Broadcast cameras can **pan, tilt, and zoom** as play develops. This changes the mapping between image pixels and rink positions.

```text
frame_0009 -> homography H09
frame_0010 -> homography H10
frame_0011 -> homography H11
```

The rink is stationary in physical coordinates, but its appearance moves within the frame. A single-frame homography should not automatically be reused across a moving-camera sequence.

**Important distinction:** Camera motion between frames does not itself explain why two landmarks disagree with the fitted homography **within the same frame**.

## 7. How does this connect to passing networks?

```text
Broadcast video
      |
      v
HockeyRink.pt -> 56 landmark predictions
      |
      v
Confidence filtering + verified landmark identities
      |
      v
RANSAC homography + geometric validation
      |
      v
Image pixels -> rink coordinates (meters)
      |
      +-------------------------------+
      |                               |
      v                               v
Player detection/tracking        Puck detection/tracking
      |                               |
      +---------------+---------------+
                      |
                      v
             Possession inference
                      |
                      v
               Pass detection
                      |
                      v
               Passing network
```

Player and puck detections initially live in **image pixels**. Homography lets us express estimated locations relative to the **rink**, reducing the effect of camera motion. Later steps must still address occlusion, tracking identity, puck visibility, possession, and distinguishing passes from other puck movements.

## 8. The essential distinctions

| Concept | What it means in our project |
|---|---|
| **Model inference** | Mehdi's pretrained YOLO model predicts landmark pixel positions. |
| **Model training** | Updating model weights from labeled examples; **not done** in this experiment. |
| **Homography estimation** | Computing a matrix relating rink-plane positions and image pixels. |
| **RANSAC** | Finding a geometric consensus despite inconsistent correspondences. |
| **Mask** | Selecting inlier or outlier correspondences. |
| **Reprojection residual** | Distance in pixels between observed and homography-projected positions. |
| **Physical validation** | Checking alignment with actual rink markings or independently labeled ground truth; **still pending**. |

## 9. Questions to carry into Experiment 02

1. Does the estimated homography align projected blue lines, the center red line, and the center circle with the painted rink markings?
2. Is KP-23's model prediction displaced from the actual faceoff dot, or is the geometric projection displaced?
3. Which location better matches the true center-ice spot for KP-26?
4. Does the mapping remain stable on nearby frames when the camera moves?
5. How does performance change when fewer landmarks are visible?

**Next experiment:** Project independent rink geometry onto `frame_0010.jpg`, visually assess alignment, and record findings in `docs/hockeyrink/experiments/landmark_consistency_analysis.md`.

## 10. Where the evidence lives

- **Landmark dictionary:** `docs/hockeyrink/hockeyrink_keypoints.md`
- **Research log:** `docs/hockeyrink/experiments/landmark_consistency_analysis.md`
- **Inference script:** `scripts/flohockey/run_rink_keypoint_pilot.py`
- **Homography script:** `scripts/hockeyrink/evaluate_g01_homography.py`
- **Predictions:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/rink_keypoint_pilot/detections.json`
- **Homography results:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/homography.json`
- **Residual table:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/landmark_residuals.csv`
- **Visual overlay:** `local_artifacts/flohockey/swiss_nl_2026_finals/G01/homography_experiment_01/homography_overlay.jpg`

---

**Study takeaway:** We combine *learned landmark predictions* with *known rink geometry*. RANSAC finds a transformation supported by a consistent subset of predictions. The next step is to check whether that transformation is **physically accurate**, not merely mathematically consistent.
