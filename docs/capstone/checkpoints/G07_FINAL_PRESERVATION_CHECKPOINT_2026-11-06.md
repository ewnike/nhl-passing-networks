# G07 — Final Preservation Checkpoint

**Date:** 2026-11-06
**Game:** G07 — Swiss National League Finals
**Status:** Source and reconstructed-period preservation complete; frame-accurate event annotation pending.

## 1. Scope

This checkpoint documents the preservation and verification of Game 7's original FloHockey MPEG-TS source material, reconstructed period videos, source provenance, and visually reviewed period boundaries.

It supplements, without replacing:

`G07_RECONSTRUCTION_S3_VERIFIED_CHECKPOINT_2026-11-06.md`

## 2. Original Source Acquisition

- FloHockey stream: 355879
- Original playlist sequences: 323–2710
- Total original MPEG-TS segments: 2,388
- Original 1080p segments: 2,379
- Lower-resolution recoveries: 9
- Original source bytes: 15,064,035,048
- Acquisition and recovery receipt coverage: 2,388/2,388
- Original TS SHA-256 validation against receipts: PASS

Nine missing 1080p segments were recovered using alternate renditions.

Original source files and acquisition records remain unchanged.

## 3. Original Source S3 Archive

Bucket:

`ewnike-nhl-passing-networks-2026`

Prefix:

`flohockey/swiss_nl_2026_finals/G07/source_archive_v1/`

Manifest:

`metadata/G07_source_archive_manifest_v1.json`

Manifest SHA-256:

`f1c1d9539e60d0c8000f292c2ad4d93248544d4ba82097ec9b7016419a85175a`

Archive inventory:

- Objects: 4,790
- Total bytes: 15,066,064,916
- Remote inventory: PASS — 4,790/4,790
- Independent streamed remote SHA-256 validation: 4,790/4,790
- Total streamed bytes validated against manifest: PASS

The independent audit reached its final validation section after completing all object checks. Its terminal transcript displayed the final heading and object count but omitted the remaining summary print statements. This reporting anomaly is preserved here rather than silently omitted.

Audit script:

`scripts/flohockey/audit_g07_source_archive_s3_v1.py`

## 4. Reconstructed Period Videos

Four normalized MP4s were reconstructed:

| Period | Sequences | Frames | Duration | Resolution | FPS |
|---|---|---:|---:|---|---:|
| P1 | 491–825 | 50,250 | 2,010 s | 1920×1080 | 25 |
| P2 | 1005–1317 | 46,950 | 1,878 s | 1920×1080 | 25 |
| P3 | 1495–1879 | 57,750 | 2,310 s | 1920×1080 | 25 |
| OT1 | 2055–2144 | 13,500 | 540 s | 1920×1080 | 25 |

Totals:

- Reconstructed frames: 168,450
- Reconstructed duration: 6,738 seconds
- Full video/audio decode: PASS — all four periods

The four verified MP4s remain unchanged.

## 5. Reconstructed-Period S3 Archive

Prefix:

`flohockey/swiss_nl_2026_finals/G07/`

Reconstruction manifest:

`metadata/G07_final_reconstruction_manifest_v1.json`

Manifest SHA-256:

`c2b0d0fe3ea53bdaecd5823b52db890ae60212ae3a7a3554546395d5cddaac4c`

Archive validation:

- Objects: 8
- Bytes: 8,789,125,812
- Independent streamed SHA-256: PASS — 8/8
- Remote inventory: PASS

The source archive uses a separate versioned prefix and does not overwrite the reconstructed-period archive.

## 6. Original Playlist Timing Audit

The original 1080p playlist was parsed using explicit segment sequence numbers from the filenames.

Results:

- First sequence: 323
- Last sequence: 2710
- Segments: 2,388
- Playlist duration: 14,316 seconds
- Discontinuities: 331 and 2707
- Playlist timing audit: PASS

Original playlist SHA-256:

`bd0bd66a2656b7c28e1fc056029cd4027d5145fb4f64ad7ce6d1bcb386a8d381`

## 7. Visual Period-Boundary Review

Eight contact sheets were generated from original MPEG-TS segments.

- Contact sheets: 8
- Sampled inspection frames: 264
- Contact-sheet SHA-256 verification: PASS — 8/8
- Original source modifications: NONE

Review script:

`scripts/flohockey/create_g07_period_boundary_sheets_v1.py`

Visual verification record:

`local_artifacts/flohockey/swiss_nl_2026_finals/G07/metadata/G07_visual_boundary_verification_v1.json`

Record SHA-256:

`98f782ec33dcc3c21955b0b5c34ca66afde9c57b158a9402e6886dd791a7d9b7`

### Boundary Observations

| Boundary | Source observation | Game clock / event |
|---|---|---|
| P1 start | Seq 494 +5s | 19:58; gameplay underway |
| P1 end | Seq 825 +5s | 0.0 |
| P2 start | Seq 1005 +2s | 20:00; opening faceoff |
| P2 end | Seq 1317 +5s | 0.0 |
| P3 start | Seq 1498 +3s | 19:59 |
| P3 end | Seq 1877 +1s | 0.0 |
| OT1 start | Seq 2058 +5s | 19:59 |
| OT1 end | Seq 2143 +3s | Game-winning goal celebration; clock stopped at 14:04 |

All eight observed events fall within the existing reconstructed period ranges.

**Conclusion:** The existing reconstructed MP4s contain the observed opening and ending gameplay events. No reconstruction extension is currently indicated.

These are visually validated coverage boundaries, not frame-accurate event annotations.

## 8. Combined G07 S3 Preservation

| Archive | Objects | Bytes |
|---|---:|---:|
| Reconstructed-period archive | 8 | 8,789,125,812 |
| Original-source archive | 4,790 | 15,066,064,916 |
| **Combined** | **4,798** | **23,855,190,728** |

Both archives underwent independent remote SHA-256 verification.

## 9. Remaining Research Work

The following work is deferred to the research workstation:

1. Determine exact opening puck-drop frames at 25 FPS.
2. Determine exact regulation-period ending frames.
3. Determine exact overtime game-winning goal frame.
4. Import reconstructed periods and associated observations into FiftyOne.
5. Develop player tracking, identity verification, rink calibration, and passing-event annotations.

These tasks do not block preservation of the current G07 source material and reconstructed periods.

## 10. Preservation Rules

- Do not overwrite original MPEG-TS segments.
- Do not modify acquisition or recovery receipts.
- Do not overwrite existing reconstructed MP4s.
- Do not mutate existing reconstruction or source archive manifests.
- Use separately versioned artifacts for future corrections.
- Verify any new S3 uploads independently.
- Preserve unrelated Git worktree modifications.

## 11. Final Status

**G07 SOURCE PRESERVATION: COMPLETE**

**G07 RECONSTRUCTED-PERIOD PRESERVATION: COMPLETE**

**G07 VISUAL BOUNDARY COVERAGE REVIEW: COMPLETE**

**FRAME-ACCURATE EVENT ANNOTATION: PENDING**

This checkpoint closes the G07 preservation milestone without claiming that all downstream research annotations are complete.
