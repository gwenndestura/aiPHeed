# E41: audit and correction of aiPHeed's Lead-2 forecast

**Date:** 2026-10-15.
**Branch:** `e41-lead2-audit` (local, not pushed), cut from `label-v3-e40` @ 371b64e.

**Commits**

| Commit | Content |
|---|---|
| `7960517` | protocol frozen before any score |
| `fb08144` | code and tests committed before the run |
| `002e1eb` | evaluation, repeat run and frozen forecast |
| `4971555` | backend integration |

**Not changed:**
- No approved frontend file.
- No production model, database, frozen record or original dataset.

**Readiness decision:** the Lead-2 price-pressure forecast is **ready for system demonstration and decision-support testing as an EXPERIMENTAL candidate**. It is **not ready to replace the served model** without your decision, and it **does not meet 75% accuracy at Lead 2**.

---

## 1. Initial findings: where the current accuracy and the 0.9x scores come from

| Claim or display | What it actually is | Evidence |
|---|---|---|
| **"Lead-2 ≥ 75%"** | P45 (the 45-feature LightGBM) at lead 2 on target T1_A: 31/35 = **0.886**. The rows were 33 HIGH and 2 LOW, and **P45 identified no LOW row (TN = 0)**. Always-HIGH scored **0.943** and persistence 0.829. The figure reflects a near-constant target, not skill. | `2026-10-14_Model_Selection_45_vs_12/MODEL_SELECTION_REPORT.md`, per-lead table |
| **Served Lead-2 model (E38-LGBM-NQ)** | **39/55 = 0.709** (95% CI 0.582–0.836), balanced 0.544, LOW recall 2/6, Brier 0.200. Persistence 0.800 (Brier 0.200); always-HIGH 0.891 (Brier 0.109). **Reproduced byte-identically** today (predictions sha `8fdfd027c8677867`). | `runs/e38_repro_20261015T095020Z/` |
| **Dashboard 2027-Q1 scores 0.95 / 0.95 / 0.95 / 0.95 / 0.80** | E38 probability of the **v1 relative label**. Four provinces get an identical value: the stump model splits only on Batangas's price pressure, and a prior shift of **+0.747 log-odds** lifts the model's ≈0.90 to 0.952. | `E38…/frozen/E38_PROSPECTIVE_2027Q1.json` |

## 2. Root causes (verified)

| # | Root cause | Evidence | Status |
|---|---|---|---|
| R1 | **The target is relative and drifting.** T1_A/S1 = H + 2D > τ, where τ is the trailing median of past S1. Regional SWS hunger roughly doubled: the mean of approved quarters was 11.3% in 2021–22 and 22.5% over 2024-Q3..2025-Q1. So S1 exceeds τ almost every quarter: HIGH share 45% (2023), 65% (2024), 80% (2025), 95% (2026); 89% of Lead-2 outer rows. | `sws_rounds.csv`; E40 METHODS_NOTE; E38 diagnosis | **Main cause of the 0.9x scores.** The model faithfully estimates a label that is HIGH almost always. It is not evidence of household food insecurity: 2023 was 55% HIGH while CALABARZON had the lowest FIES, 19.1% (E35). |
| R2 | **Regional data extrapolated to provinces.** H is SWS Balance Luzon, one value for all five provinces, and 70% of S1's variance is this shared value (E35). | E35 SCORING_AUDIT | Provinces cannot be separated on hunger; most of the differentiation must come from prices. |
| R3 | **Prior shift** moves the intercept to the HIGH rate of the latest four labelled quarters, which is about 95%. | E38 freeze | Amplifies R1. |
| R4 | **Four of the five triggers have no input in the served model.** E38's COMPACT set keeps only price features inside trigger groups. Climate, Fish Kill, Employment and OFW are structurally 0, and "Market / Prices 100%" is a SHAP-grouping artefact. P45's 45 candidates did include climate, OFW, unemployment and news features. | `e31_engine.TRIGGER_GROUP_FEATURES`; P45 `governing_model.json` | Fixed for E41 as far as official data allow (§5). |
| R5 | **Accuracy alone was used as a success criterion** on a target with 89–94% HIGH rows. | §1 | A 75% accuracy is reachable by always-HIGH. E41 gates require balanced accuracy and beating baselines. |
| – | **SWS handling: no defect found.** | `sws_rounds.csv`; E25/E36–E40 tests | Quarters are assigned by fieldwork date (e.g. "First Quarter 2021 SWS Survey, April 28–May 2" → 2021-Q2). Availability is by posted date. The supplementary 2025-Q2/Q3 rounds are excluded. Quarters without an approved round carry no label and are never zero-filled. |
| – | **PSA CPI handling: no arithmetic defect.** | E41 check; E39 D4 | Labels use PSA's published YoY, not index levels and not month-on-month changes. Index-implied YoY matches published YoY within **0.05 points on 570 province-months**. **Construct issue:** v1's D is relative inflation (province minus the five-province mean), so a province with deflation can be HIGH when hunger is high (E39 D7). |
| – | **Leakage: none found** in E36–E38 or E41. | test suites | Future-scrambling tests pass. |

