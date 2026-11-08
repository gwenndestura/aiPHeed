# E108 Deliverable C: indicator audit

## 1. Registry: the 12 FIRI v2 families as the 13 LightGBM columns

**Families vs columns.** 12 families map to 13 columns because A1 has two columns: projected food YoY and projected food − headline YoY, each minus its province threshold.

**Publication delay** below is the lag that the issue-time rule allows. Actual release dates were reconstructed only for SWS (posted dates in `sws_rounds.csv`) and PAGASA items. For the other series the rule is conservative but not checked against each release.

| ID | Name | Domain | Source | Geography | Frequency | Delay allowed at issue date O(*t*) (day 1 of *t* + 1) | Transformation | Missing data | Column(s) | Limitation |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Food-price-pressure forecast | Affordability | PSA CPI food and all-items index | province | monthly | months through month 2 of *t* (≥ 1 month lag) | latest index held flat to the target months; YoY; minus 2021–22 P60 | NaN if < 2 base months (Lead 4 uses 2 of 3) | `A1_food`, `A1_gap` | projection, not an observation |
| A2 | Headline inflation above usual | Affordability | PSA CPI all-items YoY | province | monthly | months 1–2 of *t* | YoY − province P60 | NaN if a month is missing | `A2` | — |
| A3 | Wholesale rice price change | Affordability | PSA rice prices | province | quarterly | quarter *t* − 1 | YoY | NaN before 2022-Q2 | `A3` | 27% missing overall |
| V1 | Poverty and density | Vulnerability | PSA SAE 2021, POPCEN 2024 | province | static | used at every origin (published ~2025; disclosed) | 0.6 poverty + 0.4 density, min-max | none (Lucena substitute) | `V1` | never changes over time, so it acts as a province constant |
| C1 | PAGASA El Niño alert/advisory | Climate | PAGASA ENSO items | **national** | event | items dated before O(*t*) | 1/0 | 0 before the first item | `C1` | same value for all provinces |
| C2 | Typhoons within 300 km | Climate | IBTrACS | province (≤ 3 distinct values per quarter) | quarterly | quarter *t* | count | NaN 2026-Q3 (fetched mid-quarter) | `C2` | low variation |
| C3 | Palay/corn drop | Climate | PSA production | province | quarterly | *t* − 1 | −min(YoY) | NaN before 2022-Q2 | `C3` | possible revisions |
| C4 | Fisheries drop | Climate | PSA fisheries | province | quarterly | *t* − 1 | −YoY | NaN before 2022-Q2 | `C4` | possible revisions |
| E1 | Unemployment change | Household economy | PSA LFS | **national** | monthly | months of *t* − 1 | points, *t* − 1 vs *t* − 5 | NaN before 2022-Q2 | `E1` | same value for all provinces |
| E2 | Remittance decline | Household economy | BSP OFW cash remittances | **national** | quarterly | *t* − 1 | −YoY | NaN before 2022-Q2 and after origin 2026-Q1 (series ends 2025-Q4) | `E2` | same value for all provinces |
| N1 | FSSI-v3 | News | RSS headlines, XLM-RoBERTa | province | quarterly | headlines of *t* published before O(*t*) | bias-weighted intensity | NaN when < 5 headlines | `N1` | **83% missing** |
| H1 | Hunger outlook > 11.3% | Regional hunger | SWS Balance Luzon (production rounds) | **region** | quarterly | rounds posted before O(*t*) (verified dates) | 1 − Φ((11.3 − latest)/σ_k) | NaN before the first posted round | `H1` (also the hunger factor) | same value for all provinces |

## 2. Evidence that all 12 enter the intended LightGBM pipeline

All tests are in `backend/tests/unit/test_e108.py` and were run on 2026-10-25.

| Check | Test |
|---|---|
| The family list equals `firi.LABELS`. The fitted price booster's feature names equal the 13 columns. P = H1 × price part. | `test_all_twelve_families_enter_the_fitted_price_booster` |
| A family's values published on or after O(*t*) change neither the 13 columns nor the forecast. Covers A1, A2, A3, C2, C3, C4, E1 and E2, each perturbed alone, at all four leads (32 cases). | `test_future_values_of_each_data_family_change_neither_features_nor_forecast` |
| PAGASA items, headlines and SWS rounds dated after O(*t*) change neither features nor forecast (C1, N1, H1; 4 leads) | `test_future_backend_items_change_neither_features_nor_forecast` |
| **Negative control:** the same fake items dated before O(*t*) do change C1, H1 and N1, so the tests above are not vacuous | `test_negative_control_items_published_before_the_issue_do_change_features` |
| V1 is static | `test_v1_is_a_static_profile` |
| Every PS training label uses only CPI months published at O(*t*), and never the target quarter | `test_price_training_labels_are_known_at_the_issue` |

## 3. Variation and coverage (why some families cannot contribute)

From `out/diagnosis.json`:

