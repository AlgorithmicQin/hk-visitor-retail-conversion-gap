"""Test tourist-sensitive grouping robustness with alternative category definitions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
RECOVERY_PATH = TABLE_DIR / "retail_category_recovery.csv"

PHASE_ORDER = ["early_reopening", "normalization", "recent_adjustment"]

DEFINITIONS = {
    "current": {
        "definition_label": "Current documented grouping",
        "interpretation_note": "current documented grouping.",
        "categories": [
            "Clothing, footwear and allied products",
            "Department stores",
            "Footwear, allied products and other clothing accessories",
            "Jewellery, watches and clocks, and valuable gifts",
            "Medicines and cosmetics",
            "Optical shops",
            "Wearing apparel",
        ],
    },
    "strict": {
        "definition_label": "Strict tourist-sensitive grouping",
        "interpretation_note": "strict: excludes ambiguous medicines/cosmetics and optical shops.",
        "categories": [
            "Clothing, footwear and allied products",
            "Department stores",
            "Footwear, allied products and other clothing accessories",
            "Jewellery, watches and clocks, and valuable gifts",
            "Wearing apparel",
        ],
    },
    "broad": {
        "definition_label": "Broad tourist-sensitive grouping",
        "interpretation_note": "broad: includes additional plausible visitor-facing mixed categories.",
        "categories": [
            "Clothing, footwear and allied products",
            "Department stores",
            "Footwear, allied products and other clothing accessories",
            "Jewellery, watches and clocks, and valuable gifts",
            "Medicines and cosmetics",
            "Optical shops",
            "Wearing apparel",
            "Books, newspapers, stationery and gifts",
            "Chinese drugs and herbs",
            "Alcoholic drinks and tobacco",
        ],
    },
}


def assign_phase(month: pd.Timestamp) -> str | None:
    """Assign post-reopening phases used across the project."""
    if pd.Timestamp("2023-01-01") <= month <= pd.Timestamp("2023-12-01"):
        return "early_reopening"
    if pd.Timestamp("2024-01-01") <= month <= pd.Timestamp("2024-12-01"):
        return "normalization"
    if month >= pd.Timestamp("2025-01-01"):
        return "recent_adjustment"
    return None


def load_recovery() -> pd.DataFrame:
    """Load category recovery output and prepare phase labels."""
    if not RECOVERY_PATH.exists():
        raise FileNotFoundError(
            f"Missing {RECOVERY_PATH.relative_to(PROJECT_ROOT)}. Run src/visitor_retail_pilot.py first."
        )

    recovery = pd.read_csv(RECOVERY_PATH)
    required = {
        "month",
        "retail_category",
        "visitor_retail_conversion_gap",
    }
    missing = required - set(recovery.columns)
    if missing:
        raise KeyError(f"retail_category_recovery.csv is missing required columns: {sorted(missing)}")

    recovery["month"] = pd.to_datetime(recovery["month"])
    recovery["phase"] = recovery["month"].map(assign_phase)
    return recovery.loc[recovery["phase"].notna()].copy()


def validate_definitions(recovery: pd.DataFrame) -> None:
    """Validate all configured robustness categories exist in the recovery data."""
    available_categories = set(recovery["retail_category"].dropna().unique())
    for definition_id, config in DEFINITIONS.items():
        missing = sorted(set(config["categories"]) - available_categories)
        if missing:
            raise ValueError(f"{definition_id} definition has missing categories: {missing}")


def build_detail(recovery: pd.DataFrame) -> pd.DataFrame:
    """Build definition-category-phase detail table."""
    latest_month = recovery["month"].max()
    latest = recovery.loc[
        recovery["month"].eq(latest_month),
        ["retail_category", "visitor_retail_conversion_gap"],
    ].rename(columns={"visitor_retail_conversion_gap": "latest_gap"})

    rows = []
    categories = sorted(recovery["retail_category"].dropna().unique())
    for definition_id, config in DEFINITIONS.items():
        included_categories = set(config["categories"])
        for category in categories:
            category_data = recovery.loc[recovery["retail_category"].eq(category)]
            phase_summary = (
                category_data.groupby("phase", as_index=False)
                .agg(
                    avg_gap=("visitor_retail_conversion_gap", "mean"),
                    median_gap=("visitor_retail_conversion_gap", "median"),
                )
            )
            latest_gap = latest.loc[latest["retail_category"].eq(category), "latest_gap"].iloc[0]
            for _, phase_row in phase_summary.iterrows():
                rows.append(
                    {
                        "definition_id": definition_id,
                        "definition_label": config["definition_label"],
                        "retail_category": category,
                        "phase": phase_row["phase"],
                        "avg_gap": phase_row["avg_gap"],
                        "median_gap": phase_row["median_gap"],
                        "latest_gap": latest_gap,
                        "included_in_definition": category in included_categories,
                    }
                )

    detail = pd.DataFrame(rows)
    detail["phase"] = pd.Categorical(detail["phase"], categories=PHASE_ORDER, ordered=True)
    return detail.sort_values(["definition_id", "retail_category", "phase"]).reset_index(drop=True)


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    """Build grouping robustness summary table."""
    rows = []
    for definition_id, config in DEFINITIONS.items():
        included = detail.loc[
            detail["definition_id"].eq(definition_id) & detail["included_in_definition"]
        ].copy()

        phase_avgs = included.groupby("phase", observed=False)["avg_gap"].mean()
        recent = included.loc[included["phase"].astype(str).eq("recent_adjustment")].copy()
        recent_negative_count = int((recent["avg_gap"] < 0).sum())
        recent_total = int(recent["retail_category"].nunique())
        recent_negative_share = recent_negative_count / recent_total if recent_total else 0
        recent_avg = float(phase_avgs.get("recent_adjustment", float("nan")))
        early_avg = float(phase_avgs.get("early_reopening", float("nan")))
        finding_survives = bool(recent_avg < 0 and recent_negative_share >= 0.5)

        rows.append(
            {
                "definition_id": definition_id,
                "definition_label": config["definition_label"],
                "categories_in_definition": len(config["categories"]),
                "early_reopening_avg_gap": early_avg,
                "normalization_avg_gap": float(phase_avgs.get("normalization", float("nan"))),
                "recent_adjustment_avg_gap": recent_avg,
                "early_to_recent_change": recent_avg - early_avg,
                "recent_negative_category_count": recent_negative_count,
                "recent_total_category_count": recent_total,
                "recent_negative_category_share": recent_negative_share,
                "finding_survives": finding_survives,
                "interpretation_note": config["interpretation_note"],
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    """Run grouping robustness analysis."""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    recovery = load_recovery()
    validate_definitions(recovery)
    detail = build_detail(recovery)
    summary = build_summary(detail)

    detail.to_csv(TABLE_DIR / "grouping_robustness_detail.csv", index=False)
    summary.to_csv(TABLE_DIR / "grouping_robustness_summary.csv", index=False)

    print("SUCCESS grouping robustness completed")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
