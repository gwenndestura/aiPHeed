# ALLBASE, Phase A: root-cause and experiment audit for "C-b must beat all baselines at both leads"

**Written:** 2026-11-03. Read only: no model trained, nothing committed.

**Numbers:** `runner/phase_a.py` → `out/phase_a.json`, computed from the stored C-b forecasts (NEWS_V2), the stored
comparators (IMPROVE_V2, OBJECTIVES_COMPLETION, IMPROVE_V2_LEADS) and the BL labels. Development evidence (62 labelled
quarters, 2010-Q1..2026-Q3).

## 1. Verified C-b specification

The implementation matches the brief:
- **21 inputs** (`NEWS_V2/runner/run_news_v2.py` `MODELS["C-b"]`):
  - hunger history 5 (`h_last`, `h_change`, `h_mean4`, `true_h`, `pi_H4L`);
  - local prices 4 (`R_food_yoy`, `R_head_yoy`, `R_rice_yoy`, `R_food_mom`);
  - world prices 5 (`W_rice_yoy`, `W_rice_mom`, `W_cereal_yoy`, `W_crude_yoy`, `W_urea_yoy`);
  - climate 3 (`ONI_last`, `ONI_max12`, `tc_mean`);
  - supply 2 (`R_C3`, `R_C4`);
  - NLP 1 (`z_N1R`);
  - `lead`.
- LightGBM with IMPROVE_V2's fixed 8-setting grid, chronological inner selection, seed and walk-forward refits from
  1998-Q3.
- One model on stacked leads 1–15 (not one model per lead).

## 2. Baseline audit (what C-b is compared with)

| Comparator | Definition (verified) | Inputs | Fit |
|---|---|---|---|
| Naive persistence | 1 if the newest BL reading > 11.3 | Latest reading | — |
| **PSA-only logistic** | L2 logistic (C = 1), training-median imputation, standardization | `R_food_yoy`, `R_head_yoy`, `R_rice_yoy`, `R_food_mom`, `R_C3`, `R_C4`, `E1`, `R_A3`: **no SWS hunger history** | One model per lead, walk-forward |
| **Combined logistic (LOGIT)** | The same specification on F_b(T2), i.e. the REF columns **including hunger history** | 19 | One model per lead |
| NLP-only logistic | The same on the 8 news columns, 2021+ only | News | News era only (20 / 19 quarters) |
| LightGBM government-only | REF settings, official indicators **without** SWS hunger | 14 | Stacked |
| LightGBM NLP-only | REF settings on the 8 news columns | News | News era only |
| Always-HIGH | 1 | — | — |

**Test.**
- Paired Brier difference per quarter, one-sided cluster bootstrap (seed 2036, 5000 draws), on the same quarters.
- Holm correction was applied within **two families**: Objective 4 (5 comparators: persistence, PSA-only, NLP-only,
  LOGIT, always-HIGH) and H3 (6: persistence, NLP-only, PSA-only, LOGIT, LightGBM government-only, LightGBM NLP-only).
- **The brief's single family of 7 differs** from what was run before. Choosing the family is a Phase B decision that
  must be fixed before any new result (§6).

**The comparators are not all weak.**

| Lead 1 | Accuracy | AUC | Brier | ECE (calibration error) |
|---|---|---|---|---|
| **C-b** | **0.790** | 0.702 | **0.187** | 0.169 |
| LOGIT (combined) | 0.710 | **0.759** | 0.193 | **0.130** |
| PSA-only logistic | 0.726 | 0.633 | 0.208 | 0.147 |
| LightGBM government-only | 0.677 | 0.535 | 0.233 | 0.160 |
| Persistence | 0.661 | 0.594 | 0.339 | 0.339 |

At Lead 2: C-b 0.790 / AUC 0.704 / Brier 0.184; LOGIT 0.661 / 0.670 / 0.234; PSA-only 0.677 / 0.579 / 0.239.

**At Lead 1 the combined logistic regression ranks quarters better than C-b** (AUC 0.759 vs 0.702) and is better
calibrated. C-b is more accurate at the 0.50 cut and slightly better on Brier.

## 3. Root causes

### A. Label quality and the noise ceiling (T1 vs T2)

