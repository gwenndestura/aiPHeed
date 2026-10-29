# Lead 2: root causes, point-in-time audit, development experiment and decision

**Branch.** `aiPHeed/lead2-rootcause-research`, local only.

**Protocols.** Both were frozen before running:

| Protocol | SHA-256 (prefix) | Commit |
|---|---|---|
| `PROTOCOL_LEAD2_ROOTCAUSE_II.md` | 431cdefb | a4995d0 |
| `PROTOCOL_LEAD2_BIAS_TRACK.md` | 62e7ef8b | 0f744f0 |

**Runners.** `runner/lead2_rootcause.py` and `runner/bias_track.py`.

**Outputs:**
- `out/lead2_rootcause.json`
- `out/lead2_error_trace.csv`
- `out/pit_audit.csv`
- `out/bias_track.json`
- `out/lead2_experiment_log.csv`

**Unchanged.** The served model (P0H4, a498b5ef), the dashboard, R1-R7, the adoption rule, the target, the evaluation rows and the sealed files (dd293e2e…, 07c99e56…, b1edb799…).

## 1. Decision

**The available historical data do not currently support a reliable Lead-2 claim.** The maximum reliable lead remains Lead 1.

There are three measured blockers, in order of impact.

### 1.1 Weak price predictability two quarters ahead (main blocker)

- **Every error is a price-part error.** The price part causes all 13 of B0's Lead-2 errors.
- **The price moves after the issue.** In 10 of the 13 errors, the province's price margin crossed its threshold after the forecast was issued:
  - 6 rose above it;
  - 4 fell below it;
  - usually by less than 1.5 points.
- **The projection error is wide and drifts.**
  - At Lead 2 its spread is about 1.9-2.7 points, against 1.5-1.8 at Lead 1.
  - 77% of the evaluation rows have a realised margin inside one spread of the threshold.
  - The mean error drifts with the inflation regime:

    | Target year | 2022 | 2023 | 2024 | 2025 | 2026 |
    |---|---|---|---|---|---|
    | Mean error (points) | +4.5 | +2.8 | +1.9 | +0.2 | +1.8 |

- **No persistence signal.** Carrying the last known price condition forward scores 0.569, below always-LOW at 0.600.
- **Even an upper bound fails.** The best projection-based reference, given the evaluation period's own error distribution (an oracle), still recalls only 8 of 17 HIGH (0.47 < 0.60).

### 1.2 Too few independent HIGH outcomes to judge the criteria

- **Effective sample.**
  - 65 rows, but only 13 quarters and 7 HIGH quarters.
  - The shared regional hunger reading makes errors cluster: within-quarter ICC is 0.06-0.21, design effect 1.2-1.8, effective n 36-53.
- **R6 is a coin flip.**
  - Under quarter-cluster resampling, R6 passes in only **19-45%** of resamples for *every* candidate, including CR-ANC (day-10), which passes on the point estimate (44%).
  - Recall's 90% CI is about [0.25, 0.86].
  - Every pass or fail turns on one row: B0 is one hit short, and CR-ANC (day-10) has zero precision slack.

### 1.3 Unverified CPI timing

- CR-ANC's apparent gain exists only with refreshed CPI months whose release dates are not verified (`LEAD2_ASOF_REEVAL_REPORT.md`).

### 1.4 What would settle it

**Smallest missing evidence.**
- (a) Dated release sources for the 61 owner-reported and 79 unresolved province-months. That determines whether the refreshed-CPI gain is real.
- (b) Independent scored quarters beyond 2026-Q3, starting with the sealed prospective forecasts.

**How many quarters.** This is an illustration, not a measured requirement.
- HIGH quarters have arrived at about 7 in 13.
- Adding 3 more HIGH quarters, to about 10, would need roughly 6 more scored quarters, about 1.5 years.
- That would narrow the recall interval, but not to a guaranteed margin.
- More rows alone will not remove blocker 1.1: it is a property of how far ahead the price condition must be called.

## 2. Root causes, ranked by measured impact

