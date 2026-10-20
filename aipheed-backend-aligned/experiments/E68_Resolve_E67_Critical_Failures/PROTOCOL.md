# E68 protocol: corrections for E67's critical failures

**Date:** 2026-10-20
**Branch:** `resolve-e67-critical-failures`, created from `best-model-objectives-1-4-lead2` @ f8c4416.
**Freezing:** frozen before any E68 arm is scored. The SHA-256 of this file (LF-normalised) is in `runner/PROTOCOL_SHA256.txt`.
**Requirement basis:** Chapter I §1.5 and §1.7 (verbatim in E25 `thesis_source/CHAPTER_I_verbatim.txt`, re-verified in E67).

## 0. Evidence status and honesty rules (declared before scoring)

- **Development evidence only.** Every E68 arm is evaluated on the same 50 Lead-2 province-quarters (10 origins, targets 2024-Q2..2026-Q3) that E56–E67 already examined. These rows cannot be an unseen test, so no E68 result may be called validated or used to claim the 75% goal as demonstrated.
- **Unseen period.** The only unseen evaluation period the data permit is the future: targets 2026-Q4 and 2027-Q1, whose outcomes are not published on 2026-10-20. Every E68 arm's forecasts for those targets are **sealed** in `sealed/prospective.csv` (with SHA-256) before any outcome exists, and they are to be scored later under §6.
- **Data limits.** No pre-2021 data. Data authorized to 2026-10-14. No PSA, BSP or SWS "latest" web searches; PAGASA pages only for climate status.
- **Frozen artifacts.** No change to thresholds of the approved target T43, to frozen records, or to sealed files of E38–E67.

## 1. Fixed design (inherited from E56/E57/E67, unchanged)

- **Origins:** the 10 E57 origins t = 2023-Q4..2026-Q1, target t+2. Forward origins 2026-Q2 and 2026-Q3 (sealed, not scored).
- **Procedure:** E56-TUNED (`E67 runner/e67_lib.tuned_forecast`): P(HIGH) = P_hunger × P_price, nested per-origin selection over 72 configurations by embargoed forward log-loss on training targets only.
- **Scorer:** `E66 runner/e66_lib.py`. Goal test: E67 G1–G5 (E67 `runner/r3_goal.py`).
- **Reference:** A0 = E56-TUNED, which must reproduce the sealed E57 forecasts to 1e-9.

## 2. Corrections tested on the approved target T43 (each motivated by a documented E62–E67 defect, not by results)

| Arm | Correction | Defect it addresses |
|---|---|---|
| M1 MISSING/STALE | (a) Typhoon count of a quarter still in progress at the data fetch (2026-Q3, fetched 2026-09-09) set to NaN, not 0. (b) Each news trigger share set to NaN when the province-quarter has fewer than 10 titles (`news_n < 10`), so a share from a handful of titles is "too little data", not "no risk". (c) Hunger part: the predictive RMSE of the test row is widened by sqrt((2 + H_age_test) / mean(2 + H_age) over the training pairs), so a stale SWS reading gives a less certain hunger probability. | D-E66-5; E67 R2 (news shares 0 in 96–100% of rows); E58 2024-Q2 stale-hunger misses |
| N1 PROVINCIAL-ONLY | employment and ofw_remittance groups removed from both parts (national series cannot distinguish provinces) | E67 R2/R4: national figures used as province inputs |
| K1 EL-NINO-PROJECTION | at an origin whose issue date has a PAGASA El Niño Alert, Advisory or El Niño-related Climate Advisory in force (`climate_watch.hazard`), each projection `base_m` and `hl_m` is shifted by the province's mean projection error (F_true − base_m, HL_true − hl_m) over training rows whose target quarter fell in an earlier El Niño-advisory period (known at the origin). With no such rows there is no shift. | E65/E66/E67: price part projects flat prices; no forward climate channel |
| C1 COMBINED | M1 + K1 | — |

K1 can act only at origins with an El Niño status in force. On the evaluation rows those are 2024-01-01 and 2024-04-01 (2 quarters, 10 rows), with prior-episode training errors only from targets 2023-Q3 (and 2023-Q4). **K1 is therefore declared untestable as an accuracy improvement before scoring.** Its evaluation-row effect is reported descriptively, and its forward values are sealed for the prospective test.

## 3. Candidate revised target T-AFF (exploratory; never replaces T43 without adviser approval)

