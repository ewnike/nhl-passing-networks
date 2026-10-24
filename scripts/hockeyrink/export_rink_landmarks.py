#!/usr/bin/env python3

"""
Export the canonical 56 HockeyRink landmarks from Markdown to JSON.

Source:
    docs/hockeyrink/hockeyrink_keypoints.md

Output:
    data/reference/hockeyrink_56_landmarks_iihf.json

The Markdown reference remains authoritative.
"""

import json
import re
from pathlib import Path

SOURCE = Path("docs/hockeyrink/hockeyrink_keypoints.md")

OUTPUT = Path("data/reference/hockeyrink_56_landmarks_iihf.json")


def main():

    text = SOURCE.read_text(encoding="utf-8")

    landmarks = {}

    for line in text.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue

        columns = [column.strip() for column in line.strip().strip("|").split("|")]

        if len(columns) != 6:
            continue

        kp = int(columns[0])
        name = columns[1]

        x = float(columns[2])
        y = float(columns[3])

        if kp in landmarks:
            raise ValueError(f"Duplicate landmark: KP-{kp}")

        landmarks[kp] = {
            "name": name,
            "x_m": x,
            "y_m": y,
            "description": columns[4],
            "source": columns[5],
        }

    expected = set(range(56))
    actual = set(landmarks)

    if actual != expected:
        raise RuntimeError(
            f"Landmark IDs do not match KP-0 through KP-55. "
            f"Missing: {sorted(expected - actual)}; "
            f"Unexpected: {sorted(actual - expected)}"
        )

    output = {
        "reference": str(SOURCE),
        "coordinate_system": {
            "rink_length_m": 60.0,
            "rink_width_m": 30.0,
            "origin": "center_ice",
            "x_positive": "east",
            "y_positive": "north",
            "units": "meters",
        },
        "landmarks": {str(kp): landmarks[kp] for kp in sorted(landmarks)},
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nHOCKEYRINK LANDMARK EXPORT")
    print("-" * 55)
    print("Source:", SOURCE)
    print("Output:", OUTPUT)
    print("Landmarks:", len(landmarks))
    print("Status: PASS")


if __name__ == "__main__":
    main()
