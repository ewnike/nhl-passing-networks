# FloHockey G02–G07 acquisition and S3 archival runbook

**Project:** NHL Puck Tracking & Passing Networks
**Prepared:** 2026-10-25
**Revision:** 2 (reconciled with recovered G01 history)
**Status:** Reconstructed from actual G01 Python scripts and AWS reference attached to this project, plus terminal-history excerpts in our conversation. Relevant G01 zsh-history excerpts have now been inspected and two Python heredocs located. The complete Mac repository and full history have **not** been independently audited.

## 1. What we recovered

| Source | Verified role | G02–G07 adaptation |
|---|---|---|
| `download_game1_ts_segments.py` | Actual Python file: fetches HLS playlist, chooses variant by bandwidth, previews numbered `.ts` segments, downloads a selected range with retries, writes manifest. Dry-run default. | Supply **new authorized playlist**, verified bitrate, start/end sequence and per-game output directory. Do not use hardcoded G01 playlist. |
| `build_game_periods.py` | Actual Python file: reads `metadata/period_boundaries.json`, checks missing/ambiguous TS sequences, creates FFmpeg concat list, remuxes period MP4s, checks with `ffprobe`. Dry-run default. | Supply `--root` per game; verify period boundaries visually first. |
| `AWS_S3_COMMAND_REFERENCE.md` | Actual project reference: S3 commands, backup layout, G01 observations, warnings and verification. | Parameterize S3 prefixes, verify each upload. |
| `scripts/flohockey/generate_contact_sheet.py` | Seen in terminal history, not inspected as a local source file. | Review existing script; useful for visual QC. |
| `docs/flohockey/pilot_frame_extraction.md` | Filename seen in terminal history; content not inspected. | Downstream frame QC, not acquisition. |
| `~/.zsh_history` | Recovered G01 acquisition-history excerpt (~16400–17280): playlist inspection, downloads, S3 operations, thumbnails, period investigation and reconstruction. Two Python heredocs identified. | Relevant excerpt inspected; full history not independently audited. |

**Important:** The download script has a game-specific default playlist URL and writes full segment URLs to its CSV manifest. Signed URLs, cookies, tokens and credentials must stay out of Git and shared documents. Use only streams you are authorized to access and archive; do not bypass DRM or access controls.

## 2. End-to-end flow

```text
Authorized FloHockey game page / HLS playlist
  -> verify correct G0N game and media variant
  -> inventory TS segment numbers and durations (dry run)
  -> download original TS + private manifest
  -> verify counts, continuity, integrity and playback
  -> archive original TS after S3 dry-run and verification
  -> inspect thumbnails and locate period boundaries
  -> write game-specific metadata/period_boundaries.json
  -> dry-run / execute period MP4 reconstruction
  -> ffprobe and visually review each period
  -> S3 dry-run -> upload period MP4s and sanitized metadata
  -> S3 listing + exact-key and integrity verification -> mark game complete
```

## 3. Standard game layout

```text
local_artifacts/flohockey/swiss_nl_2026_finals/G02/
  segments/                 # original TS; PRIVATE manifest_START_END.csv from downloader
  metadata/period_boundaries.json
  periods/G02_P1.mp4        # also P2 and P3, if applicable
  thumbnails/               # visual QC
  manifests/                # sanitized inventories and checksums only

s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_002/
  segments/
  periods/
  metadata/
  manifests/
```

Use `G03`/`game_003` through `G07`/`game_007`. These are **proposed consistent destinations**, not verified existing S3 objects.

## 4. Preflight (G02 example)

Run from repository root:

```bash
cd ~/Documents/github/nhl-passing-networks
GAME=G02
NUMBER=002
ROOT="local_artifacts/flohockey/swiss_nl_2026_finals/$GAME"
S3="s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_$NUMBER"
mkdir -p "$ROOT"/{segments,metadata,periods,thumbnails,manifests}
ffmpeg -version | head -1
ffprobe -version | head -1
aws sts get-caller-identity
aws s3 ls "$S3/" --recursive --summarize
```

Confirm the S3 prefix is empty or contains only the intended game before writing. Privately record game identity, source authorization, event page, actual playlist, available variants, segment range, acquisition date, and expected video duration. **Do not assume G01's bandwidth or segment numbering applies to G02.**

## 5. Download workflow

The recovered script takes `--playlist`, `--bandwidth`, `--start`, `--end`, `--output`, `--retries`, and `--download`. It does **not** discover a new game's playlist automatically. The example below uses placeholders deliberately:

```bash
# Set from the authorized source, not by guessing:
PLAYLIST='<authorized-G02-master-or-media-playlist>'
BANDWIDTH=<verified-bandwidth>
START=<verified-first-sequence>
END=<verified-last-sequence>

# Preview only; does not download:
python scripts/flohockey/download_game1_ts_segments.py \
  --playlist "$PLAYLIST" --bandwidth "$BANDWIDTH" \
  --start "$START" --end "$END" --output "$ROOT/segments"

# After inspecting the preview, repeat with --download:
python scripts/flohockey/download_game1_ts_segments.py \
  --playlist "$PLAYLIST" --bandwidth "$BANDWIDTH" \
  --start "$START" --end "$END" --output "$ROOT/segments" \
  --download
```

