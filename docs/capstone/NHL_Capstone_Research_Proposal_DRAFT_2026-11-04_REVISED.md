# NHL Puck Tracking & Passing Networks
## Master's Capstone Research Proposal — Working Draft

**Draft date:** 2026-11-04
**Status:** Revised working draft — primary identity architecture selected; not an approved protocol
**Project principle:** One coherent, reproducible data infrastructure supporting multiple controlled experiments.

## 1. Purpose and scope

Develop and evaluate a reproducible computer-vision workflow that identifies hockey players in broadcast footage, detects and annotates passing attempts, and reconstructs descriptive player-level and spatial passing networks. The study uses seven games from a Swiss National League championship series, subject to source availability and usage permissions.

**In scope:** player detection, tracking, appearance re-identification, jersey-number recognition, rink calibration where feasible, puck/possession evidence, passing-event annotation and detection, descriptive passing networks, reproducibility, and model evaluation.

**Out of scope for this capstone:** predicting optimal passing lanes, estimating counterfactual pass-completion probabilities, recommending the best offensive or defensive passing option, and training a graph neural network for passing decisions. Those form a possible follow-on project, not a requirement for completion.

## 2. Research questions and hypotheses

**RQ1 — Player identification:** Can a multi-cue system combining supervised appearance metric learning, jersey-number recognition, and temporal constraints improve identification of teammates compared with an ImageNet-pretrained ResNet-18 cosine-similarity baseline?

**RQ2 — Passing events:** Can broadcast-derived player and puck observations support reproducible identification of passing attempts and their participants, with measurable precision, recall, and timing accuracy against human annotations?

**RQ3 — Networks:** Can verified passing events be transformed into interpretable directed player passing networks and zone-level descriptive summaries with explicit uncertainty and coverage reporting?

Hypotheses will be tested, not presumed true. Unreadable numbers, camera cuts, and off-screen actions may leave identities or events unresolved.

## 3. Existing baseline and current evidence

- Experiment 07D: ImageNet-1K V1 pretrained ResNet-18, 512-dimensional embeddings, cosine similarity; five-image, two-player development smoke test.
- Experiment 07F: preserved appearance-only baseline on 301 verified player crops from 22 identities, acquired over approximately 90 seconds of G01 Period 1. Exploratory track-disjoint evaluation: 16 identities, 163 query images, Top-1 **28.22%**, Top-3 **53.37%**. Temporal holdout: 2 query identities, 16 queries, Top-1 **12.50%**, Top-3 **18.75%**. Same-player mean similarity **0.7808**; different-player same-team **0.7463**; different-team **0.7126**. Results are not independent-game generalization estimates.
- Experiment 07E12: corrected read-only audit reported **440 verified identity observations**, **8 candidates**, **41 of 44 roster identities verified**, **zero normalization issues**, and **zero duplicate keys within its namespace-aware definition**. The 440 observations are **not** 440 player crops; the existing verified crop inventory is **301**. Legacy segment-local frame references require care before cross-stage deduplication.
- Outstanding roster evidence: HCD #88 Tim Minder; FRI #1 Loic Galley and #37 Kevin Nicolet have candidate/bench evidence requiring further review. Do not delay baseline modeling solely to reach complete roster coverage.
- Original 07D and 07F artifacts are immutable reference baselines. Maintain correction and reconciliation manifests rather than silently changing earlier CSVs.

## 4. Primary experimental architecture — decision recorded 2026-11-04

**Decision:** Use **YOLO-family player detection (existing HockeyAI implementation) + a separately trained, triplet-loss player Re-ID model** as the primary identity architecture. **Jersey-number recognition and temporal tracking provide complementary identity evidence**, not replacements for Re-ID. Retain the frozen 07F ImageNet ResNet-18/cosine-similarity result as the comparator. This is an architecture commitment, **not** a claim that triplet training or the integrated pipeline has already been implemented or validated.

**Processing flow:** Broadcast frames → YOLO/HockeyAI skater detections → BoT-SORT tracklets → player crops → supervised ResNet-18 identity embeddings trained with triplet loss → cosine-similarity identity candidates → jersey-number/nameplate evidence + verified identity anchors → constrained temporal tracklet association → identity with confidence or abstention → puck/possession and passing-event pipeline → descriptive passing networks.

