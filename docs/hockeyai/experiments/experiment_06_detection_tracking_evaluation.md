# Experiment 06 — HockeyAI Detection and BoT-SORT Tracking Evaluation

**Game:** Swiss National League Finals, G01
**Data:** 75 consecutive frames (0000–0074), 25 FPS, approximately 3 seconds
**Status:** Stage 6A and Stage 6B baselines complete; Stage 6C exploratory review documented. Formal identity metrics and independent ground truth remain pending.
**Evidence:** Terminal summaries and manual review provided during the experiment; original outputs remain in local artifacts.

## Research question

Can HockeyAI detect hockey participants and can default BoT-SORT maintain consistent short-duration tracks under camera motion, overlapping skaters, and temporary classification ambiguity? These results are exploratory, not an accuracy benchmark.

## Stage 6A — Detection-only baseline

Model: `local_artifacts/models/hockeyai/HockeyAI_model_weight.pt` (Ultralytics `detect`, seven verified classes: `centriod`, `faceoff`, `goal`, `goalie`, `player`, `puck`, `referee`). Baseline used `imgsz=1280`, confidence threshold `0.15`, CPU. Saved `detections.json`, `detection_summary.csv`, `inference_summary.json`, and annotated frames under `local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_06/stage_6a/`.

| Class | Detections |
|---|---:|
| centriod | 42 |
| faceoff | 133 |
| goal | 3 |
| goalie | 3 |
| player | 744 |
| puck | 49 |
| referee | 161 |
| **Total** | **1,135** |

All 75 frames had player-class detections (range 6–14; mean 9.92). Puck-class detections appeared in 36 distinct frames (49 boxes total), not necessarily true puck positions. In the reviewed game footage, the reviewer observed two referees and two linespersons on ice; the detector has only one `referee` class for officials. Detection counts are not precision, recall, or unique-person counts.

### Targeted referee/player classification case: frames 0050–0053

A visually identified official near the boards was assigned competing class labels. Exact detection outputs, from the saved Stage 6A JSON:

| Frame | Player-class confidence | Referee-class confidence | Relevant IoU |
|---|---|---|---|
| 0050 | 0.644 | 0.304 | player/referee 0.971 |
| 0051 | 0.202 | 0.863 | player/referee 0.963 |
| 0052 | none in selected region | 0.879 | single detection in selected region |
| 0053 | 0.221 | 0.464, 0.438, 0.161 | referee/referee 0.653; player/referee 0.663 (highest reported cross-class pair) |

The frames are 40 ms apart and span 120 ms. The reviewer observed an official turning and using a crossover to follow play; body orientation as the *cause* of the classification changes is a hypothesis, not established. IoU measures spatial overlap, not identity. A separate comparison to Stage 6B tracked observations found **no** player/goalie track box overlapping the reviewed official reference region at IoU >= 0.25 in these four frames. This does not establish why no match was present, or that all such errors are filtered by BoT-SORT.

## Stage 6B — Default BoT-SORT baseline

Ultralytics version `8.3.214`; tracker `botsort.yaml`, `gmc_method=sparseOptFlow`, `with_reid=False`, `track_buffer=30`, tracking classes 3 (`goalie`) and 4 (`player`), `persist=True`, CPU. Stage 6B reran model inference rather than directly ingesting Stage 6A detections. The tracking results were written under `local_artifacts/hockeyai_test/swiss_nl_2026_finals/G01/experiment_06/stage_6b/`.

| Metric | Result |
|---|---:|
| Frames | 75 |
| Tracked observations | 676 |
| Distinct track IDs | 20 |
| Tracks observed in at least 50 frames | 10 |
| Tracks observed in all 75 frames | 2 (IDs 4 and 7) |
| Tracks with gaps within first-to-last span | 6 |
| Tracks with fewer than 10 observations | 9 |

Observation coverage is **not** identity correctness. No duplicate track IDs were found **within any individual frame** in the saved CSV. A visually apparent duplicate `2` was explained by the `6` in label `26` being obscured by another label; do not report a confirmed duplicate active ID.

## Stage 6C — Temporal and visual diagnostics

There were 656 within-track observation transitions (`676 - 20`). Track 26 had 18 observations over frames 46–73, including an eight-missing-frame gap between observations at frames 49 and 58 (164.71 px between bottom-center positions). This is a tracking gap, **not** proof that the physical player disappeared or changed identity. The largest reported one-frame bottom-center displacement was 58.30 px (Track 10, frames 54–55). The median motion vector among concurrently observed tracks reached (-32.40, +7.09) px for the transition ending at frame 69. These are image-space quantities; they combine camera and object motion.

The reviewer initially suspected ID swaps among overlapping skaters and later corrected one visual misreading caused by occluded labels. Apparent merged boxes, missing labels, and identity ambiguity merit further study, but **no formal identity-switch count is established**. A review video and contact-sheet-based inspection were used; no frame-by-frame identity ground truth with independently verified bounding boxes was produced.

### Human review of south-boards interaction (frames 0048–0061)

Source: user-exported `2,7,10.csv`, preserved as the source of the cleaned table `data/validation/g01/experiment_06/track_identity_review_0048_0061.csv`. Column names `Person A/B/C` and the numerical values reproduce the reviewer's annotations; these are **reported track labels**, not verified jersey numbers or independent physical-player identities.

- Frames 48–54: A=2, B=7, C=10.
- Frames 55–56: A=TBD, B=7, C=10. Notes describe a shared box and puck battle involving 2 and 10.
- Frame 57: A=2, B=7, C=10; reviewer notes a box around 2.
- Frames 58–59: A=2, B=7, C=TBD; reviewer notes Track 10 banner disappearance at frame 58.
- Frames 60–61: A=TBD, B=7, C=TBD; reviewer notes blur and partial camera/glass obstruction at frame 60.
- Frame 49 note: 7 and 10 in dark jerseys; 2 in a grey jersey.

The reviewer recorded label 7 consistently in all 14 rows. That is evidence of **annotation continuity**, not proof of independently validated physical identity continuity. `TBD` values are deliberately retained. The cleaned CSV merges observations that Numbers exported into two different note columns, without filling missing data or changing the source wording.

## Interpretation and limitations

1. Short-term object detection and tracking are feasible on this clip, but neither detection confidence nor track coverage establishes physical identity accuracy.
2. Overlapping player/referee detections and short-term class fluctuations are documented quantitatively.
3. The south-board manual review documents uncertain track associations and visual obstruction; it does not justify a numeric ID-switch rate.
4. The original footage is only about three seconds; longer sequences, camera cuts, player re-entry, and line changes require separate evaluation.
5. For passing networks, keep `track_id` separate from persistent, human-validated `player_id`. Do not assign pass events to unverified identities.

## Reproducibility and next research step

Existing scripts: `scripts/hockeyai/run_g01_player_detection_experiment_06.py`, `scripts/hockeyai/run_g01_botsort_experiment_06.py`, and `scripts/hockeyai/analyze_botsort_tracks_v1.py`. Original local outputs include Stage 6A detections and Stage 6B `track_observations.csv`, `track_summary.csv`, `tracks.json`, `tracking_metadata.json`, and annotated frames. Confirm these local script paths before staging because some scripts may be untracked.

Next: inspect the remaining Track 26 ambiguity against the **unannotated original frames** and construct independently verified per-person annotations for selected frames. Then compare baseline BoT-SORT with a controlled alternative configuration. Preserve this baseline unchanged. No further work is required tonight.
