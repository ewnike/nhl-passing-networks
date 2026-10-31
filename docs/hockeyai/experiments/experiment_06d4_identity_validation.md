# Experiment 06D4 — Extended Player Identity Validation

**Project:** NHL Puck Tracking & Passing Networks
**Game:** Swiss National League Finals — G01
**Date:** 2026-10-30
**Status:** Exploratory evaluation complete; additional validation deferred
**Baseline:** Experiment 06D3 — Camera-Cut-Aware BoT-SORT Tracking

---

## 1. Research Objective

Evaluate whether persistent BoT-SORT track identifiers correspond to consistent physical player identities during continuous broadcast footage.

Investigate detection and tracking anomalies identified through human review, including:

- Player identity fragmentation.
- Goalie/player classification instability.
- Occlusion and overlapping detections.
- Potential off-ice false-positive detections.
- Possible missed player detections.

Use these findings to motivate a systematic approach to contextual validation without modifying the original experimental outputs.

## 2. Experimental Data

The investigation used Stage 6D3 tracking outputs from a 30-second G01 broadcast segment recorded at 25 frames per second.

The primary review interval was Segment C, frames 0271–0749, containing 479 consecutive frames.

Source artifacts included:

- Original broadcast frames.
- BoT-SORT annotated frames.
- `track_observations.csv`.
- `tracks.json`.
- `track_summary.csv`.
- Human-reviewed contact sheets.
- Custom track-identity review overlays.

The Stage 6D3 baseline had previously passed local and remote SHA-256 integrity verification.

All Stage 6D4 diagnostics were read-only with respect to the preserved baseline.

## 3. Experimental Method

The investigation combined numerical tracking audits with human visual review.

Track histories were examined using frame indices, object classifications, confidence scores, bounding-box coordinates, and segment-qualified tracking identifiers.

Bounding-box overlap was evaluated using Intersection over Union (IoU).

Human review was used to identify potential discrepancies between numerical track identities and physical players.

The investigation was exploratory and did not establish a complete frame-by-frame ground-truth identity dataset.

## 4. Experimental Findings

### Finding 6D4.1 — Track Coverage Does Not Establish Identity Accuracy

Tracks C:5 and C:8 each contained 479 observations across Segment C, corresponding to 100% numerical coverage.

Initial contact-sheet review found no obvious identity switches in the sampled frames.

However, the review did not establish uninterrupted physical identity continuity between samples.

**Conclusion:** High numerical track coverage is useful but insufficient evidence of persistent physical player identity.

### Finding 6D4.2 — Goalie/Player Classification Instability

Track C:10 contained 465 observations across frames 0271–0749.

Its recorded classifications were:

| Classification | Observations |
|---|---:|
| Goalie | 259 |
| Player | 206 |
| Total | 465 |

Track C:10 had 14 missing observations, including an eight-frame interruption during frames 0560–0567.

Track C:142 first appeared at frame 0566 and contained 174 observations:

| Classification | Observations |
|---|---:|
| Goalie | 168 |
| Player | 6 |
| Total | 174 |

Track C:10 changed from `goalie` to `player` between frames 0568 and 0569.

The evidence establishes classification instability but does not conclusively establish which physical player each track followed throughout the sequence.

### Finding 6D4.3 — Overlapping Tracks During Crease Congestion

Human review of frames 0560–0580 identified substantial player congestion and partial occlusion near the defending goal.

Tracks C:10 and C:142 produced simultaneous observations with substantial bounding-box overlap.

Selected results:

| Frame | C:10 class | C:142 class | IoU |
|---|---|---|---:|
| 0573 | Player | Goalie | 0.867 |
| 0574 | Player | Player | 0.676 |
| 0577 | Player | Goalie | 0.649 |
| 0579 | Player | Goalie | 0.914 |
| 0580 | Player | Goalie | 0.892 |

The maximum measured overlap in the reviewed interval was 0.914.

The observations are consistent with substantial tracking ambiguity during occlusion.

However, bounding-box overlap alone cannot distinguish duplicate detections from two physically overlapping individuals.

### Finding 6D4.4 — Candidate Missed Player Detections

Human review of frame 0371 identified a crowded group of players near the defending goal.

Tracks C:1, C:6, and C:7 appeared within the congested region.

Additional skaters may have been obscured and therefore absent from the tracking observations.

This remains a candidate false-negative detection case.

The number of physically present players and the actual manpower situation were not independently established.

### Finding 6D4.5 — Candidate Off-Ice False-Positive Detection

Track C:138 appeared in frames 0557–0562.

All six observations were classified as `player`.

Detection confidence ranged from 0.191 to 0.416.

Human review suggested that the tracked object was located in the spectator area rather than on the playable ice surface.

The observation motivates a geometric plausibility test using a validated playable-surface boundary.

The suspected false positive remains unconfirmed pending dedicated spatial validation.

