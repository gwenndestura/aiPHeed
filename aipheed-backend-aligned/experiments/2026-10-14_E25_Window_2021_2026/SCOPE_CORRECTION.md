# Scope correction: E24v2 used data from before 2021

**Study window:** 2021-Q1 to the latest authorized 2026 quarter (currently 2026-Q2: January–June 2026).

E24v2 (`2026-10-14_E24v2_Reliable_Forecasting/`) used pre-2021 data. **Everything listed below is out of scope and is not evidence.** E24v2 is kept read-only and unchanged; E25 writes only to this folder.

## E24v2 items that used pre-2021 data

| Item (E24v2 path) | Pre-2021 content | Status |
|---|---|---|
| `acquisition/cpi_index_1994_2017_ACP28.csv`, `cpi_index_2018_2020_ACP22.csv`, `cpi_yoy_2019_2020_ACP23.csv`, their `raw/` responses | 1994–2020 provincial CPI | **Out of scope, not evidence** |
| `acquisition/subsistence_pop_prov_huc_2018_2023.csv`, `poverty_pop_prov_huc_2018_2023.csv` | Contain 2018 rows (mixed file) | **Out of scope, not evidence.** Not loaded in E25. |
| `data/monthly_yoy_1995_2025.csv`, `quarterly_D_1995_2025.csv`, `dnow_1995_2025.csv` | 1995–2020 rows; the 2021 YoY values were computed from 2020 indices | **Out of scope, not evidence** |
| `data/comparability_gate.json` | Gate (ii) on 2019–2020; gate (i) used 2020 indices | **Out of scope, not evidence** |
| `runs/BX_20261013T163710Z`, `runs/BX_20261013T223930Z` (back-cast) | Trained and tested on 1995–2020 | **Out of scope, not evidence.** Void: **HB1–HB4**, "0.713 vs 0.617 on 94 unseen quarters", "reliable up to 5 quarters / strict 2 quarters", "the provincial component generalizes". |
| `runs/DEV_*`: FINAL_V2_PCF, PCF_S_supplementary, PCF_n300_sensitivity, PCF_NOW_A3 (T1); M3_pcf_D, FINAL_V2_M4_pcf_D_now, B1p (T2) | D models and T2 calibrated persistence trained on pairs from 1995 onward | **Out of scope, not evidence.** Void: "PCF 0.900 vs 0.875", "Brier 0.104 vs 0.162 (p = 0.016)", "M4 0.836", "C1–C6 met for T2". |
| `runs/DEV_*`: the noise ceiling | Uses 2021+ SWS rounds and labels only | In scope; recomputed in E25 |
| `runs/SEAL_20261013T164218Z`: arms FINAL_V2_PCF, PCF_S_supplementary (T1); B1p, M1_lr_P_1995window, M3_pcf_D, FINAL_V2_M4_pcf_D_now (T2) | Trained on 1995+ D history | **Out of scope, not evidence.** The seal is kept unchanged, but these arms' future scores cannot support any claim. |
| `runs/SEAL_20261013T164218Z`: arms B1, B1p, M2_lgbm_P_E24frozen (T1); B1 (T2) | 2021+ inputs only | **In scope.** Scorable after you authorize the outcomes. |
| `runs/SEAL_20261013T222814Z` (PCF_NOW_A3) | 1995+ D history | **Out of scope, not evidence** (kept unchanged) |
| `runs/provincial_validity.json` | 2018 rows | **Out of scope, not evidence** |
| `runs/lgu_analysis.json`, `LGU_RANKING_VALIDATION.csv` | Province probabilities from the out-of-scope PCF | Probability-based ranks: **out of scope, not evidence.** The density-vs-poverty finding (2021 SAE) is in window; recomputed in E25. |
| `BASELINE_COMPARISON.csv`, `PREDICTIONS_BY_QUARTER.csv`, `FEATURE_ABLATION_RESULTS.csv` | Back-cast rows and all new-arm rows | **Out of scope, not evidence** (E24 arm rows are superseded by E25) |
| `backend_dev/data/inputs/d_quarterly_panel.csv`, `dnow_panel.csv`, `config/evidence_status.json`, and the replay and live records built from them | 1995+ panels; T2 marked "SUPPORTED" from the back-cast | **Out of scope, not evidence** |
| `dashboard_dev/public/e24v2_dashboard.json`, both E24v2 PDFs, the `/forecast-period` page | Present the back-cast as evidence | **Out of scope, not evidence.** Replaced by E25 outputs. |
| `FROZEN_EVALUATION_PROTOCOL.md` §2.1–2.4, §6 (HB1–HB4); `PROTOCOL_AMENDMENTS.md` A2 (T1 back-cast) and A3 (justified by the back-cast); `runner/bx_data.py`, `run_bx.py`, `run_bx_t1.py`, the pre-2021 parts of `acquisition/fetch_openstat.py` | Pre-2021 design | **Out of scope, not evidence** |
| `FINAL_REPORT.md`, `ROOT_CAUSE_ANALYSIS.md` §3, `DATA_ACQUISITION_REGISTER.md` (P1), `ADVISER_AND_AUTHORIZATION_CHECKLIST.md` A1, B5 | Claims built on the back-cast; the request for SWS 1998–2020 | **Out of scope, not evidence.** The SWS 1998–2020 request is **withdrawn**. |

## Also found while checking (inherited from E23/E24, in-window files)

`features_fused.parquet` is read only for 2021-Q1…2025-Q4, but some 2021 cells still encode 2020 values:

| Cells | Pre-2021 value they carry |
|---|---|
| `*_lag1` and `*_accel` at 2021-Q1 | 2020-Q4 |
| `FSSI_lag2` at 2021-Q1/Q2 | 2020-Q3/Q4 |
| `cpi_dev` at 2021-Q1…Q4 | Mean over t−4…t−1, which includes 2020 |

The E23/E24 required-model results therefore used a little pre-2021 information in their earliest training rows.

**E25 masks the lag/accel cells, recomputes `cpi_dev` from 2021+ quarters only, and re-runs every required model.**

**Residual risk (not removable without the unauthorized raw sources).** `features_fused` was built with "forward-fill within province, then zero-fill". A 2021 value could therefore be a 2020 value carried forward. It cannot be detected from the authorized 2021+ rows.

## What remains usable from E24v2

- The PCF engine design (H local level; D least squares). Its D part is re-trained in E25 on 2021+ pairs only.
- The pipeline mechanics (non-blocking news, REPLAY mode, seal refusal logic).
- The in-scope seal arms listed above.
- The noise-ceiling method.
- The 2021-SAE density-vs-poverty finding.
- `acquisition/cpi_index_2021_2025_ACP22.csv` (2021–2025 rows only; public PSA; the authorization basis still awaits your confirmation, A6). E25 uses it only to build the monthly nowcast Dnow, from 2022-Q1 onward. The 2021 year-on-year rates would need 2020 indices, so they are not computed.
