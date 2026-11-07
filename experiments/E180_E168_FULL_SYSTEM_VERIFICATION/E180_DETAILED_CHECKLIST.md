# E180 detailed checklist: E168 and the aiPHeed system (2026-11-07, updated after local fixes)

Legend: ✅ verified correct · ⚠️ works but needs qualification or a limitation disclosed · ❌ incorrect or missing

## A. E168 model
| # | Item | Status | What was checked | Result |
|---|---|---|---|---|
| A1 | Algorithm is LightGBM | ✅ | `app/e168/lgbm.py`, `app/e151/prov.py` Res2 | LightGBM survey-error model only |
| A2 | Settings | ✅ | `app.e150.model.PARAMS` | 4 leaves, depth 2, min child 10, learning rate 0.02, L2 5, 80 % row/column sampling, seed 151, trees 100/300/600 |
| A3 | Lock integrity | ✅ | re-hashed `data/e168/out/lock.json` | 0 of 12 files changed since 2026-11-06 |
| A4 | Sealed forecast | ✅ | `sealed_2027-Q1.json` vs `history/2027-Q1.json` | identical; hash 28f2c918 |
| A5 | Per-issue configuration | ✅ | `results.json` config_by_issue | 2018/2019: OH anchor, FULL; 2021: RSS, GOV; live: RSS, FULL, λ 0.751 |
| A6 | Training rule | ✅ | `app.e150.model.released` | only rounds released before each issue date |
| A7 | Reproducibility | ✅ | E171/E172/E173 refits; `recalculate.py` | refit difference 0.0; metrics identical at all 8 leads |
| A8 | Saved model file | ⚠️ | artifacts | none: E168 is reproduced by deterministic refit; served values are precomputed JSON |

## B. Statistical performance (recomputed, independent code)
| # | Item | Status | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|---|---|
| B1 | Correct / 72 | ✅ | 56 | 55 | 54 |
| B2 | Accuracy (>= 75 % rule) | ✅ | 77.78 % | 76.39 % | 75.00 % |
| B3 | Confusion tp/fp/tn/fn | ✅ | 23/14/33/2 | 23/15/32/2 | 22/15/32/3 |
| B4 | Majority rate | ✅ | 65.28 % | 65.28 % | 65.28 % |
| B5 | Effective sample size | ✅ | 45.55 | 45.55 | 45.55 |
| B6 | C1 low bound (> 65.28 %?) | ⚠️ | 65.70 % pass | **64.05 % fail** | 62.42 % fail |
| B7 | C2 Brier beats persistence | ✅ | pass | pass | pass |
| B8 | C3 both classes >= 50 % recall | ✅ | pass | pass | pass |
| B9 | C4 calibration slope includes 1 | ✅ | pass | pass | pass |
| B10 | C5 beats persistence in >= 2 rounds | ✅ | pass | pass | pass |
| B11 | C6 >= 40 rows | ✅ | pass | pass | pass |
| B12 | Strict C1-C6 | ⚠️ | **6/6** | 5/6 | 5/6 |
| B13 | ROC-AUC (>= 0.80) | ✅ | 0.895 | 0.887 | 0.860 |
| B14 | F1 (>= 0.75) | ❌ | 0.742 | 0.730 | 0.710 |
| B15 | Brier | ✅ | 0.139 | 0.137 | 0.150 |
| B16 | `leads.py` matches independent code | ✅ | yes | yes | yes |
| B17 | Evaluation independence | ⚠️ | 72 rows reused in about 29 experiments; only E168's pre-registered result is held-out evidence | | |

## C. Target validity
| # | Item | Status | Finding |
|---|---|---|---|
| C1 | Measures food insecurity directly | ✅ | HFIAS household food-insecurity scale |
| C2 | Exact definition | ✅ | moderate + severe share >= 50 % (identical to mod_sev_pct) |
| C3 | Same instrument across rounds | ✅ | NNS 2013, FNRI 2015, ENNS 2018/2019/2021 all HFIAS; FIES excluded |
| C4 | SWS Balance Luzon | ✅ | not the target; only used for probability scaling; covers all Luzon outside Metro Manila |
| C5 | Provincial truth for 2023-2026 quarters | ⚠️ | none: those quarters are back-forecasts |
| C6 | 2027-Q1 outcome | ⚠️ | sealed; no provincial HFIAS round scheduled to score it |
| C7 | Code naming | ⚠️ | `outcomes("insecure")` actually returns moderate+severe (name misleading) |

