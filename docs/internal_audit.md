# Internal Documentation Audit

Audit date: 2026-05-26

Scope reviewed:

- `docs/methodology.md`
- `docs/limitations.md`
- `docs/current_findings.md`
- `outputs/tables/regression_model_summary.csv`
- `outputs/tables/regression_coefficients.csv`
- `outputs/tables/regression_robustness_notes.md`
- `outputs/tables/retail_group_phase_gaps.csv`
- `outputs/tables/tourist_sensitive_drilldown.csv`
- `outputs/tables/local_daily_durable_drilldown.csv`

This audit did not change analysis results.

## Overall Finding

The current documentation is broadly supported by the completed visitor-retail outputs. The docs are scoped correctly as visitor-retail category mismatch work, and they consistently avoid causal interpretation.

The main improvements needed are precision and traceability: several findings should include exact values from the output tables, and the methodology should mention two implemented regression-panel fields that are currently omitted from the panel-column list.

## Unsupported Claims

No major unsupported claims were found in the current docs.

The following limitation statements are not directly estimated in the output tables, but they are valid scope limitations based on absent data fields:

- No transaction-level data.
- No tourist spending microdata.
- No controls for prices, inflation, exchange rates, resident income, retail supply changes, category reclassification, policy changes, or source-market visitor mix.
- Monthly aggregation can hide within-month timing differences.

These are safe as limitations because they describe what the dataset does not contain, not empirical results.

## Overstated Claims

The docs are mostly cautious. A few phrases should be made slightly more precise before public release:

- `current_findings.md`: “there is enough descriptive evidence to continue” is a project judgment, not a direct table output. It is reasonable, but should be framed as an internal assessment supported by the category, group, phase, and regression outputs.
- `current_findings.md`: “Post-reopening group differences remain visible” is supported, but the same section should more prominently state that `Post E` has a high condition number.
- `current_findings.md`: “durable/household categories moved closer to alignment” is supported at the group level, but the category-level durable table is mixed. The doc already says mixed internal behavior; this should stay close to any mention of durable alignment.

## Wording To Weaken

Suggested weaker phrasing:

- Replace “supports the importance of group and phase structure” with “is consistent with group and phase structure being important for interpretation.”
- Replace “group coefficients remain materially different” with “group coefficients are large and directionally consistent with the descriptive tables, though `Post E` is limited by a high condition number.”
- Replace “strongest current thesis” with “current working thesis.”

These changes would reduce the risk that readers interpret descriptive regression as a stronger research design.

## Places To Add Exact Numbers

The current docs would be more auditable if these exact values were added.

### Phase Group Gaps

From `outputs/tables/retail_group_phase_gaps.csv`, average conversion gaps:

| Group | early_reopening | normalization | recent_adjustment |
| --- | ---: | ---: | ---: |
| tourist_sensitive_discretionary | 22.24 | -2.93 | -12.38 |
| local_daily_consumption | 36.11 | 16.10 | 6.16 |
| durable_household | 41.55 | 11.50 | 0.98 |
| residual_other | 49.83 | 33.35 | 31.59 |
| benchmark_total | 32.59 | 8.73 | 0.14 |

These values support:

- Tourist-sensitive categories moved from early outperformance to recent underperformance.
- Local daily stayed above visitor recovery through recent adjustment.
- Durable/household moved close to alignment in recent adjustment.
- Residual remains high but interpretively weak.

### Tourist-Sensitive Drilldown

From `outputs/tables/tourist_sensitive_drilldown.csv`, recent adjustment average gaps:

| Category | recent_adjustment avg gap |
| --- | ---: |
| Department stores | -24.46 |
| Footwear, allied products and other clothing accessories | -17.81 |
| Jewellery, watches and clocks, and valuable gifts | -12.48 |
| Clothing, footwear and allied products | -9.18 |
| Medicines and cosmetics | -7.71 |
| Wearing apparel | -7.61 |
| Optical shops | -6.03 |

These values support the claim that all seven tourist-sensitive categories lagged visitor recovery on average in recent adjustment.

### Local Daily And Durable Drilldown

From `outputs/tables/local_daily_durable_drilldown.csv`, selected recent adjustment average gaps:

Local daily:

