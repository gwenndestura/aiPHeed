# E129 target validity decision (the gate before any provincial training)

## E128 baseline (preserved)

**Untouched.** E128 commits `e822be9` (protocol, SHA `c7a92670…`) and `9987832` (results).

**Reproduced from saved artifacts** by the E128 test suite: predictions re-scored from the saved fold models, protocol hash, recorded verdict. No E128 file was modified. Input hashes are in `out/e129_summary.json`.

| E128 finding | Still applies to provincial work? |
|---|---|
| SWS is regional; 20 independent quarters; T1 saturated since 2023-Q4 | Yes (unchanged fact) |
| No model reliable at any lead on the regional target | Yes, for the regional target only. **It says nothing about provincial forecasts**, which were not evaluated. |
| T43c not admissible (copied hunger term) | Yes |
| Overfitting with 25 features on 6–18 rows | Re-assess. A provincial panel has more rows, but its effective sample is about 29 for food CPI (design effect from 74 % shared variance). |
| Trigger groups add no stable value | Re-assess. E128 used regional or national versions. Provincial price, production, local typhoon, centroid climate and news-volume features were not tested provincially. |
| R1 unattainable (40 rows) | Re-assess. Attainable for a 5-province panel, if the target is genuinely provincial. |

## Gate criteria and result

| # | Requirement for a provincial food-insecurity target | Result |
|---|---|---|
| G1 | Measures food insecurity (experienced FI or hunger), not a correlate | Only FNRI FIES / CBMS FIES / SWS hunger qualify |
| G2 | Observed separately for each of the 5 provinces | FNRI 2021: 2 provinces. CBMS 2024: 5 (not held). SWS: no. |
| G3 | Repeated over time (≥ 10 periods per province, to support Lead 1–4 and R1) | **No source**: at most 1–2 periods |
| G4 | Dated publication (point-in-time usable) | FNRI / CBMS yes; SWS microdata unknown |
| G5 | Held or obtainable under current authority | Not held; requests (E87 A, B, C) unsent; PSA regional and NNC sites 403 |
| G6 | Not constructed from the predictors | Measured sources yes; index options no |

## Decision

**The gate fails at G3, and at G5 for every repeated source.** No official provincial food-insecurity measurement exists as a time series for 2021–2026, so:
- **no provincial food-insecurity forecasting accuracy can be established** at any lead;
- **no provincial training run is authorized** by E129.

## Defensible today, each under its own name

| Product | Target | What it validates |
|---|---|---|
| Regional hunger reference | SWS Balance Luzon (continuous) | Regional hunger forecasting (E128: no reliable lead yet) |
| **Provincial food-price pressure forecast** | Provincial food CPI YoY (continuous, measured, official, 5 × 23) | Food-price conditions by province, **not** food insecurity |
| Provincial risk index | FIRI3 (declared composite) | Index values; validation only cross-sectional against CBMS / ENNS |
| Cross-sectional provincial / LGU validation | CBMS 2024 FIES, ENNS 2021 / 2022 | Whether risk rankings match measured FI (once obtained) |
