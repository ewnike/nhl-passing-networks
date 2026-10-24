#!/usr/bin/env python3

"""
Experiment 04 — Stage 4B
Dense 25-FPS Homography Estimation

Estimate independent homographies for 75 consecutive frames.

Uses:
    Saved HockeyRink predictions
    Canonical 56-landmark IIHF coordinates

Does not rerun model inference.
Does not modify earlier experiments.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

BASE = Path(
    "local_artifacts/flohockey/"
    "swiss_nl_2026_finals/G01/"
    "homography_experiment_04/stage_4"
)

DETECTIONS = BASE / "detections.json"

REFERENCE = Path("data/reference/hockeyrink_56_landmarks_iihf.json")

OUTPUT_JSON = BASE / "dense_homographies.json"
OUTPUT_CSV = BASE / "dense_homography_summary.csv"

CONFIDENCE_THRESHOLD = 0.80
RANSAC_THRESHOLD = 5.0


def project(points, H):
    points = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(points, H).reshape(-1, 2)


def main():

    with DETECTIONS.open() as f:
        records = json.load(f)

    with REFERENCE.open() as f:
        reference = json.load(f)

    rink_points = {
        int(kp): (float(value["x_m"]), float(value["y_m"]))
        for kp, value in reference["landmarks"].items()
    }

    results = []
    summaries = []

    for record in records:
        frame = record["frame"]

        result = {
            "frame": frame,
            "status": "failed",
            "candidate_landmarks": 0,
            "ransac_inliers": 0,
            "ransac_outliers": 0,
            "inlier_ids": [],
            "outlier_ids": [],
            "mean_inlier_error_px": None,
            "median_inlier_error_px": None,
            "max_inlier_error_px": None,
            "H_rink_to_image": None,
            "H_image_to_rink": None,
            "failure_reason": None,
        }

        if record["detections"] != 1:
            result["failure_reason"] = "Expected exactly one rink detection"

        else:
            predictions = record["keypoints"][0]["points"]

            selected = [
                p
                for p in predictions
                if (
                    p["index"] in rink_points
                    and p["confidence"] >= CONFIDENCE_THRESHOLD
                )
            ]

            result["candidate_landmarks"] = len(selected)

            if len(selected) < 4:
                result["failure_reason"] = "Fewer than four eligible landmarks"

            else:
                rink = np.asarray(
                    [rink_points[p["index"]] for p in selected],
                    dtype=np.float64,
                )

                image = np.asarray(
                    [[float(p["x"]), float(p["y"])] for p in selected],
                    dtype=np.float64,
                )

                H, mask = cv2.findHomography(
                    rink,
                    image,
                    method=cv2.RANSAC,
                    ransacReprojThreshold=RANSAC_THRESHOLD,
                )

                if H is None or mask is None:
                    result["failure_reason"] = "Homography estimation failed"

                else:
                    inliers = mask.ravel().astype(bool)

                    if int(inliers.sum()) < 4:
                        result["failure_reason"] = "Fewer than four RANSAC inliers"

                    else:
                        try:
                            H_inverse = np.linalg.inv(H)

                            if abs(H_inverse[2, 2]) < 1e-12:
                                raise ValueError("Invalid inverse normalization")

                            H_inverse /= H_inverse[2, 2]

                            projected = project(rink, H)

                            residuals = np.linalg.norm(
                                projected - image,
                                axis=1,
                            )

                            inlier_errors = residuals[inliers]

                            result.update(
                                {
                                    "status": "success",
                                    "ransac_inliers": int(inliers.sum()),
                                    "ransac_outliers": int((~inliers).sum()),
                                    "inlier_ids": [
                                        int(selected[i]["index"])
                                        for i in range(len(selected))
                                        if inliers[i]
                                    ],
                                    "outlier_ids": [
                                        int(selected[i]["index"])
                                        for i in range(len(selected))
                                        if not inliers[i]
                                    ],
                                    "mean_inlier_error_px": float(inlier_errors.mean()),
                                    "median_inlier_error_px": float(
                                        np.median(inlier_errors)
                                    ),
                                    "max_inlier_error_px": float(inlier_errors.max()),
                                    "H_rink_to_image": H.tolist(),
                                    "H_image_to_rink": H_inverse.tolist(),
                                }
                            )

                        except (np.linalg.LinAlgError, ValueError) as e:
                            result["failure_reason"] = str(e)

        results.append(result)

        summaries.append(
            {
                "frame": frame,
                "status": result["status"],
                "candidate_landmarks": result["candidate_landmarks"],
                "ransac_inliers": result["ransac_inliers"],
                "ransac_outliers": result["ransac_outliers"],
                "mean_inlier_error_px": result["mean_inlier_error_px"],
                "median_inlier_error_px": result["median_inlier_error_px"],
                "max_inlier_error_px": result["max_inlier_error_px"],
                "failure_reason": result["failure_reason"],
            }
        )

    OUTPUT_JSON.write_text(json.dumps(results, indent=2) + "\n")

    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(summaries[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summaries)

    successful = [r for r in results if r["status"] == "success"]

    failed = [r for r in results if r["status"] != "success"]

    print("\nEXPERIMENT 04 — DENSE HOMOGRAPHY ESTIMATION")
    print("-" * 65)

    print("Frames processed:", len(results))
    print("Successful homographies:", len(successful))
    print("Failed homographies:", len(failed))

    if successful:
        errors = [r["mean_inlier_error_px"] for r in successful]

        inliers = [r["ransac_inliers"] for r in successful]

        print("Mean inlier reprojection error:", f"{np.mean(errors):.3f} px")

        print("Median frame mean error:", f"{np.median(errors):.3f} px")

        print(
            "Inliers per successful frame:", f"min={min(inliers)}, max={max(inliers)}"
        )

    if failed:
        print("\nFailed frames:")
        for r in failed:
            print(r["frame"], r["failure_reason"])

    print("\nSaved:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)


if __name__ == "__main__":
    main()
