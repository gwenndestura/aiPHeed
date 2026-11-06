# E167: final correction of E166. Fixed before results.

Written 2026-11-06. The E165 gates F1–F10 are unchanged (`docs/e165/PROTOCOL.md` §5). **This is the last run.** E166 results and E158 seals are preserved.

## Diagnosis from E166's saved out-of-sample forecasts (no refitting)
| Failure | Where it comes from |
|---|---|
| **F5 bias +3.25** | **All of it is in 2018 (+6.8) and 2019 (+5.4)**, and almost all in provinces later observed LOW (+9.3 and +10.9). In 2021 the error is −2.0. National HFIAS fell from 56.2 % (2015) to 46.5 % (2018). At the 2018 and 2019 issues, training holds only 2013 and 2015 (57.6 and 56.2), so **no training-only method could see the 9-point national fall.** |
| **0.4–0.6 band** (20 rows, 15 % HIGH) | 17 of the 20 rows are 2018/2019 rows near the threshold, the same cause |
| **F7, 2021 at 80 % vs 88 %** | Two near-threshold provinces flipped: Occidental Mindoro (observed 56.3, forecast 41.8) and Surigao del Norte (observed 32.6, forecast 51.6). In 2021 the training-only selection **switched source from consumption to palay** |
| **C4 calibration** | The same drift spreads the logit-level errors |

**Source audit:** E166 chose the source per issue from training rows only. Consumption uses the E154 as-of rule (year Y public from Q3 of Y+1). PSA published 2024 regional household consumption in 2025, per a PSA regional office release. **2025 is not verified, so at the 2026-Q4 issue consumption is unavailable,** and nothing older is substituted.

## Correction (one procedure: E167)
The E166 procedure, with two training-only changes aimed at the diagnosed causes:
1. **Inner folds by survey round when training holds 2 or more target rounds** (leave-one-round-out), otherwise region GroupKFold(5). Inner validation can then see a round-to-round level shift where training data contain one, which happens at the 2021 issue.
2. **Calibration options inside the inner selection:** {id, lin, platt (soft, L2, C = 1)}. Selection is by **inner Brier of the calibrated probability.**

**Everything else is E166:**
- anchors {H, RP, OH, RSS};
- learners {NONE, RIDGE, ENET, RF, LGBM};
- {GOV, FULL} × {none + 5 sources};
- P(HIGH) ≥ 0.5.

**No province-specific or year-specific adjustment.**

## Controls (Lead 1)
- all trigger and source inputs shuffled across provinces (seeds 1–3);
- **consumption columns only** shuffled (seeds 1–3), to test consumption's incremental contribution;
- unreleased-round corruption.

## Decision
- **E167 passes F1–F10 (Lead 1):** freeze it as the approved candidate and prepare production integration, which needs the owner's go-ahead. **Lead 2** is reported as an extra capability only if it also passes independently.
- **Otherwise: E158 stays.** E166 and E167 are documented, and **no further model experiment is run on these rows.**
