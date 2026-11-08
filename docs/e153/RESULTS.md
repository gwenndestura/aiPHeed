# E153 results: optimisation under overfitting control

**Verdict: not adopted under the rule fixed in advance. Accuracy fell to 0.694 (50 of 72), and Brier is worse than the E151 required model.** E151 stays. Production is unchanged. One run; the code refuses a second. Retrospective, fourth look at these rows.

| Lead 1, 72 rows | E151 required | E153 |
|---|---|---|
| Correct | 52 (0.722) | 50 (0.694) |
| HIGH recall | 0.76 | 0.92 |
| LOW recall | 0.70 | 0.57 |
| False alarms | 14 | 20 |
| AUC | 0.855 | 0.853 |
| Brier | 0.172 | 0.188 |
| Error (points) | 8.05 | 8.89 |

E153 - E151, Brier: +0.016 [+0.002, +0.030]. E153 - persistence: -0.060 [-0.111, -0.018].
By round: 2018 0.545, 2019 0.64, 2021 0.88 (above always-LOW's 0.84, but that round alone).

## Overfitting measures

1. **Held-out error is 3.4 to 4.8 times in-sample error,** even with depth at most 3. There is far more capacity in the trees than signal in the inputs. Tuning chose 7 leaves, the largest offered, with a low weight on the result in 2018 and 2019.
2. **Seeds are stable:** 0, 0 and 2 rows change class across seeds, so randomness in fitting is not the problem.
3. **Shuffled inputs reach nearly the same accuracy.** The same settings fitted to training errors shuffled within round and lead reach 0.707 on average (95th percentile 0.736). 80 % of those runs did at least as well as the real E153.

## What the third measure means

Shuffling breaks the link between inputs and errors, but keeps their average. So a model with no input signal still learns one thing: **the anchor runs too high, and scores should come down by about the average training error.** That alone lifts accuracy from the anchor's 0.639 to about 0.71.

**So most of the accuracy gain over the anchor appears to be a level correction, not information from the inputs.** The E151 required model's 0.722 is within the shuffled range, and the Lead 4 figure of 0.75 is only slightly above its 95th percentile. Those settings differ from E151's, so this is an indication and not a direct test of E151.

This is consistent with the E151 diagnosis: inputs do not improve ranking between provinces within a round. The inputs' value for provincial class accuracy is **not shown.** E151's other findings do not depend on it: SWS area-level skill, and the improvement on old surveys, which the level correction helps explain.

## Decision

E151 required model stays. **More tuning cannot fix a shortage of information.** New evidence needs a new FNRI round, SWS releases, and inputs that carry real differences between provinces.

Files: `docs/e153/PROTOCOL.md`, `backend/data/e153/out/{results.json, oof.csv, lock.json}`.
