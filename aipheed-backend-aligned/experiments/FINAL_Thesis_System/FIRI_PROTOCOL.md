# aiPHeed Food-Insecurity Risk Index (FIRI v1): frozen methodology

**Date:** 2026-10-20 (final development run)
**Freezing:** this file is frozen before the anchors are computed and before any FIRI value is scored. Its SHA-256 (LF-normalised) is in `runner/FIRI_PROTOCOL_SHA256.txt`.
**Constraint stated by the user (2026-10-20):** no direct food-insecurity outcome exists for CALABARZON provinces or LGUs. The final system must therefore estimate local food-insecurity risk from the closest available indicators. A composite index is not an observed food-insecurity label and is never presented as one.

## 1. What FIRI estimates

FIRI estimates **the relative risk that households in a province face food insecurity in the target quarter** (two quarters after the origin quarter, i.e. Lead-2). It does this by combining, on one scale, the evidence available at the issue date on:
- affordability;
- household vulnerability;
- climate and food production;
- household economic conditions;
- news warning signals;
- regional hunger.

FIRI is a **proxy composite on a 0–1 scale, not a probability**:
- 0 = every domain at or below the low end of its 2021–2022 reference range;
- 1 = every domain at or above its high end.

## 2. Indicators, their roles and direction (higher score = more risk)

| Domain | Indicator | Role | Geography | Source at issue O(t) | Direction / raw value x |
|---|---|---|---|---|---|
| A Affordability | A1 Lead-2 food-price-pressure forecast | leading indicator (model forecast for t+2) | province | E56-TUNED LightGBM price part P_price (served record / sealed E57, E63, E68) | x = P_price (already 0–1) |
| A | A2 headline inflation above the province's usual level | leading indicator (purchasing power) | province | PSA CPI, latest two months before issue: headline = F_now − gap_now; minus the province's 2021–22 headline P60 (E68) | x = headline − P60_headline |
| A | A3 wholesale rice price change | leading indicator | province | PSA wholesale rice YoY, quarter t−1 (`rice_whsl_yoy`) | x = rice YoY |
| V Vulnerability | V1 structural vulnerability | contextual vulnerability (static) | province | 0.6 × poverty_norm + 0.4 × density_norm, min-max across the five provinces (the approved LGU weighting at province level). Poverty = mean of the province's PSA 2021 municipal SAE; density = province population / area from `data/inputs/lgu_vulnerability.csv` (POPCEN 2024) | x = V1 (already 0–1) |
| C Climate and production | C1 official El Niño hazard | hazard (official, dated) | national | PAGASA El Niño Alert, Advisory or El Niño Climate Advisory in force before O(t) (`climate_watch.hazard`) | x = 1 or 0 |
| C | C2 typhoons | hazard | province (300 km) | IBTrACS count in quarter t (`tc_count`) | x = count |
| C | C3 crop production drop | exposure | province | PSA palay and corn production YoY, quarter t−1 | x = −min(palay YoY, corn YoY) |
| C | C4 fisheries production drop | exposure (not fish-kill events) | province | PSA fisheries production YoY, quarter t−1 | x = −fisheries YoY |
| E Household economy | E1 unemployment change | economic condition | **national** | PSA LFS unemployment YoY change, quarter t−1 (`ur_yoy`) | x = ur_yoy |
| E | E2 remittance decline | economic condition | **national** | BSP cash remittances (USD) YoY, quarter t−1 | x = −remittance YoY |
| N News | N1 Food Stress Sentiment Index | warning signal | province | FSSI-v3 of quarter t, articles published before O(t) (`pipeline_v3.fssi_v3`), **only when SUFFICIENT (≥ 5 articles)** | x = FSSI-v3 |
| H Regional hunger | H1 regional hunger outlook | direct observation (regional) used as context | **region (Balance Luzon), the same for all five provinces** | P(SWS hunger at t+2 > 11.3%), latest approved round posted before O(t), sigma from that rule's own past errors (E69 R0; `thesis_system.regional_hunger`) | x = probability (already 0–1) |

**Not used, with reasons:**
- Subsistence incidence: CV 17–62%; shown as context only.
- Bottom-30% CPI: redundant with the general CPI (r 0.78–0.98) and ends 2026-06.
- BERTopic topics: descriptive, no direction.
- News trigger shares: zero in 46–100% of rows.

## 3. Normalisation (anchors from 2021–2022 only; no outcomes used)

