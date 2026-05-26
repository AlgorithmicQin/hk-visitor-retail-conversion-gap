from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"


def read_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        pytest.skip(f"{path.relative_to(PROJECT_ROOT)} does not exist; run python src/pipeline.py first.")
    return pd.read_csv(path, nrows=5)


def assert_required_columns(path: Path, required_columns: set[str]) -> None:
    df = read_if_exists(path)
    missing = required_columns - set(df.columns)
    assert not missing, f"{path.name} is missing required columns: {sorted(missing)}"


def test_retail_category_recovery_schema() -> None:
    required = {
        "Month",
        "retail_category",
        "retail_recovery_index",
        "visitor_recovery_index",
        "visitor_retail_conversion_gap",
    }
    assert_required_columns(TABLE_DIR / "retail_category_recovery.csv", required)


def test_grouping_robustness_summary_schema() -> None:
    required = {
        "definition_id",
        "definition_label",
        "categories_in_definition",
        "early_reopening_avg_gap",
        "normalization_avg_gap",
        "recent_adjustment_avg_gap",
        "early_to_recent_change",
        "recent_negative_category_count",
        "recent_total_category_count",
        "recent_negative_category_share",
        "finding_survives",
        "interpretation_note",
    }
    assert_required_columns(TABLE_DIR / "grouping_robustness_summary.csv", required)


def test_regression_model_summary_schema() -> None:
    required = {
        "model_id",
        "r_squared",
        "adj_r_squared",
    }
    assert_required_columns(TABLE_DIR / "regression_model_summary.csv", required)
