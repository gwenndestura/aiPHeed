# Reliability Review: Reaching 75% Accuracy Within the Approved Methodology

Prepared 2026-10-08 for the researchers and their adviser. The production model
and Chapter III are unchanged. Every figure comes from two reproducible scripts
whose outputs are in `data/supplementary/`:

```bash
python -m scripts.supplementary.reliability_diagnostics   # Phases 2-8
python -m scripts.supplementary.algorithm4_candidate      # Algorithm 4 on the candidate
```

Reference: *THESIS 2 (9).pdf*, 1 October 2026, Chapter III.

---

## 1. Current approved model (Phase 1)

| Component | Approved method (Chapter III) | Current implementation | Correct? |
|---|---|---|---|
| Target | Eq. 3: stress = SWS hunger + 2 x (provincial food CPI YoY - regional mean); HIGH above the global median | Same; threshold 14.6 over 95 labelled rows | Yes (residual < 0.0001) |
| Robustness label | Eq. 4 | Built; compares the rising CPI level to a 24-quarter mean | Yes as written; trivially positive in later quarters |
| Data sources | PSA, BSP, DOE, PAGASA, PhilRice, SWS, PSA NRP; news | Same; DOE, BSP, SWS typed in by hand; unemployment national only | Yes, with data limits |
| Preprocessing | 512-char premise, 3-stage PSGC geocoding, bias weight Eq. 1, LIMITED_SIGNAL < 5 | Same | Yes |
| NLP / FSSI | XLM-RoBERTa zero-shot, 10 bilingual hypotheses, max, >= 0.30; Eq. 2 + lags | Same, plus a food-nexus guard not in Chapter III | Mostly; guard is undocumented |
| Triggers | Algorithm 2, five regex categories | Fixed 2026-10-08 (pipeline had never run it) | Yes now |
| Feature matrix | Sec. 3.3.2.6: ten sources **including SWS hunger**, 120 x 45 | SWS deliberately left out; 45 other candidates + CPI_dev | **No** |
| Final features | Line 1164 and Eq. 5: twelve, via Sec. 3.3.2.7 (absent from the manuscript) | Equation 5's twelve | Conflicts with Algorithms 3-4 |
| Algorithm 3 | **Default** LightGBM, input **45-feature matrix**, k = 1..8, walk-forward, min 8 quarters, 75% mean fold accuracy | `class_weight="balanced"`, Eq. 5's twelve | **No** |
| Algorithm 4 | 100-trial TPE, 9 params, gap = discovered k, mean weighted F1, 4-quarter holdout, input **45-feature matrix** | Eq. 5's twelve; gap applied as a train/test gap with a same-quarter holdout, not features(t) -> label(t+k) | **No** |
| Algorithm 5 | Eq. 6, 0.6 poverty + 0.4 density, 142 LGUs | Same | Yes |
| Horizon / Rules 2-3 | Operational horizon = furthest reliable k; features only from before the forecast period | Same-quarter estimates published (k = 0) | No (follows from the above) |
| Validation | Walk-forward expanding window; 4-quarter holdout | Same | Yes |
| Metrics | Accuracy, precision, recall, F1, AUC; 75% (Alg. 3); F1 >= 0.75, AUC >= 0.80 (holdout) | Same | Yes |
| Baselines | Six (RQ3); four (Objective 4) | Six | Yes |

## 2. Implementation verification (Phase 2)

**Verified correct:** Equation 3 (stress - SWS - 2 x CPI deviation < 0.0001 on all
rows); the global median (47 HIGH / 48 LOW); provincial codes; walk-forward
splits (no target quarter in training is at or after the test quarter);
calendar-based FSSI lags; CPI_dev uses only earlier quarters; no feature cell is
back-filled; SWS and the label are not in Equation 5.

**Implementation errors found:**

