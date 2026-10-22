# E98: direct food-insecurity target, model comparison and pre-deployment acceptance gate (pre-registered)

**Branch.** `e98-acceptance-gate`, from `e97-validation-completion` (060fceb). Frozen before any E98 scoring.
**Production.** `final-system-v2` was at 053a95d (origin) on 2026-10-22T08:39Z. E98 does not modify, merge into, or
deploy that branch. No Render/Vercel deployment is triggered.

**Evidence status.** Every SWS round to 2026-Q3 has been examined (E56–E97). All E98 historical results are
**development evidence**. The only independent outcomes will be SWS 2026-Q4 and later, against sealed forecasts.

## 1. Target (resolved from E87, E96, E97)

- **Intended outcome (measured food insecurity):** SWS involuntary hunger above 11.3% in the target quarter (R).
  - Mean of the `definition_A` rounds of the quarter (served rule).
  - Geography: Balance Luzon (regional). Conclusions apply to the region, never to a province or an LGU.
- **No provincial or municipal measured series exists** in the 2021–2026 data. None is constructed.
  - T43 (provincial price pressure) remains a proxy, reported separately.
  - DOST-FNRI FIES (5 values) is for descriptive comparison only.
- Price pressure, climate stress, household economy, poverty and news are **predictors**, never outcomes.

## 2. Question D: does a model trained directly on R beat FIRI v2 and persistence? (Lead 1 and Lead 2)

FIRI v2 is an index. Its weights were derived from R, but it was never trained as a classifier of R, so it cannot output
a calibrated probability (E97 Q2). E98 tests the direct formulation with a deliberately small model, because about 15
labelled quarters cannot support more.

**Arms.**

| Id | Model | Features (regional, known at the issue date) |
|---|---|---|
| H1 | Served regional hunger outlook `regional_hunger(t, L)` (latest posted round ± its own past error) | — (persistence analogue) |
| FIRI | Served FIRI v2 regional mean. Lead 2: `data/thesis/firi2_history.csv`. Lead 1: C3 in `E97/recovered/regional.csv`. | — (index used as score) |
| D1 | L2 logistic regression (C = 1.0, training-standardised) | H_last (latest posted SWS level) |
| D2 | as D1 | H_last, C_reg (regional mean climate/production domain at origin t) |
| D3 | as D1 | H_last, C_reg, E_reg (national household-economy domain) |

- C_reg and E_reg are the regional means of `dom_C` and `dom_E` of the served history rows with origin t. These
  scores are computed from strictly earlier origins (FIRI2 C1, verified in E97).
- **Walk-forward training.** For a target with origin t and issue date I = `issue_of(t)`, the training pairs are origins
  t′ < t whose target t′ + L has an R outcome posted before I, with complete features.
  - At least 6 pairs and at least 2 of each class are required.
  - Otherwise the arm issues the H1 value, recorded as a fallback.
- **Evaluation.** Quarters where every arm has a value and R exists (origins ≥ 2021-Q4).
  - Metrics: accuracy (Wilson CI), balanced accuracy, HIGH precision/recall/F1, AUC, Brier, log loss, confusion and
    class counts, per quarter, onsets (R = 1 while the latest posted reading was ≤ 11.3) and recoveries.
  - Paired comparisons vs H1 and vs FIRI: quarter bootstrap (5,000 draws, seed 98) and a two-sided sign test.
- **Calibration.** Reliability in two bins (p < 0.5, p ≥ 0.5): mean prediction vs observed rate.

**Decision rule D (mechanical).** A D arm is the best defensible regional model, in place of FIRI v2, only if at Lead 2:
- accuracy ≥ FIRI's on the common quarters; **and**
- Brier < H1's with the quarter-bootstrap 95% CI of the paired difference entirely below 0.

If several pass: the lowest Lead-2 Brier wins, then the fewest features. If none passes, FIRI v2 remains the best
defensible index and no regional probability is offered.

**75% claim (Chapter I Lead-2 objective).** "Met on the intended outcome (development evidence)" only if the selected
model's Lead-2 accuracy is > 0.75 and above both H1 and always-HIGH. "Independently validated" only after the sealed
prospective quarters are scored.

## 3. Question P: why PSA-only beat the LightGBM framework on its 30 eligible Lead-1 rows (E97 §8)

Diagnostic only, from the E97 Objective 4 predictions:
- which target quarters are eligible;
- per-quarter accuracy and Brier of B-PSA vs M-U96-POV on those rows;
- whether the gap is concentrated in specific quarters.

No arm is retuned.

## 4. Question R: reproducibility and version identity

- Re-run the E97 FIRI validation and Objective 4 scripts; every metric must be identical to the committed E97 outputs
  (excluding time stamps).
- Record SHA-256 of every served artifact and of the serving code. Verify they are unchanged since E97 (060fceb), so the
  model version, the evaluation and the report all refer to the same files.

## 5. Question O5: evaluation instruments

- ISO/IEC 25010: a DA Region IV-A version of the questionnaire, items 1–15 mapped as in `E97/iso25010/item_map.json`.
  Score only actual responses (none exist on 2026-10-22).
- DOST-FNRI: availability re-check from repository sources only (no web collection, per the deadline rule).

## 6. Release gate (all must pass; otherwise production is not changed)

| # | Criterion | How verified |
|---|---|---|
| G1 | Selected model predicts the intended food-insecurity target; proxies are distinguished | §1; the selected model's target is R |
| G2 | Lead-2 ≥ 75% evaluated on the approved target with a defensible design | Question D on R, walk-forward |
| G3 | Leakage and misalignment ruled out | E97 Q1b–Q1d, and E98 D-arm training-pair audit (every pair's outcome posted before I) |
| G4 | Generalisation evidence distinguished from development evidence, **and present** | Requires at least one scored unseen quarter |
| G5 | Baselines on comparable samples | Common-quarter evaluation (D), same-origin T43 table (E97) |
| G6 | Any probability shown is supported and calibrated | Decision rule D |
| G7 | Feature groups assessed without unsupported claims | E96 Q3, E97 Q3/Q5, E98 D arms |
| G8 | 142-LGU ranking and map integration pass integrity tests; substitutes disclosed | E97 tests re-run |
| G9 | ISO/IEC 25010 and DOST-FNRI evidence complete, or the objective classified incomplete | Responses on file |
| G10 | Backend, frontend, API and regression tests pass | Full suites on this branch |
| G11 | Model artifact, evaluation and report refer to the same version | Question R |
| G12 | Release candidate reproducible from documented inputs and commands | Question R |

Deployment requires G1–G12 all to pass. A criterion that cannot be verified counts as failed.
