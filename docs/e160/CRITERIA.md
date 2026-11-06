# E160: provincial ranking and LGU priority correction. Criteria fixed before results.

Written 2026-11-06. The owner's prompt calls this "E159". That number already holds the ranking test (`docs/e159`), so this work is E160.

## What was seen before this was written
- The E159 ranking test results for **E158 and PERS (latest survey)** on the same 72 Lead 1 rows. PERS ranked better within regions. This motivated the arms below, so **any arm built from the latest survey has a hindsight advantage.** Rounds 2018, 2019 and 2021 have been read many times, and every result here is retrospective.
- The 2027-Q1 calculation trace (`backend/data/e160/out/trace.json`).
- **No result for any new arm.**

## Arms (fixed; no others will be added after results)
All arms use only survey rounds released at the issue quarter. A round counts as released when its reference quarter + `ANCHOR_LAG` (6 quarters) ≤ issue quarter, the same rule as E158.

`N[s]` is the national level of round `s` (two-way fixed effects, precision-weighted) from the `Hier2` fit on the released rounds.

| Arm | Formula (logit scale) | Uses quarterly triggers and news |
|---|---|---|
| **E158** | as is: shared + structural level + shrunk deviation + LightGBM residual | yes |
| **PERS** | latest released survey of the province | no |
| **RP** (relative persistence) | latest survey − `N`[its round] + `N`[last released round] | no |
| **OH** (own history) | `N`[last] + w × precision-weighted mean of the province's own (y − `N`[round]) over released rounds. w = τ²/(τ² + 1/Σ(1/v)), v = se² + σ². τ² and σ² are estimated from those relative values exactly as `Hier` estimates them. This is `Hier` without the structural level | no |
| **RP+R** | RP + `Res2(E158.COLS)` fitted on the training as-of errors of RP | yes |
| **OH+R** | OH + `Res2(E158.COLS)` fitted on the training as-of errors of OH | yes |

- **Residual arms** use E158's training rows, columns, seed, tree grid and interval method.
- **Probabilities:** `norm.cdf(mu/sd)`. For residual arms, `sd` comes from `Res2.scale`. For RP and OH, `sd` is the RMSE of the training errors, as PERS uses.
- **HIGH threshold:** 50, unchanged.

Validation: the E158 protocol, with surveys ENNS2018, ENNS2019 and ENNS2021 and leads 1 to 4. **Lead 1 is primary.**

## Measures
1. **Class:** accuracy, precision, recall, F1, AUC, Brier, and E156 criteria C1 to C6.
2. **Ranking:** the E159 measures, on the same pairs, seed 159 and bootstrap:
   - within-region concordance (pairs in the same region and round), with the gap ≥ 5 points sensitivity;
   - within-round Spearman.
3. **Most vulnerable province:** in region-rounds with 3 or more provinces (6 clusters at Lead 1), whether the arm's top province is the observed top. Reported only, with no gate, because n = 6.
4. **Differences kept:** the median over region-rounds with 2 or more provinces of sd(predicted %) / sd(observed %). A value of 1 keeps the observed spread; near 0 means the provinces are treated as interchangeable. Reported only.

## Gates for adopting a replacement (Lead 1)
An arm can replace E158 only if it is **RP+R or OH+R**: the five trigger groups and news must stay in the model. It must pass all four gates:
- **G1:** within-region concordance, 95 % interval lower bound > 0.5.
- **G2:** within-round Spearman > 0 in all 3 rounds.
- **G3:** not worse than E158 on Brier. The bootstrap interval of the difference (`E7.diff_ci`, region clusters) must not lie entirely above 0.
- **G4:** C3 holds (HIGH and LOW recall ≥ 0.5).

If both pass, the one with the higher within-region concordance wins; on a tie, the lower Brier. If neither passes, E158 stays, and **the provincial order is not validated for display.**

## 2027-Q1 display rule
- Every arm's live scores are computed for the five provinces at issue 2026-Q4, Lead 1.
- **Uncertainty of the order:** P(each province is highest), from 10,000 normal draws per province.
  - The sd for ranking is `sd × sqrt(1 − 0.726)`. 0.726 is the share of error variance shared within region and round, from the E156 audit.
  - Shared error moves all five together and does not change their order.
  - Seed 160.
- **If an arm is adopted:** show its order, labelled "retrospective validation", with P(highest).
- **If not:** show the five as one group classification with each score's 90 % range and P(highest), and **no rank numbers.**

## LGU priority, fixed rule (LGU-v2)
The old rule is `priority = province P(HIGH) × vulnerability`. Its problem is that a province probability near 0, driven by an unvalidated provincial order, can outweigh LGU poverty.

The new rule:
1. **Tier:** LGUs in provinces classed HIGH come first, then LOW. This is the provincial context, used only through the class, which is the validated part.
2. **Within a tier:** sort by vulnerability = 0.6 × poverty percentile + 0.4 × density percentile. These are the owner's recorded weights, unchanged (PSA SAE 2021 poverty, POPCEN 2024 density).
3. **Province score and P(HIGH)** are shown as context columns. They are not multiplied in.
4. **If an arm passes the gates,** its province score breaks exact ties in vulnerability. Nothing else changes.

No municipal food-insecurity label is created. The output is labelled "vulnerability-weighted priority; not a municipal food-insecurity measurement or forecast". The old and new top 20 are compared, and every LGU that enters or leaves is listed with the reason.

## Leakage and chronological checks
1. **Assertion:** every round used by any arm at issue `i` satisfies RQ + 6 ≤ `i`.
2. **Corruption test, Lead 1:** replace the `y` of every round not released at `i` (including the target round) with random values. Every arm's forecasts must be unchanged to 1e-9.
3. **Quarterly inputs** are E158's, which already passed the E156 test for corrupting data after the issue quarter. That test is not repeated.

## Not allowed
- Adding arms after results.
- Changing gates, the 5-point cut, the 0.726 share or the LGU weights.
- Hardcoding or nudging any province.
- Changing the threshold.
- Changing production, the dashboard or the API.
