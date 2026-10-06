"""
test cases for the filter_on_ice module

1. lower_center computes the expected foot point
2. point strictly inside polygon → True
3. point strictly outside polygon → False
4. point exactly on boundary → True
5. classify_detection preserves the original track metadata
6. invalid polygon / malformed bbox behavior, if the implementation validates those inputs
"""

import pytest
from src.tracking.filter_on_ice import (
    lower_center,
    point_in_polygon,
    classify_detection,
)


def test_lower_center():
    assert lower_center([0, 0, 2, 2]) == (1.0, 2.0)
    assert lower_center([1, 3, 5, 7]) == (3.0, 7.0)


def test_point_in_polygon_inside():
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert point_in_polygon((1, 1), polygon) is True


def test_point_in_polygon_outside():
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert point_in_polygon((3, 3), polygon) is False


def test_point_in_polygon_on_boundary():
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert point_in_polygon((1, 0), polygon) is True


def test_classify_detection():
    detection = {"track_id": 1}
    xyxy = [0, 0, 2, 2]
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    result_detection, is_on_ice = classify_detection(detection, xyxy, polygon)
    assert result_detection == detection
    assert is_on_ice is True


def test_classify_detection_off_ice():
    detection = {"track_id": 2}
    xyxy = [3, 3, 5, 5]
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    result_detection, is_on_ice = classify_detection(detection, xyxy, polygon)
    assert result_detection == detection
    assert is_on_ice is False


def test_invalid_polygon():
    with pytest.raises(ValueError):
        point_in_polygon((1, 1), [(0, 0), (2, 0)])


def test_malformed_bbox():
    with pytest.raises(ValueError):
        lower_center([0, 0, 2])
    with pytest.raises(ValueError):
        lower_center([0, 0, 2, 2, 4])


def test_classify_detection_invalid_inputs():
    detection = {"track_id": 3}
    xyxy = [0, 0, 2]
    polygon = [(0, 0), (2, 0), (2, 2), (0, 2)]
    with pytest.raises(ValueError):
        classify_detection(detection, xyxy, polygon)
    xyxy = [0, 0, 2, 2, 4]
    with pytest.raises(ValueError):
        classify_detection(detection, xyxy, polygon)
    polygon = [(0, 0), (2, 0)]
    xyxy = [0, 0, 2, 2]
    with pytest.raises(ValueError):
        classify_detection(detection, xyxy, polygon)
