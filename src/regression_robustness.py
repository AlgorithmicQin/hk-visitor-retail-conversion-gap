"""Descriptive regression and robustness checks for visitor-retail mismatch."""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import pandas as pd
import yaml

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hk_visitor_conversion_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/hk_visitor_conversion_cache")

import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
CONFIG_PATH = PROJECT_ROOT / "config" / "retail_category_groups.yaml"
CATEGORY_RECOVERY_PATH = TABLE_DIR / "retail_category_recovery.csv"

GROUP_ORDER = [
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
    "benchmark_total",
]
PHASE_ORDER = [
    "pre_covid_baseline",
    "covid_disruption",
    "early_reopening",
    "normalization",
    "recent_adjustment",
]


MODELS = [
    {
        "model_id": "A",
        "sample": "full",
        "formula": "retail_recovery_index ~ visitor_recovery_index",
    },
    {
        "model_id": "B",
        "sample": "full",
        "formula": "retail_recovery_index ~ visitor_recovery_index + C(calendar_month)",
    },
    {
        "model_id": "C",
        "sample": "full",
        "formula": "retail_recovery_index ~ visitor_recovery_index + C(calendar_month) + C(phase)",
    },
    {
        "model_id": "D",
        "sample": "full",
        "formula": "retail_recovery_index ~ visitor_recovery_index * C(retail_group) + C(calendar_month) + C(phase)",
    },
    {
        "model_id": "E",
        "sample": "full",
        "formula": "conversion_gap ~ C(retail_group) + C(calendar_month) + C(phase)",
    },
    {
        "model_id": "Post D",
        "sample": "post_reopening",
        "formula": "retail_recovery_index ~ visitor_recovery_index * C(retail_group) + C(calendar_month)",
    },
    {
        "model_id": "Post E",
        "sample": "post_reopening",
        "formula": "conversion_gap ~ C(retail_group) + C(phase) + C(calendar_month)",
    },
    {
        "model_id": "Lag",
        "sample": "full_with_lags",
        "formula": (
            "retail_recovery_index ~ visitor_recovery_index + visitor_recovery_lag1 "
            "+ visitor_recovery_lag2 + C(retail_group) + C(calendar_month) + C(phase)"
        ),
    },
]


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
    duplicated = mapping.loc[mapping["retail_category"].duplicated(), "retail_category"].tolist()
    if duplicated:
        raise ValueError(f"Categories assigned to multiple groups: {duplicated}")
    return mapping


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


def build_regression_panel() -> pd.DataFrame:
    """Build the monthly category panel used by all regression checks."""
    recovery = pd.read_csv(CATEGORY_RECOVERY_PATH)
    mapping = load_group_mapping()

    panel = recovery.merge(mapping, on="retail_category", how="left")
    missing = sorted(panel.loc[panel["retail_group"].isna(), "retail_category"].unique())
    if missing:
        raise ValueError(f"Categories missing from group mapping: {missing}")

    panel["month"] = pd.to_datetime(panel["month"])
    panel["phase"] = panel["month"].map(assign_phase)
    first_month = panel["month"].min()
    panel["month_number"] = (
        (panel["month"].dt.year - first_month.year) * 12 + panel["month"].dt.month - first_month.month + 1
    )
    panel["year"] = panel["month"].dt.year
    panel["calendar_month"] = panel["month"].dt.month
    panel["conversion_gap"] = panel["retail_recovery_index"] - panel["visitor_recovery_index"]

    visitor_by_month = (
        panel[["month", "visitor_recovery_index"]]
        .drop_duplicates()
        .sort_values("month")
        .assign(
            visitor_recovery_lag1=lambda df: df["visitor_recovery_index"].shift(1),
            visitor_recovery_lag2=lambda df: df["visitor_recovery_index"].shift(2),
        )
    )
    panel = panel.drop(columns=["visitor_recovery_index"]).merge(visitor_by_month, on="month", how="left")

    panel["retail_group"] = pd.Categorical(panel["retail_group"], categories=GROUP_ORDER, ordered=True)
    panel["phase"] = pd.Categorical(panel["phase"], categories=PHASE_ORDER, ordered=True)
    panel["calendar_month"] = pd.Categorical(panel["calendar_month"], categories=list(range(1, 13)), ordered=True)

    required = [
        "month",
        "retail_category",
        "retail_group",
        "retail_recovery_index",
        "visitor_recovery_index",
        "conversion_gap",
        "phase",
        "month_number",
        "year",
        "calendar_month",
        "visitor_recovery_lag1",
        "visitor_recovery_lag2",
        "excluded_from_behavioral_interpretation",
    ]
    return panel[required].sort_values(["month", "retail_category"])