| # | Error | Effect | Fixed where |
|---|---|---|---|
| I1 | `poverty_incidence` used each survey year's figure in that same year, but PSA published the 2021 provincial figures on 15 Aug 2022 and the 2023 figures in Aug 2024 (Rule 3) | Inflated accuracy: 0.782 -> 0.764 on the full matrix | Diagnostics (production fix pending, Level 1) |
| I2 | Algorithm 3 used `class_weight="balanced"`; Chapter III says "a default LightGBM classifier" | Precision changed, accuracy unchanged on Eq. 5 (0.618 both) | Diagnostics |
| I3 | Algorithms 3-4 ran on Equation 5's twelve features; Chapter III names the 45-feature matrix as their input | **Main cause of 0.62**: 0.618 -> 0.764 | Diagnostics (Level 2, see Section 6) |
| I4 | SWS hunger left out of the matrix, although Section 3.3.2.6 joins it | 0.764 -> 0.782 when restored at k = 1 | Diagnostics (Level 2) |
| I5 | Algorithm 4 applies the gap as a train/test gap and scores the holdout on same-quarter rows | Holdout metrics describe a nowcast, not the k-quarter forecast | Must be fixed before production (Level 1) |
| I6 | Fixed earlier today: Algorithm 2 never ran; CPI_dev definition; FSSI not reproducible; BERTopic in the matrix | Triggers were constant zeros | Production (Section 7 of PROPOSAL_CONFORMANCE) |

## 3. Why the current model is below 75% (Phase 3)

**A. Label by quarter** (HIGH / LOW of 5): 2020-Q2 1/4, Q3 5/0, Q4 2/3; 2021-Q2 3/2,
Q3 0/5, Q4 0/5; 2022-Q2 2/3, Q3 1/4, Q4 1/4; 2023-Q1 0/5, Q2 1/4, Q3 1/4, Q4 3/2;
2024-Q1 4/1, Q2 5/0, Q3 4/1, Q4 5/0; 2025-Q1 5/0, Q4 4/1. No SWS round in 2020-Q1,
2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3.

**B. SWS contribution.** 65.8% of the stress score's variance is between
quarters. Variance of the SWS term 23.6 against 12.3 for the CPI term (they are
uncorrelated). SWS alone reproduces 82.1% of the labels. 7 of 19 quarters are
entirely one class.

**C. Temporal persistence.** The label is the same in the next quarter for 72% of
75 consecutive pairs; stress autocorrelation 0.70. On the test folds, repeating
the last observed label scores 0.80.

**D/E. Feature variation.** Of Equation 5's twelve, unemployment and the OFW
trigger never differ between provinces within a quarter; market and employment
triggers differ in fewer than 13% of quarters. 19 of the 45 candidates are
constant within every quarter (national or regional series). Province-separating
signal comes from the FSSI family, CPI_dev, rice price change, the climate and
fish-kill triggers, poverty incidence and the commodity prices.

**F. Class imbalance.** Training windows are 28-48% HIGH; test quarters from
2023-Q4 on are 60-100% HIGH. The model learns a mostly-LOW world and is tested
on a mostly-HIGH one.

**G. Sample size.** 95 labelled province-quarters, 19 quarters, 5 without SWS;
55 test rows over 11 walk-forward folds; one province moves a fold by 20 points.

**H. Threshold stability.** The median knowable at each point fell from 15.5
(2021-Q2) to 12.1 (2023-Q1) and rose back to 14.6 (2025-Q4). The fixed global
threshold therefore uses information from after many test quarters, and labels
near 12-15.5 depend on when the line is drawn.

**Bottleneck.** The label is mostly regional hunger. The current implementation
runs the model on twelve features that contain no hunger predictor and only a
few province-separating series, while Chapter III's Algorithm 3 names the full
45-feature matrix, which includes SWS and several provincial price series.

## 4. Strict walk-forward evaluation (Phase 4)

One quarter ahead, features at t paired with the label at t+1, minimum 8
training quarters, 11 folds, 55 rows (60% HIGH), default LightGBM, cut-off 0.50,
poverty incidence as published. No threshold, hyperparameter, scaling or feature
is chosen from test data.

