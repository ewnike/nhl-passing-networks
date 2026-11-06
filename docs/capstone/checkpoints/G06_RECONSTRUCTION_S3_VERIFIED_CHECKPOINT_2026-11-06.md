# G06 — Reconstruction and S3 Integrity Checkpoint

**Date:** 2026-11-06
**Game:** Swiss National League Finals, G06
**Status:** Reconstruction archive remotely verified.

## Source Acquisition

- Original source segments: 2,025/2,025 acquired and locally verified.
- Native 1080p segments: 1,944.
- Lower-resolution recovered segments: 81.
- Original MPEG-TS files and acquisition receipts preserved locally.

## Reconstructed Periods

| Period | Sequences | Frames | Duration | SHA-256 |
|---|---|---:|---:|---|
| P1 | 504–866 | 65,340 | 2,178 s | `29cfed9b45177fdc9c4ef1f76514567ebe948e76f84a9ab8d7d8ef3c92682d49` |
| P2 | 1051–1343 | 52,740 | 1,758 s | `1d0360e223a2bff1e64cb931eec9961c856a0442f22270bcd3d84d06e63dbdf9` |
| P3 | 1528–1830 | 54,540 | 1,818 s | `defacc91adf01649d2abc6948ce07f0de45d2fd3e3ef86a3431dba45c3da778b` |
| OT1 | 2012–2072 | 10,980 | 366 s | `36ad3369657e7106b90af067a8720ab0d2ff0f58ec9b2c3093ea367ed9fd6969` |

Total reconstructed video frames: **183,600**.
Total reconstructed video duration: **6,120 seconds**.

All four MP4s passed full FFmpeg video/audio decoding audits.

## AWS S3 Archive

Bucket: `ewnike-nhl-passing-networks-2026`

Prefix: `flohockey/swiss_nl_2026_finals/G06/`

- Objects uploaded: **8**
- Objects independently SHA-256 verified: **8/8**
- Total remote bytes verified: **6,878,145,201**
- Remote object sizes: **PASS**
- Remote SHA-256 integrity: **PASS**

The archive includes four reconstructed MP4s and four metadata files.

The original MPEG-TS segments and acquisition receipts have not been archived as part of this eight-object checkpoint.

## Outstanding Qualifications

- P2 and OT1 endpoint boundaries remain provisional.
- Final visual approval of normalized MP4s remains pending.
- The S3 audit verifies reconstruction artifacts, not the complete original source-segment collection.

## Resume Point

Proceed to G07 acquisition, period-boundary identification, reconstruction, and archival.

Preserve all G06 original source files, receipts, and versioned reconstruction artifacts.
