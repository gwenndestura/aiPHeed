# Pre-registration Conflict Resolution (2026-10-11)

**Scope:** resolve conflicts C1–C9 from `experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT.md` before any model execution.

- **Not done:** no model was trained or scored, no accuracy was computed, and no label was rebuilt or created. Production, the scheduler, frozen forecasts and the thesis are untouched. Nothing was committed, deployed, frozen or hashed.
- **Not accessed:** no SWS value was retrieved, and nothing about September or December 2026 was accessed.
- **Earlier draft preserved:** v1 is unchanged (SHA-256 `1a15b718…`). The revised draft is a new file: `experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT_v2.md`.

**Tests performed:** full suite **175 passed** (no code changed in this task; module SHA-256 still `c126ca68…`). One read-only computation was run: the training-only medians below. It used only rows eligible at each origin; no test label was examined.

---

## C1: Label-threshold leakage

**How the threshold is computed now:**

- `app/ml/features/label_generator.py` (l.222–226): `global_threshold = median(stress_score)` over **all** labelled rows; `label_stress = stress_score > global_threshold`.
- `scripts/supplementary/window2021_study.window_labels(14.345)` applies the same rule to the 80 labelled 2021–2025 rows.
- Chapter III states it the same way: "global median … across all 120 province-quarter pairs", which "guarantees a 50/50 class balance".

**Every data-dependent threshold or parameter in the pipeline:**

| Quantity | Current computation | Uses test-period data? |
|---|---|---|
| Target threshold (global median) | All labelled rows, including the evaluated quarters | **Yes (leak)** |
| Equation 3 rule baseline | Compares the known SWS + 2 × `cpi_rel` with 14.345 | **Yes**, through the threshold |
| Carry-forward baseline | Latest published label, thresholded at 14.345 | **Yes**, through the threshold |
| `scale_pos_weight` | HIGH share of training labels | Only indirectly, because the labels use 14.345 |
| Regional mean in Equation 3 | Five-province mean **of the same target quarter** | No: part of the target definition, no cross-time information |
| `cpi_dev` rolling mean | Province's prior 4 quarters | No |
| Classifier cut-off | Fixed at 0.50 | No |

**How big the leak is** (training rows only):

| Exploratory target | Training quarters (rows) | Training-only median | Training HIGH share at the fold median | Training HIGH share at 14.345 |
|---|---:|---:|---:|---:|
| 2023-Q3 | 7 (35) | 10.820 | 0.49 | 0.23 |
| 2023-Q4 | 8 (40) | 10.843 | 0.50 | 0.23 |
| 2024-Q1 | 9 (45) | 10.867 | 0.49 | 0.22 |
| 2024-Q2 | 10 (50) | 11.367 | 0.50 | 0.26 |
| 2024-Q3 | 11 (55) | 11.780 | 0.49 | 0.31 |
| 2024-Q4 | 12 (60) | 12.507 | 0.50 | 0.37 |
| 2025-Q1 | 13 (65) | 13.220 | 0.49 | 0.40 |
| 2025-Q4 | 15 (75) | 14.113 | 0.49 | 0.48 |

The approved 14.345 sits well above anything knowable at the early origins. It encodes the high-hunger level of 2024–2025. **Training on approved labels uses that future information.**

**Fold-specific procedure (specified, not run):** for each fold with target *T*:

1. **τ_T** = median of `stress_score` over the **training rows eligible under Rule L at *T*'s origin**: all five provinces of each eligible quarter. No test-quarter row enters it.
2. **Training labels:** `stress > τ_T`. `scale_pos_weight` is computed from these.
3. **Equation 3 rule:** HIGH if (known SWS + 2 × `cpi_rel`) > τ_T.
4. **Carry-forward:** the latest **published** stress score of the province, compared with τ_T.
5. **Test labels:** see the two designs below.

**Distinction this creates:**

| | Approved target ("A-global") | Fold-specific target ("A-origin") |
|---|---|---|
| Meaning | Stress above the 2021–2025 global median (a fixed level, fixed after the fact) | Stress above the median of all stress levels **observable at the forecast date** |
| Same formula? | Equation 3 stress score: **identical** | Identical |
| Threshold | 14.345 | τ_T, from 10.82 to 14.11 |
| Leak | Yes, in training and baselines | None |
| Test labels | Approved labels | **Differ from approved labels**: the target's meaning changes |

**Proposed evaluation design (recommendation, needs adviser confirmation):**