### Finding 6D4.6 — Candidate Skater Identity Fragmentation

Human review identified a possible track-ID transition involving a blue-uniformed skater wearing jersey number 6.

The player appeared associated with C:24 in frame 0471 and C:119 in frame 0521.

A possible camera movement toward the offensive blue line was identified as a contributing hypothesis.

The intervening frames have not yet been systematically reviewed.

Therefore, this remains a candidate identity-fragmentation event rather than a confirmed identity switch.

## 5. Key Research Proposition — CAVIF

### Context-Aware Validation and Inference Framework

The experimental findings motivate a proposed **Context-Aware Validation and Inference Framework (CAVIF)**.

CAVIF would combine four complementary components.

**Geometric validation:** Evaluate player detections against validated rink boundaries and spatial calibration.

**Temporal consistency:** Examine tracking histories, occlusions, camera transitions, and possible identity reassignment.

**Hockey-specific context:** Incorporate verified manpower conditions, team affiliation, player visibility, and shift continuity.

**Uncertainty moderation:** Account for camera movement, partial visibility, player interactions, and the limitations of individual contextual signals.

The framework would preserve raw model predictions and initially flag suspicious observations rather than automatically removing them.

CAVIF remains a proposed research architecture. Its effectiveness has not yet been experimentally established.

## 6. Geometric Validation and Spatial Plausibility

The proposed geometric validation layer would combine HockeyRink landmark-based calibration with a validated playable-surface boundary.

Its purpose would be to identify detections that are spatially inconsistent with the playing environment.

Two distinct measurements must be maintained.

**Homography reprojection error** measures the discrepancy between annotated rink landmarks and their positions predicted by an estimated homography.

**Out-of-bounds distance** measures how far an estimated player ice-contact point lies outside the playable rink boundary.

These quantities represent different sources of information and must not be treated interchangeably.

Because a homography is defined on the ice plane, projecting spectators or other off-ice objects onto that plane may produce misleading locations.

A validated image-space playable-surface mask should therefore complement homography-based testing.

Spatial plausibility thresholds must account for calibration uncertainty, boundary annotation uncertainty, and player-location estimation error.

**Initial policy:** Flag geometrically implausible observations for review rather than automatically rejecting them.

## 7. Probabilistic Inference — Proposed Extension

CAVIF may eventually incorporate elementary Markovian probabilistic state estimation.

A Hidden Markov Model or comparable Bayesian approach could combine imperfect observations over time to estimate hidden states such as puck possession or player identity.

The initial implementation may use explicitly documented, manually specified transition probabilities and observation likelihoods.

Such probabilities would represent experimental assumptions until evaluated against human-validated data.

The model should preserve uncertainty when evidence is insufficient to establish a definitive state.

### Hockey-Specific Inference Constraint

Hockey is a high-speed collision sport.

Professional players maintain situational awareness of opponents, teammates, passing lanes, and potential contact.

Consequently, head orientation, body orientation, and skating direction must not be treated as direct indicators of puck possession.

Collective player orientation may provide supporting evidence about the location of developing play, but it requires corroboration from puck trajectory, stick interaction, movement, and temporal evidence.

## 8. Implications for Puck Possession and Passing Networks

Context-aware validation may improve the quality of player candidates supplied to downstream puck-possession and passing-event analysis.

Potential benefits include:

- Flagging off-ice false-positive detections.
- Identifying candidate missed observations during occlusion.
- Supporting reconciliation of fragmented player tracks.
- Reducing the influence of geometrically implausible player candidates.
- Maintaining competing possession hypotheses when the puck is temporarily unobservable.

These benefits remain hypotheses requiring quantitative evaluation.

Improved detection or tracking metrics do not automatically establish improved puck-possession or passing-event accuracy.

## 9. Experimental Limitations

The investigation was restricted to one 30-second broadcast interval.

Human review used selected frames and short sequences rather than complete frame-by-frame identity annotations.

Several suspected errors remain unresolved.

The HockeyRink calibration and playable-surface boundary have not yet been validated for automated spatial rejection.

No probabilistic inference model was implemented.

No improvement in player identification, possession inference, or passing-event accuracy was demonstrated.

## 10. Conclusion and Research Status

Experiment 06D4 demonstrated the importance of distinguishing numerical tracking continuity from physical player identity.

The investigation identified measurable classification instability and substantial bounding-box overlap during crease congestion.

Human review also identified candidate missed detections, off-ice false positives, and identity fragmentation.

These findings provide an experimental rationale for investigating contextual validation.

**The principal research outcome is the proposal of CAVIF: a systematic framework combining geometric, temporal, and hockey-specific evidence with explicit uncertainty moderation and future probabilistic state estimation.**

The framework will be developed incrementally and evaluated against independently reviewed observations.

**Experiment 06D4 status:** Exploratory investigation documented; unresolved cases retained for future validation.

**Part I status:** Ready for synthesis and conclusion.