**Why separate detection and Re-ID:** YOLO learns where skaters are; triplet loss trains the embedding network to distinguish *which* skater appears in a crop. Do not assume triplet loss is applied to YOLO itself. Train/evaluate the detector and Re-ID separately first; consider joint training only if measured results justify the complexity.

**Training protocol:** Use verified SIHF-linked identity labels; select anchor/positive pairs from different, non-overlapping sequences where possible; condition hard negatives on **same team** and similar viewpoint/quality, while retaining a mix of easier negatives. Maintain disjoint training, validation, and test sequences/games; avoid near-duplicate leakage. Include classification-loss ablation if feasible and report per-team, per-player, and tracklet-level metrics. Never use candidate labels as unquestioned training ground truth.

**Evidence fusion:** Use jersey-number recognition when digits are visible; benchmark original versus CLAHE/denoising/best-frame selection, and treat OCR outputs as predictions until independently verified. BoT-SORT establishes continuity within tracklets. Clamp only genuinely verified identity anchors and apply roster/one-player-per-track constraints; do not propagate identity across uncertain cuts without an association score. Start with constrained assignment; evaluate Markov/HMM formulations only if simpler inference is insufficient.

**Controlled model comparisons:** (A) frozen 07F pretrained ResNet-18 + cosine; (B) supervised triplet-trained ResNet-18 + cosine; (C) B plus jersey-number evidence; (D) C plus temporal association. OSNet is a secondary Re-ID backbone comparison. Self-supervised adaptation, autoencoders, manifold learning, and walk-back training remain optional investigations, not capstone prerequisites.

**Acceptance evidence:** runnable code, frozen data splits, model/configuration hashes, quantitative Top-1/Top-3 and within-team results, confidence/abstention behavior, tracklet-level evaluation, and error analysis on held-out material. Improvements are hypotheses to test, not promised outcomes.

### 4.1 Supporting components and integration

**Video → YOLO/HockeyAI detection → BoT-SORT tracklets → triplet-trained Re-ID embeddings and cosine candidate ranking → complementary jersey-number evidence → constrained temporal identity fusion → puck/possession evidence → pass-event detection → descriptive passing networks (NetworkX).**

Rink calibration (HockeyRink landmarks + OpenCV homography) supplies physical coordinates only when reprojection and stability checks pass. Otherwise retain image coordinates and mark rink coordinates unavailable.

### 4.2 Appearance and identity research

1. Preserve ResNet-18 + cosine similarity as baseline.
2. Test controlled image enhancement for low-contrast Fribourg grey jerseys (e.g., CLAHE, sharpening, multi-frame best-view selection). Evaluate against original images; never treat generated digits as verified evidence.
3. Fine-tune ResNet-18 with **supervised metric learning**, including triplet loss and **conditional hard-negative sampling** among visually similar teammates. Select positives across genuinely distinct shifts/tracklets when available.
4. Evaluate OSNet as an optional specialized Re-ID comparison only after a valid baseline and held-out split exist.
5. Combine direct number evidence, appearance scores, roster constraints, and tracking continuity. **Clamp** high-confidence human-verified identity anchors; propagate identity only through defensible continuity. Start with constrained tracklet association; consider HMM/Markov inference only if it adds measured value.
6. Self-supervised hockey adaptation, autoencoders, manifold visualization, and walk-back training are **optional research extensions**, not prerequisites or promised deliverables. Reconstruction quality is not proof of identity accuracy.

## 5. Step 2 — Reproducible player-identity data acquisition

**Target:** approximately **1,255 verified player-specific appearance crops per game** across seven games (about **8,785**, commonly rounded to **8,800**). This is a planning target, not a substitute for quality or independence. Report the actual number achieved and per-player, per-game, per-track distributions.

**Primary platform:** Voxel51 FiftyOne for visual review, dataset curation, filtering, and evaluation. Test native video annotation capabilities before assuming it supports every desired event-tagging interaction. A small companion UI may be necessary for rapid pass entry.

**Reusable operator pipeline (teammate handoff):**

