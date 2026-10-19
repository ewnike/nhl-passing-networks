"""Validate canonical tables against the data contract and its semantic rules.

Each check returns a CheckResult. Severity "error" means downstream code would be
wrong or unsafe; "warn" flags something worth reading but not blocking.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from possnet.schema import contract as c


@dataclass(frozen=True)
class CheckResult:
    name: str
    severity: str  # "error" or "warn"
    n_checked: int
    n_failing: int
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.n_failing == 0


class ValidationReport:
    def __init__(self, results: list[CheckResult]) -> None:
        self.results = results

    @property
    def ok(self) -> bool:
        """True when no error severity check failed."""
        return all(r.passed for r in self.results if r.severity == "error")

    def to_frame(self) -> pd.DataFrame:
        frame = pd.DataFrame([{**asdict(r), "passed": r.passed} for r in self.results])
        return frame[["name", "severity", "passed", "n_checked", "n_failing", "detail"]]

    def summary(self) -> str:
        frame = self.to_frame()
        errors = frame[(~frame.passed) & (frame.severity == "error")]
        warns = frame[(~frame.passed) & (frame.severity == "warn")]
        return (f"{len(frame)} checks: {int(frame.passed.sum())} passed, "
                f"{len(errors)} failed (error), {len(warns)} flagged (warn)")


# ------------------------------------------------------------------- utilities
def _kind_ok(series: pd.Series, dtype: str) -> bool:
    if dtype == "string":
        return pd.api.types.is_string_dtype(series) or series.dtype == object
    if dtype == "Int64":
        return pd.api.types.is_integer_dtype(series)
    if dtype == "float64":
        return pd.api.types.is_float_dtype(series)
    if dtype == "boolean":
        return pd.api.types.is_bool_dtype(series)
    return False


def match_durations_s(events: pd.DataFrame) -> pd.Series:
    """Regulation plus extra time duration per match (seconds), from event clocks."""
    reg = events[events["period"] <= 4]
    per_period = reg.groupby(["match_id", "period"])["period_time_s"].max()
    return per_period.groupby("match_id").sum()


def _res(name: str, severity: str, n_checked: int, failing: int, detail: str = "") -> CheckResult:
    return CheckResult(name, severity, int(n_checked), int(failing), detail)


# ---------------------------------------------------------------------- checks
def check_schema(tables: dict[str, pd.DataFrame]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for table, frame in tables.items():
        cols = c.TABLES[table]
        missing = [col.name for col in cols if col.name not in frame.columns]
        extra = [n for n in frame.columns if n not in c.column_names(table)]
        results.append(_res(f"{table}.columns_present", "error", len(cols), len(missing),
                            f"missing={missing}" if missing else ""))
        if extra:
            results.append(_res(f"{table}.no_extra_columns", "warn", len(frame.columns),
                                len(extra), f"extra={extra}"))
        bad_types = [col.name for col in cols
                     if col.name in frame.columns and not _kind_ok(frame[col.name], col.dtype)]
        results.append(_res(f"{table}.dtypes", "error", len(cols), len(bad_types),
                            f"bad={bad_types}" if bad_types else ""))
        null_bad = {col.name: int(frame[col.name].isna().sum()) for col in cols
                    if not col.nullable and col.name in frame.columns
                    and frame[col.name].isna().any()}
        results.append(_res(f"{table}.non_nullable_columns", "error",
                            sum(not col.nullable for col in cols), len(null_bad),
                            str(null_bad) if null_bad else ""))
        enum_bad: dict[str, list[str]] = {}
        for col in cols:
            if col.allowed and col.name in frame.columns:
                vals = frame[col.name].dropna().astype(str)
                bad = sorted(set(vals) - set(col.allowed))
                if bad:
                    enum_bad[col.name] = bad[:5]
        results.append(_res(f"{table}.allowed_values", "error",
                            sum(bool(col.allowed) for col in cols), len(enum_bad),
                            str(enum_bad) if enum_bad else ""))
    return results


def check_event_ordering(events: pd.DataFrame) -> list[CheckResult]:
    results = []
    dup = events.duplicated(["source", "event_id"]).sum()
    results.append(_res("events.event_id_unique", "error", len(events), dup))
    ordered = events.sort_values(["match_id", "event_index"], kind="stable")
    idx = ordered.groupby("match_id")["event_index"]
    non_increasing = (idx.diff().dropna() < 1).sum()
    results.append(_res("events.event_index_strictly_increasing", "error", len(events),
                        non_increasing))
    gaps = (idx.diff().dropna() > 1).sum()
    results.append(_res("events.event_index_contiguous", "warn", len(events), gaps))
    period_back = (ordered.groupby("match_id")["period"].diff().dropna() < 0).sum()
    results.append(_res("events.period_never_decreases", "error", len(events), period_back))
    neg = (events["period_time_s"] < 0).sum()
    results.append(_res("events.period_time_nonnegative", "error", len(events), neg))
    return results


def check_referential(
    matches: pd.DataFrame, events: pd.DataFrame, appearances: pd.DataFrame
) -> list[CheckResult]:
    results = []
    orphan = (~events["match_id"].isin(matches["match_id"])).sum()
    results.append(_res("events.match_in_matches", "error", len(events), orphan))
    no_events = (~matches["match_id"].isin(events["match_id"])).sum()
    results.append(_res("matches.have_events", "warn", len(matches), no_events))

    m = events.merge(
        matches[["match_id", "home_team_id", "away_team_id"]], on="match_id", how="left"
    )
    not_team = ~((m["team_id"] == m["home_team_id"]) | (m["team_id"] == m["away_team_id"]))
    results.append(_res("events.team_in_match", "error", len(m), not_team.sum()))
    home_mismatch = (m["is_home"] != (m["team_id"] == m["home_team_id"])).sum()
    results.append(_res("events.is_home_consistent", "error", len(m), home_mismatch))

    keys = events.dropna(subset=["player_id"])[["match_id", "team_id", "player_id"]]
    keys = keys.drop_duplicates()
    app_keys = appearances[["match_id", "team_id", "player_id"]].drop_duplicates()
    joined = keys.merge(app_keys, how="left", on=["match_id", "team_id", "player_id"],
                        indicator=True)
    results.append(_res("events.player_has_appearance", "error", len(keys),
                        (joined["_merge"] == "left_only").sum()))
    return results


def check_coordinates(matches: pd.DataFrame, events: pd.DataFrame) -> list[CheckResult]:
    results = []
    located = events["event_type"].isin(c.LOCATED_EVENT_TYPES)
    miss_start = (located & (events["x_start"].isna() | events["y_start"].isna())).sum()
    results.append(_res("events.located_types_have_start", "error", int(located.sum()),
                        miss_start))
    end_needed = events["event_type"].isin(c.END_LOCATED_EVENT_TYPES)
    miss_end = (end_needed & (events["x_end"].isna() | events["y_end"].isna())).sum()
    results.append(_res("events.end_types_have_end", "error", int(end_needed.sum()), miss_end))

    dims = matches[["match_id", "field_length_m", "field_width_m"]]
    m = events.merge(dims, on="match_id", how="left")
    tol = 1.0
    out = pd.Series(False, index=m.index)
    for xcol, ycol in (("x_start", "y_start"), ("x_end", "y_end")):
        out |= (m[xcol].abs() > m["field_length_m"] / 2 + tol)
        out |= (m[ycol].abs() > m["field_width_m"] / 2 + tol)
    results.append(_res("events.coordinates_within_surface", "error",
                        int(m[["x_start", "x_end"]].notna().any(axis=1).sum()), out.sum()))
    return results


def check_passes(events: pd.DataFrame, appearances: pd.DataFrame) -> list[CheckResult]:
    results = []
    passes = events[events["event_type"] == "pass"]
    complete = passes[passes["outcome"] == "complete"]
    results.append(_res("passes.complete_have_recipient", "error", len(complete),
                        complete["recipient_id"].isna().sum()))
    self_pass = (complete["recipient_id"] == complete["player_id"]).sum()
    results.append(_res("passes.recipient_not_passer", "error", len(complete), self_pass))
    rec = complete.dropna(subset=["recipient_id"])[["match_id", "team_id", "recipient_id"]]
    rec = rec.drop_duplicates().rename(columns={"recipient_id": "player_id"})
    app = appearances[["match_id", "team_id", "player_id"]].drop_duplicates()
    joined = rec.merge(app, how="left", on=["match_id", "team_id", "player_id"], indicator=True)
    results.append(_res("passes.recipient_on_passing_team", "error", len(rec),
                        (joined["_merge"] == "left_only").sum()))
    per_match = passes.groupby("match_id").size()
    results.append(_res("passes.min_100_per_match", "warn", len(per_match),
                        (per_match < 100).sum()))
    return results


def check_possessions(events: pd.DataFrame) -> list[CheckResult]:
    results = []
    has = events.dropna(subset=["possession_id"])
    results.append(_res("possession.id_present", "warn", len(events),
                        events["possession_id"].isna().sum()))
    teams = has.groupby(["match_id", "possession_id"])["possession_team_id"].nunique()
    results.append(_res("possession.team_constant", "error", len(teams), (teams > 1).sum()))
    ordered = has.sort_values(["match_id", "event_index"], kind="stable")
    back = (ordered.groupby("match_id")["possession_id"].diff().dropna() < 0).sum()
    results.append(_res(
        "possession.id_nondecreasing", "warn", len(ordered), back,
        "Source quirk: a trailing event (for example a reception) can be logged after the "
        "next possession starts. Group by possession_id; do not assume contiguous runs.",
    ))
    return results


def check_minutes(matches: pd.DataFrame, events: pd.DataFrame, appearances: pd.DataFrame
                  ) -> list[CheckResult]:
    results = []
    dur = match_durations_s(events).rename("duration_s") / 60.0
    a = appearances.merge(dur, left_on="match_id", right_index=True, how="left")
    bad = ((a["minutes_played"] < 0) | (a["minutes_played"] > a["duration_s"] + 1.0)).sum()
    results.append(_res("appearances.minutes_in_range", "error", len(a), bad))
    starters = a[a["started"]]
    per_team = starters.groupby(["match_id", "team_id"]).size()
    results.append(_res("appearances.eleven_starters", "error", len(per_team),
                        (per_team != 11).sum()))
    totals = a.groupby(["match_id", "team_id"]).agg(
        total=("minutes_played", "sum"), duration=("duration_s", "first")
    )
    signed = (totals["total"] - 11 * totals["duration"]) / (11 * totals["duration"])
    results.append(_res("appearances.team_minutes_not_above_11_x_duration", "error",
                        len(totals), (signed > 0.002).sum()))
    worst = float(signed.min()) if len(signed) else 0.0
    results.append(_res(
        "appearances.team_minutes_shortfall", "warn", len(totals), (signed < -0.003).sum(),
        f"worst shortfall {worst:.3f}; expected only where a player was sent off",
    ))
    return results


def check_goals(matches: pd.DataFrame, events: pd.DataFrame) -> list[CheckResult]:
    reg = events[events["period"] <= 4]
    shot_goals = reg[(reg["event_type"] == "shot") & (reg["outcome"] == "goal")]
    own = reg[(reg["event_type"] == "other") & (reg["event_subtype"] == "Own Goal For")]
    credited = pd.concat([shot_goals, own]).groupby(["match_id", "team_id"]).size()
    rows = []
    for r in matches.itertuples(index=False):
        for team_id, score in ((r.home_team_id, r.home_score), (r.away_team_id, r.away_score)):
            got = int(credited.get((r.match_id, team_id), 0))
            rows.append(pd.isna(score) or got != int(score))
    mism = int(np.sum(rows))
    return [_res("matches.goals_match_score", "error", len(rows), mism)]


# ------------------------------------------------------------------- entrypoint
def validate_tables(
    matches: pd.DataFrame, events: pd.DataFrame, appearances: pd.DataFrame
) -> ValidationReport:
    """Run every check and return a report."""
    tables = {"matches": matches, "events": events, "appearances": appearances}
    results = check_schema(tables)
    if any(not r.passed and r.name.endswith(("columns_present", "dtypes")) and r.severity == "error"
           for r in results):
        return ValidationReport(results)  # later checks assume the schema is intact
    steps: list[Callable[[], list[CheckResult]]] = [
        lambda: check_event_ordering(events),
        lambda: check_referential(matches, events, appearances),
        lambda: check_coordinates(matches, events),
        lambda: check_passes(events, appearances),
        lambda: check_possessions(events),
        lambda: check_minutes(matches, events, appearances),
        lambda: check_goals(matches, events),
    ]
    for step in steps:
        results.extend(step())
    return ValidationReport(results)
