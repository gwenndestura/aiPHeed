# E52: measured five-driver condition scores (separate from the model)

These are **condition scores computed from official and measured data**. They are not the model's SHAP contributions and do not change any probability. Nothing served (model, records, API, frontend) was changed.

**Files**
- Script: `runner/e52_scores.py`
- Output: `E52_scores.csv` (every forecast quarter × province × driver, with raw inputs, ranks and flags) and `E52_results.json`

**Timing.** Forecast quarter F uses data quarter F−2, the latest complete quarter published before the origin. This is the model's own timing: for 2026-Q4 (origin 2026-10-01) the model's D_last is the 2026-Q2 food CPI.

**Score.** 0–100 percent rank of the data-quarter value against the series' own history from 2021-Q1 to that quarter:

score = 100 · #{history < x} / (n − 1)

Ties take the lowest rank, so a "nothing happened" quarter scores 0. Province series are ranked against the province's own history; national series against the national history.

| Driver | Formula | Source | Level |
|---|---|---|---|
| Market | mean of rank(D) and rank(rice CPI YoY); D = province food CPI YoY − five-province mean | PSA provincial CPI, food and rice (OpenStat) | province |
| Climate | max(rank \|rainfall anomaly\|, rank storm signal) | NASA POWER daily rainfall (E43), NOAA IBTrACS | province (storm signal nearly regional) |
| Fish Kill | rank of max(0, −ln(V_Q / V_Q−4)), total fisheries production | PSA OpenStat 0132E4GVFP1 | province, **PROXY** |
| Employment | mean of rank(unemployment) and rank(YoY change) | PSA LFS national (OpenStat 0021B3FKEI2), quarter mean, observed only | **national** |
| OFW | rank of the fall in real peso remittances, max(0, −g_real) | BSP (curated, and 2026 from secondary reports), ECB FX, PSA food CPI | national; varies only via food CPI; **PROVISIONAL** 2026 |

**Employment: provincial adjustment not applied.** PSA RSSO IV-A (rsso04a.psa.gov.ph) returned HTTP 403 for both the release page and the PDF on 2026-10-16. No provincial rate or release date could be verified, so the national score is used for all provinces.

## Q4 2026 forecast quarter (data quarter 2026-Q2)

| Province | Market | Climate | Fish Kill (proxy) | Employment (national) | OFW (provisional) |
|---|---|---|---|---|---|
| Cavite | **90** (D +0.87 pp, rice +18.6%) | 86 (rain −59%) | 0 (prod. +8.3%) | 75 | 0 (real +5.5%) |
| Laguna | 62 (D +0.10, rice +4.1%) | 90 (−63%) | 48 (−7.8%) | 75 | 0 (+6.3%) |
| Quezon | 76 (D +1.00, rice +15.1%) | 90 (−62%) | 43 (−1.2%) | 75 | 0 (+5.4%) |
| Rizal | 67 (D +0.47, rice +14.8%) | **95** (−59%) | **57** (−18.1%) | 75 | 0 (+5.9%) |
| Batangas | 33 (D −2.43, rice +6.6%) | 86 (−61%) | 0 (+4.3%) | 75 | 0 (+9.0%) |

- **History:** 22 quarters for all drivers except OFW (18).
- **Storm signal:** 0 in all provinces for 2026-Q2, so the Climate score comes from rainfall.
- **Employment inputs:** unemployment 4.79% (rank 62), up 0.90 pp YoY (rank 88).

## CALABARZON (mean of provinces)

| Forecast quarter | Data quarter | Market | Climate | Fish Kill | Employment | OFW |
|---|---|---|---|---|---|---|
| 2025-Q4 | 2025-Q2 | 26.5 | 30.6 | 50.6 | 58.8 | 78.5 |
| 2026-Q1 | 2025-Q3 | 26.7 | 82.2 | 34.4 | 69.4 | 67.1 |
| 2026-Q2 | 2025-Q4 | 27.9 | 82.1 | 34.7 | 76.3 | 14.7 |
| 2026-Q3 | 2026-Q1 | 38.5 | 19.0 | 54.0 | 85.0 | 0.0 |
| **2026-Q4** | **2026-Q2** | **65.7** | **89.5** | **29.5** | **75.1** | **0.0** |

## Do the scores move with known events?

| Event | Data | Score | Sensible? |
|---|---|---|---|
| 2023–24 rice price spike | rice CPI YoY +8.5 → +19.9% (2023-Q3..2024-Q2), rank 97–100 | Market 77–78 (forecasts 2024-Q1..2024-Q4); falls to 27–29 when rice deflated in 2025 (−9 to −14%) | yes |
| 2026-Q2 dry quarter | rainfall −59 to −63% | Climate 86–95 (forecast 2026-Q4) | yes |
| 2025-Q1 very wet quarter | rainfall +67% | Climate 100 (forecast 2025-Q3) | yes; the absolute anomaly scores wet and dry alike |
| 2024 strong typhoons | storm signal 4–5 in 2024-Q2/Q4 | Climate 78–89 (forecasts 2024-Q4, 2025-Q2) | yes |
| 2026 rising unemployment | +0.9 to +1.3 pp YoY | Employment 69–85 | yes |
| 2023 high food inflation | real remittances fell | OFW 68–100 (forecasts 2023-Q3..2024-Q1); 0 in 2026 (real growth +5–9%) | yes |

**Caution: short early histories.** Scores for forecasts before 2024 rest on short histories: 7–12 quarters, and only 3–8 for the YoY series (unemployment change, fisheries, OFW). Treat 2023 values as coarse.

## Province-specific or common?

| Driver | Differs by province? | Typical spread (max − min across provinces) |
|---|---|---|
| Market | **yes** | 30–93 |
| Fish Kill (proxy) | **yes** | 57–100 |
| Climate | mostly common (rainfall anomalies move together; storms nearly regional) | 0–12 in most quarters, up to 80 |
| OFW | **national**; differs only through provincial food inflation (real growth crossing zero) | 0–100, but not a real provincial remittance signal |
| Employment | **identical** for all provinces | 0 |

## Not the model's SHAP
These scores measure conditions, while the panel's percentages measure what moved the model. They can disagree. For 2026-Q4, Climate is **high here (89.5)**, while the model's climate SHAP is mostly protective, because it comes from the share of climate news titles.
