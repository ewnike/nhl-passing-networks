"""Render the data contract to Markdown (docs/data_contract.md)."""

from __future__ import annotations

from possnet.schema import contract as c


def _table_md(name: str, columns: tuple[c.Column, ...], blurb: str) -> str:
    lines = [f"## Table: {name}", "", blurb, "",
             "| Column | Type | Null allowed | Allowed values | Description |",
             "|---|---|---|---|---|"]
    for col in columns:
        allowed = ", ".join(col.allowed) if col.allowed else ""
        lines.append(
            f"| `{col.name}` | {col.dtype} | {'yes' if col.nullable else 'no'} "
            f"| {allowed} | {col.description} |"
        )
    return "\n".join(lines) + "\n"


def render_contract_markdown() -> str:
    """Return the full contract document as Markdown."""
    parts = [
        "# Canonical event data contract",
        "",
        "This file is generated from `src/possnet/schema/contract.py`. Do not edit it by "
        "hand. Run `python scripts/00_render_contract.py` after changing the contract.",
        "",
        "Any new data source (hockey or otherwise) is supported by writing an adapter "
        "that produces these three tables and passes `scripts/03_validate.py`. "
        "Nothing downstream of the adapter may depend on a provider specific column.",
        "",
        "## Coordinate convention",
        "",
        c.COORDINATE_CONVENTION,
        "",
        _table_md("matches", c.MATCHES_COLUMNS, "One row per match."),
        _table_md("events", c.EVENTS_COLUMNS,
                  "One row per event, sorted by `match_id`, `event_index`."),
        _table_md("appearances", c.APPEARANCES_COLUMNS,
                  "One row per player per match, including unused substitutes."),
        "## Semantic rules checked by the validator",
        "",
        *[f"* {r}" for r in c.RULES],
        "",
        "## Notes for a hockey adapter",
        "",
        *[f"* {r}" for r in c.HOCKEY_MAPPING_NOTES],
        "",
    ]
    return "\n".join(parts)
