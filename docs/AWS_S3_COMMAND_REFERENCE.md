# AWS S3 Command Reference

**Project:** NHL Puck Tracking & Passing Networks  
**Environment:** macOS / zsh, AWS CLI  
**Purpose:** A practical, reusable record of AWS commands used to preserve and inspect FloHockey Game 1 assets.

> **Repository destination:** `docs/AWS_S3_COMMAND_REFERENCE.md`  
> **Bucket:** `ewnike-nhl-passing-networks-2026`  
> **Game prefix:** `raw/flohockey/game_001/`

## 1. Key concepts

- **Bucket:** The top-level S3 storage container.
- **Object:** A stored file, identified by its **key** (path-like name).
- **Prefix:** The shared beginning of object keys; S3 does not require real folders.
- **Local path:** A file on your Mac, such as `local_artifacts/...`.
- **S3 URI:** A destination or source passed to the AWS CLI, such as `s3://bucket/prefix/`. **Do not type an S3 URI by itself at the zsh prompt**; it is not a shell command.
- **`\` at end of line:** Continues a command onto the next line in zsh. It must be the final character on the line (no trailing spaces). Do not run individual option lines separately.

## 2. Project paths

```bash
BUCKET="ewnike-nhl-passing-networks-2026"
S3_GAME="s3://$BUCKET/raw/flohockey/game_001"
LOCAL_GAME="local_artifacts/flohockey/swiss_nl_2026_finals/G01"
```

Current working layout:

```text
s3://ewnike-nhl-passing-networks-2026/
└── raw/flohockey/game_001/
    ├── segments/     # Original .ts video segments
    ├── periods/      # Reconstructed G01_P1.mp4, G01_P2.mp4, G01_P3.mp4
    └── metadata/     # period_boundaries.json
```

The `periods/` and `metadata/` prefixes are intended backup destinations; **verify uploads before assuming those objects exist**.

## 3. Read-only inspection commands (🟢)

### List objects under the segments prefix

```bash
aws s3 ls \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/segments/
```

`ls` lists objects. Without `--recursive`, nested prefixes may appear as `PRE` entries.

### Recursively list objects and summarize their total

```bash
aws s3 ls \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/segments/ \
  --recursive \
  --summarize
```

- `--recursive`: Traverse all keys beneath the prefix.
- `--summarize`: Print `Total Objects` and `Total Size` at the end.
- **Caution:** `Total Objects` includes non-video objects such as `.keep`.

### Count only `.ts` objects

```bash
aws s3 ls \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/segments/ \
  --recursive \
  | awk '$4 ~ /\.ts$/ {count++} END {print "S3 TS files:", count+0}'
```

- `|` pipes one command's output into another.
- `awk` examines fields of each listing row.
- `$4` is the object key in standard `aws s3 ls` output.
- `/\.ts$/` matches names ending in `.ts` (`$` means end of string).
- `count++` increments the count for matching rows.
- `END` prints the final count; `count+0` prints zero if nothing matched.

**Observed in our session:** 2,005 S3 `.ts` objects, versus 2,004 local `.ts` files. The extra S3 object had a different segment-name timestamp (`segment-1777384806782_1_1651.ts`). This is an **extra object**, not proof of identical video content. File-size matches are not proof of duplication; use checksums for that.

### Verify backed-up MP4s

```bash
aws s3 ls \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/periods/ \
  --recursive \
  --summarize
```

After a successful backup, expect **three** `.mp4` objects totaling **7,263,371,104 bytes**, based on the three local `ffprobe` sizes observed on 2026-10-22. Check the actual listing rather than assuming upload success.

## 4. Upload and download commands (🟡 modifies destination)

### Upload one metadata file

```bash
aws s3 cp \
  local_artifacts/flohockey/swiss_nl_2026_finals/G01/metadata/period_boundaries.json \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/metadata/period_boundaries.json
```

`cp` copies one file from the first path (source) to the second (destination). The same command can copy from S3 back to your Mac by reversing the paths. Uploading to an existing key may replace the existing object.

### Upload/synchronize only MP4 period files

```bash
aws s3 sync \
  local_artifacts/flohockey/swiss_nl_2026_finals/G01/periods/ \
  s3://ewnike-nhl-passing-networks-2026/raw/flohockey/game_001/periods/ \
  --exclude "*" \
  --include "*.mp4" \
  --no-progress
