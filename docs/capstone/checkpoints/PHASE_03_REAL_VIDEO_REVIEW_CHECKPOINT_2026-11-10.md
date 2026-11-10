# Phase 03 — Real-Video FiftyOne Review Checkpoint

**Date:** 2026-11-10
**Project:** NHL Puck Tracking & Passing Networks
**Status:** REAL-VIDEO PILOT OPERATIONAL; TEAMMATE DEPLOYMENT NOT YET APPROVED
**Last verified checkpoint:** 50 — duplicate-review eligibility PASS

## 1. Objective

Deploy an existing, protected FiftyOne player-identity review workflow on actual Swiss National League 2026 Finals G01 footage, without rebuilding historical observations or overwriting prior datasets. Prepare for a small teammate pilot: Scott (`SF_Dye`, HC Davos) and Zach (`Z_Snow`, Fribourg-Gottéron).

## 2. Completed and Verified — November 10

### EC2 and FiftyOne

- Instance: `i-09e172f552324c138` (`nhl-fiftyone-review-workstation`).
- AWS region: `us-east-2`; bucket: `ewnike-nhl-passing-networks-2026`.
- Existing EC2 instance role: `nhl-fiftyone-ec2-role`. The instance role governs AWS access; local Linux ownership is separate.
- FiftyOne version from earlier environment checkpoint: 1.8.1 (not independently rechecked today).
- Service: `nhl-fiftyone.service`, runs as `ssm-user`, bound to `127.0.0.1:5151`.
- After controlled restart, `ActiveState=active`, `SubState=running`, `MainPID=32882`, `NRestarts=0` at check time.
- Local `curl http://127.0.0.1:5151/` returned HTTP 200.
- Existing Tailscale HTTPS browser endpoint: `https://ip-172-31-5-31.tail892ff1.ts.net`. A transient HTTP 502 after service restart cleared; real video subsequently loaded in browser.
- Systemd drop-in created: `/etc/systemd/system/nhl-fiftyone.service.d/10-g01-real-video.conf`; `daemon-reload` and service restart completed. Original unit retained. Effective `ExecStart`:
  `/opt/nhl-fiftyone/venv/bin/fiftyone app launch swiss_nl_g01_player_review_workstation_v1 --address 127.0.0.1 --port 5151 --remote --wait -1`.

### Original data preserved and source media

- Four persistent datasets existed before today's new integration:
  - `nhl_phase03_atomic_review_test_v1` — 1 synthetic video sample.
  - `nhl_phase03_security_bypass_test_v1` — 1 synthetic video sample.
  - `nhl_phase03_team_review_test_v1` — 1 synthetic video sample.
  - `swiss_nl_g01_identity_review_consolidated_ec2_restored_v1` — **1,325 image observations**.
- Restored dataset's 07E5 subset: **330 observations**, comprising **124 historically verified** and **206 unverified**; **261 distinct annotated frames**.
- All 330 07E5 FiftyOne `sample.filepath` images accessible at `/opt/nhl-fiftyone/migrations/phase_02_g01_consolidated_v1/import_ready/images/`. Historical `source_image` fields still reference original Mac paths and were not rewritten.
- G01 P1 S3 source: `raw/flohockey/game_001/periods/G01_P1.mp4`; `head_object` size **1,775,952,575 bytes**. Downloaded using boto3 to `/opt/nhl-fiftyone/media/g01/G01_P1.mp4`; local size matched.
- Full period video: **1920×1080**, **25 FPS**, **43,350 frames**, **1,734 seconds**; local SHA-256 `43e3aebdb59647f62991162fb7ffcf2d3b52ec8335dbfaa774afc79d146af528`. This local hash was recorded but not independently compared to an S3 source checksum.
- `ssm-user` initially lacked write permission in root-owned `/opt/nhl-fiftyone/media`. Corrected by creating only `/opt/nhl-fiftyone/media/g01` owned by `ssm-user`; parent ownership unchanged.
- Extracted 30-second pilot at source seconds **330–360** to `/opt/nhl-fiftyone/media/g01/G01_P1_330_360.mp4` using FFmpeg H.264 (`libx264`, preset medium, CRF 18, `yuv420p`, no audio, faststart, no-overwrite).
- Pilot clip: **33,900,264 bytes**, **1920×1080**, **25 FPS**, **750 frames**, **30 seconds**; SHA-256 `81b221cb46a3fc5a049f2970da36832762e1ff8c57ec7ea20ed4cce681d295cd`.
- Original November 7 07E5 integrated clip SHA-256: `4ac8237557aded0e1c7131f24582690b20469c52ee3114d97fa650a90acaceb7`. **Hashes do not match.** Do not replace or erase this distinction.
- Representative player-crop-to-video comparisons at source frames **0, 141, 282, 422, 561, 699** yielded mean absolute pixel differences **2.2872, 2.5737, 2.4530, 2.5722, 3.4307, 2.7946** (aggregate mean **2.6852**, maximum of six **3.4307**). These support alignment at six sampled locations; they do **not** prove exhaustive frame equivalence.

