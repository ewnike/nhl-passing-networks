# G04 — Partial Acquisition and Recovery Checkpoint

Date: 2026-11-05
Project: NHL Puck Tracking & Passing Networks

Status: PARTIAL ACQUISITION — RECOVERY PLANNED

## Broadcast Acquisition

- Competition: Swiss National League Finals
- Season: 2025–2026
- Game: G04
- Broadcast date: April 24, 2026
- Source: FloHockey
- Expected segments: 1,761
- Segment range: 146–1906
- Broadcast duration: 10,560 seconds (176 minutes)
- Native resolution: 1920 × 1080
- Nominal frame rate: 25 FPS
- Downloaded 1080p segments: 1,681
- Missing 1080p segments: 80
- HTTP failure: 403 Forbidden
- All 80 failed sequences end in digit 6
- Duplicate local sequences: 0
- Empty local files: 0

## Rendition Investigation

The master playlist advertises six renditions:

| Resolution | Bandwidth | Rendition ID |
|---|---:|---:|
| 1080p | 8000000 | 1 |
| 720p | 5000000 | 2 |
| 540p | 2800000 | 3 |
| 480p | 2000000 | 4 |
| 360p | 1200000 | 5 |
| 270p | 600000 | 6 |

## Recovery Findings

- Missing 1080p sequences: 80
- Accessible at 720p: 20
- Accessible at lower renditions: 60
- Remaining sequences without an identified fallback: 0
- Fallback files downloaded: 0

Availability was established using HTTP byte-range requests.
Full-object download and decoding remain unverified.

The lower-rendition survey stopped at the first accessible
rendition in descending quality order.

## Research Integrity

The 1,681 original 1080p TS files remain unchanged.

The original acquisition manifest is preserved at:

local_artifacts/flohockey/swiss_nl_2026_finals/G04/segments/manifest_146_1906.csv

Recovery manifest:

local_artifacts/flohockey/swiss_nl_2026_finals/G04/metadata/G04_recovery_manifest_v1.json

Fallback segments must be stored separately and retain
their original resolution and rendition provenance.

No mixed-resolution MP4 has been assembled.

## Next Steps

1. Preserve recovery metadata in Git.
2. Download authorized fallback segments into separate directories.
3. Validate file sizes, codecs, and SHA-256 checksums.
4. Establish complete sequence coverage.
5. Determine a scientifically defensible reconstruction strategy.
6. Identify G04 period boundaries.
7. Assemble and validate period MP4s.
8. Archive validated artifacts in S3.

## Checkpoint Status

1080P ACQUISITION: PARTIAL
1080P SEGMENTS: 1681/1761
MISSING SEGMENTS: 80
FALLBACK AVAILABILITY: 80/80
FALLBACK DOWNLOAD: NOT STARTED
ORIGINAL ARTIFACTS: PRESERVED