| Family | Distinct values per quarter | Missing | Consequence |
|---|---|---|---|
| A1, A2, A3, C3, C4 | 5 (provincial) | 0–27% | can separate provinces |
| V1 | 5, never changes over time | 0% | a province constant; cannot track change over time |
| C2 | ≤ 3 | 4% | little variation |
| C1, E1, E2, H1 | **1 (national/regional)** | 0–30% | shift all provinces together; cannot rank provinces |
| N1 | ≤ 4 | **83%** | only 2–14 non-missing rows per training set: too few for any 15-row leaf |

## 4. Contribution to the F1 forecast (diagnostic; the final model keeps all 12)

**4a. Domain ablation** (same nested procedure, same rows). Values are accuracy / Brier, with the one-sided sign-flip p that the full model is better.

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| Full, 12 families | 0.892 / 0.098 | 0.691 / 0.231 | 0.622 / 0.193 | 0.600 / 0.289 |
| − Affordability (A) | **0.677 / 0.175 (p = 0.008)** | 0.545 / 0.260 (p = 0.09) | 0.733 / 0.197 | 0.600 / 0.275 |
| − Vulnerability (V) | 0.892 / 0.096 | 0.691 / 0.240 | 0.622 / 0.193 | 0.600 / 0.289 |
| − Climate (C) | 0.877 / 0.102 | 0.691 / 0.236 | 0.578 / 0.211 | 0.600 / 0.286 |
| − Household economy (E) | 0.877 / 0.103 (p = 0.11) | 0.691 / 0.252 | 0.578 / 0.220 (p = 0.06) | 0.600 / 0.287 |
| − News (N) | 0.892 / 0.098 (identical) | 0.691 / 0.231 | 0.622 / 0.193 | 0.600 / 0.289 |
| − H1 column (the hunger factor stays) | 0.892 / 0.099 | 0.709 / 0.232 | 0.644 / 0.199 | 0.314 / 0.424 |
| A only | 0.892 / 0.112 (p = 0.12) | 0.691 / 0.253 | 0.622 / 0.234 (p = 0.055) | 0.229 / 0.387 |

**4b. Grouped permutation importance** (Brier increase when the family's columns are shuffled across evaluation rows; 200 draws; 5–95% range).

| Family | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| A1 price projection | **+0.139 (0.098–0.186)** | **+0.050 (0.027–0.077)** | +0.022 (−0.001–0.045) |
| H1 hunger outlook (factor and column) | **+0.053 (0.023–0.081)** | −0.021 (−0.061–0.020) | +0.009 (−0.019–0.041) |
| E1 unemployment | +0.008 (0.003–0.012) | +0.008 (0.004–0.012) | +0.011 (0.006–0.016) |
| C3 palay/corn | 0.000 | +0.009 (0.005–0.012) | 0.000 |
| C4 fisheries | +0.003 | 0.000 | +0.018 (0.003–0.029) |
| A2, A3, V1, C1, C2, E2 | |Δ| ≤ 0.006 | |Δ| ≤ 0.004 | |Δ| ≤ 0.006 |
| N1 FSSI-v3 | 0.000 | 0.000 | 0.000 |

**4c. SHAP family shares across origins** (mean ± SD of each origin's share of mean |SHAP|).

| Family | Lead 1 (13 origins) |
|---|---|
| A1 | 0.49 ± 0.17 |
| H1 | 0.13 ± 0.11 |
| E1 | 0.10 ± 0.12 |
| C4 | 0.10 ± 0.10 |
| C3 | 0.06 ± 0.16 |
| E2 | 0.05 ± 0.07 |
| A3, C2, V1, A2 | ≤ 0.03 each |
| **C1, N1** | **never used** |

**What this means.**
1. **Price (A1) is the only family with a clear, stable contribution.** It carries half the explanation at Lead 1, removing it costs 0.21 accuracy (p = 0.008), and shuffling it raises Brier by 0.14.
2. **The factoring and 15-row leaves removed E107's harmful reliance on national series.** Dropping household economy no longer improves the model (0.877 vs 0.892).
   - E1 now adds a small but consistent signal (+0.008 Brier when shuffled, at every lead).
   - Its SHAP share varies widely across origins (± 0.12), so it is not a stable driver.
3. **Climate/harvest, vulnerability and news add no measurable predictive information** with these data. The reasons are, in order:
   - N1: coverage (83% missing);
   - C1: a national 0/1 series that switched only around the 2023–24 and 2026 El Niño episodes;
   - V1: constant over time;
   - C2: low variation.

   This is a finding about data volume and variation, not proof that these factors do not matter for food insecurity.
4. All 12 families remain in the final model, as required. **They are reported as included, not as contributing.**

## 5. Sensitivities

| Variant | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| Primary (production SWS rounds) | 0.892, inconclusive (G3) | 0.691, not reliable | 0.622 | 0.600 |
| S1: all SWS rounds (adds 2025-Q2, 2025-Q3) | 0.893 / AUC 0.926 / 15 quarters, **inconclusive (G3)** | 0.677, not reliable | 0.582 | 0.578 |
| S2: V1 strict (missing before 2025-07-01) | 0.892 / AUC 0.921 | 0.691 | 0.622 | 0.600 |

E108's verdict does not depend on the disputed SWS rounds. E107's Lead-1 verdict did.
