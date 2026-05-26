"""Phase segmentation analysis for retail group conversion gaps."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
GROUP_RECOVERY_PATH = TABLE_DIR / "retail_group_recovery.csv"

PHASE_ORDER = [
    "pre_covid_baseline",
    "covid_disruption",
    "early_reopening",
    "normalization",
    "recent_adjustment",
]
BEHAVIORAL_GROUPS = [
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
]
BENCHMARK_GROUP = "benchmark_total"


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


def phase_status(value: float) -> str:
    """Classify group gap direction with a small near-zero band."""
    if value > 5:
        return "outperformed visitor recovery"
    if value < -5:
        return "lagged visitor recovery"
    return "aligned with visitor recovery"


def load_group_recovery() -> pd.DataFrame:
    """Load group recovery output from grouped retail gap analysis."""
    if not GROUP_RECOVERY_PATH.exists():
        raise FileNotFoundError(
            f"Missing {GROUP_RECOVERY_PATH}. Run src/grouped_retail_gap_analysis.py first."
        )
    df = pd.read_csv(GROUP_RECOVERY_PATH)
    df["month"] = pd.to_datetime(df["month"])
    df["phase"] = df["month"].map(assign_phase)
    return df


def build_phase_gaps(group_recovery: pd.DataFrame) -> pd.DataFrame:
    """Calculate group average gaps by phase."""
    latest_month = group_recovery["month"].max()
    latest = group_recovery.loc[
        group_recovery["month"].eq(latest_month),
        ["retail_group", "group_conversion_gap"],
    ].rename(columns={"group_conversion_gap": "latest_gap"})

    summary = (
        group_recovery.groupby(["retail_group", "phase"], as_index=False)
        .agg(
            avg_gap=("group_conversion_gap", "mean"),
            median_gap=("group_conversion_gap", "median"),
            min_gap=("group_conversion_gap", "min"),
            max_gap=("group_conversion_gap", "max"),
            std_gap=("group_conversion_gap", "std"),
            months=("group_conversion_gap", "count"),
            avg_group_recovery_index=("group_recovery_index", "mean"),
            avg_visitor_recovery_index=("visitor_recovery_index", "mean"),
        )
        .merge(latest, on="retail_group", how="left")
    )
    summary["latest_month"] = latest_month.strftime("%Y%m")
    summary["is_benchmark"] = summary["retail_group"].eq(BENCHMARK_GROUP)
    summary["phase_status"] = summary["avg_gap"].map(phase_status)
    summary["phase"] = pd.Categorical(summary["phase"], categories=PHASE_ORDER, ordered=True)
    return summary.sort_values(["retail_group", "phase"]).reset_index(drop=True)


def build_phase_changes(phase_gaps: pd.DataFrame) -> pd.DataFrame:
    """Calculate selected phase-to-phase gap changes."""
    pivot = phase_gaps.pivot(index="retail_group", columns="phase", values="avg_gap").reset_index()
    changes = pd.DataFrame(
        {
            "retail_group": pivot["retail_group"],
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
    changes["is_benchmark"] = changes["retail_group"].eq(BENCHMARK_GROUP)
    return changes.sort_values(["is_benchmark", "retail_group"]).reset_index(drop=True)


def save_figures(group_recovery: pd.DataFrame, phase_gaps: pd.DataFrame) -> None:
    """Save phase segmentation figures."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    behavioral = phase_gaps.loc[phase_gaps["retail_group"].isin(BEHAVIORAL_GROUPS)]
    heatmap = behavioral.pivot(index="retail_group", columns="phase", values="avg_gap")
    heatmap = heatmap[[phase for phase in PHASE_ORDER if phase in heatmap.columns]]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    sns.heatmap(heatmap, annot=True, fmt=".1f", cmap="RdBu_r", center=0, ax=ax)
    ax.set_title("Retail group average conversion gaps by phase")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "retail_group_phase_gap_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    for group_name, group in group_recovery.groupby("retail_group"):
        is_benchmark = group_name == BENCHMARK_GROUP
        ax.plot(
            group["month"],
            group["group_conversion_gap"],
            label=group_name,
            linewidth=2.2 if is_benchmark else 1.8,
            linestyle=":" if is_benchmark else "-",
            alpha=0.75 if is_benchmark else 1,
        )
    for boundary in ["2020-01-01", "2023-01-01", "2024-01-01", "2025-01-01"]:
        ax.axvline(pd.Timestamp(boundary), color="black", linewidth=0.8, alpha=0.2)
    ax.axhline(0, color="black", linewidth=1, alpha=0.55)
    ax.set_title("Retail group conversion gap trends by phase")
    ax.set_xlabel("Month")
    ax.set_ylabel("Group recovery index minus visitor recovery index")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "retail_group_phase_gap_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_summary(phase_gaps: pd.DataFrame, phase_changes: pd.DataFrame) -> None:
    """Write phase segmentation markdown summary."""
    lines = [
        "# Retail Group Phase Gap Summary",
        "",
        "Gap formula: retail group recovery index minus visitor recovery index.",
        "",
        "- Positive gap: retail group recovered above visitor recovery.",
        "- Negative gap: retail group lagged visitor recovery.",
        "- Near zero: retail group aligned with visitor recovery.",
        "",
        "Behavioral group interpretation excludes `benchmark_total`. Total retail is retained only as a benchmark comparison.",
        "",
        "## Phase-Level Read",
        "",
    ]
    for group in BEHAVIORAL_GROUPS:
        group_rows = phase_gaps.loc[phase_gaps["retail_group"].eq(group)]
        lines += [f"### {group}", ""]
        for phase in PHASE_ORDER:
            row = group_rows.loc[group_rows["phase"].astype(str).eq(phase)]
            if row.empty:
                continue
            item = row.iloc[0]
            lines.append(f"- {phase}: {item['avg_gap']:.1f} average gap, {item['phase_status']}.")
        lines.append("")

    residual = phase_gaps.loc[
        phase_gaps["retail_group"].eq("residual_other")
        & phase_gaps["phase"].astype(str).eq("recent_adjustment"),
        "avg_gap",
    ].iloc[0]
    lines += [
        f"Residual_other remains interpretively weak, even with a recent adjustment gap of {residual:.1f}. It should not drive the main thesis.",
        "",
        "## Benchmark Total",
        "",
    ]
    benchmark_rows = phase_gaps.loc[phase_gaps["retail_group"].eq(BENCHMARK_GROUP)]
    for phase in PHASE_ORDER:
        row = benchmark_rows.loc[benchmark_rows["phase"].astype(str).eq(phase)]
        if row.empty:
            continue
        item = row.iloc[0]
        lines.append(f"- {phase}: {item['avg_gap']:.1f} average benchmark gap.")

    lines += ["", "## Phase Changes", ""]
    for _, row in phase_changes.loc[~phase_changes["is_benchmark"]].iterrows():
        lines.append(
            f"- {row['retail_group']}: early to normalization {row['early_to_normalization_change']:.1f}; "
            f"normalization to recent {row['normalization_to_recent_change']:.1f}."
        )

    tourist_recent = phase_gaps.loc[
        phase_gaps["retail_group"].eq("tourist_sensitive_discretionary")
        & phase_gaps["phase"].astype(str).eq("recent_adjustment"),
        "avg_gap",
    ].iloc[0]
    local_recent = phase_gaps.loc[
        phase_gaps["retail_group"].eq("local_daily_consumption")
        & phase_gaps["phase"].astype(str).eq("recent_adjustment"),
        "avg_gap",
    ].iloc[0]
    durable_recent = phase_gaps.loc[
        phase_gaps["retail_group"].eq("durable_household")
        & phase_gaps["phase"].astype(str).eq("recent_adjustment"),
        "avg_gap",
    ].iloc[0]
    lines += [
        "",
        "## Interpretation",
        "",
        f"Tourist-sensitive discretionary retail is phase-specific: it outperformed visitor recovery during early reopening and lagged visitor recovery in recent adjustment with an average gap of {tourist_recent:.1f}.",
        f"Local daily consumption remained above visitor recovery under the primary baseline in recent adjustment with an average gap of {local_recent:.1f}, but later baseline sensitivity checks treat this as baseline-sensitive.",
        f"Durable household moved toward broad alignment under the primary baseline, with a recent adjustment gap of {durable_recent:.1f}.",
        "",
        "## Corrected Thesis Statement",
        "",
        "The phase evidence is consistent with a category-group and phase-specific visitor-retail conversion mismatch. Tourist-sensitive discretionary retail shifted from above visitor recovery in early reopening to below visitor recovery in recent adjustment. Local daily and durable/household patterns require more cautious interpretation because later robustness checks show baseline sensitivity.",
    ]
    (TABLE_DIR / "retail_group_phase_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    group_recovery = load_group_recovery()
    phase_gaps = build_phase_gaps(group_recovery)
    phase_changes = build_phase_changes(phase_gaps)

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    phase_gaps.to_csv(TABLE_DIR / "retail_group_phase_gaps.csv", index=False)
    phase_changes.to_csv(TABLE_DIR / "retail_group_phase_changes.csv", index=False)
    save_figures(group_recovery, phase_gaps)
    write_summary(phase_gaps, phase_changes)

    print("SUCCESS retail group phase analysis completed")
    print("Outputs:")
    for path in [
        TABLE_DIR / "retail_group_phase_gaps.csv",
        TABLE_DIR / "retail_group_phase_changes.csv",
        TABLE_DIR / "retail_group_phase_summary.md",
        FIGURE_DIR / "retail_group_phase_gap_heatmap.png",
        FIGURE_DIR / "retail_group_phase_gap_trends.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
