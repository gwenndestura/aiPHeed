# E108 Deliverable E: maximum reliable lead-time decision

## Criteria (frozen before scoring: `PROTOCOL.md` §7, sha `fc3e42f9…`)

**Rule.** E107's R1–R7 and G1–G3, unchanged, plus a stricter G4:

| | Requirement |
|---|---|
| R1 | at least 6 quarters |
| R2 | accuracy ≥ 0.75 |
| R3 | accuracy above persistence and majority |
| R4 | Brier below persistence and climatology, sign-flip p < 0.10 |
| R5 | both recalls ≥ 0.5 |
| R6 | AUC ≥ 0.65 |
| R7 | 10–90% predicted HIGH |
| G1 | at least 2/3 of quarters with ≥ 3/5 provinces correct |
| G2 | better Brier in both halves |
| G3 | not worse than the naive baselines on the four most recent quarters |
| G4 | the same on the hunger-elevated quarters, where risk depends on prices |

**Classification.**
- **Reliable:** all criteria pass.
- **Inconclusive:** the point criteria pass, but only significance or the recent/half-period checks fail; or there are too few quarters.
- **Not reliable:** otherwise.

## Decision for the primary model F1 (factored LightGBM, all 12 indicators)

| Lead | Quarters (rows) | Accuracy | ≥ 75%? | Class | Criteria failed |
|---|---|---|---|---|---|
| 1 | 13 (65) | 0.892 (cluster CI 0.79–0.99) | **yes** | **inconclusive** | G3 only |
| 2 | 11 (55) | 0.691 | no | not reliable | R2, R3, R4, R5, R6, G3, G4 |
| 3 | 9 (45) | 0.622 | no | not reliable | R2, R3, R4, R5, G1, G2, G3, G4 |
| 4 | 7 (35) | 0.600 | no | not reliable | R2, R3, R4, R5, R6, G1, G2, G3, G4 |

- **Maximum horizon tested:** Lead 4 (four quarters). Longer leads leave fewer than 6 evaluable quarters.
- **Maximum horizon demonstrated reliable:** **none.** Lead 1 is the only horizon with supporting evidence.

**Why Lead 1 is inconclusive rather than reliable.** On the four most recent quarters (2025-Q4..2026-Q3: 1 HIGH row in 20), F1 scores 0.85 and Brier 0.104. "Always LOW" scores 0.95 and Brier 0.076. The gap comes from two false alarms in 2025-Q4, where price pressure was expected but disinflation came.

Every other criterion passes, including:
- R4: Brier 0.098 vs climatology 0.208, p = 0.064;
- G4 on the hunger-elevated quarters: accuracy 0.86, HIGH recall 0.81.

The rule was not relaxed.

**Same rule, other models** (post hoc, `out/rule_all_arms_posthoc.json`; 11 arms × 4 leads, so multiplicity applies):
- **Lead 1, inconclusive (G3 only):** F0, F2, STRUCT (the no-learning CPI projection) and E56 (the production LightGBM, 50 rows).
- **Lead 1, reliable:** the PSA-only logistic × H1 (Objective 4-II baseline): accuracy 0.892, HIGH recall 0.62, LOW recall 0.98, p = 0.081. It is the one arm that passes, out of 44 arm-lead checks, and it was not pre-registered as a decision. It shows that Lead-1 reliability is attainable with price information alone. It does not establish a reliable LightGBM horizon.
- **Leads 2–4:** every arm is not reliable. E107 at Leads 2–4 is "inconclusive" only because it has fewer than 6 quarters (R1); its accuracy there is 0.10–0.55.

## Why Leads 2+ fail (evidence, not a defect)

1. **The price signal is the CPI base-effect projection, and it fades.** On PS training labels, the projection's AUC falls from 0.92–0.95 at Lead 1 to 0.77–0.83 at Lead 2 and 0.53–0.69 at Lead 4 (`ROOT_CAUSE.md`). At Lead 2 the price part alone scores AUC 0.76 on PS, versus 0.84 at Lead 1 (`results.json` → `price_only_on_PS`).
2. **The other ten families do not replace it.** Ablations and permutation importance are in `INDICATOR_AUDIT.md` §4.
3. **Onsets are visible only one quarter ahead.** The 2024-Q2 onset is caught at Lead 1 (4/4) and missed at Lead 2 (1/5).
4. **The hunger factor cannot anticipate a hunger onset.** 2023-Q4 is missed at Leads 1 and 2, the leads that evaluate it, because the last SWS round sat exactly on 11.3%.

## What would be needed to support a longer horizon

- **More independent outcome quarters.** 19 SWS quarters gave 7–13 evaluable quarters per lead. Each additional year adds 4.
- **A provincial food-insecurity outcome**, for example CBMS food-shortage items or provincial FIES. The hunger condition is currently one regional value.
- **Leading price information beyond the latest index:** futures-like or wholesale-to-retail lead indicators, published import and tariff schedules, published before the issue date.
- **Unseen-quarter confirmation.** The sealed forecasts can be scored once SWS 2026-Q4 is published (expected around January 2027).
