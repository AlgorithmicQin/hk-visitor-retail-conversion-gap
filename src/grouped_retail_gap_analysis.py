"""Grouped retail category recovery and visitor-retail gap analysis."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yaml

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "retail_category_groups.yaml"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
RECOVERY_PATH = TABLE_DIR / "retail_category_recovery.csv"
DIAGNOSTICS_PATH = TABLE_DIR / "category_gap_diagnostics.csv"
BEHAVIORAL_GROUPS = {
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
}
BENCHMARK_GROUP = "benchmark_total"

def load_group_mapping() -> pd.DataFrame:
    """Load the manual category grouping file."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    rows = []
    for group_name, group_config in config["groups"].items():
        for item in group_config["categories"]:
            rows.append(
                {
                    "retail_group": group_name,
                    "retail_category": item["name"],
                    "group_note": item.get("note", ""),
                    "group_description": group_config.get("description", ""),
                    "excluded_from_behavioral_interpretation": bool(
                        group_config.get("excluded_from_behavioral_interpretation", False)
                    ),
                }
            )
    mapping = pd.DataFrame(rows)

    duplicates = mapping.loc[mapping["retail_category"].duplicated(), "retail_category"].tolist()
    if duplicates:
        raise ValueError(f"Categories assigned to multiple groups: {duplicates}")
    return mapping


def validate_mapping(recovery: pd.DataFrame, mapping: pd.DataFrame) -> None:
    """Ensure every category has exactly one group assignment."""
    data_categories = set(recovery["retail_category"].unique())
    mapped_categories = set(mapping["retail_category"])
    missing = sorted(data_categories - mapped_categories)
    extra = sorted(mapped_categories - data_categories)
    if missing:
        raise ValueError(f"Categories missing from group mapping: {missing}")
    if extra:
        raise ValueError(f"Mapped categories not present in recovery data: {extra}")


