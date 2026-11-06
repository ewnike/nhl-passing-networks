# G07 Reconstruction — S3 Verified Checkpoint

**Checkpoint date:** 2026-11-06
**Series:** Swiss National League Finals — seven-game series
**Game:** G07
**Status:** Reconstruction complete; independent S3 integrity verified

## 1. Original Acquisition

- Original MPEG-TS sequences: **2,388**
- Source sequence range: **323–2710**
- Original 1080p segments: **2,379**
- Lower-resolution recovered segments: **9**
- Original MPEG-TS files and acquisition receipts: **preserved locally**
- Original MPEG-TS files archived to S3: **No**

The original acquisition artifacts remain separate from this
reconstructed-period archive.

## 2. Reconstructed Periods

| Period | Sequences | Segments | Frames | Duration |
|---|---|---:|---:|---|
| P1 | 491–825 | 335 | 50,250 | 33:30 |
| P2 | 1005–1317 | 313 | 46,950 | 31:18 |
| P3 | 1495–1879 | 385 | 57,750 | 38:30 |
| OT1 | 2055–2144 | 90 | 13,500 | 9:00 |
| **Total** | | **1,123** | **168,450** | **112:18** |

All four outputs use:

- Resolution: **1920 × 1080**
- Frame rate: **25 FPS**
- Video: **H.264**
- Audio: **AAC stereo, 48 kHz**

All four reconstruction validations passed.

Independent full video/audio decoding completed successfully
for P1, P2, P3, and OT1.

## 3. Reconstructed MP4 SHA-256 Checksums

| Period | SHA-256 |
|---|---|
| P1 | `11165c14845bb2f2c59e9ac2ebd0de9569c1078fc0f5f3b39d55547498cb11ba` |
| P2 | `2d09b221680d8f7ec607eec9c0add9414266c5ea9226b5168414c07f6c0263ef` |
| P3 | `9b318078ab60a29f69aa58c4883c13f80c4c5d43a917b52e635e38065424e86f` |
| OT1 | `10061cb8644a6a7e64cd574cfc287eee435050928613d136edd859881c97f066` |

## 4. Reconstruction Manifest

**File:** `metadata/G07_final_reconstruction_manifest_v1.json`

**SHA-256:** `c2b0d0fe3ea53bdaecd5823b52db890ae60212ae3a7a3554546395d5cddaac4c`

The immutable manifest records the seven source archive artifacts,
their exact byte sizes, and their SHA-256 checksums.

The manifest itself is the eighth archived object.

## 5. AWS S3 Archive

**Bucket:** `ewnike-nhl-passing-networks-2026`

**Prefix:** `flohockey/swiss_nl_2026_finals/G07/`

### Independent Remote Integrity Audit

| Check | Result |
|---|---|
| Remote objects | 8/8 |
| Total remote bytes | 8,789,125,812 |
| Remote inventory | PASS |
| Remote SHA-256 | PASS — 8/8 |
| S3 checkpoint integrity | PASS |

The audit independently streamed all eight remote objects and
compared their SHA-256 hashes against the immutable local manifest.

Stored S3 checksum metadata was not used as a substitute for
independently hashing the remote bytes.

## 6. Remaining Qualifications

1. Period boundaries are **provisional**, based on user-supplied
   FloHockey playback timestamps.
2. Exact period opening and ending frames require visual review.
3. The original 2,388 MPEG-TS segments and their acquisition
   receipts have **not** been archived to S3.
4. The reconstruction checkpoint does not constitute completion
   of the entire seven-game acquisition project.

## 7. Checkpoint Conclusion

**G07 reconstructed-period archival milestone: COMPLETE.**

- Four reconstructed periods validated.
- All expected video frames accounted for.
- Full video/audio decoding passed.
- Eight S3 objects independently SHA-256 verified.
- Original local artifacts preserved.

The next workstream is visual boundary review and subsequent
computer-vision experimentation.
