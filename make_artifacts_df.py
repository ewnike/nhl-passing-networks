import pandas as pd

YOUR_BUCKET = "ewnike-nhl-passing-networks-2026"

data = {
    "artifact_id": [
        "flo_clip_001_wide_hockeyai",
        "flo_clip_001_wide_botsort",
        "puck_yolo_v2-2",
        "puck_yolo_v5_cpu",
        "flo_game001_seg1651",
        "clip_001_wide",
    ],
    "s3_uri": [
        f"s3://{YOUR_BUCKET}/runs/hockeyai_baseline/flo_clip_001_wide_hockeyai/",
        f"s3://{YOUR_BUCKET}/runs/botsort/flo_clip_001_wide_botsort/",
        f"s3://{YOUR_BUCKET}/runs/puck_legacy/puck_yolo_v2-2/",
        f"s3://{YOUR_BUCKET}/runs/puck_legacy/puck_yolo_v5_cpu/",
        f"s3://{YOUR_BUCKET}/raw/flohockey/game_001/segments/segment-1777384806782_1_1651.ts",
        f"s3://{YOUR_BUCKET}/derived/clips/game_001/clip_001_wide.mp4",
    ],
    "artifact_type": [
        "detection_run",
        "tracking_run",
        "training_run",
        "training_run",
        "raw_video",
        "derived_video",
    ],
    "source": [
        "HockeyAI",
        "HockeyAI+BoT-SORT",
        "Custom YOLO",
        "Custom YOLO",
        "FloHockey",
        "FloHockey",
    ],
    "description": [
        "HockeyAI baseline inference on 6-second wide-view FloHockey clip; saved rendered video and frame-level labels/confidences",
        "HockeyAI detections tracked with BoT-SORT; 180 frame label files plus rendered tracked MP4",
        "Earlier puck-only detector experiment; retained as legacy baseline",
        "Later puck-only detector experiment; retained as legacy baseline",
        "Original 6-second transport-stream source segment preserved before remuxing",
        "6-second continuous wide-view control clip used for HockeyAI and BoT-SORT baseline experiments",
    ],
}

# Create the DataFrame
df = pd.DataFrame(data)

print(df)

df.to_csv("data/manifests/artifacts.csv", index=False)
