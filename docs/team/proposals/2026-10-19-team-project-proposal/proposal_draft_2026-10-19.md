# NHL Puck Tracking & Passing Networks
## SIADS 699 — Team Project Proposal (Working Draft)

**Status:** Draft for team rewrite and review; **not submitted**  
**Team planning meeting:** Friday, October 16, 2026  
**Canvas deadline:** Monday, October 19, 2026, **11:59 p.m.**  
**Final capstone deadline:** Monday, December 14, 2026, **11:59 p.m.**  
**Proposal lead / Canvas submitter:** **[Assign one teammate at the October 16 meeting]**  
**Teammates and contributions:** **[Insert names and roles]**  
**Required format / length / rubric:** **[Proposal lead must verify the Canvas assignment instructions]**

> **Editing note:** This draft consolidates the team's existing GitHub README, October 16 meeting brief, meeting goals, and preliminary technical experiments. It is a starting point for the designated proposal lead, not an instructor-approved or independently reviewed final submission.

### 1. Research question and motivation

**Primary question:** Can player and spatial passing-network structure help characterize how hockey teams create and maintain puck possession, and does network structure reveal patterns that conventional event summaries and possession measures, such as Corsi, may miss?

A hockey possession is not a single independent event: it can include a puck recovery, breakout, neutral-zone transition, zone entry, and several passes before a shot attempt. A directed network representation preserves relationships among the players and rink locations involved in these sequences. Our immediate emphasis is on **descriptive structure and testable associations**, not causal claims about centrality or player value.

We propose a modular design in which structured pass-event data and future validated video-derived pass events conform to a shared schema. This allows core network research to proceed even if broadcast-video puck tracking remains unresolved.

### 2. Available data and scope

**Core analytical source — Stathletes Big Data Cup.** We have event data for selected games, including passing-related records with anonymized player and team identifiers. An existing repository script, `stathletes_event_info.py`, reads an example event CSV, selects records labeled `Play` and `Incomplete Play`, extracts candidate passer/target IDs, source and destination coordinates, and context, and aggregates completed-event directed edges. Before claiming a validated dataset or network, the assigned data owner will audit available game files, exact field definitions, event labels, missingness, game/period clocks, stable identifier scopes, venue geometry, coordinate units, data-use permissions, and whether target and receiver semantics differ for unsuccessful attempts.

**Experimental source — broadcast hockey video.** Existing project experiments include HockeyAI player detection, BoT-SORT player tracking, on-ice player-position filtering, a HockeyRink 56-landmark geometry dictionary, homography/RANSAC diagnostics, and manual landmark review. The current HockeyRink project convention uses a 60 m × 30 m IIHF-style rink, center ice `(0, 0)`, longitudinal X from −30 m to +30 m, and lateral Y from −15 m to +15 m. Vendor event coordinates, vendor tracking coordinates, and NHL-sized physical rinks may use **different dimensions, origins, units, and orientation conventions**. We will not merge or compare physical locations until transformations have been independently checked.

**Identity limitation.** The anonymized Big Data Cup players and teams are not assumed to correspond to named historical NHL players or unrelated video tracks. The initial integration goal is compatible data processing, **not** an identity-level join across different games or sources. Historical player/Corsi analysis is conditional on an appropriate identity-linked dataset becoming available.

### 3. Proposed methods and shared architecture

**Workstream A — Stathletes ingestion and passing networks (core deliverable).**

1. Inventory source event files and document data provenance, missing values, and event semantics.
2. Normalize a versioned event table while retaining original source identifiers and native coordinates.
3. Build **directed, weighted player passing graphs** using verified completed pass events. Investigate edge counts, in-/out-degree, weighted degree, betweenness, reciprocity, and context-sensitive networks, choosing measures that remain interpretable given dataset size.
4. Where coordinate validity permits, construct **spatial transition networks** between defined rink regions and examine passing distance, direction and zone transitions.
5. Produce reproducible graphs, tables, visualizations, and a cautious discussion of observed patterns and limitations. Compare results across available teams, periods, strength states, or games only when the data supports the comparison.

**Workstream B — Computer vision, rink calibration, and visual QA (experimental).**

1. Document correspondence definitions, landmark coverage, revised project geometry, and differences between historical and updated homography experiments.
2. Assess calibration using inlier/outlier residuals, spatial spread, controlled perturbations, and independently reviewed or held-out image landmarks. A successful fitted matrix or low inlier residual is not by itself proof of physically accurate projection.
3. Inspect HockeyAI/BoT-SORT player tracks and the quality of candidate rink positions.
4. Use Voxel51 **FiftyOne** as a visual QA environment to inspect original observations, historical model projections, provisional review flags, and proposed corrections. Preserve source annotations unchanged.
5. If feasible, manually verify a small number of pass events from video and export these with clear provenance and confidence/verification status. We do **not** currently claim automatic completed-pass recognition.