## 3. Data audit (study window 2021-01..2026-09; no pre-2021 value requested or loaded)

| Dataset | Source / table | Level | Reference period | Release lag (rule) | Coverage | Role in E41 |
|---|---|---|---|---|---|---|
| Food and headline CPI, published YoY | PSA OpenStat 0012M4ACP23 | Province | 2021-01..2026-09 | about 5–13 days; at the origin, months up to month 2 of t | complete | outcome (T-P, T-F); market features |
| Food and headline CPI index (2018 = 100) | PSA OpenStat 0012M4ACP22, **fetched 2026-10-15** | Province | 2021-01..2026-09 | same | complete (740 values) | base-effect projection |
| Hunger, approved rounds | SWS, `sws_rounds.csv` | **Region** (Balance Luzon) | 2021-Q2..2026-Q3 | posted date | 4 quarters with no approved round (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) | T-H; hunger features; E40 label |
| Palay and corn production | PSA OpenStat 0012E4EVCP0, **fetched** | Province | 2021-Q1..2026-Q2 | quarter t−1 | YoY from 2022-Q1 | Climate-stress **supply proxy** |
| Fisheries production (total, aquaculture) | PSA OpenStat 0132E4GVFP1, **fetched** | Province | 2021-Q1..2026-Q2 | quarter t−1 | YoY from 2022-Q1 | Fish-kill **supply proxy** |
| Unemployment and underemployment rate | PSA LFS 0021B3FKEI2, **fetched** | **National** | 2021-01..2026-08 | months of t−1 | complete | Employment (no provincial differentiation) |
| News titles, trigger hits | E31 store, E40 composition | Province | 2021-Q1..2026-Q4 | quarter t | 2,820 attributed titles; 192 trigger hits | News for all five triggers |
| FIES moderate+severe | DOST-FNRI NNS 2023 (19.1%, CALABARZON) | Region, annual | 2023 | – | one point | face validity only |
| PSA 2021 SAE poverty; POPCEN 2024 | PSA | City/municipality | 2021, 2024 | – | 141/142, 142/142 | LGU prioritization only |

**Not obtainable from an official in-window source in this run:**

| Indicator | Why not |
|---|---|
| OFW remittances (BSP) | P45's copy sits in a file containing 2020 rows, so it cannot be loaded. |
| PAGASA rainfall and typhoon series | P45's copy sits in a file containing 2020 rows, so it cannot be loaded. |
| BFAR fish-kill events | No series found. |
| DA provincial price monitoring | No series found. |
| DSWD food-assistance records | No series found. |
| Provincial or municipal hunger | No series found. |

These remain **missing**, never zero.

## 4. Label comparison

