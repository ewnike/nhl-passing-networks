# NHL Puck Tracking & Passing Networks — Team Meeting Goals

**Meeting:** Friday, October 16, 2026  
**Course:** SIADS 699  
**Team Project Proposal due:** Monday, October 19, 2026, 11:59 p.m.  
**Final Team Project Submission due:** Monday, December 14, 2026, 11:59 p.m.

**Meeting purpose:** Agree on a realistic, evidence-based capstone plan and assign the work needed to submit the team proposal on Monday.

## Goals and Done-When Criteria

| Goal | Discussion / decision | Done When |
|---|---|---|
| **1. Confirm scope and minimum viable deliverable** | Agree on the central research question; distinguish the structured-passing-data workstream from experimental broadcast CV. | Team can state in one or two sentences what must be reproducibly delivered by December 14; optional capabilities are explicitly labeled as stretch goals. |
| **2. Assign owners** | Select leads for Stathletes ingestion/network analysis; HockeyRink/homography/tracking/FiftyOne QA; event schema and coordinate integration; report/evaluation/proposal. | Each workstream has a named owner and a next action due before October 19 or October 26. |
| **3. Approve an initial shared passing-event contract** | Compare existing Stathletes columns with anticipated CV event fields; agree on time, IDs, intended target versus receiver, pass completion, native coordinates, and provenance. | A provisional schema owner is assigned and the team agrees not to merge data merely because field names match. |
| **4. Agree on source-specific geometry rules** | Preserve IIHF 60 × 30 m center-origin coordinates used by HockeyRink; record Stathletes and venue rink size, source units, orientation, and transforms separately. | Both workstreams agree to preserve native coordinates and validate physical conversions before comparison or spatial integration. |
| **5. Review our working proof of concept** | Demonstrate FiftyOne's original annotations, provisional proposed relabel, human-review flag, and persisted KP-02/KP-03 equality check. | Teammates can explain what `FIFTYONE-QA-001` proves (0 px displacement) and what it does not (correct physical identity). |
| **6. Agree on evaluation and proposal tasks** | Define initial network outputs, data-quality checks, CV validation criteria, and paper sections. Assign proposal drafter, reviewers and submitter. | The team has owners and a review schedule for the October 19 submission, with an initial path to the November 2 Evaluation Plan deliverable. |

## Proposed 30-Minute Agenda

| Minutes | Topic |
|---:|---|
| 0–5 | Confirm research question, scope, and minimum viable deliverable |
| 5–12 | Assign workstream leads and proposal responsibilities |
| 12–19 | Live FiftyOne demonstration: source KP-02, proposed KP-03, review flag, 0-pixel verification |
| 19–25 | Shared event schema, anonymized IDs, rink geometry, and source provenance |
| 25–30 | Confirm initial deliverables, action owners, and Monday proposal review process |

## Proposed Immediate Assignments (Fill In at Meeting)

| Responsibility | Owner | First output | Target |
|---|---|---|---|
| Stathletes Big Data Cup data audit | TBD | Inventory of usable games/files, CSV fields and pass semantics | Oct. 19–26 |
| Directed passing-network prototype | TBD | Reproducible event table and first graph | Initial result by Nov. 9 |
| Broadcast CV / landmark quality assurance | TBD | Reproducible two-frame FiftyOne demo and audit limitations | Oct. 26 |
| Common schema and coordinate contract | TBD | Schema v0.1, dataset profiles, ID/time/units rules | Oct. 26 |
| Evaluation plan and figures | TBD | Metrics and verification criteria across both workstreams | Nov. 2 |
| October 19 team proposal | TBD | Consolidated draft, review, and submission | Oct. 19, 11:59 p.m. |

## Evidence to Show at the Meeting

- **Existing structured-data start:** `stathletes_event_info.py` parses selected `Play` and `Incomplete Play` records and generates directed edge counts. Source semantics, missing values and coordinate conventions still require audit.
- **Existing CV work:** 56-landmark rink dictionary, experimental homography residuals and stability tests, a documented project-derived revision to 16 hash-mark geometry entries, and suspected annotation inconsistencies.
- **FiftyOne QA demonstration:** Persistent dataset `nhl_hockeyrink_landmark_audit_v1`; 2 frames, 34 source landmarks, 9 review entries. `FIFTYONE-QA-001` verified source KP-02 and proposed KP-03 share normalized coordinates `(0.223110, 0.078811)` and pixels `(428.3712, 85.11588)` — **0.000000000 px displacement**. The proposed identity remains provisional.
- **Methodological limits:** Anonymized Big Data Cup IDs are not automatically linkable to real NHL player IDs or unrelated CV video; shared event format is an interface, not proof of matching players, games or rink locations.

## Meeting Notes / Decisions (Complete During Meeting)

**Agreed minimum viable deliverable:**

**Confirmed workstream owners:**

**Approved provisional event fields / schema owner:**

**Initial network outputs and evaluation criteria:**

**Major risks, dependencies, and fallback plan:**

**Proposal drafter, reviewer(s), and submitter:**

**Next check-in date / time:**

## Final Meeting Done-When

The meeting is successful when the team has **(1) a shared minimum viable deliverable, (2) workstream and integration owners, (3) a provisional event schema and coordinate-quality standard, and (4) a dated plan to review and submit the October 19 proposal**.

*This is a planning document. Dates not explicitly identified as course deadlines are proposed internal targets, subject to team agreement.*
