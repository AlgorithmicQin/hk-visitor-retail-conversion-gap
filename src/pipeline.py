"""Run the full visitor-retail analysis pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_RAW_PAYLOADS = [
    PROJECT_ROOT / "data" / "raw" / "visitor_arrivals_real.csv",
    PROJECT_ROOT / "data" / "raw" / "retail_sales_real.csv",
]

PIPELINE_SCRIPTS = [
    PROJECT_ROOT / "src" / "preprocess_censd_json.py",
    PROJECT_ROOT / "src" / "visitor_retail_pilot.py",
    PROJECT_ROOT / "src" / "grouped_retail_gap_analysis.py",
    PROJECT_ROOT / "src" / "retail_group_phase_analysis.py",
    PROJECT_ROOT / "src" / "tourist_sensitive_drilldown.py",
    PROJECT_ROOT / "src" / "grouping_robustness.py",
    PROJECT_ROOT / "src" / "local_daily_durable_drilldown.py",
    PROJECT_ROOT / "src" / "regression_robustness.py",
    PROJECT_ROOT / "src" / "baseline_sensitivity.py",
]


def missing_raw_payloads() -> list[Path]:
    """Return required raw payload paths that are not available locally."""
    return [path for path in REQUIRED_RAW_PAYLOADS if not path.exists()]


def run_pipeline() -> int:
    """Run each existing analysis script and stop at the first failure."""
    missing = missing_raw_payloads()
    if missing:
        print(
            "Missing raw C&SD API payloads. See docs/raw_data_acquisition.md before running the pipeline.",
            flush=True,
        )
        for path in missing:
            print(f"- {path.relative_to(PROJECT_ROOT)}", flush=True)
        return 1

    total_steps = len(PIPELINE_SCRIPTS)
    for step_number, script_path in enumerate(PIPELINE_SCRIPTS, start=1):
        print(f"[{step_number}/{total_steps}] Running {script_path.name}", flush=True)
        result = subprocess.run([sys.executable, str(script_path)], cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"Pipeline failed while running {script_path.relative_to(PROJECT_ROOT)}", flush=True)
            return result.returncode

    print(
        "Pipeline completed successfully. Generated outputs are available under outputs/tables and outputs/figures.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())
