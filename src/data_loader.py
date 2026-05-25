"""Data loading utilities for the Hong Kong visitor conversion pilot."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd


MONTH_COLUMN = "month"
RAW_FILE_EXTENSIONS = (".csv", ".xlsx", ".xls")


def standardize_month(values: pd.Series | Iterable[object]) -> pd.Series:
    """Convert month-like values to month-start timestamps."""
    series = pd.Series(values)
    parsed = pd.to_datetime(series, errors="coerce")

    if parsed.isna().any():
        alternate = pd.to_datetime(series.astype(str), format="%Y%m", errors="coerce")
        parsed = parsed.fillna(alternate)

    if parsed.isna().any():
        bad_values = series[parsed.isna()].dropna().unique()[:10]
        raise ValueError(f"Unable to parse month values: {bad_values}")

    return parsed.dt.to_period("M").dt.to_timestamp()


def read_tabular_file(path: str | Path, **read_kwargs) -> pd.DataFrame:
    """Read a CSV or Excel file without applying source-specific assumptions."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, **read_kwargs)
    if suffix in {".xls", ".xlsx", ".xlsm"}:
        return pd.read_excel(path, **read_kwargs)

    raise ValueError(f"Unsupported file type for {path}. Use CSV or Excel.")


def find_raw_file_by_stem(
    raw_dir: str | Path,
    stem: str,
    *,
    extensions: Iterable[str] = RAW_FILE_EXTENSIONS,
) -> Path:
    """Find the first raw file matching a stem and supported extension."""
    raw_dir = Path(raw_dir)
    for extension in extensions:
        path = raw_dir / f"{stem}{extension}"
        if path.exists():
            return path

    expected = ", ".join(f"{stem}{extension}" for extension in extensions)
    raise FileNotFoundError(f"No raw file found for {stem}. Expected one of: {expected}")


def load_monthly_dataset(
    path: str | Path,
    column_map: Mapping[str, str],
    required_columns: Iterable[str],
    *,
    value_columns: Iterable[str] | None = None,
    **read_kwargs,
) -> pd.DataFrame:
    """Load a raw monthly dataset and apply explicit column mapping.

    Args:
        path: Raw CSV or Excel file.
        column_map: Mapping from raw source columns to standard pilot columns.
        required_columns: Standard columns required after renaming.
        value_columns: Numeric columns to coerce after mapping. Defaults to all
            required columns except ``month``.
        read_kwargs: Extra keyword arguments passed to pandas.
    """
    raw = read_tabular_file(path, **read_kwargs)
    required = list(required_columns)
    required_raw_columns = {
        raw_col for raw_col, standard_col in column_map.items() if standard_col in required
    }
    missing_raw = required_raw_columns - set(raw.columns)
    if missing_raw:
        raise KeyError(f"Raw file is missing mapped columns: {sorted(missing_raw)}")

    available_map = {raw_col: standard_col for raw_col, standard_col in column_map.items() if raw_col in raw.columns}
    df = raw.rename(columns=available_map).copy()
    missing_standard = set(required) - set(df.columns)
    if missing_standard:
        raise KeyError(f"Mapped data is missing required columns: {sorted(missing_standard)}")

    df[MONTH_COLUMN] = standardize_month(df[MONTH_COLUMN])

    if value_columns is None:
        value_columns = [col for col in required if col != MONTH_COLUMN]
    for col in value_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    keep_columns = list(dict.fromkeys(required + [col for col in df.columns if col not in required]))
    return df[keep_columns].sort_values(MONTH_COLUMN).reset_index(drop=True)


def aggregate_monthly(
    df: pd.DataFrame,
    value_columns: Iterable[str],
    *,
    date_col: str = MONTH_COLUMN,
    agg: str = "sum",
) -> pd.DataFrame:
    """Aggregate a dataset to one row per month."""
    if date_col not in df.columns:
        raise KeyError(f"Missing date column: {date_col}")

    grouped = df.groupby(date_col, as_index=False)[list(value_columns)]
    if agg == "sum":
        return grouped.sum(min_count=1)
    if agg == "mean":
        return grouped.mean()

    raise ValueError("agg must be either 'sum' or 'mean'")


def merge_monthly_panel(
    visitors: pd.DataFrame,
    retail: pd.DataFrame,
    hotel: pd.DataFrame,
    *,
    date_col: str = MONTH_COLUMN,
    how: str = "outer",
) -> pd.DataFrame:
    """Merge visitor, retail, and hotel data into one monthly panel."""
    for name, df in {"visitors": visitors, "retail": retail, "hotel": hotel}.items():
        if date_col not in df.columns:
            raise KeyError(f"{name} data is missing '{date_col}'")
        if df[date_col].duplicated().any():
            duplicates = df.loc[df[date_col].duplicated(), date_col].dt.strftime("%Y-%m").unique()
            raise ValueError(f"{name} data has duplicate months: {duplicates[:10]}")

    panel = visitors.merge(retail, on=date_col, how=how).merge(hotel, on=date_col, how=how)
    return panel.sort_values(date_col).reset_index(drop=True)


def save_processed(df: pd.DataFrame, path: str | Path) -> None:
    """Save a processed table, creating parent directories if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
