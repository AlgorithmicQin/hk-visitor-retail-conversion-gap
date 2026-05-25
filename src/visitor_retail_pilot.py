"""Run the visitor-retail recovery pilot without hotel inputs."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
BASELINE_YEARS = (2018, 2019)


def month_start(series: pd.Series) -> pd.Series:
    """Convert YYYYMM period strings to month-start timestamps."""
    return pd.to_datetime(series.astype(str), format="%Y%m").dt.to_period("M").dt.to_timestamp()


def clean_category(value: object) -> str:
    """Normalize C&SD category labels while preserving category meaning."""
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Total"


def add_recovery_index(
    df: pd.DataFrame,
    value_col: str,
    *,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Add a 2018-2019 average equals 100 recovery index."""
    result = df.copy()
    result[value_col] = pd.to_numeric(result[value_col], errors="coerce")
    baseline_mask = result["month"].dt.year.between(*BASELINE_YEARS)

    if group_cols:
        baseline = (
            result.loc[baseline_mask]
            .groupby(group_cols, dropna=False)[value_col]
            .mean()
            .rename("baseline")
            .reset_index()
        )
        result = result.merge(baseline, on=group_cols, how="left")
    else:
        result["baseline"] = result.loc[baseline_mask, value_col].mean()

    invalid_baseline = result["baseline"].isna() | (result["baseline"] == 0)
    if invalid_baseline.any():
        keys = group_cols or ["Month"]
        bad = result.loc[invalid_baseline, keys].drop_duplicates().head(20)
        raise ValueError(f"Invalid baseline for {value_col}: {bad.to_dict(orient='records')}")

    result["recovery_index"] = result[value_col] / result["baseline"] * 100
    return result.drop(columns=["baseline"])


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load normalized visitor and retail CSV files."""
    visitors = pd.read_csv(RAW_DIR / "visitor_arrivals.csv")
    visitors["month"] = month_start(visitors["Month"])
    visitors = visitors.rename(columns={"Total arrivals": "visitor_arrivals"})
    visitors = visitors[["Month", "month", "visitor_arrivals"]].sort_values("month")

    retail = pd.read_csv(RAW_DIR / "retail_sales.csv")
    retail["month"] = month_start(retail["Month"])
    retail["retail_category"] = retail["Retail category"].map(clean_category)
    retail = retail.rename(columns={"Sales value": "retail_sales_value"})
    retail = retail[["Month", "month", "retail_category", "retail_sales_value"]]
    retail = retail.sort_values(["month", "retail_category"])
    return visitors, retail


def build_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build pilot tables."""
    visitors, retail = load_inputs()

    visitors_indexed = add_recovery_index(visitors, "visitor_arrivals")
    visitors_indexed = visitors_indexed.rename(columns={"recovery_index": "visitor_recovery_index"})

    category_recovery = add_recovery_index(
        retail,
        "retail_sales_value",
        group_cols=["retail_category"],
    )
    category_recovery = category_recovery.rename(columns={"recovery_index": "retail_recovery_index"})
    category_recovery = category_recovery.merge(
        visitors_indexed[["month", "visitor_recovery_index"]],
        on="month",
        how="left",
    )
    category_recovery["visitor_retail_conversion_gap"] = (
        category_recovery["retail_recovery_index"] - category_recovery["visitor_recovery_index"]
    )
    category_recovery = category_recovery[
        [
            "Month",
            "month",
            "retail_category",
            "retail_sales_value",
            "retail_recovery_index",
            "visitor_recovery_index",
            "visitor_retail_conversion_gap",
        ]
    ].sort_values(["month", "retail_category"])

    retail_total = category_recovery.loc[category_recovery["retail_category"] == "Total"].copy()
    if retail_total.empty:
        raise ValueError('Retail category "Total" was not found.')

    master = visitors_indexed.merge(
        retail_total[
            ["month", "retail_sales_value", "retail_recovery_index", "visitor_retail_conversion_gap"]
        ],
        on="month",
        how="inner",
    )
    master = master.rename(
        columns={
            "retail_sales_value": "total_retail_sales_value",
            "retail_recovery_index": "total_retail_recovery_index",
            "visitor_retail_conversion_gap": "total_retail_vs_visitor_gap",
        }
    )
    master = master[
        [
            "Month",
            "month",
            "visitor_arrivals",
            "total_retail_sales_value",
            "visitor_recovery_index",
            "total_retail_recovery_index",
            "total_retail_vs_visitor_gap",
        ]
    ].sort_values("month")

    latest_month = category_recovery["month"].max()
    summary = category_recovery.loc[category_recovery["month"] == latest_month].copy()
    post_recovery = category_recovery.loc[category_recovery["month"] >= pd.Timestamp("2023-01-01")]
    mean_gap = (
        post_recovery.groupby("retail_category")["visitor_retail_conversion_gap"]
        .mean()
        .rename("mean_gap_2023_to_latest")
    )
    summary = summary.merge(mean_gap, on="retail_category", how="left")
    summary["abs_latest_gap"] = summary["visitor_retail_conversion_gap"].abs()
    summary = summary.rename(
        columns={
            "retail_recovery_index": "latest_retail_recovery_index",
            "visitor_recovery_index": "latest_visitor_recovery_index",
            "visitor_retail_conversion_gap": "latest_conversion_gap",
        }
    )
    summary["latest_month"] = latest_month.strftime("%Y%m")
    summary = summary[
        [
            "latest_month",
            "retail_category",
            "retail_sales_value",
            "latest_visitor_recovery_index",
            "latest_retail_recovery_index",
            "latest_conversion_gap",
            "abs_latest_gap",
            "mean_gap_2023_to_latest",
        ]
    ].sort_values("latest_conversion_gap", ascending=False)

    return master, category_recovery, summary


