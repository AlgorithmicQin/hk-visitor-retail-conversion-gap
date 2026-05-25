"""Preprocess C&SD API JSON payloads into pilot-ready CSV files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

VISITOR_INPUT = RAW_DIR / "visitor_arrivals_real.csv"
VISITOR_OUTPUT = RAW_DIR / "visitor_arrivals.csv"
RETAIL_INPUT = RAW_DIR / "retail_sales_real.csv"
RETAIL_OUTPUT = RAW_DIR / "retail_sales.csv"


def load_censd_json(path: Path) -> list[dict]:
    """Load a C&SD API response saved with any extension."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    status = payload.get("header", {}).get("status", {})
    if status.get("name") != "Success":
        raise ValueError(f"C&SD response was not successful for {path}: {status}")

    data = payload.get("dataSet")
    if not isinstance(data, list):
        raise ValueError(f"C&SD response has no dataSet list: {path}")
    return data


def validate_monthly_coverage(df: pd.DataFrame, month_col: str, label: str) -> tuple[str, str]:
    """Validate that output has continuous monthly coverage from 201801."""
    months = sorted(df[month_col].astype(str).unique())
    if not months:
        raise ValueError(f"{label} output has no monthly rows.")

    start, end = months[0], months[-1]
    expected = pd.period_range(start="2018-01", end=pd.Period(end, freq="M"), freq="M")
    expected_months = [period.strftime("%Y%m") for period in expected]
    missing = sorted(set(expected_months) - set(months))

    if start != "201801":
        print(f"WARNING: {label} coverage starts at {start}, expected 201801.")
    if missing:
        print(f"WARNING: {label} is missing monthly periods: {missing[:12]}")

    return start, end


def preprocess_visitors() -> pd.DataFrame:
    """Extract monthly total visitor arrivals."""
    records = load_censd_json(VISITOR_INPUT)
    rows = [
        {
            "Month": str(record["period"]),
            "Total arrivals": pd.to_numeric(record.get("figure"), errors="coerce"),
        }
        for record in records
        if record.get("freq") == "M"
        and (record.get("REGIONDesc") == "Total" or record.get("REGION") == "")
        and record.get("sv") == "VIS_ARR"
    ]

    df = pd.DataFrame(rows, columns=["Month", "Total arrivals"])
    df = df.sort_values("Month").reset_index(drop=True)
    validate_monthly_coverage(df, "Month", "Visitor arrivals")
    df.to_csv(VISITOR_OUTPUT, index=False)
    return df


def preprocess_retail() -> pd.DataFrame:
    """Extract monthly retail sales value by outlet type, including total."""
    records = load_censd_json(RETAIL_INPUT)
    rows = [
        {
            "Month": str(record["period"]),
            "Retail category": record.get("OUTLET_TYPEDesc"),
            "Sales value": pd.to_numeric(record.get("figure"), errors="coerce"),
        }
        for record in records
        if record.get("freq") == "M" and record.get("sv") == "VAL_RS"
    ]

    df = pd.DataFrame(rows, columns=["Month", "Retail category", "Sales value"])
    df["Retail category"] = df["Retail category"].fillna("")
    df = df.sort_values(["Month", "Retail category"]).reset_index(drop=True)
    validate_monthly_coverage(df, "Month", "Retail sales")
    df.to_csv(RETAIL_OUTPUT, index=False)
    return df


def print_summary(label: str, path: Path, df: pd.DataFrame) -> None:
    """Print a compact preprocessing summary."""
    start, end = validate_monthly_coverage(df, "Month", label)
    print(f"\n{label}")
    print(f"Output: {path}")
    print(f"Rows: {len(df)}")
    print(f"Coverage: {start} to {end}")
    print("First 10 rows:")
    print(df.head(10).to_string(index=False))


def main() -> None:
    visitors = preprocess_visitors()
    retail = preprocess_retail()
    print_summary("Visitor arrivals", VISITOR_OUTPUT, visitors)
    print_summary("Retail sales", RETAIL_OUTPUT, retail)


if __name__ == "__main__":
    main()

