# E107 Deliverable D: indicator audit

## 1. All 12 indicators enter LightGBM (verified programmatically)

**The authoritative list.** These are the 12 FIRI v2 indicators, `backend/app/ml/inference/firi.py: LABELS`. E107 adds no indicator and drops none.

**The checks.** Tests in `backend/tests/unit/test_e107.py`:
- `test_all_twelve_families_are_model_columns`: the family list equals `firi.LABELS`, each family has at least one column, and every column has observed values.
- `test_fitted_booster_uses_every_column_as_an_input`: the fitted booster's feature names equal the 13 columns.

**Families vs columns.** 12 families map to **13 columns**: A1 has two (food and food − headline), and every other family has one.

| Code | Indicator | Domain | Source | Frequency | Available at issue date O(*t*) | Transformation | Missing-data handling | LightGBM column(s) |
|---|---|---|---|---|---|---|---|---|
| A1 | Food-price-pressure forecast | Affordability | PSA CPI food and all-items index (OpenSTAT 0012M4ACP22) | monthly | months through month 2 of *t* | latest index held flat to the target months of *t* + *k*; YoY; minus the province's 2021–22 P60 (food) and gap P60 | NaN if fewer than 2 base months are published (*k* = 4 uses 2 of 3) or the base is before 2021 | `A1_food`, `A1_gap` (lead-specific) |
| A2 | Headline inflation above usual | Affordability | PSA CPI all-items YoY | monthly | months 1–2 of *t* | headline YoY − province 2021–22 headline P60 | NaN if a month is missing | `A2` |
| A3 | Wholesale rice price change | Affordability | PSA wholesale rice prices | quarterly | *t* − 1 | YoY %, *t* − 1 vs *t* − 5 | NaN before 2022-Q2 (no pre-2021 base) | `A3` |
| V1 | Poverty and population density | Vulnerability | PSA SAE 2021, POPCEN 2024, land area | static | static profile at every origin (strictly published ~2025; disclosed) | 0.6 × min-max poverty + 0.4 × min-max density | none (Lucena uses a substitute poverty value) | `V1` |
| C1 | PAGASA El Niño alert/advisory in force | Climate and production | PAGASA ENSO alert items | event | items issued before O(*t*) | 1/0 | 0 before the first item (2023-03-24) | `C1` |
| C2 | Typhoons within 300 km | Climate and production | IBTrACS | quarterly | quarter *t* | count | NaN for 2026-Q3 (fetched mid-quarter) | `C2` |
| C3 | Palay/corn production drop | Climate and production | PSA production | quarterly | *t* − 1 | −min(palay, corn YoY %) | NaN before 2022-Q2 | `C3` |
| C4 | Fisheries production drop | Climate and production | PSA fisheries | quarterly | *t* − 1 | −fisheries YoY % | NaN before 2022-Q2 | `C4` |
| E1 | Unemployment change (national) | Household economy | PSA LFS | monthly | months of *t* − 1 | points, *t* − 1 vs *t* − 5 | NaN before 2022-Q2 | `E1` |
| E2 | Remittance decline (national) | Household economy | BSP OFW cash remittances | quarterly | *t* − 1 | −YoY % (USD) | NaN before 2022-Q2 and for origins after 2026-Q1 (series acquired only to 2025-Q4) | `E2` |
| N1 | FSSI-v3 | News | RSS headlines, XLM-RoBERTa zero-shot | quarterly | headlines of *t* published before O(*t*) | bias-weighted mean intensity | NaN when fewer than 5 admitted headlines; never 0 | `N1` |
| H1 | Regional hunger outlook > 11.3% | Regional hunger | SWS Balance Luzon, production rounds | quarterly | rounds posted before O(*t*) | 1 − Φ((11.3 − latest) / σ_k), σ_k = RMSE of the rule's earlier lead-*k* errors | NaN only before the first posted round (origins 2021-Q1, Q2) | `H1` (lead-specific) |

**No future information.** `test_values_published_after_the_issue_do_not_change_features` checks 6 origins × 4 leads. It multiplies or shifts every value published on or after O(*t*) and asserts that all 13 columns are unchanged. `test_backend_asof_inputs_respect_the_issue_date` checks H1, N1 and C1.

**Revisions.** Values are the latest published, not real-time vintages. PSA CPI is rarely revised. Production and LFS revisions cannot be excluded, so strict real-time validation is not claimed.

## 2. Coverage (share of non-missing values)

| Column | All origins 2021-Q1..2026-Q3 (Lead 2) | Evaluation origins 2023-Q3..2026-Q3 |
|---|---|---|
| A1_food, A1_gap | 0.91 | 1.00 |
| A2 | 1.00 | 1.00 |
| A3 | 0.73 | 0.92 |
| V1 | 1.00 | 1.00 |
| C1 | 1.00 | 1.00 |
| C2 | 0.96 | 0.92 |
| C3, C4, E1 | 0.78 | 1.00 |
| E2 | 0.70 | 0.85 |
| **N1** | **0.17** | **0.28** |
| H1 | 0.91 | 1.00 |

N1 (FSSI-v3) has a value for only 20 of 115 province-origins, because a province needs at least 5 admitted headlines in a quarter. It is in the model, but the evidence behind it is thin by construction.

## 3. Contribution analysis (diagnostic; the required model keeps all 12)

**3a. Where the model's explanation goes.** Share of mean |TreeSHAP| (log-odds) over the evaluation predictions, by family. Source: `out/diagnostics.json` → `importance.T43`.

