# Research gaps and root causes (Phase 0)

Each gap: what is observed, the likely causes with the evidence for each, and whether a cause is testable without
compromising existing evidence. "Tried" lists earlier experiments, so they are not repeated.

## G1. News (FSSI) changes no forecast (Objective 1)

**Observed:** C-b's FSSI anomaly has 0.0% SHAP and changes 0 of 62 calls; every construction that let news carry
weight lost accuracy (REF+news, C-a, GDELT 2015+).

| Cause | Evidence | Testable? |
|---|---|---|
| **Temporal coverage:** news exists from 2021 (anomaly from 2023-Q2); about 90% of the 1998–2026 training rows have no news, so a tree model trained on all history cannot learn a news effect | `PHASE2_INVESTIGATION.md` §5; news SHAP 15.8% *within* the news era for REF+news | Partly: a news-era-only model has about 20 labelled quarters, so any result is underpowered |
| **Geographic mismatch:** the target is Balance Luzon (about 12 regions); the news is CALABARZON-tagged (296 province-attributed headlines) | Target definition; `OBJ1_NLP_PIPELINE.md` §3 | Not fixable: no CALABARZON hunger series exists |
| **Signal validity:** only disaster share tracks its reference (ρ 0.81); price and jobs shares do not | E112 §2 | Yes, and partly done |
| **Representation:** level FSSI drifts with corpus growth; the anomaly removes drift but leaves 8–14 values | NEWS_V2 | Tried (C-a, C-b) |
| **Unmeasured pipeline accuracy:** relevance and geocoding precision/recall never measured on labelled data, so noise could be pipeline error | No labelled set in the repository (the paper's "371 audited" set is not present) | **Yes:** needs about 300 headlines labelled by two team members (inter-rater κ) |
| **Real-world limitation:** quarterly hunger in Balance Luzon may simply not be anticipated by CALABARZON headlines | All of the above | It is the conclusion if the tests above hold |

**Tried:** REF+news, I1/I2/I3 ± news, C-a (8 anomalies), C-b, GDELT 2015–2026 (OLD_NEWS), news-era diagnostic.

## G2. AUC 0.70 and the 2015–2020 failure (Objective 2)

**Observed:** C-b AUC 0.702; follows persistence in 77% of quarters; 10 of 13 Lead-1 errors are persistence's call;
2015–2020 accuracy 0.571.

| Cause | Evidence | Testable? |
|---|---|---|
| **Label noise:** SWS ±5.7 points; noise ceiling 0.849 overall, 0.773 in 2015–2020; noise-floor Brier 0.103 | Phase A §3A | Measured |
| **Raw last reading as the state:** `h_last` is one noisy survey value; nothing in C-b estimates *true* hunger from the history of noisy readings | `hr_lib.rows_t2` (h_last, h_mean4 and h_change are raw); NOISE_W changed only training weights | **Yes, new:** a measurement-error state-space (local-level Kalman) estimate of true hunger and of P(true > 11.3), with per-quarter variance from the number of rounds |
| **Discrimination vs threshold:** K1 (C-b + LOGIT) reaches AUC 0.786 but loses accuracy at the fixed 0.50 cut | Phase C §2 | **Yes, new combination:** K1 with a walk-forward threshold chosen on past forecasts only. RELIABLE_L12 tried thresholds on REF only (0 calls changed) |
| **Small n:** 62 labelled quarters at quarterly frequency | Phase A §3C power | Not fixable historically; prospective only |
| **Missing drivers:** remittances (BSP blocked, HTTP 403), provincial unemployment (national LFS only), 4Ps / social assistance | `MORE_SOURCES/SOURCES.md`, `APIS_CHECK.md` | Only if you supply the files; otherwise documented |

**Tried (do not repeat):** E99 (paper pipeline, MRLT 0), P0H4, HISTORY_RETRAIN (T1/T2, GRU, LOGIT), IMPROVE_V2 (pooled
areas, level regression, Platt), Leads 1–15, per-origin threshold, π-blend, CHIRPS rainfall, GDELT, news anomalies,
measurement-error weights, K1–K3.

## G3. "Province-level" (Objectives 2 and 3)

**Observed:** the outcome is regional; provinces differ only through vulnerability weights.

| Cause | Evidence | Testable? |
|---|---|---|
| SWS publishes Balance Luzon only; FNRI FIES is provincial only for Batangas and Cavite in 2021, and regional in 2023 | `nns_fies_verified.json` | No: the data do not exist. Copying the regional value to provinces would be fabrication |
| The paper's Eq. 3 province label (SWS + 2 × CPI deviation) was tried: label leakage (global median) and regime switch, MRLT 0 | E99; `label_guard.py` | Tried |

## G4. LGU ranking method (Objective 3)

| Problem | Evidence | Testable? |
|---|---|---|
| **Density works against poverty:** Spearman −0.53; the 40% density weight ranks urban, low-poverty LGUs first | Computed in this audit from `cb_lgu_2026-10-01.csv` | **Yes:** sensitivity of ranks to weights (Kendall τ, top-10 overlap) |
| Province factor P × poverty / max is undocumented in the paper | `align_cb.py` spatial | Yes: document it, or replace it by the paper's Eq. 6 (P × vulnerability) with an adviser decision |
| Mixed poverty sources (Lucena) and SAE CVs above 20% in 25 LGUs | `lgu_vulnerability.csv` | **Yes:** Monte Carlo rank uncertainty from the CVs |
| No independent check | — | Partly: DSWD Listahanan / 4Ps household shares per LGU (if obtainable); ENNS 2021 Batangas/Cavite; DA evaluator ranking (H4) |

## G5. Statistical superiority (Objective 4)

**Cause:** power (Phase A §3C). The logistic regressions are strong because hunger history is linear and dominant.
**The only honest remedy is the prospective sealed comparison**, which is already built and verified but uncommitted.

## G6. Dashboard and evaluation (Objective 5)

| Problem | Cause | Testable / fixable? |
|---|---|---|
| The deployed map serves the FIRI price score | Earlier decision to keep FIRI the default; C-b mode added as non-default | Fixable by configuration (`AIPHEED_MAP_MODEL=foodinsecurity`) plus frontend text, **with your approval** |
| Hardcoded frontend numbers and model descriptions | Written for earlier models | Fixable (frontend change: approval needed) |
| Questionnaire for the wrong group and partial 25010 coverage | Drafted for a DOST meeting (2026-09-23) | Fixable: new instrument |
| No 2019 FNRI regional figure | ENNS 2019 rolling sample covered 2 CALABARZON provinces; no regional estimate published | Not fixable; report it, and use 2023 regional plus 2021 provincial as the anchors |
| FIES (moderate or severe, annual) vs SWS involuntary hunger (quarterly) measure different constructs | Definitions | Face validity only: compare levels and ordering, not accuracy |
