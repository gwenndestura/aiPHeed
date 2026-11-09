# E179: E168 plus tuned synthetic training rows. Report

## Decision: **tuned synthetic augmentation did not improve the model on the pre-registered rule. E168 stays in production.**

E179 was run once, as fixed in `docs/e179/PROTOCOL.md` (committed `e1db15f`, before any E178 or E179 result on the outer
rows). The 72 real outer rows per lead were used only for this final evaluation.

| Rule (all must hold) | Result |
|---|---|
| Brier CI upper bound vs E168 below 0, Lead 1 | ❌ −0.0016 [−0.0090, +0.0071] |
| Brier CI upper bound vs E168 below 0, Lead 2 | ❌ +0.0008 [−0.0024, +0.0043] |
| Accuracy ≥ E168, Lead 1 | ✅ 77.8 % vs 75.0 % |
| Accuracy ≥ E168, Lead 2 | ❌ 75.0 % vs 77.8 % |
| Leakage below 1e-9 | ✅ 0.0 (corrected control, deviation D3) |
| Beats shuffled triggers | ❌ −0.0015 [−0.0207, +0.0175] |

**Reproduce:**
- `cd backend; python -m app.e179.tuned run` (33 minutes on 7 cores)
- `python -m app.e179.tuned leakage` (deviation D3)

**Outputs:** `backend/data/e179/out/`, with hashes in `hashes.json`.

## Results on the 72 real outer rows (primary seed 17901)

| | Accuracy | Balanced acc. | HIGH precision | HIGH recall | Macro-F1 | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|
| **Lead 1** | | | | | | | | |
| Persistence | 0.625 | 0.703 | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | 0.750 | 0.780 | 0.595 | 0.88 | 0.745 | 0.891 | 0.1230 | 0.76 |
| **E179** | **0.778** | **0.802** | **0.629** | 0.88 | **0.771** | **0.894** | **0.1214** | 0.81 |
| **Lead 2** | | | | | | | | |
| Persistence | 0.625 | 0.703 | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | **0.778** | **0.802** | **0.629** | **0.88** | **0.771** | **0.893** | **0.1221** | 0.71 |
| E179 | 0.750 | 0.762 | 0.606 | 0.80 | 0.740 | 0.883 | 0.1229 | 0.72 |

- **Exact McNemar test against E168.** Lead 1: E179 right where E168 was wrong on 5 rows, the reverse on 3 (p = 0.73).
  Lead 2: 1 against 3 (p = 0.63).
- **Per survey round, Lead 1:**

  | Round | E168 accuracy | E179 accuracy |
  |---|---|---|
  | 2018 | 68.2 % | 72.7 % |
  | 2019 | 76.0 % | 76.0 % |
  | 2021 | 80.0 % | 84.0 % |

  At Lead 2, E179 is lower in 2018 (63.6 % against 68.2 %) and 2019 (76.0 % against 80.0 %), and equal in 2021.

**Stability over five generator seeds** (17901–17905):

| | Lead 1 | Lead 2 |
|---|---|---|
| Accuracy, mean ± SD | 76.7 % ± 2.1 (range 73.6–79.2) | 76.7 % ± 1.2 (range 75.0–77.8) |
| Brier − E168, mean ± SD | −0.0014 ± 0.0006 | −0.0015 ± 0.0022 |
| Seeds with a lower Brier than E168 | 5 of 5 | 4 of 5 |
| Seeds meeting rule items 1–2 | 0 of 5 | 0 of 5 |

**Reading.**
- **Brier.** E179's Brier score is slightly lower than E168's in 9 of 10 seed × lead runs, but the gain is about 1 %
  (−0.0014). That is far inside the uncertainty of 72 rows.
- **Accuracy.** Accuracy moves by ±2 provinces, in opposite directions at the two leads. On average it equals E168: about
  76.7 % against E168's 76.4 % average of Leads 1 and 2.
- **Conclusion.** Tuned synthetic augmentation is **not a measurable improvement** on the available validation data.

## What the tuning chose (primary seed)

| Outer training set | Settings clearly better than "none" (1-SE rule) | Chosen |
|---|---|---|
| ENNS2021 L1 (532 rows) | 68 of 128 | jitter, 2× rows, weight 1.0, noise 0.25 SD, boundary |
| ENNS2021 L2 | 54 of 128 | jitter, 2× rows, weight 1.0, noise 0.5 SD, uniform |
| ENNS2019 L1 (156 rows) | 2 of 128 | jitter, 0.5× rows, weight 0.2, noise 0.5 SD, boundary |
| ENNS2019 L2 | 1 of 128 | jitter, 1× rows, weight 0.2, noise 0.5 SD, boundary |
| ENNS2018 L1 (156 rows) | 5 of 128 | jitter, 1× rows, weight 0.4, noise 0.5 SD, boundary |
| ENNS2018 L2 | 3 of 128 | jitter, 1× rows, weight 0.2, noise 0.5 SD, boundary |

Over all seeds, 84 % of the main jobs used augmentation. SMOTE was never chosen. Large-noise jitter near the 50 % line
(the "boundary" focus) dominates.

- **Where training data was plentiful (2021)**, synthetic rows improved the inner-fold fit a lot. On the outer rows,
  Lead 1 gained (+1 province) while the Brier score at 2021 rose slightly (0.0835 → 0.0890). The inner-fold gains did
  not transfer.
- **Where it was scarce (2018/2019)**, almost no setting helped, and the chosen ones carry low weight (0.2–0.4). This
  agrees with E178's fidelity finding: 156 real rows cannot support realistic synthetic data.
- **The shuffled controls at 2018/2019 chose "none".** Augmentation was selected only when the inputs carried real signal.

## Checks
- **E168 inside E179.** Stage A without augmentation reproduces the stored E168 rows exactly: 432 rows, same
  configuration, max |Δp| = 0.0.
- **Synthetic rows were never scored.** Unit test `test_synthetic_rows_never_scored_and_rule_is_consistent`; the metrics
  above use real rows only.
- **Deviation D3 (leakage control).**
  - In the first run, the corrupted-data jobs drew their synthetic rows from their own random stream, because the
    stream key included the job mode. Their difference from the main run was therefore 0.1235: generator randomness,
    not information.
  - Re-run with the main jobs' stream (`python -m app.e179.tuned leakage`), the corrupted runs select the same settings
    and give **identical** forecasts (0.0).
  - Both numbers are in `results.json`, and the first-run rows are kept as `corrupt_own_stream`.
  - The same keying affects E178's design, but E178 Stage 2 did not run.
- **Environment.** As E178: scikit-learn 1.7.2 against the pinned 1.8.0 (deviation D1, owner-approved). Two gitignored
  inputs are hash-checked; the SunStar panel is a stand-in whose columns E168 never uses.

## Conclusion for the thesis
- **E178** (fixed settings) was stopped by its fidelity gate.
- **E179** (augmentation tuned on training data, with a no-harm fallback) ran in full and did not beat E168. Its
  accuracy swung ±2.8 points between leads, averaged the same, and gave about a 1 % Brier change that is not
  significant.
- **Both point the same way.** E168's limit is the amount of real survey data: three validation rounds and about 46
  effective training rows at the early origins. Synthetic rows built from those same rows cannot add the missing
  information.
- **What would help:** more real provincial HFIAS rounds (ENNS 2022 or later), provincial employment and remittance
  series, and newer regional consumption data.
- **No candidate staged.** No E179 candidate was staged. Nothing was registered or promoted.
