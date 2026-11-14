# E182: the E181 jitter-2× candidate, fixed and fully tested. Report

## Decision: **E182 did not meet the pre-registered rule. E168 stays in production.**

E182 is E168's selection plus one fixed augmentation setting: jitter, 2× synthetic rows, full weight, 0.5 SD noise,
boundary focus, averaged over generator seeds 17901–17905 (`docs/e182/PROTOCOL.md`, committed `d0ca5ff` before any
E182 output). The setting was found post hoc in E181, so the scores on the 72 outer rows are optimistic.

| Rule (all must hold) | Result |
|---|---|
| Brier CI upper bound vs E168 below 0, Lead 1 | ❌ −0.0018 [−0.0120, +0.0078] |
| Brier CI upper bound vs E168 below 0, Lead 2 | ❌ −0.0022 [−0.0104, +0.0056] |
| Accuracy ≥ E168, Lead 1 | ✅ 79.2 % vs 75.0 % |
| Accuracy ≥ E168, Lead 2 | ✅ 79.2 % vs 77.8 % |
| Leakage below 1e-9 | ✅ 0.0 |
| Beats shuffled triggers | ❌ +0.0031 [−0.0094, +0.0180]: the shuffled version scores **better** |

**Checks.**
- E182's main forecasts equal E181's recorded forecasts for this variant (max |Δp| 2.2 × 10⁻¹⁶).
- Its E168 part equals the stored E168 rows (max |Δp| 0.0).

**Reproduce:**
- `cd backend; python -m app.e182.candidate run`
- `python -m app.e182.candidate seal`

## Metrics on the 72 real outer rows

| | Accuracy | Balanced acc. | HIGH precision | HIGH recall | F1 | Macro-F1 | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|
| **Lead 1** | | | | | | | | | |
| Persistence | 62.5 % | 70.3 % | 0.480 | 0.96 | 0.640 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | 75.0 % | 78.0 % | 0.595 | 0.88 | 0.710 | 0.745 | 0.891 | 0.1230 | 0.76 |
| **E182** | **79.2 %** | **80.3 %** | **0.656** | 0.84 | **0.737** | **0.782** | 0.889 | **0.1212** | **0.83** |
| **Lead 2** | | | | | | | | | |
| Persistence | 62.5 % | 70.3 % | 0.480 | 0.96 | 0.640 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | 77.8 % | 80.2 % | 0.629 | 0.88 | 0.733 | 0.771 | 0.893 | 0.1221 | 0.71 |
| **E182** | **79.2 %** | **81.2 %** | **0.647** | 0.88 | **0.746** | **0.785** | **0.894** | **0.1199** | **0.79** |

- **Confusion.**

  | | False alarms (L1 / L2) | Missed HIGH (L1 / L2) |
  |---|---|---|
  | E168 | 15 / 13 | 3 / 3 |
  | E182 | 11 / 12 | 4 / 3 |

- **McNemar test against E168.** Lead 1: 5 rows right only for E182, 2 only for E168 (p = 0.45). Lead 2: 2 against 1
  (p = 1.0).
- **By round, accuracy.** E182's gain at Lead 1 comes from 2018 (68.2 % → 77.3 %) and 2019 (76.0 % → 80.0 %). At Lead 2
  it comes from 2019 (80.0 % → 84.0 %).
- **By round, Brier.** E182 is better in 2018 and worse in 2019 and 2021.

## The shuffled control: why these accuracy gains cannot be credited to the inputs
In the shuffled control, the trigger inputs (weather and farm, prices, jobs, remittances, fish catch, news) are permuted
across provinces within each round, in training and test alike. Lead 1, 72 rows:

| | Accuracy | Balanced acc. | HIGH recall | Brier |
|---|---|---|---|---|
| E168, real inputs | 75.0 % | 78.0 % | 0.88 | 0.1230 |
| E168, shuffled (mean of 3) | 79.2 % | 82.2 % | 0.92 | 0.1233 |
| E182, real inputs | 79.2 % | 80.3 % | 0.84 | 0.1212 |
| E182, shuffled (mean of 3) | **84.7 %** | **86.4 %** | 0.92 | **0.1181** |

- **The finding.** Putting the trigger inputs in the wrong provinces **raises** accuracy for both models.
  - The provincial forecast skill on these 72 rows comes from the survey baseline (anchor).
  - The trigger inputs, as currently measured (several are national series), add no demonstrable province-specific
    information.
  - Accuracy differences of four or five points arise from the arrangement of the inputs alone.
- **What it means for the thesis.**
  - **E182's +4 / +1.4 points cannot be attributed to synthetic data improving the model's use of the inputs.**
  - Nor can any accuracy difference of this size on 72 rows be read as a better model.
  - It also qualifies E168: it does not beat shuffled triggers either (E168 report: −0.0003 [−0.015, +0.018]).

## ENNS 2022 seal
- **File:** `backend/data/e182/out/sealed_enns2022.json`.
  - SHA-256 `11680b71d3be4d26773287abb04b3134c5db386a64d3db256e797ed188acc9e6`.
  - 156 forecasts, every province × Leads 1–2.
- **E168 check.** The E168 part matches E168's own seal to its rounding (max |Δμ| 5 × 10⁻⁷).
- **Discriminating rows.** E182 changes the class on only **2** provinces, so ENNS 2022 will decide it on those 2 rows.

## Conclusion (E178–E182)
| | Synthetic design | Accuracy L1 / L2 | Passes the rule? |
|---|---|---|---|
| E168 (production) | none | 75.0 % / 77.8 % | (in production) |
| E178 | fixed, fidelity gate | not run (gate) | — |
| E179 | tuned on training folds | 77.8 % / 75.0 % | no |
| E180 | E179 averaged over 5 seeds | 75.0 % / 77.8 % | no |
| E181 | 129-variant search (exploratory) | up to 81.9 % / 79.2 % (recall drops) | exploratory |
| E182 | best forward-checked variant, fixed | 79.2 % / 79.2 % | no (Brier CI includes 0; shuffled better) |

- **What synthetic augmentation does.** It can shift E168's accuracy by a few points either way and slightly improve its
  calibration. None of these changes is distinguishable from noise on 72 validation rows. The shuffled control shows that
  differences of this size occur without any real input information.
- **What would make the model more accurate.** More real provincial survey rounds, and more province-specific trigger
  data (provincial employment and remittances instead of national series). Not more synthetic rows.
- **What will decide it.** The ENNS 2022 seals (E168, E179, E180, E182) are the fair test once FNRI publishes.
