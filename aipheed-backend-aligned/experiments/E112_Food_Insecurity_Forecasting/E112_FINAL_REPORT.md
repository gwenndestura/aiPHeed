# E112 Final report: answers to the twelve questions

**Status.** These are development results. Every quarter scored was already seen in E109–E111. The rules were frozen before E112 scoring (`PROTOCOL.md` sha `77c3d9e2…`, plus `ADDENDUM_1.md` for the two Objective-4 baselines, hashed before they were scored).

## 1. Which root causes were resolved?

| Root cause | Status |
|---|---|
| Sparse news (2–7 admitted headlines per quarter) | **Resolved.** Dense indicators from all 9,485 de-duplicated headlines, 0% missing. |
| Noisy relevance filter | **Resolved.** A transparent category lexicon replaces it. |
| Seasonality and coverage drift in news | **Resolved.** Coverage-normalised shares and year-over-year change. |
| Lead mislabelled vs data age | **Resolved.** True horizon recorded per forecast. |
| Composite or price targets mistaken for food insecurity | **Resolved.** T43 and price pressure discontinued as outcomes. |
| Missing Objective-4 baselines | **Resolved.** PSA-only and linear-regression baselines added (Addendum 1). |
| 20 noisy regional quarters, survey-design change | **Not resolvable with existing data** |
| No provincial or municipal outcome | **Not resolvable with existing data** |
| No unseen confirmation | **Not resolvable with existing data.** Pending the sealed prospective scoring. |

Details: `E112_ROOT_CAUSE_AUDIT_AND_DECISION_RECORD.md`.

## 2. What is the final methodology, and why is it simple?

- **Outcome:** forecast SWS Balance Luzon hunger (continuous).
- **Information:** only what was published before the issue date.
- **Adopted forecast:** the latest published reading, labelled with its true horizon (Lead 1 = 2 quarters past the newest survey) and its typical error (about 3.7 points).
- **Research model, run beside it:** the 12-family LightGBM with six dated news indicators.

It is simple because it has one outcome, one adopted rule, one fixed research model, one news representation and one frozen evaluation rule. There are no composite targets or thresholds. Diagram: `E112_FINAL_METHODOLOGY.md`.

## 3. What does news contribute, and is it measurable?

**It is measurable:**
- every quarter has category volumes, shares and direction, dated and cut at the issue date;
- disaster news is validated against typhoon counts (ρ = 0.81) and coincides with hunger changes in the corpus (ρ = 0.76);
- one advance-warning association (agricultural supply → next quarter's hunger change, Holm p = .074) meets the pre-registered rule, but it is not replicated in GDELT.

**Forecast contribution: none demonstrated.**

| Test | Result |
|---|---|
| News-only vs RW | Lead 1: 3.52 vs 3.72, p = .36 |
| Ablation (LightGBM with vs without news) | +0.01 points |
| Contribution of any category | Holm p = 1 |

## 4. Does the system forecast actual food insecurity?

**Yes, at the regional level.** The target is SWS experienced hunger for Balance Luzon, a direct food-insecurity measure. It is not price pressure or poverty.

**Not at the provincial or municipal level.** No outcome exists there.

## 5. Does it outperform the baselines?

**Against persistence:** no. The proposed LightGBM is worse than the latest reading at every lead (Lead 1: 4.04 vs 3.72).

**Against the other baselines:**
- it beats PSA-only at Leads 2–4 and linear regression at Leads 1, 2 and 4, in point estimates only (Holm p ≥ .82);
- the news-only model is the most accurate at Lead 1, but not significantly.

## 6. Does it generalize across quarters?

**No.**
- Gains appear only in the 2024 surge.
- Losses follow after the 2025 survey change, in falling-hunger quarters (LightGBM +2.6 points worse than RW) and in the last 4 quarters.
- The news ridge does not generalize across the four SWS areas.

## 7. Can it anticipate surges?

**Not reliably.**
- Lead 1 has only 2 sharp increases: RW missed both; NEWS-C and LGBM12N caught 1 of 2; every method missed 2025-Q3 except MA2.
- At Lead 2, warnings come with as many false alarms as hits.

Too few events support any claim.

## 8. Which indicator families add value?

**None** passes the removal test (Holm p = 1 at Leads 1–2).
- Seven families are never used at Lead 1 by the depth-1 trees: V1, C1, C2, E1, E2, N1 and H1.
- Price news, A3 and C1 help slightly in point estimates; A2, C4, E1 and jobs news hurt slightly. None is significant.

## 9. What is the maximum reliable forecast horizon?

**None established.** There is no provisional lead either.
- Leads 2–4 have fewer than 8 evaluable quarters.
- E111's panel near misses (ASYM at Lead 1, LLR at Lead 2) remain exploratory.

## 10. Are the Chapter I objectives achieved?

| Objective | Status |
|---|---|
| 1 | **Partially** (pipeline and measurable news; no predictive gain) |
| 2 I–IV | **Partially** (computed; the classification metrics are degenerate on a one-class outcome) |
| 2 V | **Not demonstrated** |
| 3 | **Not achieved** as specified (no validated provincial forecast or LGU outcome) |
| 4 | **Achieved as a comparison** (the proposed model is not superior) |
| 5 | Not assessed here |

Details: `E112_OBJECTIVES_ASSESSMENT.md`.

## 11. What can DA IV-A responsibly use?

**Usable now:**
- **The regional hunger outlook.** It is the latest SWS Balance Luzon reading, with its true horizon ("two quarters past the newest survey") and a typical error of about ±3.7 points, not a validated prediction.
- **The news context panel:** dated counts and shares of disaster, supply, price and assistance headlines, as situational awareness. Disaster coverage is validated against the typhoon record.
- **The LGU table as a vulnerability ranking** (poverty and density), explicitly not as a forecast of local food insecurity.

**Not usable now:**
- any provincial or municipal food-insecurity forecast;
- any lead-time claim;
- any HIGH/LOW alert presented as validated.

## 12. What evidence is still missing?

1. **Unseen outcomes.** SWS rounds from 2026-Q4 onward, to score the sealed E109–E112 forecasts (`runner/score_prospective.py`). About 8 quarters are needed for a confirmatory Lead-1 test.
2. **Local outcomes.** CBMS 2024 LGU food-security aggregates, to validate the municipal ranking.
3. **Provincial outcomes.** A provincial FIES or hunger series, e.g. FNRI ENNS/NNS, for any provincial forecast.
4. **News replication.** Prospective replication of the agricultural-supply association. Full-text or severity-scored news with stable coverage would also help.
5. **Survey comparability.** Adviser-approved handling of the 2025 SWS respondent-base change.
