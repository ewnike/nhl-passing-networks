# NHL Puck Tracking & Passing Networks — Team Meeting Brief

**Meeting:** Friday, October 16, 2026  
**Course:** SIADS 699  
**Team Project Proposal:** Monday, October 19, 2026, 11:59 p.m.  
**Final Team Project Submission:** Monday, December 14, 2026, 11:59 p.m.  
**Final Reflection:** Monday, December 21, 2026, 11:59 p.m.

**Purpose of the meeting:** Agree on a deliverable that is achievable by December 14, assign owners for structured passing data and video analysis, and approve a shared event schema and evaluation approach for the October 19 proposal.

## 1. Research question and intended outcome

**Research question:** Can player and spatial passing-network structure characterize puck movement and possession patterns beyond conventional event summaries and possession statistics?

**Minimum viable result:** A reproducible passing-event dataset, directed player-to-player passing network, spatial passing analysis where source coordinates are validated, interpretable network measures and visualizations, and an evidence-based evaluation of results and limitations. The core network result must not depend on successfully reconstructing every puck movement from broadcast video.

**Longer-term objective:** A modular pipeline where verified computer-vision passing events can eventually enter the same schema and network-analysis code as structured vendor events. Compatible schema does **not** mean the two datasets can currently be joined by real person/game identifiers.

## 2. Three connected technical components

**A. Structured events / network science — core workstream**
- Starting source: **Stathletes Big Data Cup**, with pass-event information for selected games. Player and team identities are anonymized.
- Current repository starting point: `stathletes_event_info.py`, which reads an event CSV, treats `Play` and `Incomplete Play` as passing-event candidates, extracts player IDs, start/end coordinates, completion outcome and context, and constructs directed edge counts.
- Proposed analysis: NetworkX graphs, directional edge weights, centrality, pass sequences, spatial movement between rink areas, and thoughtful comparisons across game situations.
- Data owner must verify CSV headers, event semantics, coordinate geometry, ID stability, missingness, and availability of target/receiver IDs before making stronger claims.

**B. Broadcast computer vision — experimental workstream**
- Player detection/tracking: HockeyAI and BoT-SORT experiments, with on-ice foot-point filtering.
- Rink geometry: HockeyRink 56-landmark dictionary; homography, landmark consistency, RANSAC residuals, held-out stability, physical coordinate review.
- Next aims: trustworthy player tracking and human-confirmed pass examples, with uncertain identity, puck state, or rink locations preserved as unknown.
- **Not yet demonstrated:** a reliable end-to-end automatic completed-pass detector or validated puck reconstruction from video.

**C. FiftyOne by Voxel51 — visual QA and human-review layer**
- Used to browse images, inspect landmark layers and metadata, compare original evidence to proposed labels, and flag cases for independent review.
- It is **not** the graph-analysis engine and does **not** itself prove a proposed correction or identify completed passes automatically.
- Team benefit: the same workflow can later review player detections, track continuity, occluded observations, and candidate passing events.

**Integration flow:**

```text
Stathletes Big Data Cup events        Broadcast video
             |                            |
    inspected ETL adapter         HockeyAI + BoT-SORT
             |                            |
             |                HockeyRink / homography checks
             |                            |
             |                  FiftyOne visual QA
             |                            |
             |               Human-confirmed CV event adapter
             \____________________  _______/
                                  \/
                      Shared pass-event contract
                                  |
                    NetworkX / spatial analysis
                                  |
                     Figures, findings, limitations
```

## 3. Integration contract: decide early, validate next

**Proposed canonical fields** (schema design, not a claim that all sources presently supply them):

| Group | Candidate fields | Rule |
|---|---|---|
| Provenance | `source`, `source_file`, `source_event_id`, `verification_status` | Keep observed, inferred and manually verified events distinct |
| Event key | `game_id`, `period`, `event_time_s`, `event_sequence` | Specify whether clock counts up/down; avoid silent time conversion |
| Participant | `team_id`, `passer_id`, `target_id`, optional `receiver_id` | Intended target is not automatically a completed receiver; source-specific IDs are scoped |
| Outcome | `pass_complete`, `pass_type`, optional `confidence` | Separate source event labels from model predictions |
| Spatial | `pass_start_x`, `pass_start_y`, `pass_end_x`, `pass_end_y` | Preserve native source values and separate standardized coordinates |
| Geometry | `rink_profile_id`, `coordinate_system`, `units`, `orientation_reference`, `transform_version`, `coordinate_validation_status` | Do not assume physical rink sizes, axes, units or period/camera orientation agree |
| Context | `strength_state`, optional `score_state`, `possession_id` | Document unavailable fields rather than fabricate them |

