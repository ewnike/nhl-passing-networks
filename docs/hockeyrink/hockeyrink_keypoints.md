# HockeyRink Landmark and Coordinate Reference

## Purpose

Explain how HockeyRink keypoint predictions are mapped from
broadcast-image coordinates to physical rink coordinates for the
NHL Passing Networks project.

## Source

Houshmand Sarkhoosh et al. (2025)
"HockeyRink: A Dataset for Precise Ice Hockey Rink Keypoint
Mapping and Analytics"

## 1. Physical Rink Geometry

### Figure 1 — IIHF Standard Rink Dimensions

![Standard IIHF hockey rink dimensions](figures/hockeyrink_figure_01.png)

*Figure 1. Standard hockey rink dimensions as defined by the IIHF
(60 m × 30 m). Source: Houshmand Sarkhoosh et al. (2025),
HockeyRink.*

Physical dimensions:
- Length: 60 m
- Width: 30 m

### Coordinate Convention

North:
South:
East:
West:
Origin:
x-axis:
y-axis:

## 2. HockeyRink Landmark System

### Figure 2 — 56 HockeyRink Keypoints

![HockeyRink 56-keypoint annotation map](figures/hockeyrink_figure_02.png)

*Figure 2. HockeyRink annotation scheme showing the 56 canonical
rink landmarks, KP-0 through KP-55. Source: Houshmand Sarkhoosh
et al. (2025), HockeyRink.*

HockeyRink defines 56 fixed rink landmarks:

KP-0 through KP-55.

Only landmarks present in the current broadcast view are expected
to be observable.

## 3. Annotation Representation

Bounding box:
[class_id, x_center, y_center, width, height]

Keypoint:
(x_i, y_i, v_i)

Visibility:
0 = not present
1 = occluded
2 = visible

## 4. Keypoint Reference

### Rink Orientation Convention

Landmark names use the fixed orientation shown in Figure 2:

- North = top of the canonical rink diagram
- South = bottom of the canonical rink diagram
- West = left end of the canonical rink diagram
- East = right end of the canonical rink diagram

These directions refer to the canonical rink coordinate system and do
not change with broadcast camera orientation, camera panning or zooming,
or team direction of play.

### Physical Coordinate Convention

The center-ice faceoff spot is the origin `(0, 0)`.

- X measures position along the length of the rink.
- Negative X = West.
- Positive X = East.
- Y measures position across the width of the rink.
- Positive Y = North.
- Negative Y = South.
- Coordinates are expressed in meters.

For a 60 m × 30 m rink:

- West extreme: X = -30.00 m
- East extreme: X = +30.00 m
- North extreme: Y = +15.00 m
- South extreme: Y = -15.00 m
- Center ice: (0.00, 0.00)

### Faceoff Hash-Mark Convention

For end-zone faceoff-circle landmarks:

- `d` = defensive-side hash mark. The defending player occupies the
  side of the faceoff alignment closest to that end's goal.
- `o` = offensive-side hash mark. The attacking player faces the goal
  with the defending player positioned between the attacking player
  and the goal.

The `d` and `o` terms are project-specific descriptive terminology.
The canonical HockeyRink identifiers remain KP-0 through KP-55.

> **Mapping status:** Semantic mapping complete (V1).
> Physical rink coordinates are partially assigned.
> Coordinate values will be derived separately from the documented
> rink geometry rather than estimated from Figure 2.

### Landmark Dictionary

