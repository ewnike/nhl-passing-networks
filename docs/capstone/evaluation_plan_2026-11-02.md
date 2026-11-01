# Team 5 — Hockey Visual Classification, Tracking, and Passing-Network Analysis

## Evaluation Plan — November 2, 2026

### Project Objective and Evolution

Our project has two complementary workstreams: (1) generating structured hockey events from broadcast video and (2) analyzing those events through passing networks.

Our original proposal established player localization, identity, and game-time identification as the video-classification MVP, with passing-event generation as a broader objective.

Our research has progressed toward a more ambitious goal: developing a reproducible computer-vision pipeline capable of identifying players, tracking puck possession, and generating player-to-player passing attempts and outcomes.

The detailed passing-event information required for our Swiss National League analysis is not available to our team as a ready-to-use dataset. Consequently, generating reliable event data has become a central technical challenge.

We are developing the two workstreams in parallel, with the objective of integrating video-derived events into the hockey passing-network platform.

### 1. Metrics and Baselines

**Computer vision and event generation**

We will evaluate:

- **Detection:** Player/goalie precision, recall, and F1 against human annotations.
- **Classification:** Player, goalie, and official confusion matrices.
- **Localization:** Bounding-box IoU and rink-coordinate error where validated reference positions exist.
- **Tracking:** Observation coverage, identity switches, fragmentation, and physical player identification accuracy.
- **Event generation:** Pass-attempt precision/recall, passer/receiver identification accuracy, and pass-outcome classification against human-reviewed events.

Our baseline is the pretrained HockeyAI detector with standard BoT-SORT tracking.

A controlled 750-frame experiment compared persistent tracking with camera-cut-aware initialization. The modified pipeline recovered 13 additional observations at two camera cuts. Outside those frames, 6,482 bounding-box pairs matched with mean IoU = 0.999909. This demonstrates improved post-cut observation availability, not established physical identity accuracy.

**Passing-network analysis — teammate contribution**

[Insert concise evaluation of network construction, expected-threat modeling, incremental value beyond shot-count baselines, and the interactive hockey explorer.]

### 2. Evaluation Data and Independence

Our computer-vision development uses seven broadcast games from the Swiss National League championship finals, featuring the same two teams.

We will reserve previously unused footage for independent evaluation, separate from sequences used to develop tracking, recognition, and contextual inference methods. Human-reviewed annotations will establish reference player identities, locations, and passing events.

Our network-analysis workstream uses 20 games of Stathletes competition data, independently of the Swiss NL video dataset.

[Teammate: specify the network-analysis evaluation split and any additional validation procedures.]

### 3. Risks, Limitations, and Safeguards

Broadcast camera cuts, occlusions, classification ambiguity, and track fragmentation can produce misleading performance estimates. High numerical track coverage does not guarantee correct physical player identity.

We will preserve raw predictions, evaluate failures as well as successes, and avoid testing on sequences used to develop or tune the system. We will report unresolved observations rather than force uncertain classifications.

Our experiments have motivated a proposed Context-Aware Validation and Inference Framework (CAVIF), combining geometric plausibility, temporal consistency, hockey-specific constraints, and probabilistic inference. Initially, questionable detections will be flagged rather than automatically removed. CAVIF remains proposed and will require independent evaluation.

**Evaluation objective:** Demonstrate measurable progress toward reliable video-derived hockey events and verify that those events can support reproducible passing-network analysis.