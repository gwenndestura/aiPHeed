# Y14: what is being forecast, and what can validate it

## 1. The thesis objective

aiPHeed's objective is to forecast **food-insecurity risk** for DA Region IV-A (CALABARZON) two quarters ahead (Lead 2), so that risk can be acted on early. Food prices are one contributing driver among five, not the objective. The five approved driver labels are unchanged:

1. Market / Prices
2. Climate Stress
3. Fish Kill
4. Employment
5. OFW Remittance

## 2. The two existing formulations, and how they differ

| | FIRI v2 | P0H4 |
|---|---|---|
| What it is | A 0–1 **composite risk index** (not a probability) over six domains: affordability, vulnerability, climate and production, household economy, news, regional hunger | A **probability** of the joint event T43c = Balance Luzon (BL) hunger > 11.3% **and** a provincial food-price condition |
| What it claims to measure | Relative food-insecurity risk | A specific hunger-and-price-stress event |
| Observed outcome that can validate it | **BL involuntary hunger > 11.3%** in the target quarter (target R in `FIRI_LEAD2_FEASIBILITY`). The index itself has no observed counterpart. | T43c. Its price half is a CPI condition, which is a **price outcome, not a food-insecurity outcome**. |
| Relation to the thesis objective | Close in intent | Partly off-objective: half of its target is food-price stress |

**Consequence.** For the objective "forecast food insecurity", the only defensible validation target in the project is **observed hunger**. P0H4's T43c mixes in a price event, which the prior research (Y7, Y9, Y12) showed is the harder half and is not itself food insecurity. This experiment therefore evaluates forecasts **against observed hunger**, and keeps P0H4 out of the primary comparison.

## 3. Observed food-insecurity outcomes available (`DATA_AUDIT.md`)

| Outcome | Provider | Frequency | Geography | Usable as a Lead-2 target? |
|---|---|---|---|---|
| **Involuntary hunger** (share of families who experienced hunger at least once in the past 3 months) | SWS | **Quarterly**, 1998+ (with gaps) | NCR, Balance Luzon, Visayas, Mindanao | **Yes. The only one.** |
| Moderate or severe food insecurity (FIES, SDG 2.1.2) | PSA / FNRI | Irregular: Region IV-A has **one** value (19.1%); national has 3 | Region | No |
| Subsistence (food-poverty) incidence | PSA FIES | 2006, 2009, 2012, 2015, 2018, 2021, 2023 | Province | No. Values are 0.2–4.7%, with CV up to 59%; triennial. |
| Self-rated food poverty | SWS | Quarterly | Areas | Not in the project, and not acquired (SWS release tables) |

## 4. The target used here

**Primary target (TFI-2).** y(t) = 1 if observed BL involuntary hunger in quarter t + 2 is greater than 11.3%. The forecast is issued at O(t) = the first day of quarter t + 1.

- This is FIRI's existing validation target R. It is **not** a new definition.
- 11.3 is the project's existing threshold.
- Observed hunger is the mean of the non-commissioned SWS rounds in the quarter. The 2021+ production series and the pre-2021 area series are those used throughout the research.

**Secondary target.** The continuous BL hunger level in quarter t + 2 (mean absolute error). It is reported for information, not used for the rules.

## 5. Limitations of the target (stated, not hidden)

1. **Severity.** Involuntary hunger measures the **severe end** of food insecurity (going without food). Milder food insecurity (worrying, reducing quality or quantity) is not observed quarterly anywhere in the project.
2. **Geography.** Balance Luzon covers all Luzon regions outside NCR, not Region IV-A alone. Every province gets the same regional outcome, so there is **no observed provincial food-insecurity outcome**. Provincial differences in any forecast are unvalidated.
3. **Measurement noise.** About 300 BL respondents per round, ±4–6 points at 95%. Two of the 2021+ LOW quarters are exactly 11.3 (X1, Y1).
4. **Sample size.** There are 17 Lead-2 targets with a known outcome in 2021–2026 (12 HIGH, 5 LOW) and one class change. Independent development uses 1998–2020.

## 6. The seven rules for this target

The rules are kept **unchanged**. Their compatibility with a regional quarterly target is recorded here and not redefined:

| Rule | Compatible with TFI-2? |
|---|---|
| R1 ≥ 10 quarters and ≥ 40 rows | **Structurally incompatible for 2021–2026.** One regional outcome per quarter gives 17 rows. As written, R1 cannot pass until 40 quarters are observed, around 2031. Repeating the regional row for 5 provinces would duplicate observations, which is forbidden. **R1 is reported as FAIL**, not reinterpreted. |
| R2, R3, R6 | Compatible (classification at 0.50) |
| R4 accuracy > always-LOW and > persistence | Compatible. Persistence = the newest published BL reading > 11.3. |
| R5 Brier < persistence and < climatology, cluster p < 0.10 | Compatible. One row per quarter, so the cluster is the quarter. |
| R7 thirds ≥ 0.60 and leave-one-quarter-out ≥ 0.70 | Compatible |

**Consequence:** no candidate can pass all seven rules on the 2021–2026 regional target, because of R1. This is a fact about the sample size, not about any model. A Lead-2 food-insecurity forecast can only be called reliable after enough sealed prospective quarters accumulate, or under a formally revised rule set that the thesis committee approves. It is not redefined here.