def save_tables(master: pd.DataFrame, category_recovery: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Save pilot tables."""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    master.to_csv(TABLE_DIR / "master_monthly_panel.csv", index=False)
    category_recovery.to_csv(TABLE_DIR / "retail_category_recovery.csv", index=False)
    summary.to_csv(TABLE_DIR / "conversion_gap_summary.csv", index=False)


def save_figures(master: pd.DataFrame, category_recovery: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Save pilot figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(master["month"], master["visitor_recovery_index"], label="Visitor arrivals", linewidth=2.2)
    ax.plot(master["month"], master["total_retail_recovery_index"], label="Total retail sales", linewidth=2.2)
    ax.axhline(100, color="black", linewidth=1, alpha=0.45)
    ax.set_title("Visitor vs total retail recovery")
    ax.set_xlabel("Month")
    ax.set_ylabel("Recovery index, 2018-2019 average = 100")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "visitor_vs_total_retail_recovery.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 7))
    for category, group in category_recovery.groupby("retail_category"):
        is_total = category == "Total"
        ax.plot(
            group["month"],
            group["retail_recovery_index"],
            label=category,
            linewidth=2.4 if is_total else 0.9,
            alpha=1 if is_total else 0.45,
            color="black" if is_total else None,
        )
    ax.axhline(100, color="black", linewidth=1, alpha=0.35)
    ax.set_title("Retail category recovery indices")
    ax.set_xlabel("Month")
    ax.set_ylabel("Recovery index, 2018-2019 average = 100")
    ax.grid(True, alpha=0.22)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "category_recovery_indices.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    latest_month = summary["latest_month"].iloc[0]
    plot_summary = summary.sort_values("latest_conversion_gap")
    fig, ax = plt.subplots(figsize=(11, max(6, 0.28 * len(plot_summary))))
    colors = ["#b65f5f" if value < 0 else "#4d7c78" for value in plot_summary["latest_conversion_gap"]]
    ax.barh(plot_summary["retail_category"], plot_summary["latest_conversion_gap"], color=colors)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title(f"Category conversion gap vs visitors, {latest_month}")
    ax.set_xlabel("Retail recovery index minus visitor recovery index")
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "category_conversion_gap_latest.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    master, category_recovery, summary = build_outputs()
    save_tables(master, category_recovery, summary)
    save_figures(master, category_recovery, summary)

    latest_month = summary["latest_month"].iloc[0]
    latest_total_gap = master.loc[master["Month"].astype(str) == latest_month, "total_retail_vs_visitor_gap"].iloc[0]
    print("SUCCESS visitor-retail pilot completed")
    print(f"coverage={master['Month'].min()} to {master['Month'].max()}")
    print(f"master_rows={len(master)}")
    print(f"category_rows={len(category_recovery)}")
    print(f"retail_categories={category_recovery['retail_category'].nunique()}")
    print(f"latest_month={latest_month}")
    print(f"latest_total_gap={latest_total_gap}")
    print("\nTop positive latest gaps:")
    print(
        summary.head(8)[
            [
                "retail_category",
                "latest_conversion_gap",
                "latest_retail_recovery_index",
                "latest_visitor_recovery_index",
            ]
        ].to_string(index=False)
    )
    print("\nClosest to visitor recovery latest:")
    print(
        summary.sort_values("abs_latest_gap").head(8)[
            [
                "retail_category",
                "latest_conversion_gap",
                "latest_retail_recovery_index",
                "latest_visitor_recovery_index",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()

