# E32: a new forecasting model built on the E31 improvements

**Date:** 2026-10-15.
**Branch:** `e31-chapter1-completion`.
**Folder:** `aipheed-backend-aligned/experiments/E32_New_Model/`.
**Read first:** `PROTOCOL.md` (frozen: sha `8bea43d2…`, git `4e0531f`) and `DEVIATIONS.md`.

## 1. Answer

- **A genuinely new model was built and genuinely retrained.**
  - E32-PCFN is a new engine; three further candidates were built beside it.
  - It is not PCF21 or P45 renamed, and no existing prediction was reused for it.
  - At every walk-forward origin it was refitted on the history available then, and finally retrained at the operational origin 2026-10-01.
- **It is not more accurate than what already exists.**
  - Under the pre-registered selection rule, E32-PCFN was chosen.
  - It **fails acceptance** on the development walk-forward (lead 1, 10 dates, 50 rows):

    | Criterion | E32-PCFN | Comparator | Result |
    |---|---|---|---|
    | A1: Brier below PCF21 | 0.1007 | PCF21 0.0946 | Fails |
    | A2: Brier no worse than persistence | 0.1007 | persistence 0.1000 | Fails |
    | A3: accuracy ≥ 0.75 | 0.86 | — | Passes |

  - **It is therefore not served.** PCF21 remains the served engine.
- **The 75% requirement.**
  - E32-PCFN reaches 0.86 accuracy (95% CI 0.76–0.96). Every E32 candidate exceeds 75%.
  - Always-HIGH reaches 0.92 and persistence 0.90.
  - No candidate beats persistence or always-HIGH with any statistical support (best: E32-ENS vs PCF21, Brier gain 0.0015 per date, p = 0.39).
  - The requirement is met only in a form that a constant forecast also meets. **That is not evidence of forecasting skill.**
- **No result here comes from an unseen evaluation period.**
  - Every scored quarter (2023-Q4 to 2026-Q3) had been examined earlier.
  - The unseen test is **prospective**: predictions for 2026-Q4 and 2027-Q1 were frozen at git `c9bba1f` (sha `37e0d66b…`) before those outcomes exist.
  - They will be scored with `runner/e32_score_prospective.py` after the SWS December 2026 round.

## 2. What E31 changed that can reach a model (PROTOCOL §1)

| Change | Reaches the model? | Effect measured in E32 |
|---|---|---|
| Validated news gate (R1.1) and FSSI-v2 | Yes: `news_n`, `news_reg`, `news_direct_share`, `fssi_v2` | **Small.** Next-quarter correlations: ρ 0.24 (p .02) for news count vs S1, which may share a time trend; FSSI vs D not significant. PCFN's news coefficient on D is negative and unstable. |
| Verified SWS posting dates and September 2026 round | Yes: as-of H, τ and labels | One more labelled quarter. Persistence is now correctly publication-aware. |
| PSA CPI to September 2026 | Yes: D, Dnow | Current inputs at the operational origin |
| New in E32: provincial rice CPI | Yes: `rice_rel` | Used by PCFN, LR and LGBM; no measurable gain |
| Forecast/nowcast alignment | Yes (timing) | Forecast features use quarter-t news for target t+k |
| Dashboard, API, alerts, schema, PDF | **No** | Not claimed as a model improvement |

## 3. Why previous models failed, and what E31/E32 resolves (`runs/e32_diagnosis.json`)

| Cause | Measured | Resolved by E31/E32? |
|---|---|---|
| Regional hunger dominates the label | 70% of S1 variance is between-quarter | **No** (target design) |
| Little provincial outcome variation | 6/10 quarters have all five provinces sharing the label; the persistent between-province part of D is 3.6% | **No** |
| Class imbalance | 46 HIGH / 4 LOW. HIGH share rose from 0.47 (2022) to 0.95 (2024) as hunger rose from 11% to 20% and the trailing-median τ lagged behind | **No** |
| Few observations | 10 evaluable dates; one H per date | **No.** Only time adds dates |
| Latest hunger unknown at the origin | 90% of rounds are posted after the next quarter starts (median 27 days) | **No.** It is structural to a quarterly forecast |
| Weak news signal | Weak, non-significant links | **Partly.** E31 made the signal valid; it is still weak |
| Leaky or mis-timed inputs | Fixed: verified dates, as-of features, a scramble-the-future test | **Yes** |
| Persistence baseline given unpublished labels (`cycle.reference_probabilities`) | Found in E32 | **Yes.** Fixed in E32 and in the E31 ledger code |
| Oracle bound | Knowing H gives 0.96 accuracy; knowing D gives 0.94 | The error is the unknown next hunger round |

**Alternative targets** (`runs/e32_alt_targets.json`; exploratory, not adopted):

