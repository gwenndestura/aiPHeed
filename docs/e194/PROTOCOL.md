# E194: averaging E184 over the top-5 inner-CV configurations. Fixed before results. Local only.

Written 2026-11-10 at the owner's request ("fix it"), after E193.

## Rationale
- **Selection noise.** E168/E184's Stage A picks one configuration out of 384 (anchor × feature set × pruning × 16 HPO
  settings) by real-row inner-OOF weighted SSE. On 156–532 rows, that pick is itself noisy.
- **Where it shows.** Most remaining non-structural errors are coin-flips (p between 0.45 and 0.55), where small
  differences between configurations decide the side.
- **The fix.** Averaging the best few configurations is a standard variance reduction, a form of Bayesian model
  averaging. It was not tested in E178–E193.

## Method (everything else is E184)
- **Configurations.** For each outer job (survey, lead): E168's Stage A on real rows, unchanged. Keep the **5
  configurations with the lowest inner SSE.**
- **Synthetic training.** For each configuration, E184's synthetic augmentation (jitter, 50/50, weight 1.0, 0.5 SD,
  boundary focus) and calibration, with **20 draws (17901–17920)**.
- **Forecasts.**
  - **E194 = the equal-weight mean of the 5 configurations' probabilities** (100 fits).
  - E194_k3 = the mean over the top 3 (secondary).
- **Reproduction check.** Configuration 1 with draws 17901–17905 must equal E184.

## Comparison and decision
- **Reference: E184 converged** (E193: 100 draws of configuration 1). The official 5-draw E184 is also shown.
- **E194 is preferred only if all three hold:**
  - accuracy ≥ E184-converged's at all six leads;
  - Brier ≤ E184-converged's at all six leads;
  - accuracy higher at at least one lead.
- Otherwise E184 stays.
- **Also reported:** McNemar, Brier CI and the owner rule. Whether Leads 1–3 reach 80 % is reported separately.
- **Scope.** Nothing is staged, committed or pushed.