### Roster and production review plugin

- Roster file: `/opt/nhl-fiftyone/repository/data/sihf/swiss_nl_2026_finals_game_rosters_v1.csv`.
- G01 game ID `20261105000415`; **44 unique dressed players**, **22 per team** (team IDs `101151` and `103138`). This is **G01-only**, not the seven-game series total.
- Production plugin path: `/opt/nhl-fiftyone/repository/plugins/fiftyone_player_identity_review/`.
- Production plugin hardcoded dataset: `swiss_nl_g01_player_review_workstation_v1`.
- Approved manually entered reviewer IDs: `E_Wnike`, `SF_Dye`, `Z_Snow`.
- Protected operator requires exactly one selected video detection and `review_status='pending'`; validates roster ID and conflicting historical verified identity; atomic conditional MongoDB update locks the initial review and sets `training_approved=False`.

### New real-video review dataset — created and validated

- Construction script (outside Git repo): `/home/ssm-user/create_g01_real_video_review_v1.py` — **11,135 bytes**, **364 lines**, syntax PASS; executed successfully after preflight.
- New persistent FiftyOne dataset: **`swiss_nl_g01_player_review_workstation_v1`**.
- Post-import audit: **1 video sample**, **261 annotated frames**, **330 detections**, **124 historically verified**, **206 historically unverified**, **10 identity-conflicted detections**, **330 initially pending teammate reviews**, **0 training-approved**.
- Original identity fields retained independently from new review fields (`review_status`, `reviewer_id`, `reviewed_player_id`, `review_notes`, `review_submitted_at`, `training_approved`).
- Known conflicting track `E4_A:55`: historically verified SIHF IDs **121606** (Julien Sprunger) and **152416** (Sven Jung); preserve conflict, do not propagate identity across track.
- FiftyOne dataset load verified: persistent video dataset; video path correct; annotated frame numbers span **1–750** (FiftyOne one-based numbering).
- Browser confirmed real G01 footage with spatially aligned bounding boxes; selected real player detection; production protected-review form opened and displayed existing identity safety warning.

### First real-video protected submission — PASS

- Detection: **Lukas Frick #38**, HCD, historical SIHF ID **153736**, track **`E4_A:27`**, FiftyOne **frame 116**.
- Submitted through production `NHL: Submit Protected Review` operator as reviewer **`E_Wnike`**, decision **verified**, reviewed SIHF ID **153736**.
- Browser displayed **REVIEW SAVED** and initial review lock notice.
- Independent reload/database audit confirmed:
  - `identity_status=verified`; `verified_player_id=153736` (historical identity preserved).
  - `review_status=verified`; `reviewer_id=E_Wnike`; `reviewed_player_id=153736`.
  - `review_notes=Phase 03 real-video pilot validation — historical identity confirmed.`
  - `review_submitted_at=2026-11-10 18:31:12.909000` (database timestamp; UTC convention in submission code).
  - `training_approved=False`.
- Follow-up read-only eligibility test: `review_status=verified`, **not pending**, so **not eligible for another initial review**. This was **not** a live duplicate submission attempt on real footage; earlier synthetic operator tests separately confirmed duplicate rejection.
- Thus the new dataset now has **329 pending** and **1 newly reviewed**, assuming no other changes after the audit; recheck before quoting as live state.

## 3. Problems Encountered and Resolutions

