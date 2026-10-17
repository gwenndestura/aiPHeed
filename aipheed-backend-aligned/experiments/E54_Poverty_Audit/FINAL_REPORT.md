# E54 final report: is poverty used to forecast food-insecurity risk, and would it help?

**Branch:** `e46-lead2-policy`. Audit + protocol frozen in commit 559935f, before any E54 score.
**Protocol:** sha256 `a6932d65…` (`runner/PROTOCOL_SHA256.txt`).
**Runs:**

| Comparison | Run 1 | Repeat |
|---|---|---|
| C1/C2 | `runs/c12_20261017T145258Z` | `runs/c12_20261017T145708Z` |
| C3 | `runs/c3_20261017T145258Z` | `runs/c3_20261017T150746Z` |

Every predictions and rows file is byte-identical between run and repeat.

**Evidence status:** development evidence on 2024–2026 quarters already examined in E37–E53. It is not independent validation.

## 1. Answer in one paragraph

**Poverty is not used to forecast food-insecurity risk** in E38 (production default), E46-I7, E52 or E53. No poverty statistic is in their raw inputs, feature matrices or inference (`AUDIT.md`). PSA poverty is used only by the **Objective 3 municipal vulnerability ranking** (risk_index = province probability × (0.6 poverty + 0.4 density)) and by the dashboard's display.

When provincial poverty was added to each model as a pre-registered test, **no poverty arm improved balanced accuracy, HIGH/LOW recall or the Brier score on any target**:
- as-of or look-ahead;
- SAE 2021 mean or PSA subsistence incidence;
- on the PS, T43 and E38 targets.

Poverty changed no HIGH/LOW decision in C1/C2 (0 flips in 50 and 35 rows). Its largest Brier change was 0.0002. In E38 the as-of arms were identical to the served model.

**Poverty's current role, a vulnerability weight for ranking and not a forecasting input, is the one the evidence supports.**

## 2. Audit (summary of `AUDIT.md`)

| Model | Raw dataset | Training feature matrix | Inference | Ranking / display |
|---|---|---|---|---|
| E38 (production default) | no | no (6 served features: `H_margin, H_trend, D_last, Dnow, news_reg, fssi_v2`) | no | **yes**: `e36_record.json` `lgu_ranking`, 141 municipal SAE + 1 province substitute (Lucena); dashboard poverty rates |
| E46-I7 | no | no (30 price + 12 hunger inputs) | no | not in its record; dashboard municipal view = Objective 3 ranking |
| E52 | no | no (same 30 price inputs) | no | not in its record |
| E53 | no | no (same; R0 = E52 kept) | no | not in its record |

**Non-missing poverty observations in the four feature matrices:** 0.

**Indirect proxy only:** the news employment keywords include *kahirapan* and "economic hardship" (→ `news_employment`, a news-title share). E53 found no reliable value for the news group.

## 3. Pre-registered comparison (`PROTOCOL.md`)

**Arms:** each adds one provincial input to the reference model R's residual inputs. Nothing else changes.

| Arm | Input | Timing |
|---|---|---|
| POV-AS | mean 2021 municipal SAE | known from 2025-01-01 (as-of) |
| SUB-AS | PSA subsistence incidence, 2023 vintage | known after 2024-08-15 (as-of) |
| POV-LA | mean 2021 municipal SAE | known at every origin (look-ahead) |
| SUB-LA | PSA subsistence incidence, reference-year matched | look-ahead |
| FE | province indicators | diagnostic |

**Encoding:** centred across the five provinces; 0 when not yet published.

**Comparisons:**
- **C1:** PS target (E52/E53), 50 rows, 18 HIGH.
- **C2:** T43 target (E46-I7), S44 = 35 rows, 9 HIGH; EXT = 40 rows, 13 HIGH.
- **C3:** E38 label, 55 rows, 49 HIGH / 6 LOW.

**Reproduction:** R reproduced the committed E52/I7 price probabilities (≤ 1e-9), the I7 T43 probabilities (≤ 1e-9), E52's metrics (≤ 1e-12), and E38's committed probabilities and thresholds (≤ 1e-9).

### C1 — PS (E52 / E53): baselines B1–B7, climatology, always HIGH / LOW (`tables/metrics.csv`)

