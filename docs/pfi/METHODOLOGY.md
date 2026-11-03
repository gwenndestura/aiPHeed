# PFI: provincial food-insecurity estimation and next-quarter forecasting

Version `pfi-1.0` · code `backend/app/pfi/` · artifact `backend/data/pfi/model/pfi_model.json` (sha256 in the file) ·
evaluation `backend/data/pfi/out/evaluation.json` · built 2026-11-03.

> **Status: CANDIDATE, REJECTED by the release gate (2026-11-03).** Not shown on the dashboard and not served by any
> public route. Review copies only at `/api/v1/admin/candidates/pfi-1.0/*` (admin login). Gate result:
> `backend/data/registry/gate_results/pfi-1.0.json`; see `docs/release/FINAL_VERIFICATION_REPORT.md`.

## 1. Why the method changed

Earlier engines (P0H4, FI9, FI10, CH1) predicted SWS regional hunger, a price-pressure proxy, or provincial food
inflation. None predicted a measured food-insecurity outcome for provinces. The owner workbook and the public FNRI/PSA
tables hold the only food-insecurity measurements available:

| Source | Instrument | Geography and years | Status | Role in PFI |
|---|---|---|---|---|
| FNRI NNS/ENNS via PSA OpenSTAT (SDG 2.1.2) | FIES moderate-or-severe, 12-month recall | 17 regions 2023; national 2021, 2023 | verified primary | **Outcome.** Level model (17 regions), benchmark (CALABARZON 19.1%, CI 17.0–21.1), bridge fit (national 2021→2023) |
| FNRI 2025 Updating Survey (reported by PIA) | FIES | CALABARZON 2025: 22.6% | provisional secondary, no CI | Held-out test of the bridge, then a state update |
| FNRI 2015 Food Security Survey | HFIAS | 5 provinces, with SEs | verified primary | Direct provincial evidence in the composite (relative position only; never used as a FIES value) |
| ENNS by province (RDP results matrix) | not stated | one year per province, 2018–2021 | secondary, unverified | Consistency check only |
| PSA poverty and subsistence incidence | income-based | regions and provinces 2021, 2023 (with CVs) | official | Structural covariates of the level model |
| SWS involuntary hunger | 3-month hunger | Balance Luzon and national, quarterly | measured | Quarterly movement between survey waves |

Different constructs are never pooled into one label. No annual value is interpolated into a quarterly label.

## 2. Final methodology

Outcome: **share of households moderately or severely food insecure (FIES)**, by province, for the next calendar quarter.

Three layers, each validated on its own evidence:

1. **Level (small-area estimation).** `logit FIES_r = a + b·logit(subsistence_r)` across the 17 regions (2023). Seven
   candidates, one per information group plus two pairs, scored leave-one-region-out; rule fixed before scoring: lowest
   LOO MAE, fewer covariates within 0.25 pp. Selected: subsistence (food poverty), b = 0.256.
   Provinces: Fay-Herriot composite of (a) the direct FNRI 2015 provincial offset from CALABARZON (published SEs plus an
   assumed drift allowance of 0.10 logit for 8 years and the instrument change) and (b) the regression offset, using
   provincial covariates shrunk by their published CVs (Ybarra–Lohr). Weight on the direct value = between-area variance
   / (between-area + direct variance). The provincial values are then benchmarked so their population-weighted mean equals
   the direct CALABARZON survey estimate.
2. **Bridge (time).** `Δ logit FIES = λ · Δ logit SWS12`, SWS12 = mean of the year's quarterly SWS readings. λ = 0.55
   from national 2021→2023 (both verified, in the study window), bootstrap 90% CI 0.07–2.0 (wide: one interval).
3. **State and projection.** Region state 2023 = survey; 2025 = bridge prediction combined with the 2025 value by
   inverse-variance weighting (weight 0.94 on the measurement); target quarter = 2025 state bridged with the 12-month SWS
   window ending in the target quarter. Unobserved quarters use FI9's frozen damped persistence (φ 0.67, conformal
   half-width 10.4 pp), normal = mean of the last 20 published quarters.

