# FINAL-ETMIX: forecast performance and maximum reliable lead (Objective 2)

**Model.** FINAL-ETMIX (protocol `a365da1f`, locked 2026-11-13).
- One FINAL fit (RATE + MIND LightGBM on the survey-anchored target).
- It predicts each test row under two elapsed-time hypotheses: **g** (own-survey gap) and **s** (time since the latest released round).
- p = ½(p_g + p_s); HIGH when p ≥ 0.50; five seeds averaged.

**Design.** Walk-forward, expanding window.
- At each fold and lead: origin = target − lead.
- Training uses only survey outcomes released by the origin, with inputs as of the origin.
- Input selection, anchor choice, hyperparameters and calibration are refitted inside every fold (`app.hcw.final_engine`; research `engine_final`).
- No new fit was made for this report: the 220 stored ETMIX fits (`../aiPHeed_final_7of7_20261113/parts_mix`) were re-scored by `scripts/etmix_eval.py`.
- The contributor study refitted 110 of these and reproduced them to 1e-16 (`evidence/contributor_registry.json` → `integrity`).

**Evidence status.** These results are **retrospective**. The 72 province-rounds (2018, 2019, 2021) were reused while FINAL and its variants were developed, and ETMIX was designed knowing its components' results on them. They are **not independent validation** (see `FINAL_ETMIX_INDEPENDENT_VALIDATION_REPORT.md`).

## 1. Results by lead (5-seed average forecast; 95 % intervals: province-round bootstrap)

| Lead | n | HIGH / LOW | Accuracy [CI] | Precision | HIGH recall [CI] | F1 | AUC-ROC [CI] | Balanced acc. | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 72 | 25 / 47 | **0.861** [0.78, 0.93] | **0.778** | **0.840** [0.67, 0.96] | **0.808** | **0.903** [0.82, 0.96] | 0.856 | 0.127 | 21/6/4/41 |
| 2 | 72 | 25 / 47 | 0.833 [0.75, 0.92] | 0.741 | 0.800 [0.63, 0.95] | 0.769 | 0.907 [0.83, 0.97] | 0.826 | 0.124 | 20/7/5/40 |
| 3 | 72 | 25 / 47 | 0.819 [0.72, 0.90] | 0.731 | 0.760 [0.58, 0.92] | 0.745 | 0.895 [0.82, 0.96] | 0.806 | 0.129 | 19/7/6/40 |
| 4 | 72 | 25 / 47 | 0.833 [0.75, 0.92] | 0.724 | 0.840 [0.68, 0.96] | 0.778 | 0.898 [0.82, 0.96] | 0.835 | 0.129 | 21/8/4/39 |
| 5 | 72 | 25 / 47 | 0.792 [0.69, 0.88] | 0.679 | 0.760 [0.58, 0.91] | 0.717 | 0.888 [0.81, 0.95] | 0.784 | 0.133 | 19/9/6/38 |
| 6 | 72 | 25 / 47 | 0.750 [0.65, 0.85] | 0.630 | 0.680 [0.48, 0.86] | 0.654 | 0.876 [0.79, 0.95] | 0.734 | 0.142 | 17/10/8/37 |
| 7 | 50 | 17 / 33 | 0.700 [0.56, 0.82] | 0.545 | 0.706 [0.46, 0.92] | 0.615 | 0.815 [0.69, 0.92] | 0.701 | 0.180 | 12/10/5/23 |
| 8 | 50 | 17 / 33 | 0.740 [0.62, 0.86] | 0.583 | 0.824 [0.63, 1.00] | 0.683 | 0.818 [0.70, 0.92] | 0.760 | 0.175 | 14/10/3/23 |

- Leads 1–6 use 72 province-rounds from 72 provinces.
- Leads 7–8 have no 2018 fold, leaving 50 rows. They are not comparable with Leads 1–6.
- Nothing beyond Lead 8 is supported by the survey calendar.

Source: `evidence/ETMIX_summary_by_lead.csv`, `evidence/ETMIX_lead_results.json`.

## 2. By survey round (HIGH found / HIGH observed)

| Lead | 2018 (8 HIGH of 22) | 2019 (13 of 25) | 2021 (4 of 25) | Worst seed accuracy |
|---|---|---|---|---|
| 1 | 8/8, accuracy 0.86 | 11/13, 0.84 | **2/4**, 0.88 | 0.847 |
| 2 | 8/8, 0.82 | 11/13, 0.84 | **1/4**, 0.84 | 0.833 |
| 3 | 7/8 | 10/13 | 2/4 | 0.792 |
| 4 | 8/8 | 11/13 | 2/4 | 0.806 |
| 5 | 8/8 | 10/13 | 1/4 | **0.736** |
| 6 | 7/8 | 9/13 | 1/4 | 0.750 |
| 7 | — | 8/13 | 4/4 | 0.700 |
| 8 | — | 10/13 | 4/4 | 0.720 |

**HIGH-risk identification:**
- Strong in 2018 and 2019.
- Weak in 2021, where provinces had last been surveyed six years earlier: 2 of 4 at Lead 1, 1 of 4 at Lead 2.
- Each 2021 HIGH province is a quarter of that round's recall, so one province decides the verdict.

