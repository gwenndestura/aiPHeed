# E53 final report: calibrating E52, the LightGBM requirement, the five triggers, and the independent test

**Date:** 2026-10-17. **Branch:** `e46-lead2-policy`, not pushed. **Production default:** unchanged (E38).
- E52 and E46 are unchanged.
- E53 is served only with `AIPHEED_LEAD2_MODEL=e53`.

**Pre-registration:**
- `PROTOCOL.md` (sha 4d2e1496…) was committed before any E53 score (473de52).
- `ADDENDUM_I2.md` (sha fb238a3e…) was committed before the second round (2d3c29e).
- Deviations are in `DEVIATIONS.md`:
  - D-1: explanation mapping;
  - D-2: float tolerance in a reproduction check, with the aborted run kept;
  - D-3: what `e53` serves when no arm is adopted.
- The objective mapping is in `OBJECTIVES.md`.

## 1. Answers to the eight questions

| # | Question | Answer |
|---|---|---|
| 1 | ≥ 75% Lead-2 accuracy? | **Yes for the E52 model on PS (0.760), as development evidence only.** No new E53 arm reaches it; the best are C2 at 0.760 and LGB-R2 at 0.700. Accuracy CI 0.66–0.88. Not reached on the thesis Eq.3 label. |
| 2 | Beats all applicable baselines fairly? | **Yes for E52/R0:** lowest Brier (0.190 vs ≥ 0.309) and highest balanced accuracy (0.752 vs ≤ 0.630) on the identical 50 rows. Every E53 arm also beats every baseline on Brier (A3), and all except LGB-C2 on balanced accuracy (A4). |
| 3 | Meaningful HIGH/LOW discrimination? | **Yes:** HIGH recall 0.722, LOW recall 0.781, AUC 0.797. |
| 4 | Sufficiently calibrated probabilities? | **No.** CITL −0.094 (about 9 points too high); calibration slope 0.585 (too extreme). In the 0.8–1.0 bin, mean p is 0.92 against 0.64 observed. Four pre-registered calibrators made it worse (CITL −0.112 to −0.133). |
| 5 | Generalizes to independent forecast quarters? | **Not yet known.** All 10 historical quarters were examined during development. The independent test is the frozen 2027-Q1 forecast (sha dc01bb84…); `runner/e53_prospective.py` reports it as pending. |
| 6 | Uses the five triggers correctly? | **Aligned, available at issue and genuinely used as inputs.** None adds reliable predictive information on these rows (section 4). Every input is now attributed (D-1), and missing inputs show as limited data. |
| 7 | Meets the Chapter 1 LightGBM requirement? | **No.** Five pre-registered LightGBM candidates reached 0.48–0.70 accuracy and failed A1–A5. The served model is a base-effect CPI projection with ridge residuals. **This deviation from Chapter 1 needs adviser approval** (section 7). |
| 8 | Suitable for experimental or production use? | **Experimental use only** (`e53` / `e52` flags). It is not ready for production: the target (PS) is unapproved, the model family deviates from LightGBM, probabilities are over-confident, and there is no independent evidence yet. |

## 2. E52 reproduction and calibration audit

**Reproduction:**
- R0 refits the E52 model at all 12 origins (2023-Q4..2026-Q3) and reproduces the committed I7 `p_price` and the frozen 2027-Q1 values within 1e-9.
- E52's eleven metric blocks are reproduced from E52's `rows.csv`, CIs included.
- Run 1 (`20261017T140057Z`) and its repeat (`20261017T140524Z`) are byte-identical apart from the timestamp.

**Verified figures:**

| Metric | Value |
|---|---|
| Accuracy | 0.760 [0.66, 0.88] |
| Balanced accuracy | 0.752 |
| Brier | 0.190 |
| AUC | 0.797 |
| Calibration-in-the-large | −0.094 |
| Calibration slope | 0.585 |
| Leave-one-quarter-out minimum | 0.733 |
| Per-quarter accuracy | 0.6 to 1.0 |

**Reliability of R0 (`tables/reliability.csv`):**

| Bin | n | Mean p | Observed |
|---|---|---|---|
| 0.0–0.2 | 14 | 0.08 | 0.14 |
| 0.2–0.4 | 10 | 0.29 | 0.10 |
| 0.4–0.6 | 11 | 0.51 | 0.36 |
| 0.6–0.8 | 4 | 0.72 | 1.00 |
| 0.8–1.0 | 11 | 0.92 | 0.64 |