| KP | Project landmark name | X (m) | Y (m) | Description |
|---:|---|---:|---:|---|
| 0 |west_trapezoid_line_north_board_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 1 |west_trapezoid_line_south_board_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 2 |west_goal_line_north_board_intersection | -26.00 | +15.00 | The goal line is located 4.0 m from the end boards and extends across the width of the rink. |
| 3 | west_trapezoid_line_north_goal_line_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 4 | west_goalie_crease_line_north_goal_line_intersection | TBD | TBD | Northern intersection of the west goal crease boundary with the west goal line. |
| 5 | west_goalie_crease_line_south_goal_line_intersection | TBD | TBD | Southern intersection of the west goal crease boundary with the west goal line. |
| 6 | west_trapezoid_line_south_goal_line_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 7 | west_goal_line_south_board_intersection | -26.00 | -15.00 | The goal line is located 4.0 m from the end boards and extends across the width of the rink. |
| 8 | west_top_of_goalie_crease_north | TBD | TBD | Northern endpoint of the front boundary of the west goal crease. |
| 9 | west_top_of_goalie_crease_south | TBD | TBD | Southern endpoint of the front boundary of the west goal crease. |
| 10 | western_end_zone_north_d_fo_hash_mark_north | TBD | TBD | Northern endpoint of the d-side hash-mark pair associated with the north faceoff circle in the western end zone. |
| 11 | western_end_zone_north_d_fo_hash_mark_south | TBD | TBD | Southern endpoint of the d-side hash-mark pair associated with the north faceoff circle in the western end zone. |
| 12 | western_end_zone_south_d_fo_hash_mark_north | TBD | TBD | Northern endpoint of the d-side hash-mark pair associated with the south faceoff circle in the western end zone. |
| 13 | western_end_zone_south_d_fo_hash_mark_south | TBD | TBD | Southern endpoint of the d-side hash-mark pair associated with the south faceoff circle in the western end zone. |
| 14 | western_end_zone_fo_dot_north | -20.00 | +7.00 | Center faceoff dot of the north faceoff circle in the western end zone. |
| 15 | western_end_zone_fo_dot_south | -20.00 | -7.00 | Center faceoff dot of the south faceoff circle in the western end zone. |
| 16 | western_end_zone_north_o_fo_hash_mark_north | TBD | TBD |  Northern endpoint of the o-side hash-mark pair associated with the north faceoff circle in the western end zone. |
| 17 | western_end_zone_north_o_fo_hash_mark_south | TBD | TBD | Southern endpoint of the o-side hash-mark pair associated with the north faceoff circle in the western end zone. |
| 18 | western_end_zone_south_o_fo_hash_mark_north | TBD | TBD | Northern endpoint of the o-side hash-mark pair associated with the south faceoff circle in the western end zone. |
| 19 | western_end_zone_south_o_fo_hash_mark_south | TBD | TBD | Southern endpoint of the o-side hash-mark pair associated with the south faceoff circle in the western end zone. |
| 20 | western_blue_line_north_board_intersection | -8.66 | +15.00 | Northern endpoint of western blue line at north boards |
| 21 | western_blue_line_south_board_intersection | -8.66 | -15.00 | Southern endpoint of western blue line at south boards |
| 22 | west_neutral_zone_north_faceoff_dot| TBD | +7.00 | Faceoff dot immediately east of the western blue line, north side |
| 23 | west_neutral_zone_south_faceoff_dot | TBD | -7.00 | Faceoff dot immediately east of the western blue line, south side |
| 24 | center_red_line_north_board_intersection | 0.00 | +15.00 |Intersection of the center red line with the north boards. |
| 25 | center_ice_faceoff_circle_north_hash_marks | TBD | TBD | Northern intersection of the center red line with the center faceoff circle. |
| 26 | center_ice_faceoff_spot | 0.00 | 0.00 | Center faceoff spot at the geometric center of the rink. |
| 27 | center_ice_faceoff_circle_south_hash_marks | TBD | TBD | Southern intersection of the center red line with the center faceoff circle. |
| 28 | western_point_of_referee_crease | TBD | TBD | Western endpoint of the referee crease along the south boards. |
| 29 | top_of_referee_crease | TBD | TBD | Northernmost point of the referee crease. |
| 30 | center_red_line_south_board_intersection | 0.00 | -15.00 |Intersection of the center red line with the south boards. |
| 31 | eastern_point_referee_crease | TBD | TBD | Eastern endpoint of the referee crease along the south boards. |
| 32 | east_neutral_zone_north_faceoff_dot | TBD | +7.00 | Faceoff dot immediately west of the eastern blue line, north side |
| 33 | east_neutral_zone_south_faceoff_dot | TBD | -7.00 | Faceoff dot immediately west of the eastern blue line, south side |
| 34 | eastern_blue_line_north_board_intersection | +8.66 | +15.00 |Northern endpoint of eastern blue line at boards |
| 35 | eastern_blue_line_south_board_intersection | +8.66 | -15.00 | Southern endpoint of eastern blue line at boards |
| 36 | eastern_end_zone_north_o_fo_hash_mark_north | TBD | TBD | Northern endpoint of the o-side hash-mark pair associated with the north faceoff circle in the eastern end zone. |
| 37 | eastern_end_zone_north_o_fo_hash_mark_south | TBD | TBD | Southern endpoint of the o-side hash-mark pair associated with the north faceoff circle in the eastern end zone. |
| 38 | eastern_end_zone_south_o_fo_hash_mark_north | TBD | TBD | Northern endpoint of the o-side hash-mark pair associated with the south faceoff circle in the eastern end zone. |
| 39 |  eastern_end_zone_south_o_fo_hash_mark_south | TBD | TBD | Southern endpoint of the o-side hash-mark pair associated with the south faceoff circle in the eastern end zone. |
| 40 | eastern_end_zone_fo_dot_north | +20.00 | +7.00 | Center faceoff dot of the north faceoff circle in the eastern end zone. |
| 41 | eastern_end_zone_fo_dot_south | +20.00 | -7.00 | Center faceoff dot of the south faceoff circle in the eastern end zone. |
| 42 | eastern_end_zone_north_d_fo_hash_mark_north | TBD | TBD | Northern endpoint of the d-side hash-mark pair associated with the north faceoff circle in the eastern end zone. |
| 43 | eastern_end_zone_north_d_fo_hash_mark_south | TBD | TBD | Southern endpoint of the d-side hash-mark pair associated with the north faceoff circle in the eastern end zone. |
| 44 | eastern_end_zone_south_d_fo_hash_mark_north | TBD | TBD | Northern endpoint of the d-side hash-mark pair associated with the south faceoff circle in the eastern end zone. |
| 45 | eastern_end_zone_south_d_fo_hash_mark_south | TBD | TBD | Southern endpoint of the d-side hash-mark pair associated with the south faceoff circle in the eastern end zone. |
| 46 | east_top_of_goalie_crease_north | TBD | TBD | Northern endpoint of the front boundary of the east goal crease. |
| 47 | east_top_of_goalie_crease_south | TBD | TBD | Southern endpoint of the front boundary of the east goal crease. |
| 48 | east_goal_line_north_board_intersection | +26.00 | +15.00 | The goal line is located 4.0 m from the end boards and extends across the width of the rink. |
| 49 | east_trapezoid_line_north_goal_line_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 50 | east_goalie_crease_line_north_goal_line_intersection | TBD | TBD | Northern intersection of the east goal crease boundary with the east goal line. |
| 51 | east_goalie_crease_line_south_goal_line_intersection | TBD | TBD | Southern intersection of the east goal crease boundary with the east goal line. |
| 52 | east_trapezoid_line_south_goal_line_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 53 | east_goal_line_south_board_intersection | +26.00 | -15.00 | The goal line is located 4.0 m from the end boards and extends across the width of the rink. |
| 54 | east_trapezoid_line_north_board_intersection | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |
| 55 | east_trapezoid_line_south_board_intersection  | TBD | TBD | One of two 5 cm wide red lines that run diagonally from the goal line to the boards. |

## 5. HockeyRink Inference

For each predicted keypoint:

KP index
→ pixel coordinate
→ confidence
→ canonical rink landmark

## 6. Homography

Known rink landmarks provide correspondences:

image pixel (x, y)
↔
physical rink (x_m, y_m)

These correspondences are used to estimate the image-to-rink
homography.

## 7. Player Location

BoT-SORT bounding box
→ lower-center skate proxy
→ image coordinate
→ homography
→ physical rink coordinate

## 8. Validation Notes

Document SHL → Swiss National League model-transfer experiments,
confidence thresholds, failure cases, camera movement, and
occlusions.