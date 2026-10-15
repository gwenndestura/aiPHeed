# E35: does hyperparameter tuning improve E32-PCFN's forecasting skill?

**Date:** 2026-10-15.
**Branch:** `e35-pcfn-hyperparameter-tuning` (from `e34-main-app-integration`; nothing pushed).
**Folder:** `aipheed-backend-aligned/experiments/E35_PCFN_Tuning/`.

**Read first:**
- `PROTOCOL.md` (frozen: sha `4af6492a…`, git `37dc255`, before any tuned score);
- `DEVIATIONS.md`;
- `runs/20261015T005446Z/RESULTS_TABLE.md` (the complete table).

## 1. Answer

**No.** Tuning does not produce a defensible improvement. The verdict under the frozen rule is **NO IMPROVEMENT**.

**Lead 1, 10 development dates, 50 rows (46 HIGH / 4 LOW), mean per-date Brier:**

| Arm | Brier | Accuracy |
|---|---|---|
| Always-HIGH | **0.0800** | 0.92 |
| PCF21 (served) | 0.0946 | 0.88 |
| **E35-TUNED (nested)** | **0.0966** | 0.86 |
| Persistence | 0.1000 | 0.90 |
| E32-PCFN (original) | 0.1007 | 0.86 |

**Acceptance (E32 §6 criteria, applied to E35-TUNED):**

| Criterion | Result |
|---|---|
| A1: Brier below PCF21 | **Fails** (0.0966 vs 0.0946) |
| A2: no worse than persistence | Passes, by 0.003 |
| A3: accuracy ≥ 0.75 | Passes (0.86; the same accuracy as before tuning) |
| T: Brier below E32-PCFN | Passes, by 0.004 (one-sided p = 0.11, Holm 0.44) |

**Decisions:**
- PCF21 remains the served model.
- E32-PCFN and its frozen prospective record are unchanged: all 97 preserved files were re-hashed and match.
- **Validation noise against real gain.** The 0.004 gain over the original is the size of difference these 10 dates cannot separate from noise. The in-sample tuned score (0.078), which would appear to beat always-HIGH, is selection optimism: the nested estimate is 0.019 worse.

## 2. What was tuned (inspection of `E32_New_Model/runner/e32_lib.py`)

**E32-PCFN is not LightGBM.** It is a structural forecaster:
- a Kalman local-level filter on SWS hunger, with σ_η estimated by maximum likelihood, shifted by λ × the news-volume slope;
- an OLS model (no intercept) for the provincial food-inflation differential D on [D_last, Dnow, rice_rel, news_n];
- a Gaussian probability that S1 = H + 2D exceeds τ.

It has no random seed and no learned trees. Its free choices are:

| Hyperparameter | Grid | E32 value |
|---|---|---|
| λ (news-shift shrinkage) | 0, 0.5, 1 | 0.5 |
| D regressor set | D1 [D_last] … D4 [+Dnow, +rice_rel, +news_n] | D4 |
| c (predictive spread scale) | 0.8, 1, 1.25 | 1 |

- **Grid size:** 36 configurations, fixed before fitting.
- **c is not a threshold.** It never changes a HIGH/LOW decision (tested), so it cannot buy accuracy; it changes calibration only.
- **Not tuned:**
  - the 0.5 cut;
  - τ and the target;
  - σ_η (already maximum likelihood);
  - the data-sufficiency rules.

**Default reproduction.** The default configuration reproduces E32-PCFN on all 90 E32 rows (to 5e-11, the CSV precision). The engine was decomposed, not rewritten.

## 3. Verification before tuning (`verification/VERIFICATION.json`: 7/7 pass)

- **Target formula:**
  - S1 = mean definition-A H + 2D reproduces every label row;
  - D, Dnow and rice_rel are centred across the five provinces;
  - τ was recomputed independently at all 20 origins;
  - all 90 E32 labels equal S1 > τ.
- **Probability law:** the closed form matches a 400,000-draw Monte-Carlo simulation for all 36 configurations (largest error 0.002).
- **Scoring:** Brier arithmetic was recomputed independently.
- **Publication timing:**
  - every round, D, Dnow, rice, news and training label used at an origin was public before it;
  - **scramble-the-future:** replacing everything unpublished at O(t) with noise changes **0 of 7,200** probabilities across all configurations.

## 4. Design (PROTOCOL §4)

- **Unit:** the date, not the province-quarter row. The five provinces share one regional hunger value per date, so losses are averaged per date, and every resample or sign flip moves whole dates.
- **Primary: rolling-origin nested selection.**
  - At each outer origin, a configuration is chosen only on earlier walk-forward forecasts whose outcomes were *posted before that origin*.
  - With fewer than 3 such dates, the E32 default is kept. That happens for the first 4 of 10 dates at lead 1 and 4 of 8 at lead 2.
  - Ties within 0.005 Brier go to the configuration closest to E32-PCFN.
- **Sensitivity (never used to accept):**
  - **S-LODO** selects on all other dates, including later ones. It is not temporally valid.
  - **S-FULL** is the in-sample best.

