# Target validity and data gaps (E60, written before any E60 candidate was scored)

**Sources:**
- `runner/t1_target.py` → `out/target_analysis.json`, `out/target_by_quarter.csv` (labels only);
- the E59 audit.

## 1. What the current target measures

**T43:** HIGH when Balance Luzon SWS hunger > 11.3% **and** the province's PSA food YoY or food-minus-headline YoY is above its own 2021–2022 60th percentile.

| Finding | Evidence |
|---|---|
| The hunger condition changed state 5 times in 21 labelled quarters, all before 2023-Q4. From 2023-Q4 it holds in every quarter. | `target_by_quarter.csv` |
| **T43 = PS (provincial food-price pressure) on 100% of the 50 evaluation rows.** It differs only in 2021–2023 (29 rows, where hunger ≤ 11.3%). | `T43_equals_PS` |
| On the evaluation rows, **13 of 18 HIGH rows are set by the food-minus-headline gap alone**, 4 by both conditions, and 1 by food YoY alone. | `which_condition_makes_HIGH_eval` |
| Gap thresholds are small and province-specific (−0.56 to +0.92 points), so the label is sensitive to tenths of a percentage point. | E40 `label_spec.json` |
| About 59% of the label's variance on the evaluation rows is between provinces within a quarter, so the label does discriminate provinces. | `within_quarter_variance_share` |
| Class balance on the evaluation rows: 18 HIGH / 32 LOW. 7 of 10 quarters have both classes; 3 quarters (2025-Q4, 2026-Q1, 2026-Q3) are all LOW. | `evaluation_rows` |
| Prevalence by year (T43 / PS) | 2021 0.13 / 0.40; 2022 0.00 / 0.40; 2023 0.15 / 0.85; 2024 0.40 / 0.40; 2025 0.45 / 0.45; 2026 0.07 / 0.07 |

**Conclusion.** In the evaluable period, the target measures **whether a province's food inflation runs ahead of headline inflation** (or above its usual level), during a period of elevated regional hunger. It depends almost entirely on one indicator family, provincial CPI.

## 2. Does it validly represent food-insecurity risk?

**Partially, as a risk indicator.**
- It combines the two sources Chapter I names (SWS hunger and PSA food prices).

**But it is not validated against food insecurity:**
1. No provincial outcome is used. Hunger is one Balance Luzon value, and Balance Luzon extends beyond CALABARZON.
2. Chapter I describes the label as "anchored to the FAO SDG 2.1.2 baseline established by the DOST-FNRI ENNS". T43's thresholds are 2021–22 percentiles, not FNRI/FIES anchors.
3. Chapter I's own composite is the additive Eq. 3 form (served by E38). That form is saturated: 40/45 HIGH in 2024–26.

## 3. Strongest defensible target available now

**No authoritative, quarterly, provincial food-insecurity outcome exists in the project data:**

| Outcome | Coverage |
|---|---|
| SWS hunger | quarterly, regional only |
| PSA subsistence incidence | provincial, 2021 and 2023 only |
| FNRI FIES | regional, survey years |
| CBMS / provincial FIES | not available |

**A provincial food-insecurity label cannot be constructed** without inventing measurements.

The strongest defensible choice is therefore to **keep T43, renamed accurately as the "food-stress risk indicator"**: elevated regional hunger together with provincial food-price pressure. It should be reported with:
- (a) the regional SWS hunger series as a separate observed indicator;
- (b) the explicit statement that, in 2024–2026, its provincial variation is food-price pressure.

**PS is kept as the training label of the price learner.** It is observed every quarter, including 2021–2023, and it is what the evaluated variation consists of.

E60 does **not** change the target. That would require the adviser, and changing it after five years of examining these quarters would not be defensible.

## 4. Can the target support useful forecasting?

**Positives and negatives:** 18 / 32 evaluation rows, and 31 PS-HIGH training rows by the last origin. That is enough to train a regularized price learner.

**What can be evaluated:**

| Quantity | Available | Consequence |
|---|---|---|
| Independent evaluation quarters | 10 | small |
| Rising-stress (onset) episodes | 4 | very small |
| Hunger-condition changes in the evaluable window | 0 | hunger-driven risk cannot be forecast or evaluated at all |

## 5. Data gaps and the minimum to close them

| Gap | Effect | Minimum to close it |
|---|---|---|
| No provincial food-insecurity outcome | the target is a proxy | CBMS FIES by LGU (DILG/PSA), or provincial FIES/NNS tables (FNRI) for at least two survey years |
| Hunger only regional, posted 1–2 months late | stale hunger; 2024-Q2 misses | issue forecasts after each SWS release (adviser decision); a provincial hunger proxy would need a new source |
| 10 evaluation quarters, one hunger regime | no generalization claim | continue frozen prospective forecasts (2027 onward); about 16 quarters needed even at 0.85 true accuracy |
| News corpus: titles only, retrospective, 34% province-attributed, food/shock queries only | NLP signal near zero (E59) | addressed in E60 (`NEWS_PIPELINE_AUDIT.md`) |
| BSP remittances end 2025-Q4 | OFW inputs missing for 2026 | authorize the data refresh |
| No fish-kill event series | fisheries trigger relies on production and news | BFAR fish-kill bulletins (manual compilation) |
