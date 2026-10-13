# E23 Protocol (frozen before any E23 comparison was run)

**Requirement basis:** Chapter I only (`CHAPTER_I_EXTRACTION_AND_TRACEABILITY.md`).
**Freeze:** the SHA-256 of this file, `runner/e23_lib.py` and `runner/run_e23.py` are in `runner/PROTOCOL_SHA256.txt` (computed by script). The runner stops if any of them changes.

**Not blind.** Every 2021–2025 quarter, and the 2026-Q1/Q2 values, were examined in E9–E18. The primary threshold rule below (training-window median) was also seen in an earlier study (E8 "C1", 70.9% accuracy under different settings). These results are therefore **development evidence, not an untouched test**. The only untouched outcomes are 2026-Q3 onward, which stay protected.

## 1. Primary target (Chapter I, Section 1.2 and 1.4)

Chapter I defines the dependent variable as "the binary food insecurity risk classification, either high or low, of a CALABARZON province in a given quarter", built from "a composite food stress label combining SWS (Social Weather Stations) quarterly hunger data and PSA province-level food CPI deviation". Chapter I gives **no formula weights and no threshold.** The implemented formula is used unchanged:

- `S1(p,q) = H(q) + 2 × D(p,q)`
- `H(q)` = mean of the production-series SWS Balance Luzon rounds of quarter q (one regional value per quarter).
- `D(p,q) = F(p,q) − mean of F over the five provinces`, where F is the quarterly mean of monthly provincial food-CPI year-on-year inflation; D only when all five provinces are present.
- Quarters with no production round (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) have **no label**; nothing is imputed.

**Threshold (primary, training-window only).** At each forecast origin O, τ(O) = the median of S1 over every province-quarter label **published before O**. Training labels, test labels and persistence all use τ(O). No test-period value enters τ.

**Sensitivity (reported, never used for decisions):** the implemented fixed threshold 14.6 (it was computed over the full period, so it carries test-period information).

## 2. Timing (strict publication availability)

| Item | Rule |
|---|---|
| Forecast origin for feature quarter t | O(t) = 00:00 PHT on the first day of quarter t+1 |
| News features (9) | Articles of quarter t (FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel, five trigger shares) |
| Government features (36) | Quarter t−1 values (the 45 governing candidates minus 9 news minus poverty_incidence, plus cpi_dev). `poverty_incidence` is excluded: its stored values do not follow PSA release dates (E17). |
| SWS hunger feature (1) | Mean of the production rounds of the latest fieldwork quarter **published before O(t)** (verified per-round dates) |
| Target | Label of quarter t+k (lead k = 1…8) |
| Training pairs | Any lead-k pair (t′, t′+k) with t′ ≥ 2021-Q1 whose label is **published before O(t)**: label quarter ≤ t−1 **and** every production SWS round of that quarter published before O(t). |
| Minimum training | ≥ 8 distinct labelled training target quarters; otherwise that origin is skipped |
| Feature range | News and government features are eligible only through 2025-Q4. 2026 news is not authorized. |
| Test targets | Every labelled quarter t+k with t ≤ 2025-Q4, **including 2026-Q1/Q2 labels** (authorized Jan–Jun 2026; previously viewed). Sensitivity: 2026 targets excluded. |

## 3. Models (all on identical origins, rows, labels and metric code)

| ID | Model | Features | Tuning |
|---|---|---|---|
| **PROPOSED** | LightGBM, news + government | 46 (9 news + 36 government + SWS) | Nested (below) |
| B1 | Naive persistence | Province's latest published label at O | None |
| B2 | Logistic regression, combined | 46 | None (C = 1) |
| B3 | Logistic regression, government only | 37 (36 government + SWS) | None |
| B4 | Logistic regression, news only | 9 | None |
| B5 | LightGBM, government only | 37 | Nested, same grid as PROPOSED |
| B6 | LightGBM, news only | 9 | Nested, same grid as PROPOSED |
| S_lr_psa_only | Logistic regression, the 20 PSA series | 20 | None. **Objective 4-II literal reading, descriptive only** |
| ABL_no_FSSI, ABL_no_cpi_dev | PROPOSED refit without that feature, same selected configuration | 45 | — (H1 ablation) |

**Objective 4 → H3 mapping:** I naive persistence → B1; II PSA-only indicator → B3 (government indicators; the literal 20-series PSA variant is reported beside it); III NLP-only sentiment → B4; IV logistic regression → B2. B5 and B6 come from SOP Q3/H3 only.

**Logistic regression:** training-median imputation and standardization, C = 1.0, threshold 0.5. Single-class training gives a constant prediction.