**Critical coordinate distinction:** The HockeyRink geometry dictionary in our current experiments uses a **60 m × 30 m** rink, center-ice origin `(0,0)`, longitudinal **X = −30 to +30 m** and lateral **Y = −15 to +15 m**. NHL-sized rinks are physically different, and Stathletes event/tracking coordinate conventions differ as well. A shared column name is *not* a shared spatial reference. Source units, real rink dimensions, orientation and transformations must be documented and validated independently. Dimensionless rink-relative locations may help comparisons, but cannot substitute for real distances in speed/interception calculations.

**Important scope limit:** Anonymized Big Data Cup player IDs cannot automatically be matched to our historical named NHL/Corsi database. Cross-source integration initially means compatible **processing**, not cross-dataset player identity matching.

## 4. What is already working: Landmark QA case study

**FiftyOne dataset created on the user's Mac:** `nhl_hockeyrink_landmark_audit_v1`  
**FiftyOne version:** `1.8.1`  
**Samples:** 2 actual hockey frames (each 1920 × 1080); 34 original annotated keypoints total; 9 review entries.  
**Four independently viewable label fields:** `source_annotations`, `historical_projections`, `review_flags`, `proposed_relabels`.

| Frame | Original landmarks | Review entries | Saved projection geometry |
|---|---:|---:|---|
| `8d4fe67c-6528-4fbb-a8e5-860c2b650cfc` | 25 | 5 | After correction of 16 hash-mark geometry entries |
| `0016cbde-770d-4d43-88ea-676d2f5f5f48` | 9 | 4 | Original pre-correction geometry |

The suspect western-frame labeling shift is provisional: source KP-02 appears to correspond to physical KP-03, and further adjacent source slots may also be offset. A large fitted homography residual motivates review but **does not independently prove the identity is wrong**.

### Preserved checkpoint: FIFTYONE-QA-001 — PASS

**Question:** Does proposed KP-03 use precisely the same recorded image position as original source KP-02?

**Method:** Load the persisted FiftyOne dataset; query source `KP-02` and `PROPOSED KP-03` with original annotation slot `2`; compare their normalized coordinates and reconstructed 1920 × 1080 pixel positions.

| Measurement | Original KP-02 | Proposed KP-03 |
|---|---:|---:|
| Normalized X | 0.223110 | 0.223110 |
| Normalized Y | 0.078811 | 0.078811 |
| Pixel X | 428.3712 | 428.3712 |
| Pixel Y | 85.11588 | 85.11588 |
| Pixel displacement | \- | **0.000000000 px** |
| Exact coordinate equality | \- | **True** |

**Interpretation:** The proposed change is an **identity hypothesis**, not a move of the image point. Original labels and pixel coordinates were not modified. This test **does not validate KP-03 as the correct physical identity**.

**Supporting findings:** The source KP-02 label was marked visible (`source_visibility=2`), had a saved fit residual of **351.084 px**, was excluded by historical RANSAC, and was stored with `human_flagged_provisional` review status. The alternative label retains `hypothesis_not_applied_to_source`. Screenshots demonstrate source, proposal, and review tooltips in FiftyOne.

**Reproducible assets copied locally into the repository (not verified committed):**
- `scripts/hockeyrink/create_fiftyone_landmark_audit_v1.py`
- `docs/hockeyrink/experiments/results/fiftyone_landmark_audit_v1.json`
- `docs/hockeyrink/experiments/fiftyone_landmark_audit_workflow_v1.md`
- Earlier results: `docs/hockeyrink/experiments/results/homography_perturbation_summary_2026-10-15.csv` and `homography_perturbation_tests_B_C_2026-10-15.csv`

**Environmental note:** A warning reported the oldest supported MongoDB major version. Importing and viewing the persistent FiftyOne dataset nevertheless succeeded. Do not perform an unplanned MongoDB upgrade as part of this checkpoint.

## 5. Official SIADS 699 deadlines and proposed internal Done-When milestones