def build_group_recovery(recovery: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """Aggregate category recovery paths into group-level indices."""
    df = recovery.merge(mapping, on="retail_category", how="left")
    validate_mapping(recovery, mapping)

    grouped = (
        df.groupby(["Month", "month", "retail_group"], as_index=False)
        .agg(
            group_retail_sales_value=("retail_sales_value", "sum"),
            visitor_recovery_index=("visitor_recovery_index", "first"),
        )
    )
    grouped["month"] = pd.to_datetime(grouped["month"])
    baseline_mask = grouped["month"].dt.year.between(2018, 2019)
    baseline = (
        grouped.loc[baseline_mask]
        .groupby("retail_group")["group_retail_sales_value"]
        .mean()
        .rename("baseline")
        .reset_index()
    )
    grouped = grouped.merge(baseline, on="retail_group", how="left")
    if grouped["baseline"].isna().any() or (grouped["baseline"] == 0).any():
        bad = grouped.loc[grouped["baseline"].isna() | (grouped["baseline"] == 0), "retail_group"].unique()
        raise ValueError(f"Invalid group baseline for: {sorted(bad)}")

    grouped["group_recovery_index"] = grouped["group_retail_sales_value"] / grouped["baseline"] * 100
    grouped["group_conversion_gap"] = grouped["group_recovery_index"] - grouped["visitor_recovery_index"]
    return grouped.drop(columns=["baseline"]).sort_values(["month", "retail_group"])


def summarize_groups(group_recovery: pd.DataFrame) -> pd.DataFrame:
    """Summarize reopening-period group gaps."""
    latest_month = group_recovery["month"].max()
    reopening = group_recovery.loc[group_recovery["month"] >= pd.Timestamp("2023-01-01")].copy()
    summary = (
        reopening.groupby("retail_group")
        .agg(
            reopening_avg_gap=("group_conversion_gap", "mean"),
            reopening_median_gap=("group_conversion_gap", "median"),
            reopening_gap_std_dev=("group_conversion_gap", "std"),
            reopening_positive_months=("group_conversion_gap", lambda s: int((s > 0).sum())),
            reopening_negative_months=("group_conversion_gap", lambda s: int((s < 0).sum())),
            reopening_months=("group_conversion_gap", "count"),
            reopening_avg_group_recovery=("group_recovery_index", "mean"),
            reopening_avg_visitor_recovery=("visitor_recovery_index", "mean"),
        )
        .reset_index()
    )
    latest = group_recovery.loc[
        group_recovery["month"] == latest_month,
        ["retail_group", "group_conversion_gap", "group_recovery_index", "visitor_recovery_index"],
    ].rename(
        columns={
            "group_conversion_gap": "latest_gap",
            "group_recovery_index": "latest_group_recovery_index",
            "visitor_recovery_index": "latest_visitor_recovery_index",
        }
    )
    summary = summary.merge(latest, on="retail_group", how="left")
    summary["latest_month"] = latest_month.strftime("%Y%m")
    summary["is_benchmark"] = summary["retail_group"].eq(BENCHMARK_GROUP)
    return summary.sort_values(["is_benchmark", "reopening_avg_gap"])


def save_figures(group_recovery: pd.DataFrame) -> None:
    """Save group-level figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for group_name, group in group_recovery.groupby("retail_group"):
        is_benchmark = group_name == BENCHMARK_GROUP
        ax.plot(
            group["month"],
            group["group_recovery_index"],
            label=group_name,
            linewidth=2.2 if is_benchmark else 2,
            linestyle=":" if is_benchmark else "-",
            alpha=0.8 if is_benchmark else 1,
        )
    visitor = group_recovery[["month", "visitor_recovery_index"]].drop_duplicates()
    ax.plot(visitor["month"], visitor["visitor_recovery_index"], label="visitor_recovery", color="black", linestyle="--")
    ax.axhline(100, color="black", linewidth=1, alpha=0.35)
    ax.set_title("Retail group recovery paths")
    ax.set_xlabel("Month")
    ax.set_ylabel("Recovery index, 2018-2019 average = 100")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "retail_group_recovery_indices.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for group_name, group in group_recovery.groupby("retail_group"):
        is_benchmark = group_name == BENCHMARK_GROUP
        ax.plot(
            group["month"],
            group["group_conversion_gap"],
            label=group_name,
            linewidth=2.2 if is_benchmark else 2,
            linestyle=":" if is_benchmark else "-",
            alpha=0.8 if is_benchmark else 1,
        )
    ax.axhline(0, color="black", linewidth=1, alpha=0.55)
    ax.set_title("Retail group visitor-retail conversion mismatch")
    ax.set_xlabel("Month")
    ax.set_ylabel("Group recovery index minus visitor recovery index")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "retail_group_conversion_gap_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_markdown_summary(summary: pd.DataFrame, mapping: pd.DataFrame) -> None:
    """Write a short grouped-analysis markdown summary."""
    tourist = summary.loc[summary["retail_group"] == "tourist_sensitive_discretionary"].iloc[0]
    local = summary.loc[summary["retail_group"] == "local_daily_consumption"].iloc[0]
    durable = summary.loc[summary["retail_group"] == "durable_household"].iloc[0]
    behavioral_summary = summary.loc[~summary["is_benchmark"]].copy()
    residual_notes = mapping.loc[mapping["retail_group"] == "residual_other", ["retail_category", "group_note"]]

    lines = [
        "# Retail Group Gap Summary",
        "",
        "This grouped diagnostic compares category group recovery paths with visitor recovery. It describes visitor-retail alignment and conversion mismatch; it does not claim causality.",
        "",
        "## Reopening Average Gap",
        "",
    ]
    for _, row in behavioral_summary.iterrows():
        lines.append(f"- {row['retail_group']}: {row['reopening_avg_gap']:.1f} index points.")

    diff = tourist["reopening_avg_gap"] - local["reopening_avg_gap"]
    benchmark = summary.loc[summary["retail_group"] == BENCHMARK_GROUP].iloc[0]
    lines += [
        "",
        "Total retail is a benchmark, not a behavioral category. Group interpretation is based only on behavioral category groups.",
        f"- benchmark_total latest comparison gap: {benchmark['latest_gap']:.1f} index points.",
        "",
        "## Tourist-Sensitive Vs Local Daily",
        "",
        f"- Tourist-sensitive discretionary average reopening gap: {tourist['reopening_avg_gap']:.1f}.",
        f"- Local daily consumption average reopening gap: {local['reopening_avg_gap']:.1f}.",
        f"- Difference: {diff:.1f} index points.",
        "",
        "## Residual Category Warning",
        "",
        "Residual categories remain interpretively weak and should not drive the main thesis. They are included as a separate behavioral group because they are observed retail categories, but their composition is broad or overlapping.",
    ]
    for _, row in residual_notes.iterrows():
        note = f" {row['group_note']}" if row["group_note"] else ""
        lines.append(f"- {row['retail_category']}:{note}")

    lines += [
        "",
        "## Thesis Signal",
        "",
        "The grouped view strengthens the project thesis if the goal is to compare recovery paths by retail exposure type. The strongest mismatch is not simply total retail versus visitors; it appears in how grouped categories align differently with visitor recovery.",
        "",
        f"Durable/household average reopening gap: {durable['reopening_avg_gap']:.1f}. This group should be interpreted as a separate recovery path, not as a visitor-sensitive benchmark.",
    ]
    (TABLE_DIR / "retail_group_gap_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    recovery = pd.read_csv(RECOVERY_PATH)
    diagnostics = pd.read_csv(DIAGNOSTICS_PATH)
    mapping = load_group_mapping()
    validate_mapping(recovery, mapping)

    grouped = build_group_recovery(recovery, mapping)
    unexpected_groups = sorted(set(grouped["retail_group"]) - BEHAVIORAL_GROUPS - {BENCHMARK_GROUP})
    if unexpected_groups:
        raise ValueError(f"Unexpected retail groups: {unexpected_groups}")

    summary = summarize_groups(grouped)
    summary = summary.merge(
        mapping.groupby("retail_group")
        .agg(
            mapped_category_count=("retail_category", "size"),
            excluded_from_behavioral_interpretation=(
                "excluded_from_behavioral_interpretation",
                "max",
            ),
        )
        .reset_index(),
        on="retail_group",
        how="left",
    )
    summary = summary.sort_values(["excluded_from_behavioral_interpretation", "reopening_avg_gap"])

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(TABLE_DIR / "retail_group_recovery.csv", index=False)
    summary.to_csv(TABLE_DIR / "retail_group_gap_summary.csv", index=False)
    save_figures(grouped)
    write_markdown_summary(summary, mapping)

    tourist = summary.loc[summary["retail_group"] == "tourist_sensitive_discretionary", "reopening_avg_gap"].iloc[0]
    local = summary.loc[summary["retail_group"] == "local_daily_consumption", "reopening_avg_gap"].iloc[0]
    residual = mapping.loc[mapping["retail_group"] == "residual_other", "retail_category"].tolist()
    behavioral_summary = summary.loc[~summary["excluded_from_behavioral_interpretation"]]

    print("SUCCESS grouped retail gap analysis completed")
    print("Category group mapping:")
    for group_name, group in mapping.groupby("retail_group", sort=False):
        print(f"- {group_name}: {', '.join(group['retail_category'])}")
    print("\nAverage reopening gap by group:")
    print(
        behavioral_summary[
            ["retail_group", "reopening_avg_gap", "reopening_median_gap", "latest_gap"]
        ].to_string(index=False)
    )
    benchmark = summary.loc[summary["retail_group"] == BENCHMARK_GROUP]
    if not benchmark.empty:
        print("\nBenchmark total, excluded from behavioral interpretation:")
        print(benchmark[["retail_group", "reopening_avg_gap", "reopening_median_gap", "latest_gap"]].to_string(index=False))
    print(f"\nTourist-sensitive minus local-daily average gap: {tourist - local:.2f}")
    print(f"Residual categories flagged separately: {', '.join(residual)}")
    print("\nDiagnostics source categories:", diagnostics["retail_category"].nunique())
    print("\nOutputs:")
    for path in [
        TABLE_DIR / "retail_group_recovery.csv",
        TABLE_DIR / "retail_group_gap_summary.csv",
        TABLE_DIR / "retail_group_gap_summary.md",
        FIGURE_DIR / "retail_group_recovery_indices.png",
        FIGURE_DIR / "retail_group_conversion_gap_trends.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
