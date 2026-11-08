"""Protected G01 player identity review — preview only."""

import csv
from pathlib import Path

import fiftyone as fo
import fiftyone.operators as foo
from .atomic_submission import submit_initial_review
import fiftyone.operators.types as types


REVIEW_DATASET = "swiss_nl_g01_player_review_workstation_v1"
GAME_ID = "20261105000415"

APPROVED_REVIEWERS = {
    "SF_Dye",
    "Z_Snow",
    "E_Wnike",
}

ROSTER_PATH = (
    Path(__file__).resolve().parents[2]
    / "data/sihf/swiss_nl_2026_finals_game_rosters_v1.csv"
)


def load_roster():
    with ROSTER_PATH.open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        rows = list(csv.DictReader(stream))

    dressed = [
        row for row in rows
        if row["research_game_id"] == "G01"
        and row["game_id"] == GAME_ID
        and row["dressed"].strip().upper() == "TRUE"
    ]

    ids = [row["player_id"] for row in dressed]

    if len(dressed) != 44 or len(set(ids)) != 44:
        raise ValueError("G01 roster validation failed")

    return sorted(
        dressed,
        key=lambda row: (
            row["team_id"],
            int(row["player_jersey"]),
        ),
    )


def selected_detection(ctx):
    if ctx.dataset_name != REVIEW_DATASET:
        raise ValueError(
            "Open the protected G01 review dataset first"
        )

    selections = ctx.selected_labels or []

    if len(selections) != 1:
        raise ValueError(
            "Select exactly one player detection"
        )

    selected = selections[0]

    if selected.get("field") not in (
        "frames.player_detections",
        "player_detections",
    ):
        raise ValueError("Unexpected annotation field")

    sample_id = selected.get("sample_id")
    frame_number = selected.get("frame_number")
    label_id = selected.get("label_id")

    if not sample_id or frame_number is None or not label_id:
        raise ValueError("Incomplete detection selection")

    sample = ctx.dataset[sample_id]
    frame = sample.frames[int(frame_number)]

    labels = frame.player_detections

    if labels is None:
        raise ValueError("No detections in selected frame")

    matches = [
        detection
        for detection in labels.detections
        if str(detection.id) == str(label_id)
    ]

    if len(matches) != 1:
        raise ValueError("Selected detection not found")

    return selected, matches[0]


def validate_pending_review(detection):
    """Reject duplicate initial reviews.

    This function is read-only. It does not save annotations.

    Production submissions must additionally enforce an atomic
    pending-to-reviewed transition to prevent concurrent overwrites.
    """

    status = detection.get_field("review_status")

    if status == "pending":
        return True

    if status in ("verified", "uncertain", "rejected"):
        reviewer = detection.get_field("reviewer_id")

        raise ValueError(
            "DUPLICATE REVIEW BLOCKED — "
            f"This observation was already reviewed "
            f"(status={status}, reviewer={reviewer}). "
            "Use the separate adjudication workflow."
        )

    raise ValueError(
        "REVIEW BLOCKED — "
        f"Unexpected existing review status: {status!r}. "
        "Manual inspection required."
    )


def validate_review(params, detection):
    validate_pending_review(detection)

    reviewer = str(params.get("reviewer_id") or "").strip()

    if reviewer not in APPROVED_REVIEWERS:
        raise ValueError(
            "Reviewer ID must be SF_Dye, Z_Snow, or E_Wnike"
        )

    status = params.get("review_status")

    if status not in ("verified", "uncertain", "rejected"):
        raise ValueError("Select a review decision")

    roster = {
        row["player_id"]: row
        for row in load_roster()
    }

    player_id = params.get("reviewed_player_id")

    if player_id in ("", None):
        player_id = None
    else:
        player_id = str(player_id)

    if status == "verified" and player_id is None:
        raise ValueError(
            "Verified decisions require an SIHF player"
        )

    if player_id is not None and player_id not in roster:
        raise ValueError(
            "Selected player is not on the G01 dressed roster"
        )

    original_status = detection.get_field(
        "identity_status"
    )

    original_player = detection.get_field(
        "verified_player_id"
    )

    if (
        status == "verified"
        and original_status == "verified"
        and original_player is not None
        and str(original_player) != player_id
    ):
        raise ValueError(
            "Conflicting existing verified identity — "
            "manual adjudication required"
        )

    notes = str(params.get("review_notes") or "").strip()

    if status == "rejected" and not notes:
        raise ValueError(
            "Rejected decisions require supporting notes"
        )

    return {
        "reviewer_id": reviewer,
        "review_status": status,
        "reviewed_player_id": player_id,
        "roster_player": (
            roster[player_id]
            if player_id is not None
            else None
        ),
        "review_notes": notes,
    }


