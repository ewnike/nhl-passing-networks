# G05 — Source Acquisition Complete Checkpoint

**Date:** 2026-11-05
**Project:** NHL Puck Tracking & Passing Networks
**Competition:** Swiss National League Finals, 2025–2026
**Game:** G05 — April 26, 2026
**Status:** SOURCE ACQUISITION VERIFIED

## 1. Executive Summary

Game 5 source acquisition has been completed.

All 2,022 expected MPEG-TS segments were acquired from
the original 1080p rendition.

An independent source integrity audit verified every
downloaded segment against its SHA-256 acquisition receipt.

No missing segments, unexpected segments, or outstanding
failure records were identified.

No lower-resolution recovery was required.

## 2. Registered Source Inventory

| Property | Value |
|---|---|
| Stream ID | 355877 |
| Sequence range | 164–2185 |
| Expected segments | 2,022 |
| Acquired segments | 2,022 |
| Missing segments | 0 |
| Unexpected segments | 0 |
| Duplicate sequences | 0 |
| Playlist duration | 12,120 seconds |
| Total source bytes | 12,802,571,392 |
| Total source GiB | 11.923 |
| Primary resolution | 1920 × 1080 |
| Actual frame rate | 30 FPS (sampled) |
| Video codec | H.264 |
| Audio codec | AAC |
| Audio sample rate | 48,000 Hz |
| Audio channels | 2 |

## 3. Playlist Registration

Seven HLS playlists were registered locally:

- Master playlist
- 1080p media playlist
- 720p media playlist
- 540p media playlist
- 480p media playlist
- 360p media playlist
- 270p media playlist

### Registered Playlist SHA-256 Checksums

| Rendition | SHA-256 |
|---|---|
| master | `1ef5614749cc95de130df7c2cd679379a226f77a29bd5dbfe0330eb7bf142fd1` |
| 1080p | `4b59293945546c3aec199d7ee7abb6434d3a62adc3361ead5c171d4ba3ee344d` |
| 720p | `d81595e672e7aeaddfcec8475c8c785a4e5106f18a905327c2af0907ad5de124` |
| 540p | `30a8ecf2a8a3c4b21d15c3f90f81320cb73fc445ce010c59cda0a5e96ff0f87c` |
| 480p | `87614871e444221e53bcc2d124b5791c5cfeabd67a008c3c825d6c422f952e18` |
| 360p | `caa70629d9000e43091ce144f4837f14eef75d3341a6c2a0a075a4a53008037a` |
| 270p | `fa1ece9392030607acdef1d6d2fc7bc04b03c48d5042a7aa594ef5e3ba089bef` |

Registration manifest:

`metadata/G05_playlist_registration_v1.json`

Registration SHA-256:

`afbc5b674e7625eb453838cca007b9f60d5257b6dcc30694912aa46640736ce2`

All six media playlists contained 2,022 sequences
numbered 164 through 2185.

Cross-rendition sequence and duration alignment passed.

Each media playlist contained two HLS discontinuities
and three EXT-X-DATERANGE markers.

## 4. Media Property Inspection

Representative 1080p segments were inspected using
FFprobe.

Inspected sequences:

- 164
- 1126
- 2185

All three samples reported:

- Video: H.264
- Resolution: 1920 × 1080
- Nominal frame rate: 30 FPS
- Average frame rate: 30 FPS
- Audio: AAC
- Audio sample rate: 48 kHz
- Audio channels: 2
- Segment duration: 6 seconds

The master playlist advertised 25 FPS, whereas
the inspected media contained 30 FPS video.

The 30 FPS observation applies to the inspected
samples and should not be interpreted as a
frame-by-frame audit of the entire broadcast.

## 5. Acquisition Procedure

Downloader:

`scripts/flohockey/acquire_g05_1080p.py`

The acquisition used the registered 1080p playlist.

The downloader supported:

- Configurable concurrent download workers
- Configurable retry attempts
- Per-segment SHA-256 acquisition receipts
- Verification of previously acquired segments
- Resumable acquisition
- Non-destructive handling of existing files
- Failure diagnostics

The controlled initial test acquired ten segments.

A second execution verified and skipped all ten.

The full acquisition used three concurrent workers
and three configured retry attempts.

## 6. Independent Source Integrity Audit

The independent audit reported:

| Check | Result |
|---|---|
| Registered metadata integrity | PASS |
| Expected sequence inventory | PASS |
| MPEG-TS file inventory | PASS |
| Acquisition receipt inventory | PASS |
| Outstanding failure records | 0 |
| Verified source segments | 2,022/2,022 |
| Source SHA-256 integrity | PASS |
| Total source bytes | 12,802,571,392 |

Every stored segment was independently hashed and
compared against its acquisition receipt.

The audit also checked receipt provenance,
sequence identifiers, filenames, source URLs,
playlist identity, and file sizes.

**Final source integrity status: PASS**

## 7. Original Artifact Preservation

Original 1080p MPEG-TS files remain preserved under:

`local_artifacts/flohockey/swiss_nl_2026_finals/G05/source_segments/1080p/`

Per-segment acquisition receipts remain preserved under:

`local_artifacts/flohockey/swiss_nl_2026_finals/G05/metadata/acquisition_1080p/receipts/`

No original source files were overwritten during
the independent audit.

The source footage is excluded from the Git repository.

## 8. Archival Status

This checkpoint confirms successful local source
acquisition and integrity verification.

It does not establish that G05 period videos have
been reconstructed or archived in AWS S3.

Those stages remain pending.

## 9. Next Research Milestone

Identify G05 gameplay period boundaries using
broadcast contact sheets and visual inspection.

Determine whether overtime occurred before
registering final period ranges.

Subsequently:

1. Register period boundaries.
2. Reconstruct period MP4s.
3. Independently validate video outputs.
4. Perform visual playback review.
5. Archive validated artifacts to AWS S3.
6. Independently verify remote SHA-256 checksums.
7. Create the final G05 archival checkpoint.

## Final Checkpoint

**G05 SOURCE INVENTORY: 2022/2022 PASS**

**G05 SHA-256 INTEGRITY: 2022/2022 PASS**

**G05 RECOVERY REQUIRED: NONE**

**G05 SOURCE ACQUISITION STATUS: COMPLETE**
