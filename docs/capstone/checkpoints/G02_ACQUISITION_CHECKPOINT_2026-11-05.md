# G02 — Championship Video Acquisition Checkpoint

Date: 2026-11-05
Status: COMPLETE — S3 integrity verified

## Project
NHL Puck Tracking & Passing Networks

## Acquisition Results

- Competition: Swiss National League Finals 2025–2026
- Game: G02
- Source: FloHockey
- HLS segments: 1,561
- Segment range: 363–1923
- Missing segments: 0
- Duplicate segments: 0
- Empty files: 0
- Manifest size mismatches: 0
- Original broadcast duration: 156 minutes
- Local TS storage: 9.204 GiB

## Period Boundaries

| Period | Start | End | Preferred MP4 |
|---|---:|---:|---|
| P1 | 486 | 983 | G02_P1_trimmed_v1.mp4 |
| P2 | 1046 | 1364 | G02_P2.mp4 |
| P3 | 1551 | 1885 | G02_P3.mp4 |

Boundaries are visually identified, pending frame-level validation.

P1 required an additional trim because the original assembled
MP4 contained approximately ten minutes of post-period footage.

The original P1 MP4 remains preserved locally.

## Validated Media

P1: H.264, AAC, 25 FPS, visually validated.
P2: H.264, AAC, 25 FPS, visually validated.
P3: H.264, AAC, 25 FPS, visually validated.

Preferred period videos total approximately 6.4 GB.
The original untrimmed P1 assembly is approximately 3.06 GB.

## AWS S3

Bucket: ewnike-nhl-passing-networks-2026

Prefix: swiss_nl_2026_finals/G02/

Uploaded objects: 5
Remote objects verified: 5
SHA-256 mismatches: 0
Size mismatches: 0

S3 integrity status: PASS

Manifest:
local_artifacts/flohockey/swiss_nl_2026_finals/G02/metadata/G02_s3_integrity_manifest_v1.json

Manifest SHA-256:
07095b8440ec514540d30582c609ca940d7fac10ceaac1a40d51ec0e1a7e4fef

## Preservation Notes

- Original transport-stream segments remain local.
- Original transport streams were not included in the five-object S3 upload.
- Preferred period MP4s and metadata are archived in S3.
- Existing G01 experiments remain unchanged.
- The generalized period builder supports game-specific temporary filenames.
- HLS playlist contained one discontinuity at approximately 36 seconds.

## Additional Identity Evidence

G02 segment 1892 contains a potential observation of:

HCD #88 Tim Minder

Status: Candidate — pending formal identity verification.

Preserve this postgame evidence for future FiftyOne identity review.

## Next Session

1. Begin G03 acquisition.
2. Reuse the established HLS download workflow.
3. Preserve original video and audio.
4. Identify period boundaries.
5. Assemble and validate period MP4s.
6. Upload validated artifacts to S3.
7. Verify remote SHA-256 checksums.

## Capstone Context

The Hockey Research Workstation will use these videos for:

- YOLO player detection
- BoT-SORT tracking
- Verified player-crop collection
- Triplet-loss Re-ID training
- Jersey-number recognition
- Whisper commentary transcription
- Passing-attempt annotation
- Spatial passing-network construction

Predictive passing-lane optimization remains outside the current capstone scope.

## Final Status

G02 ACQUISITION: COMPLETE
G02 PERIOD VIDEOS: VALIDATED
G02 S3 INTEGRITY: PASS
G03–G07: PENDING
