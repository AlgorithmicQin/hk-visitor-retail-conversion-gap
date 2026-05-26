"""Comparative drill-down for local daily and durable retail groups."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import yaml

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "retail_category_groups.yaml"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
RECOVERY_PATH = TABLE_DIR / "retail_category_recovery.csv"
TARGET_GROUPS = ["local_daily_consumption", "durable_household"]
PHASE_ORDER = ["early_reopening", "normalization", "recent_adjustment"]


def assign_phase(month: pd.Timestamp) -> str | None:
    """Assign post-reopening drilldown phases."""
    if pd.Timestamp("2023-01-01") <= month <= pd.Timestamp("2023-12-01"):
        return "early_reopening"
    if pd.Timestamp("2024-01-01") <= month <= pd.Timestamp("2024-12-01"):
        return "normalization"
    if month >= pd.Timestamp("2025-01-01"):
        return "recent_adjustment"
    return None


def phase_status(value: float) -> str:
    """Classify category gap direction with a small near-zero band."""
    if value > 5:
        return "outperformed visitor recovery"
    if value < -5:
        return "lagged visitor recovery"
    return "aligned with visitor recovery"


def load_mapping() -> pd.DataFrame:
    """Load category-to-group mapping."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    rows = []
    for group_name, group_config in config["groups"].items():
        for item in group_config["categories"]:
            rows.append({"retail_group": group_name, "retail_category": item["name"]})
    return pd.DataFrame(rows)


def build_drilldown() -> pd.DataFrame:
    """Build local-daily and durable category phase summary."""
    recovery = pd.read_csv(RECOVERY_PATH)
    recovery["month"] = pd.to_datetime(recovery["month"])
    mapping = load_mapping()
    df = recovery.merge(mapping, on="retail_category", how="left")
    df = df.loc[df["retail_group"].isin(TARGET_GROUPS)].copy()
    df["phase"] = df["month"].map(assign_phase)
    df = df.loc[df["phase"].notna()].copy()

    latest_month = df["month"].max()
    latest = df.loc[
        df["month"].eq(latest_month),
        ["retail_group", "retail_category", "visitor_retail_conversion_gap"],
    ].rename(columns={"visitor_retail_conversion_gap": "latest_gap"})

    summary = (
        df.groupby(["retail_group", "retail_category", "phase"], as_index=False)
        .agg(
            avg_gap=("visitor_retail_conversion_gap", "mean"),
            median_gap=("visitor_retail_conversion_gap", "median"),
            min_gap=("visitor_retail_conversion_gap", "min"),
            max_gap=("visitor_retail_conversion_gap", "max"),
            std_gap=("visitor_retail_conversion_gap", "std"),
            months=("visitor_retail_conversion_gap", "count"),
            avg_retail_recovery_index=("retail_recovery_index", "mean"),
            avg_visitor_recovery_index=("visitor_recovery_index", "mean"),
        )
        .merge(latest, on=["retail_group", "retail_category"], how="left")
    )
    recent = summary.loc[
        summary["phase"].eq("recent_adjustment"),
        ["retail_group", "retail_category", "avg_gap", "std_gap"],
    ].rename(columns={"avg_gap": "recent_adjustment_avg_gap", "std_gap": "recent_adjustment_std_gap"})
    summary = summary.merge(recent, on=["retail_group", "retail_category"], how="left")
    summary["latest_minus_recent_avg"] = summary["latest_gap"] - summary["recent_adjustment_avg_gap"]
    summary["latest_representative_recent"] = (
        summary["latest_minus_recent_avg"].abs() <= summary["recent_adjustment_std_gap"]
    )
    summary["phase_status"] = summary["avg_gap"].map(phase_status)
    summary["phase"] = pd.Categorical(summary["phase"], categories=PHASE_ORDER, ordered=True)
    return summary.sort_values(["retail_group", "retail_category", "phase"]).reset_index(drop=True)


def build_phase_changes(drilldown: pd.DataFrame) -> pd.DataFrame:
    """Build phase-to-phase category gap changes."""
    pivot = (
        drilldown.pivot_table(
            index=["retail_group", "retail_category"],
            columns="phase",
            values="avg_gap",
            aggfunc="first",
            observed=False,
        )
        .reset_index()
    )
    changes = pd.DataFrame(
        {
            "retail_group": pivot["retail_group"],
            "retail_category": pivot["retail_category"],
            "early_reopening_avg_gap": pivot["early_reopening"],
            "normalization_avg_gap": pivot["normalization"],
            "recent_adjustment_avg_gap": pivot["recent_adjustment"],
        }
    )
    changes["early_to_normalization_change"] = (
        changes["normalization_avg_gap"] - changes["early_reopening_avg_gap"]
    )
    changes["normalization_to_recent_change"] = (
        changes["recent_adjustment_avg_gap"] - changes["normalization_avg_gap"]
    )
    recent = drilldown.loc[
        drilldown["phase"].astype(str).eq("recent_adjustment"),
        [
            "retail_group",
            "retail_category",
            "latest_gap",
            "recent_adjustment_std_gap",
            "latest_minus_recent_avg",
            "latest_representative_recent",
            "phase_status",
        ],
    ].rename(columns={"phase_status": "recent_status"})
    changes = changes.merge(recent, on=["retail_group", "retail_category"], how="left")
    return changes.sort_values(["retail_group", "recent_adjustment_avg_gap"], ascending=[True, False]).reset_index(drop=True)


