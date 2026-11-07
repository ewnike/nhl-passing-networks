# Phase 02 — FiftyOne Selected-Detection Diagnostic

**Date:** 2026-11-07
**Status:** PASS — Live selected-detection resolution validated

## Objective

Determine whether FiftyOne 1.8.1 can identify an individual
player detection selected within a video frame and expose that
selection to a custom Python operator.

## Environment

- Project: NHL Puck Tracking & Passing Networks
- FiftyOne: 1.8.1
- Dataset: swiss_nl_g01_video_identity_integrated_07e5_v1
- Plugin: nhl_selected_detection_diagnostic
- Operator: selected_detection_diagnostic
- Operator label: NHL: Inspect Selected Detection

## Implementation

Created a custom FiftyOne plugin under:

plugins/fiftyone_selected_detection_diagnostic/

Files:

- fiftyone.yml
- __init__.py

The plugin is made available to FiftyOne through a symbolic link
in the configured FiftyOne plugin directory.

A backup of the initial plugin implementation was retained as:

plugins/fiftyone_selected_detection_diagnostic/__init__.py.pre_output_display

The operator uses:

- ExecutionContext.selected_labels
- Individual detection IDs
- Video sample IDs
- Video frame numbers
- frames.player_detections
- JSONView for diagnostic output

The operator performs no dataset-writing operations.

## Live Test — PASS

The operator successfully resolved one selected detection in
the integrated G01 video dataset.

Observed results:

- Dataset: swiss_nl_g01_video_identity_integrated_07e5_v1
- Annotation field: frames.player_detections
- Frame number: 45
- Detection ID: 6aeeb405c74adb8ab88c316b
- Video sample ID: 6aeeb405c74adb8ab88c3153
- Identity status: unverified
- Identity conflict: false
- Selected-label count: 1
- Read-only: true

The operator also returned the selected detection's bounding box.

The diagnostic results were displayed successfully in the
FiftyOne App using JSONView.

## Conclusions

PASS: FiftyOne can expose a selected video-frame detection
to a custom operator.

PASS: The operator can resolve an individual detection
using its unique label ID and frame number.

PASS: The operator can display structured diagnostic results.

NOT YET TESTED:

- Teammate identity-review form
- SIHF roster dropdown
- Review submission
- Annotation writes
- Versioned review dataset
- Training-image approval workflow

## Research Safeguards

- Original identity observations remain unchanged.
- Integrated video annotations remain unchanged.
- No automatic identity propagation along BoT-SORT tracks.
- Track IDs are not treated as verified player identities.
- Identity verification remains separate from training approval.

## Next Session

1. Preserve and verify this Git checkpoint.
2. Design a protected, versioned teammate review dataset.
3. Build an SIHF roster-constrained review form.
4. Validate one review submission without modifying source datasets.
5. Prepare teammate instructions and assignments.

## Session Outcome

PHASE 02 SELECTED-DETECTION DIAGNOSTIC: PASS

The custom operator successfully identified an individual
player detection in the G01 video and displayed its metadata.
