# G03 — Championship Video Acquisition Checkpoint

Date: 2026-11-05
Project: NHL Puck Tracking & Passing Networks
Status: COMPLETE — S3 SHA-256 integrity verified

## Acquisition

- Competition: Swiss National League Finals
- Season: 2025–2026
- Game: G03
- Source: FloHockey
- Broadcast date: April 22, 2026
- Original HLS segments: 2,488
- Segment range: 147–2634
- Missing segments: 0
- Duplicate sequences: 0
- Empty segments: 0
- Manifest size mismatches: 0
- Original broadcast duration: 14,922 seconds (248.7 minutes)
- Original TS storage: 14.673 GiB
- HLS discontinuities: 1, after the first seven playlist segments

## Five-Period Boundary Inventory

| Period | Start segment | End segment | Start reference | End reference |
|---|---:|---:|---|---|
| P1 | 462 | 764 | 462_04 | 764_00 |
| P2 | 945 | 1273 | 945_00 | 1273_00 |
| P3 | 1456 | 1763 | 1456_05 | 1762_01 |
| OT1 | 1943 | 2248 | 1943_02 | 2247_03 |
| OT2 | 2431 | 2595 | 2431_05 | 2590_00 |

Total selected segments: 1,411.

Boundary status: Visually identified, pending exact frame validation.

P3, OT1, and OT2 include provisional boundary selections or
post-event safety margins.

## Double-Overtime Evidence

- Regulation ended tied 2–2.
- OT1 opening reference: 1943_02.
- OT1 ending reference: 2247_03.
- OT2 pre-faceoff reference: 2431_05.
- First confirmed OT2 gameplay reference: 2432_00.
- Apparent winning team: Fribourg-Gottéron.
- Winning-goal interval: segments 2589–2590.
- Frame 2589_05: puck observed in goaltender crease.
- Frame 2590_00: referee signaling goal; FRI celebration begins.
- Approximate game clock: 11:14 remaining in OT2.
- OT2 MP4 ends at segment 2595 to retain celebration footage.

The exact puck-crossing frame remains unverified.

## MP4 Assembly

Five period videos were assembled using FFmpeg stream copying.

| File | Duration (seconds) | Approximate size |
|---|---:|---:|
| G03_P1.mp4 | 1817.88 | 1.86 GB |
| G03_P2.mp4 | 1974.02 | 2.02 GB |
| G03_P3.mp4 | 1847.97 | 1.89 GB |
| G03_P4.mp4 | 1835.88 | 1.88 GB |
| G03_P5.mp4 | 989.93 | 1.01 GB |

Technical properties:

- Video: H.264
- Audio: AAC
- Resolution: 1920 × 1080
- Nominal frame rate: 25 FPS
- Visual playback: PASS for all five periods

P5 assembly produced non-monotonic DTS warnings.
Visual playback passed, but full packet-level timestamp integrity
has not been independently established.

Original TS files and assembled MP4s remain unchanged.

## AWS S3 Archive

Bucket: ewnike-nhl-passing-networks-2026

Prefix: swiss_nl_2026_finals/G03/

Uploaded objects: 7
Remote objects verified: 7
Remote size mismatches: 0
Remote SHA-256 mismatches: 0

Remote integrity audit: PASS

Integrity manifest:
metadata/G03_s3_integrity_manifest_v1.json

Manifest SHA-256:
f6ea7aa70135c09240f1dfe463380135e5938696ab835393c00775e666066cdd

The five MP4s, period-boundary metadata, and integrity manifest
are verified in S3.

The original 2,488 TS segments remain local and were not included
in this seven-object S3 archive.

## Next Research Tasks

1. Complete G04 acquisition and manifest audit.
2. Identify G04 period boundaries.
3. Assemble and visually validate G04 MP4s.
4. Create SHA-256 integrity manifest.
5. Upload G04 to AWS S3.
6. Verify remote SHA-256 integrity.
7. Continue acquisition of G05–G07.

## Final Checkpoint

G03 ACQUISITION: PASS
G03 FIVE-PERIOD ASSEMBLY: PASS
G03 VISUAL PLAYBACK: PASS
G03 S3 REMOTE INTEGRITY: 7/7 PASS
G03 ORIGINAL TS BACKUP TO S3: NOT PERFORMED
