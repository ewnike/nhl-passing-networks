# ADR-001: Reuse-first, geometry-aware hockey analytics architecture

- **Status:** Accepted (project direction); implementation milestones remain proposed
- **Date:** 2026-10-18
- **Project:** NHL Puck Tracking & Passing Networks
- **Suggested repository location:** `docs/architecture/ADR-001_geometry_aware_hockey_analytics_architecture_2026-10-18.md`

## Decision statement

> We are developing a reproducible, geometry-aware hockey analytics pipeline that combines pretrained computer-vision models with player and puck tracking, spatial analysis, human-verified passing-event detection, and graph-based passing-network research.

## Context

The project has investigated HockeyRink source annotations, a 56-landmark physical-coordinate dictionary, homography estimation, RANSAC residuals, and FiftyOne visual audit datasets. These investigations established the importance of distinguishing original annotations, pretrained-model predictions, geometric projections, and human hypotheses. They do not constitute training a replacement HockeyRink neural network.

The primary research objective is reconstruction and analysis of passing events, rather than creation of a new rink-landmark detector. Reusing available pretrained models should accelerate progress while retaining independent validation of their outputs.

## Decision and responsibilities

| Component | Responsibility | Approach |
|---|---|---|
| HockeyRink | Detect rink landmark IDs and image coordinates | Evaluate and reuse pretrained weights where compatible |
| HockeyAI | Detect supported hockey objects/players | Inspect model metadata and verify actual classes before integration |
| Rink geometry model | Define venue/league rink dimensions, lines, curves, origin, axes, units, and uncertainty | Project-owned, versioned; venue-specific when necessary |
| 56-keypoint correspondence dictionary | Map HockeyRink landmark IDs to physical rink locations under a specified geometry and annotation convention | Project-owned, versioned, validated against primary sources |
| Homography calibration | Map image and physical rink coordinates with residuals and spatial-support diagnostics | OpenCV-based implementation and validation |
| Player and puck tracking | Maintain detections and identities over time | Integrate evaluated detectors and trackers; verify puck capability separately |
| Spatial analytics | Voronoi regions, passing-lane geometry, interception opportunities and uncertainty | Project-developed; distinguish proximity from time-to-intercept and calibrated probability |
| Passing-event system | Infer and human-verify passer, receiver, and event outcome | Core project contribution |
| NetworkX | Represent and analyze passing-event networks | Project-developed analyses using established library |
| FiftyOne | Inspect datasets, compare predictions/projections, curate review cases and evaluate failures | QA workbench, not a mandatory real-time inference dependency |

## Data provenance and review rules

- Keep **source annotations**, **pretrained predictions**, **homography projections**, **review flags**, and **proposed corrections** as separate, traceable records.
- Preserve source files and historical experiment outputs unchanged. Record frame IDs, model versions, geometry/dictionary versions, coordinate conventions, transforms, confidence and uncertainty, and review decisions.
- A lower reprojection residual does **not** independently prove a physical coordinate or landmark identity is correct.
- Do not promote provisional corrections into training data without independent verification and explicit approval.
- Store canonical datasets and approved labels in portable, versioned formats outside the FiftyOne database; use FiftyOne as an inspection and curation layer. Maintain tested backups.
- Respect dataset/model licenses and attribution, including Houshmand Sarkhoosh et al., *HockeyRink: A Dataset for Precise Ice Hockey Rink Keypoint Mapping and Analytics* (MMSys 2025), DOI: 10.1145/3712676.3718338.

## Explicit scope decisions

1. **Reuse first.** Do not train a new rink-landmark model or fine-tune existing weights without evidence of a specific performance gap and a held-out evaluation plan.
2. **Keep both geometry assets.** The physical rink model and the 56-ID correspondence mapping have different purposes; do not conflate them.
3. **Keep FiftyOne.** Use it for visual QA, failure analysis, annotation review, and potential curated fine-tuning sets; do not make the production pipeline depend on its UI or database.
4. **Keep geometry revisions provisional.** Rounded-corner and goalie-crease hypotheses remain under investigation pending authoritative definitions and validation; do not silently update the canonical dictionary.
5. **Focus original development on passing intelligence.** Prioritize event reconstruction, possession and interception analysis, uncertainty, and network evaluation.

## Near-term milestones (proposed)

1. **Model inventory:** Inspect `HockeyRink.pt` and `HockeyAI_model_weight.pt` safely; document architecture, classes/keypoints, licenses, and compatibility.
2. **Local pretrained inference:** Run a reproducible inference experiment on an existing SHL frame; save numerical predictions and provenance.
3. **FiftyOne comparison:** Inspect original annotations, numerical model predictions, and homography projections in separate fields.
4. **First verified passing event:** Produce one traceable, human-reviewed passer–receiver–puck event from a short sequence; include physical coordinates only if calibration is validated.
5. **Spatial analysis:** Add Voronoi and passing-lane measures with clearly stated geometric and uncertainty assumptions.

## Consequences and trade-offs

**Benefits:** Less duplicated model-development effort; clear ownership of project contributions; reproducible calibration and QA; earlier path to passing-event analysis.

**Costs and risks:** Dependencies on third-party weights, licensing, and model generalization; uncertain venue geometry; potential detection and tracking errors; human review effort. These require explicit evaluation rather than assumptions.

## Evidence status

This ADR records a **project architectural decision**, not a claim that every listed component is implemented. Existing evidence includes the two-frame FiftyOne landmark audit, separately saved homography experiments, and preliminary hosted pretrained-model inference. No dictionary revisions or model fine-tuning are authorized by this ADR.

## Follow-up

Revisit this ADR if evaluation demonstrates that a pretrained model is unsuitable, the coordinate conventions cannot be reconciled, or passing-event requirements justify a different architecture. Record any replacement decision in a new ADR rather than silently editing the historical rationale.
