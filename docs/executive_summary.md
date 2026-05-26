# Hong Kong Visitor-Retail Conversion Gap Analytics

## Project Purpose

Hong Kong's post-reopening visitor recovery appears visible in headline indicators, but traditional tourist-shopping retail categories show weaker recent alignment with visitor recovery.

This project examines whether Hong Kong's post-reopening visitor recovery aligned with recovery in retail sales categories. It focuses on the gap between visitor recovery and retail category recovery, using official monthly visitor-arrival and retail-sales data.

Hong Kong's visitor recovery does not automatically imply recovery in traditional tourist-shopping retail categories.

## Business / Analytical Question

Did visitor recovery translate evenly across retail categories, or did traditional tourist-shopping categories follow a different recovery path?

## Data

- C&SD Visitor Arrivals Table `650-80001`.
- C&SD Retail Sales Table `620-67002`.
- Monthly coverage: `201801` to `202603`.
- Official public data.
- No transaction-level data.
- No tourist-spending microdata.

## Method

The project uses:

- C&SD API extraction and preprocessing.
- Recovery index construction.
- Visitor-retail conversion gap calculation.
- Manual retail category grouping.
- Recovery phase segmentation.
- Tourist-sensitive category drilldown.
- Descriptive regression.
- Baseline sensitivity check.

Formula:

```text
conversion_gap = retail_recovery_index - visitor_recovery_index
```

Sign convention:

- Positive gap: retail recovered above visitor recovery.
- Negative gap: retail lagged visitor recovery.
- Near zero: broadly aligned.

## Main Findings

### Primary finding

- Tourist-sensitive discretionary categories moved from early reopening outperformance to recent underperformance relative to visitor recovery.

### Supporting evidence

- Total retail can look broadly aligned with visitor recovery, but category-level analysis shows more differentiated recovery paths.
- Under the 2019 same-month baseline, `tourist_sensitive_discretionary` recent adjustment gap is `-16.00`.
- Under the 2019 same-month baseline, `7 of 7` tourist-sensitive categories were below visitor recovery in the recent adjustment phase.
- Visitor recovery alone has weak explanatory fit: Model A R-squared is `0.087`.
- Group and phase structure explain more observed variation: Model D R-squared is `0.336`, and Model E R-squared is `0.691`.

### Caveats

- Local daily and durable/household categories are more baseline-sensitive.
- These results are descriptive and should not be read as causal evidence.

## Interpretation

The project suggests that visitor arrivals and retail recovery should not be treated as interchangeable recovery indicators. For post-reopening Hong Kong, the more useful analytical question is whether visitor-facing retail categories recovered in alignment with returning visitor flows, rather than whether visitor counts recovered in isolation.

## Limitations

- Descriptive, not causal.
- Monthly aggregation.
- No transaction-level data.
- No tourist-spending microdata.
- Category grouping requires judgment.
- Local daily/durable interpretations are baseline-sensitive.
- Post E has a high-condition-number caveat.
- Hotel and event modules are excluded.

## Portfolio Relevance

This project demonstrates how official public data can be converted into a reproducible category-level business analytics workflow. It combines API extraction, recovery-index construction, segmentation, descriptive regression, baseline sensitivity checks, and dashboard communication. It is positioned as a research pilot / portfolio candidate, not a production dashboard or policy evaluation.