## 5. Results

### Lead 1 (primary)

| Arm | Brier | 95% CI (dates) | BSS vs always-HIGH | Accuracy | Balanced accuracy | F1 | ROC-AUC* | Calibration-in-the-large | 3-bin ECE |
|---|---|---|---|---|---|---|---|---|---|
| **E35-TUNED** | 0.0966 | 0.048–0.148 | −0.21 | 0.86 | 0.70 | 0.92 | 0.750 | −0.134 | 0.134 |
| E32-PCFN | 0.1007 | 0.054–0.148 | −0.26 | 0.86 | 0.70 | 0.92 | 0.755 | −0.159 | 0.159 |
| PCF21 | 0.0946 | 0.054–0.136 | −0.18 | 0.88 | 0.71 | 0.93 | 0.761 | −0.165 | 0.165 |
| Persistence (B1) | 0.1000 | 0.040–0.160 | −0.25 | 0.90 | 0.83 | 0.94 | 0.832 | −0.060 | 0.100 |
| Calibrated persistence | 0.0956 | 0.051–0.144 | −0.20 | 0.90 | 0.83 | 0.94 | 0.769 | −0.175 | 0.175 |
| Always-HIGH | 0.0800 | 0.020–0.140 | 0 | 0.92 | 0.50 | 0.96 | 0.500 | +0.080 | 0.080 |
| Climatology | 0.2208 | 0.175–0.271 | −1.76 | 0.60 | 0.55 | 0.74 | 0.568 | −0.375 | 0.375 |
| E32-ENS | 0.0931 | 0.051–0.139 | −0.16 | 0.92 | 0.84 | 0.96 | 0.755 | −0.167 | 0.167 |
| P45 (9 common dates) | 0.1398 | 0.076–0.208 | −0.75 | 0.82 | 0.68 | 0.90 | 0.579 | −0.185 | 0.185 |
| *S-LODO (not valid)* | *0.0858* | | *−0.07* | *0.88* | | | | | |
| *S-FULL (in-sample)* | *0.0776* | | *+0.03* | *0.88* | | | | | |

\*ROC-AUC, precision on LOW and the reliability bins are **UNSTABLE**: there are 4 LOW rows. Precision and recall for every arm are in RESULTS_TABLE.md.

**Paired one-sided exact sign-flip tests on per-date Brier** (Holm across four comparators):

| E35-TUNED vs | Gain per date | Better / worse / equal dates | p | p (Holm) |
|---|---|---|---|---|
| E32-PCFN | +0.0041 | 5 / 1 / 4 | 0.109 | 0.438 |
| PCF21 | −0.0020 | 6 / 4 / 0 | 0.632 | 1.000 |
| Persistence | +0.0034 | 5 / 5 / 0 | 0.393 | 1.000 |
| Always-HIGH | −0.0166 | 4 / 6 / 0 | 0.730 | 1.000 |

### Lead 2 (secondary; 8 dates, 38 HIGH / 2 LOW)

| Arm | Brier |
|---|---|
| E35-TUNED | 0.1210 |
| E32-PCFN | 0.1201 |
| PCF21 | 0.1279 |
| Persistence | 0.1750 |
| Always-HIGH | **0.0500** |

- Tuning did not help at lead 2. Against E32-PCFN: 2 dates better, 2 worse, 4 equal.
- AUC is below 0.5 for every model, with 2 LOW rows. It is meaningless here.

## 6. Selection uncertainty (PROTOCOL §8)

**Where the selection landed.** It moved in the same direction at both leads: λ = 1 (unshrunk news shift) and c = 0.8 (sharper probabilities).
- Lead 1, D set: D2 at 2024-Q4 to 2026-Q1, then D1.
- Lead 2: D4 throughout.

**How stable it was:**
- **Lead 1:** 4 distinct selections over 10 origins.
- **Bootstrap of dates (2000 resamples):** no single configuration wins more than 21% of resamples at lead 1 (26% at lead 2). The E32 default wins 0.1% (0.5%).
- **The grid ranks the default low:** 28th of 36 at lead 1 and 20th of 36 at lead 2.
- **Overlapping intervals:** the full-period Brier of every configuration lies within 0.075–0.117, and every 95% CI overlaps every other.

**Optimism:**
- The in-sample best (S-FULL) scores 0.0776 at lead 1. The honest nested estimate of the same procedure is 0.0966. The 0.019 gap is selection optimism, about 4.5 times the gain over E32-PCFN.
- At lead 2 the gap is 0.013.

## 7. Genuine gain or noise?

The evidence says noise, plus a little base-rate calibration.

1. **No discrimination gain.**
   - Accuracy, the confusion matrix (41/2/2/5) and the HIGH/LOW decision on every row are the same as E32-PCFN's.
   - AUC moved from 0.755 to 0.750.
   - All of the Brier change is calibration. The upper probability bin rose from mean p 0.85 to 0.88, against an observed rate of 0.98, and calibration-in-the-large improved from −0.159 to −0.134.
   - This is the model moving toward always-HIGH, which wins because 92% of the outcomes are HIGH. It is not better forecasting of which provinces change.
