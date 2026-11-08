"""Atomic initial-review submission for FiftyOne video detections.

This module does not select datasets or validate SIHF roster identities.
Callers must perform those checks before invoking submit_initial_review().
"""

from datetime import datetime, timezone

from bson import ObjectId


VALID_STATUSES = frozenset({
    "verified",
    "uncertain",
    "rejected",
})

VALID_REVIEWERS = frozenset({
    "SF_Dye",
    "Z_Snow",
    "E_Wnike",
})


def submit_initial_review(
    collection,
    frame_id,
    detection_id,
    review,
):
    """Atomically submit one initial detection review.

    Returns a result dictionary. A pending detection can be claimed
    by only one submission. Subsequent attempts are rejected.
    """

    reviewer = review.get("reviewer_id")
    status = review.get("review_status")
    player_id = review.get("reviewed_player_id")
    notes = review.get("review_notes")

    if reviewer not in VALID_REVIEWERS:
        raise ValueError("Unapproved reviewer")

    if status not in VALID_STATUSES:
        raise ValueError("Invalid review decision")

    if status == "verified" and not player_id:
        raise ValueError(
            "Verified reviews require a player identity"
        )

    if status == "rejected" and not str(notes or "").strip():
        raise ValueError(
            "Rejected reviews require supporting notes"
        )

    timestamp = datetime.now(timezone.utc)

    frame_oid = ObjectId(str(frame_id))
    detection_oid = ObjectId(str(detection_id))

    result = collection.update_one(
        {
            "_id": frame_oid,
            "player_detections.detections": {
                "$elemMatch": {
                    "_id": detection_oid,
                    "review_status": "pending",
                }
            },
        },
        {
            "$set": {
                "player_detections.detections.$.review_status":
                    status,
                "player_detections.detections.$.reviewer_id":
                    reviewer,
                "player_detections.detections.$.reviewed_player_id":
                    player_id,
                "player_detections.detections.$.review_notes":
                    str(notes or "").strip(),
                "player_detections.detections.$.review_submitted_at":
                    timestamp,
                "player_detections.detections.$.training_approved":
                    False,
            }
        },
    )

    if result.matched_count == 0:
        return {
            "saved": False,
            "status": "REVIEW BLOCKED",
            "reason": (
                "The selected observation is no longer pending "
                "or could not be found. Reload before retrying."
            ),
            "frame_id": str(frame_oid),
            "detection_id": str(detection_oid),
        }

    if result.matched_count != 1 or result.modified_count != 1:
        raise RuntimeError(
            "Unexpected atomic submission result"
        )

    return {
        "saved": True,
        "status": "REVIEW SAVED",
        "reviewer_id": reviewer,
        "review_status": status,
        "reviewed_player_id": player_id,
        "review_submitted_at": timestamp.isoformat(),
        "training_approved": False,
        "frame_id": str(frame_oid),
        "detection_id": str(detection_oid),
    }
