# E38: diagnosis and nested tuning of the next-quarter (lead 2) LightGBM

**Date:** 2026-10-15.
**Branch:** `e38-lead2-diagnosis-tuning`, cut from `final-aipheed-integration` @ `0782a40`.
**Commits:**
- `b9a2349`: verification, diagnosis, protocol frozen (sha `3e851f34…`);
- the library, tests and runner commit before scoring;
- the final commit with runs, freeze and this report.

Nothing pushed. The approved frontend branch `10-15-updated-flexible-ui` was not modified. E38 touches no frontend file.

## Answers

**1. Was E37 reproduced? Did the reporting bug affect the evaluation?**
- **Reproduced byte-identically:** predictions sha `e8ec326e…`; 39/55 and 44/55 recomputed independently (`runs/e37_repro_*`).
- The `select()` fix changed **only the displayed names** of the prior dates (origin+1 instead of origin+2). Every choice and every inner score is identical with and without it (`runs/e38_verification_diagnosis.json` → `select_fix`).
- The LightGBM and persistence rows are identical: 55 rows, 11 dates, 6 LOW.
- One side finding: `results.json` input hashes differed only because git had converted the input CSVs to CRLF on checkout. LF-normalized hashes equal the originals, and the files are now restored byte-for-byte (`.gitattributes`).

**2. Why 70.9% and LOW recall 2/6?** Evidence in `runs/e38_verification_diagnosis.json`.
- **Few outcomes:** 11 independent regional observations; 6 LOW rows on 5 dates (Laguna and Quezon 2023-Q3, Quezon 2023-Q4 and 2024-Q1, Batangas 2025-Q4 and 2026-Q2).
- **Base-rate drift:**
  - The label is relative to a trailing median. Early training sets are LOW-rich, but 89% of outer outcomes are HIGH.
  - The model is under-confident about HIGH (calibration-in-the-large −0.24).
  - **12 of the 16 errors are HIGH outcomes called LOW**; only 4 are missed LOWs.
- **Threshold is not the cause:** thresholds from 0.3 to 0.5 give identical decisions. This was a diagnostic sweep on outer rows and was never used to choose.
- **Inputs** (training rows only, at 2026-10-01):
  - prices carry the signal (Dnow AUC 0.83, D_last 0.81, y_last 0.78);
  - news is weak (0.55–0.63) and mostly zeros (FSSI 80%);
  - H_last and H_margin are redundant (r = 0.998).
- **The five triggers:** 192 of 2,820 attributed titles match any trigger (climate 164, fish_kill 17, market 10, employment 1, OFW 0). They carry almost no data.

**3. What was tested?**
24 configurations, each chosen per origin by the nested rule:
- {COMPACT, COMB, COMB + five trigger proportions} × {G1 stumps, G5 stumps with reg_alpha/lambda and min_child 10, G6 stumps with bagging and feature subsampling, G3 depth 2} × {no adjustment, prior-shift};
- prior-shift = intercept moved to the HIGH rate of the 4 latest labelled quarters posted before the origin;
- threshold chosen from {0.3, …, 0.7} by the inner rule (balanced accuracy on prior dates, only with ≥ 3 LOW rows).

**4. Selected candidate and rule.**
- At the operational origin (2026-10-01) the rule picks **COMPACT × G5 + prior-shift, threshold 0.5** ("E38-LGBM").
- It was adopted because it satisfies the frozen adoption rule (§6): accuracy ≥ E37, balanced accuracy ≥ E37, and per-date Brier ≤ E37 (0.1996 vs 0.2156).

**5. Tuned candidate's metrics** (55 rows, 11 dates):

| Metric | Value |
|---|---|
| Accuracy | **39/55 = 0.709** (date-bootstrap 95% CI 0.582–0.836) |
| LOW recall | **2/6** |
| HIGH recall | 37/49 |
| Balanced accuracy | 0.544 |
| Brier | 0.1996 |

The other metrics are in `runs/20261015T033922Z/results.json`.

**6. Against persistence and the six thesis models** (E38 per-date Brier gain; two-sided p; Holm over six):