2. **The model's LOW calls show no skill, tuned or not.** Five rows got p < 0.35, and 3 of them turned out HIGH.
3. **The gain sits inside noise.**
   - 0.004 per date, p = 0.11, with 4 of 10 dates identical because there were too few inner dates to tune.
   - On the 6 dates where tuning was active: E35-TUNED 0.058, E32-PCFN 0.065, PCF21 0.064, persistence 0.033, always-HIGH 0.067. Persistence was best on those dates.
4. **The in-sample result looks good only in-sample.** The S-FULL score that would beat always-HIGH disappears under nested selection. Even S-LODO, which is allowed to use future outcomes, stays behind always-HIGH (0.086 vs 0.080).
5. **λ = 1 may amplify a trend, not a mechanism.** Regional news volume and hunger both rose over 2022–2024. E32 found the news–S1 link may share a time trend (ρ 0.24). An unshrunk news shift is the setting most exposed to that.

## 8. Limitations

- **Too few independent units.**
  - 10 lead-1 dates and 8 lead-2 dates; one regional H per date. The 50 rows are not 50 observations.
  - E34 estimated that about 62 dates are needed to detect a 0.02 Brier gain.
- **Too few LOW outcomes.** 4 at lead 1 and 2 at lead 2. AUC, LOW precision, balanced accuracy and reliability bins cannot be estimated stably.
- **The outer dates are not unseen.** They were scored in E32 and earlier, and the grid was designed by an analyst who knew E32's aggregate results. The nested design keeps each selection blind to later outcomes, but it is development evidence, not a test.
- **Small inner sets.** 0–9 dates for lead 1. The first selections rest on 3 dates (2024-Q4 origin), so the procedure is fragile by construction.
- **News timing.** The news features use articles collected retrospectively in 2026 and dated by publisher timestamp. Survivorship of older articles in the news index cannot be ruled out. This is a limitation of the data, not of the tuning.
- **CPI release timing** follows the E25/E31 convention (month m is released in month m+1). It was not verified per month in E35.

## 9. Prospective record (the only unseen test)

`frozen/E35_PROSPECTIVE.json` (sha `73a7ab1c…`) freezes the configuration that the nested rule selects at the operational origin 2026-10-01. It is a **research arm, not served**.
- **Inner dates:** those posted before that origin, so 2026-Q3, posted 2026-10-14, is excluded.

| Target | Selected configuration | P(HIGH): Cavite / Laguna / Quezon / Rizal / Batangas | E32-PCFN frozen, same order |
|---|---|---|---|
| 2026-Q4 (lead 1) | `lam1.0\|D1\|c0.80` | 0.90 / 0.87 / 0.91 / 0.89 / 0.67 | 0.71 / 0.88 / 0.83 / 0.76 / 0.61 |
| 2027-Q1 (lead 2) | `lam1.0\|D4\|c1.00` | 0.67 / 0.90 / 0.79 / 0.75 / 0.73 | 0.62 / 0.87 / 0.76 / 0.71 / 0.68 |

- Every decision is HIGH, the same as E32-PCFN, so the prospective test can separate the two only by Brier.
- One or two quarters cannot settle the question either. They add evidence to the ledger.
- Score it together with E32's record after the SWS December 2026 round and the Q4 CPI are authorized.

## 10. Deliverables

| Deliverable | Where |
|---|---|
| Tuning protocol (frozen) | `PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt`, git `37dc255` |
| Complete results table | `runs/20261015T005446Z/RESULTS_TABLE.md` (all arms, both leads, every metric) and `results.json` |
| Every configuration | `config_scores.csv` (36 × 2 leads: Brier, accuracy, precision, recall, F1, AUC, log loss, ECE, confusion matrix), `grid_predictions.csv`, `inner_scores.csv`, `selection_log.csv` |
| Hashes and seeds | `results.json`: `protocol_sha256`, `dataset_sha256` (7 input files), `seeds` (metrics bootstrap 20261014, selection bootstrap 35; model deterministic) |
| Selected parameters | `selection_log.csv` (per origin); `frozen/E35_PROSPECTIVE.json` (operational origin) |
| Reproducibility tests | `tests/test_e35.py`: 14 pass. E32's own 16 still pass |
| Verification | `verification/VERIFICATION.json` |
| Preservation | `preservation/BASELINE_MANIFEST.json` (97 files), checked after the run: 0 changed |
| How to reproduce | `REPRODUCE.md` |

## 11. Recommendation

1. **Keep PCF21 served** and keep E32-PCFN as it is. Do not adopt the tuned parameters.
2. **Stop tuning on these dates.** Further tuning of any model on these 10 dates cannot produce evidence of skill. The binding constraints are the number of dates, the LOW outcomes and a target that 92% of the time says HIGH.
3. **What would change this:**
   - more scored quarters (prospective);
   - or an adviser-approved target with real provincial variation (E32 §3).