**LightGBM (PROPOSED, B5, B6): fixed settings** learning_rate 0.05, max_depth 3, reg_lambda 1.0, colsample_bytree 0.8, no bagging, scale_pos_weight = (1−p)/p from the training rows, random_state 42, deterministic. **Search space (16 configurations, the only ones tried):**

- mode ∈ {single-lead, pooled multi-lead (all leads 1–8 published pairs, with `lead` as a feature)}
- (num_leaves, min_child_samples) ∈ {(3,5), (3,10), (7,5), (7,10)}
- n_estimators ∈ {50, 150}

**Nested chronological selection (training rows only):** validation targets = the last 3 distinct target quarters among the lead-k training pairs. For validation target v, inner training rows = pairs whose target quarter ≤ v − k − 1. Score = mean log loss. Lowest wins; ties go to the earlier grid entry; if no inner fold is usable, the first grid entry is used. **No outer-test outcome is used for any choice.** No probability calibration (too few rows); stated as a limitation.

Columns constant or entirely missing in the training rows are dropped in that fold (no effect on any model).

## 4. Evaluation

**Expanding window:** every feasible origin 2021-Q1…2025-Q4 at every lead 1–8.

**Evaluable lead:** ≥ 8 origins **and** ≥ 5 HIGH **and** ≥ 5 LOW pooled test rows. Otherwise "not evaluable" (metrics still listed, no decisions drawn).

**Metrics (pooled over origins, per lead):**

- Primary: ROC-AUC.
- Secondary: Brier score.
- Also: accuracy, precision, recall, F1 (HIGH class, threshold 0.5), specificity, confusion matrix, class counts, per-origin Brier and accuracy, and training-window class counts.

**Paired comparisons (PROPOSED vs each baseline, identical rows):**

- Brier: exact one-sided sign-flip test on per-origin mean Brier differences.
- AUC: paired permutation that swaps the two models' scores within whole origins. All 2^n assignments when n ≤ 16; otherwise 50,000 seeded draws.
- Holm adjustment across the six baselines.
- Effect sizes: the mean Brier difference and the AUC difference; origins better/worse/tied; leave-one-origin-out range of the AUC difference.
- **Province rows from one quarter are not independent; every test resamples whole origins.**

**Reliability rule (Objective 2-V, H2).** Chapter I defines no criterion; this one is researcher-declared and needs adviser approval. Lead k is **reliable** iff:

1. it is evaluable;
2. PROPOSED's pooled AUC origin-cluster bootstrap 95% lower bound > 0.5 (4,000 resamples, seed 20261013); **and**
3. PROPOSED's Brier is lower than naive persistence's, with one-sided sign-flip p < 0.05 after Holm across the evaluable leads.

**Maximum reliable lead time** = the largest reliable k, or "none".

## 5. Null-hypothesis decision rules (decided before running)

| H | Rejected iff | Not testable iff |
|---|---|---|
| **H1** | At the primary lead (k = 1 if evaluable, else the smallest evaluable lead), **both** `FSSI` and `cpi_dev` (the "food CPI deviation" feature): (a) rank in the top 5 of mean \|SHAP\| pooled across origins; (b) are in the top 5 in ≥ 50% of origins; (c) have permutation importance (pooled test rows, 200 permutations) with ΔBrier origin-cluster bootstrap 95% lower bound > 0. Drop-column ablation is reported. | No evaluable lead |
| **H2** | ≥ 2 leads are reliable (Section 4) | Fewer than 2 evaluable leads |
| **H3** | At the primary lead, PROPOSED beats **every one** of the six baselines: Holm-adjusted one-sided AUC p < 0.05 **and** a lower mean Brier | No evaluable lead |
| **H4, H5** | Participant rules in `instruments/DECISION_RULES.md` | Until genuine DA Region IV-A responses exist |

**SHAP:** LightGBM TreeSHAP (`pred_contrib`) of each origin's PROPOSED model on its test rows. The tree statistics come from that origin's training rows only, so the background is training-only.

**Leave-one-quarter-out:** lead 1, global median threshold, first grid configuration. **Non-chronological; descriptive only.**

## 6. Integrity

- Data reads only through the E23 guard; its allowlist is imported from the E17/E18 guards and every file is hash-verified before reading.
- Predictions are written and SHA-256-sealed **before** scoring; scoring re-reads the sealed file.
- Seeds are fixed.
- A crash caused by a coding error (not by results) may be fixed once. Any such fix is recorded in `PROTOCOL_AMENDMENTS.md` with the reason and new hashes, before results are read.