| Label | Meaning | Level | Prevalence | Observable every quarter? | Lead-2 predictability (best evidence) |
|---|---|---|---|---|---|
| v1 / T1_A: S1 = H + 2D > trailing median (served) | Above-usual composite, relative | Province (H regional) | 70% overall; 2026: 95% | No (4 SWS gaps) | No model beats persistence; best of 24 configurations in hindsight 0.727 (E38) |
| E39 FPP: food YoY > 4% (BSP ceiling) | **Food price pressure** | Province | 47.0% (54/115). By year: 2021 70%, 2022 50%, 2023 85%, 2024 25%, 2025 15%, 2026 33% (2026 = 3 quarters). Prevalence at 3%: 60.9%; at 5%: 34.8%. | **Yes** | **E41 M1 0.632, beats all baselines (§6)** |
| E40 P60 sustain-2 (researcher's, frozen 10-15) | Hunger above the 2021–22 P60 **and** price signal, two consecutive quarters | Province (H regional) | Development 11.1% (2023 0%, 2024 10%, 2025-Q1 60%); in 6 of 9 quarters all five provinces have the same label | No (4 SWS gaps) | Too few positives to train (E40 gate failed); E41 simulation Brier 0.071 vs 0.125 (§6, not significant) |
| Continuous F (food inflation) | Price level change | Province | – | Yes | M1 MAE 2.88 points vs persistence 3.50 |
| Continuous H (hunger) | Hunger level | Region | – | No | Persistence MAE 4.2 points vs mean 4.9; no model tried beyond these |

**Recommendation:** keep two layers. Price pressure (FPP/F) is provincial, observable every quarter and forecastable. Hunger (H) is regional and only monitorable. The E40 label can be reported as exploratory, derived from the two layers. The v1 relative label should not drive a "risk probability" display: it cannot recognize low-stress periods once hunger shifts upward.

## 5. Five-trigger audit (E41 M3, P45 configuration on rebuilt in-window features; 9 target quarters, 45 rows)

| Trigger | Features in E41 | Mean group \|SHAP\| | Drop-group accuracy (full model 0.556) | Only-group accuracy | Verdict |
|---|---|---|---|---|---|
| Market / Prices | 7 CPI features incl. base-effect projection | 0.54 | 0.511 | 0.622 | **Carries the real signal** |
| Hunger (SWS) | H_last, H_chg, H_age | 0.51 | 0.711 | 0.556 | Regional; removing it helps M3 |
| Climate Stress (palay/corn production) | 2 | 0.26 | 0.556 | 0.378 | Implemented; no predictive value shown |
| Fish Kill (fisheries/aquaculture production) | 2 | 0.24 | 0.600 | 0.311 | Implemented; no predictive value shown |
| Employment (national LFS) | 3 | **0.96** | 0.489 | 0.711 | **Spurious time proxy.** It is province-invariant; M3's AUC is 0.374, below chance, so a high SHAP does not mean a real driver. |
| OFW Remittance | none | – | – | – | **Not implemented**: no official in-window data |
| News (all five) | counts and trigger shares | 0.27 | 0.556 | 0.533 | Weak (192 of 2,820 titles match any trigger) |

- Correlated pairs (|r| ≥ 0.8 on training rows): F_now/HL_now, F_now/gap_now, under/ur, and H_last/ur_yoy, the last a shared time trend.
- **Conclusion:** the five triggers are now genuinely wired in. Only Market / Prices adds predictive information, so the E41 primary model (M1) uses only prices.
- **Display:** the dashboard trigger panel shows Market 100% and the other four at 0% for E41. The four zeros mean "no model input", which is true, not invented. The per-trigger official indicators are served as **observed evidence** by `/api/v1/lead2`.

## 6. Model comparison: Lead 2 (issued at O(t) = first day of quarter t+1; target t+2)

**Primary set S-P:** 19 target quarters (2022-Q1..2026-Q3), 95 province-quarters, 40 HIGH (42.1%).
- Pre-registered protocol, sha `2d415a41…`, frozen and committed before any score.
- The run was repeated byte-identically.
- CIs are date-cluster bootstrap.

| Method | Accuracy (95% CI) | Balanced | HIGH recall | LOW recall | Brier | ROC-AUC | MAE of F (points) |
|---|---|---|---|---|---|---|---|
| **M1 base-effect projection (primary)** | **0.632 (0.505–0.768)** | 0.617 | 0.53 | 0.71 | **0.203** | 0.744 | 2.88 |
| M1z, flat prices (sensitivity, not selectable) | 0.716 (0.589–0.842) | 0.673 | 0.40 | 0.95 | 0.189 | 0.790 | 2.53 |
| B0 majority | 0.432 | 0.502 | 0.95 | 0.05 | 0.311 | – | – |
| B1 persistence | 0.516 | 0.510 | 0.47 | 0.55 | 0.484 | – | 3.50 |
| B2 latest-month persistence | 0.600 | 0.597 | 0.57 | 0.62 | 0.400 | – | 3.21 |
| B3 seasonal naive | 0.400 | 0.400 | 0.40 | 0.40 | 0.600 | – | – |

**M1 confusion matrix:** TP 21, TN 39, FP 16, FN 19. PR-AUC 0.728 at 42% prevalence; log loss 0.583.

**Paired per-date Brier gain of M1** (one-sided, Holm):

| Against | Brier gain | Holm p |
|---|---|---|
| Persistence | +0.281 | 0.001 |
| Latest month | +0.197 | 0.001 |
| Majority | +0.108 | 0.006 |
| Seasonal | +0.397 | < 0.001 |

**Accuracy gains** (one-sided, unadjusted): +0.116 over persistence (p = 0.11); +0.200 over majority (p = 0.047).

**Secondary set S-ML:** 9 quarters, 2024-Q3..2026-Q3, 45 rows, 21% HIGH.

| Method | Accuracy | Brier | ROC-AUC |
|---|---|---|---|
| M2 logistic regression | 0.733 | 0.178 | 0.65 |
| M1 | 0.622 | 0.219 | 0.57 |
| M3 LightGBM (P45 configuration, all triggers) | 0.556 | 0.294 | 0.37 |
| Latest month | 0.689 | 0.311 | – |
| Persistence | 0.578 | 0.422 | – |

On S-ML, no paired difference between M1 and M2 or M3 is significant: Brier gain −0.042 vs M2 (p = 0.54) and +0.074 vs M3 (p = 0.16).

**The original models on their own target:** P45 0.886 at lead 2 (degenerate, TN = 0) and E38 0.709 (§1). They predict a different target, so they cannot be placed in the same table. Retraining P45's original 45-column matrix is blocked by the study-window rule (`features_fused.parquet` contains 2020 rows), so M3 is P45's configuration on the in-window rebuild.

**Lead 1** (context; target = the quarter under way at the origin; 19 quarters):

| Method | Accuracy | Balanced | Brier |
|---|---|---|---|
| M1 | **0.842** | 0.836 | 0.128 |
| Latest month | 0.705 | – | 0.295 |
| Persistence | 0.600 | – | 0.400 |
| Majority | 0.421 | – | 0.300 |

At lead 1, M1's Brier gain is Holm-significant over every baseline (p ≤ 0.001).

**Hunger layer:** persistence MAE 4.2 points (16 quarters) vs historical mean 4.9.

**E40 label** (development quarters 2023-Q2..2025-Q1; 8 quarters, 40 rows, 5 HIGH):

| Method | Accuracy | Brier | Hits / false alarms |
|---|---|---|---|
| Component simulation | 0.925 | 0.071 | 2 of 5 HIGH, 0 false alarms |
| Persistence | 0.875 | 0.125 | – |
| Always-LOW | 0.875 | 0.121 | – |

The simulation's paired p is 0.25, not significant. 2023-Q1 was withheld: too few SWS changes at that origin.

## 7. Reliability assessment

**Gates for M1:**

| Gate | Result | Detail |
|---|---|---|
| G0 validity | **pass** | 21 leakage, alignment and label tests: perturbing every value published at or after the origin leaves M1, M2, M3 and the E40 simulation unchanged; Lead-2 months verified; no pre-2021 value |
| G1 accuracy ≥ 0.75 | **FAIL** | 0.632 |
| G2 balanced ≥ 0.70 and both class recalls ≥ 0.60 | **FAIL** | 0.617; HIGH recall 0.53 |
| G3 beats baselines | **pass** | point estimates beat all four; Brier gain over persistence Holm p = 0.001 |
| G4 calibration-in-the-large | **pass** | −0.04 (CI −0.19..0.10) |

**Verdict:** *experimental* (G1 and G2 failed).

**Calibration:**
- Slope 0.60, i.e. over-confident at the extremes.

| Band | Rows | Mean p | Observed HIGH rate |
|---|---|---|---|
| Low | 38 | 0.19 | 0.24 |
| Watch | 34 | 0.48 | 0.41 |
| High | 23 | 0.88 | 0.74 |

- The bands are ordered and usable, but the High band overstates.

**Stability:**
- Accuracy by year: 0.60 (2022), 0.85 (2023), 0.55 (2024), 0.50 (2025), 0.67 (2026).
- By province: Batangas 0.79 and Rizal 0.68 are the best; Quezon 0.53 is the worst.
- M1 errs at turning points. The trailing drift extrapolated the 2023–24 rice surge into 2025. M1z, which holds prices flat, did better: 0.716. This was a sensitivity arm, so it is **not adopted post hoc**. It should be pre-registered against M1 for the prospective quarters.

**Uncertainty:**
- 19 independent quarters; provinces within a quarter are correlated, which is why CIs are by quarter.
- The 80% intervals for food inflation are wide, about ±4.7 points, which reflects real track-record error.

**Independence of the test:**
- Every 2022–2026 quarter has been read by earlier experiments, so this is development evidence.
- **Contamination log C-1:** an accidental print of the SWS file exposed the E40 holdout hunger values. E41 therefore scores the E40 label on development quarters only. E40's own sealed forecasts are unaffected.
- The first blind outcomes are **2026-Q4 (lead 1)** and **2027-Q1 (lead 2)**, frozen in `frozen/E41_PROSPECTIVE_2027Q1.json` (sha `37a3db25…`).

## 8. Risk-score assessment

| Question | Answer |
|---|---|
| Are the served 0.95 scores justified? | Only as P(v1 relative label HIGH), which is HIGH in 95% of 2026 rows. **They are not a probability of food insecurity.** |
| Can low-stress periods be recognized? | **v1: no.** E41: **yes.** 2027-Q1 is forecast Low/Watch: P(food inflation > 4%) = Quezon 0.49, Rizal 0.36, Laguna 0.29, Cavite 0.27, Batangas 0.19. Over 2022–26, Low-band forecasts (38 rows, mean p 0.19) were followed by HIGH in 24% of cases. |
| Is E41's score a probability? | Yes, of a **defined, observable event** (provincial food inflation > 4% in the target quarter), calibrated in the large. It is **price pressure**, labelled as such in every response, and never presented as hunger. |
| The three concepts | `/api/v1/lead2` returns **observed** evidence (value, level, quarter, age, source), the **forecast probability** (`scoreType = price_pressure_probability`) and the **operational band and alert candidate** (documented rule) as separate fields. The E40 probability is flagged `exploratory`. |
| Single-signal alarms | The alert candidate needs a High price-pressure band **and** regional hunger above 11.3%: two independent official signals. |

## 9. DA IV-A usefulness

**What the system can reliably tell DA IV-A (development evidence):**
- **Which provinces are likely to see food inflation above 4% in the current quarter:** lead 1, 84% accurate, well above every baseline.
- **A ranked, probabilistic two-quarters-ahead outlook for price pressure:** Brier clearly better than persistence and AUC 0.74, but only 63% accurate as a yes/no call.
- **The observed evidence behind each province:** food and headline inflation, regional hunger with its age, palay, corn and fisheries production changes, national unemployment, news volume, and explicit missing-data flags.
- **A plain-language reason for each forecast:** how much comes from year-ago prices (base effect) and how much from the recent price trend.

**Not suitable for operational claims:**
- household food insecurity or hunger probabilities, at any level;
- provincial hunger, since SWS is regional;
- municipal forecasts: LGU rankings stay relative prioritization from PSA poverty and density, with no municipal probability produced;
- Lead-2 yes/no calls presented as reliable;
- any statement that DA has validated the model.

## 10. Implementation record

**Experiment folder:** `aipheed-backend-aligned/experiments/E41_Lead2_Audit/`
- `PROTOCOL.md` + `runner/PROTOCOL_SHA256.txt`;
- `CONTAMINATION_LOG.md`, `DEVIATIONS.md` (D-1: a crash before any result; withheld E40 rows are now excluded from scoring);
- `runner/e41_fetch_gov.py`, `e41_lib.py`, `e41_evaluate.py`, `serve_local_e41.py`, `serve_frontend_e41.py`;
- `data_acquired/` (4 OpenStat tables with query, raw response and sha256);
- `tests/test_e41.py` (22 passed after the freeze; 21 + 1 skipped before it);
- `runs/20261015T101016Z` (primary) and `runs/20261015T101418Z` (byte-identical repeat);
- `runs/e38_repro_20261015T095020Z`;
- `frozen/E41_PROSPECTIVE_2027Q1.json` + `.sha256`.

**Backend (served only with `AIPHEED_LEAD2_MODEL=e41`; the default `e38` is unchanged):**
- `app/ml/inference/e41_lead2.py`: integrity-checked record, target check, five-trigger structure.
- `app/api/v1/lead2.py`: `/api/v1/lead2/summary` and `/api/v1/lead2/provinces/{id}`. Returns 409 when the dashboard target is no longer the record's target (no stale fallback), and 503 on an integrity failure.
- `app/services/dashboard.py`: the candidate replaces the E38 row for **exactly** its target quarter. Caches are keyed by the Lead-2 mode.
- `app/schemas/public.py`: optional `scoreType`, `scoreDefinition`, `riskBand`.
- `app/api/router.py`: the new router.
- `scripts/build_record_e41.py` → `data/e41/e41_lead2_record.json`, built from the frozen forecast.
- `tests/integration/test_e41_lead2.py`: 7 tests.

**Tests run:**

| Suite | Result |
|---|---|
| E41 | 22 passed (21 + 1 skipped before the freeze) |
| Backend full suite | **311 passed, 18 skipped** (the 18 are the known superseded tests; was 304 before E41) |
| E38 reproduction | byte-identical |

**Live check:**
- E41 API on port 8001 with the approved frontend unchanged on port 8082.
- Q1 2027 shows a regional index of 0.32; all five provinces Low; Market / Prices 100%.
- All `/api/v1` calls returned 200. The only console errors are the known missing `basemap.pmtiles`.
- Port 8000 was occupied by a backend this session did not start, and it was left alone.

**Reproduce** (from the repository root):
```
backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider aipheed-backend-aligned/experiments/E41_Lead2_Audit/tests
cd aipheed-backend-aligned/experiments/E41_Lead2_Audit && ../../../backend/venv/Scripts/python.exe -B runner/e41_evaluate.py
cd backend && venv/Scripts/python.exe -B scripts/build_record_e41.py && venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
```

## 11. Limitations

- **Lead-2 accuracy is 0.632 and the 75% target is not met.** The limiting factor is the unknown five-to-seven months of future food-price changes (e.g. rice policy shocks). It is not a code defect.
- **Few independent observations:** 19 quarters, all seen by earlier experiments. Prospective outcomes are pending.
- **No official in-window series** for OFW remittances, PAGASA climate, BFAR fish kills or provincial hunger. Climate and fish triggers rely on production proxies with no shown value.
- **The 4% threshold** is a BSP headline-target ceiling adopted as a tool default (E39). It is not adviser-endorsed and not food-specific.
- **The E40 probability** rests on an independence assumption between hunger and CPI paths, and on only 5 HIGH development rows.
- **The approved frontend's trigger copy** describes a direction even at 0% ("Weather is hurting food supply"). It needs your decision to change.

## 12. Final recommendation

1. **Ready for demonstration and decision-support testing:** the E41 two-layer output, enabled with `AIPHEED_LEAD2_MODEL=e41`, as an **experimental price-pressure early warning** with observed evidence and warnings.
2. **Not ready:**
   - replacing E38 as the default. That changes what the dashboard's main number means and needs your (and your adviser's) decision;
   - any claim of 75% Lead-2 accuracy or of validated food-insecurity forecasting.
3. **Still needs methodological work:**
   - score the frozen 2026-Q4 and 2027-Q1 forecasts once their outcomes are released;
   - pre-register M1 vs M1z (flat-price base effect) for the next origin (2027-01-01);
   - decide on the target (the two-layer design vs v1);
   - obtain official OFW and climate series if the five-trigger design must carry data.