| Model | Correct/55 | LOW recall | Brier | E38 gain (p, Holm) |
|---|---|---|---|---|
| E38-LGBM (tuned) | 39 | 2/6 | 0.200 | – |
| B1 Naive persistence | 44 | 4/6 | 0.200 | +0.0004 (1.00, 1.00) |
| B2 LR combined | 33 | 4/6 | 0.286 | +0.087 (0.06, 0.36) |
| B3 LR government (PSA-only) | 33 | 4/6 | 0.253 | +0.054 (0.25, 1.00) |
| B4 LR NLP | 32 | 2/6 | 0.221 | +0.022 (0.62, 1.00) |
| B5 LightGBM government | 39 | 2/6 | 0.223 | +0.023 (0.28, 1.00) |
| B6 LightGBM NLP | 39 | 2/6 | 0.210 | +0.011 (0.80, 1.00) |
| *Diagnostic, not a thesis baseline:* always-HIGH | 49 | 0/6 | 0.109 | −0.091 |

**7. 75% on a defensible evaluation? No.**
- 0.709, and the bootstrap interval reaches 0.582.
- **Even the best of the 24 configurations picked in hindsight on the outer outcomes reaches only 0.727.** The data do not support 75% at this horizon with the approved target.

**8. Skill beyond persistence? No.**
- Brier is equal (0.200 vs 0.200).
- Persistence has higher accuracy (0.800) and higher LOW recall (4/6).

**9. Overfitting, leakage, instability?**
- **Leakage:** none. The 7 E38 tests pass:
  - future scrambling, including the trigger features, leaves every prediction and the prior shift unchanged;
  - the threshold and selection use only labels posted before each origin;
  - changing the last outcome alters no earlier choice;
  - the shared COMB × G1 configuration reproduces E37 exactly.
- **Optimism:** the outer dates were examined for the fourth time (E25, E32, E35, E37), and choosing to run E38 at all was prompted by E37's result on them. E38's score is development evidence, not independent validation.
- **Stability:** the selection path moves from COMB × G1 to COMPACT × G1 + PS to COMPACT × G5 + PS. Accuracy is 20/30 on 2023-Q3..2024-Q4 and 19/25 on 2025-Q1..2026-Q3.

**10. Suitable for production?**
- Usable as an **experimental** estimate with a disclosed status. It is the procedure the frozen rule selects, and its probabilities are better calibrated than E37's.
- **Predictive validation: NOT DEMONSTRATED.** It is INCONCLUSIVE on reliability until prospective outcomes exist.
- Limitation: the four non-Batangas provinces get an identical p (0.952), because the stump model on COMPACT features splits mainly on province price pressure.

**11. Dynamic next-quarter forecast.** This is integrated on `final-aipheed-integration` (see that branch's report). E38 froze the 2027-Q1 record that the backend serves:
- `frozen/E38_PROSPECTIVE_2027Q1.json`, sha `9549071c…`;
- origin 2026-10-01, cutoff exclusive;
- latest label 2026-Q2;
- six baselines copied from the E37 freeze.

**12. Frontend and triggers.** E38 changes no frontend file. The five-trigger finding (near-empty news coverage) is reported here; their display is handled on the integration branch.

**13. Files**
- `PROTOCOL.md`, `runner/{e38_diagnose,e38_lib,e38_evaluate,e38_freeze}.py`, `tests/test_e38_tuning.py`.
- `runs/`:
  - verification and diagnosis;
  - E37 reproduction;
  - two byte-identical evaluation runs (`20261015T033922Z`, `20261015T034245Z`).
- `models/E38-LGBM-NQ_O2026-10-01_lead2.{txt,json}`.
- `frozen/E38_PROSPECTIVE_2027Q1.json` and `E38_SERVING_BUNDLE.json`, with `.sha256`.

**14. What is still needed**
- Prospective outcomes: 2026-Q4 (E36, lead 1) and 2027-Q1 (E38, lead 2), scored once each.
- More LOW quarters.
- An adviser decision on the relative target, which drives the base-rate drift.
- A richer news source for the five triggers (titles alone contain almost none).