**Where the error is:**
- The over-prediction is concentrated after the 2024 rice-tariff cut: 2025-Q2..2026-Q3, mean p 0.26–0.75 against 0.0–0.6 observed.
- Probabilities near 0.9 are too confident.

**Calibration attempts** (fitted only on data available at each origin):

| Arm | Fitted on | Acc | Brier | CITL | Result |
|---|---|---|---|---|---|
| C1 intercept | inner out-of-fold | 0.740 | 0.195 | −0.112 | fails K1, K2 |
| C2 Platt | inner out-of-fold | 0.760 | 0.191 | −0.127 | fails K1, K2 |
| C3 intercept (I2) | earlier issued forecasts | 0.740 | 0.206 | −0.113 | fails A1, K1, K2 |
| C4 Platt (I2) | earlier issued forecasts | 0.700 | 0.209 | −0.133 | fails A1, A5, K1, K2 |

**Why calibration cannot fix this from past data:** the calibrators learn from 2022–2024, when the model under-predicted, so they push up just as the regime turns down. The intercept is +1.21 at 2024-Q3 and +0.67 at 2025-Q4, and only becomes negative from 2026-Q2.

**Conclusion:** the bias is a regime shift that no calibration fitted on the past can anticipate. No calibrated arm is adopted, and the probabilities stay as E52's. They are labelled over-confident in the report, and the 0.5 decision is unchanged.

## 3. LightGBM development (same PS target, origins, as-of features, training rows and rows scored)

| Arm | Design | Acc [CI] | Bal | Rec H | Rec L | Brier | AUC | Min LOQO | Passes |
|---|---|---|---|---|---|---|---|---|---|
| R0 = E52 (ridge) | base projection + ridge residual | 0.760 [0.66, 0.88] | 0.752 | 0.722 | 0.781 | 0.190 | 0.797 | 0.733 | A1–A5 |
| LGB-R (primary) | base projection + LightGBM residual | 0.640 [0.44, 0.80] | 0.682 | 0.833 | 0.531 | 0.260 | 0.743 | 0.600 | A3, A4 only |
| LGB-RL | LGB-R with linear trees | 0.620 [0.46, 0.76] | 0.642 | 0.722 | 0.562 | 0.228 | 0.741 | 0.578 | A3, A4 only |
| LGB-C | LightGBM classifier on PS | 0.560 [0.38, 0.70] | 0.644 | 0.944 | 0.344 | 0.262 | 0.634 | 0.533 | A3, A4 only |
| LGB-R2 (I2) | shrinkage-heavy, 5% selection margin; trees used at 9/12 origins | 0.700 [0.56, 0.80] | 0.729 | 0.833 | 0.625 | 0.221 | 0.786 | 0.667 | A2, A3, A4 |
| LGB-C2 (I2) | monotone classifier; non-constant at 6/12 origins | 0.480 [0.32, 0.66] | 0.582 | 0.944 | 0.219 | 0.259 | 0.538 | 0.444 | A3 only |

**Paired Brier difference against R0:** LGB-R +0.070 [−0.011, 0.167]; LGB-R2 +0.031 [−0.015, 0.090].

**Why LightGBM loses:**
- About 30–60 training province-quarters per origin are too few for trees.
- The selected LightGBM gap residuals push the 2025-Q4 and 2026-Q1 probabilities up (mean 0.59 and 0.66) when no province was HIGH.
- Where LightGBM chooses no residual, it equals the base projection, so the trees add nothing.
- Five LightGBM attempts were made; the I2 arms are hindsight-informed.

**Conclusion:** no defensible LightGBM candidate meets A1–A5 on PS. E52/R0 stays as the experimental alternative.

## 4. Five triggers: coverage, alignment and real contribution

**Coverage at each issue date** (`tables/trigger_coverage.csv`, 2023-Q4..2026-Q3 origins):

| Group | Inputs | Mean share present | Provincial or national |
|---|---|---|---|
| Market / Prices | 10 (CPI projections, food/gap now, rice wholesale, rice policy, market news) | 0.99 | provincial CPI and rice; national policy |
| Climate Stress | 9 (typhoons, ENSO, palay/corn, interactions, climate news) | 1.00 | typhoons, crops and news provincial; ENSO national |
| Fish Kill | 3 (fisheries, aquaculture, fish-kill news) | 1.00 | provincial; **no official fish-kill event series** |
| Employment | 3 (unemployment, underemployment, employment news) | 1.00 | national |
| OFW Remittance | 4 (BSP remittances USD/PHP, USD/PHP rate, OFW news) | 0.92 | national; **BSP remittances end at 2025-Q4 in the dataset**, so they are missing at the 2026-Q2/Q3 issue dates |