| Target | HIGH/LOW | Quarters with all provinces on one label | What it measures |
|---|---|---|---|
| T1 approved | 46/4 | 6/10 | Food stress composite |
| TR "rising" (Chapter I 1.2) | 38/12 | 6/10 | Still moves with regional hunger |
| T2 D > 0 | 24/26 | **0/10** | Prices, not food insecurity |

No target gives both provincial discrimination and a food-insecurity meaning. Any target change needs the adviser.

## 4. Development comparison (identical rows, E32 labels, lead 1)

| Arm | Selection, 7 dates: accuracy | Brier | Development test, 3 dates: accuracy | Brier | All, 10 dates: accuracy | Brier |
|---|---|---|---|---|---|---|
| **E32-PCFN (selected)** | 0.829 | 0.123 | 0.933 | 0.047 | 0.86 | 0.101 |
| E32-ENS | 0.886 | 0.120 | 1.000 | 0.031 | 0.92 | 0.093 |
| E32-LR | 0.857 | 0.132 | 0.933 | 0.032 | 0.88 | 0.102 |
| E32-LGBM | 0.829 | 0.175 | 0.933 | 0.032 | 0.86 | 0.132 |
| PCF21 | 0.857 | 0.115 | 0.933 | 0.046 | 0.88 | 0.095 |
| P45 (common rows) | 0.800 | 0.147 | 0.900 (2 dates) | 0.116 | 0.822 | 0.140 |
| Persistence | 0.857 | 0.143 | 1.000 | 0.000 | 0.90 | 0.100 |
| Always-HIGH | 0.914 | 0.086 | 0.933 | 0.067 | 0.92 | 0.080 |

**Lead 1, all dates, other metrics:**

| Arm | Precision | Recall | F1 | ROC-AUC | TP/FP/TN/FN |
|---|---|---|---|---|---|
| E32-PCFN | 0.95 | 0.89 | 0.92 | 0.76 | 41/2/2/5 |
| PCF21 | 0.95 | 0.91 | 0.93 | 0.76 | 42/2/2/4 |

AUC is UNSTABLE: there are 4 LOW rows.

**Lead 2** (8 dates; two early dates are not computable for PCF21):

| Arm | Brier |
|---|---|
| Always-HIGH | 0.050 |
| E32-ENS | 0.106 |
| E32-PCFN | 0.120 |
| PCF21 | 0.128 |
| P45 | 0.129 |

- **Per province** (10 rows each; descriptive): E32-PCFN accuracy ranges from 0.7 (Batangas) to 1.0 (Rizal).
- **Per quarter:** persistence is perfect wherever the label did not change.

**E32-ENS observation:** it would have passed A1 and A2. It was not selected under the pre-registered tie rule, and it is **not** promoted after seeing the results. It is frozen prospectively with the others, so the 2026-Q4 outcome can test it.

## 5. Deliverables

| # | Deliverable | Where |
|---|---|---|
| 1 | Retrained model and artifacts | `models/E32-PCFN_O2026-10-01.json` (parameters, feature definitions, configuration, dataset version); `models/E32-LR_*.joblib`; `models/E32-LGBM_*.txt` |
| 2 | Comparison vs PCF21, P45 and persistence | §4; `runs/20261014T165201Z/results.json` (repeat `…165320Z`, byte-identical) |
| 3 | Audit trail | Protocol and deviations; the ledger below; input hashes in every result |
| 4 | Tests | `tests/`: 16 passed. They cover data timing (scramble-the-future), features, training pairs, publication-aware references, artifact = frozen prediction, inference recompute, operational-origin inputs, reproducibility and selection/acceptance logic. API integration is not tested because the model is not served. |
| 5 | Dashboard with the new model | **Not integrated:** acceptance failed (PROTOCOL §6) |
| 6 | Report | This file |
| 7 | Retrained? Data? Unseen? | §1. Data: E31 vintage-2 inputs (SWS 2021–Sep 2026 with verified dates; PSA food CPI 2021–Sep 2026); E31 validated news; PSA rice CPI 2021–Sep 2026. Unseen periods: none yet (prospective). |

## 6. Ledger

| Step | Git | Note |
|---|---|---|
| Diagnosis, rice data, protocol frozen | 4e0531f | before any fit |
| Code, deviations A1–A7, timing tests | 9be810d | before any score |
| A8 (evaluable dates) | in c9bba1f | after a crash that produced no score |
| Evaluation run ×2 and prospective freeze | c9bba1f | predictions sha 2dd0b51a; frozen sha 37e0d66b |

## 7. Next steps

1. When the SWS December 2026 round and October–December CPI are released, the researcher authorizes them.
2. Write `inputs/AUTHORIZED_OUTCOMES.csv`, then run `runner/e32_score_prospective.py`.
3. ~~Fix `cycle.reference_probabilities`~~ **Done:** it now takes `rounds`/`origin`, and the cycle passes them (E31 `backend_dev`; test `tests/test_e32_reference_fix.py`).
4. Adviser decision on the target (§3). A model cannot create the provincial variation the approved label lacks.
