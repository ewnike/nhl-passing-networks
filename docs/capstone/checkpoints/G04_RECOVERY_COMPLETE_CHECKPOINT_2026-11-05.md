# G04 — Complete Source Recovery Checkpoint

Date: 2026-11-05
Project: NHL Puck Tracking & Passing Networks
Status: SOURCE COVERAGE COMPLETE — PERIOD VALIDATION PENDING

## Acquisition Summary

- Competition: Swiss National League Finals
- Season: 2025–2026
- Game: G04
- Broadcast date: April 24, 2026
- Source: FloHockey
- Expected broadcast sequences: 1,761
- Segment range: 146–1906
- Broadcast duration: 10,560 seconds (176 minutes)
- Native 1080p segments acquired: 1,681
- Original 1080p acquisition failures: 80
- Recovered fallback segments: 80
- Combined unique sequences: 1,761
- Missing sequences: 0
- Overlapping sequences: 0

## Recovery Investigation

The original 1080p acquisition encountered 80 HTTP 403
responses.

All failed sequence numbers ended in digit 6.

The failures were selective rather than universal:
other sequences ending in 6 downloaded successfully.

The master playlist advertised six renditions.

Alternative authorized renditions were inspected using
HTTP byte-range requests.

An accessible fallback rendition was identified for
every missing sequence.

The underlying server-side cause of the HTTP 403
responses remains unconfirmed.

## Recovery Resolution Distribution

| Resolution | Recovered segments |
|---|---:|
| 720p | 20 |
| 540p | 23 |
| 480p | 16 |
| 360p | 12 |
| 270p | 9 |

Total recovered: 80.

These are fallback sources, not native 1080p footage.

## Frame-Rate Investigation

The G04 master playlist advertised 25 FPS.

Sampled original 1080p segments and sampled fallback
segments reported 30 FPS.

The three-segment recovery test established that
30 FPS footage could be successfully decoded.

The full recovery process subsequently validated
all 80 recovered files.

The playlist/frame-rate discrepancy remains documented.

## Recovery Validation

- Recovery files: 80/80 present
- Recovery file sizes: PASS
- Recovery SHA-256 checksums: 80/80 PASS
- Recovery video codec: H.264
- Recovery audio codec: AAC
- Recovery validation: PASS
- Combined sequence inventory: PASS
- Missing sequences: 0
- Original 1080p files unchanged

The original 1080p inventory was checked for
presence, uniqueness, and nonzero size.
This checkpoint does not constitute a new SHA-256
audit of all 1,681 original 1080p files.

## Provenance and Integrity

Original acquisition manifest:

local_artifacts/flohockey/swiss_nl_2026_finals/G04/segments/manifest_146_1906.csv

Original recovery mapping:

local_artifacts/flohockey/swiss_nl_2026_finals/G04/metadata/G04_recovery_manifest_v1.json

Recovery results manifest:

local_artifacts/flohockey/swiss_nl_2026_finals/G04/metadata/G04_recovery_results_v1.json

Recovery mapping SHA-256:

8d775c781dc82d6b6abc5f28995f50eeca75d8c4214afbb5f70f43cc1b937f71

Recovery results SHA-256:

8a43f77364186ae9b2d6f770bc5a66d0e865a803aa72f81d50f356210109a47d

## Research Integrity Considerations

The recovered segments have different spatial
resolutions from the original 1080p footage.

They must remain separately identifiable during
player detection, tracking, jersey recognition,
rink calibration, and passing-event analysis.

Mixed-resolution transport streams must not be
silently concatenated using stream copying.

Any reconstructed viewing or analysis copy must
retain source-resolution provenance.

## Next Steps

1. Generate G04 broadcast timeline contact sheets.
2. Identify regulation-period boundaries.
3. Determine which fallback segments overlap gameplay.
4. Design a mixed-resolution reconstruction workflow.
5. Assemble and validate period MP4s.
6. Generate SHA-256 integrity manifests.
7. Upload validated artifacts to AWS S3.
8. Perform remote SHA-256 verification.

## Final Checkpoint

SOURCE SEQUENCE COVERAGE: 1761/1761 PASS
ORIGINAL 1080P SEGMENTS: 1681
RECOVERED FALLBACK SEGMENTS: 80
RECOVERY SHA-256: 80/80 PASS
MISSING SEQUENCES: 0
PERIOD MP4 ASSEMBLY: NOT STARTED
AWS S3 ARCHIVAL: NOT STARTED
