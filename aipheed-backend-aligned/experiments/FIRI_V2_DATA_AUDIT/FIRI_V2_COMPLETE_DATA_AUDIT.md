# FIRI v2 complete data audit

**Branch:** `aiPHeed/firi-data-audit` (from `aiPHeed/final-thesis-objectives`). **Date:** 2026-10-26.
**Scope:** the 12 indicator families of `backend/app/ml/inference/firi.py`, as they enter the primary CH1-LGBM model.
**Rules kept:** study window 2021+; no new data requests; no artificial labels, duplicated observations or future
information; no municipal validation claimed from regional data; target and criteria unchanged (corrections went into
a frozen addendum before the rerun).

Companion files: `INDICATOR_SOURCE_AND_COVERAGE_MATRIX.md`, `INDICATOR_FEATURE_LINEAGE.md`,
`MISSING_DATA_AND_CORRECTIONS.md`, `FINAL_LIGHTGBM_DATA_VALIDATION.md`, `UPDATED_FORECAST_EVALUATION.md`,
`FINAL_THESIS_OBJECTIVE_ASSESSMENT.md`.

## Method

1. **Fresh pull** of every public source reachable without a request (`runner/pull_public.py`; PSA OpenSTAT tables
   0012M4ACP22, 0052M4AWB01, 0012E4EVCP0, 0132E4GVFP1, 0021B3FKEI2; raw files in `data/raw/`, log `data/pull_log.json`).
2. **Reconcile** held repo values against the fresh pull (`runner/reconcile.py` → `out/reconcile.json`).
3. **Rebuild** what cannot be reconciled from a table: BSP remittances from 22 cited press-release figures; typhoon
   counts recomputed from IBTrACS (`runner/typhoons.py`).
4. **Build** the audited training tables with issue-date bookkeeping (`runner/audit_build.py`).
5. **Freeze** Addendum 1 (corrections) and Addendum 2 (news coverage) before scoring; **rerun** the frozen evaluation
   (`runner/rerun_ch1.py`, `runner/news_coverage.py`); **export** the audited run to the backend (`runner/export_audited.py`).

## Per indicator

**A1 food-price pressure.** Collected: PSA CPI food and all-items indices and YoY, 5 provinces, monthly 2021-01 to
2026-09. Validation: 690/690 index values equal the fresh pull; published YoY equals recomputed within 0.05. Gaps: none.
Processing: latest index held flat to the target months, YoY, minus the province's frozen P60; plus 3-month momentum.
Issue date: months ≤ month 2 of the origin quarter (released about day 5 of the next month). Reaches the model: yes
(`A1_food`, `A1_gap`, `A_mom`); the dominant family (SHAP share 0.67 at Lead 1).

**A2 headline inflation.** Same table and validation as A1. Processing: latest two months minus the headline P60.
Reaches the model: yes (`A2`); share ≈ 0, since A1's gap term already carries headline inflation.

**A3 wholesale rice.** Collected: PSA regular-milled rice wholesale price, monthly. Validation: 107/112 quarters
equal; the 5 that differ are 2026-Q3, held with only July–August. Correction: complete 3-month means. Gaps: some
Laguna/Quezon/Batangas quarters have 0–2 published months (means over existing months, else NaN). Issue date:
quarter t−1. Reaches the model: yes (`A3`); share 0.04.

**V1 poverty and density.** Collected: 2021 municipal SAE poverty, POPCEN 2024, land area for 142 LGUs (Lucena uses the
Quezon value). Static. Processing: 0.6 × poverty + 0.4 × density, min-max across provinces. Reaches the model: yes
(`V1`); share 0.01 (constant per province, so it can only shift levels). It is also the basis of the LGU ranking.

**C1 El Niño alert.** Collected: 20 PAGASA ENSO items 2023-03-24 to 2026-10-07; verified against PAGASA's monitoring
page. Processing: 1 if an El Niño Alert or Advisory is in force before the issue date. National. Reaches the model:
yes (`C1`); share 0 (a national flag constant through most training windows).