1. Select game/period and validate video metadata and source SHA-256.
2. Import official SIHF lineup, jersey numbers, player IDs, TOI, goals, and penalties using fastRhockey; create event-based review suggestions, without claiming shift-level timestamps where unavailable.
3. Run detection/tracking; generate candidate player crops and tracklet contact sheets.
4. Review candidates in FiftyOne; label verified/candidate/rejected and evidence type (number, nameplate, continuity, roster-context). Keep bench-only observations distinct from gameplay.
5. Extract and register crops with source game, period, source-frame index, segment-local index if applicable, source timestamp, track ID, player ID, bounding box, reviewer, quality flags, and evidence SHA-256.
6. Validate schema, official roster IDs, duplicate identity/frame keys, image availability, and track/sequence independence; write append-only manifests and summary reports.
7. Sync approved artifacts to AWS S3 with post-upload checksum/inventory verification; grant teammates least-privilege access limited to appropriate prefixes and actions.

Convert existing heredoc utilities into reusable Python modules/CLI commands; **reuse functioning code**, do not rewrite it unnecessarily. Pilot end-to-end on G02 before scaling to G03–G07. Provide a teammate operating guide with a short practice exercise and troubleshooting notes.

### Shared identity record (minimum)

`game_id, period, source_video_id, source_frame_index, segment_id, segment_frame_index, video_time_seconds, track_uid, team_id, sihf_player_id, jersey_number, bbox_xyxy, crop_path, identity_status, evidence_type, reviewer, source_sha256, crop_sha256, split_group_id`

Use nullable fields rather than inventing values. Distinguish source frames, player observations, player-specific crops, and independent tracklets in every report.

## 6. Passing-event annotation and detection

Parallel workstream: primary researcher reviews game footage and annotates attempted passes, receptions, failed attempts, interceptions, clearances, shots, carries, and possession changes. Record event start/end frames, participants when identifiable, puck start/end image coordinates, optional calibrated rink coordinates, game state, and uncertainty. Preserve negative examples and ambiguous events.

Test FiftyOne on the already-reviewed G01 P2 Sprunger-to-Walser pass/shot sequence. If native tagging is cumbersome, use a keyboard-driven event logger exporting a schema FiftyOne can inspect. Do not require complete annotation of all seven games before running an initial detector; iteratively pilot, evaluate, correct, and expand. The seven-game annotation campaign remains the intended dataset collection effort.

**Minimum passing event record:** `game_id, period, start_frame, end_frame, event_type, passer_id, receiver_id, outcome, puck_start_px, puck_end_px, puck_start_rink, puck_end_rink, source_video_id, review_status, reviewer, confidence`.

Start with transparent rule-based event proposals and evaluate against human annotations. Add supervised temporal event classification only when the labeled sample and evaluation design justify it. Report precision, recall, F1, timing tolerance/error, and identifiable-participant coverage.

## 7. Descriptive network analysis

Construct directed player graphs from human-verified and/or confidence-filtered detected passes. Report edge counts, completion rates, centrality, and offensive/defensive-zone summaries. Explicitly identify missing or off-screen events and do not interpret unobserved passes as absent. Spatial coordinates are conditional on successful rink calibration.

**Deferred follow-on project:** estimate available lanes, counterfactual pass-success probabilities, and optimal passing decisions from spatial graphs and defenders' trajectories. Those tasks require labels for unattempted alternatives and stronger spatial coverage and are excluded from this capstone's definition of done.

## 8. Experimental design and evaluation integrity

- Freeze 07D and 07F outputs; version new experiments and keep code/configuration hashes.
- Avoid random frame-level train/test splits that place adjacent frames or overlapping tracklets on both sides.
- Use track/sequence-separated evaluations for development, and game-level held-out evaluation when identity coverage permits; distinguish closed-set recognition from unseen-identity Re-ID.
- Report image-weighted and tracklet-weighted accuracy, per-team results, Top-1/Top-3, confusion matrices, and uncertainty/coverage.
- Never promote candidates or OCR guesses to verified ground truth without independent review.
- Record dataset composition and exclusions alongside all accuracy claims.
- Preserve video rights and access controls; do not assume sharing permissions.