| Model | Accuracy (mean fold) | Precision | Recall | F1 | AUC | Confusion [[TN,FP],[FN,TP]] |
|---|---:|---:|---:|---:|---:|---|
| D0 current implementation (Eq. 5, balanced) | 0.618 | 0.657 | 0.618 | 0.621 | 0.789 | [[16,6],[15,18]] |
| D1 Eq. 5, default LightGBM | 0.618 | 0.805 | 0.618 | 0.591 | 0.860 | [[22,0],[21,12]] |
| D2 45-feature matrix, SWS excluded | 0.764 | | | 0.765 | 0.799 | |
| **D3 45-feature matrix incl. SWS (Algorithm 3 as written)** | **0.782** | **0.819** | **0.782** | **0.784** | **0.815** | [[20,2],[10,23]] |
| D4 Eq. 5 + SWS only | 0.709 | | | 0.705 | 0.883 | |

| Baseline | Accuracy | Precision | Recall | F1 | Confusion |
|---|---:|---:|---:|---:|---|
| Always HIGH | 0.600 | 0.360 | 0.600 | 0.450 | [[0,22],[0,33]] |
| Always LOW | 0.400 | 0.160 | 0.400 | 0.229 | [[22,0],[33,0]] |
| Persistence (last observed label) | 0.800 | 0.808 | 0.800 | 0.802 | [[18,4],[7,26]] |

Precision, recall and F1 are weighted, as Algorithm 4 specifies.

## 5. Methodology-compliant improvements (Phase 5)

| Change | Accuracy | Why it is inside Chapter III |
|---|---:|---|
| Algorithm 3 with default LightGBM (I2) | 0.618 | Algorithm 3 says "a default LightGBM classifier" |
| Algorithm 3-4 input = the 45-feature matrix (I3) | 0.764 | Algorithms 3 and 4 each list "Input - 45-feature matrix" |
| SWS hunger at t in the matrix (I4) | 0.782 | Section 3.3.2.6 joins SWS hunger; at k = 1 it is from before the forecast period (Rule 3) |
| Poverty incidence as published (I1) | lowers 0.782 -> 0.764 without SWS | Rule 3 |

**Robustness of D3** (mean fold accuracy): minimum training window 6 / 7 / 8 / 9 / 10
quarters gives 0.769 / 0.783 / 0.782 / 0.780 / 0.778. By year: 2022 0.80, 2023
0.75, 2024 0.75, 2025 0.90. Eight of eleven folds score 0.80 or 1.00; the three
at 0.60 are 2023-Q4 to 2024-Q2, where hunger turned upward. By horizon: k = 1
0.782, k = 2 0.720, k = 3 0.644. **Maximum Reliable Lead Time = 1 quarter.**
LightGBM defaults are deterministic, so there is no seed to re-run.

## 6. Minimum methodology modification (Phase 6)

| Level | Item | Current | Problem | Proposed | Leakage? | Objective preserved? |
|---|---|---|---|---|---|---|
| **1** Implementation | I1 poverty vintage | Same-year figure | Not yet published (Rule 3) | Latest release before each quarter | Removes it | Yes |
| **1** Implementation | I2 default LightGBM in Algorithm 3 | Balanced weights | Contradicts "default" | Library defaults | No | Yes |
| **1** Implementation | I5 Algorithm 4 forward pairing | Same-quarter holdout | Holdout is a nowcast | features(t) -> label(t+k) in search and holdout | Removes it | Yes |
| **2** Clarification | I3 model input | Eq. 5's twelve | Line 1164 / Eq. 5 say twelve; Algorithms 3-4 say 45; Sec. 3.3.2.7 missing | Algorithms 3-4 run on the 45-feature matrix; Eq. 5 is read as the core variables the matrix contains | No | Yes |
| **2** Clarification | I4 SWS in the matrix | Excluded | Sec. 3.3.2.6 includes it; leakage only at k = 0 | Include SWS hunger at t; never use the model at k = 0 | No at k >= 1 | Yes |
| 3 Refinement | Skill requirement | 75% only | A rule with no skill can reach 75% | Also report against persistence | No | Yes |
| 3 Refinement | Threshold | Global median (uses future) | Moves 12.1-15.5 over time | Expanding or fixed reference median | No | Changes labels |
| 4 Major | Longer history | 2020-2025 | 95 rows | Add pre-2020 quarters | No | Needs data collection |