**C2 typhoons.** Collected: IBTrACS v04r01 Western Pacific tracks to 2026-10-22. Validation: 108/115 held counts
reproduced; 7 differ by one storm. Correction: documented recomputation (area-weighted centroids of the app's
province boundaries, 300 km). Issue date: quarter t. Reaches the model: yes (`C2`); share 0.01.

**C3 palay/corn.** Collected: PSA production, quarterly, to 2026-Q2. Validation: 220/220 equal. Processing: −(lower of
palay and corn YoY, t−1). Reaches the model: yes (`C3`); share 0.03 at Lead 1, 0.13 at Lead 2.

**C4 fisheries.** Collected: PSA fisheries production, quarterly, to 2026-Q2. Validation: equal to the fresh pull.
Processing: −(YoY, t−1). Reaches the model: yes (`C4`); share 0.05.

**E1 unemployment.** Collected: PSA LFS unemployment rate, monthly (4 months not surveyed), national. Validation: 68/68
equal. Processing: quarter mean t−1 minus t−5. Reaches the model: yes (`E1`); share 0.08. One national value for every
province.

**E2 remittances.** Collected: BSP OFW cash remittances. **Defect:** held levels did not match BSP's releases and
2026-Q1/Q2 were missing. Correction: rebuilt from 22 cited BSP cumulative figures, 2021-Q1 to 2026-Q2. Processing:
−(YoY, t−1). Issue date: quarter t−1 (BSP releases about 45 days after quarter end). Reaches the model: yes (`E2`);
share 0.05. National.

**N1 news.** Collected: 9,659 RSS headlines (FSSI-v3), 58,576 GDELT documents, the E113 GDELT price-news composite.
Gap: provincial FSSI-v3 is sufficient in only 17% of province-quarters because only 33% of headlines carry a province
tag. Processing: FSSI-v3 mean intensity (NaN below 5 headlines); GDELT price-news YoY; price news between SWS fieldwork
end and the issue date. Issue date: publication time before O(t). Reaches the model: yes (`N1`, `G_pri_yoy`,
`NG_gap_price`). Contribution tested: no gain at Leads 0–1, significantly worse at Leads 2–3; a regional FSSI with full
coverage also gives no gain.

**H1 regional hunger.** Collected: SWS involuntary hunger, Balance Luzon, 23 regular rounds 2021+ (20 quarters with a
reading). **Defect (fixed before the first scoring):** the backend series used the commissioned 2025-Q1 round and
dropped the regular 2025-Q2/Q3 rounds. Processing: π_H = Φ((latest − 11.3)/σ). Region only (Balance Luzon is wider
than CALABARZON). Reaches the model: yes (π_H factor and `H1` column).

## Pooled SWS areas vs Balance Luzon only

Using NCR, Visayas or Mindanao readings as extra CALABARZON outcomes would invent labels, so they were used only to
estimate the hunger-condition noise. Lead 1 accuracy 0.929 with pooled σ vs 0.914 primary: one row out of 70. The
primary stays Balance-Luzon-only, as frozen.

## Outcome

- Three input defects corrected (E2, C2, A3 2026-Q3) plus a cache defect that could hide corrections.
- **No verdict changed:** Lead 1 accuracy 0.914 (lower 90% bound 0.843) before and after; Leads 2–4 fail; maximum
  reliable lead 1 quarter.
- The binding limits are the number of independent outcomes (20 SWS quarters, 19 HIGH province-quarters), the one
  regional hunger value shared by all provinces, and price pressure that is not forecastable beyond one quarter. More
  complete inputs cannot change those.

## Reproduce

```bash
cd aipheed-backend-aligned/experiments/FIRI_V2_DATA_AUDIT/runner
python pull_public.py && python reconcile.py && python typhoons.py
python audit_build.py && python rerun_ch1.py && python news_coverage.py && python export_audited.py
```

Tests: `backend/tests/unit/test_firi_data_audit.py`, `backend/tests/integration/test_api_ch1_risk.py`.