With SWS's ±5.7-point margin (one SE = 2.908 / √rounds), the **noise ceiling** is the expected accuracy, against the
published labels, of a forecaster that knew **true** hunger exactly:

| Period | Noise ceiling | C-b | Persistence | C-b gives persistence's call |
|---|---|---|---|---|
| All 62 quarters | **0.849** | 0.790 | 0.661 | 77% |
| 2010-Q1..2015-Q1 | 0.931 | 0.952 | 0.905 | 95% |
| **2015-Q2..2020-Q4** | **0.773** | **0.571** | 0.429 | 57% |
| 2021-Q2..2026-Q3 | 0.842 | 0.850 | 0.650 | 80% |

**The noise-floor Brier** (the expected score of that perfect-knowledge forecaster) is **0.103**.

**Correction to earlier wording.** RELIABLE_NEWINFO said the 2015–2020 failure "looks like survey noise". The ceiling
refines that.
- **Noise explains part of it:** even perfect knowledge of true hunger would score only about 0.77 there, against about
  0.93 in 2010–2015.
- **It does not explain all of it:** C-b is about 20 points below the ceiling there, and R7 needs only 0.60.

The rest is genuine unpredictability of quarter-to-quarter movements of true hunger, which no input tried has captured.
Of C-b's 13 Lead-1 errors, 10 are quarters where it gave persistence's call. Its main failure is following the last
reading through reversals.

### B. Hunger-history dominance

- Hunger history carries 64.7% of SHAP; C-b gives persistence's call in 77% of quarters.
- It is still far better than persistence (0.790 vs 0.661; Brier −0.151, Holm p 0.001), because it does not follow
  persistence where world prices and hunger levels argue otherwise.
- The dominance is legitimate: past hunger is the best available predictor. Reducing it artificially would worsen
  every metric.

### C. Why the logistic regressions cannot be beaten significantly (power)

Paired Brier difference, C-b minus comparator, observed:

| Comparator | Lead | Mean diff | SD per quarter | z | Quarters needed (raw α 0.05) | Needed (Holm strictest, 0.05/6) |
|---|---|---|---|---|---|---|
| LOGIT | 1 | −0.005 | 0.284 | 0.15 | **7,540** | **15,972** |
| PSA-only | 1 | −0.021 | 0.248 | 0.66 | 385 | 814 |
| LOGIT | 2 | −0.050 | 0.278 | 1.43 | 83 | 175 |
| PSA-only | 2 | −0.055 | 0.247 | 1.76 | 55 | 115 |
| LightGBM NLP-only | 2 | −0.103 | 0.234 | 1.92 | 14 | 30 (news era has 19) |
| Persistence, NLP-only logistic, LightGBM government-only, always-HIGH | 1–2 | −0.05 to −0.23 | — | 2.3–3.2 | 8–29 | 17–60 (already met) |

**What it would take with 62 quarters.** To reach Holm's strictest step, a candidate would need a Brier gain of about
**0.086 over LOGIT at Lead 1**, i.e. a Brier of about **0.107**. The noise floor is **0.103**.
- **In plain words:** to beat the combined logistic regression significantly at Lead 1, a model would have to forecast
  almost as well as a model that knew the true hunger level exactly.
- **This is not achievable with the available data,** short of a predictor that anticipates true hunger
  quarter-to-quarter far better than anything tried.
- **Lead 2 is less extreme:** a gain of about 0.085 over LOGIT, i.e. a Brier of about 0.149, still well below C-b's
  0.184.

### D. News and NLP

Already established (`../PHASE2_INVESTIGATION.md` §5, `../NEWS_V2/RESULTS.md`):
- news exists only from 2021, and the FSSI anomaly from 2023-Q2;
- about 90% of training rows have no news;
- C-b's news input changed 0 of 62 calls;
- every construction that let news carry weight lost accuracy;
- **a valid result:** NLP adds no measurable predictive value at quarterly frequency with this history.

LightGBM NLP-only is unbeaten at Lead 2 only because the news era has 19 quarters (needs about 30).

## 4. Experiments already attempted (do not repeat without a methodological correction)