Do not execute with placeholders. **Actual downloader manifest location:** `"$ROOT/segments/manifest_START_END.csv"` (not `manifests/`). It contains full source URLs: keep private and exclude from Git and S3. This G01 downloader assumes TS filenames ending in `_NUMBER.ts`; different HLS packaging, encryption, discontinuities, or playlist naming requires separate evaluation. It skips existing nonempty files without checksum verification.

## 6. Verify TS inventory and locate periods

```bash
find "$ROOT/segments" -maxdepth 1 -name '*.ts' -type f | wc -l
find "$ROOT/segments" -maxdepth 1 -name '*.ts' -type f -size 0 -print
ls -lh "$ROOT/segments"/manifest_*.csv
```

Compare exact sequence IDs and filenames with the **actual playlist** (including missing, duplicate and unexpected entries), inspect representative files with `ffprobe`, and visually review transitions. Maintain a sanitized filename/size/SHA-256 inventory under `manifests/`; a nonempty file is not proof of integrity. G01 history used FFmpeg thumbnails such as:

```bash
ffmpeg -hide_banner -loglevel error -y \
  -ss 3 -i "$ROOT/segments/<verified-filename>.ts" \
  -frames:v 1 -q:v 2 "$ROOT/thumbnails/inspection.jpg"

ffmpeg -hide_banner -loglevel error -y \
  -i "$ROOT/segments/<verified-filename>.ts" \
  -vf 'fps=1' -q:v 2 "$ROOT/thumbnails/sample_%02d.jpg"
```

**Recovered G01 visual workflow:** first sample every tenth segment (`125, 135, …, 2125`) at approximately two seconds into each TS file. The Pillow heredoc (history extract line 229) sorted `segment_*.jpg` numerically, then created 5-column × 5-row contact sheets with 320×180 thumbnails, 35-pixel labels and JPEG quality 90 (`contact_sheet_01.jpg`, etc.). After coarse review, G01 used targeted neighboring-segment loops and `-vf 'fps=1'` for finer inspection. Examples of exploratory ranges: 436–444, 725–735, 906–915, 1265–1275, 1455–1465 and 1990–2003. **Do not treat exploratory ranges as final boundaries.** The existing `generate_contact_sheet.py` has not been inspected for compatibility with `segment_*.jpg`; check before reuse.

**Authoritative G01 provisional boundaries** from `metadata/period_boundaries.json`:

| Period | Start segment | Start frame reference | End segment | End frame reference | Inclusive segments |
|---|---:|---|---:|---|---:|
| P1 | 443 | `443_06` | 731 | `731_04` | 289 |
| P2 | 911 | `911_01` | 1266 | `1266_06` | 356 |
| P3 | 1456 | `1456_01` | 1992 | `1992_02` | 537 |

Status is **`visually_identified_pending_frame_validation`**. The period builder uses whole segments and does not trim to the referenced frames. These G01 values must never be copied as G02 boundaries.

Use thumbnails and contact sheets to determine period boundaries; do not assume a fixed number of TS files per period. The builder expects a `periods` object with numbered keys and `start_segment` / `end_segment`, plus optional `start_frame_reference` / `end_frame_reference`. For example, **schema only (not valid boundaries)**:

```json
{"game_id":"G02","periods":{"1":{"start_segment":0,"end_segment":0,"start_frame_reference":"PENDING","end_frame_reference":"PENDING"}}}
```

Fill all actual periods and replace all placeholders **before** running the builder. Review intermissions, replays, discontinuities and overtime.

## 7. Build period MP4s

```bash
python scripts/flohockey/build_game_periods.py --root "$ROOT"             # dry run
python scripts/flohockey/build_game_periods.py --root "$ROOT" --execute   # after verification
for f in "$ROOT"/periods/*.mp4; do
  ffprobe -v error -show_entries format=duration,size -of json "$f"
done
```

The builder uses FFmpeg concat + stream copy and refuses existing output unless explicitly overwritten. **Portability issue:** its concat-list and temporary MP4 filenames still contain `G01` even when `--root` selects another game. Generalize these before concurrent G02–G07 builds, retaining the original G01 version. Validate start/end and interior playback, timestamps, audio/video synchronization and continuity; `ffprobe` size/duration alone is not sufficient.

## 8. S3 backup and verification

```bash
# Read-only previews:
aws s3 sync "$ROOT/segments/" "$S3/segments/" --exclude '*' --include '*.ts' --dryrun
aws s3 sync "$ROOT/periods/" "$S3/periods/" --exclude '*' --include '*.mp4' --dryrun
aws s3 cp "$ROOT/metadata/period_boundaries.json" "$S3/metadata/period_boundaries.json" --dryrun

# After reviewing exact destination and contents:
aws s3 sync "$ROOT/segments/" "$S3/segments/" --exclude '*' --include '*.ts' --no-progress
aws s3 sync "$ROOT/periods/" "$S3/periods/" --exclude '*' --include '*.mp4' --no-progress
aws s3 cp "$ROOT/metadata/period_boundaries.json" "$S3/metadata/period_boundaries.json"

# Read-only checks:
aws s3 ls "$S3/segments/" --recursive --summarize
aws s3 ls "$S3/periods/" --recursive --summarize
aws s3 ls "$S3/metadata/" --recursive
```