## D. Five risk drivers
| # | Driver | Status | Source / resolution | Share of 2027-Q1 attribution | Issue |
|---|---|---|---|---|---|
| D1 | Market / Prices | ✅ | PSA CPI, provincial | 15.0 % | current-vintage data |
| D2 | Climate Stress | ✅ | NASA POWER, IBTrACS, PSA crops (provincial); ONI (global) | 52.8 % | centroid climate |
| D3 | Fish Production | ✅ | PSA fisheries production, provincial | **0 %** (all 17 quarters) | FIXED label; 0 % disclosed |
| D4 | Employment | ⚠️ | PSA LFS, **national** | 8.2 % | not provincial |
| D5 | OFW Remittance | ⚠️ | BSP, **national** | 1.3 % | not provincial |
| D6 | Other inputs (news tone, poverty, density, survey history) | ⚠️ | mixed | 22.8 % | not shown on the dashboard |
| D7 | Any displayed driver missing from the model | ✅ | all five map to real inputs | | |

## E. SHAP / explainability
| # | Item | Status | Finding |
|---|---|---|---|
| E1 | Attributions from the served model | ✅ | LightGBM pred_contrib of each issue's chosen configuration |
| E2 | Additivity | ✅ | base + contributions = forecast (asserted < 1e-6, 17 quarters) |
| E3 | Correct province, lead, issue | ✅ | per province Lead-1 row of each issue |
| E4 | Model-wide SHAP / H1 | ✅ | FSSI rank 9, food-CPI deviation rank 10; H1 supported |
| E5 | Required share formula (Σ|SHAP| group ÷ Σ|SHAP| all) | ✅ | FIXED 2026-11-07: dashboard.py uses |SHAP| of all inputs |
| E6 | otherPct returned and shown | ✅ | FIXED: API returns otherPct; panel shows "Other model inputs" |
| E7 | Five + other = 100 % | ✅ | FIXED: Batangas 32/30/8/1/0 + other 29 = 100 (tested) |
| E8 | Non-causal wording | ⚠️ | attributions are associations; keep the note |

## F. NLP
| # | Item | Status | Finding |
|---|---|---|---|
| F1 | News reaches E168 as input | ✅ | 36 news inputs; 23.6 % of attribution |
| F2 | Data up to the live issue | ✅ | news panel 2013-Q1 to 2026-Q4 |
| F3 | H1 (FSSI) supported | ✅ | rank 9 |
| F4 | 300-headline annotations in the repository | ❌ | not found |
| F5 | Inter-annotator agreement (kappa) | ❌ | not computed anywhere |
| F6 | Classifier validated | ❌ | `validation_result.json`: n_annotated 0 |
| F7 | News volume | ⚠️ | 3-12 articles per province per quarter |
| F8 | Missing news handling | ⚠️ | no news = 0.0 (looks neutral) |
| F9 | One news count everywhere | ⚠️ | dashboard feed ≠ model panel counts |

## G. Data and leakage
| # | Item | Status | Finding |
|---|---|---|---|
| G1 | Future survey outcomes excluded | ✅ | corruption test: 0.0 change |
| G2 | Future SWS excluded | ✅ | 0.0 change; unit-tested |
| G3 | Issue < outcome, anchor < issue | ✅ | all rows |
| G4 | Duplicates / mapping | ✅ | none / correct |
| G5 | Data vintages (revisions) | ⚠️ | current-release series; not reconstructable |
| G6 | Provenance inventory | ✅ | `DATA_PROVENANCE_AUDIT.csv` (15 datasets) |

