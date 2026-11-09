# E180: seed ensemble of E179, and sealed ENNS 2022 forecasts. Report

## Decision: **the seed ensemble did not improve the model on the pre-registered rule. E168 stays in production.**

E180 is the mean of E179's forecasts over generator seeds 17901–17905 (`docs/e180/PROTOCOL.md`, committed `f04efaa`
before any E180 output). As the protocol states, E180 was designed after E179's per-seed results were seen. It is the
last candidate scored on the 72 outer rows. The independent test is the ENNS 2022 seal below.

| Rule (all must hold) | Result |
|---|---|
| Brier CI upper bound vs E168 below 0, Lead 1 | ❌ −0.0018 [−0.0061, +0.0032] |
| Brier CI upper bound vs E168 below 0, Lead 2 | ❌ −0.0019 [−0.0063, +0.0019] |
| Accuracy ≥ E168, Lead 1 | ✅ 75.0 % = 75.0 % |
| Accuracy ≥ E168, Lead 2 | ✅ 77.8 % = 77.8 % |
| Leakage below 1e-9 | ✅ 0.0 |
| Beats shuffled triggers | ❌ −0.0021 [−0.0190, +0.0154] |

## Results on the 72 real outer rows

| | Accuracy | Balanced acc. | HIGH precision | HIGH recall | Macro-F1 | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|
| **Lead 1** | | | | | | | | |
| Persistence | 0.625 | 0.703 | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | 0.750 | 0.780 | 0.595 | 0.88 | 0.745 | 0.891 | 0.1230 | 0.76 |
| E179 (seed 17901) | 0.778 | 0.802 | 0.629 | 0.88 | 0.771 | 0.894 | 0.1214 | 0.81 |
| **E180** | 0.750 | 0.762 | 0.606 | 0.80 | 0.740 | 0.889 | **0.1213** | 0.79 |
| **Lead 2** | | | | | | | | |
| Persistence | 0.625 | 0.703 | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| E168 | 0.778 | 0.802 | 0.629 | 0.88 | 0.771 | 0.893 | 0.1221 | 0.71 |
| E179 (seed 17901) | 0.750 | 0.762 | 0.606 | 0.80 | 0.740 | 0.883 | 0.1229 | 0.72 |
| **E180** | 0.778 | 0.792 | 0.636 | 0.84 | 0.769 | 0.890 | **0.1202** | 0.73 |

- **Exact McNemar test against E168.** Lead 1: 2 rows right only for E180, 2 right only for E168 (p = 1.0). Lead 2:
  1 against 1 (p = 1.0).
- **Per survey round, accuracy (E168 → E180):**

  | Round | Lead 1 | Lead 2 |
  |---|---|---|
  | 2018 | 68.2 % → 68.2 % | 68.2 % → 63.6 % |
  | 2019 | 76.0 % → 72.0 % | 80.0 % → 80.0 % |
  | 2021 | 80.0 % → 84.0 % | 84.0 % → 88.0 % |

- **Brier by round.** E180's Brier score is lower than E168's in 2018 and 2019 at both leads, and slightly higher in
  2021.

**Reading.**
- **What averaging did.** It removed E179's seed luck. Accuracy now equals E168's at both leads.
- **What remains.** The Brier score is about 1.5 % lower at both leads, the first time the direction is the same at
  Lead 1 and Lead 2. The gain is still well inside the uncertainty of 72 rows.
- **The trade-off.** E180 raises fewer false alarms but misses one or two more HIGH provinces (recall 0.80–0.84
  against 0.88). For an early-warning system, that is not clearly an improvement.

## ENNS 2022 seal (the independent test)
- **File:** `backend/data/e180/out/sealed_enns2022.json`, written 2026-11-09 12:59 UTC.
  - SHA-256 `6e2c1e96db01c206b629fb68c94eaf575693a1a66b543753519fc58cc53bd050`.
  - It holds 156 forecasts (every ENNS 2022 province × Leads 1–2) for E168, E179 and E180.
- **Construction.**
  - Frames come from `app.e168.enns2022_seal`, unchanged, at origin O3, so ENNS 2021 had not yet been released.
  - Only the model call is replaced by E179's procedure.
  - The E168 forecasts inside it reproduce E168's own seal (`f8228fae`) to its 6-decimal rounding (max |Δμ| = 5 × 10⁻⁷).
- **HIGH calls.** E168 29, E179 31, E180 29 of 156. E180 changes the class on only **4** provinces (E179: 10). All five
  CALABARZON provinces are LOW under all three models.
- **Scoring rule (fixed in the protocol).** Once FNRI's ENNS 2022 provincial HFIAS moderate+severe results are public
  and verified as comparable HFIAS:
  - score accuracy, Brier and HIGH recall for E168, E179 and E180;
  - do no re-fitting.
  - This is the only evidence that can show whether synthetic augmentation helps on data no model has seen.

## Conclusion across E178–E180

| Experiment | Synthetic-data design | Outcome |
|---|---|---|
| E178 | Fixed settings, fidelity gate | Stopped by the gate: synthetic rows not realistic for the 2018/2019 training sets |
| E179 | Settings tuned on training folds, no-harm fallback | 77.8 % / 75.0 % (E168 75.0 / 77.8). Not better. |
| E180 | E179 averaged over 5 seeds | 75.0 % / 77.8 %, equal to E168. Brier −1.5 %, not significant. Not better. |

- **What synthetic augmentation can do here.** On the available data it can smooth E168's probabilities slightly. It
  does not measurably improve which provinces are called HIGH.
- **What limits the model.** The limit is real information: three validation rounds and 156 training rows at the early
  origins. Rows generated from those same rows cannot add it.
- **The next real gain** will come from new survey rounds (ENNS 2022 or later), which will also score the seal above.
- **No candidate staged.** Nothing was registered or promoted.
