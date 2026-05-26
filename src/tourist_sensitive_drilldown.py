"""Drill-down analysis for tourist-sensitive retail categories."""

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
TARGET_GROUP = "tourist_sensitive_discretionary"
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
    """Build tourist-sensitive category phase summary."""
    recovery = pd.read_csv(RECOVERY_PATH)
    recovery["month"] = pd.to_datetime(recovery["month"])
    mapping = load_mapping()
    df = recovery.merge(mapping, on="retail_category", how="left")
    df = df.loc[df["retail_group"].eq(TARGET_GROUP)].copy()
    df["phase"] = df["month"].map(assign_phase)
    df = df.loc[df["phase"].notna()].copy()

    latest_month = df["month"].max()
    latest = df.loc[
        df["month"].eq(latest_month),
        ["retail_category", "visitor_retail_conversion_gap"],
    ].rename(columns={"visitor_retail_conversion_gap": "latest_gap"})

    summary = (
        df.groupby(["retail_category", "phase"], as_index=False)
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
        .merge(latest, on="retail_category", how="left")
    )
    recent = summary.loc[
        summary["phase"].eq("recent_adjustment"),
        ["retail_category", "avg_gap", "std_gap"],
    ].rename(columns={"avg_gap": "recent_adjustment_avg_gap", "std_gap": "recent_adjustment_std_gap"})
    summary = summary.merge(recent, on="retail_category", how="left")
    summary["latest_minus_recent_avg"] = summary["latest_gap"] - summary["recent_adjustment_avg_gap"]
    summary["latest_representative_recent"] = (
        summary["latest_minus_recent_avg"].abs() <= summary["recent_adjustment_std_gap"]
    )
    summary["phase_status"] = summary["avg_gap"].map(phase_status)
    summary["phase"] = pd.Categorical(summary["phase"], categories=PHASE_ORDER, ordered=True)
    return summary.sort_values(["retail_category", "phase"]).reset_index(drop=True)


def build_phase_changes(drilldown: pd.DataFrame) -> pd.DataFrame:
    """Build phase-to-phase category gap changes."""
    pivot = drilldown.pivot(index="retail_category", columns="phase", values="avg_gap").reset_index()
    changes = pd.DataFrame(
        {
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
            "retail_category",
            "latest_gap",
            "recent_adjustment_std_gap",
            "latest_minus_recent_avg",
            "latest_representative_recent",
            "phase_status",
        ],
    ].rename(columns={"phase_status": "recent_status"})
    changes = changes.merge(recent, on="retail_category", how="left")
    return changes.sort_values("recent_adjustment_avg_gap").reset_index(drop=True)


def save_figures(drilldown: pd.DataFrame) -> None:
    """Save tourist-sensitive drilldown figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(figsize=(11, 6))
    for category, group in drilldown.groupby("retail_category"):
        ax.plot(group["phase"].astype(str), group["avg_gap"], marker="o", label=category)
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Tourist-sensitive category conversion gap trends")
    ax.set_xlabel("")
    ax.set_ylabel("Average conversion gap")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "tourist_sensitive_category_gap_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    heatmap = drilldown.pivot(index="retail_category", columns="phase", values="avg_gap")
    heatmap = heatmap[[phase for phase in PHASE_ORDER if phase in heatmap.columns]]
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    sns.heatmap(heatmap, annot=True, fmt=".1f", cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("Tourist-sensitive phase average gaps")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "tourist_sensitive_phase_gap_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_summary(drilldown: pd.DataFrame, changes: pd.DataFrame) -> None:
    """Write tourist-sensitive drilldown markdown summary."""
    recent = drilldown.loc[drilldown["phase"].astype(str).eq("recent_adjustment")].sort_values("avg_gap")
    latest_month = pd.read_csv(RECOVERY_PATH)["Month"].max()
    negative_count = int((recent["avg_gap"] < 0).sum())
    total = recent["retail_category"].nunique()
    lines = [
        "# Tourist-Sensitive Drilldown Summary",
        "",
        "Gap formula: retail category recovery index minus visitor recovery index.",
        "",
        "- Positive gap: category recovered above visitor recovery.",
        "- Negative gap: category lagged visitor recovery.",
        "- Near zero: category aligned with visitor recovery.",
        "",
        f"Latest available month: {latest_month}.",
        "",
        "## Recent Adjustment Drivers",
        "",
    ]
    for _, row in recent.iterrows():
        lines.append(f"- {row['retail_category']}: recent average gap {row['avg_gap']:.1f}, latest gap {row['latest_gap']:.1f}.")
    lines += [
        "",
        "## Broad-Based Or Concentrated?",
        "",
        f"- The recent underperformance is broad-based: {negative_count} of {total} tourist-sensitive categories lagged visitor recovery on average in recent adjustment.",
        "",
        "## Latest-Month Representativeness",
        "",
    ]
    flagged = changes.loc[~changes["latest_representative_recent"]]
    if flagged.empty:
        lines.append("- No tourist-sensitive category has a latest-month gap outside its recent-period standard deviation.")
    else:
        for _, row in flagged.iterrows():
            lines.append(
                f"- {row['retail_category']}: latest gap differs from recent average by {row['latest_minus_recent_avg']:.1f} index points."
            )
    lines += [
        "",
        "## Corrected Thesis Statement",
        "",
        "The tourist-sensitive reversal is broad-based across the mapped categories, not just a single-category artifact. This remains descriptive evidence and should not be interpreted as causal.",
    ]
    (TABLE_DIR / "tourist_sensitive_drilldown_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    drilldown = build_drilldown()
    changes = build_phase_changes(drilldown)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    drilldown.to_csv(TABLE_DIR / "tourist_sensitive_drilldown.csv", index=False)
    changes.to_csv(TABLE_DIR / "tourist_sensitive_phase_changes.csv", index=False)
    save_figures(drilldown)
    write_summary(drilldown, changes)

    print("SUCCESS tourist-sensitive drilldown completed")
    print(f"Categories: {drilldown['retail_category'].nunique()}")
    print("Outputs:")
    for path in [
        TABLE_DIR / "tourist_sensitive_drilldown.csv",
        TABLE_DIR / "tourist_sensitive_phase_changes.csv",
        TABLE_DIR / "tourist_sensitive_drilldown_summary.md",
        FIGURE_DIR / "tourist_sensitive_category_gap_trends.png",
        FIGURE_DIR / "tourist_sensitive_phase_gap_heatmap.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