def review_warning(message, selected=None, detection=None):
    """Build a persistent, read-only validation result."""

    result = {
        "status": "REVIEW BLOCKED",
        "reason": str(message),
        "saved": False,
        "mode": "PREVIEW_ONLY",
    }

    if selected is not None:
        result["frame_number"] = selected.get("frame_number")
        result["detection_id"] = selected.get("label_id")

    if detection is not None:
        result["existing_identity_status"] = (
            detection.get_field("identity_status")
        )
        result["existing_verified_player_id"] = (
            detection.get_field("verified_player_id")
        )
        result["track_uid"] = detection.get_field("track_uid")

    return {"preview": result}


def warning_markdown(result):
    """Create a readable warning without modifying annotations."""

    if result.get("status") != "REVIEW BLOCKED":
        return "## Review Preview\\n**No changes saved.**"

    reason = str(
        result.get("reason") or "Review validation failed"
    )

    lines = [
        "## ⚠️ REVIEW BLOCKED",
        "",
        f"**Reason: {reason}**",
        "",
    ]

    existing_id = result.get("existing_verified_player_id")

    if existing_id is not None:
        lines.append(
            f"**Existing verified SIHF ID:** {existing_id}"
        )
        lines.append("")

    lines.extend([
        "**NO CHANGES SAVED**",
        "",
        "Review the information before trying again.",
    ])

    return "\\n".join(lines)


class ReviewPlayerIdentity(foo.Operator):

    @property
    def config(self):
        return foo.OperatorConfig(
            name="review_player_identity",
            label="NHL: Review Player Identity (Preview)",
            dynamic=True,
        )

    def resolve_input(self, ctx):
        inputs = types.Object()

        try:
            selected, detection = selected_detection(ctx)

            summary = (
                f"Frame: {selected['frame_number']} | "
                f"Track: {detection.get_field('track_uid')} | "
                f"Existing status: "
                f"{detection.get_field('identity_status')} | "
                f"Existing SIHF ID: "
                f"{detection.get_field('verified_player_id')}"
            )

        except (ValueError, KeyError, IndexError) as exc:
            summary = f"Selection not ready: {exc}"

        inputs.view(
            "existing_identity",
            types.Notice(label=summary),
        )

        inputs.view(
            "review_safety_notice",
            types.Notice(
                label="Review Safety Notice",
                description=(
                    "Existing verified identities are protected. "
                    "Conflicting assignments require manual adjudication."
                ),
            ),
        )

        inputs.str(
            "reviewer_id",
            label="Reviewer ID",
            description=(
                "Enter SF_Dye, Z_Snow, or E_Wnike"
            ),
            required=True,
        )

        player_choices = types.Dropdown()

        # Explicit empty choice prevents an implicit player assignment
        player_choices.add_choice(
            "",
            label="— No player selected —",
        )

        roster = load_roster()

        for row in roster:
            team = (
                "HCD" if row["team_id"] == "101151"
                else "FRI"
            )

            player_choices.add_choice(
                row["player_id"],
                label=(
                    f"{team} #{row['player_jersey']} "
                    f"{row['player_name']} "
                    f"(SIHF {row['player_id']})"
                ),
            )

        inputs.enum(
            "reviewed_player_id",
            [""] + [row["player_id"] for row in roster],
            label="G01 SIHF Player",
            view=player_choices,
            required=False,
            default="",
        )

        status_choices = types.RadioGroup()

        for status in ("verified", "uncertain", "rejected"):
            status_choices.add_choice(
                status,
                label=status.capitalize(),
            )

        inputs.enum(
            "review_status",
            ["verified", "uncertain", "rejected"],
            label="Review Decision",
            view=status_choices,
            required=True,
        )

        inputs.str(
            "review_notes",
            label="Supporting Notes",
            required=False,
        )

        return types.Property(
            inputs,
            view=types.View(
                label="NHL Player Identity Review — Preview Only"
            ),
        )

    def execute(self, ctx):
        selected = None
        detection = None

        try:
            selected, detection = selected_detection(ctx)

            review = validate_review(
                ctx.params,
                detection,
            )

        except ValueError as exc:
            return review_warning(
                str(exc),
                selected=selected,
                detection=detection,
            )

        result = {
            "mode": "PREVIEW_ONLY",
            "dataset": ctx.dataset_name,
            "sample_id": selected["sample_id"],
            "frame_number": selected["frame_number"],
            "detection_id": selected["label_id"],
            "track_uid": detection.get_field("track_uid"),
            "original_identity_status": detection.get_field(
                "identity_status"
            ),
            "original_verified_player_id": detection.get_field(
                "verified_player_id"
            ),
            **review,
            "training_approved": False,
            "saved": False,
        }

        return {"preview": result}

    def resolve_output(self, ctx):
        outputs = types.Object()

        result = (ctx.results or {}).get("preview", {})

        if result.get("status") == "REVIEW BLOCKED":
            outputs.view(
                "warning_heading",
                types.Warning(
                    label="REVIEW BLOCKED",
                    description="The proposed review was rejected.",
                ),
            )

            outputs.view(
                "warning_reason",
                types.Notice(
                    label="Reason",
                    description=str(
                        result.get("reason")
                        or "Review validation failed"
                    ),
                ),
            )

            existing_id = result.get(
                "existing_verified_player_id"
            )

            if existing_id is not None:
                outputs.view(
                    "existing_identity_warning",
                    types.Notice(
                        label="Existing verified SIHF ID",
                        description=str(existing_id),
                    ),
                )

            outputs.view(
                "no_changes_saved",
                types.Warning(
                    label="NO CHANGES SAVED",
                ),
            )

        else:
            outputs.view(
                "preview_heading",
                types.Notice(
                    label="Review Preview",
                    description="No changes saved.",
                ),
            )

        outputs.obj(
            "preview",
            label="Proposed Review — NOT SAVED",
            view=types.JSONView(),
        )

        return types.Property(
            outputs,
            view=types.View(
                label="NHL Player Review Preview"
            ),
        )



