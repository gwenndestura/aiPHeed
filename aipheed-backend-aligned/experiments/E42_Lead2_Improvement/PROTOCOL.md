# E42 protocol: untested Lead-2 hypotheses, five-trigger and NLP tests (frozen before any E42 score)

**Written:** 2026-10-15 on branch `e42-lead2-improvement` (cut from `e41-lead2-audit` @ a0c3c70).
**Freeze:** the SHA-256 of this file (LF) is in `runner/PROTOCOL_SHA256.txt` and is committed before any E42 model is fitted or scored. `runner/e42_evaluate.py` refuses to run if this file changed.
**Run rule:** run once, then a byte-identical repeat. No setting changes after results. Deviations go to `DEVIATIONS.md`.

## 0. What is already known, and the evidence status

**Phase 1:**
- E41 was reproduced byte-identically: `runs/e41_repro_20261015T130306Z`.
- E41 results: Lead-2 FPP M1 0.632 and M1z 0.716 on 19 quarters; lead-1 M1 0.842.
- Served E38: 0.709 on v1.

**Phase 2** (`runs/audit/audit.json`; no model fitted):
- v1 is HIGH in 83% of rows when regional hunger is above its 2021–22 median, against 24% otherwise.
- 50% of v1 HIGH rows have food inflation below 4%.
- v1 agrees with FPP on 50% of rows and with E40 on 39%.
- **E40** is HIGH in 5 of 95 rows overall, 0 in 2026, and identical across the five provinces in 16 of 19 quarters. The lagged regional H alone gives AUC 0.945 for it at lead 2.
- **Evidence status:** every quarter from 2021 to 2026-Q3 has been examined by earlier experiments. The E40 holdout (2025-Q4..2026-Q3) is **exposed** (E41 C-1). E42 is therefore development evidence. No E42 result is called independent confirmation. The independent test is prospective (§7).
- I know E41's per-arm results, including that M1z beat M1. This is why §3 tests a **selection procedure that only uses past performance at each origin**, rather than adopting M1z after the fact.

## 1. Targets

| ID | Target | Use |
|---|---|---|
| T-P | `FPP = 1[provincial food YoY > 4.0]` (E39/E41) | primary price-pressure outcome |
| T-H | regional SWS H (continuous) | hunger layer (regional only) |
| T-E40 | E40 frozen label | Chapter I-consistent SWS + CPI label; reported, with exposure flags |
| T-v1 | served relative label | served-model reproduction only (no new model) |

Timing is identical to E41 (PROTOCOL §3 there):
- the origin O(t) is the first day of t+1;
- Lead 2 = target t+2;
- CPI up to month 2 of t;
- SWS posted before O(t);
- production and LFS up to t−1;
- news up to quarter t.

**FSSI-v2** (E31 store) for quarter t is allowed at O(t). Its bias weight uses only the same quarter's cross-province article counts.

## 2. Features and trigger groups (E41 §5, plus the NLP block and the M1z projection)

| Group | Features |
|---|---|
| market | F_last, F_now, HL_now, gap_now, mom3, F_hat_M1, F_hat_M1z, D_now |
| hunger_sws | H_last, H_chg, H_age |
| climate_supply | palay_yoy, corn_yoy |
| fish_supply | fish_yoy, aqua_yoy |
| employment | ur_last, ur_yoy, under_last |
| ofw_remittance | none: no official in-window regional or provincial series exists (Phase 2 search) |
| news (NLP) | news_n, five trigger shares, fssi_v2, fssi_admitted, fssi_sufficient |

- **GOV** = market + hunger_sws + climate_supply + fish_supply + employment.
- **NLP** = news.
- **COMB** = GOV + NLP.

## 3. Candidates for T-P at Lead 2 (all fixed now)

**E41 arms** (recomputed with the E41 library):
- B0 majority;
- B1 persistence;
- B2 latest month;
- B3 seasonal;
- M1 (drift);
- M1z (flat).

**New:**
- **M1h:** M1 with half the trailing drift.
- **PS (primary E42 procedure):** prequential selection plus recalibration.
  - At each origin, choose among {M1, M1z, M1h} the arm with the lowest mean per-date Brier over the target quarters whose outcomes were published before the origin.
  - At least 4 such dates are required; otherwise use M1, E41's primary. Ties go to M1.
  - Then apply walk-forward Platt recalibration: a logistic regression (C = 1.0) of outcome on logit(p) over the chosen arm's earlier out-of-sample predictions (the arm's own history, not the selector's).
  - Platt needs at least 8 prior dates and both classes; otherwise the raw p is used.
  - The decision is p ≥ 0.5.
- **LR-GOV, LR-NLP, LR-COMB** (Chapter I baselines: PSA-only, NLP-only, logistic regression):
  - L2, C = 0.5, standardized;
  - missing values imputed with the training median, plus a missing indicator for every feature that has any missing value in training.