| Experiment | What changed | Result |
|---|---|---|
| E99 (paper pipeline) | Eq. 3 label, 12 features, Optuna | Lead 1 0.30; MRLT 0 |
| P0H4 (`ch1`) | Hunger and price hybrid, province level | Lead 1 R1–R7 pass; Lead 2 fails |
| HISTORY_RETRAIN | T1/T2 targets, feature options (b)/(c) incl. `E1`, GRU, LOGIT | REF chosen |
| IMPROVE_V2 | Arms REF, I1 (pooled areas), I2 (regression), I3 (Platt calibration), ALL; ± news | REF best; news no gain |
| IMPROVE_V2_LEADS / OPTION_1 | Leads 1–15; REF+news | MRLT 2 |
| RELIABLE_L12 | Per-origin threshold (C1 REF, C2 REF+news) | 0 calls changed |
| RELIABLE_NEWINFO | 0.5 REF + 0.5 `pi_H4L` blend; REF + CHIRPS rainfall | Blend worse; rainfall 0 calls changed |
| OLD_NEWS | REF + GDELT 2015–2026 | Fails R5, R7; 1 call changed for the worse |
| NEWS_V2 | C-a (8 anomalies), **C-b** (FSSI anomaly) | C-b = REF in effect; adopted |
| NOISE_W | C-b + measurement-error weights (T2-style) | 0 calls changed; Brier −0.007 (n.s.) |
| E13–E114, FINAL_*, LEAD2_* | Earlier targets (S1, FIRI, price conditions) and models | Documented in each folder |

**Already covered from the brief's list (Part 5):** class weighting (in the grid), calibration (I3 Platt), regression
on the level (I2), sampling-error-aware training (NOISE_W), news anomalies and a single news feature (NEWS_V2), and
the news-era split (Phase 2).

## 5. Opportunities that remain (for Phase B; none can be promised to succeed)

| # | Candidate | Weakness addressed | Why it is genuinely new | Expected limit |
|---|---|---|---|---|
| O1 | **A combined logistic + C-b average** (fixed 50/50 or a weight chosen walk-forward on past forecasts only) | LOGIT ranks better (AUC 0.759), C-b classifies better: the errors may partly offset | No ensemble of LightGBM and logistic was tried | Gains are likely about 0.01 in Brier, far below the 0.086 needed for significance at Lead 1 |
| O2 | **Per-lead regularized logistic with C-b's inputs** (as the comparator, but tuned on C chronologically) | Simple models win at small n | Only the fixed C = 1 version exists | It would be "beating LOGIT with LOGIT"; same power limit |
| O3 | **Isotonic or Platt calibration of C-b** fitted walk-forward | C-b's ECE 0.169 is worse than LOGIT's 0.130 | Platt was tried on REF (I3), not on C-b | Calibration cannot raise AUC; small Brier gain |
| O4 | **Change-point or "reversal" features** (e.g. the sign of the last two hunger changes, distance of the reading to the line in SE units) | C-b follows persistence through reversals | Not tried as inputs | Reversals in 2015–2020 alternate quarter to quarter; may fit noise |
| O5 | **Prospective comparison** | All power limits | Adds the logistic regressions to the sealed 2027+ forecasts | Answer only after 2028+ (about 40+ quarters for real power) |

## 6. Bottom line for Phase B

1. **All seven baselines at both leads, significant after Holm at p < 0.05, is not achievable with 62 development
   quarters unless a model approaches the noise floor.** At Lead 1 that would require Brier ≈ 0.107 against a floor
   of 0.103, while the best model to date is 0.187.
2. **R7** can in principle be met (the 2015–2020 ceiling is 0.77 > 0.60), but every input tried has failed to
   anticipate the reversals. O4 is the only untried idea aimed directly at it.
3. **AUC ≥ 0.80** has not been reached by any model; LOGIT is the closest (0.759, Lead 1).
4. **Decisions needed before any training (Phase B):**
   - the Holm family (the brief's single family of 7, or the existing two families), fixed in advance;
   - which of O1–O4 to pre-register (I recommend at most two, e.g. O1 and O4);
   - whether to add the logistic regressions to the sealed prospective forecasts (O5), which is the only honest route
     to a significant all-baseline result.
