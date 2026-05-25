# Pilot Notes

## Purpose

Validate whether Hong Kong monthly visitor, retail, and hotel data can support a visitor-to-retail and visitor-to-hotel recovery mismatch analysis.

The pilot should answer one narrow question: is there enough consistent monthly signal to justify a fuller project?

## Partial Hotel Data Warning

The pilot is allowed to run with partial hotel data. A hotel file may contain occupancy only, room rate only, or both. Each pilot run must report which hotel indicators are missing before interpreting visitor-hotel gaps.

Do not treat a missing hotel indicator as evidence of recovery mismatch. It is a data availability limitation that must be carried into the go/no-go decision.

## Go / No-Go Checklist

Mark each item after running the notebooks.

| Check | Go condition | Status | Notes |
| --- | --- | --- | --- |
| Monthly coverage | Visitor, retail, and hotel datasets cover 2018 onward with enough overlap for baseline and recovery periods. | TBD |  |
| Baseline quality | 2018-2019 values are present and stable enough to calculate average baseline indices. | TBD |  |
| Date consistency | Source periods can be standardized to one monthly date format without ambiguous parsing. | TBD |  |
| Metric consistency | Retail and hotel definitions are consistent over time or documented well enough to adjust. | TBD |  |
| Missing data | Missing months are limited, explainable, and not concentrated in key recovery windows. | TBD |  |
| Category usefulness | Retail categories are detailed enough to compare tourism-sensitive and less tourism-sensitive segments. | TBD |  |
| Hotel usefulness | Available occupancy and/or room rate fields provide a meaningful hotel recovery measure, and missing hotel indicators are reported. | TBD |  |
| Signal strength | Visitor recovery indices diverge visibly from retail and/or hotel recovery indices for meaningful periods. | TBD |  |
| Interpretability | Conversion gaps can be explained without overclaiming causality. | TBD |  |
| Output reproducibility | Processed tables and figures can be regenerated from raw files and mappings. | TBD |  |

## Go Criteria

Continue to a fuller project only if:

- All three data families have overlapping monthly coverage including 2018-2019.
- At least one retail metric and one hotel metric can be indexed consistently.
- Visitor-retail or visitor-hotel gaps show persistent, interpretable divergence rather than one-off noise.
- Missing data does not drive the main pattern.
- Source definitions and transformations can be documented clearly.

## No-Go Criteria

Pause or redesign the project if:

- A 2018-2019 baseline cannot be constructed.
- Monthly retail or hotel data is unavailable, too sparse, or definitionally unstable.
- Gaps are dominated by missing months, source breaks, or unit mismatches.
- The analysis would require invented values or undocumented adjustments.
- The pilot cannot distinguish a real mismatch from data collection artifacts.

## Notes From Pilot Runs

Add observations here after each notebook run.

- 
