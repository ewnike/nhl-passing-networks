"""Helpers to coerce DataFrames to the canonical column order and dtypes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from possnet.schema.contract import TABLES


def coerce_frame(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Return ``df`` restricted to the contract columns, in order, with contract dtypes.

    Raises ``KeyError`` if a contract column is missing. Extra columns are dropped.
    Idempotent, so it is safe to call after reading Parquet (which may change the
    string dtype flavor).
    """
    columns = TABLES[table]
    missing = [c.name for c in columns if c.name not in df.columns]
    if missing:
        raise KeyError(f"{table}: missing contract columns {missing}")
    out = df[[c.name for c in columns]].copy()
    for col in columns:
        series = out[col.name]
        if col.dtype == "string":
            out[col.name] = series.astype("string")
        elif col.dtype == "Int64":
            out[col.name] = pd.to_numeric(series, errors="coerce").astype("Int64")
        elif col.dtype == "float64":
            out[col.name] = pd.to_numeric(series, errors="coerce").astype("float64")
        elif col.dtype == "boolean":
            out[col.name] = series.astype("boolean")
        else:  # pragma: no cover - guards future contract edits
            raise ValueError(f"Unsupported dtype {col.dtype} for {table}.{col.name}")
    return out.reset_index(drop=True)


def read_table(path: Path, table: str) -> pd.DataFrame:
    """Read a canonical Parquet table and coerce it to the contract."""
    return coerce_frame(pd.read_parquet(path), table)
