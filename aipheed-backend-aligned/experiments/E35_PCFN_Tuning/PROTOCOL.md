# E35 protocol: hyperparameter tuning of E32-PCFN

**Status: FROZEN before any non-default configuration was scored.** The SHA-256 is in `runner/PROTOCOL_SHA256.txt`, and the freezing commit is on branch `e35-pcfn-hyperparameter-tuning`.

**Written 2026-10-15.** Before freezing, only these had been run:
- the preservation baseline;
- the pre-tuning verification (`verification/VERIFICATION.json`);
- a computability probe that listed which dates every configuration can be computed on and how many inner dates each origin has (no scores).

**Question:** does hyperparameter tuning improve E32-PCFN's real forecasting skill, beyond what validation noise can produce?

## 0. Disclosure

- **The outer dates are not unseen.** Every development date (2023-Q4 to 2026-Q3) was scored in E32 and in earlier experiments. E32's aggregate results are known to the analyst who wrote this protocol: PCFN Brier 0.1007, PCF21 0.0946, persistence 0.100, always-HIGH 0.080.
- **What the outer score can show.** The nested design keeps every selection decision blind to later outcomes. The outer score therefore estimates how the *tuning procedure* performs. It is still not unseen-period evidence.
- **The only unseen test is prospective:** 2026-Q4 and 2027-Q1 (§10).
- **This is a re-tuning.** The E32 memo said "never re-tune on 2021–2026-Q3". The researcher has now explicitly asked for this re-tuning. It is reported as such, and nothing in E32 is changed.

## 1. What E32-PCFN is (inspected in `E32_New_Model/runner/e32_lib.py::pcfn`)

**Algorithm.** PCFN is not LightGBM, and it is not a learned classifier. It is a structural probabilistic component forecaster.

**H, regional SWS hunger:**
- PCF21 local-level Kalman filter (random walk plus binomial sampling noise, n = 600 per round).
- σ_η is chosen by maximum likelihood on the grid 0.0–8.0 (step 0.1), using the definition-A rounds usable before the origin.
- **News shift.** μ_H is shifted by λ·b·(news_reg(t) − mean news_reg).
  - b is the OLS slope of the round-to-round H change on the previous quarter's log1p regional validated-news count.
  - b is 0 if there are fewer than 6 pairs.
  - **λ = 0.5 in E32.**