1. **Local permission error:** root-owned media directory prevented `ssm-user` from creating `g01`; fixed by creating dedicated owned subdirectory, without broad `chown`.
2. **Original clip SHA mismatch:** new clip differs byte-for-byte from November 7 source. Six spatial crop comparisons support representative alignment; discrepancy documented, not bypassed or declared identical.
3. **Historical source-image paths invalid on EC2:** restored sample `filepath` locations are accessible for all 330 07E5 observations; provenance fields left intact.
4. **Systemd drop-in initially absent from `systemctl cat`:** fixed with `sudo systemctl daemon-reload`, then verified and restarted service.
5. **Transient Tailscale 502 after restart:** localhost returned HTTP 200; refreshing browser restored app access.
6. **Session Manager terminal temporarily unresponsive during large paste:** refresh/reconnect; script confirmed on disk, AST syntax PASS.

## 4. Outstanding / Not Yet Proven

- **SEC-001 remains open:** earlier testing proved that general-purpose FiftyOne Python/database write access can bypass the custom protected operator. Built-in FiftyOne operators cannot simply be assumed disabled. Tailscale limits network reachability but is **not** sufficient proof of annotation-write authorization.
- **Reviewer attribution is not authenticated:** `reviewer_id` is manually typed, so browser users could impersonate another reviewer. Need identity-bound access and verified permission boundaries before teammate invitation.
- **Teammate access:** Scott and Zach not yet verified on tailnet or invited; no end-to-end teammate-specific access test.
- **Assignments:** 07E5 verified team split **78 HCD**, **46 FRI**, **206 unverified/team unknown**. These are observation counts, not unique players. Unknown-team observations must not be automatically assigned from tracking IDs.
- **Pilot quality:** only six frame/crop comparisons; not exhaustive frame alignment or full detection accuracy. No separate independent media checksum match to original November 7 clip.
- **Production plugin robustness:** earlier synthetic test plugin required optional-field `getattr` fixes; production plugin still contains `get_field()` calls. Real matching-identity submission succeeded, but other optional-field paths require testing.
- **Export/backup:** Git scripts/checkpoint do not back up MongoDB. No validated S3 export of today's new review dataset is recorded.
- **Training:** zero observations training-approved. Triplet-loss Re-ID training is a separate future pipeline; no new model training occurred today.
- **Daily checkpoint Git commit:** not yet made by this file's creation alone.

## 5. Exact Next Action / Resume Instructions

**First preserve this checkpoint in Git before any further infrastructure changes.** Suggested repository path:

`docs/capstone/checkpoints/PHASE_03_REAL_VIDEO_REVIEW_CHECKPOINT_2026-11-10.md`

Verify its content and `git status`, stage **only this checkpoint file**, then commit. Do not blanket-stage the repository. Update `START_HERE`/master context references in a separate deliberate edit if desired.

After checkpoint preservation, plan and test **SEC-001 remediation and authenticated reviewer attribution** before inviting Scott and Zach. Preserve full FiftyOne video browsing and protected submission behavior; test actual alternative write paths rather than assuming a proxy solves them. Then prepare a small, balanced HCD/FRI pilot and written instructions. Do not restart/rebuild footage, recreate the restored observations, or rerun the dataset construction script (target already exists).

### Immediate state to remember

- FiftyOne browser currently configured to launch `swiss_nl_g01_player_review_workstation_v1`.
- The dataset is **already created** and has one verified new teammate-review record (Lukas Frick frame 116).
- The original 1,325-observation source dataset and three synthetic test datasets remain separate.
- The systemd override is already active; do not create a second competing override.
- The original 07E5 SHA mismatch is documented and the new clip hash is recorded separately.

## 6. Reference Files / Historical Checkpoint

- `docs/capstone/checkpoints/PHASE_02_FIFTYONE_INTEGRATION_2026-11-07.md` — original 07E5 dataset and visual validation.
- `scripts/hockeyai/create_g01_fiftyone_video_identity_07e5_v1.py` — original integration logic, not altered today.
- `scripts/hockeyai/create_g01_fiftyone_video_pilot.py` — original FFmpeg clip extraction procedure.
- `plugins/fiftyone_player_identity_review/__init__.py` and `atomic_submission.py` — production operator and atomic submission logic.
- `/home/ssm-user/create_g01_real_video_review_v1.py` — today's EC2-only construction script; **not yet version-controlled**. Preserve/review this script separately before future changes.

**Evidence standard:** PASS refers to specific terminal/browser checks listed above. Historical statuses, current observations, proposed next steps, and unverified security claims are intentionally distinguished.