class SubmitProtectedReview(ReviewPlayerIdentity):
    """Protected submission using MongoDB atomic conditional updates."""

    @property
    def config(self):
        return foo.OperatorConfig(
            name="submit_protected_review",
            label="NHL: Submit Protected Review",
            dynamic=True,
        )

    def resolve_input(self, ctx):
        # Reuse the preview operator's validated form.
        form = super().resolve_input(ctx)
        form.view.label = "NHL Player Identity Review — Submit"
        return form

    def execute(self, ctx):
        selected = None
        detection = None

        try:
            selected, detection = selected_detection(ctx)

            review = validate_review(
                ctx.params,
                detection,
            )

            # Reload the authoritative dataset rather than relying
            # exclusively on the operator's existing context.
            dataset = fo.load_dataset(REVIEW_DATASET)
            dataset.reload()

            sample = dataset[selected["sample_id"]]
            frame = sample.frames[
                int(selected["frame_number"])
            ]

            fresh_matches = [
                d for d in frame.player_detections.detections
                if str(d.id) == str(selected["label_id"])
            ]

            if len(fresh_matches) != 1:
                raise ValueError(
                    "Selected detection no longer exists"
                )

            fresh_detection = fresh_matches[0]

            # Revalidate the proposed review against fresh data.
            review = validate_review(
                ctx.params,
                fresh_detection,
            )

            result = submit_initial_review(
                collection=dataset._frame_collection,
                frame_id=frame.id,
                detection_id=fresh_detection.id,
                review=review,
            )

            result.update({
                "dataset": REVIEW_DATASET,
                "sample_id": selected["sample_id"],
                "frame_number": selected["frame_number"],
                "track_uid": fresh_detection.get_field(
                    "track_uid"
                ),
            })

            return {"preview": result}

        except (ValueError, KeyError, IndexError) as exc:
            warning = review_warning(
                str(exc),
                selected=selected,
                detection=detection,
            )
            warning["preview"]["mode"] = "PROTECTED_SUBMISSION"
            return warning

    def resolve_output(self, ctx):
        result = (ctx.results or {}).get("preview", {})

        if result.get("saved") is not True:
            return super().resolve_output(ctx)

        outputs = types.Object()

        outputs.view(
            "success_heading",
            types.Notice(
                label="REVIEW SAVED",
                description=(
                    "The initial review was accepted "
                    "and saved atomically."
                ),
            ),
        )

        outputs.view(
            "review_lock_notice",
            types.Notice(
                label="Initial Review Locked",
                description=(
                    "Further submissions for this detection "
                    "will be rejected. Corrections require "
                    "a separate adjudication workflow."
                ),
            ),
        )

        outputs.obj(
            "preview",
            label="Saved Review",
            view=types.JSONView(),
        )

        return types.Property(
            outputs,
            view=types.View(
                label="NHL Protected Review Submission"
            ),
        )

def register(plugin):
    plugin.register(ReviewPlayerIdentity)
    plugin.register(SubmitProtectedReview)
