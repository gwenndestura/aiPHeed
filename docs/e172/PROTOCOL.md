# E172 protocol: E168 plus the thesis decision cutoff, set from training out-of-fold scores

Locked 2026-11-07, before any E172 result exists.

## Why
- Chapter III, Section 3.5 of the thesis says "the decision cutoff will be set from the walk-forward out-of-fold scores".
- E168 fixed the cutoff at P(HIGH) ≥ 0.5 (docs/e168/PROTOCOL.md) and never applied this step.
- **Disclosure:** this step was chosen after E168's errors were seen (15 false HIGH, 3 missed HIGH at Lead 1). Its justification is the thesis text, not those errors. The cutoff itself is chosen on training rows only.

## Procedure
1. **Everything in E168 is unchanged:** `app.e168.lgbm_only.run_proc` (anchors, feature sets, 384-configuration LightGBM grid, region GroupKFold, calibration layer chosen on inner out-of-fold Brier). The test-row probability `p` must equal E168's `p` exactly; this is checked.
2. **New step.** At each origin, take the chosen calibration layer's out-of-fold probability on the training rows (raw `Φ(oof/sd)`, linear `Φ(lin/sdl)`, or Platt `pl`) and the training HIGH labels (`y_true ≥ 0`, that is HFIAS ≥ 50 %).
   - Choose the cutoff c from {0.20, 0.225, …, 0.80} that maximises unweighted training out-of-fold accuracy.
   - On ties, take the c closest to 0.5.
3. Forecast HIGH when `p ≥ c`. No other change. Test rows never touch the choice.
4. Run at Leads 1–8 for ENNS 2018, 2019 and 2021, with the same skip rule as `app.e168.longer_leads.guarded`.

## Evaluation (thesis Chapter III, Algorithm 3 and Section 3.4.4)
- **Stopping metric:** mean fold accuracy, where a fold is a survey round and the mean is unweighted over rounds.
- **Search:** iterate k = 1…8, halting at the first k below 75 %.
- **Maximum Reliable Lead Time** is the last passing k (0 if k = 1 fails).
- **Also reported at every lead:**
  - pooled accuracy
  - HIGH precision, recall and F1
  - weighted F1
  - AUC-ROC (the same as E168, since `p` is unchanged)
  - persistence comparison

## Decision rule (fixed now)
E172 replaces E168 as the thesis model only if both hold:
1. Its Maximum Reliable Lead Time under Algorithm 3 is ≥ 1.
2. At every passing lead, its mean fold accuracy is above persistence's.

Otherwise E168 stays. The thesis reports that MRLT = 0 under Algorithm 3, together with both results.
