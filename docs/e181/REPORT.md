# E181: exploratory search over synthetic-augmentation variants. Report

> **EXPLORATORY.** The variants were ranked on the same 72 real outer rows they are reported on, so the best numbers
> here are optimistic. The chronological checks are the honest estimate. E168 stays in production; nothing was
> registered or promoted.

**What ran.**
- **Variants.** 129 variants: every E179 augmentation setting plus "none" (E168). Each is E168's selected
  configuration with one fixed setting.
- **Seeds.** Each variant is averaged over generator seeds 17901–17905. Synthetic rows were never scored.
- **Reproduce:** `cd backend; python -m app.e181.search run` (about 30 min), then `python -m app.e181.search report`.

## 1. The pre-registered "balanced" rule (`docs/e181/PROTOCOL.md`)
- **Rule.** A variant is eligible only if its HIGH recall is at least E168's (0.88) at both leads. Eligible variants are
  ranked by mean balanced accuracy, then by Brier.
- **Eligibility.** Only **7 of 129** variants keep HIGH recall at 0.88 at both leads, and one of them is E168 itself.
- **Winner.** Jitter, 0.25× rows, weight 0.2, noise 0.5 SD, near the 50 % line.

| | Accuracy L1 / L2 | Balanced acc. L1 / L2 | HIGH recall | Brier L1 / L2 |
|---|---|---|---|---|
| E168 | 75.0 % / 77.8 % | 0.780 / 0.802 | 0.88 / 0.88 | 0.1230 / 0.1221 |
| Winner | 75.0 % / 77.8 % | 0.780 / 0.802 | 0.88 / 0.88 | 0.1207 / 0.1204 |

- **Result.** The same accuracy and the same classifications as E168. The Brier score is slightly lower (−0.0023
  [−0.0061, +0.0011]; −0.0017 [−0.0048, +0.0011]).
- **Chronological check.**
  - Choosing on 2018 picked "none" for 2019.
  - Choosing on 2018 + 2019 picked the winner for 2021.
  - On the 2019 + 2021 rows the procedure's accuracy equals E168's (78 % / 82 %), with a slightly higher Brier.
  - **Under this rule, searching gives no real gain.**

## 2. Higher-accuracy variants exist, but they trade HIGH recall
- **How many.** 32 of the 129 variants have higher mean accuracy than E168 on the 72 rows.
- **The highest.** SMOTE, 2× rows, full weight, near the 50 % line: **81.9 % / 79.2 %**, but HIGH recall 0.84 / 0.80.
- **How they gain.** They gain accuracy mainly by calling fewer provinces HIGH: fewer false alarms, and more missed
  HIGH provinces.

## 3. Post-hoc check without the recall floor (not in the protocol)
After the results above were seen, the recall floor was dropped. The variant with the highest mean balanced accuracy
was then selected on earlier rounds only and tested on the next round (`post_hoc_nofloor.json`).

- **Both selections picked the same variant:** jitter, 2× rows, full weight, noise 0.5 SD, near the 50 % line.
- **On the held-out rounds (2019 + 2021, 50 rows per lead).**

  | | Accuracy L1 / L2 | Balanced acc. L1 / L2 | HIGH recall L1 / L2 | Brier L1 / L2 |
  |---|---|---|---|---|
  | E168 | 78 % / 82 % | 0.791 / 0.821 | 0.82 / 0.82 | 0.110 / 0.109 |
  | Selected | **80 % / 84 %** | **0.806 / 0.850** | 0.82 / **0.88** | 0.114 / 0.112 |

- **The same variant on all 72 rows (optimistic, because it was selected on them).**

  | | Accuracy L1 / L2 | Balanced acc. L1 / L2 | HIGH recall L1 / L2 | HIGH precision L1 / L2 | False alarms L1 / L2 | Brier L1 / L2 |
  |---|---|---|---|---|---|---|
  | E168 | 75.0 % / 77.8 % | 0.780 / 0.802 | 0.88 / 0.88 | 0.595 / 0.629 | 15 / 13 | 0.1230 / 0.1221 |
  | Variant | **79.2 % / 79.2 %** | **0.803 / 0.812** | 0.84 / 0.88 | **0.656 / 0.647** | **11 / 12** | **0.1212 / 0.1199** |

  - Brier difference: −0.0018 [−0.012, +0.007] at Lead 1 and −0.0022 [−0.011, +0.006] at Lead 2.
  - Exact McNemar test: 5 rows right only for the variant against 2 only for E168 (p = 0.45) at Lead 1; 2 against 1
    (p = 1.0) at Lead 2.

**Reading.**
- **Most promising signal.** This is the most promising signal in E178–E181: a gain that survives a forward-in-time
  check. It is still about one province per lead out of 50, not statistically significant, and its Brier score on the
  held-out rounds is slightly worse than E168's.
- **Missing controls.** The leakage and shuffled-trigger controls were **not** run for this variant.
- **Status.** The rule that found it was chosen after seeing the results, so it is a **hypothesis for the next real
  test**, not a demonstrated improvement.
- **How to confirm it honestly:**
  1. Seal this variant's ENNS 2022 forecasts now, alongside E168, E179 and E180.
  2. Run its leakage and shuffled controls.
  3. Score it when FNRI publishes the ENNS 2022 provincial results.