| Rank | Cause | Evidence | Correctable now? |
|---|---|---|---|
| 1 | Price condition two quarters ahead depends on price moves after the issue | 10 of 13 B0 errors cross the threshold after issue; projection error SD ~2 pp with regime-dependent bias; label persistence 0.569 < 0.600; oracle reference recall 0.47 | No with current inputs: no timely leading signal. X1 (recent projection error) did not help (§5). |
| 2 | Few independent HIGH quarters; quarter-clustered errors | 7 HIGH quarters; R6 pass rate 19-45% under cluster resampling; one-row margins | No: needs future quarters |
| 3 | CPI release timing unverified for refreshed months | verified-only timing removes CR-ANC's gain (Brier −0.036 → −0.002) | Only by owner-collected dated sources |
| 4 | Low-resolution non-market inputs | E1, E2, H1, C1, G_pri: one value per quarter, zero between-province variance, ~18-20 distinct values; V1 a static province constant (5 values); N1 missing in 83% of Lead-2 rows | Partly: needs provincial and timelier series (not in the repository) |
| 5 | Hunger component | Accuracy 0.846 vs its own label; 0 of 13 B0 errors from the hunger part. The 2023-Q4 cap (π_H = 0.500 → three misses) is the known 11.3 tie. | Not the binding cause |

**Label and target** (*what is predicted*). T43c is regional SWS hunger > 11.3 **and** provincial price pressure.
- **Hunger part.** π_H is the latest regional SWS reading. It is observed food insecurity, but regional, with one value for all five provinces.
- **Price part.** The LightGBM part predicts only the provincial price label, a food-price-pressure proxy.
- **No provincial outcome to check against.** No provincial, independently observed food-insecurity series exists in the repository, so the provincial component cannot be validated as food insecurity.
- **What a Lead-2 result means.** It is a forecast of the composite proxy, and must not be described as validated provincial food insecurity.
- **The frozen target stays the benchmark.**
- **No alternative target was built.** The only observed outcome, regional hunger, is already the persistence-forecast component and is unforecastable beyond the latest reading (E109, E112).

## 3. Point-in-time audit of the 12 indicators (`out/pit_audit.csv`)

**Stack-level checks, all rows:**
- The newest CPI month ends before the issue.
- SWS rounds and news (1,575 dated rows) are published before the issue.
- The target is after the origin.
- Training labels are known at the origin (q ≤ t − 1).
- Missing values use LightGBM's native NaN handling. No imputation or scaling is fitted on future rows.

| Indicator | Status | Point-in-time issue |
|---|---|---|
| A1 food projection, A2 headline | verified for the base cut-off m0 (35 of 36 archived releases before issue; Batangas 2025-02 unverified); refresh partly unresolved | final-vintage index: 3 of 29 archived headline rates differ (≤ 0.4 pp); 375 training rows predate the public 2018=100 series |
| A3 rice | rule only (quarter t − 1) | releases and revisions not checked |
| V1 poverty / density | **violation (disclosed)** | SAE 2021 and POPCEN 2024 were published 2024-25 but are used at every origin. Time-invariant, so they cannot carry temporal signal. |
| C1 El Niño advisory | verified (dated items) | — |
| C2 typhoons | rule plausible | IBTrACS best-track revisions not checked |
| C3, C4 production | rule only (t − 1) | revisions not checked |
| E1 unemployment, E2 remittances | rule only (t − 1) | national only; revisions not checked |
| N1 news | verified | 83% missing at Lead 2 |
| H1 hunger outlook | verified | — |

**Threshold window.**
- The 2021-22 P60 thresholds close at 2022-12. That month was released 2023-01-06, before the first Lead-2 evaluation issue (2023-01-20).
- 600 earlier training rows use thresholds that were not yet computable when those rows were issued. This is a frozen label constant, not a fitted parameter.
- It is disclosed as a residual training-period leakage.

