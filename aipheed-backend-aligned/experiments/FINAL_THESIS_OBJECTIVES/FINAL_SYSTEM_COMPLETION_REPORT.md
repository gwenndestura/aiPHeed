# Final system completion report

**Branches:** `aiPHeed/final-thesis-objectives` (Chapter I target, model, protocol, first run) →
`aiPHeed/firi-data-audit` (12-indicator data audit, audited rerun, serving, tests, documents). Not merged, not deployed.
Preserved untouched: `aiPHeed/final-system-completion`, `aiPHeed/final-objective-achievement`, E107–E114, all earlier seals.

## The ten acceptance questions

**1. What was wrong?** The work had drifted from Chapter I's dependent variable (province-quarter high/low risk from
SWS + PSA) to a regional hunger-change label that is noisy by construction; the Chapter I target had been scored on a
defective SWS series (commissioned round in, two regular rounds out); the persistence baseline was given older
information than the model; Lead 0 nowcasts were described as forecasts. The data audit then found three input defects
(BSP remittances, typhoon counts, a partial rice quarter) and a feature-cache bug that could hide corrections.

**2. What changed?** Target fixed to T43c (Chapter I definition, frozen E40 thresholds, verified SWS series). One model,
CH1-LGBM = P(hunger condition) × P(price condition from one 12-family LightGBM). Same-information baselines. One time
convention (issue on the first day of the quarter). Inputs audited and corrected via a frozen addendum. The dashboard
now serves this forecast (`AIPHEED_MAP_MODEL=firi` restores FIRI v2).

**3. Which objective does it address?** Objectives 2 (I–V) and 4 directly; 1 (news tested), 3 (rankings built on a
validated province forecast) and 5 (dashboard, FNRI face validity).

**4. Is 75% reached under valid evaluation?** **Yes at Lead 1:** 0.914 (90% CI 0.843–0.971), walk-forward, issue-date
information only, frozen target and rule, 70 province-quarters from 14 quarters. **No at Leads 2–4** (0.583, 0.520,
0.575).

**5. Does it beat the baselines?** At Lead 1: always-LOW 0.757, same-information persistence 0.743, climatology Brier
(p 0.008); significantly better Brier than LR-COMB, LR-GOV, LR-NLP, LGBM-NLP and persistence (Holm p < 0.001); ties
LGBM-GOV (the same model without news). H3 is therefore not rejected under the all-six rule.

**6. Does news help?** No. Neutral at Leads 0–1, significantly worse at Leads 2–3; a full-coverage regional FSSI
also gives no gain. News is shown as context.

**7. Maximum reliable horizon?** One quarter (up to 3 months). Leads 2–4 fail every accuracy criterion.

**8. What evidence supports the LGU ranking?** Its province input is validated at Lead 1 and its poverty/density
inputs are the official PSA figures. It has not been validated against municipal outcomes (none are open) and DA
evaluators have not yet assessed it (Hypothesis 4).

**9. Objective status.** 1 met as a pipeline, no predictive value; 2 I–IV met at Lead 1; 2 V determined (1 quarter);
3 ranking delivered, evaluation pending; 4 mostly met (5/6 comparators); 5 dashboard and face validity done,
ISO 25010 survey pending. See `THESIS_OBJECTIVE_ASSESSMENT.md`.

**10. What is defensible?** "A province-level high/low food-insecurity risk forecast, as Chapter I defines risk, is
correct 91% of the time one quarter ahead in 2023–2026 walk-forward testing, above the 75% target and above
persistence; it is not reliable further ahead; news did not improve it; LGU values are priority rankings." Not
defensible: municipal accuracy, measured provincial hunger, a two-quarter warning, a news benefit.

## Verification

| Check | Result |
|---|---|
| Backend test suite | 807 passed, 18 skipped |
| New tests (`test_api_ch1_risk.py`, `test_firi_data_audit.py`) | 19 passed |
| Frontend tests | 75 passed |
| Frontend production build | succeeded |
| Served rows = evaluated predictions | asserted in export and tested |
| Protocol / addenda hashes unchanged | tested |
| Seals | first run `e0bc1ec1…`, audited `be52d5c3…`, both intact |

## Documents

`ROOT_CAUSE_AND_METHOD_DECISION.md`, `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md`, `ADDENDUM_1_DATA_CORRECTIONS.md`,
`ADDENDUM_2_NEWS_COVERAGE.md`, `FINAL_LIGHTGBM_FORECASTING_RESULTS.md`, `NEWS_PREDICTIVE_VALUE.md`,
`MAXIMUM_RELIABLE_LEAD_TIME.md`, `LGU_VALIDATION_AND_PRIORITY_METHOD.md`, `FINAL_SIMPLE_METHODOLOGY.md`,
`THESIS_OBJECTIVE_ASSESSMENT.md`, and the seven files in `../FIRI_V2_DATA_AUDIT/`.

## Reproduce

```bash
cd aipheed-backend-aligned/experiments/FINAL_THESIS_OBJECTIVES/runner
python run_ch1.py audit && python run_ch1.py score && python run_ch1.py placebo && python run_ch1.py seal
cd ../../FIRI_V2_DATA_AUDIT/runner
python audit_build.py && python rerun_ch1.py && python news_coverage.py && python export_audited.py
```

## Pending (not data problems)

- ISO 25010 and Hypothesis 4 survey with DA Region IV-A evaluators.
- Scoring the sealed 2026-Q4 forecast when SWS publishes that round.
- Authorization to merge or deploy.
