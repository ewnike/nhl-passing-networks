# G04 — AWS S3 Archive Complete Checkpoint

**Date:** 2026-11-05
**Project:** NHL Puck Tracking & Passing Networks
**Competition:** Swiss National League Finals, 2025–2026
**Game:** G04
**Status:** AWS S3 ARCHIVE VERIFIED

## 1. Executive Summary

G04 source acquisition, recovery, period identification,
mixed-resolution reconstruction, technical validation,
and AWS S3 archival have been completed.

The original 1080p acquisition contained 80 inaccessible
segments. All 80 were subsequently recovered from
alternative authorized renditions.

The complete broadcast inventory contains 1,761 unique
sequences with no missing or overlapping sequences.

Three regulation-period MP4s were reconstructed and
independently validated.

All six archived S3 objects passed remote inventory,
size, metadata SHA-256, and streamed content SHA-256
verification on 2026-11-05.

## 2. Source Acquisition and Recovery

| Metric | Result |
|---|---:|
| Expected broadcast sequences | 1,761 |
| Sequence range | 146–1906 |
| Original 1080p segments | 1,681 |
| Recovered segments | 80 |
| Missing sequences after recovery | 0 |
| Overlapping sequences | 0 |
| Recovered SHA-256 checks | 80/80 PASS |

### Recovery Resolution Distribution

| Resolution | Segments |
|---|---:|
| 720p | 20 |
| 540p | 23 |
| 480p | 16 |
| 360p | 12 |
| 270p | 9 |
| **Total** | **80** |

The cause of the original HTTP 403 failures was not
established.

The recovered sources remain separately preserved,
with their original resolution provenance.

## 3. Registered Period Boundaries

| Period | First segment | Last segment | Segment count |
|---|---:|---:|---:|
| P1 | 469 | 753 | 285 |
| P2 | 932 | 1291 | 360 |
| P3 | 1473 | 1872 | 400 |
| **Total** | | | **1,045** |

The selected ranges preserve the opening faceoffs,
regulation gameplay, and relevant immediate post-period
player activity.

P3 includes immediate postgame celebrations.

## 4. Mixed-Resolution Reconstruction

The reconstruction pipeline normalized 1,045 selected
segments to a common output format.

### Source Distribution Within Selected Periods

| Source resolution | Segments |
|---|---:|
| Native 1080p | 995 |
| Recovered 720p | 12 |
| Recovered 540p | 15 |
| Recovered 480p | 10 |
| Recovered 360p | 9 |
| Recovered 270p | 4 |
| **Total** | **1,045** |

### Output Configuration

- Video codec: H.264
- Resolution: 1920 × 1080
- Frame rate: 30 FPS
- Audio codec: AAC
- Audio sample rate: 48 kHz
- Encoding quality: CRF 18
- Encoding preset: fast

Lower-resolution sources were upscaled for consistent
output dimensions. Upscaling does not restore source
image detail.

Original source-resolution provenance remains relevant
to downstream computer-vision analysis.

### Reconstruction Script

`scripts/flohockey/reconstruct_mixed_resolution_periods.py`

The pipeline supports resumable segment normalization
and separate period assembly.

## 5. Final MP4 Validation

| Period | Duration (seconds) | Video frames | Approx. size |
|---|---:|---:|---:|
| P1 | 1710.021333 | 51,300 | 1.962 GB |
| P2 | 2160.021333 | 64,800 | 2.521 GB |
| P3 | 2400.021333 | 72,000 | 2.765 GB |
| **Total** | **6270.064** | **188,100** | **7.248 GB** |

Independent validation confirmed:

- H.264 video: PASS
- AAC audio: PASS
- 1920 × 1080 resolution: PASS
- 30 FPS nominal and average frame rate: PASS
- Expected frame counts: PASS
- Expected durations: PASS
- Local SHA-256 checksums: PASS
- Visual playback review: PASS

## 6. AWS S3 Archive

**Bucket:** `ewnike-nhl-passing-networks-2026`

**Prefix:** `swiss_nl_2026_finals/G04/`

### Archived Object Inventory

| Relative S3 key | Size (bytes) | SHA-256 |
|---|---:|---|
| `periods/G04_P1.mp4` | 1,961,571,216 | `21041b4e6508eaa7af3077691c1ec94e5568b49ae61d8bd6c06eb53f59c18026` |
| `periods/G04_P2.mp4` | 2,521,482,962 | `eae7118bb18325bc50fd142c9c8b3ef62eded416b0dd246b476792a548d850f5` |
| `periods/G04_P3.mp4` | 2,765,135,457 | `c46ef75e0aa63e8d702257f746c0a3c18c53b1d489ecddc671032cc285433b7c` |
| `metadata/period_boundaries.json` | 1,097 | `c577bdb3e18126b761b48e7860e36836a313bbd52ec88ba7b5f001128b5ed8e4` |
| `metadata/G04_recovery_results_v1.json` | 31,097 | `8a43f77364186ae9b2d6f770bc5a66d0e865a803aa72f81d50f356210109a47d` |
| `metadata/G04_s3_integrity_manifest_v1.json` | 936 | `0827e578e2656c8ae40da310fac463af4f62f7a0adf9d071bb5c77d032b49ba7` |

### Remote Integrity Verification

The final AWS S3 integrity audit reported:

- Expected remote objects: 6
- Verified remote objects: 6
- Remote inventory: PASS
- Remote object sizes: PASS
- SHA-256 object metadata: PASS
- Independently streamed content SHA-256: PASS
- Missing objects: 0
- Unexpected objects: 0

**Final archival status: PASS — G04 S3 ARCHIVE VERIFIED**

The remote audit was completed on 2026-11-05.
This checkpoint records its successful terminal output;
it does not rerun the remote audit.

## 7. Research Observation — Player Participation

During G04 video inspection, Adam Tambellini
(#19, HC Davos) was observed participating.

He was not observed in G01 during the earlier review.

This is a game-specific video observation, not an
independently verified official lineup comparison.

Player participation should be tracked separately
for each game rather than assumed constant across
the series.

## 8. Preservation and Research Integrity

The following local artifacts remain preserved:

- Original 1080p MPEG-TS segments
- Recovered lower-resolution MPEG-TS segments
- Recovery manifests and SHA-256 records
- Period boundary metadata
- Normalized intermediate video segments
- Three reconstructed period MP4s

The original source files were not overwritten.

The normalized output resolution must not be confused
with the native source resolution.

## 9. Next Research Milestone

Proceed to G05 acquisition.

Identified G05 master playlist:

`https://d17cyqyz9yhmep.cloudfront.net/streams/355877/playlist_vo_1777224672000_1777236803350.m3u8`

Before downloading G05:

1. Inspect the complete master playlist.
2. Identify the highest-quality rendition.
3. Verify the complete segment inventory.
4. Check for discontinuities and unusual durations.
5. Establish a new acquisition manifest.
6. Download and validate source segments.
7. Preserve acquisition provenance and checksums.

## Final Checkpoint

**G04 SOURCE COVERAGE: 1761/1761 PASS**

**G04 RECOVERY: 80/80 PASS**

**G04 PERIOD MP4S: 3/3 PASS**

**G04 AWS S3 REMOTE INTEGRITY: 6/6 PASS**

**G04 ARCHIVAL STATUS: COMPLETE**