- **Continuous indicators** (A2, A3, C2, C3, C4, E1, E2, N1): score s = clip((x − P10) / (P90 − P10), 0, 1). P10 and P90 are the 10th and 90th percentiles of x over all province rows (national series: one value per quarter) at origins 2021-Q3..2022-Q4. This is the same 2021–2022 reference window as the approved E40 thresholds. The anchors are computed once by `runner/firi_anchors.py` before any label is read, and frozen in `out/firi_anchors.json` with its SHA-256.
- **Indicators already on a 0–1 scale** (A1, V1, C1, H1) are used as they are.
- **Degenerate anchors:** if a continuous indicator has fewer than 5 window values or P90 = P10, it is excluded from FIRI (documented in the anchors file).

## 4. Aggregation, weights, threshold

- **Domain score** = mean of the domain's available indicator scores.
- **Domain weights:** equal across the six domains. This is the default for composite indicators when no outcome exists to estimate weights (OECD/JRC *Handbook on Constructing Composite Indicators*, 2008). No weight is estimated from data.
- **FIRI** = mean of the available domain scores. At least 4 of the 6 domains must be available; otherwise FIRI is INSUFFICIENT DATA.
- **Classification:** HIGH if FIRI ≥ 0.5, the midpoint of the scale (on average above the middle of the 2021–2022 reference range); LOW otherwise. The threshold is not tuned.
- **Explanation:** each domain's share of FIRI = (domain score / number of available domains) / FIRI, listed with its indicators, values, periods and status.

## 5. Missing, stale and unavailable data (never zero)

| Case | Rule |
|---|---|
| Missing indicator (NaN, not published by the issue date, FSSI below SUFFICIENT) | dropped from its domain, with its status reported |
| A domain with no indicator | dropped; FIRI is renormalised over the remaining domains, and the domain count is shown |
| Typhoon count of a quarter still in progress when the data were fetched (2026-Q3, fetched 2026-09-09) | missing |
| V1 timing | Both sources were published after the earliest origins (SAE 2021 in 2024; POPCEN 2024 later). V1 is used only at issue dates on or after **2025-07-01**, an assumed, conservative availability date for both, and is missing before it. A static-V sensitivity is reported, not used. |

## 6. Evaluation (walk-forward, frozen; development evidence only)

FIRI has no fitted parameters of its own:
- the anchors come from 2021–2022;
- the weights are equal;
- the threshold is fixed;
- its model component A1 comes from the expanding-window walk-forward LightGBM predictions already sealed (E57 for Lead 2; E63 for leads 1–3).

**Scored:**
1. **Lead-2, 50 rows** (E57 origins 2023-Q4..2026-Q1), label T43.
   - Metrics: accuracy (Wilson CI), precision, recall, F1, AUC-ROC (FIRI as the score), Brier (FIRI used as a score, noted as not a calibrated probability), confusion matrix, both class recalls.
   - Paired Brier against persistence and climatology (E63 reliability rule).
2. **Objective 4, 45 identical rows:** FIRI, the LightGBM and the four Chapter I baselines plus the majority class, with paired Brier and McNemar.
3. **Leads 1–3:** E63 rows, with P_price from E63 and H1 at the same lead. Reliability rule E63 §8.
4. **Regional outcome:** the regional mean of FIRI against observed SWS hunger above 11.3% at t+2, per quarter (the only direct food-insecurity observation; regional). The H1 component shares the hunger source, which is stated.
5. **Sensitivities (descriptive, never used to change the method):** static V1 at all origins; FIRI without the H domain.

**Caveat, stated before scoring:** T43 shares its price source with A1 and A2, and the regional outcome shares its source with H1. Neither is an independent food-insecurity outcome, so **no FIRI result can validate it as a measure of food insecurity**.

## 7. Serving (thesis mode)

- **Province estimate:** the province "risk level score" equals FIRI. The map colour follows FIRI ≥ 0.5 (approved palette unchanged).
- **LGU index** = FIRI × LGU vulnerability (the approved 0.6 poverty + 0.4 density weighting): a relative prioritization.
- **Kept separate:** the LightGBM price score (A1), the regional hunger outlook (H1), and the domain and indicator breakdown with freshness and status.
- **Past quarters:** FIRI values come from `backend/data/thesis/firi_history.csv` (built by the runner from sealed predictions).
- **The issued target quarter:** FIRI is computed at runtime from the served record and the model's own inference features, and checked against the history table by a test.
