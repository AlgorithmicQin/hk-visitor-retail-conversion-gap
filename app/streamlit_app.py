"""Minimal Streamlit dashboard for visitor-retail conversion gap outputs."""

from __future__ import annotations

from pathlib import Path

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
        st.subheader("Group Phase Gaps")
        st.caption("Total retail is used as a benchmark, not as a behavioral retail group.")
        cols = [
            "retail_group",
            "phase",
            "avg_gap",
            "median_gap",
            "latest_gap",
            "phase_status",
        ]
        display = group_phase[cols].copy()
        display["role"] = display["retail_group"].map(
            lambda value: "benchmark" if value == "benchmark_total" else "behavioral group"
        )
        st.dataframe(display, width="stretch", hide_index=True)


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
        cols = [
            "retail_category",
            "avg_gap",
            "latest_gap",
            "phase_status",
            "latest_representative_recent",
        ]
        st.dataframe(recent[cols].sort_values("avg_gap"), width="stretch", hide_index=True)

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
            st.dataframe(tourist[cols], width="stretch", hide_index=True)


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
        st.subheader("Regression Model Summary")
        st.dataframe(regression, width="stretch", hide_index=True)

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
    st.markdown(
        "- Monthly aggregation can hide shorter timing differences.\n"
        "- No transaction-level data are used.\n"
        "- No tourist-spending microdata are used.\n"
        "- The analysis is descriptive, not causal.\n"
        "- Category grouping requires judgment.\n"
        "- Local daily and durable/household interpretations are baseline-sensitive.\n"
        "- Post E has a high-condition-number caveat.\n"
        "- Local daily and durable/household comparisons are more baseline-sensitive than the tourist-sensitive reversal.\n"
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
