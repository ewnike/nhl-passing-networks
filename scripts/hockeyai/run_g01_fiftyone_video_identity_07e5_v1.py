#!/usr/bin/env python3
"""Protected runner for G01 FiftyOne video identity integration."""

import subprocess
import sys
from pathlib import Path

import fiftyone as fo

TARGET = "swiss_nl_g01_video_identity_integrated_07e5_v1"

SCRIPT = Path(
    "scripts/hockeyai/create_g01_fiftyone_video_identity_07e5_v1.py"
)


def main():
    print("PHASE 02 — PROTECTED FIFTYONE INTEGRATION")
    print("=" * 72)

    if fo.dataset_exists(TARGET):
        raise SystemExit(
            f"STOP — Target dataset already exists: {TARGET}"
        )

    if not SCRIPT.is_file():
        raise SystemExit("STOP — Integration script missing")

    result = subprocess.run(
        [sys.executable, "-u", str(SCRIPT)],
        check=False,
    )

    if result.returncode != 0:
        print()
        print("INTEGRATION FAILED — INSPECTING PARTIAL DATASET")

        if fo.dataset_exists(TARGET):
            dataset = fo.load_dataset(TARGET)

            print("Dataset:", TARGET)
            print("Samples:", len(dataset))

            if len(dataset) == 1:
                sample = dataset.first()
                print("Stored frame documents:", len(sample.frames))

            print()
            print("Partial dataset retained for investigation.")
            print("Automatic deletion was not performed.")

        raise SystemExit(result.returncode)

    dataset = fo.load_dataset(TARGET)

    print()
    print("Protected runner: PASS")
    print("Dataset:", dataset.name)
    print("Samples:", len(dataset))


if __name__ == "__main__":
    main()
