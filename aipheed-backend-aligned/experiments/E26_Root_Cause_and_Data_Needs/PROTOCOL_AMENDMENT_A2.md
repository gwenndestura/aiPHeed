# E26 Protocol Amendment A2: signal-requirement scenarios in the horizon simulation

**Written 2026-10-14, before running these scenarios. Synthetic paths only; no outcome of any kind is used.** It adds scenarios to section D. The baseline scenario and every other rule are unchanged.

**Why.** The baseline horizon shows that even a correctly specified forecaster barely beats calibrated persistence, because the fitted regional hunger process is close to a random walk. The question is therefore what information would be needed: a fresher reading, or a leading signal of a given strength.

**Scenarios.** Same paths, seed, labels and baselines as the baseline:

| Scenario | Content |
|---|---|
| **S0** | Baseline (the forecaster sees rounds ≤ t−1 at O(t)) |
| **S_timely** | The forecaster also sees the round of quarter t at O(t), one quarter fresher. The labels used by persistence stay as in S0, because the label of t still needs D(t) complete. This mirrors the VOI set I1. |
| **S_signal(ρ), ρ ∈ {0.3, 0.5, 0.7, 0.9}** | The forecaster sees, at O(t), a standardized leading signal z whose correlation with the unknown regional change from the last published round to the target quarter is ρ, and uses it optimally (Gaussian conditioning) |

**Reported per scenario and year end:**

- P(evaluable);
- P(claim) under the frozen e-process rule and under amendment A1 (accuracy and Brier, both baselines);
- the mean per-date score advantage.

The horizon outputs then state the **minimum signal strength or timeliness** that would make a valid claim plausible within a stated number of years.