- **D, the provincial relative food inflation:**
  - OLS without intercept of D(t'+k) on **[D_last, Dnow, rice_rel, news_n]**, using as-of features at every past origin t' with t'+k ≤ t−1.
  - σ_D is the residual standard deviation (df = n − 4).
  - With fewer than 25 complete rows, PCF21's D_last-only model is used instead.
- **Probability:** P(HIGH) = 1 − Φ((τ − (μ_H + 2μ_D)) / √(V_H + 4σ_D²)).
- **Decision:** HIGH if P ≥ 0.5.
- **Seeds:** none. The model is deterministic.

**Target T1 (approved Chapter I label):**
- S1 = H + 2D.
- HIGH if S1(t+k) > τ(t), where τ(t) is the median S1 of the labelled quarters whose rounds were all posted before O(t).

**Origins and leads:**
- O(t) = 00:00 PHT on the first day of quarter t+1.
- Lead 1 is primary; lead 2 is secondary.

**Training:** PCFN is refitted at every origin on the history available then (walk-forward, expanding window).

**Original acceptance (E32 PROTOCOL §6):**
- A1: mean per-date Brier below PCF21's.
- A2: no worse than persistence's.
- A3: accuracy ≥ 0.75.
- A4: inference at the operational origin is verified.
- E32-PCFN failed A1 and A2.

## 2. Pre-tuning verification (done; `verification/VERIFICATION.json`, all pass)

| Check | What it verifies |
|---|---|
| V1 | S1 = mean definition-A H + 2D for every row. D = F − cross-province mean, and D, Dnow and rice_rel each sum to 0 across provinces |
| V2 | τ(t) recomputed independently at every origin; every E32 label equals S1 > τ (strict) |
| V3 | The closed-form probability equals a Monte-Carlo simulation of H + 2D for all 36 configurations |
| V4 | E32's mean per-date Brier recomputed with plain numpy; 5 rows per date |
| V5 | At all 20 origins (18 development and 2 operational), every input was released before the origin |
| V6 | Scramble-the-future test: everything not public at O(t) is replaced by noise, twice per origin. None of 7,200 probabilities (36 configurations × 5 provinces × 20 origins × 2) changes |
| V7 | The default configuration of the decomposed engine equals E32-PCFN on every E32 row |

## 3. Search space (36 configurations, fixed)

| Hyperparameter | Values | E32 value | Why it is tunable, and why this range |
|---|---|---|---|
| λ, news-shift shrinkage | 0, 0.5, 1.0 | 0.5 | E32 fixed it at ×0.5 by judgment. 0 removes the news effect on H, which tests whether news helps at all. 1.0 is the unshrunk OLS slope. |
| D regressor set | D1 = [D_last]; D2 = +Dnow; D3 = +rice_rel; D4 = +news_n | D4 | A nested sequence that adds E32's new inputs one at a time. D1 is PCF21's regressor fitted on PCFN's rows. All sets use the same complete-case training rows, so only the regressors differ. |
| c, predictive spread scale | 0.8, 1.0, 1.25 | 1.0 | The Gaussian plug-in ignores parameter uncertainty, which argues for c > 1. The filter variance may overstate the error, which argues for c < 1. Scaling σ never changes the sign of μ − τ, so **c cannot change any HIGH/LOW decision or the accuracy.** It changes only sharpness and calibration. It is not a classification threshold. |

**Not tuned, with reasons:**
- **σ_η:** already estimated by maximum likelihood at every origin.
- **n = 600:** a survey-design constant.
- **Minimum-pair rules (6, 25):** data-sufficiency guards, not skill parameters.
- **The 0.5 decision cut:** fixed by the user's rule; it is never tuned.
- **τ and the target:** the approved Chapter I label.
- **The H filter structure and the probability law:** they define the model.

**Why the grid is small.** There are 10 lead-1 dates and 4 LOW rows. A larger grid would raise the chance that the best inner score is noise (§8 measures this).

## 4. Validation design

- **Unit of evaluation: the date** (one target quarter).
  - The five provinces of a date share the regional H, so they are not independent.
  - Losses are averaged within a date first (per-date Brier), and every test resamples or flips whole dates.
  - Province-quarter rows are never split at random.
- **Primary: rolling-origin nested selection, per lead.** At each outer origin O(t):
  1. **Inner dates I(t):** development dates of the same lead whose target T' ≤ t−1 and whose definition-A rounds were all posted before O(t).
     - Each inner forecast is itself a walk-forward forecast, made at O(T'−k) with the information available then. So the selection uses only outcomes that were public at O(t).
  2. **Inner score** of a configuration: mean per-date Brier over I(t).
  3. **Minimum inner dates.** If |I(t)| < 3, the default (E32-PCFN) configuration is used.
     - Lead 1: the default is used at 2023-Q4, 2024-Q1, 2024-Q2 and 2024-Q3.
     - Lead 2: it is used at 2024-Q2, 2024-Q3, 2024-Q4 and 2025-Q1.
  4. **Selection.** Take the lowest inner score. Every configuration within **0.005** of the best (E32's tie tolerance) is tied. A tie goes, in order, to:
     - the fewest changes from E32-PCFN;
     - then fewer D regressors;
     - then c nearer 1;
     - then smaller λ.
  5. The selected configuration's forecast at O(t) is the **E35-TUNED** forecast for that date.
- **Outer dates (identical for every arm):**
  - Lead 1: 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4, 2026-Q1–Q3. That is 10 dates and 50 rows, the E32 set.
  - Lead 2: 2024-Q2–Q4, 2025-Q1, 2025-Q4, 2026-Q1–Q3. That is 8 dates and 40 rows.
- **Sensitivity analyses (reported, never used to accept):**
  - **S-LODO:** select on all *other* outer dates, including later ones. This is not temporally valid. It is a generous upper bound on what tuning could do.
  - **S-FULL:** the in-sample best configuration on all dates. This measures selection optimism and is not an estimate of skill.

## 5. Arms (identical rows)

| Arm | Notes |
|---|---|
| E35-TUNED | Nested selection (§4) |
| E32-PCFN | The original; must equal E32's `predictions.csv` |
| PCF21 | The served engine |
| B1 | Persistence, publication-aware |
| B1p | Calibrated persistence |
| CLIM | Climatology |
| ALWAYS_HIGH | Majority class |
| E32-ENS | Reported only |
| P45 | Its common rows only, read from E32's `predictions.csv` |

All recomputed arms must equal E32's stored predictions to 5e-10.

## 6. Metrics (per lead; outer dates; E28 definitions, unchanged)

- **Primary:** mean per-date Brier.
- **Also reported:**
  - accuracy (0.5 cut), balanced accuracy, precision, recall, F1;
  - ROC-AUC and PR-AUC, flagged UNSTABLE when the minority class has fewer than 5 rows or there are fewer than 8 dates;
  - log loss, calibration-in-the-large, 3-bin ECE with reliability bins, and the confusion matrix;
  - date-bootstrap 95% CIs (B = 2000, seed 20261014);
  - Brier skill score against ALWAYS_HIGH and against CLIM.

## 7. Paired tests

- **Test:** one-sided exact sign-flip test on per-date Brier differences (comparator minus E35-TUNED).
- **Comparators:** E32-PCFN, PCF21, B1 and ALWAYS_HIGH.
- **Correction:** Holm across these four.

## 8. Selection uncertainty

1. The configuration selected at every outer origin, and the number of distinct selections.
2. A date bootstrap of the S-FULL selection (B = 2000, seed 35): how often each configuration wins, and how often the default wins.
3. The number of configurations whose full-period Brier is within 0.005 of the best.
4. **Optimism:** E35-TUNED outer Brier minus the S-FULL in-sample best Brier.
5. The full-period Brier of every configuration, with its date-bootstrap CI.

## 9. Acceptance and verdict (lead 1, outer dates)

**Criteria.** E32 §6 is applied unchanged to E35-TUNED, plus one tuning criterion:

| # | Criterion |
|---|---|
| A1 | Mean per-date Brier below PCF21's |
| A2 | No worse than B1 (persistence) |
| A3 | Accuracy ≥ 0.75 |
| A4 | Inference at the operational origin O = 2026-10-01 is computable from inputs public before it (V5/V6) |
| T | Mean per-date Brier below E32-PCFN's |

**Verdict:**

| Verdict | Condition |
|---|---|
| **GENUINE IMPROVEMENT** | A1–A4 and T pass, and the Holm-adjusted p < 0.05 against E32-PCFN, PCF21 and B1 |
| **NOMINAL, WITHIN VALIDATION NOISE** | A1–A4 and T pass, but not all three adjusted p-values are < 0.05 |
| **NO IMPROVEMENT** | Otherwise |

**Production.**
- PCF21 stays served in every case.
- E35 changes no served model, frozen record or E32 artifact.
- A GENUINE verdict leads to a recommendation only. Serving needs the researcher's approval, and E32 §6 still applies (EXPERIMENTAL until prospective validation).
- Beating ALWAYS_HIGH is reported but not required (E32 did not require it). A model that does not beat it has shown no skill beyond the base rate, and the report says so.

## 10. Prospective record (unseen test)

- **What is frozen.** The configuration that the nested rule selects at the operational origin O(2026-Q3) = 2026-10-01 is frozen, whatever the verdict, as a **research arm** in `E35_PCFN_Tuning/frozen/`:
  - lead 1 targets 2026-Q4 and lead 2 targets 2027-Q1;
  - the inner dates are those posted before 2026-10-01, so the 2026-Q3 label (posted 2026-10-14) is excluded.
- **If it equals the default,** the E32 frozen PCFN prediction is the record, and E35 freezes the same numbers with a pointer to it.
- **Not used for scoring now.** No 2026-Q4 or 2027-Q1 outcome exists or is used. The E32 frozen record is never altered.

## 11. Integrity

- **Prohibited:**
  - tuning the 0.5 cut;
  - changing the target or τ;
  - using data after the authorized limit or before 2021;
  - selecting on prospective outcomes.
- **Reproducibility:**
  - the run is repeated and must be byte-identical;
  - preserved artifacts are re-hashed after the run (`runner/e35_preserve.py check`).
- **Records:**
  - every configuration and result is written with the dataset SHA-256s, the seeds and the protocol SHA-256;
  - any deviation goes to `DEVIATIONS.md`.

## 12. Power (stated before the run)

- With 10 dates, the smallest attainable one-sided sign-flip p is 1/1024.
- E34 estimated that about 62 dates are needed to detect a 0.02 Brier gain.
- There are 4 LOW rows in 50, so AUC, precision on LOW and the reliability bins are unstable.
- A gain of the size E32 saw between arms (≈ 0.005) cannot be told apart from noise with these data.