## H. Geospatial
| # | Item | Status | Finding |
|---|---|---|---|
| H1 | Province polygons | ✅ | 81 provinces; 5 CALABARZON |
| H2 | Municipality join | ✅ | 142 / 142 matched (name-key join) |
| H3 | Provincial values = E168 forecasts | ✅ | per-province history values |
| H4 | Map colours vs classification | ✅ | riskLevel from 0.50 / 0.60 thresholds |
| H5 | Municipal values | ⚠️ | Algorithm 5 ranking, not forecasts |

## I. Backend and frontend
| # | Item | Status | Finding |
|---|---|---|---|
| I1 | Province probabilities | ✅ | API = E168 history |
| I2 | Thresholds | ✅ | 0.50 display, 0.60 alert, < 5 articles limited |
| I3 | History chart | ✅ | FIXED: every E168 value flagged isForecast true |
| I4 | Risk card label | ✅ | FIXED: "Food-insecurity risk" |
| I5 | Landing / About text | ✅ | FIXED: describe E168, its accuracy, seal 28f2c918 and limitations |
| I6 | "Fish Kill" label | ✅ | FIXED: "Fish Production" |
| I7 | PDF report / config / thesis routes | ✅ | describe E168 (uncommitted fixes) |
| I8 | Alerts | ⚠️ | queue is empty and not E168-based (none warranted: max P = 0.075) |
| I9 | Mock data | ⚠️ | unused components; Admin SidebarPeek |
| I10 | Local CORS | ⚠️ | only port 5173 by default |

## J. Deployment
| # | Item | Status | Finding |
|---|---|---|---|
| J1 | Deployed branch contains E168 | ❌ | Render deploys main; E168 not merged |
| J2 | Render env serves E168 | ❌ | AIPHEED_LEAD2_MODEL=thesis disables E168 → Chapter I model served |
| J3 | Silent fallback | ❌ | falls back to the old engine without warning |
| J4 | Scheduled updates use E168 | ❌ | quarterly cycle has 0 E168 references; manual regeneration needed |
| J5 | Health check / persistence | ✅ | /api/v1/config; 1 GB disk |

## K. Tests
| # | Item | Status | Finding |
|---|---|---|---|
| K1 | Safe subset | ✅ | 69 passed, 8 skipped, 0 failed |
| K2 | Full suite | ⚠️ | not re-run: rewrites a tracked file; last run 1612 passed / 32 failed (27 legacy, 2 by design) |
| K3 | Test for the driver-share formula | ✅ | FIXED: test_driver_shares_use_abs_shap_over_all_inputs_and_add_to_100 |
| K4 | Test for deployment env | ❌ | missing |

## L. Thesis objectives
| # | Objective | Status | Basis |
|---|---|---|---|
| L1 | Food-insecurity forecasting | ✅ | HFIAS target; retrospective accuracy 76-78 % |
| L2 | Provincial forecasting | ⚠️ | survey-round level only |
| L3 | NLP integration | ⚠️ | integrated, not validated |
| L4 | Five drivers | ⚠️ | 2 national, fish 0 % and mislabelled |
| L5 | ML reliability | ⚠️ | Lead 3 (75 % rule); strict at Lead 1 only; F1 0.742 |
| L6 | Geospatial visualization | ✅ | map and join verified |
| L7 | Explainability | ✅ | FIXED locally: correct shares + other |
| L8 | Deployed decision support | ❌ | production not on E168 |

## M. Protected state
| # | Item | Status |
|---|---|---|
| M1 | E168 seal 28f2c918; lock unchanged | ✅ |
| M2 | SIMPLE ad38a0f1; E173 seal 55c1bd37 | ✅ |
| M3 | E172-E178 and E168 data fingerprint unchanged | ✅ |
| M4 | Backend, frontend, service files unchanged; Git status identical | ✅ |

## Totals
✅ verified: 64 · ⚠️ qualify: 24 · ❌ incorrect or missing: 10 (10 fixed locally on 2026-11-07; not yet deployed)

## Fix order before submission
1. J1-J3 production on E168 → 2. E5-E7 driver shares + otherPct → 3. I4, I5, I6 labels and text → 4. I3 back-forecast flag →
5. F4-F6 add annotations and kappa (or disclose) → 6. thesis wording for B6/B12/B14, C5, D4/D5, L2-L5.