```

- `sync` transfers missing or changed files, using AWS CLI comparison rules (typically size and timestamps for local-to-S3 transfers); it does **not** prove cryptographic equality.
- `--exclude "*"` starts by excluding all files.
- `--include "*.mp4"` re-includes MP4 files. **Filter order matters.**
- `--no-progress` hides transfer progress output; it does not prevent uploads.
- Without `--delete`, extra destination objects are **not** removed.

### Preview a sync before uploading

```bash
aws s3 sync \
  "$LOCAL_GAME/periods/" \
  "$S3_GAME/periods/" \
  --exclude "*" \
  --include "*.mp4" \
  --dryrun
```

`--dryrun` displays planned transfers without performing them. This is a good habit before large uploads.

### Download a single object

```bash
aws s3 cp \
  "$S3_GAME/metadata/period_boundaries.json" \
  "$LOCAL_GAME/metadata/period_boundaries_from_s3.json"
```

This retrieves a copy under a different local filename so it will not overwrite the working metadata file.

## 5. Local checks (not AWS commands)

### Count local `.ts` files

```bash
find "$LOCAL_GAME/segments" -type f -name "*.ts" | wc -l
```

`find` locates matching files; `wc -l` counts output lines. In our session, this returned **2,004**.

### Check local MP4 sizes

```bash
ls -lh "$LOCAL_GAME/periods/"
```

The `-h` flag shows human-readable sizes; use `ffprobe` or `stat` for exact byte counts.

### Detect byte-identical local TS files by SHA-256

```bash
find "$LOCAL_GAME/segments" -type f -name "*.ts" -print0 \
  | xargs -0 shasum -a 256 \
  | awk '{print $1}' \
  | sort \
  | uniq -d
```

No output means no repeated SHA-256 digest among the files examined. It does **not** rule out duplicate scenes or overlapping video with different bytes.

## 6. Safety legend

| Level | Examples | Meaning |
|---|---|---|
| 🟢 Read-only | `aws s3 ls`, `--recursive`, `--summarize` | Inspects storage without changing objects. |
| 🟡 Writes destination | `aws s3 cp`, `aws s3 sync` | Can create or replace destination objects. |
| 🔴 Destructive | `aws s3 rm`, `aws s3 sync --delete` | Can remove stored objects. Do not run without deliberate review and backups. |

**Policy for this project:** Preview large syncs with `--dryrun`; verify after transfer. Do not run destructive S3 commands without explicitly reviewing their effects.

## 7. Common mistakes and fixes

| Symptom | Why it happens | Fix |
|---|---|---|
| `zsh: no such file or directory: s3://...` | An S3 URI was entered as a command. | Prefix it with `aws s3 ls`, `aws s3 cp`, etc. |
| `zsh: command not found: --recursive` | A multiline command was broken. | Ensure each continued line ends in `\` with no trailing spaces. |
| S3 object count exceeds `.ts` count | Prefix also contains `.keep` or other file types. | Filter on `.ts` using `awk`. |
| Upload says success but count differs | Different filenames, unexpected prefixes, or extra objects. | Compare exact keys, not just totals. |
| A command shows no output | Some commands are quiet when no changes are required. | Check exit status with `echo $?` and verify via `aws s3 ls`. |
| `sync` seems to skip files | Source and destination already compare as synchronized. | Inspect `--dryrun`, paths, filters, sizes and timestamps. |

## 8. Session facts worth retaining

- FloHockey G01 source segments were downloaded locally under `local_artifacts/flohockey/swiss_nl_2026_finals/G01/segments/`.
- Local segment count: **2,004**.
- S3 `.ts` count reported: **2,005** (includes one earlier, differently named segment object).
- Three period MP4s were built locally and verified with `ffprobe`:
  - `G01_P1.mp4`: **1,775,952,575 bytes**, **1734.020 seconds**.
  - `G01_P2.mp4`: **2,188,105,965 bytes**, **2135.924 seconds**.
  - `G01_P3.mp4`: **3,299,308,564 bytes**, **3221.894667 seconds**.
- Each MP4 reports H.264 video, 1920×1080, 25 fps, and AAC audio.
- The period boundaries are recorded in `metadata/period_boundaries.json` and remain pending frame-level validation.
- **The conversation does not yet confirm that the MP4 and metadata S3 uploads finished.** Run the verification commands above.

## 9. Learning checklist

- [ ] Explain bucket, key, object, and prefix.
- [ ] List S3 objects and summarize their sizes.
- [ ] Count only `.ts` files in a listing.
- [ ] Preview a sync with `--dryrun`.
- [ ] Upload three MP4s with an include filter.
- [ ] Verify exact MP4 object count and total bytes.
- [ ] Upload and retrieve the JSON metadata.
- [ ] Explain why `sync --delete` is dangerous.

---

**Maintenance rule:** When we use a new AWS command, append its exact tested form, a plain-English explanation, its safety level, and a verification step to this reference.