**The integration contract.** Both workstreams will map to a documented, versioned passing-event interface. Candidate fields include:

| Group | Fields / required decisions |
|---|---|
| Provenance | `source`, `source_file`, `source_event_id`, `verification_status`, optional model/run version |
| Event/time | `game_id`, `period`, `event_time_s`, `event_sequence`; explicitly document whether source clocks count up or down |
| Participants | Source-scoped `team_id`, `passer_id`, `target_id`, optionally `receiver_id`; do not confuse an intended target with a confirmed receiver |
| Outcome | `pass_complete`, `pass_type` when supported, optional uncertainty/confidence |
| Space | Original `pass_start_x/y` and `pass_end_x/y`; separately transformed locations if and only if validated |
| Geometry | `rink_profile_id`, `coordinate_system`, units, axes/origin, orientation reference, transformation version, coordinate-validation status |
| Context | Strength state, score state or possession ID where source evidence permits |

Two records conforming to the same contract can be analyzed by the same code while still representing different games, leagues, and rink profiles. Unit conversion is not the same as rink-relative normalization; real physical distances are necessary for speed and reachability models.

**Proposed future extensions, not promised core outputs:** Voronoi spatial dominance, movement-aware reachability, probabilistic puck-location inference, and trained event-recognition models. The feasibility of these methods depends on validated player positions, suitable observations, and available time.

### 4. Work completed before the proposal

The repository contains an initial Big Data Cup pass-event extraction/edge-aggregation script and computer-vision research artifacts. One concrete quality-assurance demonstration has been performed with FiftyOne 1.8.1:

- A persistent two-frame HockeyRink audit dataset was created with **34 source landmark annotations**, **9 review entries**, and distinct layers for original annotations, saved projections, review flags and proposed relabels.
- In a western broadcast frame, original source annotation **KP-02** had a saved reprojection residual of **351.084 px** and was excluded from that saved RANSAC inlier set. Visual review suggested that the feature could instead represent physical KP-03.
- The persisted FiftyOne dataset was queried directly: original `KP-02` and proposed `KP-03` both occupied normalized coordinates `(0.223110, 0.078811)`, or `(428.3712, 85.11588)` pixels in a 1920 × 1080 image. **Measured displacement = 0.000000000 px**.
- **Interpretation:** This validates that the proposal changes the keypoint **identity hypothesis**, not its image position. It does **not** establish that KP-03 is the true physical landmark. Original source labels remain unchanged.

The landmark dictionary also contains a locally revised **project-derived** convention for 16 faceoff hash-mark positions, distinct from the source annotation definitions and older experiment results. These findings motivate robust annotation QA rather than claims that calibration is already solved.

### 5. Evaluation plan and success criteria

**Data integrity:** Verify source file coverage, row uniqueness where appropriate, missing/unknown identities, valid event categories, event ordering, coordinate conventions, and stable identifier scopes. Preserve source columns and provide clear mapping/validation reports.

**Network correctness:** For a testable subset, reconcile graph edge weights to the verified completed-event table; demonstrate that graph construction is reproducible and that statistics are interpreted within the limits of sample size and anonymity. Include basic descriptive baselines and, where appropriate, comparisons across available game contexts.

**Spatial validity:** Check transformations against documented rink dimensions and verified reference locations. Keep native and transformed coordinates distinct. Any visual puck-motion or zone claim must declare the relevant rink profile.

**Computer-vision QA:** Keep source annotations, proposed edits and human-review decisions separate. Report full residual distributions and held-out checks—not just RANSAC inlier means. Store traceable failure cases for independent review.

**Minimum viable deliverable by December 14:** A documented and reproducible passing-event ETL, a directed player passing network built from verified events, at least one interpretable quantitative network analysis and visualization, spatial analysis if coordinate quality supports it, and a report describing evidence, reproducibility, limitations, and the parallel computer-vision feasibility findings.

**Contingency:** If vendor-to-video integration or full rink calibration cannot be validated, submit the completed structured-data/network work and a defensible CV QA/feasibility report rather than inventing pass coordinates or model performance.

### 6. Tools and reproducibility

The initial toolkit includes Python, pandas/NumPy for ingestion and transformation, **NetworkX** for graph analysis, Git/GitHub for version control, and HockeyAI/BoT-SORT/OpenCV for the experimental video pipeline. **FiftyOne (Voxel51)** will support visual inspection of images, labels, errors, and human-review metadata. Each tool's purpose, environment/version, installation steps, and limitations will be documented in the October 26 Software Tools deliverable. Repository source artifacts should be versioned; local FiftyOne database state and raw footage require a documented reproducibility/data-access strategy rather than assumptions that GitHub contains them.