def save_figures(drilldown: pd.DataFrame) -> None:
    """Save local-daily and durable drilldown figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(figsize=(12, 6.5))
    for (group_name, category), group in drilldown.groupby(["retail_group", "retail_category"]):
        ax.plot(group["phase"].astype(str), group["avg_gap"], marker="o", label=f"{group_name}: {category}")
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Local daily and durable category conversion gap trends")
    ax.set_xlabel("")
    ax.set_ylabel("Average conversion gap")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "local_daily_durable_category_gap_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    heatmap = drilldown.pivot_table(
        index=["retail_group", "retail_category"],
        columns="phase",
        values="avg_gap",
        aggfunc="first",
        observed=False,
    )
    heatmap = heatmap[[phase for phase in PHASE_ORDER if phase in heatmap.columns]]
    fig, ax = plt.subplots(figsize=(9.5, 7))
    sns.heatmap(heatmap, annot=True, fmt=".1f", cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("Local daily and durable phase average gaps")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "local_daily_durable_phase_gap_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_summary(drilldown: pd.DataFrame, changes: pd.DataFrame) -> None:
    """Write local-daily and durable drilldown markdown summary."""
    latest_month = pd.read_csv(RECOVERY_PATH)["Month"].max()
    recent = drilldown.loc[drilldown["phase"].astype(str).eq("recent_adjustment")].copy()
    local = recent.loc[recent["retail_group"].eq("local_daily_consumption")].sort_values("avg_gap", ascending=False)
    durable = recent.loc[recent["retail_group"].eq("durable_household")].sort_values("avg_gap", ascending=False)
    local_positive = int((local["avg_gap"] > 0).sum())
    durable_positive = int((durable["avg_gap"] > 0).sum())

    lines = [
        "# Local Daily And Durable Drilldown Summary",
        "",
        "Gap formula: retail category recovery index minus visitor recovery index.",
        "",
        "- Positive gap: category recovered above visitor recovery.",
        "- Negative gap: category lagged visitor recovery.",
        "- Near zero: category aligned with visitor recovery.",
        "",
        f"Latest available month: {latest_month}.",
        "",
        "## Local Daily Consumption Drivers",
        "",
    ]
    for _, row in local.iterrows():
        lines.append(f"- {row['retail_category']}: recent average gap {row['avg_gap']:.1f}, latest gap {row['latest_gap']:.1f}.")
    lines += ["", "## Durable Household Drivers", ""]
    for _, row in durable.iterrows():
        lines.append(f"- {row['retail_category']}: recent average gap {row['avg_gap']:.1f}, latest gap {row['latest_gap']:.1f}.")

    lines += [
        "",
        "## Concentration Read",
        "",
        f"- local_daily_consumption: {local_positive} of {len(local)} categories outperformed visitor recovery in recent adjustment.",
        f"- durable_household: {durable_positive} of {len(durable)} categories outperformed visitor recovery in recent adjustment.",
        "",
        "## Latest-Month Representativeness",
        "",
    ]
    flagged = changes.loc[~changes["latest_representative_recent"]]
    if flagged.empty:
        lines.append("- No local daily or durable category has a latest-month gap outside its recent-period standard deviation.")
    else:
        for _, row in flagged.iterrows():
            lines.append(
                f"- {row['retail_category']}: latest gap differs from recent average by {row['latest_minus_recent_avg']:.1f} index points."
            )

    lines += [
        "",
        "## Corrected Thesis Statement",
        "",
        "The comparative drilldown is consistent with group-specific and category-mix dependent recovery paths. Local daily consumption remains more positive than tourist-sensitive discretionary under the primary baseline, while durable/household is closer to alignment with mixed internal behavior. Later baseline sensitivity checks should be used before treating either group as uniformly above visitor recovery.",
    ]
    (TABLE_DIR / "local_daily_durable_drilldown_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    drilldown = build_drilldown()
    changes = build_phase_changes(drilldown)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    drilldown.to_csv(TABLE_DIR / "local_daily_durable_drilldown.csv", index=False)
    changes.to_csv(TABLE_DIR / "local_daily_durable_phase_changes.csv", index=False)
    save_figures(drilldown)
    write_summary(drilldown, changes)

    print("SUCCESS local daily and durable drilldown completed")
    print(f"Categories: {drilldown['retail_category'].nunique()}")
    print("Outputs:")
    for path in [
        TABLE_DIR / "local_daily_durable_drilldown.csv",
        TABLE_DIR / "local_daily_durable_phase_changes.csv",
        TABLE_DIR / "local_daily_durable_drilldown_summary.md",
        FIGURE_DIR / "local_daily_durable_category_gap_trends.png",
        FIGURE_DIR / "local_daily_durable_phase_gap_heatmap.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
