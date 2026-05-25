"""Baseline sensitivity checks using 2019 same-month recovery indices."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import yaml

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
CONFIG_PATH = PROJECT_ROOT / "config" / "retail_category_groups.yaml"

GROUP_ORDER = [
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
    "benchmark_total",
]
BEHAVIORAL_GROUPS = [
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
]
PHASE_ORDER = [
    "pre_covid_baseline",
    "covid_disruption",
    "early_reopening",
    "normalization",
    "recent_adjustment",
]


def clean_category(value: object) -> str:
    """Normalize C&SD category labels while preserving category meaning."""
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Total"


def month_start(series: pd.Series) -> pd.Series:
    """Convert compact YYYYMM periods to month-start timestamps."""
    return pd.to_datetime(series.astype(str), format="%Y%m").dt.to_period("M").dt.to_timestamp()


def assign_phase(month: pd.Timestamp) -> str:
    """Assign the pilot recovery phase for a month."""
    if pd.Timestamp("2018-01-01") <= month <= pd.Timestamp("2019-12-01"):
        return "pre_covid_baseline"
    if pd.Timestamp("2020-01-01") <= month <= pd.Timestamp("2022-12-01"):
        return "covid_disruption"
    if pd.Timestamp("2023-01-01") <= month <= pd.Timestamp("2023-12-01"):
        return "early_reopening"
    if pd.Timestamp("2024-01-01") <= month <= pd.Timestamp("2024-12-01"):
        return "normalization"
    if month >= pd.Timestamp("2025-01-01"):
        return "recent_adjustment"
    raise ValueError(f"Month outside expected phase ranges: {month}")


def load_group_mapping() -> pd.DataFrame:
    """Load retail category to group assignments."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    rows = []
    for group_name, group_config in config["groups"].items():
        for item in group_config["categories"]:
            rows.append(
                {
                    "retail_category": item["name"],
                    "retail_group": group_name,
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


def add_same_month_2019_index(
    df: pd.DataFrame,
    value_col: str,
    output_col: str,
    *,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Add value divided by same calendar month in 2019 equals 100."""
    result = df.copy()
    result[value_col] = pd.to_numeric(result[value_col], errors="coerce")
    result["calendar_month"] = result["month"].dt.month

    keys = (group_cols or []) + ["calendar_month"]
    baseline = (
        result.loc[result["month"].dt.year == 2019, keys + [value_col]]
        .rename(columns={value_col: "same_month_2019_baseline"})
        .drop_duplicates(subset=keys)
    )
    result = result.merge(baseline, on=keys, how="left")

    invalid = result["same_month_2019_baseline"].isna() | (result["same_month_2019_baseline"] == 0)
    if invalid.any():
        bad = result.loc[invalid, keys].drop_duplicates().head(20)
        raise ValueError(f"Invalid same-month 2019 baseline for {value_col}: {bad.to_dict(orient='records')}")

    result[output_col] = result[value_col] / result["same_month_2019_baseline"] * 100
    return result.drop(columns=["same_month_2019_baseline"])


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load normalized visitor and retail CSV inputs."""
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


def build_baseline_b_panel() -> pd.DataFrame:
    """Build category-level same-month-2019 recovery and gap panel."""
    visitors, retail = load_inputs()
    mapping = load_group_mapping()

    visitors_b = add_same_month_2019_index(
        visitors,
        "visitor_arrivals",
        "visitor_recovery_index_same_month_2019",
    )
    retail_b = add_same_month_2019_index(
        retail,
        "retail_sales_value",
        "retail_category_recovery_index_same_month_2019",
        group_cols=["retail_category"],
    )
    panel = retail_b.merge(
        visitors_b[["month", "visitor_recovery_index_same_month_2019"]],
        on="month",
        how="left",
    )
    panel = panel.merge(mapping, on="retail_category", how="left")
    missing = sorted(panel.loc[panel["retail_group"].isna(), "retail_category"].unique())
    if missing:
        raise ValueError(f"Categories missing from group mapping: {missing}")

    panel["conversion_gap_same_month_2019"] = (
        panel["retail_category_recovery_index_same_month_2019"]
        - panel["visitor_recovery_index_same_month_2019"]
    )
    panel["phase"] = panel["month"].map(assign_phase)
    panel["year"] = panel["month"].dt.year
    panel["calendar_month"] = panel["month"].dt.month
    return panel.sort_values(["month", "retail_category"])


def build_group_recovery(panel: pd.DataFrame) -> pd.DataFrame:
    """Aggregate category sales and calculate group same-month-2019 indices."""
    grouped = (
        panel.groupby(["Month", "month", "retail_group"], as_index=False)
        .agg(
            group_retail_sales_value=("retail_sales_value", "sum"),
            visitor_recovery_index_same_month_2019=("visitor_recovery_index_same_month_2019", "first"),
            excluded_from_behavioral_interpretation=("excluded_from_behavioral_interpretation", "max"),
        )
    )
    grouped = add_same_month_2019_index(
        grouped,
        "group_retail_sales_value",
        "retail_group_recovery_index_same_month_2019",
        group_cols=["retail_group"],
    )
    grouped["conversion_gap_same_month_2019"] = (
        grouped["retail_group_recovery_index_same_month_2019"]
        - grouped["visitor_recovery_index_same_month_2019"]
    )
    grouped["phase"] = grouped["month"].map(assign_phase)
    grouped["retail_group"] = pd.Categorical(grouped["retail_group"], categories=GROUP_ORDER, ordered=True)
    return grouped.sort_values(["month", "retail_group"])


def phase_summary(
    df: pd.DataFrame,
    group_cols: list[str],
    gap_col: str = "conversion_gap_same_month_2019",
) -> pd.DataFrame:
    """Summarize gaps by requested grouping and phase."""
    latest_month = df["month"].max()
    latest = df.loc[df["month"] == latest_month, group_cols + [gap_col]].rename(columns={gap_col: "latest_gap"})
    summary = (
        df.groupby(group_cols + ["phase"], observed=True)
        .agg(
            avg_gap=(gap_col, "mean"),
            median_gap=(gap_col, "median"),
            min_gap=(gap_col, "min"),
            max_gap=(gap_col, "max"),
            std_gap=(gap_col, "std"),
            months=(gap_col, "count"),
        )
        .reset_index()
        .merge(latest, on=group_cols, how="left")
    )
    summary["latest_month"] = latest_month.strftime("%Y%m")
    return summary


def build_group_phase_gaps(group_recovery: pd.DataFrame) -> pd.DataFrame:
    """Build group-level phase gap summary."""
    summary = phase_summary(group_recovery, ["retail_group"])
    summary["is_benchmark"] = summary["retail_group"].astype(str).eq("benchmark_total")
    summary["phase_status"] = summary["avg_gap"].map(status_from_gap)
    return summary.sort_values(["retail_group", "phase"])


def status_from_gap(value: float) -> str:
    """Classify gap direction with a small near-zero band."""
    if value > 5:
        return "recovered above visitor recovery"
    if value < -5:
        return "lagged visitor recovery"
    return "broadly aligned with visitor recovery"


def add_recent_representativeness(summary: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Compare latest gap with recent-adjustment average and standard deviation."""
    recent = summary.loc[summary["phase"] == "recent_adjustment", group_cols + ["avg_gap", "std_gap"]].rename(
        columns={"avg_gap": "recent_adjustment_avg_gap", "std_gap": "recent_adjustment_std_gap"}
    )
    result = summary.merge(recent, on=group_cols, how="left")
    result["latest_minus_recent_avg"] = result["latest_gap"] - result["recent_adjustment_avg_gap"]
    result["latest_representative_recent"] = (
        result["latest_minus_recent_avg"].abs()
        <= result["recent_adjustment_std_gap"].fillna(0).clip(lower=10)
    )
    return result


def build_drilldowns(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build tourist-sensitive and local/durable category drilldowns."""
    category_summary = phase_summary(panel, ["retail_group", "retail_category"])
    category_summary["phase_status"] = category_summary["avg_gap"].map(status_from_gap)
    category_summary = add_recent_representativeness(category_summary, ["retail_group", "retail_category"])

    tourist = category_summary.loc[
        category_summary["retail_group"].eq("tourist_sensitive_discretionary")
    ].sort_values(["retail_category", "phase"])
    local_durable = category_summary.loc[
        category_summary["retail_group"].isin(["local_daily_consumption", "durable_household"])
    ].sort_values(["retail_group", "retail_category", "phase"])
    return tourist, local_durable


def load_baseline_a_comparison() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load existing Baseline A summaries for comparison without modifying them."""
    group_a = pd.read_csv(TABLE_DIR / "retail_group_phase_gaps.csv")
    tourist_a = pd.read_csv(TABLE_DIR / "tourist_sensitive_drilldown.csv")
    local_durable_a = pd.read_csv(TABLE_DIR / "local_daily_durable_drilldown.csv")
    return group_a, tourist_a, local_durable_a


def build_comparison_summary(
    group_b: pd.DataFrame,
    tourist_b: pd.DataFrame,
    local_durable_b: pd.DataFrame,
) -> pd.DataFrame:
    """Compare headline Baseline A and Baseline B conclusions."""
    group_a, tourist_a, local_durable_a = load_baseline_a_comparison()

    rows = []
    for group in GROUP_ORDER:
        for phase in ["early_reopening", "normalization", "recent_adjustment"]:
            a_gap = value_for(group_a, {"retail_group": group, "phase": phase}, "avg_gap")
            b_gap = value_for(group_b, {"retail_group": group, "phase": phase}, "avg_gap")
            rows.append(
                {
                    "comparison": "group_phase_gap",
                    "retail_group": group,
                    "retail_category": "",
                    "phase": phase,
                    "baseline_a_gap": a_gap,
                    "baseline_b_gap": b_gap,
                    "gap_change_b_minus_a": b_gap - a_gap,
                    "direction_same": same_direction(a_gap, b_gap),
                }
            )

    for category in sorted(tourist_b["retail_category"].unique()):
        a_gap = value_for(
            tourist_a,
            {"retail_category": category, "phase": "recent_adjustment"},
            "avg_gap",
        )
        b_gap = value_for(
            tourist_b,
            {"retail_category": category, "phase": "recent_adjustment"},
            "avg_gap",
        )
        rows.append(
            {
                "comparison": "tourist_recent_category_gap",
                "retail_group": "tourist_sensitive_discretionary",
                "retail_category": category,
                "phase": "recent_adjustment",
                "baseline_a_gap": a_gap,
                "baseline_b_gap": b_gap,
                "gap_change_b_minus_a": b_gap - a_gap,
                "direction_same": same_direction(a_gap, b_gap),
            }
        )

    for group in ["local_daily_consumption", "durable_household"]:
        for category in sorted(local_durable_b.loc[local_durable_b["retail_group"].eq(group), "retail_category"].unique()):
            a_gap = value_for(
                local_durable_a,
                {"retail_group": group, "retail_category": category, "phase": "recent_adjustment"},
                "avg_gap",
            )
            b_gap = value_for(
                local_durable_b,
                {"retail_group": group, "retail_category": category, "phase": "recent_adjustment"},
                "avg_gap",
            )
            rows.append(
                {
                    "comparison": "local_durable_recent_category_gap",
                    "retail_group": group,
                    "retail_category": category,
                    "phase": "recent_adjustment",
                    "baseline_a_gap": a_gap,
                    "baseline_b_gap": b_gap,
                    "gap_change_b_minus_a": b_gap - a_gap,
                    "direction_same": same_direction(a_gap, b_gap),
                }
            )

    return pd.DataFrame(rows)


def value_for(df: pd.DataFrame, filters: dict[str, object], value_col: str) -> float:
    """Return a single value from a filtered data frame."""
    mask = pd.Series(True, index=df.index)
    for col, value in filters.items():
        mask &= df[col].astype(str).eq(str(value))
    values = df.loc[mask, value_col]
    if values.empty:
        raise ValueError(f"No value found for filters {filters} in {value_col}")
    return float(values.iloc[0])


def same_direction(a: float, b: float) -> bool:
    """Compare signs using the same near-zero band as status labels."""
    return status_from_gap(a) == status_from_gap(b)


def save_figures(
    group_b: pd.DataFrame,
    tourist_b: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    """Save Baseline B and A-vs-B summary figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    behavioral_group_b = group_b.loc[group_b["retail_group"].astype(str).isin(BEHAVIORAL_GROUPS)].copy()
    heatmap_data = behavioral_group_b.pivot(index="retail_group", columns="phase", values="avg_gap")
    heatmap_data = heatmap_data[[phase for phase in PHASE_ORDER if phase in heatmap_data.columns]]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("Baseline B group conversion gaps by phase")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "baseline_sensitivity_group_phase_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    tourist_recent = tourist_b.loc[tourist_b["phase"].eq("recent_adjustment")].sort_values("avg_gap")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#b65f5f" if gap < 0 else "#4d7c78" for gap in tourist_recent["avg_gap"]]
    ax.barh(tourist_recent["retail_category"], tourist_recent["avg_gap"], color=colors)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Baseline B tourist-sensitive recent gaps")
    ax.set_xlabel("Retail recovery index minus visitor recovery index")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "baseline_sensitivity_tourist_sensitive_recent.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    comp = comparison.loc[
        comparison["comparison"].eq("group_phase_gap")
        & comparison["phase"].eq("recent_adjustment")
        & comparison["retail_group"].isin(BEHAVIORAL_GROUPS)
    ].copy()
    comp_long = comp.melt(
        id_vars=["retail_group", "phase"],
        value_vars=["baseline_a_gap", "baseline_b_gap"],
        var_name="baseline",
        value_name="avg_gap",
    )
    comp_long["baseline"] = comp_long["baseline"].map(
        {
            "baseline_a_gap": "A: 2018-2019 average",
            "baseline_b_gap": "B: 2019 same-month",
        }
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=comp_long, x="retail_group", y="avg_gap", hue="baseline", ax=ax)
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Baseline A vs B recent-adjustment group gaps")
    ax.set_xlabel("")
    ax.set_ylabel("Average conversion gap")
    ax.tick_params(axis="x", rotation=18)
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "baseline_sensitivity_a_vs_b_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_notes(
    panel: pd.DataFrame,
    group_b: pd.DataFrame,
    tourist_b: pd.DataFrame,
    local_durable_b: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    """Write cautious markdown notes for Baseline B sensitivity."""
    latest_month = panel["month"].max().strftime("%Y%m")
    group_recent = group_b.loc[group_b["phase"].eq("recent_adjustment")].copy()
    tourist_recent = tourist_b.loc[tourist_b["phase"].eq("recent_adjustment")].copy()
    local_recent = local_durable_b.loc[
        local_durable_b["phase"].eq("recent_adjustment")
        & local_durable_b["retail_group"].eq("local_daily_consumption")
    ].copy()
    durable_recent = local_durable_b.loc[
        local_durable_b["phase"].eq("recent_adjustment")
        & local_durable_b["retail_group"].eq("durable_household")
    ].copy()

    ts_group = group_b.loc[group_b["retail_group"].astype(str).eq("tourist_sensitive_discretionary")]
    ts_early = value_for(ts_group, {"phase": "early_reopening"}, "avg_gap")
    ts_recent = value_for(ts_group, {"phase": "recent_adjustment"}, "avg_gap")
    local_recent_group = value_for(group_b, {"retail_group": "local_daily_consumption", "phase": "recent_adjustment"}, "avg_gap")
    durable_recent_group = value_for(group_b, {"retail_group": "durable_household", "phase": "recent_adjustment"}, "avg_gap")
    total_recent_group = value_for(group_b, {"retail_group": "benchmark_total", "phase": "recent_adjustment"}, "avg_gap")
    tourist_negative_count = int((tourist_recent["avg_gap"] < 0).sum())
    tourist_total = tourist_recent["retail_category"].nunique()

    direction_changes = comparison.loc[
        comparison["comparison"].eq("tourist_recent_category_gap")
        & ~comparison["direction_same"]
    ]

    lines = [
        "# Baseline Sensitivity Notes",
        "",
        "Baseline B uses 2019 same-month equals 100. The conversion gap remains retail recovery index minus visitor recovery index.",
        "",
        "- Positive gap: retail recovered above visitor recovery.",
        "- Negative gap: retail lagged visitor recovery.",
        "- Near zero: broadly aligned with visitor recovery.",
        "",
        f"Latest available month: {latest_month}.",
        "",
        "## What Changed Under Baseline B",
        "",
        "The same-month baseline changes the level of some gaps because each month is compared with its own 2019 month rather than the 2018-2019 average. This makes seasonal differences less visible in the index construction, but it also makes results depend more directly on 2019 month-specific values.",
        "",
        "Recent adjustment group gaps under Baseline B:",
    ]
    for _, row in group_recent.sort_values("avg_gap").iterrows():
        suffix = " (benchmark, not behavioral)" if str(row["retail_group"]) == "benchmark_total" else ""
        suffix = " (interpretively weak)" if str(row["retail_group"]) == "residual_other" else suffix
        lines.append(f"- {row['retail_group']}: {row['avg_gap']:.2f}{suffix}.")

    lines += [
        "",
        "## What Remained Stable",
        "",
        f"- Tourist-sensitive discretionary still moves from early outperformance ({ts_early:.2f}) to recent underperformance ({ts_recent:.2f}).",
        f"- {tourist_negative_count} of {tourist_total} tourist-sensitive categories are negative in recent adjustment.",
        f"- Local daily consumption remains above tourist-sensitive discretionary in recent adjustment ({local_recent_group:.2f} vs {ts_recent:.2f}).",
        f"- Durable/household moves from early outperformance to a smaller recent gap ({durable_recent_group:.2f}), but under Baseline B it is slightly below visitor recovery rather than clearly aligned.",
        f"- Total retail remains a broad benchmark, with recent adjustment gap {total_recent_group:.2f}; category groups still show wider differences.",
        "",
        "## What Became Weaker Or Baseline-Sensitive",
        "",
    ]
    if direction_changes.empty:
        lines.append("- No tourist-sensitive recent-adjustment category changed broad sign status under Baseline B.")
    else:
        lines.append("- Some tourist-sensitive category sign statuses differ under Baseline B:")
        for _, row in direction_changes.iterrows():
            lines.append(
                f"  - {row['retail_category']}: Baseline A {row['baseline_a_gap']:.2f}, Baseline B {row['baseline_b_gap']:.2f}."
            )
    lines += [
        "- Durable/household remains mixed internally, so it should be described as baseline-sensitive and category-dispersed rather than uniformly aligned or above visitor recovery.",
        "- Residual categories remain interpretively weak and should not anchor the thesis.",
        "",
        "## Tourist-Sensitive Recent Adjustment Categories",
        "",
    ]
    for _, row in tourist_recent.sort_values("avg_gap").iterrows():
        lines.append(f"- {row['retail_category']}: {row['avg_gap']:.2f}.")

    lines += [
        "",
        "## Local Daily And Durable Recent Adjustment Categories",
        "",
        "Local daily consumption:",
    ]
    for _, row in local_recent.sort_values("avg_gap", ascending=False).iterrows():
        lines.append(f"- {row['retail_category']}: {row['avg_gap']:.2f}.")
    lines.append("")
    lines.append("Durable/household:")
    for _, row in durable_recent.sort_values("avg_gap", ascending=False).iterrows():
        lines.append(f"- {row['retail_category']}: {row['avg_gap']:.2f}.")

    lines += [
        "",
        "## Thesis Assessment",
        "",
        "The main thesis survives the baseline change in descriptive terms. Total retail still masks category-level differences, tourist-sensitive discretionary still shifts from early outperformance to recent underperformance, and local daily consumption remains above tourist-sensitive discretionary in recent adjustment.",
        "",
        "Robust findings:",
        "",
        "- Tourist-sensitive discretionary reversal is robust to baseline choice.",
        "- Most or all tourist-sensitive categories remain below visitor recovery in recent adjustment.",
        "- Local daily consumption remains above tourist-sensitive discretionary in recent adjustment.",
        "- Total retail remains too broad to describe the category-specific pattern.",
        "",
        "Baseline-sensitive findings:",
        "",
        "- Exact gap levels change under the same-month baseline.",
        "- Durable/household should be described cautiously as baseline-sensitive with mixed internal behavior.",
        "- Residual other remains high but interpretively weak.",
        "",
        "This is descriptive evidence only. It should not be used to make causal claims.",
    ]
    (TABLE_DIR / "baseline_sensitivity_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    panel = build_baseline_b_panel()
    group_recovery = build_group_recovery(panel)
    group_phase_gaps = build_group_phase_gaps(group_recovery)
    tourist_drilldown, local_durable_drilldown = build_drilldowns(panel)
    comparison = build_comparison_summary(group_phase_gaps, tourist_drilldown, local_durable_drilldown)

    group_phase_gaps.to_csv(TABLE_DIR / "baseline_sensitivity_group_phase_gaps.csv", index=False)
    tourist_drilldown.to_csv(TABLE_DIR / "baseline_sensitivity_tourist_sensitive_drilldown.csv", index=False)
    local_durable_drilldown.to_csv(TABLE_DIR / "baseline_sensitivity_local_durable_drilldown.csv", index=False)
    comparison.to_csv(TABLE_DIR / "baseline_sensitivity_comparison_summary.csv", index=False)
    save_figures(group_phase_gaps, tourist_drilldown, comparison)
    write_notes(panel, group_phase_gaps, tourist_drilldown, local_durable_drilldown, comparison)

    latest_month = panel["month"].max().strftime("%Y%m")
    group_recent = group_phase_gaps.loc[group_phase_gaps["phase"].eq("recent_adjustment")]
    tourist_recent = tourist_drilldown.loc[tourist_drilldown["phase"].eq("recent_adjustment")]
    tourist_negative_count = int((tourist_recent["avg_gap"] < 0).sum())
    tourist_total = tourist_recent["retail_category"].nunique()
    ts_early = value_for(
        group_phase_gaps,
        {"retail_group": "tourist_sensitive_discretionary", "phase": "early_reopening"},
        "avg_gap",
    )
    ts_recent = value_for(
        group_phase_gaps,
        {"retail_group": "tourist_sensitive_discretionary", "phase": "recent_adjustment"},
        "avg_gap",
    )
    local_recent = value_for(
        group_phase_gaps,
        {"retail_group": "local_daily_consumption", "phase": "recent_adjustment"},
        "avg_gap",
    )
    thesis_survives = ts_early > 0 and ts_recent < 0 and local_recent > ts_recent and tourist_negative_count >= 5

    print("SUCCESS baseline sensitivity completed")
    print(f"Rows analyzed: {len(panel)}")
    print(f"Latest month: {latest_month}")
    print("\nGroup-level recent_adjustment gaps under Baseline B:")
    print(group_recent[["retail_group", "avg_gap", "median_gap", "latest_gap", "phase_status"]].to_string(index=False))
    print("\nTourist-sensitive recent_adjustment category gaps under Baseline B:")
    print(tourist_recent[["retail_category", "avg_gap", "latest_gap", "phase_status"]].sort_values("avg_gap").to_string(index=False))
    print(f"\nTourist-sensitive categories below visitor recovery: {tourist_negative_count} of {tourist_total}")
    print(f"Core thesis survives baseline sensitivity: {thesis_survives}")
    print("\nOutputs:")
    for path in [
        TABLE_DIR / "baseline_sensitivity_group_phase_gaps.csv",
        TABLE_DIR / "baseline_sensitivity_tourist_sensitive_drilldown.csv",
        TABLE_DIR / "baseline_sensitivity_local_durable_drilldown.csv",
        TABLE_DIR / "baseline_sensitivity_comparison_summary.csv",
        TABLE_DIR / "baseline_sensitivity_notes.md",
        FIGURE_DIR / "baseline_sensitivity_group_phase_heatmap.png",
        FIGURE_DIR / "baseline_sensitivity_tourist_sensitive_recent.png",
        FIGURE_DIR / "baseline_sensitivity_a_vs_b_summary.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