### 7. Research risks and mitigations

| Risk | Mitigation |
|---|---|
| Limited selected-game coverage or anonymized IDs | Scope claims to available games; validate identity stability; do not make unsupported NHL player/Corsi joins |
| Vendor and CV coordinates differ | Record rink profile, native units/axes/orientation and transform status; verify before spatial comparisons |
| Broadcast occlusion and annotation errors | Preserve source evidence; use FiftyOne human review and independent validation; leave unknown positions unknown |
| End-to-end CV event recognition remains unreliable | Make event-data network analysis the core deliverable; present CV as parallel research with measurable findings |
| Scope expands beyond capstone schedule | Time-box extensions, assign owners, review status weekly, and freeze major analytical changes before final submission |
| Data permissions and reproducibility | Confirm use/distribution constraints; document sources without redistributing restricted materials |

### 8. Team ownership and schedule

**At the October 16 team meeting, designate one accountable proposal lead and Canvas submitter.** Other teammates contribute their sections and review for accuracy. The lead verifies assignment requirements, consolidates the draft, records team sign-off, and **personally confirms submission in Canvas** by the official deadline. A separate backup submitter should be selected only if course rules permit it.

| Official due date | Course assignment | Internal project Done-When (proposed) |
|---|---|---|
| **Oct 19** | **Team Project Proposal** | Proposal lead verifies rubric, integrates input, obtains review and submits by 11:59 p.m. |
| **Oct 26** | Software Tools Mini-Deliverable | Stathletes/FiftyOne tooling, source inventories, environment and shared-schema plan documented |
| **Nov 2** | Evaluation Plan Mini-Deliverable; 1st Slack stand-up video | Integrity checks, network measures, geometry/CV verification criteria and evaluation protocol established |
| **Nov 9** | Report Outline; 1st stand-up responses; mentor scheduling reminder | First network prototype and outline documented; mentor check-in scheduled |
| **Nov 16** | Visuals Mini-Deliverable; 2nd stand-up video | Passing-network figures and validated CV/QA example prepared |
| **Nov 23** | Revised Outline; 2nd stand-up responses | Findings, methods, limitations and references integrated |
| **Nov 30** | GitHub Repository; Mentor Check-In; 3rd stand-up video | Reproducibility materials and mentor feedback recorded |
| **Dec 7** | Pre-Flight Checklist; 3rd stand-up responses | Integrated draft and technical results reviewed; major-work freeze |
| **Dec 14** | **Team Project Submission** | Final capstone submitted by 11:59 p.m. |
| **Dec 21** | Final Reflection | Individual reflection submitted by 11:59 p.m. |

### 9. Selected literature

- Fonseca, S., Milho, J., Travassos, B., & Araújo, D. (2012). *Spatial dynamics of team sports exposed by Voronoi diagrams*. **Human Movement Science**, 31(6), 1652–1659. https://doi.org/10.1016/j.humov.2012.04.006
- Radke, D., Brecht, T., & Radke, D. (2022). *Identifying Completed Pass Types and Improving Passing Lane Models*. **Proceedings of the Linköping Hockey Analytics Conference**. https://doi.org/10.3384/ecp191008
- Caetano, F. G., et al. (2021). *Football player dominant region determined by a novel model based on instantaneous kinematics variables*. **Scientific Reports**, 11. https://doi.org/10.1038/s41598-021-97537-4

The citations guide the proposal's conceptual background; the team proposal lead should confirm bibliographic formatting and explain what each cited study actually establishes. Voronoi-based puck inference is **proposed**, not completed.

### 10. Before submitting this proposal

- [ ] Read the **actual SIADS 699 Team Project Proposal rubric/instructions** and adapt required sections, length, and format.
- [ ] Record teammate names, responsibilities, scope/MVP agreement, and data/evaluation ownership.
- [ ] Verify the available Big Data Cup files, coordinate metadata, any licensing limits, and source event semantics.
- [ ] Confirm the team accepts the anonymized-data limitations and risk-managed CV scope.
- [ ] Check the references and remove unsupported claims.
- [ ] Team-review the rewritten final proposal; preserve its final version in the repository.
- [ ] Submit the required artifact to **Canvas by Monday Oct 19, 11:59 p.m.** and record submission confirmation in team notes.

**Source working materials:** `README.md`, `stathletes_event_info.py`, `docs/team/meetings/2026-10-16-project-planning/team_meeting_brief.md`, and `meeting_goals.md` in the existing project repository.