| Family | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| A1 price projection | **0.45** | 0.09 | 0.23 | 0.00 |
| A2 headline above usual | 0.19 | 0.01 | 0.02 | 0.00 |
| A3 rice | 0.01 | 0.00 | 0.01 | 0.00 |
| V1 vulnerability | 0.01 | 0.01 | 0.00 | 0.00 |
| C1 El Niño advisory | 0.01 | 0.00 | 0.02 | 0.00 |
| C2 typhoons | 0.00 | 0.00 | 0.00 | 0.00 |
| C3 palay/corn | 0.00 | 0.04 | 0.09 | 0.17 |
| C4 fisheries | 0.00 | 0.00 | 0.15 | 0.00 |
| E1 unemployment | 0.11 | **0.66** | 0.24 | 0.23 |
| E2 remittances | 0.09 | 0.19 | 0.11 | **0.55** |
| N1 FSSI-v3 | **0.00** | **0.00** | **0.00** | **0.00** |
| H1 hunger outlook | 0.14 | 0.00 | 0.15 | 0.06 |

**By domain at Lead 1:** Affordability 0.65, Household economy 0.20, Regional hunger 0.14, Climate 0.01, Vulnerability 0.01, News 0.00.

**Findings.**
- The model relies on one domain: affordability, through the price projection.
- **N1 (FSSI-v3) never received a split** at any lead.
- C2 (typhoons) was never used either.
- Beyond Lead 1 the national household-economy series E1/E2 dominate. Section 3b shows that this reliance is harmful.
- Importance is not causation. The E1/E2 weight is the period-marker effect described in `EXPERIMENT_REPORT.md` §2.

**3b. Ablations** (same nested procedure, same rows; T43). Values are accuracy / Brier. *p* is the one-sided quarter sign-flip p that the full model is better than the ablated one.

| Model | Lead 1 (40 rows) | Lead 2 (25) | Lead 3 (20) | Lead 4 (20) |
|---|---|---|---|---|
| Full, 12 indicators | 0.750 / 0.183 | 0.24 / 0.315 | 0.10 / 0.351 | 0.55 / 0.302 |
| − Affordability (A) | 0.450 / 0.358 (*p* = 0.004) | 0.16 / 0.360 | 0.10 / 0.371 | 0.55 / 0.302 |
| − Vulnerability (V) | 0.750 / 0.187 | 0.20 / 0.318 | 0.10 / 0.351 | 0.55 / 0.302 |
| − Climate (C) | 0.800 / 0.181 | 0.28 / 0.290 | 0.10 / 0.425 | 0.55 / 0.313 |
| − Household economy (E) | **0.825 / 0.129** | 0.36 / 0.382 | 0.25 / 0.302 | **0.95 / 0.109** |
| − News (N) | 0.750 / 0.183 (identical) | 0.24 / 0.315 | 0.10 / 0.351 | 0.55 / 0.302 |
| − Regional hunger (H) | 0.775 / 0.162 | 0.24 / 0.317 | 0.15 / 0.331 | 0.55 / 0.333 |
| A only | **0.875 / 0.116** | **0.72 / 0.253** | 0.50 / 0.241 | 0.90 / 0.126 |
| H only | 0.525 / 0.292 (*p* = 0.047) | 0.28 / 0.401 | 0.05 / 0.442 | 0.95 / 0.097 |
| A + H | 0.825 / 0.127 | 0.28 / 0.390 | 0.10 / 0.329 | 1.00 / 0.125 |

**Reading.**
- **Only affordability adds information that is significant at the quarter level:** removing it costs 0.30 accuracy at Lead 1, p = 0.004.
- **Household economy hurts at Leads 1, 3 and 4** on both accuracy and Brier. At Lead 2, removing it raises accuracy (0.36 vs 0.24) but worsens Brier (0.382 vs 0.315). With 2–5 HIGH quarters, a national series acts as a time marker.
- **News, vulnerability and climate are neutral.**
- **The "A only" model is better than the full 12-indicator model at every lead.**
- These results come from the evaluated rows (seen), so they are diagnostic. They must not be used to select a new model without fresh data.
- Lead 4 rows have 1 HIGH in 20, so a model that says LOW everywhere scores 0.95 there.

## 4. Sensitivities

| Variant | T43 Lead 1 | Lead 2 | Lead 3 | Note |
|---|---|---|---|---|
| Primary (production SWS rounds) | 0.750 / bal 0.675 / AUC 0.755 / Brier 0.183 | 0.24 | 0.10 | fails R4, R5, G2, G3 at Lead 1 |
| **S1: all SWS rounds as labels** (supplementary 2025 rounds included; 50 rows / 10 quarters at Lead 1) | **0.780 / 0.743 / 0.851 / 0.154** | 0.43 | 0.23 | At Lead 1, passes R1–R7, G1 and G2 (Brier below climatology, sign-flip p = 0.016). **Fails only G3:** the final block is not better than climatology. |
| S2: V1 strict (missing before 2025-07-01) | 0.750 / 0.675 / 0.732 / 0.187 | 0.20 | 0.10 | V1's timing deviation does not drive the result |
| S3: A1 as served (E56 price probability instead of the projection) | 0.800 / 0.852 / 0.870 / 0.163 | 0.20 | 0.05 | Training rows before the E63 range have no served A1 |

**The Lead-1 verdict depends on a data decision.** With production rounds only (the served rule, primary), Lead 1 is not reliable. Counting the three supplementary 2025 rounds adds two outcome quarters (2025-Q2, 2025-Q3) with 5 HIGH rows. Lead 1 then fails only G3, because no model can beat "LOW everywhere" on the 1-HIGH final block. The provenance of those rounds is disputed (`docs/DATA_AVAILABILITY.md` vs the 2026-10-09 collection), and the protocol fixed production rounds before scoring. The primary verdict therefore stands: **no reliable lead is established**, and Lead 1 is the only horizon with supporting evidence.