**Timing:** cutoffs are as verified in E47:
- CPI through the month before publication at the origin;
- typhoons and news through quarter t;
- production, LFS and remittances through quarter t−1.

**Ablation** (R0 refitted without the group; paired quarter-cluster bootstrap; `tables/trigger_ablation.csv`):

| Removed | Brier | Change vs R0 [95% CI] | Adds reliable information? |
|---|---|---|---|
| Climate | 0.194 | +0.004 [−0.001, 0.010] | no |
| Fish Kill | 0.190 | −0.0004 [−0.0008, −0.0001] | no; it slightly *hurts* |
| Employment | 0.189 | −0.001 [−0.004, 0.000] | no |
| OFW Remittance | 0.193 | +0.003 [−0.001, 0.011] | no |
| News | 0.194 | +0.004 [−0.000, 0.013] | no |
| Rice policy | 0.190 | +0.000 [−0.000, 0.001] | no |
| All non-market (market only) | 0.202 | +0.012 [−0.001, 0.033] | no; closest to significant |

**Reading:**
- The five triggers are real, aligned inputs that are available at the issue date.
- On 50 rows, none of the non-market groups adds predictive information that can be distinguished from zero.
- Together they may help slightly: removing all of them gives +0.012 Brier and −0.06 accuracy, but the CI includes 0.
- They are not forced to contribute.

**Explanation defect found and fixed (D-1):**
- E52's (and E46's) attribution left the rice-policy and news contributions unattributed (median 0.10, maximum 1.01 food-inflation points) while showing other = 0%.
- E53 attributes every input:
  - rice policy → Market;
  - `news_<group>` → its group;
  - total news volume → "other", up to 13.2%.
- Trigger tally in the E53 record (60 province-quarters): Market contributes in 60, Climate 21, Employment 15, OFW 5, Fish Kill 0. OFW has partial inputs in 10 of them.
- The E46 record has the same gap. Its artifact is left unchanged, as instructed; the fix is a follow-up.

## 5. Explanations (`tables/explanation_examples.md`)

For each province-quarter the dashboard shows:
- the target quarter and probability;
- HIGH or LOW;
- the top two or three contributing groups, each with its direction;
- the evidence: indicator, period and source;
- the data status: sufficient, or limited with the reason;
- one sentence.

Example (live API, 2027-Q1):
> "Food-price pressure in Quezon for 2027-Q1 is forecast LOW (15% probability), mainly because Market / Prices lowered it."

The data status is **limited**: "Some inputs not available at the issue date for OFW Remittance."

**Faithfulness checks:**
- Each group's effect is the log-odds change of the served probability when its inputs are set to their training mean.
- Ridge contributions plus the base deviation reconcile with F̂ and Ĝ: error 0.0 on every entry.
- The served probability is reproduced within 1e-9 at every origin.
- The text says "model attributions, not causes" and "food-price pressure, not food insecurity".

**Display bug fixed:** `str.capitalize()` lower-cased group names in the data-status note ("ofw remittance").

## 6. Before and after

| | Before (E52) | After (E53) |
|---|---|---|
| Served probability | E52 R0 | unchanged (no arm adopted) |
| Accuracy / bal / Brier / AUC | 0.760 / 0.752 / 0.190 / 0.797 | same |
| Calibration | CITL −0.094 (not reported as a defect) | the same, now audited: slope 0.585, reliability table, 4 calibrators tried and rejected |
| LightGBM | not tried on PS | 5 arms tried, best 0.700; deviation documented |
| Trigger evidence | contribution tally only | coverage, timing and ablation; none adds reliable information |
| Explanation completeness | news/policy unattributed, other = 0% | every input attributed, other up to 13.2% |
| Data status | missing remittances shown as "no effect" | shown as "limited" with the reason |

## 7. Decisions for the adviser

1. **LightGBM (Chapter 1, objective 2).** No LightGBM candidate meets 75% with discrimination on PS; the best, LGB-R2, reaches 0.700. Options:
   - (a) approve the E52 model (base-effect projection + ridge residuals) as the forecasting model, with LightGBM reported as a compared, losing alternative;
   - (b) keep LightGBM as specified and report that the 75% objective is not met with it.
