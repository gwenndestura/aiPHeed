# E193: E184 with converged synthetic averaging (100 draws). Fixed before results. Local only.

Written 2026-11-10 at the owner's request ("do better"), after E192.

## Rationale
- **E184's synthetic augmentation is a Monte Carlo procedure.** Its forecast is the average over random synthetic
  draws, and E184 uses only 5 (seeds 17901–17905).
- **That makes it noisy.**
  - Single-draw accuracy varies by 3–6 points (E191).
  - The same generator gave 80.6 % or 75.0 % at Lead 2 depending only on the random stream (E192).
- **The intended quantity is the expectation over draws.** E193 estimates it with 100 draws (seeds 17901–18000).
  Everything else is E184 exactly: method, frames, E168 selection and calibration, one job per (survey, lead).

## Adoption rule (fixed now, so the result cannot be cherry-picked)
- **E193 is the converged estimate of E184, not a new candidate.** It is reported and adopted as "E184 (converged)"
  whatever its accuracy, higher or lower.
- **Serving.** No change to what is served without the owner's decision.

## Reported
- Leads 1–6, 72 real rows per lead.
- Accuracy, false alarms, misses, Brier, balanced accuracy and the owner rule.
- Paired comparisons with E184's 5-draw rows: McNemar and Brier CI.
- **Convergence curve:** accuracy and Brier of the running mean after 5, 10, 20, 50 and 100 draws.
- **Distribution of single-draw accuracy:** mean, SD, minimum and maximum. This shows how much luck a single 5-draw
  result can hold.
