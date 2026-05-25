# Methodology Draft

This pilot tests whether monthly Hong Kong visitor arrivals and retail sales data show visitor-retail recovery mismatch patterns. It is a descriptive analysis, not a causal design.

## Data Sources

The current visitor-retail layer uses official Hong Kong Census and Statistics Department monthly public data:

- Monthly visitor arrivals.
- Monthly retail sales by retail outlet category.

The normalized working files are:

- `data/raw/visitor_arrivals.csv`
- `data/raw/retail_sales.csv`

Hotel data and event data are not included in the current visitor-retail results.

## C&SD API Extraction

The C&SD web-table download links returned HTML pages during setup rather than direct CSV files. The pilot therefore uses C&SD API POST JSON responses saved as raw files, then preprocesses those JSON payloads into normalized CSV files.

The preprocessing step extracts monthly records from the JSON payloads and writes:

- `Month` and `Total arrivals` for visitor arrivals.
- `Month`, `Retail category`, and `Sales value` for retail sales.

The raw JSON payloads are not overwritten. The normalized CSV files are generated from those official payloads and used by the analysis scripts.

## Baseline

The primary recovery indices use the 2018-2019 monthly average as the baseline. This is Baseline A. It gives a pre-COVID reference period and avoids using a single month as the comparison point.

For each series, the baseline is:

```text
baseline = average monthly value from 2018-01 through 2019-12
```

## Baseline Sensitivity

The pilot also tests Baseline B as a robustness check:

```text
baseline_b = value for the same calendar month in 2019
```

Under Baseline B, each month is compared with its 2019 same-month value. For example, a March 2025 recovery index is calculated against March 2019, not against the full 2018-2019 average.

This sensitivity check is used to test whether the main visitor-retail mismatch patterns depend on using the 2018-2019 average baseline. It helps separate broad recovery-pattern findings from findings that are more baseline-sensitive.

Both baselines use the same conversion gap formula:

```text
conversion_gap = retail_recovery_index - visitor_recovery_index
```

## Recovery Index Formula

The recovery index is calculated as:

```text
recovery_index = observed_monthly_value / 2018_2019_average * 100
```

A value of `100` means the monthly observation is equal to the 2018-2019 monthly average for that series. Values above `100` recovered above that baseline, and values below `100` recovered below that baseline.

## Conversion Gap Formula

The visitor-retail conversion gap is:

```text
conversion_gap = retail_recovery_index - visitor_recovery_index
```

Sign interpretation:

- Positive gap: retail recovered above visitor recovery.
- Negative gap: retail lagged visitor recovery.
- Near zero: retail was broadly aligned with visitor recovery.

This formula is used for category-level and group-level analysis.

## Retail Category Grouping

Retail categories are manually mapped into groups in `config/retail_category_groups.yaml`:

- `tourist_sensitive_discretionary`
- `local_daily_consumption`
- `durable_household`
- `residual_other`
- `benchmark_total`

The grouping is a pilot interpretation layer. It is intended to compare broad category-specific recovery patterns, not to create definitive classifications. Ambiguous categories are marked in the YAML notes.

`benchmark_total` contains `Total` retail and is treated as a benchmark, not a behavioral category. Group interpretation is based on the behavioral groups only.

`residual_other` is retained for completeness, but it is interpretively weak because it contains broad or mixed categories.

## Phase Definitions

The analysis separates months into recovery phases:

- `pre_covid_baseline`: 2018-01 to 2019-12.
- `covid_disruption`: 2020-01 to 2022-12.
- `early_reopening`: 2023-01 to 2023-12.
- `normalization`: 2024-01 to 2024-12.
- `recent_adjustment`: 2025-01 to the latest available month.

These phases are used to compare whether visitor-retail alignment is stable or phase-specific.

## Drilldown Analysis

The drilldown layer examines category-level gaps within selected groups.

For `tourist_sensitive_discretionary`, the pilot checks whether recent underperformance is broad-based or concentrated in one or two categories.

For `local_daily_consumption` and `durable_household`, the pilot checks which categories explain group-level outperformance or alignment, and whether those patterns are broad-based or concentrated.

Latest-month gaps are compared with recent-period averages to flag cases where a single month may not represent the broader recovery path.

## Regression Models

The regression layer uses a monthly category panel with:

- month
- retail category
- retail group
- retail recovery index
- visitor recovery index
- conversion gap
- phase
- month number
- year
- calendar month
- visitor recovery lag 1
- visitor recovery lag 2
- excluded-from-behavioral-interpretation flag

Baseline descriptive models:

- Model A: `retail_recovery_index ~ visitor_recovery_index`
- Model B: `retail_recovery_index ~ visitor_recovery_index + C(calendar_month)`
- Model C: `retail_recovery_index ~ visitor_recovery_index + C(calendar_month) + C(phase)`
- Model D: `retail_recovery_index ~ visitor_recovery_index * C(retail_group) + C(calendar_month) + C(phase)`
- Model E: `conversion_gap ~ C(retail_group) + C(calendar_month) + C(phase)`

Post-reopening models use 2023-01 to the latest available month:

- Post D: `retail_recovery_index ~ visitor_recovery_index * C(retail_group) + C(calendar_month)`
- Post E: `conversion_gap ~ C(retail_group) + C(phase) + C(calendar_month)`

Lag model:

- `retail_recovery_index ~ visitor_recovery_index + visitor_recovery_lag1 + visitor_recovery_lag2 + C(retail_group) + C(calendar_month) + C(phase)`

## Descriptive Regression, Not Causal Inference

These models test whether visitor recovery is associated with retail category recovery and whether the relationship differs across retail groups and phases.

They do not identify causal effects. The current dataset does not include transaction-level spending, tourist spending microdata, prices, resident demand, exchange rates, policy controls, event data, or hotel indicators. The models should therefore be read as descriptive evidence about alignment and mismatch patterns.
