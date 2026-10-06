"""
Filter tracked hockey players to the playable ice surface.

Assumption: A skater’s lower bounding-box position is a better proxy for physical ice location than the center of the bounding box.

Workflow:
1. Read a tracked player bounding box.
2. Compute the lower-center point of the box as an approximate skate/foot position.
3. Test whether that point falls inside a supplied playable-rink polygon.
4. Retain on-ice tracks and reject bench/background tracks.
"""

from collections.abc import Sequence
from typing import TypeVar

Point = tuple[float, float]
DetectionT = TypeVar("DetectionT")


def lower_center(xyxy: Sequence[float]) -> Point:
	"""Return the lower-center point of an (x1, y1, x2, y2) box."""
	if len(xyxy) != 4:
		raise ValueError("xyxy bounding boxes must contain exactly four coordinates")

	x1, _, x2, y2 = xyxy
	return (float(x1 + x2) / 2, float(y2))


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
	"""Return whether a point is inside or on the boundary of a polygon."""
	if len(polygon) < 3:
		raise ValueError("a polygon must contain at least three points")

	x, y = point
	inside = False
	previous_x, previous_y = polygon[-1]

	for current_x, current_y in polygon:
		cross = (x - previous_x) * (current_y - previous_y) - (
			y - previous_y
		) * (current_x - previous_x)
		if (
			cross == 0
			and min(previous_x, current_x) <= x <= max(previous_x, current_x)
			and min(previous_y, current_y) <= y <= max(previous_y, current_y)
		):
			return True

		if (current_y > y) != (previous_y > y):
			crossing_x = previous_x + (y - previous_y) * (current_x - previous_x) / (
				current_y - previous_y
			)
			if x < crossing_x:
				inside = not inside

		previous_x, previous_y = current_x, current_y

	return inside


def classify_detection(
	detection: DetectionT,
	xyxy: Sequence[float],
	polygon: Sequence[Point],
) -> tuple[DetectionT, bool]:
	"""Return the unchanged detection and whether its lower-center is on-ice."""
	return detection, point_in_polygon(lower_center(xyxy), polygon)
