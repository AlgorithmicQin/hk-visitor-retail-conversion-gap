"""Minimal Streamlit dashboard for visitor-retail conversion gap outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

TABLES = {
    "master": TABLE_DIR / "master_monthly_panel.csv",
    "group_phase": TABLE_DIR / "retail_group_phase_gaps.csv",
    "tourist_drilldown": TABLE_DIR / "tourist_sensitive_drilldown.csv",
    "local_durable": TABLE_DIR / "local_daily_durable_drilldown.csv",
    "regression": TABLE_DIR / "regression_model_summary.csv",
    "baseline_group_phase": TABLE_DIR / "baseline_sensitivity_group_phase_gaps.csv",
    "baseline_tourist": TABLE_DIR / "baseline_sensitivity_tourist_sensitive_drilldown.csv",
}

GROUP_LABELS = {
    "benchmark_total": "Total benchmark",
    "tourist_sensitive_discretionary": "Tourist-sensitive",
    "local_daily_consumption": "Local daily",
    "durable_household": "Durable / household",
    "residual_other": "Residual other",
}

GROUP_DISPLAY_ORDER = [
    "Tourist-sensitive",
    "Local daily",
    "Durable / household",
    "Total benchmark",
    "Residual other",
]

ROUND_COLUMNS = {
    "avg_gap",
    "median_gap",
    "latest_gap",
    "r_squared",
    "adj_r_squared",
    "early_reopening_avg_gap",
    "normalization_avg_gap",
    "recent_adjustment_avg_gap",
}

GROUP_TABLE_LABELS = {
    "retail_group": "Retail group",
    "avg_gap": "Average gap",
    "median_gap": "Median gap",
    "latest_gap": "Latest gap",
    "phase_status": "Phase status",
}

TOURIST_TABLE_LABELS = {
    "retail_category": "Retail category",
    "avg_gap": "Average gap",
    "latest_gap": "Latest gap",
    "phase_status": "Phase status",
    "latest_representative_recent": "Latest month representative",
}

REGRESSION_TABLE_LABELS = {
    "model_id": "Model",
    "r_squared": "R-squared",
    "adj_r_squared": "Adjusted R-squared",
    "condition_number": "Condition number",
}


def load_table(key: str) -> pd.DataFrame | None:
    """Load an output table, returning None if the pipeline has not generated it."""
    path = TABLES[key]
    if not path.exists():
        st.warning(f"Missing output table: `{path.relative_to(PROJECT_ROOT)}`")
        return None
    return pd.read_csv(path)


def fmt(value: float) -> str:
    """Format a numeric dashboard value."""
    return f"{value:.2f}"


def readable_group(group: str) -> str:
    """Convert internal group id to readable dashboard label."""
    return GROUP_LABELS.get(group, group)


def group_role(group: str) -> str:
    """Label group interpretation role for dashboard tables."""
    if group == "benchmark_total":
        return "benchmark"
    if group == "residual_other":
        return "behavioral group; interpretively weak"
    return "behavioral group"


def format_display_table(df: pd.DataFrame, *, keep_large_condition_number: bool = False) -> pd.DataFrame:
    """Return a display-only copy with rounded numeric values."""
    display = df.copy()
    for col in display.columns:
        if col in ROUND_COLUMNS and pd.api.types.is_numeric_dtype(display[col]):
            display[col] = display[col].round(2)
    if "condition_number" in display.columns and pd.api.types.is_numeric_dtype(display["condition_number"]):
        if keep_large_condition_number:
            display["condition_number"] = display["condition_number"].map(
                lambda value: f"{value:.2e}" if abs(value) >= 1_000_000 else f"{value:.2f}"
            )
        else:
            display["condition_number"] = display["condition_number"].round(2)
    return display


def rename_for_display(df: pd.DataFrame, labels: dict[str, str]) -> pd.DataFrame:
    """Rename dashboard table columns without changing source data."""
    return df.rename(columns=labels)


def sort_group_display(df: pd.DataFrame) -> pd.DataFrame:
    """Sort rows by the dashboard group display order."""
    result = df.copy()
    result["group_label"] = result["retail_group"].map(readable_group)
    result["group_label"] = pd.Categorical(result["group_label"], categories=GROUP_DISPLAY_ORDER, ordered=True)
    return result.sort_values("group_label")


def get_baseline_tourist_recent() -> tuple[float | None, int | None, int | None]:
    """Return Baseline B tourist-sensitive recent gap and below-visitor count."""
    baseline_group = load_table("baseline_group_phase")
    baseline_tourist = load_table("baseline_tourist")
    recent_gap = None
    below_count = None
    total_count = None

    if baseline_group is not None:
        row = baseline_group.loc[
            baseline_group["retail_group"].eq("tourist_sensitive_discretionary")
            & baseline_group["phase"].eq("recent_adjustment")
        ]
        if not row.empty:
            recent_gap = float(row["avg_gap"].iloc[0])

    if baseline_tourist is not None:
        recent = baseline_tourist.loc[baseline_tourist["phase"].eq("recent_adjustment")].copy()
        below_count = int((recent["avg_gap"] < 0).sum())
        total_count = int(recent["retail_category"].nunique())

    return recent_gap, below_count, total_count


def show_overview() -> None:
    """Render overview section."""
    st.header("Overview")
    master = load_table("master")
    recent_gap, below_count, total_count = get_baseline_tourist_recent()

    col1, col2, col3 = st.columns(3)
    if master is not None and not master.empty:
        col1.metric("Data coverage", f"{int(master['Month'].min())} to {int(master['Month'].max())}")
    else:
        col1.metric("Data coverage", "201801 to 202603")
    col2.metric(
        "Tourist-sensitive recent gap",
        fmt(recent_gap) if recent_gap is not None else "Unavailable",
        help="2019 same-month baseline, recent adjustment",
    )
    col2.caption("2019 same-month baseline, recent adjustment")
    col3.metric(
        "Tourist-sensitive categories below visitor recovery",
        f"{below_count} of {total_count}" if below_count is not None and total_count is not None else "Unavailable",
        help="2019 same-month baseline",
    )
    col3.caption("2019 same-month baseline")

    st.write(
        "Visitor recovery does not automatically imply recovery in traditional "
        "tourist-shopping retail categories."
    )
    st.write(
        "Total retail recovery can look broadly aligned with visitor recovery, but "
        "category-level data show a weaker recent pattern in traditional tourist-shopping "
        "categories such as department stores, jewellery, apparel, cosmetics, footwear, and optical shops."
    )
    st.info(
        "This dashboard summarizes descriptive evidence from official monthly visitor-arrival "
        "and retail-sales data. It does not make causal claims."
    )


def show_gap_section() -> None:
    """Render visitor-retail gap section."""
    st.header("Visitor-Retail Gap")
    st.code("conversion_gap = retail_recovery_index - visitor_recovery_index", language="text")
    st.markdown(
        "- Positive gap: retail recovered above visitor recovery.\n"
        "- Negative gap: retail lagged visitor recovery.\n"
        "- Near zero: broadly aligned with visitor recovery."
    )

    group_phase = load_table("group_phase")
    if group_phase is not None:
        recent = group_phase.loc[group_phase["phase"].eq("recent_adjustment")].copy()
        if not recent.empty:
            st.write(
                "The recent-adjustment snapshot shows tourist-sensitive categories below visitor recovery, "
                "while local daily and durable/household groups are closer to visitor recovery under the primary baseline."
            )
            st.subheader("Recent Adjustment Snapshot")
            chart_data = sort_group_display(
                recent[["retail_group", "avg_gap", "median_gap", "latest_gap", "phase_status"]]
            )
            chart_labels = chart_data["group_label"].astype(str).tolist()
            chart_values = chart_data["avg_gap"].tolist()
            colors = ["#b65f5f" if value < 0 else "#4d7c78" for value in chart_values]
            fig, ax = plt.subplots(figsize=(7.5, 3.2))
            ax.bar(chart_labels, chart_values, color=colors)
            ax.axhline(0, color="black", linewidth=1)
            ax.set_title("Recent adjustment conversion gap by retail group", fontsize=11)
            ax.set_ylabel("Average conversion gap", fontsize=9)
            ax.tick_params(axis="x", rotation=18, labelsize=8)
            ax.tick_params(axis="y", labelsize=8)
            ax.grid(axis="y", alpha=0.25)
            fig.tight_layout()
            st.pyplot(fig, width="stretch")
            plt.close(fig)
            st.caption(
                "Negative values indicate retail recovery below visitor recovery under the selected "
                "recovery-index baseline. Total benchmark is not a behavioral retail group; Residual other is interpretively weak."
            )
            st.caption("Residual other is shown for completeness and should not drive the main interpretation.")

            st.subheader("Recent Adjustment Table")
            compact = chart_data[["group_label", "avg_gap", "median_gap", "latest_gap", "phase_status"]].copy()
            compact = compact.rename(columns={"group_label": "retail_group"})
            st.dataframe(
                rename_for_display(format_display_table(compact), GROUP_TABLE_LABELS),
                width="stretch",
                hide_index=True,
            )

        st.caption("Total retail is used as a benchmark, not as a behavioral retail group.")
        st.caption("Residual other is interpretively weak.")
        cols = [
            "retail_group",
            "phase",
            "avg_gap",
            "median_gap",
            "latest_gap",
            "phase_status",
        ]
        display = group_phase[cols].copy()
        display["group_label"] = display["retail_group"].map(readable_group)
        display["role"] = display["retail_group"].map(group_role)
        display = display[
            ["group_label", "retail_group", "phase", "avg_gap", "median_gap", "latest_gap", "phase_status", "role"]
        ].rename(columns={"group_label": "display_group"})
        with st.expander("Show full group phase gap table"):
            st.dataframe(format_display_table(display), width="stretch", hide_index=True)


def show_tourist_reversal() -> None:
    """Render tourist-sensitive reversal section."""
    st.header("Tourist-Sensitive Reversal")
    recent_gap, below_count, total_count = get_baseline_tourist_recent()

    col1, col2 = st.columns(2)
    col1.metric(
        "Tourist-sensitive recent adjustment gap",
        fmt(recent_gap) if recent_gap is not None else "Unavailable",
        help="2019 same-month baseline",
    )
    col1.caption("2019 same-month baseline")
    col2.metric(
        "Tourist-sensitive categories below visitor recovery",
        f"{below_count} of {total_count}" if below_count is not None and total_count is not None else "Unavailable",
        help="Descriptive robustness check",
    )
    col2.caption("descriptive robustness check")

    st.write(
        "Tourist-sensitive discretionary categories moved from early reopening "
        "outperformance to recent underperformance relative to visitor recovery."
    )

    baseline_tourist = load_table("baseline_tourist")
    if baseline_tourist is not None:
        recent = baseline_tourist.loc[baseline_tourist["phase"].eq("recent_adjustment")].copy()
        st.write(
            "Under the 2019 same-month baseline, all seven tourist-sensitive discretionary "
            "categories were below visitor recovery in the recent adjustment phase. This "
            "supports the descriptive finding that traditional tourist-shopping categories "
            "did not fully realign with visitor recovery."
        )
        st.subheader("Recent Adjustment Under 2019 Same-Month Baseline")
        st.caption("Phase status is based on the recent-adjustment average gap, not the latest-month value.")
        cols = [
            "retail_category",
            "avg_gap",
            "latest_gap",
            "phase_status",
            "latest_representative_recent",
        ]
        st.dataframe(
            rename_for_display(format_display_table(recent[cols].sort_values("avg_gap")), TOURIST_TABLE_LABELS),
            width="stretch",
            hide_index=True,
        )

    tourist = load_table("tourist_drilldown")
    if tourist is not None:
        with st.expander("Show primary-baseline tourist-sensitive phase drilldown"):
            cols = [
                "retail_category",
                "phase",
                "avg_gap",
                "latest_gap",
                "phase_status",
                "latest_representative_recent",
            ]
            st.caption("Phase status is based on phase-average gaps; latest-month values may differ.")
            st.dataframe(
                rename_for_display(format_display_table(tourist[cols]), TOURIST_TABLE_LABELS),
                width="stretch",
                hide_index=True,
            )


def show_regression_robustness() -> None:
    """Render regression and robustness section."""
    st.header("Regression & Robustness")
    regression = load_table("regression")
    if regression is not None:
        model_lookup = regression.set_index("model_id")
        cols = st.columns(3)
        captions = {
            "A": "visitor recovery alone",
            "D": "visitor recovery with group interaction, month and phase controls",
            "E": "conversion gap with group, month and phase structure",
        }
        for col, model_id in zip(cols, ["A", "D", "E"], strict=True):
            if model_id in model_lookup.index:
                col.metric(f"Model {model_id} R-squared", fmt(model_lookup.loc[model_id, "r_squared"]))
                col.caption(captions[model_id])
        st.write(
            "Visitor recovery alone has weak explanatory fit; group and phase structure "
            "explain more of the observed category-level variation."
        )
        st.caption("Post E is marked with a high-condition-number caveat and should be interpreted cautiously.")
        with st.expander("Show detailed regression model table"):
            st.dataframe(
                rename_for_display(
                    format_display_table(regression, keep_large_condition_number=True),
                    REGRESSION_TABLE_LABELS,
                ),
                width="stretch",
                hide_index=True,
            )

    baseline_group = load_table("baseline_group_phase")
    if baseline_group is not None:
        row = baseline_group.loc[
            baseline_group["retail_group"].eq("tourist_sensitive_discretionary")
            & baseline_group["phase"].eq("recent_adjustment")
        ]
        if not row.empty:
            st.metric(
                "Baseline B tourist-sensitive recent adjustment gap",
                fmt(float(row["avg_gap"].iloc[0])),
            )
            st.caption("Baseline B uses 2019 same-month = 100.")


def show_limitations() -> None:
    """Render limitations section."""
    st.header("Limitations")
    st.subheader("Data Limits")
    st.markdown(
        "- Monthly aggregation can hide shorter timing differences.\n"
        "- No transaction-level data are used.\n"
        "- No tourist-spending microdata are used."
    )
    st.subheader("Interpretation Limits")
    st.markdown(
        "- The analysis is descriptive, not causal.\n"
        "- Category grouping requires judgment.\n"
        "- Local daily and durable/household interpretations are baseline-sensitive.\n"
        "- Local daily and durable/household comparisons are more baseline-sensitive than the tourist-sensitive reversal.\n"
        "- Post E has a high-condition-number caveat.\n"
        "- Hotel and event modules are excluded."
    )


def main() -> None:
    """Run the dashboard."""
    st.set_page_config(
        page_title="Hong Kong Visitor-Retail Conversion Gap Analytics",
        layout="wide",
    )
    st.title("Hong Kong Visitor-Retail Conversion Gap Analytics")
    st.caption("Research pilot / portfolio candidate, not a production dashboard.")

    sections = {
        "Overview": show_overview,
        "Visitor-Retail Gap": show_gap_section,
        "Tourist-Sensitive Reversal": show_tourist_reversal,
        "Regression & Robustness": show_regression_robustness,
        "Limitations": show_limitations,
    }
    selected = st.sidebar.radio("Section", list(sections))
    sections[selected]()


if __name__ == "__main__":
    main()