def fit_model(model_spec: dict[str, str], panel: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    """Fit a model and return summary and coefficient rows."""
    sample = model_spec["sample"]
    if sample == "post_reopening":
        data = panel.loc[panel["month"] >= pd.Timestamp("2023-01-01")].copy()
    elif sample == "full_with_lags":
        data = panel.dropna(subset=["visitor_recovery_lag1", "visitor_recovery_lag2"]).copy()
    else:
        data = panel.copy()

    summary = {
        "model_id": model_spec["model_id"],
        "sample": sample,
        "formula": model_spec["formula"],
        "nobs": len(data),
        "df_model": None,
        "df_resid": None,
        "r_squared": None,
        "adj_r_squared": None,
        "condition_number": None,
        "status": "ok",
        "warning": "",
    }
    coef_rows: list[dict[str, object]] = []

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = smf.ols(model_spec["formula"], data=data).fit()

        model_warnings = sorted({str(item.message) for item in caught})
        condition_number = float(result.condition_number)
        status_notes = []
        if condition_number > 1e8:
            status_notes.append("high_condition_number")
        if result.df_resid <= 0:
            status_notes.append("no_residual_degrees_of_freedom")
        if model_warnings:
            status_notes.append("warnings")

        summary.update(
            {
                "df_model": float(result.df_model),
                "df_resid": float(result.df_resid),
                "r_squared": float(result.rsquared),
                "adj_r_squared": float(result.rsquared_adj),
                "condition_number": condition_number,
                "status": ";".join(status_notes) if status_notes else "ok",
                "warning": " | ".join(model_warnings),
            }
        )
        conf_int = result.conf_int()
        for term, estimate in result.params.items():
            coef_rows.append(
                {
                    "model_id": model_spec["model_id"],
                    "sample": sample,
                    "term": term,
                    "estimate": float(estimate),
                    "std_error": float(result.bse[term]),
                    "t_value": float(result.tvalues[term]),
                    "p_value": float(result.pvalues[term]),
                    "ci_lower": float(conf_int.loc[term, 0]),
                    "ci_upper": float(conf_int.loc[term, 1]),
                }
            )
    except Exception as exc:  # pragma: no cover - reported to user through output table
        summary["status"] = "failed"
        summary["warning"] = str(exc)

    return summary, pd.DataFrame(coef_rows)


def run_models(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all requested descriptive regression models."""
    summaries = []
    coefficients = []
    for model_spec in MODELS:
        summary, coef = fit_model(model_spec, panel)
        summaries.append(summary)
        if not coef.empty:
            coefficients.append(coef)

    summary_df = pd.DataFrame(summaries)
    coef_df = pd.concat(coefficients, ignore_index=True) if coefficients else pd.DataFrame()
    return summary_df, coef_df


def save_figures(panel: pd.DataFrame) -> None:
    """Save descriptive diagnostic figures for group gaps and retail recovery."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    behavioral = panel.loc[~panel["excluded_from_behavioral_interpretation"]].copy()
    post = behavioral.loc[behavioral["month"] >= pd.Timestamp("2023-01-01")].copy()

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=behavioral,
        x="phase",
        y="conversion_gap",
        hue="retail_group",
        ax=ax,
        showfliers=False,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Group conversion gaps by phase")
    ax.set_xlabel("")
    ax.set_ylabel("Retail recovery index minus visitor recovery index")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(title="Retail group", loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "group_gap_boxplot_by_phase.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.scatterplot(
        data=behavioral,
        x="visitor_recovery_index",
        y="retail_recovery_index",
        hue="retail_group",
        alpha=0.72,
        s=28,
        ax=ax,
    )
    low = min(behavioral["visitor_recovery_index"].min(), behavioral["retail_recovery_index"].min())
    high = max(behavioral["visitor_recovery_index"].max(), behavioral["retail_recovery_index"].max())
    ax.plot([low, high], [low, high], color="black", linestyle="--", linewidth=1)
    ax.set_title("Visitor recovery vs retail category recovery by group")
    ax.set_xlabel("Visitor recovery index")
    ax.set_ylabel("Retail recovery index")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "visitor_vs_retail_by_group_scatter.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.violinplot(
        data=post,
        x="retail_group",
        y="conversion_gap",
        ax=ax,
        inner="quartile",
        cut=0,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Post-reopening group conversion gap distribution")
    ax.set_xlabel("")
    ax.set_ylabel("Retail recovery index minus visitor recovery index")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "post_reopening_group_gap_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def coefficient_lookup(coefficients: pd.DataFrame, model_id: str, term_contains: str) -> pd.DataFrame:
    """Return matching coefficient rows for notes."""
    if coefficients.empty:
        return coefficients
    mask = coefficients["model_id"].eq(model_id) & coefficients["term"].str.contains(term_contains, regex=False)
    return coefficients.loc[mask].copy()


def format_model_rows(summary: pd.DataFrame) -> list[str]:
    """Format compact model fit lines for markdown."""
    rows = []
    for _, row in summary.iterrows():
        if row["status"] == "failed":
            rows.append(f"- Model {row['model_id']}: failed ({row['warning']}).")
            continue
        rows.append(
            "- Model {model_id}: R-squared {r2:.3f}, adjusted R-squared {adj:.3f}, "
            "n={nobs}, status={status}.".format(
                model_id=row["model_id"],
                r2=row["r_squared"],
                adj=row["adj_r_squared"],
                nobs=int(row["nobs"]),
                status=row["status"],
            )
        )
    return rows


def write_notes(panel: pd.DataFrame, summary: pd.DataFrame, coefficients: pd.DataFrame) -> None:
    """Write regression interpretation notes using descriptive language only."""
    post = panel.loc[panel["month"] >= pd.Timestamp("2023-01-01")].copy()
    recent = panel.loc[
        (panel["phase"].astype(str) == "recent_adjustment")
        & (~panel["excluded_from_behavioral_interpretation"])
    ].copy()
    recent_group_avg = (
        recent.groupby("retail_group", observed=True)["conversion_gap"]
        .mean()
        .sort_values()
    )

    model_a = summary.loc[summary["model_id"] == "A"].iloc[0]
    model_d = summary.loc[summary["model_id"] == "D"].iloc[0]
    post_e = summary.loc[summary["model_id"] == "Post E"].iloc[0]
    lag_summary = summary.loc[summary["model_id"] == "Lag"].iloc[0]

    lag_terms = coefficients.loc[
        (coefficients["model_id"] == "Lag")
        & (coefficients["term"].isin(["visitor_recovery_index", "visitor_recovery_lag1", "visitor_recovery_lag2"]))
    ].copy()
    lag_lines = []
    for _, row in lag_terms.iterrows():
        lag_lines.append(
            f"- {row['term']}: estimate {row['estimate']:.3f}, p-value {row['p_value']:.3f}."
        )
    if not lag_lines:
        lag_lines.append("- Lag model coefficients were unavailable because the model failed.")

    group_coef = coefficient_lookup(coefficients, "Post E", "C(retail_group)")
    group_lines = []
    for _, row in group_coef.iterrows():
        clean_term = row["term"].replace("C(retail_group)[T.", "").replace("]", "")
        group_lines.append(
            f"- {clean_term}: {row['estimate']:.2f} index points relative to tourist_sensitive_discretionary, "
            f"p-value {row['p_value']:.3f}."
        )
    if not group_lines:
        group_lines.append("- Post E group coefficients were unavailable.")

    recent_lines = [
        f"- {group}: {value:.2f} average gap in recent_adjustment."
        for group, value in recent_group_avg.items()
    ]

    lines = [
        "# Regression Robustness Notes",
        "",
        "These are descriptive regressions for visitor-retail alignment. The conversion gap remains retail recovery index minus visitor recovery index.",
        "",
        "## Model Fit",
        "",
        *format_model_rows(summary),
        "",
        "## Interpretation",
        "",
        (
            f"- Visitor recovery is associated with category retail recovery in the simplest model, "
            f"but Model A explains a limited share of cross-category variation "
            f"(R-squared {model_a['r_squared']:.3f}, adjusted R-squared {model_a['adj_r_squared']:.3f})."
        ),
        (
            f"- With retail group, calendar month, and phase controls, Model D has adjusted R-squared "
            f"{model_d['adj_r_squared']:.3f}. This suggests category-specific recovery pattern matters."
        ),
        (
            f"- In the post-reopening gap model, adjusted R-squared is {post_e['adj_r_squared']:.3f}. "
            "Retail groups differ materially, but this model is limited if its status flags a high condition number."
        ),
        "- The benchmark_total group is retained in the panel for comparison, but it is not a behavioral retail category.",
        "",
        "## Post-Reopening Group Gap Coefficients",
        "",
        "These coefficients compare group conversion gaps with tourist_sensitive_discretionary as the reference group.",
        "",
        *group_lines,
        "",
        "## Recent Adjustment Group Gaps",
        "",
        *recent_lines,
        "",
        "Tourist-sensitive discretionary remains weaker in recent_adjustment: its average gap is below the other behavioral groups and below zero. In this panel, the recent_adjustment group averages continue to show tourist-sensitive discretionary below visitor recovery while local daily consumption remains above visitor recovery and durable household is near alignment.",
        "",
        "## Lag Checks",
        "",
        *lag_lines,
        "",
        (
            "Lagged visitor recovery terms should be treated as useful only if their estimates are stable and statistically distinguishable from zero. "
            f"The lag model status is {lag_summary['status']} with adjusted R-squared {lag_summary['adj_r_squared']:.3f}."
        ),
        "",
        "## Limitations",
        "",
        "- These regressions are descriptive and use only fields already present in the pilot dataset.",
        "- The same visitor recovery series is repeated across categories, so category and phase controls are important but do not turn the models into a causal design.",
        "- High condition numbers or warnings in the model summary table indicate multicollinearity or limited independent variation; those models should be read as limited diagnostics.",
        "- The post-reopening gap model includes both phase and calendar-month controls over a shorter period, so its high condition number should be treated as a meaningful limitation.",
        "- The model does not include hotel data, event data, income, prices, exchange rates, resident spending, or policy controls.",
        "",
        "## Thesis Assessment",
        "",
        "The regression layer strengthens the thesis in a descriptive sense: total retail is too broad, while category and group recovery paths differ after accounting for calendar month and phase. The supported claim is that visitor recovery is associated with retail recovery, but the visitor-retail alignment varies by retail group and recovery phase.",
        "",
        "## What Should Not Be Claimed",
        "",
        "- Do not claim that visitor recovery mechanically determines retail recovery.",
        "- Do not claim that omitted controls are accounted for.",
        "- Do not claim that event data or hotel data support the pattern until those modules are added and inspected.",
    ]
    (TABLE_DIR / "regression_robustness_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    panel = build_regression_panel()
    summary, coefficients = run_models(panel)

    panel.to_csv(TABLE_DIR / "regression_panel.csv", index=False)
    summary.to_csv(TABLE_DIR / "regression_model_summary.csv", index=False)
    coefficients.to_csv(TABLE_DIR / "regression_coefficients.csv", index=False)
    save_figures(panel)
    write_notes(panel, summary, coefficients)

    print("SUCCESS regression robustness layer completed")
    print(f"Regression panel rows: {len(panel)}")
    print(f"Retail categories: {panel['retail_category'].nunique()}")
    print("Retail groups:", ", ".join([str(group) for group in panel["retail_group"].dropna().unique()]))
    print("Phases:", ", ".join([str(phase) for phase in panel["phase"].dropna().unique()]))
    print("\nModel summary:")
    print(
        summary[
            [
                "model_id",
                "sample",
                "nobs",
                "r_squared",
                "adj_r_squared",
                "condition_number",
                "status",
            ]
        ].to_string(index=False)
    )
    key_terms = coefficients.loc[
        coefficients["term"].isin(
            [
                "visitor_recovery_index",
                "visitor_recovery_lag1",
                "visitor_recovery_lag2",
            ]
        )
    ]
    print("\nKey visitor recovery coefficients:")
    if key_terms.empty:
        print("None")
    else:
        print(key_terms[["model_id", "term", "estimate", "p_value"]].to_string(index=False))
    print("\nOutputs:")
    for path in [
        TABLE_DIR / "regression_panel.csv",
        TABLE_DIR / "regression_model_summary.csv",
        TABLE_DIR / "regression_coefficients.csv",
        TABLE_DIR / "regression_robustness_notes.md",
        FIGURE_DIR / "group_gap_boxplot_by_phase.png",
        FIGURE_DIR / "visitor_vs_retail_by_group_scatter.png",
        FIGURE_DIR / "post_reopening_group_gap_distribution.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
