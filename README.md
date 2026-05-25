# Hong Kong Visitor-Retail Conversion Gap Analytics

A public-data analytics project examining whether Hong Kong's post-reopening visitor recovery aligned with retail category recovery.

## Core Question

Did visitor recovery translate evenly across retail categories, or did tourist-sensitive and local-consumption categories follow different recovery paths?

## Key Findings

This is a research pilot, and the findings should be read as descriptive evidence rather than causal inference.

- Total retail masks category-level differences.
- Tourist-sensitive discretionary retail shifted from early outperformance to broad recent underperformance relative to visitor recovery.
- The tourist-sensitive reversal is robust to baseline choice:
  - Baseline A: 2018-2019 average = 100.
  - Baseline B: 2019 same-month = 100.
- Local daily and durable/household interpretations are more baseline-sensitive and closer to visitor recovery.
- Visitor recovery alone has weak explanatory fit. Group and phase structure are more informative for describing category-specific recovery patterns.

Current working thesis:

```text
Total retail masks category-specific recovery paths. Tourist-sensitive discretionary categories moved from early reopening outperformance to recent underperformance relative to visitor recovery, and this reversal is robust to the same-month 2019 baseline check. Local daily and durable/household categories are closer to visitor recovery and more baseline-sensitive, so they should be interpreted more cautiously.
```

## Data

The current visitor-retail layer uses official Hong Kong Census and Statistics Department public data:

- C&SD visitor arrivals table `650-80001`.
- C&SD retail sales table `620-67002`.
- Coverage in the current processed pilot outputs: `201801` to `202603`.

The project uses aggregate monthly public data only. It does not include transaction-level data or tourist-spending microdata.

## Methods

The pipeline currently covers:

- C&SD API JSON extraction and preprocessing into normalized CSV files.
- Recovery index construction.
- Visitor-retail conversion gap calculation.
- Manual retail category grouping.
- Phase segmentation.
- Category and group drilldown analysis.
- Descriptive regression.
- Baseline sensitivity checks.

### Conversion Gap Formula

```text
gap = retail_recovery_index - visitor_recovery_index
```

Interpretation:

- Positive gap: retail recovered above visitor recovery.
- Negative gap: retail lagged visitor recovery.
- Near zero: broadly aligned with visitor recovery.

## Main Outputs

Documentation:

- `docs/current_findings.md`
- `docs/methodology.md`
- `docs/limitations.md`
- `docs/internal_audit.md`

Generated tables and figures:

- `outputs/tables/`
- `outputs/figures/`

Key generated tables include recovery panels, category and group gap diagnostics, descriptive regression summaries, and baseline sensitivity outputs.

## Limitations

- The analysis is descriptive, not causal.
- Monthly aggregation can hide shorter timing differences and within-month changes.
- The project does not use transaction-level data.
- The project does not use tourist-spending microdata.
- Retail category grouping requires judgment, and some categories are ambiguous.
- Local daily and durable/household findings are baseline-sensitive.
- The post-reopening regression layer includes a model with a high condition number, so that result is limited.
- Hotel and event modules are not included in the current analysis.
- This is an analytics pilot, not a recommendation document.

## How To Reproduce

The conservative script order is:

```bash
python src/preprocess_censd_json.py
python src/visitor_retail_pilot.py
python src/grouped_retail_gap_analysis.py
python src/regression_robustness.py
python src/baseline_sensitivity.py
```

The raw C&SD API JSON payloads should already be present in `data/raw/` before preprocessing. Some phase segmentation and drilldown tables were produced during the pilot analysis and are stored under `outputs/tables/`; the listed script order includes the currently formalized scripts in `src/`. The original 2018-2019 baseline outputs are not overwritten by the baseline sensitivity script.

## Project Status

Research pilot / portfolio candidate, not a final production dashboard.

The current scope is visitor-retail category mismatch only. Hotel and event modules are intentionally excluded from the present results.