**Tests.** `backend/tests/integration/test_lead2_pit_leakage.py` fails if any of these breaks:
- an input is published on or after its issue;
- a training label is not yet known at its origin;
- a verified-timing CPI month is not released strictly before its issue;
- a row has more than one CPI cut-off;
- the target does not re-derive from its components;
- the threshold window closes after the first evaluation issue.

## 4. Trigger groups (verified timing; refitted chronological ablation, quarter-block 90% CI)

**Δ Brier at Lead 2 when the group is removed** (positive = the group helps):

| Group | B0 | CR-ANC (verified) | Why the contribution is weak |
|---|---|---|---|
| Market / food prices | **+0.037** [+0.009, +0.063], Holm p 0.069 | +0.039 [+0.008, +0.072], Holm p 0.101 | Only material group. The price label is its own target domain. |
| Climate | −0.005 [−0.010, −0.001] | +0.000 | C1 national binary; C2 sparse counts; C3 provincial but lagged one quarter |
| Employment / remittances | +0.004 [−0.001, +0.012] | +0.002 [+0.000, +0.006] | national only: zero between-province variance, ~18 values |
| News / NLP | −0.007 [−0.014, −0.000] | −0.007 [−0.014, −0.001] | N1 missing in 83% of Lead-2 rows; GDELT national |
| Poverty / vulnerability | +0.002 [−0.005, +0.010] | +0.008 [−0.004, +0.022] | static province constant |
| All five removed | +0.031 [+0.003, +0.057] | +0.033 [+0.001, +0.066] | — |

- **Inclusion is not contribution.** All five groups are in the model, but only market prices shows out-of-sample value.
- **SHAP is not used as evidence.**
- **The weak groups are limited by data, not by temporal alignment.** Their inputs are national, static or sparse, so with about 20 distinct quarterly values they cannot separate provinces or anticipate post-issue price moves.
- **What would help.** Provincial, monthly series of the same indicators, such as provincial labour-force and remittance estimates, station rainfall and denser news coverage. These are not in the repository, and none are fabricated.

## 5. Controlled development experiment (BIAS_TRACK, frozen before fitting)

**Hypothesis (from cause 1).**
- The projection bias drifts by regime.
- Giving LightGBM the projection's own most recent realised error should let it correct the bias.

**Change.** X1 = B0 + `EF_recent`, `EG_recent`.
- These are the realised food and gap margins of quarter t − 1, minus the projection made for it.
- They are CPI-derived, use no labels, are available at issue, and have 70% coverage.

**Selection.** On development target quarters (≤ 2024-Q4) only.

**Result.**

| | Dev L2 Brier | Rule result |
|---|---|---|
| B0 | 0.1766 | baseline |
| X1 | 0.1807 | fails (worse; balanced accuracy lower) |
| CR-VER | 0.1689 | baseline for X1-VER |
| X1-VER | 0.1719 | fails (worse) |

- X1-VER happens to pass R1-R7 at Lead 2 on all 65 rows.
- That is **not** evidence: it failed the pre-declared selection, fails R6 at Lead 1, fails the adoption rule (new FA > new hits; Lead 1), and its R6 pass rate under cluster resampling is 0.43.
- No development candidate results.

**Experiment log.** `out/lead2_experiment_log.csv` has 20 entries, including every earlier screen, with its hypothesis, change, selection data and result. Every intervention on the price part has been tried and failed the frozen rules:
- anchored projections, recency weighting and trigger dynamics;
- lagged price-condition labels;
- tuning, composition and subgroup features;
- thresholds, calibration and CPI refresh;
- bias tracking.

**Further experiments stopped.** The remaining levers need data the repository does not hold (verified dates; provincial, timely leading series). Further variants on the same 65 rows would only reuse the inspected evaluation.

## 6. Strongest defensible candidate vs served model and baselines (Lead 2, 65 rows, 17 HIGH)

**CR-VER** is the only verified-timing candidate that passes the frozen *development* rule:
- dev L2 Brier 0.1689 vs B0's 0.1766;
- dev balanced accuracy 0.686, not lower than B0's;
- L1 dev Brier +0.002.

