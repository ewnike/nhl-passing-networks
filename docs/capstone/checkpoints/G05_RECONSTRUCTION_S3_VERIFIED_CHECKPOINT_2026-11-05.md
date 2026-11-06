# G05 — Reconstruction and AWS S3 Integrity Checkpoint

**Date:** 2026-11-05
**Game:** G05 — Swiss National League Finals 2025–26
**Status:** VERIFIED — LOCAL RECONSTRUCTION AND S3 ARCHIVE

## Executive Summary

G05 acquisition, four-period reconstruction, technical validation, visual inspection, and remote AWS S3 reconstruction archival have been completed.

The original 2,022 native-1080p MPEG-TS source segments remain preserved locally.

## Acquisition

- Original MPEG-TS segments: **2,022/2,022**
- Source resolution: **1920 × 1080**
- Observed source frame rate: **30 FPS**
- Source SHA-256 verification: **PASS**
- Original source files: **UNCHANGED**

## Period Boundaries

| Period | Start | End | Segments | Playlist duration |
|---|---:|---:|---:|---:|
| P1 | 466 | 859 | 394 | 2364.000s |
| P2 | 1040 | 1366 | 327 | 1962.000s |
| P3 | 1539 | 1866 | 328 | 1968.000s |
| OT1 | 2035 | 2077 | 43 | 258.000s |

**Selected source segments:** 1,092
**Total decoded video frames:** 196,560

## Final Reconstruction Artifacts

| Period | Filename | Bytes | SHA-256 |
|---|---|---:|---|
| P1 | `G05_P1_1080p_tsconcat_v2.mp4` | 2,422,319,415 | `4783e15e0dc6deb6dd761bf69a958c8e2fd235ce1e7bcbd15d83f587bfea89e0` |
| P2 | `G05_P2_1080p.mp4` | 2,010,583,291 | `6956f31d1ba999c3aa7302521a33df75b1cae18c309d621ebdb5064f7c0cba91` |
| P3 | `G05_P3_1080p_tsconcat_v2.mp4` | 2,016,753,542 | `f4eb4b0b3a875b2d15829a0a49dc2d63532266a14487dde24aa98fa9cd58b128` |
| OT1 | `G05_OT1_1080p.mp4` | 264,379,977 | `b618640f3f015ced8ef9fe3e0d27d11e18b1f423c1e3a0642304e57749449fc3` |

## Reconstruction Method

- P1 and P3: MPEG-TS byte concatenation followed by lossless MP4 stream-copy remuxing (V2).
- P2 and OT1: FFmpeg concat-demuxer stream copy.
- No video re-encoding was performed.
- Superseded P1/P3 reconstructions remain preserved locally.

## Timestamp Investigation

Initial P1 and P3 reconstructions contained three duplicate video presentation timestamps:

- P1: source boundary 597 → 598.
- P3: source boundary 1767 → 1768.
- P3: source boundary 1840 → 1841.

Original source MPEG-TS files did not contain overlapping presentation timestamps at these boundaries.

Controlled MPEG-TS byte-concatenation tests passed at all three boundaries.

The final P1/P3 V2 MP4s passed:

- Expected decoded frame counts.
- Unique video packet PTS.
- Strictly increasing video packet DTS.
- Full video/audio decoding without warnings.
- Visual and audio playback inspection.

P2 and OT1 passed their original technical validation.

## AWS S3 Archive

**Bucket:** `ewnike-nhl-passing-networks-2026`

**Prefix:** `swiss_nl_2026_finals/G05/reconstruction_v1/`

**Objects:** 6

- Four verified period MP4s.
- `period_boundaries.json`.
- `G05_final_reconstruction_manifest_v1.json`.

**Remote integrity audit:**

- Remote inventory: **PASS — 6/6**
- Remote byte counts: **PASS — 6/6**
- Remote SHA-256: **PASS — 6/6**
- Total archived bytes: **6,714,042,593**

## Metadata Integrity

- Period boundaries SHA-256: `5b4acd7ffca885b9ca65d870c5cbbe5a936948dd46ca869dadd650524c3dab2e`
- Final reconstruction manifest SHA-256: `c103969d05d90953b6dc1c1620fccceccb2470ba452e37a6b835ef7c177695ad`

## Archival Scope

The six-object reconstruction archive is complete and remotely verified.

The original 2,022 source MPEG-TS files and acquisition receipts are preserved locally and are not included in this six-object S3 reconstruction checkpoint.

## Player Identification Notes

- HCD #70 Enzo Covi was observed in G05.
- Additional returning HC Davos players require roster reconciliation.
- Game-specific player rosters should be maintained for the 8,800-image identification library.

## Next Steps

1. Begin G06 source acquisition.
2. Register G06 playlists and acquisition receipts.
3. Identify period boundaries and reconstruct native-1080p MP4s.
4. Validate G06 and archive verified outputs.
5. Continue player-identification and passing-event workflows.
