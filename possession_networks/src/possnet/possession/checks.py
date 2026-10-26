"""Validation of the possession table against the events and match results."""

from __future__ import annotations

import pandas as pd

from possnet.possession.sequences import BROAD_LABELS, OUTCOME_DETAILS, STRICT_LABELS
from possnet.validate.checks import CheckResult, ValidationReport, _res


def validate_possessions(
    poss: pd.DataFrame, events: pd.DataFrame, matches: pd.DataFrame
) -> ValidationReport:
    results: list[CheckResult] = []
    results.append(_res("possessions.unique_key", "error", len(poss),
                        poss.duplicated(["match_id", "possession_id", "segment"]).sum()))
    teams = matches.set_index("match_id")[["home_team_id", "away_team_id"]]
    j = poss.join(teams, on="match_id")
    bad_team = ~((j["team_id"] == j["home_team_id"]) | (j["team_id"] == j["away_team_id"]))
    results.append(_res("possessions.team_in_match", "error", len(poss), bad_team.sum()))

    results.append(_res(
        "possessions.outcome_labels_valid", "error", len(poss),
        (~poss["outcome_detail"].isin(OUTCOME_DETAILS)).sum()
        + (~poss["outcome_strict"].isin(STRICT_LABELS)).sum()
        + (~poss["outcome_broad"].isin(BROAD_LABELS)).sum()))
    # The broad scheme can only add turnovers; it must never relabel goals or shots.
    changed = (poss["outcome_strict"] != poss["outcome_broad"])
    allowed = (changed & (poss["outcome_strict"] == "censored")
               & (poss["outcome_broad"] == "turnover"))
    results.append(_res("possessions.broad_only_adds_turnovers", "error", int(changed.sum()),
                        int((changed & ~allowed).sum())))

    reg = events[events["period"] <= 4]
    shots = reg[reg["event_type"] == "shot"].groupby(["match_id", "team_id"]).size()
    in_poss = poss.groupby(["match_id", "team_id"])["n_shots"].sum()
    diff = shots.sub(in_poss, fill_value=0)
    results.append(_res("possessions.shots_reconcile_with_events", "error", len(shots),
                        int((diff != 0).sum()),
                        f"net shot difference {int(diff.sum())}"))

    goals_by_poss = poss.groupby(["match_id", "team_id"])["has_goal"].sum()
    rows = []
    for r in matches.itertuples(index=False):
        for team_id, score in ((r.home_team_id, r.home_score), (r.away_team_id, r.away_score)):
            rows.append(int(goals_by_poss.get((r.match_id, team_id), 0)) != int(score))
    results.append(_res("possessions.goals_reconcile_with_scores", "error", len(rows), sum(rows),
                        "a possession with several goals would count once"))
    results.append(_res("possessions.duration_nonnegative", "error", len(poss),
                        (poss["duration_s"] < 0).sum()))
    results.append(_res("possessions.min_one_team_event", "warn", len(poss),
                        ((poss["n_passes"] == 0) & (poss["n_events"] == 0)).sum()))
    return ValidationReport(results)