Never use `--delete` casually. Compare **exact expected S3 keys and sizes**, not just counts. `aws s3 sync` is not cryptographic integrity verification. Keep a sanitized local SHA-256 inventory and independently verify important archived objects. Do not upload raw manifests containing signed source URLs.

## 9. G01 reference observations (not targets for other games)

From the attached AWS command reference: G01 had **2,004 local TS files** and **2,005 S3 TS objects**, including one differently named extra object. Local period MP4s were P1 **1,775,952,575 bytes / 1734.020 s**, P2 **2,188,105,965 bytes / 2135.924 s**, P3 **3,299,308,564 bytes / 3221.894667 s**. Reported video H.264 1920×1080 25 fps, audio AAC. **The recovered history shows period-MP4 sync and metadata-copy commands were executed, followed by an S3 listing, but does not independently confirm upload success. Verify live objects before marking archived.**

## 10. Recover remaining heredocs and scripts

**Recovered heredocs:**

1. OpenCV inspection of `segment-..._445.ts` (extract line 26): reports FPS, reported frame count, first-frame decoding and dimensions without modifying the TS file.
2. Pillow contact-sheet generator (extract line 229): numeric segment sorting and 5×5 sheets, used for visual period identification.

**Recovered command chronology:** playlist inspection (~extract lines 100–110); downloader preview and range downloads (~110–145); S3 segment sync and verification (~145–170); coarse thumbnails (~170–228); Pillow sheets (~229–295); fine boundary inspection (~300–840); JSON edit, builder, FFprobe, MP4 and metadata S3 commands (~845–880). These are approximate **extracted-file line numbers**, not full zsh-history line numbers. Source: `local_artifacts/flohockey/workflow_audit/G01_acquisition_history.txt` (keep local; may contain private URLs).

The optional `audit_flohockey_workflow.py` scans the **local** repository and `~/.zsh_history` without executing historical commands. Run:

```bash
python scripts/flohockey/audit_flohockey_workflow.py \
  --repo ~/Documents/github/nhl-passing-networks \
  --history ~/.zsh_history \
  --output-dir ~/Documents/github/nhl-passing-networks/local_artifacts/flohockey/workflow_audit
```

Review `workflow_inventory.md` and the redacted `history_matches.txt` locally. Redaction is best effort; review again before sharing. Compare against `git log --all --name-only -- scripts/flohockey docs/flohockey`. The history excerpts we have already seen include `ffmpeg -vf 'fps=1'` thumbnails, `ffmpeg -ss 3 -frames:v 1`, TS inspection, and Python heredocs for contact sheets. **The two heredocs above are confirmed in the inspected excerpt; other sessions may contain more.**

Suggested repository destinations: `docs/flohockey/FLOHOCKEY_ACQUISITION_RUNBOOK.md`, `scripts/flohockey/audit_flohockey_workflow.py`. Keep original G01 scripts intact until generalized versions are tested on G02.

## 11. Per-game completion checklist

- [ ] Authorized source and correct game verified; no unsupported encryption/DRM or HLS features.
- [ ] S3 game prefix inspected before any upload.
- [ ] Variant, segment range and estimated duration verified.
- [ ] Download preview checked; original TS complete and nonempty.
- [ ] Segment continuity and representative playback validated.
- [ ] Period boundaries independently reviewed and recorded.
- [ ] MP4 build dry-run, execution, ffprobe and visual QC passed.
- [ ] S3 upload previews reviewed; no destructive flags.
- [ ] Segment, MP4 and metadata backups verified, with integrity checks.
- [ ] Sanitized manifest and provenance archived; raw URL-bearing manifests remain private.
- [ ] Exact S3 keys/sizes compared and selected objects independently hash-verified.
- [ ] Boundary status explicitly marked provisional or frame-validated.

**Recommended sequence:** Complete G02 end-to-end before running a six-game batch. Then reuse the verified pattern for G03–G07.


## 12. Operational status and next improvements

**G01 executed, not necessarily fully verified:** Downloader, TS segment sync, thumbnail loops, Pillow heredoc, boundary JSON, period builder, FFprobe, MP4 sync, metadata copy and S3 listing all appear in the supplied history. Historical G01 counts and sizes are recorded above. Actual current S3 objects must be checked.

**G02 proposed / not yet tested:** Confirm playlist, variant, naming and authorization; test the downloader dry run; generalize hardcoded G01 temporary filenames; validate full TS inventory; inspect boundaries; build and review periods; archive and independently verify. Complete G02 end-to-end before attempting a six-game batch.

**Preserve original scripts first:** Existing `scripts/flohockey/` files were previously untracked. Review and commit the exact G01 working versions before refactoring. A future generalized downloader should reject unsupported playlist features, avoid silent acceptance of truncated existing files, and separate sanitized manifests from source-URL manifests. Do not claim these improvements are implemented yet.
