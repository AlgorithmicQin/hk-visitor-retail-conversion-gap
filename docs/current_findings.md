# Current Findings Draft

The completed visitor-retail pilot suggests there is enough descriptive evidence to continue, with a tighter focus on category and group recovery paths rather than total retail alone.

Conversion gap sign convention:

```text
conversion_gap = retail_recovery_index - visitor_recovery_index
```

- Positive gap: retail recovered above visitor recovery.
- Negative gap: retail lagged visitor recovery.
- Near zero: retail was broadly aligned with visitor recovery.

## Total Retail Masks Category Structure

Total retail is a useful benchmark, but it masks substantial category-level variation. The category and group results show different recovery paths across tourist-sensitive, local daily, durable/household, and residual categories.

The main finding is not simply total retail versus visitor arrivals. The more useful signal is how different retail categories aligned with visitor recovery across phases.

## Tourist-Sensitive Categories Reversed Over Time

The `tourist_sensitive_discretionary` group recovered above visitor recovery during early reopening, then moved below visitor recovery in the later phases.

Group average gaps:

- `early_reopening`: `+22.24`.
- `normalization`: `-2.93`.
- `recent_adjustment`: `-12.38`.

This suggests a phase-specific category pattern rather than a stable visitor-retail relationship.

## Recent Tourist-Sensitive Underperformance Is Broad-Based

The tourist-sensitive drilldown shows recent underperformance across all seven mapped tourist-sensitive categories on average in `recent_adjustment`:

- Department stores: `-24.46`.
- Footwear, allied products and other clothing accessories: `-17.81`.
- Jewellery, watches and clocks, and valuable gifts: `-12.48`.
- Clothing, footwear and allied products: `-9.18`.
- Medicines and cosmetics: `-7.71`.
- Wearing apparel: `-7.61`.
- Optical shops: `-6.03`.

This strengthens the descriptive evidence that the recent tourist-sensitive pattern is not just a single-category artifact.

## Local Daily Remains Modestly Above Visitor Recovery

Under the primary 2018-2019 average baseline, `local_daily_consumption` remains modestly above visitor recovery in recent adjustment. Its group average recent adjustment gap is `+6.16`.

Selected category average gaps in recent adjustment:

- Fruits and vegetables, fresh: `+42.31`.
- Alcoholic drinks and tobacco: `+27.36`.
- Supermarkets: `+9.76`.
- Other food not elsewhere classified: `+9.75`.
- Supermarkets and supermarket sections of department stores: `+9.32`.
- Bread, pastry, confectionery and biscuits: `-22.04`.

Recent outperformance is not universal within the group, and the same-month baseline sensitivity check weakens a simple local-daily outperformance interpretation. The category pattern still suggests local daily consumption should be interpreted separately from tourist-sensitive discretionary retail.

## Durable Household Is Near Alignment With Mixed Internal Behavior

Under the primary 2018-2019 average baseline, `durable_household` is close to visitor recovery in recent adjustment, with a group average recent adjustment gap of `+0.98`, but internal category behavior is mixed.

Selected category average gaps in recent adjustment:

- Electrical goods and other consumer durable goods not elsewhere classified: `+8.83`.
- Consumer durable goods: `+1.44`.
- Fuels: `-5.02`.
- Motor vehicles and parts: `-9.33`.
- Furniture and fixtures: `-18.90`.

This group should be treated as a separate recovery path rather than as tourist-sensitive retail.

## Baseline Sensitivity Check

The primary results use Baseline A: 2018-2019 average equals `100`.

The sensitivity check uses Baseline B: 2019 same-month equals `100`. Under Baseline B, each month is compared with the same calendar month in 2019.

Baseline B recent adjustment group gaps:

- `tourist_sensitive_discretionary`: `-16.00`.
- `local_daily_consumption`: `-3.95`.
- `durable_household`: `-5.37`.
- `benchmark_total`: `-5.84`.
- `residual_other`: `+24.89`, but interpretively weak.

The tourist-sensitive reversal is robust to baseline choice. Under Baseline B, `tourist_sensitive_discretionary` still moves from early outperformance (`+19.02`) to recent underperformance (`-16.00`).

All seven tourist-sensitive categories remain below visitor recovery on average in recent adjustment under Baseline B:

- Tourist-sensitive categories below visitor recovery: `7 of 7`.

Baseline B weakens any simple claim that local daily or durable/household categories consistently recovered above visitor recovery. Under the same-month baseline, `local_daily_consumption` is closer to visitor recovery but slightly negative on average (`-3.95`), and `durable_household` is also slightly negative (`-5.37`) with mixed internal behavior.

The narrower robustness-driven finding is that tourist-sensitive discretionary retail shows recent underperformance relative to visitor recovery across both baseline choices, while local daily and durable/household groups are more baseline-sensitive and closer to visitor recovery.

## Regression Supports Group And Phase Structure

The regression layer is consistent with group and phase structure being important for interpretation in a descriptive sense.

Visitor recovery alone has weak explanatory fit for category retail recovery:

- Model A adjusted R-squared: `0.086`.

Adding calendar month, phase, and retail group interactions improves fit:

- Model D adjusted R-squared: `0.330`.

The gap model with group, calendar month, and phase has stronger descriptive fit:

- Model E adjusted R-squared: `0.688`.

This suggests that category-specific recovery pattern and phase are important for interpreting visitor-retail alignment.

## Post-Reopening Group Differences Remain Visible

In the post-reopening gap model, group coefficients are large and directionally consistent with the descriptive tables, though this model is limited by a high condition number.

Group coefficients relative to `tourist_sensitive_discretionary`:

- `local_daily_consumption`: `+18.06`, p-value `< 0.001`.
- `durable_household`: `+13.62`, p-value `< 0.001`.
- `residual_other`: `+35.12`, p-value `< 0.001`, but interpretively weak.
- `benchmark_total`: `+10.99`, p-value `0.004`, but it is a benchmark rather than a behavioral category.

Post E adjusted R-squared is `0.441`, with status `high_condition_number`. It should be treated as a limited descriptive diagnostic, not as a standalone result.

## Lag Evidence Is Mixed

The lag model does not provide a clean lag story. The lag 1 term is not meaningful, while the lag 2 term is negative and statistically distinguishable from zero.

Lag model visitor terms:

- `visitor_recovery_index`: `+0.285`, p-value `< 0.001`.
- `visitor_recovery_lag1`: `+0.029`, p-value `0.598`.
- `visitor_recovery_lag2`: `-0.134`, p-value `0.003`.

This should not be overclaimed. The current lag evidence is best read as a robustness check rather than a core finding.

## Working Thesis

The current descriptive evidence suggests that Hong Kong visitor recovery is associated with retail recovery, but the alignment differs materially by retail category group and recovery phase.

The current working thesis is:

```text
Total retail masks category-specific recovery paths. Tourist-sensitive discretionary categories moved from early reopening outperformance to recent underperformance relative to visitor recovery, and this reversal is robust to the same-month 2019 baseline check. Local daily and durable/household categories are closer to visitor recovery and more baseline-sensitive, so they should be interpreted more cautiously.
```

This remains a descriptive thesis. It should not be framed as a causal claim.