- Fruits and vegetables, fresh: 42.31.
- Alcoholic drinks and tobacco: 27.36.
- Supermarkets: 9.76.
- Other food not elsewhere classified: 9.75.
- Supermarkets and supermarket sections of department stores: 9.32.
- Bread, pastry, confectionery and biscuits: -22.04.

Durable/household:

- Electrical goods and other consumer durable goods not elsewhere classified: 8.83.
- Consumer durable goods: 1.44.
- Fuels: -5.02.
- Motor vehicles and parts: -9.33.
- Furniture and fixtures: -18.90.

These values support the current “mixed internal behavior” wording for durable/household.

### Regression Fit

From `outputs/tables/regression_model_summary.csv`:

| Model | Adjusted R-squared | Status |
| --- | ---: | --- |
| A | 0.086 | ok |
| B | 0.119 | ok |
| C | 0.146 | ok |
| D | 0.330 | ok |
| E | 0.688 | ok |
| Post D | 0.239 | ok |
| Post E | 0.441 | high_condition_number |
| Lag | 0.260 | ok |

These values support the claim that visitor recovery alone has weak explanatory fit and that group/phase structure improves descriptive fit.

### Regression Coefficients

From `outputs/tables/regression_coefficients.csv`, `Post E` group coefficients relative to `tourist_sensitive_discretionary`:

- `local_daily_consumption`: 18.06, p-value < 0.001.
- `durable_household`: 13.62, p-value < 0.001.
- `residual_other`: 35.12, p-value < 0.001.
- `benchmark_total`: 10.99, p-value 0.004.

Important caveat: `Post E` has a high condition number, so these should be presented as limited descriptive coefficients.

Lag model visitor terms:

- `visitor_recovery_index`: 0.285, p-value < 0.001.
- `visitor_recovery_lag1`: 0.029, p-value 0.598.
- `visitor_recovery_lag2`: -0.134, p-value 0.003.

These values support the “mixed lag evidence” wording.

## Sign Convention

The sign convention is clearly stated in `docs/methodology.md` and indirectly repeated in `docs/limitations.md`.

It should also be repeated near the top of `docs/current_findings.md`, because that document discusses positive and negative gaps extensively.

Recommended text:

```text
Conversion gap = retail recovery index - visitor recovery index. Positive values mean retail recovered above visitor recovery; negative values mean retail lagged visitor recovery; near-zero values mean broad alignment.
```

## Methodology Versus Implemented Scripts

One minor mismatch was found.

`docs/methodology.md` lists the regression panel columns as:

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

The implemented `outputs/tables/regression_panel.csv` also includes:

- `visitor_recovery_lag1`
- `visitor_recovery_lag2`
- `excluded_from_behavioral_interpretation`

The methodology should mention these additional fields, especially because the lag model uses the lag fields and benchmark handling uses the exclusion flag.

No mismatch was found in the stated regression formulas. The formulas in `docs/methodology.md` match `outputs/tables/regression_model_summary.csv`.

## Public GitHub Safety

The docs are mostly safe for a public GitHub repo because they:

- Avoid causal claims.
- State that hotel and event modules are not included.
- Treat `benchmark_total` as a benchmark rather than a behavioral group.
- Flag `residual_other` as interpretively weak.
- Flag the post-reopening model high condition number.
- Describe regressions as descriptive.

Before public release, the docs should add exact output numbers in `current_findings.md` and repeat the conversion-gap sign convention there. This would make the findings easier to verify from the output tables.

## Project Scope Check

The current docs remain scoped correctly as visitor-retail category mismatch only.

They do not add hotel claims, event claims, dashboard framing, or tourism-program evaluation. Hotel and event modules are mentioned only as missing or future modules, which is appropriate.

## Recommended Follow-Up Edits

Do not change results. Recommended documentation-only edits:

1. Add the conversion-gap sign convention near the top of `docs/current_findings.md`.
2. Add exact phase gap values for the main group findings.
3. Add exact tourist-sensitive recent adjustment average gaps for all seven categories.
4. Add exact regression fit values and `Post E` high-condition-number caveat beside the regression interpretation.
5. Update `docs/methodology.md` to include `visitor_recovery_lag1`, `visitor_recovery_lag2`, and `excluded_from_behavioral_interpretation` in the implemented regression panel fields.
6. Slightly weaken public-facing wording around “supports” and “materially different” so the docs remain firmly descriptive.