| Arm | Accuracy | Balanced | Recall HIGH | Recall LOW | Brier | ΔBrier vs R [95% CI] | Decision |
|---|---|---|---|---|---|---|---|
| R (E52) | 0.760 | 0.752 | 0.722 | 0.781 | 0.1900 | — | — |
| POV-AS (**primary**) | 0.760 | 0.752 | 0.722 | 0.781 | 0.1899 | −0.00012 [−0.00030, +0.0000002] | NO DEMONSTRATED DIFFERENCE |
| SUB-AS | 0.760 | 0.752 | 0.722 | 0.781 | 0.1902 | +0.00015 [−0.00045, +0.00083] | NO DEMONSTRATED DIFFERENCE |
| POV-LA | 0.760 | 0.752 | 0.722 | 0.781 | 0.1900 | +0.00001 [−0.00004, +0.00010] | NO DEMONSTRATED DIFFERENCE |
| SUB-LA | 0.760 | 0.752 | 0.722 | 0.781 | 0.1901 | +0.00005 [−0.00020, +0.00033] | NO DEMONSTRATED DIFFERENCE |
| FE | 0.760 | 0.752 | 0.722 | 0.781 | 0.1900 | −0.00001 [−0.00038, +0.00030] | NO DEMONSTRATED DIFFERENCE |
| best baseline (B1 persistence) | 0.620 | 0.630 | 0.667 | 0.594 | 0.3800 | | |

**What the C1 numbers show:**
- Every arm still passes E52's A1–A5 against every baseline, as R does.
- Calibration-in-the-large is unchanged (−0.094).
- 0 decision flips. Max |Δp| = 0.006 (POV-AS) and 0.011 (SUB-AS).
- The primary POV-AS interval touches 0 (upper bound +2e-7), so it does not meet the rule. The point gain, 0.00012 Brier (0.07%), is in any case negligible.

### C2 — T43 (E46-I7; hunger part unchanged because it is regional)

| Arm (S44) | Accuracy | Balanced | Recall HIGH | Recall LOW | Brier | ΔBrier vs R [95% CI] | Decision |
|---|---|---|---|---|---|---|---|
| R (I7) | 0.800 | 0.684 | 0.444 | 0.923 | 0.1736 | — | — |
| POV-AS | 0.800 | 0.684 | 0.444 | 0.923 | 0.1735 | −0.00017 [−0.00036, +0.0000003] | NO DEMONSTRATED DIFFERENCE |
| SUB-AS | 0.800 | 0.684 | 0.444 | 0.923 | 0.1738 | +0.00021 [−0.00076, +0.00116] | NO DEMONSTRATED DIFFERENCE |
| POV-LA | 0.800 | 0.684 | 0.444 | 0.923 | 0.1737 | +0.00002 [−0.00006, +0.00013] | NO DEMONSTRATED DIFFERENCE |
| SUB-LA | 0.800 | 0.684 | 0.444 | 0.923 | 0.1737 | +0.00005 [−0.00034, +0.00038] | NO DEMONSTRATED DIFFERENCE |
| FE | 0.800 | 0.684 | 0.444 | 0.923 | 0.1736 | −0.00002 [−0.00055, +0.00041] | NO DEMONSTRATED DIFFERENCE |

- EXT (40 rows) gives the same picture: R 0.725 / balanced 0.617 / recall HIGH 0.308 / Brier 0.2195, and no arm differs.
- The comparators are unchanged from E46: SIM-5T balanced 0.682, E41-M1 Brier 0.1639, BASE-m0.5 accuracy 0.829.
- The weak recall HIGH of I7 (4 of 9) is not repaired by poverty.

### C3 — E38 label (production-default procedure): baselines = the six E36 baselines, always HIGH, climatology

| Arm | Correct | Balanced | Recall HIGH | Recall LOW | Brier | ΔBrier vs R [95% CI] | Decision |
|---|---|---|---|---|---|---|---|
| R (E38) | 39/55 | 0.544 | 0.755 | 0.333 | 0.1996 | — | — |
| POV-AS / SUB-AS | 39/55 | 0.544 | 0.755 | 0.333 | 0.1996 | 0 | IDENTICAL |
| POV-LA | 39/55 | 0.544 | 0.755 | 0.333 | 0.2006 | +0.0009 [−0.0007, +0.0034] | NO DEMONSTRATED DIFFERENCE |
| SUB-LA | 39/55 | 0.544 | 0.755 | 0.333 | 0.1994 | −0.0002 [−0.0039, +0.0039] | NO DEMONSTRATED DIFFERENCE |
| FE | 39/55 | 0.544 | 0.755 | 0.333 | 0.2010 | +0.0014 [−0.0006, +0.0039] | NO DEMONSTRATED DIFFERENCE |

