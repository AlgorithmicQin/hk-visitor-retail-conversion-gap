"""Recovery index and conversion gap calculations."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def calculate_recovery_indices(
    df: pd.DataFrame,
    value_columns: Iterable[str],
    *,
    date_col: str = "month",
    baseline_years: tuple[int, int] = (2018, 2019),
    suffix: str = "_recovery_index",
) -> pd.DataFrame:
    """Calculate recovery indices where the baseline-year average equals 100."""
    if date_col not in df.columns:
        raise KeyError(f"Missing date column: {date_col}")

    result = df.copy()
    dates = pd.to_datetime(result[date_col])
    baseline_mask = dates.dt.year.between(baseline_years[0], baseline_years[1])

    if not baseline_mask.any():
        raise ValueError(f"No baseline rows found for {baseline_years[0]}-{baseline_years[1]}")

    for col in value_columns:
        if col not in result.columns:
            raise KeyError(f"Missing value column: {col}")

        baseline = pd.to_numeric(result.loc[baseline_mask, col], errors="coerce").mean()
        if pd.isna(baseline) or baseline == 0:
            raise ValueError(f"Cannot build recovery index for {col}; invalid baseline: {baseline}")

        result[f"{col}{suffix}"] = pd.to_numeric(result[col], errors="coerce") / baseline * 100

    return result


def calculate_conversion_gaps(
    df: pd.DataFrame,
    *,
    visitor_index_col: str = "visitor_arrivals_recovery_index",
    retail_index_cols: Iterable[str] = ("retail_sales_value_recovery_index",),
    hotel_index_cols: Iterable[str] = (
        "hotel_occupancy_rate_recovery_index",
        "hotel_room_rate_recovery_index",
    ),
) -> pd.DataFrame:
    """Calculate outcome recovery minus visitor recovery gaps."""
    if visitor_index_col not in df.columns:
        raise KeyError(f"Missing visitor index column: {visitor_index_col}")

    result = df.copy()

    for col in list(retail_index_cols) + list(hotel_index_cols):
        if col not in result.columns:
            continue
        gap_name = col.replace("_recovery_index", "_vs_visitors_gap")
        result[gap_name] = result[col] - result[visitor_index_col]

    return result


def select_index_columns(df: pd.DataFrame) -> list[str]:
    """Return all recovery index columns in a panel."""
    return [col for col in df.columns if col.endswith("_recovery_index")]


def select_gap_columns(df: pd.DataFrame) -> list[str]:
    """Return all conversion gap columns in a panel."""
    return [col for col in df.columns if col.endswith("_vs_visitors_gap")]

