# Deep analysis: can tuning, employment or remittances improve C-B6? (2026-11-04)

**Scope:** an owner-directed optimisation of the food-insecurity forecast (target: SWS Balance Luzon hunger > 11.3%;
62 verdict quarters, 2010-Q1..2026-Q3).

**Basis:** every number is development evidence. All tuning ran inside the walk-forward (past quarters only). Each
attempt was pre-registered and committed before its fit:
- `PLAN_CB6E.md`
- `PLAN_CB6E_OPT.md`
- `PLAN_STAB_TUNE.md`

## 1. Results of all optimisation attempts

| Model | What changed | Acc L1/L2 | Balanced | AUC L1/L2 | Brier L1/L2 | ECE L1 | R1–R7 |
|---|---|---|---|---|---|---|---|
| **C-B6 (served)** | — | **0.806/0.806** | **0.743** | **0.723**/0.712 | **0.183/0.181** | 0.184 | **all pass** |
| C-B6E | + E1, E2 | 0.790/0.790 | 0.717 | 0.698/**0.720** | 0.192/0.184 | — | R5, R7 fail |
| C-B6E-OPT | + 32-setting nested search, direction constraints | 0.774/0.774 | 0.705 | 0.697/0.718 | 0.191/0.184 | — | R5, R7 fail |
| T-B6 | 12-origin validation, 32 settings, top-3 average | 0.758/0.758 | 0.693 | 0.723/0.712 | 0.185/0.186 | 0.123 | R3, R7 fail |
| T-B6E | the same, + E1, E2 | 0.742/0.742 | 0.682 | 0.720/0.720 | 0.185/0.186 | **0.087** | R2, R3, R7 fail |

**Under identical tuning, E1 + E2 add nothing:** T-B6E − T-B6 Brier is +0.0003 (p 0.56), with 1 call changed.

**None of the tuned models is significantly better or worse than C-B6 on Brier** (p 0.59–0.71). They do change 3–4
HIGH/LOW calls, and most changes are wrong.

## 2. Why employment and remittances cannot help (with the data available)

**Pre-fit diagnostics** (Lead 1, Spearman, 62 quarters):

| Input | vs the label | vs the change from the latest SWS reading |
|---|---|---|
| E1, national unemployment change | +0.24 (p 0.06) | −0.07 (p 0.59) |
| E2, national remittance decline | −0.12 (p 0.34) | 0.00 (p 0.99) |
| h_last, the latest SWS reading | +0.34 (p 0.007) | **−0.41 (p 0.001)**: mean reversion |

1. **E1 tracks the hunger level, which the latest reading already carries.** It says nothing about the change, and the
   change is the only thing left to predict.
2. **Both signs flip across eras.** Versus the change, E1 is +0.04, −0.14 and +0.12 across 2010–15, 2015–20 and
   2021–26; E2 is −0.03, −0.11 and +0.15. A tree that learns a sign in one era is wrong in the next.
3. **Both series are national.** Balance Luzon hunger depends on local conditions that national unemployment and
   remittances average out.
4. **The only forecast E1/E2 changed** in C-B6E was origin 2018-Q3. It moved from 0.458 (correct LOW) to 0.530 (wrong
   HIGH). This is the same fragile forecast on which C-B6's R1–R7 pass depends.

## 3. Why careful tuning does not help either

1. **The selection is noisy whatever the method.**
   - Top-1 setting switches in the evaluation era: 26 (C-B6, 4-origin validation); 27 (T-B6) and 26 (T-B6E), with
     12-origin validation.
   - The best setting genuinely differs from quarter to quarter because the 62 quarters cross regimes.
2. **Tuning trades accuracy for calibration.**
   - The tuned arms are much better calibrated: ECE 0.184 → 0.123 / 0.087. Their probabilities mean what they say.
   - But they sit closer to 0.5, so 3–4 calls flip, mostly in the wrong direction.
   - On 62 quarters one flipped call moves accuracy by 0.016, and a third's accuracy by 0.048. That is enough to fail
     R3 or R7.
3. **C-B6's advantage is partly luck in one forecast.**
   - Removing any single quarter leaves C-B6's 2015–2020 third at a minimum of 0.600, exactly at the R7 line.

## 4. Where the remaining errors come from (C-B6, Lead 1, 12 errors)

| Source | Errors |
|---|---|
| 2015–2020 regime (hunger crossing 11.3% back and forth) | **8 of 12** |
| Labels within SWS sampling error (could flip by survey noise) | 6 of the 13 such quarters |
| Quarters where the label changed from the previous quarter | 5 of 13 |

- **On the 49 clear labels, C-B6 is 87.8% accurate.**
- The ceiling for a perfect forecaster of true hunger, given sampling noise, is about 0.925
  (`FORECASTING_FAILURE_ANALYSIS.md`).

## 5. Conclusions

1. **C-B6 remains the best model.** Every tuned or extended variant has lower accuracy and fails R1–R7. Per the
   pre-registered serving rules, nothing replaces it.
2. **Employment and remittances do not improve the forecast**, whether as plain inputs, with nested tuning, or with
   careful stable tuning. The cause is the data (national, sign-unstable, no information beyond the latest reading),
   not the tuning.
3. **The forecast is limited by the target, not the model:**
   - 62 quarters;
   - one regime break (2015–2020);
   - about 21% of labels within survey sampling error.

   More tuning on these quarters would only fit noise. This is the 29th attempt on them.
4. **What could genuinely improve it:**
   - regional (CALABARZON or Balance Luzon) labour and income data instead of national;
   - more labelled quarters (prospective seals from 2027-01-01);
   - a less noisy outcome (SWS microdata, or FNRI FIES rounds).
5. **For the dashboard:** if all five driver groups must be shown as model inputs, the least-bad option is C-B6E
   (accuracy 0.790, fails R5/R7). The thesis must then report that it does not meet the reliability rules.