- **Primary:** A-origin, fold-specific everywhere, for training labels, test labels, the Equation 3 rule, carry-forward and `scale_pos_weight`. It is leakage-free and internally consistent. It is Rule 3's "no look-ahead" applied to the label threshold, and **it is a re-operationalization of Equation 3's "global median", not a new stress formula**.
- **Secondary, for comparability with every earlier study:** A-global, with test labels and every threshold at 14.345, explicitly labelled "uses the full-period threshold (C1 leakage)".
- **A hybrid is rejected:** training on τ_T but scoring against 14.345 mixes two different decision boundaries, which would penalize models for a definitional mismatch rather than for forecasting error.
- **Adviser decision required:** whether A-origin may be the primary analysis. If not, A-global stays primary with the leak disclosed, and A-origin becomes the sensitivity analysis.

## C2: Alternative label definitions

**Resolved:**

- Definition A remains the primary target concept.
- No alternative label (A-adult, C, D) is built.
- Sensitivity S3 is removed from this pre-registration and deferred to a separate, later authorization.
- If S3 is ever run, it follows the C1 fold-specific rule, which also answers C2: thresholds are recomputed per fold from that definition's training rows.

## C3: Keep or drop 2023-Q3 (7 eligible training quarters)

| | Keep 2023-Q3 | Drop 2023-Q3 |
|---|---|---|
| Exploratory test quarters | 8 (40 rows) | 7 (35 rows) |
| First fold's training history | 7 quarters (35 rows) | 8 quarters (40 rows) |
| Chapter III Algorithm 3 | **Below** "a minimum training window of 8 quarters" | **Meets** it |
| Fold-specific threshold | Median from 35 rows | Median from 40 rows or more |
| Comparability with earlier studies | Same 8 quarters | One fewer quarter |

**Recommendation:** **drop 2023-Q3.** The minimum training window is a chronological requirement stated in Chapter III. Under Rule L, the history that counts is the number of **eligible** labelled quarters, and 2023-Q3 has only 7.

- The rule is applied as "**at least 8 eligible labelled quarters**". Gaps such as 2022-Q1 mean these are not strictly "consecutive" quarters as Chapter III's architecture text says. That nuance is recorded for the adviser.
- This is chosen on the requirement, not on any result: no results exist.

## C4–C9: Required treatment

| # | Conflict | Required treatment |
|---|---|---|
| C4 | Definition A's 2025-Q1 label comes from a registered-voter round (Stratbase-SWS, March 2025), not household heads | Keep it (definition A). **Disclose.** Report per-quarter results so 2025-Q1 as a test quarter, and as training input for 2025-Q4, is visible. No alternative label is built (C2). An adviser decision (D3) is still outstanding. |
| C5 | WD1 provincial CPI proxy; WD2 revised climate data | Development protocol only. Disclose in every result. Sensitivities S1 (no revised inputs) and S2 (strict input mask) are kept. **No strict or real-time claim is possible** until the 19 provincial dates and point-in-time vintages exist. |
| C6 | June, September and November 2025 SWS rounds are [V-single] (read once) | Use as inputs, flagged. Sensitivity S4 (without the supplementary 2025 inputs) is kept. **Before any final claim**, confirm them by hand. If a confirmed value differs, the experiment is re-run under a new, separately labelled pre-registration. **No retrieval in this task.** |
| C7 | The March 2026 SWS value is an exposed 2026-Q1 outcome | Not used in this development experiment (no 2026 targets or inputs). In any protected 2026-Q3/Q4 evaluation it is a legitimate **input** (published 2026-05-12, before both origins). Disclose its exposure. |
| C8 | The June 2026 SWS publication date is unknown | Excluded as an input (Rule L4). Not relevant to the development experiment. It must be verified (date only) before any 2026-Q4 forecast. |
| C9 | The `backend/` scheduler (2026-10-15) can retrain and promote the thesis-documented served model | Outside this experiment; nothing in `aipheed-backend-aligned/` is affected. The researcher's decision on `SCHEDULER_ENABLED` is still needed. If the served `backend/` model changes, "MODEL-A as served" comparisons must name the model version. |

**New items surfaced while resolving C1:**

| # | Item | Treatment |
|---|---|---|
| C10 | Under A-origin, the test labels for 2023–2025 differ from the approved labels, so A-origin results are **not comparable** with any earlier reported accuracy (all used 14.345) | State this beside every A-origin result. The secondary A-global analysis supplies comparability. |
| C11 | The fold medians rise from 10.8 to 14.1 as high-hunger quarters enter training, so the A-origin target drifts | Disclose. Report τ_T for every fold. |

## Unresolved decisions (adviser or researcher)

1. **C1 primary design:** A-origin as primary (recommended) or A-global as primary.
2. **C3:** confirm dropping 2023-Q3 (recommended), giving 7 exploratory quarters.
3. **C4 / D3:** the 2025 label composition; 2025-Q1 currently uses a registered-voter round.
4. **C6:** manual confirmation of the three [V-single] SWS rounds.
5. **C9:** `SCHEDULER_ENABLED` before 2026-10-15.
6. **When to freeze v2.** Freezing and hashing it is a separate step that needs your authorization.

**Stopping here.**
