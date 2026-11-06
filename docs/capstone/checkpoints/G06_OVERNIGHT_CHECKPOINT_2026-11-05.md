# G06 — Overnight Checkpoint

**Date:** 2026-11-05
**Game:** Swiss National League Finals, G06
**Status:** Acquisition complete; reconstruction in progress.

## Source Acquisition

- FloHockey stream ID: `355878`
- Source segments: **2,025/2,025**
- Sequence range: **267–2291**
- Playlist duration: **12,144 seconds**
- Native 1080p segments: **1,944**
- Recovered lower-resolution segments: **81**
- Missing sequences: **0**
- SHA-256 integrity errors: **0**
- Original source files: **unchanged**

## Recovery Resolution Distribution

| Resolution | Segments |
|---|---:|
| 720p | 7 |
| 540p | 16 |
| 480p | 33 |
| 360p | 21 |
| 270p | 4 |

All 81 recovered segments passed frame-count, resolution, codec, and decoding checks.

## Registered Period Boundaries

| Period | Start | End | Segments |
|---|---:|---:|---:|
| P1 | 504 | 866 | 363 |
| P2 | 1051 | 1343 | 293 |
| P3 | 1528 | 1830 | 303 |
| OT1 | 2012 | 2072 | 61 |

P1 and P3 boundaries visually verified. P2 and OT1 endpoints remain provisional in the registered manifest.

Period-boundary manifest SHA-256:

`2fc5177da3bfaddabbe38f8c717e8e59d1a7ac960bd2fdf571448347f9d78af0`

## OT1 Review Reconstruction

File:

`local_artifacts/flohockey/swiss_nl_2026_finals/G06/reconstructed_periods/G06_OT1_review_v1.mp4`

- Source sequences: **2012–2072**
- Source segments: **61**
- Output resolution: **1920 × 1080**
- Frame rate: **30 FPS**
- Duration: **366.004 seconds**
- Output bytes: **425,507,159**
- Expected frames: **10,980**
- Actual decoded frames: **10,971**
- Difference: **9 frames**
- Visual playback: **PASS — user verified**
- Archival status: **Review artifact only**

SHA-256:

`43403302c826c0ff1b19176a00c8294254bfa0ad6b55f018cc782e098d52f697`

## Outstanding Work

1. Investigate the nine-frame OT1 discrepancy.
2. Confirm provisional P2 and OT1 endpoints.
3. Determine a validated mixed-resolution reconstruction method.
4. Reconstruct P1, P2, and P3.
5. Perform full video/audio integrity validation.
6. Archive final G06 reconstruction artifacts to AWS S3.
7. Independently verify remote SHA-256 checksums.
8. Commit the final G06 reconstruction checkpoint.

## Preservation Rules

- Never overwrite original MPEG-TS files.
- Preserve original acquisition and recovery receipts.
- Preserve the OT1 review MP4.
- Version all corrected reconstruction outputs.
- Never stage unrelated Git changes.
- Do not claim S3 archival until remote verification passes.

## Resume Point

**Resume by investigating the nine-frame discrepancy in `G06_OT1_review_v1.mp4`.**

The original source acquisition is complete. Do not repeat the 2,025-segment download.
