# Limitations Draft

This pilot is intentionally narrow. It is designed to test whether the visitor-retail category mismatch question has enough descriptive signal to continue.

## No Causal Claims

The analysis does not show that visitor arrivals changed retail sales. It only describes whether visitor recovery is associated with retail recovery, and whether retail categories recovered above, below, or close to visitor recovery.

## Monthly Aggregation

All analysis is monthly. Monthly aggregation can hide within-month timing differences, short events, holidays, visitor mix changes, and category-specific volatility.

## No Transaction-Level Data

The retail data are aggregate category totals. The pilot does not observe individual transactions, customer origin, payment method, basket composition, or store-level variation.

## No Tourist Spending Microdata

The analysis cannot separate tourist spending from resident spending within a retail category. A category that appears aligned with visitor recovery may still include substantial local demand.

## Category Grouping Subjectivity

The retail grouping layer is manually assigned. It is useful for a pilot comparison, but some categories are ambiguous and could reasonably be grouped differently.

Examples include medicines and cosmetics, optical shops, alcoholic drinks and tobacco, fuels, and books/newspapers/stationery/gifts.

## Residual Other Risk

`residual_other` is interpretively weak. It includes broad or mixed categories whose composition is less clear. It should not drive the main thesis, even when it shows large positive gaps.

## Benchmark Total Is Not Behavioral

`benchmark_total` contains total retail. It is useful as an overall comparison line, but it is not a behavioral category group and should not be ranked with the category groups.

## Post-Reopening Model Limitation

The post-reopening gap model has a high condition number. This suggests multicollinearity or limited independent variation when phase and calendar-month controls are included in the shorter post-reopening sample.

That model should be read as a limited diagnostic, not as a standalone result.

## Mixed Lag Evidence

Lag checks are mixed. The lag 1 visitor recovery term is not meaningful in the fitted model, while lag 2 is statistically distinguishable from zero but negative. This is not strong enough to claim a stable lag structure.

## Baseline Sensitivity

Local daily consumption and durable/household interpretations are baseline-sensitive. Under the 2019 same-month baseline, both groups are closer to visitor recovery and slightly negative on average in recent adjustment, rather than clearly above visitor recovery.

The most robust current finding is tourist-sensitive recent underperformance, not a universal local-consumption outperformance story.

## Missing Hotel And Event Modules

Hotel data and event data are not included in the current results. The visitor-retail layer should not be used to make statements about hotel performance, event activity, or tourism-program evaluation.

## Omitted Context

The current dataset does not control for prices, inflation, exchange rates, resident income, retail supply changes, category reclassification, policy changes, or source-market visitor mix.

These omissions limit interpretation and reinforce that the current results are descriptive.
