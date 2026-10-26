#!/usr/bin/env python3

"""
Experiment 05 — Stage 5B
Full Pilot-Sequence Homography Evaluation

Estimate independent homographies from saved HockeyRink predictions.

Supports configurable input/output paths and thresholds.

Does not rerun inference.
Does not modify Experiment 04 artifacts.
"""

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

DEFAULT_BASE = Path("local_artifacts/flohockey/swiss_nl_2026_finals/G01")

DEFAULT_DETECTIONS = DEFAULT_BASE / "rink_keypoint_pilot/detections.json"

DEFAULT_REFERENCE = Path("data/reference/hockeyrink_56_landmarks_iihf.json")

DEFAULT_OUTPUT = DEFAULT_BASE / "homography_experiment_05"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--detections",
        type=Path,
        default=DEFAULT_DETECTIONS,
    )

    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.80,
    )

    parser.add_argument(
        "--ransac-threshold",
        type=float,
        default=5.0,
    )

    return parser.parse_args()


def project(points, H):
    array = np.asarray(
        points,
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    return cv2.perspectiveTransform(
        array,
        H,
    ).reshape(-1, 2)


def main():
    args = parse_args()

    if not 0 <= args.confidence <= 1:
        raise ValueError("Confidence threshold must be between 0 and 1")

    if args.ransac_threshold <= 0:
        raise ValueError("RANSAC threshold must be positive")

    records = json.loads(args.detections.read_text())

    reference = json.loads(args.reference.read_text())

    rink_points = {
        int(kp): (
            float(value["x_m"]),
            float(value["y_m"]),
        )
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
            "minimal_fit": False,
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
                if (p["index"] in rink_points and p["confidence"] >= args.confidence)
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
                    ransacReprojThreshold=args.ransac_threshold,
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

                            if (
                                not np.isfinite(H_inverse).all()
                                or abs(H_inverse[2, 2]) < 1e-12
                            ):
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
                                    "minimal_fit": bool(int(inliers.sum()) == 4),
                                    "mean_inlier_error_px": float(inlier_errors.mean()),
                                    "median_inlier_error_px": float(
                                        np.median(inlier_errors)
                                    ),
                                    "max_inlier_error_px": float(inlier_errors.max()),
                                    "H_rink_to_image": H.tolist(),
                                    "H_image_to_rink": H_inverse.tolist(),
                                }
                            )

                        except (np.linalg.LinAlgError, ValueError) as exc:
                            result["failure_reason"] = str(exc)

        results.append(result)

        summaries.append(
            {
                "frame": frame,
                "status": result["status"],
                "candidate_landmarks": result["candidate_landmarks"],
                "ransac_inliers": result["ransac_inliers"],
                "ransac_outliers": result["ransac_outliers"],
                "minimal_fit": result["minimal_fit"],
                "mean_inlier_error_px": result["mean_inlier_error_px"],
                "median_inlier_error_px": result["median_inlier_error_px"],
                "max_inlier_error_px": result["max_inlier_error_px"],
                "failure_reason": result["failure_reason"],
            }
        )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_json = args.output_dir / "pilot_homographies.json"
    output_csv = args.output_dir / "pilot_homography_summary.csv"

    output_json.write_text(json.dumps(results, indent=2) + "\n")

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(summaries[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summaries)

    successful = [r for r in results if r["status"] == "success"]

    failed = [r for r in results if r["status"] != "success"]

    minimal = [r for r in successful if r["minimal_fit"]]

    print("\nEXPERIMENT 05 — STAGE 5B")
    print("FULL PILOT HOMOGRAPHY ESTIMATION")
    print("-" * 65)

    print("Frames processed:", len(results))
    print("Successful homographies:", len(successful))
    print("Failed homographies:", len(failed))
    print("Minimal four-inlier fits:", len(minimal))

    if successful:
        errors = [r["mean_inlier_error_px"] for r in successful]

        inlier_counts = [r["ransac_inliers"] for r in successful]

        print("Mean inlier reprojection error:", f"{np.mean(errors):.3f} px")

        print("Median frame mean error:", f"{np.median(errors):.3f} px")

        print(
            "Inliers per successful frame:",
            f"min={min(inlier_counts)}, max={max(inlier_counts)}",
        )

    if failed:
        print("\nFailed frames:")
        for r in failed:
            print(r["frame"], r["failure_reason"])

    print("\nSaved:")
    print(output_json)
    print(output_csv)


if __name__ == "__main__":
    main()
