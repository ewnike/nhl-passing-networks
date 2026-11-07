"""Read-only FiftyOne selected-detection diagnostic."""

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types


class SelectedDetectionDiagnostic(foo.Operator):

    @property
    def config(self):
        return foo.OperatorConfig(
            name="selected_detection_diagnostic",
            label="NHL: Inspect Selected Detection",
            dynamic=True,
        )

    def resolve_input(self, ctx):
        inputs = types.Object()

        selections = ctx.selected_labels or []

        inputs.str(
            "selection_count",
            label="Selected detection count",
            default=str(len(selections)),
            view=types.TextView(),
        )

        return types.Property(
            inputs,
            view=types.View(
                label="NHL Selected Detection Diagnostic"
            ),
        )

    def resolve_output(self, ctx):
        outputs = types.Object()

        outputs.obj(
            "diagnostic",
            label="Selected Detection Diagnostic Results",
            view=types.JSONView(),
        )

        return types.Property(
            outputs,
            view=types.View(
                label="NHL Selected Detection Diagnostic Results"
            ),
        )

    def execute(self, ctx):
        selections = ctx.selected_labels or []

        result = {
            "dataset": ctx.dataset_name,
            "selection_count": len(selections),
            "selected_labels": selections,
            "read_only": True,
        }

        if len(selections) != 1:
            result["status"] = (
                "Select exactly one detection before running"
            )
            return {"diagnostic": result}

        selected = selections[0]

        sample_id = selected.get("sample_id")
        frame_number = selected.get("frame_number")
        label_id = selected.get("label_id")
        field = selected.get("field")

        result.update({
            "sample_id": sample_id,
            "frame_number": frame_number,
            "label_id": label_id,
            "field": field,
        })

        if not all([
            sample_id,
            frame_number is not None,
            label_id,
            field,
        ]):
            result["status"] = "Incomplete selection context"
            return {"diagnostic": result}

        sample = ctx.dataset[sample_id]
        frame = sample.frames[int(frame_number)]

        if field not in (
            "frames.player_detections",
            "player_detections",
        ):
            result["status"] = "Unexpected annotation field"
            return {"diagnostic": result}

        labels = frame.player_detections

        matches = [
            detection
            for detection in labels.detections
            if str(detection.id) == str(label_id)
        ]

        if len(matches) != 1:
            result["status"] = "Detection ID resolution failed"
            return {"diagnostic": result}

        detection = matches[0]

        result.update({
            "track_uid": detection.get_field("track_uid"),
            "identity_status": detection.get_field(
                "identity_status"
            ),
            "verified_player_id": detection.get_field(
                "verified_player_id"
            ),
            "verified_player_name": detection.get_field(
                "verified_player_name"
            ),
            "identity_conflict": detection.get_field(
                "identity_conflict"
            ),
            "bounding_box": detection.bounding_box,
            "status": "PASS — Detection resolved",
        })

        return {"diagnostic": result}


def register(plugin):
    plugin.register(SelectedDetectionDiagnostic)
