from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "src" / "pipeline.py"


def test_pipeline_entrypoint_exists() -> None:
    assert PIPELINE_PATH.exists()


def test_pipeline_references_required_inputs_and_steps() -> None:
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    required_fragments = [
        "visitor_arrivals_real.csv",
        "retail_sales_real.csv",
        "docs/raw_data_acquisition.md",
        "preprocess_censd_json.py",
        "grouping_robustness.py",
    ]
    for fragment in required_fragments:
        assert fragment in text