- **LGBM-GOV, LGBM-NLP, LGBM-COMB** (Chapter I: LightGBM with all available triggers):
  - num_leaves 4, max_depth 2, min_child_samples 10, n_estimators 100, learning_rate 0.05, reg_lambda 5.0, seed 42, deterministic, one thread;
  - NaN is passed through.
- **Withholding:** ML arms are trained on pairs `(X(t'), FPP(t'+2))` with `t'+2 ≤ t−1`, and are withheld when there are fewer than 8 distinct training target quarters or only one class (as E41).

**Evaluation sets:**
- **S-P:** targets 2022-Q1..2026-Q3, for B0–B3, M1, M1z, M1h and PS (expected 19 dates).
- **S-C:** targets where every candidate forecasts (expected 2024-Q3..2026-Q3). All grid comparisons, including GOV vs NLP vs COMB, are on S-C.

## 4. Trigger and NLP tests (S-C, secondary; nothing is chosen from them)

1. **Single-group** LR and LGBM: each group alone.
2. **Leave-one-group-out** from COMB (LR and LGBM).
3. **Grouped permutation importance:** the mean Brier increase over 200 permutations of a group's columns, within the test rows, for LR-COMB and LGBM-COMB.
4. **Grouped SHAP** of LGBM-COMB at each origin.
5. **Missing-data sensitivity:** for each group, set its features to missing at prediction time and report the mean change in p. A large systematic drop means "missing reads as low risk".
6. **Stale-data sensitivity:** metrics on the rows whose SWS input is more than one quarter old, versus the rest.
7. **Redundancy:** pairs with |r| ≥ 0.8 on training rows; the variance inflation of the GOV block.
8. **NLP value:** per-date paired Brier of LR-COMB vs LR-GOV and LGBM-COMB vs LGBM-GOV.

## 5. Other targets

| Target | What is reported |
|---|---|
| T-H, Lead 2 | MAE of H-persistence, H-mean and a ridge regression (α = 1.0) of H(t'+2) on [H_last, F_now, ur_last], fitted on pairs posted before the origin (at least 8) |
| T-E40, Lead 2 | E41's component simulation SIM over every target with a label (2023-Q2..2026-Q3), against persistence and always-LOW. E40's own sealed holdout forecasts (issued 09:30:46Z, before C-1) are scored on 2025-Q4..2026-Q3, flagged "scored after exposure; forecasts sealed before it". |
| T-v1 | E38 reproduction numbers (E41) quoted; no new model |

## 6. Gates for PS on S-P

| Gate | Rule |
|---|---|
| G0 | leakage, alignment and label tests pass (`tests/`) |
| G1 | accuracy ≥ 0.75 |
| G2 | balanced accuracy ≥ 0.70, and HIGH and LOW recall ≥ 0.60 |
| G3 | (a) accuracy and Brier better than each of B0–B3; (b) the Brier gain over persistence has Holm p < 0.05 |
| G4 | the 95% CI of calibration-in-the-large contains 0, **and** the calibration slope is between 0.7 and 1.3 |
| G5 (improvement over E41) | the per-date Brier gain of PS over M1 is > 0 with one-sided p < 0.05 |

**Classification** (the prompt's four categories):
- G0–G4 pass → "Suitable for exploratory decision-support testing". There is no "validated" without prospective outcomes.
- G0 and G3 pass, others fail → "Requires further model development (usable for a controlled system demonstration as experimental)".
- G3 fails → "Insufficient evidence to support Lead-2 operational use".

"Improved over E41" is claimed only if G5 passes.

## 7. Prospective freeze

- From O = 2026-10-01: PS (and every S-P arm) for 2027-Q1 (lead 2) and 2026-Q4 (lead 1), plus SIM for E40 2027-Q1.
- These go to `frozen/E42_PROSPECTIVE_2027Q1.json` with a sha256.
- The procedure for the 2027-01-01 origin is this protocol unchanged.

## 8. Outputs for DA (documented rules, not tuned)

- **Bands:** Low (P < 0.33), Watch, High (P ≥ 0.67), as in E41.
- **Exploratory food-stress signal count (0–2):** price pressure High band, plus the latest approved regional H above 11.3. Each component is shown with its status. No weights; it is not a validated index.
- **Trigger status per group:**
  - `contributes`: has model input and non-zero attribution;
  - `no_model_input`;
  - `no_data`: no official series.
  - The dashboard text is built from the status, never from a fixed direction.
- **Municipal:** relative rankings only (Chapter I Objective 3: province forecast weighted by PSA poverty and density). No municipal probability.
- **Default serving:** stays E38 unless the user decides otherwise.