| Official deadline | Course assignment(s) | Suggested internal Done-When |
|---|---|---|
| **Mon Oct 19, 11:59 p.m.** | Team Project Proposal | Agree scope, research question, workstreams, data owner, schema owner, risks, evaluation plan and task assignments; submit proposal |
| **Mon Oct 26, 11:59 p.m.** | Software Tools Mini-Deliverable | Reproduce Stathletes event import and FiftyOne 2-frame landmark QA; document tools and geometry conventions |
| **Mon Nov 2, 11:59 p.m.** | 1st Slack Stand-up Video; Evaluation Plan Mini-Deliverable | Define data checks, network measures, CV calibration quality, held-out verification criteria, and evaluation limits |
| **Mon Nov 9, 11:59 p.m.** | 1st Stand-up Responses; Mentor scheduling reminder; Report Outline | First reproducible network prototype and evidence-led outline; mentor appointment scheduled |
| **Mon Nov 16, 11:59 p.m.** | 2nd Slack Stand-up Video; Visuals Mini-Deliverable | Produce interpretable passing-network and spatial figures plus a documented FiftyOne/CV QA illustration |
| **Mon Nov 23, 11:59 p.m.** | 2nd Stand-up Responses; Revised Outline | Integrate network findings, dataset caveats, relevant literature and measured CV results |
| **Mon Nov 30, 11:59 p.m.** | 3rd Slack Stand-up Video; GitHub Repository; Mentor Check-In | Reproducibility instructions, curated data artifacts, code review, mentor feedback captured |
| **Mon Dec 7, 11:59 p.m.** | 3rd Stand-up Responses; Pre-Flight Checklist | Major research and report integrated; final internal review/feature freeze |
| **Mon Dec 14, 11:59 p.m.** | **Team Project Submission** | Final required deliverables submitted |
| **Mon Dec 21, 11:59 p.m.** | Final Reflection | Reflection submitted |

Course deadlines are as provided from the Canvas calendar; the *Done-When* items are proposals for team discussion.

## 6. Tomorrow's meeting: proposed 30-minute agenda

1. **5 min — Agree scope and MVP.** A reproducible network-analysis result is the primary deliverable; broadcast CV is an evidence-based experimental workstream.
2. **7 min — Appoint owners.** Stathletes ETL/network lead; CV/homography lead; shared schema/integration lead; report/evaluation coordination.
3. **7 min — Demonstrate completed work.** Show the 2-frame FiftyOne audit; click original KP-02, proposed KP-03 and review flag; explain the zero-pixel identity-preserving validation, without presenting it as identity proof.
4. **6 min — Set the data contract and first milestones.** Approve a provisional field schema, coordinate metadata, test samples, and ownership of validation.
5. **5 min — Confirm proposal content and responsibilities.** Assign final sections and review path for Monday evening's submission.

### Decisions to leave the meeting with

- Exactly which **Big Data Cup games/files** may be used, and any data/license restrictions.
- Who owns **source semantics, cleaned pass table and network evaluation**.
- Who owns **CV validation, FiftyOne review, and visual evidence**.
- Who owns the **common schema** and approves field names and coordinate transforms.
- Which analysis/visualizations form the **minimum viable December result**.
- How and when teammates will review the **October 19 proposal**.

## 7. References to include in the proposal

- Fonseca, S., Milho, J., Travassos, B., & Araújo, D. (2012). *Spatial dynamics of team sports exposed by Voronoi diagrams*. Human Movement Science, 31(6), 1652–1659. https://doi.org/10.1016/j.humov.2012.04.006
- Radke, D., Brecht, T., & Radke, D. (2022). *Identifying Completed Pass Types and Improving Passing Lane Models*. Proceedings of the Linköping Hockey Analytics Conference. https://doi.org/10.3384/ecp191008
- Caetano, F. G., et al. (2021). *Football player dominant region determined by a novel model based on instantaneous kinematics variables*. Scientific Reports, 11. https://doi.org/10.1038/s41598-021-97537-4

**Proposed, not implemented:** Voronoi spatial dominance, movement-aware reachability, model-based puck-location inference and automated pass recognition. They are research extensions after validation of positions and tracked identities.

## 8. End-of-evening checkpoint / handoff

**Completed:** FiftyOne app was launched and showed two images; three label layers were visually inspected; persisted dataset coordinates were compared, confirming exact identity-preserving KP-02 → proposed KP-03 point equality; no original source labels were modified.

**Not claimed:** independent approval of the proposed landmark identity, a production-ready homography, automatic passing-event extraction, or a verified integration between anonymized vendor event IDs and CV tracks.

**No Git commit or push was performed by this conversation.** The local repository files and the persistent FiftyOne database should be treated as the present checkpoint. Before committing later, review `git status` and the intended additions. The FiftyOne database is not automatically part of GitHub; the importer and manifest are needed for reproducibility.

**Article idea:** *From Homography Errors to Visual Dataset Audits: Using Voxel51 FiftyOne and Codex in an NHL Computer Vision Pipeline*. Use the original/source/proposed/review screenshots with clear provenance and limitations.