**Rationale (documented before evaluation).**
- The T43 price condition counts a faster rise in non-food prices as relief, through the clause food YoY − headline YoY > P60 (E62 W1).
- For household affordability, headline inflation erodes purchasing power whatever the food-minus-headline gap.
- Chapter I §1.7 says food-insecurity risk is determined from SWS hunger and PSA food price data and covers economic conditions.

**Definition.** T-AFF HIGH iff regional SWS hunger > 11.3% (same as T43) AND (province food YoY > food P60 OR province headline YoY > headline P60). The P60 values come from the same frozen 2021-Q1..2022-Q4 window, by the same `numpy.percentile` method that reproduces the E40 food thresholds exactly.

| Province | Headline P60 |
|---|---|
| Cavite | 5.013 |
| Laguna | 4.653 |
| Quezon | 5.060 |
| Rizal | 6.073 |
| Batangas | 5.547 |

**Hindsight disclosure.** This candidate was motivated in part by the already-observed 2026-Q3 case: hunger 23.6% and headline inflation 4.8–7.3%, but T43 LOW. It is therefore **hindsight-informed** and is reported as an exploratory alternative definition, not as an improvement.

**Arms on T-AFF:**
- TAFF-LGBM: the E56-TUNED procedure, with the gap projection replaced by the headline projection in the structural offset, the label replaced by the T-AFF price condition, and thresholds replaced by the headline P60. It is run serially, so the threshold change reaches every fit.
- TAFF-RULE: the transparent projection rule (food projection > food P60 OR headline projection > headline P60).
- Baselines: persistence, always-LOW and always-HIGH on T-AFF labels.

T-AFF results are not compared by accuracy with T43 results, because the labels differ.

## 4. Diagnostics (descriptive, no selection)

- **R-T target validity:**
  - HIGH rate by year and province for T43, PS and T-AFF;
  - the share of rows where hunger is above the line;
  - cross-tabulation of T43 against T-AFF;
  - label agreement across provinces within a quarter;
  - the number of independent quarters.
- **R-FV independent face validity:** Spearman correlation between each province's 2021 and 2023 annual HIGH rate (T43, PS, T-AFF) and PSA subsistence incidence for the same year (E27 `acquisition/validated/psa_subsistence_population_2021_2023.csv`; CVs 17–62%; n = 5 per year). Descriptive only; PSA warns that CV > 30% is unfit for ranking.
- **R-G trigger groups:**
  - each feature's share of variance that lies within quarters (cross-province) rather than between quarters;
  - exact-zero and NaN shares (from E67);
  - per-origin tree splits (E67);
  - the explanation of why single-group ablations are null.

## 5. Selection rule (frozen)

- **T43 arms.** An arm is better than A0 only if its paired Brier difference has a quarter-cluster 95% CI below 0 and a quarter sign test p < 0.05 (Holm over M1, N1, K1, C1), with G2 not worse. A better arm is a candidate for the next record build (2027-01-01 origin). It is **not served in E68**, because serving would change frozen forecasts.
- **Goal test.** G1–G5 are applied to every arm. Its G4 is "partial", because the arms were pre-specified here but the rows were examined.
- **T-AFF.** Reported only. Adoption requires adviser approval of the target.

## 6. Prospective scoring (future, pre-registered now)

**When.** After the 2026-Q4 outcomes are published (PSA CPI Oct–Dec 2026; the SWS 2026-Q4 round) and then the 2027-Q1 outcomes.

**How.** Score every sealed arm on T43 (and T-AFF for the TAFF arms) with the same scorer. The comparison against A0 uses the same rule as §5. With 2 quarters (10 rows) no rule can be met; those results are informative only, and they accumulate with later quarters.

## 7. Serving (E68 mode `AIPHEED_LEAD2_MODEL=e68`)

- **Unchanged:** the E58 record numbers and the E66/E67 layers.
- **Added**, in existing text fields and optional API fields only (no new UI element, colour or legend):
  - (a) an input-status list classifying each input at the issue date as observed, observed zero, missing, stale, unavailable at issue, or substituted, with its data age;
  - (b) the target wording "exploratory food-price-pressure-under-high-hunger score";
  - (c) the K1 El Niño projection scenario for the issued forecast, labelled "scenario, not a forecast";
  - (d) the face-validity result.
- **Default:** the production default stays E38.