| | Served P0H4 | B0 (P0H4-U) | **CR-VER** | CR-ANC verified | CR-ANC day-10 (provisional) | Always-LOW | Persistence | Climatology |
|---|---|---|---|---|---|---|---|---|
| Accuracy | 0.769 | 0.800 | **0.815** | 0.769 | 0.800 | 0.738 | 0.723 | 0.738 |
| Balanced accuracy | 0.635 | 0.732 | **0.742** | 0.692 | 0.770 | 0.500 | – | 0.500 |
| Precision / recall | 0.60 / 0.35 | 0.63 / 0.59 | **0.67 / 0.59** | 0.56 / 0.53 | 0.60 / 0.71 | – / 0 | – / 0.65 | – / 0 |
| F1 | 0.444 | 0.606 | **0.625** | 0.545 | 0.649 | 0 | – | 0 |
| TP / FP / FN / TN | 6/4/11/44 | 10/6/7/42 | **10/5/7/43** | 9/7/8/41 | 12/8/5/40 | 0/0/17/48 | 11/12/6/36 | 0/0/17/48 |
| Predicted HIGH rate (observed 0.262) | 0.154 | 0.246 | 0.231 | 0.246 | 0.308 | 0 | – | 0 |
| Brier | 0.194 | 0.167 | **0.171** | 0.165 | 0.132 | 0.262 | 0.277 | 0.228 |
| Calibration slope | 0.47 | 1.04 | 1.08 | 1.04 | 1.45 | – | – | – |
| Dev Brier (≤ 2024-Q4, 35 rows) / later Brier (30 rows) | 0.235 / 0.148 | 0.177 / 0.156 | **0.169 / 0.174** | 0.172 / 0.156 | 0.149 / 0.111 | – | – | – |
| Accuracy 90% CI (quarter clusters) | – | [0.71, 0.89] | [0.72, 0.91] | [0.66, 0.86] | [0.69, 0.91] | – | – | – |
| R6 pass rate (cluster bootstrap) | – | 0.38 | 0.45 | 0.19 | 0.44 | – | – | – |
| R1-R7 fails | R3 R5 R6 | R6 | **R5 R6** | R3 R6 | none | – | – | – |
| Adoption rule | – | – | **fails** (new FA > new hits; L1 fails R6) | fails | fails | – | – | – |
| Data timing | base m0 | base m0 | verified | verified | unverified | – | – | – |

**CR-VER's development gain does not hold.**
- In the 2025-Q2+ confirmation quarters its Brier is 0.174, against B0's 0.156.
- Its full-sample Brier (0.171) is worse than B0's.
- Its accuracy edge over B0 is one row.

**Overfitting and generalization.**
- Training vs next-origin test Brier: 0.188 vs 0.222 for B0, and 0.180 vs 0.218 for CR-ANC verified. That is a moderate gap.
- Leaving each province out of training leaves overall Brier unchanged: B0 0.166 vs 0.167.
- Thirds accuracy for B0 is 0.84 / 0.65 / 0.90. The 2024 decline is the projection over-shooting after the 2023 regime, followed by price reversals.

## 7. Supported, uncertain, next step

**Supported.**
- **Not reliable.** Lead 2 is not reliable under the frozen criteria with verified data.
- **Where the skill comes from.** The Lead-2 signal comes from the regional hunger reading carried forward plus a weak price-pressure forecast.
- **The binding constraint.** Price predictability two quarters ahead, not model form or trigger weighting.

**Uncertain.**
- Whether refreshed CPI was genuinely available; this needs dated sources.
- The vintage effects: 3 revised headline rates, and the 2012=100 training rows.
- The assumed lags of A3, C3, C4, E1 and E2.
- Whether provincial, timelier leading series would add signal.

**Next authorized step (your decision).**
- (1) Collect dated PSA release sources for the P and U province-months, then run the single addendum re-score.
- (2) Score the sealed prospective forecasts as their outcomes publish.
- No candidate is proposed for adoption.