Uncertainty: 20,000 Monte Carlo draws with a fixed seed (survey error of the anchor, coefficient and between-area error,
covariate sampling error, λ, SWS sampling and projection error). Output per province: 2023 estimate, current estimate,
forecast median, 80% and 90% ranges, P(significantly above the 2023 level), P(rise), exact two-factor Shapley split
(province structure vs change since 2023), approximate persons in food-insecure households, priority rank.

Class: **Elevated (HIGH)** when P(forecast ≥ 2023 estimate + 2.05 pp, the 2023 survey margin) ≥ 0.5.

## 3. Results (all recomputable with `python -m app.pfi.engine build`)

### 3a. Level model, leave-one-region-out (17 regions, FIES 2023; independent observation-level validation)

| Candidate | MAE pp | RMSE pp | Spearman | 95% PI coverage | Accuracy* | Bal. acc. | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 no covariate | 7.26 | 8.61 | −1.00† | 0.94 | 0.65 | 0.50 | 0.65 | 1.00 | 0.79 | 0.00† | 0.46 | 0.253 |
| M1 poverty | 5.39 | 6.20 | 0.76 | 0.88 | 0.94 | 0.92 | 0.92 | 1.00 | 0.96 | 1.00 | 1.00 | 0.079 |
| **M2 subsistence (selected)** | **5.30** | 6.23 | 0.69 | 0.88 | **1.00** | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **0.072** |
| M3 unemployment | 7.29 | 8.83 | 0.21 | 0.94 | 0.65 | 0.58 | 0.69 | 0.82 | 0.75 | 0.55 | 0.66 | 0.265 |
| M4 rice inflation | 6.12 | 7.62 | 0.34 | 0.94 | 0.65 | 0.61 | 0.73 | 0.73 | 0.73 | 0.55 | 0.72 | 0.241 |
| M5 poverty + unemployment | 5.67 | 6.64 | 0.75 | 0.94 | 0.88 | 0.83 | 0.85 | 1.00 | 0.92 | 0.97 | 0.99 | 0.101 |
| M6 poverty + rice inflation | 5.34 | 6.36 | 0.73 | 0.88 | 0.82 | 0.79 | 0.83 | 0.91 | 0.87 | 0.95 | 0.98 | 0.101 |

\* Class = region above the national prevalence (31.4%). Selected model: 11 TP, 6 TN, 0 FP, 0 FN; accuracy 17/17,
Wilson 95% CI 0.82–1.00. Calibration: bins 0.6–1.0 observed 1.0, 0.2–0.4 observed 0.0 (n per bin 1–7).
† A leave-one-out mean is mechanically anti-correlated with the held-out value.

Caveats: one wave; the class split is coarse (most regions are far from 31.4%); CALABARZON itself is over-predicted by
9.7 pp (28.8 vs 19.1), which is why provincial values are benchmarked to the direct survey estimate.

### 3b. Bridge, held-out survey wave

CALABARZON 2025 predicted from 2023 with Balance Luzon SWS (11.2% → 18.9%): **24.9%** vs 22.6% reported (error +2.3 pp);
no-change baseline 19.1% (error −3.5 pp); λ = 1 (error +7.9 pp). Class (above the 2023 CI): predicted HIGH, observed HIGH
(n = 1). Sensitivity (pre-2021, not used): national 2019→2021 moves in opposite directions (COVID lockdown hunger), so the
bridge does not hold across that shock.

### 3c. Provincial consistency (n = 5, weak evidence)

| | Spearman with served estimates |
|---|---|
| FNRI 2015 HFIAS (an input; not independent) | 0.6 |
| ENNS secondary values (not used by the model) | 0.0 |
| Synthetic-only variant vs ENNS | −0.8 (why the composite was needed) |