On this label, B1 persistence (44/55, balanced 0.741) and always HIGH (Brier 0.109) still beat E38 with or without poverty. E38's per-date configuration choices were the same in every arm (`runs/c3_*/results.json` → `paths`).

**Decisions:**
- No arm IMPROVES anywhere, so nothing is frozen in `frozen/` and nothing is served.
- `claim_poverty_improves_past_quarters` = **false**.

## 4. Why poverty does not help: what the runs show

1. **The model rarely uses residual inputs at all** (`tables/poverty_selection_by_origin.csv`).
   - At 6 of the 10 scored PS origins, the embargoed forward-chaining selection picks the base-effect projection with no residual model, so no input (poverty included) can matter.
   - At the other 4, it picks the heaviest shrinkage (α = 1000). The standardized poverty coefficients are then at most 0.027 YoY points in absolute value.
   - Adding poverty never changed the selected configuration on a scored origin.
   - Province identity (FE) fares no better. A static provincial attribute, poverty or otherwise, carries no out-of-sample residual signal that the selection can find.
2. **As-of availability.**
   - Under the as-of rule, POV first appears in a training row at the forecast for 2026-Q1 (5 of 70 training rows); SUB first at 2025-Q4 (4 of 65).
   - The 2021–2024 history on which the models learn could not have contained poverty.
   - In E38 the as-of arms were therefore exactly identical to the served model.
3. **No time variation and geographic mismatch.**
   - SAE 2021 is one number per province, and the subsistence vintages arrive together.
   - The SWS hunger part is regional, so provincial poverty cannot enter it.
   - The province-specific price thresholds already absorb level differences.
4. **Descriptive pattern** (`tables/province_outcome_vs_poverty.csv`; not pre-registered, computed on the evaluation outcomes themselves).
   - On these rows the poorest province, Quezon (SAE mean 20.3%), had the highest PS HIGH share (0.6), and Rizal (6.9%) had none.
   - Spearman(POV, HIGH share) across the five provinces: PS 0.70, T43 0.87, E38 label −0.56.
   - With five provinces this is one ordering of five numbers, seen in hindsight, and its sign flips on the E38 label.
   - Neither the as-of arms nor the look-ahead or FE arms could turn it into a better forecast.
   - It is not evidence that poverty forecasts risk.

## 5. Can poverty be added without leakage, mismatch or misuse of static data?

| Concern | Finding |
|---|---|
| Leakage | Avoidable only by the as-of rule. Under it, poverty is unknown for 2021–2024 origins (SAE 2021 released in 2024, month unverified; subsistence published 2024-08-15). The LA arms show that even ignoring publication lag adds nothing. |
| Geographic mismatch | Municipal SAE has no municipal target. It must be aggregated to the province (here an unweighted mean of 141 estimates, which is not an official PSA figure). Provincial poverty cannot inform the regional SWS hunger series. |
| Static data | One 2021 value per province is a fixed effect. FE shows that a fixed province effect gives no gain on these targets. Poverty would become a useful dynamic input only with a time series (e.g. the 2023/2026 FIES vintages as they are published), and even then at the cadence of a few points per 3 years. |
| Appropriate use | As a vulnerability weight (impact), not a hazard predictor. This is Chapter I Objective 3, already implemented. |

## 6. Recommendations

1. **Keep poverty where it is.** In the thesis, state explicitly that the forecasting models do not use poverty, and that poverty enters only the Objective 3 vulnerability weighting. E54 is the evidence that adding it does not improve the forecasts.
2. **Do not add poverty to the served model.** No arm met the pre-registered rule, so there is nothing to freeze for 2027.
3. **Weak inputs (`AUDIT.md`):**
   - The Lucena substitute (16.8, unverified).
   - The SAE 2021 release month (assumed by 2024-12-31).
   - The secondary 2024-08-15 subsistence date.
   - None of these affects any forecast today.
   - If the SAE release month is later verified as earlier, the POV-AS arm would gain a few more training rows. The C1 POV-LA result, which assumes poverty was known at every origin, already bounds that case: no gain.
4. **`psa_subsistence.parquet` holds 2018 rows.** It must stay unloaded (study-window rule).

## 7. What was not changed

- Production default E38.
- The served e46/e52/e53 records.
- The backend app code.
- The frontend.
- The Objective 3 ranking.
- The uncommitted E46 D-1 files of another session.

**Backend test suite after E54:** see `tests_status.json`.
**E54's own tests:** `tests/test_e54_experiment.py`, 17 passed.