## 3. Lead-1 errors (10 of 72)

| Province | Round | Observed | ETMIX p | Type |
|---|---|---|---|---|
| Lanao del Norte | 2019 | HIGH (59 %) | 0.32 | Missed (Marawi displacement 2017, not a model input) |
| Misamis Oriental | 2019 | HIGH (55 %) | 0.38 | Missed (borderline outcome) |
| Masbate | 2021 | HIGH | 0.26 | Missed (stale 2015 anchor, peers fell faster) |
| Occidental Mindoro | 2021 | HIGH | 0.30 | Missed (same) |
| Camarines Norte, Iloilo, Sorsogon | 2018 | LOW | 0.57–0.79 | False alarms (2015→2018 national fall not visible at the origin) |
| Quirino, Southern Leyte | 2019 | LOW | 0.69–0.84 | False alarms |
| Sarangani | 2021 | LOW | 0.55 | False alarm (the mixture's predicted cost) |

ETMIX differs from FINAL only in the 2021 rows at Leads 1–6. There it finds Agusan del Sur (FINAL missed it) and adds one false alarm (Sarangani).

## 4. Probabilities (supplementary diagnostics)

| Lead 1 | Value | Reading |
|---|---|---|
| ECE (10 bins) | 0.111 | Below the null 95 % limit for n = 72 (0.16): consistent with calibration at this sample size |
| Mean p − HIGH rate | +0.074 | Mild over-prediction |
| Calibration slope / logit intercept | 1.46 / −0.49 | Probabilities are, if anything, *too modest* in spread and shifted up |
| Cox recalibration test | p = 0.10 | No significant miscalibration |
| Brier skill vs training HIGH share | 0.57 | Better than climatology |
| By round (mean p vs rate) | 2018 0.55 vs 0.36; 2019 0.49 vs 0.52; 2021 0.23 vs 0.16 | 2018 over-predicted by about +0.19 |

**Reliability (Lead 1):** in the 0.9–1.0 bin, 7 of 7 are HIGH; at p ≤ 0.2, 0 of 20 are HIGH. In the 0.4–0.5 bin, 0 of 7 are HIGH. The probabilities **rank** risk well (AUC 0.90). With 72 forecasts they cannot be shown to be calibrated within ±0.05 (`evidence/ETMIX_reliability_L1.csv`).

**Threshold sensitivity (Lead 1, supplementary; the 0.50 cut-off is fixed by protocol and was not tuned):**

| Cut-off | 0.40 | 0.45 | **0.50** | 0.55 | 0.60 |
|---|---|---|---|---|---|
| Recall | 0.84 | 0.84 | **0.84** | 0.76 | 0.76 |
| Precision | 0.62 | 0.68 | **0.78** | 0.76 | 0.83 |

Between 0.45 and 0.60, accuracy moves by at most ±0.06, so the results are not an artefact of one cut-off (`evidence/ETMIX_threshold_sensitivity.csv`).

## 5. Maximum reliable lead

| Rule (fixed before this scoring) | Definition | FINAL-ETMIX |
|---|---|---|
| Thesis Algorithm 3 | Mean fold accuracy ≥ 75 %, consecutive from Lead 1 | **Lead 5** (L6 0.747) |
| 11-11 robust rule | Thesis rule + Brier significantly better than persistence + every seed ≥ 75 % + every round ≥ 70 % + HIGH and LOW recall ≥ 0.75 | **Lead 4** (L5: worst seed 0.736) |
| Locked PROTOCOL_SA (seven rules, incl. per-round HIGH recall ≥ 0.50 where ≥ 4 HIGH) | `../aiPHeed_final_7of7_20261113/FINAL_MAXIMUM_RELIABLE_LEAD_REPORT.md` | **Lead 1** (L2 fails 7c: 2021 recall 1/4) |

**Where performance deteriorates.**
- Balanced accuracy holds from Lead 1 to Lead 4 (0.86 → 0.84), then falls: 0.78 at Lead 5, 0.73 at Lead 6.
- HIGH recall falls to 0.68 at Lead 6.
- At Leads 7–8, precision drops below 0.6 (on a different row set).

## 6. Answers
1. **Is Lead 1 sufficiently reliable?**
   - Retrospectively, yes under all three rules: accuracy 0.861, recall 0.84, precision 0.78, AUC 0.90.
   - Admissibly, no: no independent evidence yet.
2. **Is Lead 2 sufficiently reliable?**
   - Under the thesis and robust rules, yes.
   - Under the strict per-round rule, no, because 2021 HIGH recall is 1/4.
3. **Are longer leads defensible?**
   - Leads 3–4: only under the thesis and robust rules, and retrospectively.
   - Leads 5–8: not defensible.
4. **Where does it deteriorate?** After Lead 4.
5. **Furthest supported horizon:**
   - **Lead 4** (robust rule, retrospective);
   - **Lead 1** under the strict per-round rule;
   - **none established** on admissible (independent) evidence.
   - The sealed ENNS 2022 forecasts (Leads 1–2, `71ebe142`) are the first admissible test.