Sensitivity of the 2023 provincial estimates to the drift allowance (0 / 0.10 / 0.20): Quezon 21.8 / 21.4 / 20.7%;
the other provinces stay within 18.3–19.5%. Provinces differ by about 3 points, less than each forecast's range.

### 3d. Regional quarterly hunger component (input of the bridge; not a provincial result)

Next-quarter SWS Balance Luzon "significantly above normal", walk-forward 2010–2026, 62 quarters: served damped
persistence accuracy 0.82, balanced accuracy 0.71, HIGH recall 0.55; naive persistence 0.87 / 0.74 / 0.55.

### 3e. The 75% objective

| Task | Result | Status |
|---|---|---|
| Classifying measured food-insecurity levels of held-out regions | 17/17 (CI 0.82–1.00), balanced 1.00 | **Met** (one wave, regional resolution) |
| Bridge on a held-out survey wave | 1/1 correct class; MAE 2.3 pp vs 3.5 pp baseline | Supported, n = 1 |
| Provincial next-quarter forecasts | no survey measures provinces quarterly | **Not evaluable**; registered prospectively |
| Regional quarterly hunger class | 0.82 accuracy, 0.71 balanced | Accuracy above 75%, balanced below |

Maximum defensible horizon: one calendar quarter (the SWS projection's validated lead; beyond it the forecast is the
damped normal plus the structural level).

## 4. Information groups (FIRI v2 families)

| Group | Families | Tested how | Result | Role |
|---|---|---|---|---|
| Poverty and social vulnerability | V1 | M1, M2 | LOO MAE 7.3 → 5.3 pp | **Model input** (level) |
| Regional hunger | H1 | bridge + holdout | 2.3 vs 3.5 pp | **Model input** (time) |
| Market and food prices | A1–A3 | M4, M6 | 6.1 pp alone; no gain added to poverty | Secondary task (FI10 food inflation, shown as a driver column) |
| Employment and remittances | E1, E2 | M3, M5 | no better than no covariate | Supporting indicator; E2 national only |
| Climate and production | C1–C4 | no 17-region 2023 series on file | not tested for the level | Context and price drivers |
| News and NLP | N1 | no regional news series matched to FIES regions | not tested | Food-stress intelligence beside the forecast |

## 5. Geography

Five provinces get their own estimates. The 142 LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14) inherit
their province's forecast, labelled as such; LGU poverty (PSA SAE 2021, 141 of 142 published) is shown as structural
context. No municipal food-insecurity value is invented.

## 6. Operation

- `python -m app.pfi.engine build`: fit, evaluate, seal the artifact (refuses inputs released after `--as-of`).
- `python -m app.pfi.engine issue`: forecast for the next calendar quarter of the Philippine-time clock
  (`AIPHEED_NOW` overrides it). The API re-issues automatically when the quarter, the SWS cutoff or the artifact changes
  (inference only, ~0.2 s; never refits) and appends the first issue of each quarter to `register.jsonl`.
- Routes: candidate review only, `/api/v1/admin/candidates/pfi-1.0/{outlook,evaluation,model,lgus,register,gate}`
  (admin). The public `/api/v1/final/food-insecurity/outlook` serves only a registry-approved model and answers 503
  `validation_pending` while none is approved. Existing `/final/*` routes unchanged. Not on the dashboard.

## 7. Limitations

- One FIES wave with regional breakdown; λ rests on one verified interval (wide CI) and one provisional holdout.
- The 2025 value has no published CI; SE assumed 1.5 × the 2023 SE.
- Province offsets rest on the 2015 HFIAS survey plus an assumed drift allowance; provincial estimates are not measured.
- Survey release dates are approximate (conservative, month-end).
- FIES Region VI/VII 2023 predates NIR; their restated poverty figures exclude it.
- Next evidence: FNRI provincial FIES estimates (NNS/ENNS public-use files) or PSA 2026 FIES, scored against the register.
