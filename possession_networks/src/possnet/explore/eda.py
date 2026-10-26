"""Exploratory summaries and figures for the canonical tables (step 4b)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from possnet.validate.checks import match_durations_s
from possnet.viz.pitch import (
    ACCENT,
    HALF_L,
    HALF_W,
    INK,
    MUTED,
    add_attribution,
    draw_pitch,
    save_figure,
    style_axes,
)

SEQUENTIAL = LinearSegmentedColormap.from_list(
    "blue_seq", ["#eef4fd", "#9dbff0", "#2a6fdb", "#123a82"]
)


def key_facts(matches: pd.DataFrame, events: pd.DataFrame, appearances: pd.DataFrame) -> dict:
    dur = match_durations_s(events) / 60.0
    return {
        "competition": f"{matches['competition_name'].iloc[0]} {matches['season_name'].iloc[0]}",
        "matches": int(len(matches)),
        "teams": int(pd.concat([matches.home_team_id, matches.away_team_id]).nunique()),
        "players": int(appearances["player_id"].nunique()),
        "events": int(len(events)),
        "passes": int((events.event_type == "pass").sum()),
        "shots": int((events.event_type == "shot").sum()),
        "date_min": str(matches["match_date"].min()),
        "date_max": str(matches["match_date"].max()),
        "median_match_minutes": round(float(dur.median()), 1),
        "data_versions": sorted(matches["data_version"].dropna().unique().tolist()),
    }


def event_counts(events: pd.DataFrame) -> pd.DataFrame:
    counts = events["event_type"].value_counts().rename_axis("event_type").reset_index(name="n")
    counts["share"] = counts["n"] / counts["n"].sum()
    return counts


def missingness(events: pd.DataFrame) -> pd.DataFrame:
    """Share of nulls per column, overall (null is legitimate for many columns)."""
    out = events.isna().mean().rename("null_share").rename_axis("column").reset_index()
    return out.sort_values("null_share", ascending=False)


def team_match_summary(events: pd.DataFrame) -> pd.DataFrame:
    passes = events[events.event_type == "pass"]
    grp = passes.groupby(["match_id", "team_id", "team_name"])
    out = grp.agg(passes=("event_id", "size"),
                  complete=("outcome", lambda s: (s == "complete").sum())).reset_index()
    out["completion_rate"] = out["complete"] / out["passes"]
    shots = events[events.event_type == "shot"].groupby(["match_id", "team_id"]).size()
    out = out.merge(shots.rename("shots").reset_index(), on=["match_id", "team_id"], how="left")
    out["shots"] = out["shots"].fillna(0).astype(int)
    return out


def possession_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Per possession length in events and in passes, as a preview of step 6."""
    has = events.dropna(subset=["possession_id"])
    grp = has.groupby(["match_id", "possession_id", "possession_team_id"])
    out = grp.agg(
        n_events=("event_id", "size"),
        n_passes=("event_type", lambda s: (s == "pass").sum()),
        has_shot=("event_type", lambda s: (s == "shot").any()),
        play_pattern=("play_pattern", "first"),
    ).reset_index()
    return out


def player_minutes_summary(appearances: pd.DataFrame) -> pd.DataFrame:
    played = appearances[appearances.minutes_played > 0]
    per_player = played.groupby("player_id")["minutes_played"].sum()
    thresholds = [0, 90, 450, 900, 1800]
    rows = [{"min_season_minutes": t, "players": int((per_player >= t).sum())} for t in thresholds]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- figures
def fig_event_mix(counts: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    data = counts.sort_values("n")
    ax.barh(data["event_type"], data["n"], color=ACCENT, height=0.6)
    for y, (n, share) in enumerate(zip(data["n"], data["share"], strict=True)):
        ax.text(n, y, f"  {share:.1%}", va="center", fontsize=8, color=MUTED)
    ax.set_xlabel("Events", color=MUTED)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_title("Event mix in the canonical table", loc="left", color=INK, fontsize=12)
    style_axes(ax)
    ax.grid(axis="x", color="#e5e7eb")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, data["n"].max() * 1.12)
    add_attribution(fig)
    save_figure(fig, out)


def fig_pass_density(events: pd.DataFrame, out: Path) -> None:
    passes = events[(events.event_type == "pass") & events.x_start.notna()
                    & ~events.is_dead_ball]
    fig, ax = plt.subplots(figsize=(8, 5.4))
    hb = ax.hexbin(passes.x_start, passes.y_start, gridsize=(30, 20), mincnt=1,
                   extent=(-HALF_L, HALF_L, -HALF_W, HALF_W), cmap=SEQUENTIAL, linewidths=0.2,
                   edgecolors="white")
    draw_pitch(ax)
    ax.annotate("", xy=(HALF_L - 6, -HALF_W - 6), xytext=(HALF_L - 36, -HALF_W - 6),
                arrowprops={"arrowstyle": "->", "color": MUTED}, annotation_clip=False)
    ax.text(HALF_L - 21, -HALF_W - 9, "attacking direction", ha="center", fontsize=8,
            color=MUTED)
    cbar = fig.colorbar(hb, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Passes started", color=MUTED)
    cbar.outline.set_visible(False)
    ax.set_title("Where open play passes start (set pieces excluded, attacking left to right)",
                 loc="left", color=INK, fontsize=11)
    add_attribution(fig)
    save_figure(fig, out)


def fig_passes_per_team_match(team_matches: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    ax = axes[0]
    ax.hist(team_matches["passes"], bins=30, color=ACCENT, edgecolor="white", linewidth=0.5)
    med = team_matches["passes"].median()
    ax.axvline(med, color=INK, lw=1)
    ax.text(med, ax.get_ylim()[1] * 0.95, f" median {med:.0f}", fontsize=8, color=INK, va="top")
    ax.set_xlabel("Passes per team per match", color=MUTED)
    ax.set_ylabel("Team matches", color=MUTED)
    style_axes(ax)
    ax = axes[1]
    ax.scatter(team_matches["passes"], team_matches["completion_rate"], s=10, color=ACCENT,
               alpha=0.5, linewidths=0)
    r = np.corrcoef(team_matches["passes"], team_matches["completion_rate"])[0, 1]
    ax.set_xlabel("Passes per team per match", color=MUTED)
    ax.set_ylabel("Completion rate", color=MUTED)
    ax.text(0.03, 0.05, f"r = {r:.2f}", transform=ax.transAxes, fontsize=9, color=INK)
    style_axes(ax)
    fig.suptitle("Pass volume and accuracy", x=0.01, ha="left", color=INK, fontsize=12)
    fig.tight_layout()
    add_attribution(fig)
    save_figure(fig, out)
