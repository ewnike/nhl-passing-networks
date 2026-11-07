# Phase 02 — SIHF Seven-Game Roster Checkpoint

Date: 2026-11-07
Project: NHL Puck Tracking & Passing Networks

## Status

Seven-game Swiss National League Finals roster acquisition,
validation, and local preservation: PASS.

Source: fastRhockey 1.1.0
Function: sihf_game_lineups()
Season: 2025–26 (season end year 2026)

## Official SIHF Game Identifiers

| Research game | Date | SIHF game ID |
|---|---|---|
| G01 | 2026-04-18 | 20261105000415 |
| G02 | 2026-04-20 | 20261105000416 |
| G03 | 2026-04-22 | 20261105000417 |
| G04 | 2026-04-24 | 20261105000418 |
| G05 | 2026-04-26 | 20261105000419 |
| G06 | 2026-04-28 | 20261105000420 |
| G07 | 2026-04-30 | 20261105000421 |

## Seven-Game Roster Inventory

| Game | Total records | No absence code |
|---|---:|---:|
| G01 | 59 | 44 |
| G02 | 60 | 44 |
| G03 | 58 | 44 |
| G04 | 59 | 44 |
| G05 | 58 | 44 |
| G06 | 60 | 44 |
| G07 | 58 | 44 |
| TOTAL | 412 | 308 |

- Unique SIHF identities across all lineup records: 60
- Unique players listed without absence codes: 48
- HC Davos series-wide dressed candidates: 25
- Fribourg-Gottéron series-wide dressed candidates: 23
- Players never listed without an absence code: 12
- Each game: 22 home and 22 away players without absence codes

Absence codes observed:
- AB: absent
- IN: injured
- SU: surplus / not selected
- Missing absence code: provisionally interpreted as dressed

The provisional dressed interpretation should be checked against
official game participation records.

## Identity Integrity

- Missing player identifiers: 0
- Missing jersey numbers: 0
- Duplicate player IDs within games: 0
- Cross-game player-name conflicts: 0
- Cross-game team conflicts: 0
- Cross-game jersey-number conflicts: 0
- SIHF game-ID mismatches: 0

## Dressed-Lineup Changes

G01 to G02:
- Entered: Juuso Arola #76
- Left: Patrik Nemeth #12

G02 to G03:
- Entered: Michael Fora #20
- Left: Tim Minder #88

G03 to G04:
- Entered: Patrik Nemeth #12, Adam Tambellini #19,
  Enzo Corvi #70
- Left: Michael Fora #20, Filip Zadina #18,
  Juuso Arola #76

G04 to G05:
- Entered: Filip Zadina #18, Juuso Arola #76
- Left: Patrik Nemeth #12, Brendan Lemieux #22

G05 to G06:
- Entered: Patrik Nemeth #12
- Left: Juuso Arola #76

G06 to G07:
- Entered: Brendan Lemieux #22
- Left: Adam Tambellini #19

These transitions compare stable SIHF player IDs.

## FiftyOne Identity Coverage Baseline

Dataset:
swiss_nl_g01_identity_review_consolidated_v1

- FiftyOne samples: 1325
- Human-verified observations: 301
- Distinct verified player identities: 22
- Series-wide dressed identities: 48
- Identities with verified G01 observations: 22
- Series-wide identities without verified G01 observations: 26
- Identity coverage: 22/48 = 45.8%

This measures identity coverage in the existing G01 review
dataset, not Re-ID model accuracy.

## Preserved Research Assets

### Original SIHF archive

File:
data/sihf/swiss_nl_2026_finals_lineups_raw_v1.rds

Size: 3362 bytes

SHA-256:
2f0af286261ebca97f65b36f5e7b8446c53c7697b2cd56370b441a1e78287459

### Master player identity reference

File:
data/sihf/swiss_nl_2026_finals_master_players_v1.csv

Size: 2362 bytes

SHA-256:
0b71bc0aafd0526aa656068cab0caf3da4928915d10a8cc01475fdc53eb3ed74

### Game-specific roster reference

File:
data/sihf/swiss_nl_2026_finals_game_rosters_v1.csv

Size: 42228 bytes

SHA-256:
8a849169f0bc660790cf2f3aa316c711310a4558d33c7b0dc9490b136f2f1722

All three source files passed independent local checksum verification.

## Research Architecture

Maintain separate, versioned assets:

1. Official SIHF roster and identity reference
2. Human-verified observation database
3. Approved training dataset
4. Model registry

Roster eligibility is not proof of video appearance.
Tracking identifiers are not verified player identities.
Human verification does not automatically update trained models.

## Next Task

Resume Phase 02 FiftyOne teammate annotation development:

1. Integrate game-specific roster eligibility without modifying
   existing verified observations.
2. Inspect FiftyOne 1.8.1 review and annotation capabilities.
3. Build representative player-candidate selection.
4. Establish verification, uncertainty, quality, and
   training-approval fields.
5. Develop versioned annotation export and validation.
6. Write teammate instructions and assignments.

Target: functioning pilot and assignments ready by
Sunday, November 8, 2026.

## Preservation Status

Three roster assets: locally saved and checksum verified.

Git commit and remote push: pending at checkpoint creation.

Original FiftyOne datasets: unchanged.