## 9. Division of labor

**Teammate:** acquire/validate G02–G07 footage and official metadata; operate the FiftyOne-assisted identity workflow; collect and register verified player crops; produce per-game QA reports.

**Primary researcher:** establish experiments and evaluation protocol; review passing attempts and possession events; assess jersey-number recognition; develop passing-event and descriptive-network analyses; integrate and validate teammate output.

**Shared:** review QA exceptions, protect the held-out evaluation data, maintain reproducible manifests and documentation.

## 10. Definition of Done — THIS CAPSTONE

The capstone is **done** when the following deliverables are produced and their limitations are explicitly documented:

1. **Reproducible data foundation:** seven-game source inventory (or documented acquisition limitations), official roster/event mapping, standardized schemas, provenance/checksums, and a working teammate-operable FiftyOne-assisted identity collection workflow demonstrated on at least one game beyond G01.
2. **Identity research:** preserved 07D/07F baselines; a controlled triplet-trained Re-ID experiment and a jersey-number/temporal-fusion ablation where data permit; quantitative comparisons with leakage-aware splits and error analysis; ability to output player IDs **or abstain** with confidence and provenance.
3. **Passing ground truth:** a documented, reproducible annotation protocol and a verified event dataset covering the selected evaluation material; progress and coverage across all seven games reported transparently. Full seven-game labeling is an acquisition goal, not grounds to misrepresent unreviewed events.
4. **Pass recognition prototype:** an executable pipeline that outputs candidate passing events with timestamps, outcomes where observable, and player associations where supportable; measured precision/recall and timing error against held-out human annotations.
5. **Descriptive passing networks:** reproducible directed player passing graphs and at least one game/zone analysis, including uncertainty and missing-data discussion.
6. **Research handoff:** scripts, configuration, installation/runbook, experiment registry, data dictionary, QA report, and capstone write-up sufficient for another team member to reproduce the reported results.

**Not required for Done:** perfect player recognition, identification of every bench player, 100% pass detection, full-ice coordinates on every frame, predictive passing-lane probabilities, optimal-pass recommendations, graph neural networks, autoencoder walk-back training, or a production-grade real-time system.

**Data quantity guardrail:** the 8,800-crop and seven-game passing-annotation targets guide collection and should be tracked, but model quality, reproducibility, honest coverage, and evaluated outputs determine scientific completion. Any shortfall is reported explicitly, not hidden.

## 11. Immediate sequence and schedule

1. Preserve 07F and 440-observation checkpoint.
2. Run grey-jersey enhancement/number-recognition pilot (07G), with controlled original-versus-enhanced comparisons.
3. Complete LSEG deliverable before further large engineering tasks.
4. Inventory and refactor existing heredoc scripts into a reusable collection CLI; prototype FiftyOne identity review.
5. Download and checksum remaining championship games to S3 with controlled access; test workflow on G02 and hand off G03–G07.
6. In parallel, begin structured passing-event annotation and evaluation on G01; expand to other games.
7. Train and compare supervised triplet-loss Re-ID against 07F only after robust train/evaluation separation; add constrained temporal identity inference as evidence supports.

## 12. Non-negotiable design principle

> **Build one coherent data infrastructure supporting multiple experiments, not separate image collections for each model.**

Every verified crop must be reusable for supervised Re-ID, jersey-number recognition, temporal identity evaluation, and future models. Every passing-event annotation must be reusable for detection evaluation and descriptive network construction. Source videos, frame indices, official IDs, reviewer decisions, crop geometry, checksums, and dataset splits form the common contract. Human annotation should generate reusable evidence, not one-off screenshots.

## 13. Open decisions and next revision

- Verify the installed FiftyOne version and exact native video-labeling capabilities.
- Confirm game acquisition rights, source availability, S3 prefix plan, and IAM policy with least privilege.
- Define concrete acceptance thresholds for recognition and passing detection after a G02 pilot and review of class/event prevalence; do not invent accuracy targets retroactively.
- Confirm the temporal synchronization between SIHF clock and broadcast files.
- Agree on the evaluation sample and held-out game/sequence policy before further training.
- Keep the predictive passing-lane project in a separate proposal.