Expected effect of Levels 1-2 together: mean fold accuracy 0.782 at k = 1,
measured above. Chapter III would need: a sentence that Algorithms 3 and 4 use
the 45-feature matrix (resolving line 1164 and the missing Section 3.3.2.7), a
sentence that SWS hunger enters only at lagged form for k >= 1, and the
poverty-release rule. Risk: the clarification of I3 must be accepted as reading
the existing text, not as a new method.

## 7. The SWS question (Phase 7)

- **A. Is SWS a predictor?** Section 3.3.2.6 joins "SWS hunger" into the training
  matrix, and Algorithms 3 and 4 take that matrix as input. Yes, as written.
- **B. Is it part of the target?** Yes, Equation 3's first term.
- **C. Does Rule 3 allow lagged SWS?** Rule 3 requires features "exclusively from
  data available before the forecast period". SWS at t is published before
  quarter t+1, so at k = 1 it is allowed. At k = 0 it is the target's own term
  and is leakage.
- **D. Does it change the conceptual model?** No: Figure 3.2 and Section 3.5
  already list SWS among the government data the pipeline collects and fuses.
- **E. Does it change Equation 5?** Equation 5 does not name it. Because
  Equation 5 and Algorithms 3-4 disagree in the manuscript itself, the adviser
  must confirm which governs. Hence Level 2, not Level 1.

## 8. Controlled experiment (Phase 8)

Identical folds, rows and protocol:

| Model | Accuracy | Precision | Recall | F1 | AUC | Beats persistence? |
|---|---:|---:|---:|---:|---:|---|
| Approved as implemented (D0) | 0.618 | 0.657 | 0.618 | 0.621 | 0.789 | No |
| Corrected candidate (D3) | **0.782** | 0.819 | 0.782 | 0.784 | 0.815 | No (0.782 vs 0.800) |
| Persistence | 0.800 | 0.808 | 0.800 | 0.802 | - | - |

The improvement holds in every year and every training-window size tested; it
is not one favourable split. It does not beat persistence overall: it is better
in 2022 (0.80 vs 0.60), equal in 2025, and worse in 2023-2024.

**Algorithm 4 on the candidate** (100 TPE trials, k = 1, holdout 2024-Q3,
2024-Q4, 2025-Q1, 2025-Q4 never seen by Optuna): accuracy 0.80, weighted F1
0.83 (target met), AUC-ROC 0.50 (target not met). The holdout is 18 of 20 HIGH,
so AUC rests on two LOW rows, and always-HIGH (0.90) and persistence (0.85)
score higher on it. The walk-forward table above is the better evidence.

## 9. Recommendation

Adopt the Level 1 fixes (I1, I2, I5) and ask the adviser to confirm the two
Level 2 clarifications (I3, I4). Together they give **0.782 mean walk-forward
accuracy one quarter ahead under Chapter III's own Algorithm 3**, a Maximum
Reliable Lead Time of one quarter, and no leakage. Report it beside the
persistence baseline (0.800), because the model does not yet beat it.
For skill above persistence, the next step is a longer history (Level 4).

## 10. Adviser decision required before implementation

1. Algorithms 3 and 4 run on the full Section 3.3.2.6 matrix, not only
   Equation 5's twelve (resolves line 1164 and the missing Section 3.3.2.7).
2. SWS hunger enters that matrix and the model is used only at k >= 1.
3. Whether results must also be compared with persistence when judging
   reliability.
4. Unchanged from earlier: the food-nexus guard, the ISO Likert scale, and the
   unverified NNS 2019/2023 figures.