2. **Target:** approve PS (provincial food-price pressure) as the forecasting target, with SWS hunger shown separately. This is still pending from E52.
3. **Probabilities:** accept that the probabilities are over-confident (slope 0.585) and present them as indicative, with the HIGH/LOW decision at 0.5 as the operational output. No recalibration is possible from past data alone.
4. **Five triggers:** accept that the non-market triggers are shown as model inputs with small or no measurable effect, rather than as proven predictors.
5. **Data refresh:** authorize loading the 2026 BSP remittance months (2026-Q1/Q2), which are missing from the dataset.
6. **Independent test:** confirm the 2027-Q1..Q4 rule (E52 PROTOCOL section 6) and the scoring script `runner/e53_prospective.py`.
7. **Serving:** whether to make `e53` (E52 probabilities with corrected explanations) the dashboard default. It currently stays E38.

## 8. Tests and live verification

**Tests:**

| Suite | Result |
|---|---|
| Backend (full) | 378 passed, 18 skipped |
| E53 serving tests | 4 passed |
| E52 serving tests | 6 passed |
| E53 experiment tests | 4 passed |
| E52 experiment tests | 4 passed |
| Frontend | tsc clean, 45 vitest passed |

**Live check** (`aipheed-e53-api` on port 8001 + frontend on port 8082, clock 2026-10-17):

| Check | Result |
|---|---|
| Map and ranking | 2027-Q1 shows Quezon 0.15, Cavite 0.06, Laguna 0.05, Batangas 0.04, Rizal 0.03; region 0.07 |
| Summary sentence | shown with the limited data status |
| Timeline | 12 of 17 quarters available; target 2027-Q1, origin 2026-10-01 |
| Trend series | 12 points |
| Quezon municipalities | 41 LGUs, relative prioritisation |
| News for Cavite 2026-Q3 | 5 articles |
| Backtest summary, Batangas 2026-Q3 | LOW 7%, observed LOW |
| Municipality summary | names the province ("Quezon (province of Infanta)") |

## 9. Artifacts and hashes

| Artifact | SHA-256 |
|---|---|
| `PROTOCOL.md` | 4d2e14966dd8f76afaba02691670961aa84bad36b1864ee2cd594068e2e138fd |
| `ADDENDUM_I2.md` | fb238a3e83371df532185f93bc73280dfc7fe6ae41b28ad0a24f9a441b7dfe89 |
| `backend/data/e53/e53_record.json` | 4e5a1e16ab05fe1cb344b7c4daf72a2b0d121cff474db9f6a56e04e8ba57a253 |
| E52 frozen 2027-Q1, the independent test (unchanged) | dc01bb84b3c4e03e3d038f40bcc7904ab15cc48c2cb346ff000a86d3016fabaf |
| E46 I7 frozen 2027-Q1 (unchanged) | 5592d53ee00eb3e1e13d5112d1f69223f561e97c9f7077d8a05d5c587647be8d |

**Runs:**
- `20261017T135737Z`: aborted, D-2.
- `20261017T140057Z`: run 1.
- `20261017T140524Z`: the repeat.
- `i2_20261017T140757Z`: round I2.

No new frozen forecast was written, because no E53 arm passed.

## 10. Modified and added files

**Experiment** (`E53_LightGBM_Calibration/`):
- `PROTOCOL.md`, `ADDENDUM_I2.md`, `DEVIATIONS.md`, `OBJECTIVES.md`, this report;
- `runner/`: `e53_lib.py`, `e53_evaluate.py`, `e53_evaluate_i2.py`, `e53_coverage.py`, `e53_prospective.py`, `e53_tables.py`, and the sha files;
- `runs/` (4), `tables/` (9 files), `tests/`, `prospective_status.json`, console logs.

**Backend:**
- `scripts/build_record_e53.py`, `data/e53/e53_record.json`;
- `app/ml/inference/e41_lead2.py`: e53 mode, `partial_inputs`;
- `app/api/v1/insights.py`: E53 note;
- `app/services/dashboard.py`: e53 event, partial-input data status, the capitalisation fix;
- `tests/integration/test_e53_corrected_attribution.py`.

**Frontend:** no change in E53.

**Local only:** launch configuration `aipheed-e53-api` (in the gitignored `.claude/launch.json`).
