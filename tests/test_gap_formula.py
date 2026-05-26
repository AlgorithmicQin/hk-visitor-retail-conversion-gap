import pandas as pd


def test_visitor_retail_conversion_gap_formula() -> None:
    df = pd.DataFrame(
        {
            "retail_recovery_index": [120.0, 80.0, 100.0],
            "visitor_recovery_index": [90.0, 95.0, 100.0],
        }
    )

    df["visitor_retail_conversion_gap"] = (
        df["retail_recovery_index"] - df["visitor_recovery_index"]
    )

    expected = pd.Series([30.0, -15.0, 0.0], name="visitor_retail_conversion_gap")
    pd.testing.assert_series_equal(df["visitor_retail_conversion_gap"], expected)
