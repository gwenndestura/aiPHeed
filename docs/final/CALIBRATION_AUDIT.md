# Calibration audit

**Sources:** `data/final_audit/out/audit.json`; `docs/e166/C1_C4_ANALYSIS.md`; E165 and E167 nested runs.
**Reliability diagrams:** `data/final_audit/out/reliability_lead1_E158_E166.png`, `reliability_lead1_PERS_E158.png`.

## 1. Measured calibration (Lead 1, n = 72)
| Model | C4 logit-level slope [95 %] (pre-registered) | Probability slope [95 %] (supplementary) | Mean signed error (points) | Brier |
|---|---|---|---|---|
| Persistence | 0.71 [0.51, 0.86] | 1.09 [0.62, 1.80] | +9.5 | 0.213 |
| E158 | 0.72 [0.47, 0.91] | 1.53 [0.96, 2.73] | +2.9 | 0.134 |
| E166 | 0.74 [0.51, 0.87] | 1.53 [0.93, 3.40] | +3.25 | 0.125 |
| E167 | 0.63 [0.45, 0.74] | 1.39 [0.98, 2.51] | +6.3 | 0.156 |

**E166 reliability table:**

| Probability band | Rows | Mean predicted | Observed HIGH rate |
|---|---|---|---|
| 0–0.2 | 14 | 0.07 | 0.00 |
| 0.2–0.4 | 12 | 0.27 | 0.17 |
| **0.4–0.6** | 20 | 0.51 | **0.15** |
| 0.6–0.8 | 13 | 0.70 | 0.69 |
| 0.8–1.0 | 13 | 0.91 | 0.85 |

- **The extremes are well calibrated.** The **0.4–0.6 band is over-predicted**, and 17 of its 20 rows are 2018/2019 LOW provinces near the line.
- **Direction:**
  - prevalence levels are too spread out (C4 slope < 1);
  - P(HIGH) is compressed (probability slope > 1);
  - there is a net upward level bias.
- **By round, the C4 slope is 1.15 (2018), 0.91 (2019) and 0.62 (2021).** Calibration is **not stable across origins.**
- **By province:** one row per province, so calibration by province cannot be estimated.

## 2. Methods evaluated (all fitted on training data only)
| Method | Where tested | Result vs uncalibrated |
|---|---|---|
| Uncalibrated (Φ(mu/sd), gap-dependent sd) | All | Baseline |
| Linear logit recalibration (intercept + slope) | E164/E166 inner selection (an option); E165/E167 (scored by inner Brier) | **Rarely chosen. When chosen it did not fix C4.** E167 was worse (Brier 0.156) |
| Platt scaling (soft labels, L2, C = 1) | E165, E167 inner selection | **Never chosen by inner validation.** E165 probability slope 1.73 (more compressed) |
| Prior / intercept adjustment from earlier rounds | Chronological: 2018 + 2019 → 2021 (C1_C4_ANALYSIS) | **Worse:** 2021 bias −2.0 → −7.9, Brier 0.098 → 0.106, slope unchanged (0.61) |
| Isotonic | Not run | **Not supported:** 3 rounds and about 46 effective rows. A step function would fit noise |

## 3. Verdict
- **No calibration method improved on the uncalibrated baseline under training-only, chronological fitting.**
- **The cause is not the calibrator.** The miscalibration is round-specific and changes sign:
  - the 2015→2018 fall was unseen in training;
  - the 2021 over-dispersion was unseen in 2018/2019.
- At the 2018 and 2019 origins, training holds a single target round (2015), so a between-round correction **cannot be estimated** there.
- **Reliable calibration cannot be established with the current observations.**
- **Needed:**
  - at least one more provincial HFIAS round, so a correction can be learned on one round and tested on the next;
  - or a timely national HFIAS-level indicator (none exists: SWS moved the opposite way in 2020–2021).
- **Selected method: none (uncalibrated retained).** A calibrator that does not beat the baseline out of sample is not adopted.
