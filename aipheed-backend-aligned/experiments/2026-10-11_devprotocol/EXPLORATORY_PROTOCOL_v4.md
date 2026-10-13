# Exploratory Protocol v4: the first controlled exploratory training run

**Status:** proposed, NOT executed.

| Item | Value |
|---|---|
| Builds on | `PREREGISTRATION_DRAFT_v3.md`, preserved unchanged. v4 adds the disclosure in §1, fixes the designation rule for the threshold analyses, and names the runner. |
| Runner | `runner/run_exploratory.py`. A dry run is the default; execution needs `--execute --authorized-by`. |
| Tests | `tests/unit/test_exploratory_runner.py` (20) and `tests/unit/test_devprotocol_rule_l.py` (16) |

**Every result is an EXPLORATORY development estimate on reused 2021–2025 quarters.**

- It is not a final or independent evaluation.
- **It cannot establish accuracy above 75%.**
- The thesis methodology is not changed by this run. §2 states where the run departs from Chapter III, and what the adviser must still approve.

## 1. Disclosure: earlier training-only-threshold result

The idea of a threshold computed only from training rows has been tested before:

| Item | Detail |
|---|---|
| Reports | `OVERFITTING_AUDIT_MODEL_B2_2026-10-09.md`, `GENERALIZATION_STUDY_2026-10-09.md`, `IMPROVEMENT_STUDY_2026-10-09.md` |
| Results reported | **70.9%** for MODEL-B2 and **72.7%** for configuration P |
| Thresholds | 12.1–14.3 |
| Design | 2020–2025 window, 95 labelled rows, before Rule L, with the older timing and test quarters |

**This was seen by the researcher and the assistant** before the A-origin analysis below was proposed. The choice of design is therefore not result-blind.

**Mitigation:**

- Both threshold analyses are run and reported in full.
- The rule that decides which one is primary (§2) is fixed in writing now, before execution.
- Nothing is selected afterwards.
- The earlier numbers are **not** a preview of this run: the window, label eligibility, inputs and folds all differ.

## 2. Threshold: global vs fold-specific

| | A-global (approved definition) | A-origin (fold-specific) |
|---|---|---|
| Threshold | 14.345, the median of all 80 labelled 2021–2025 rows | τ_T, the median of the stress scores of the training rows eligible at *T*'s origin |
| Meaning of HIGH | Above the 2021–2025 median: a fixed level set after the fact | Above the median of stress levels published by the forecast date |
| Uses future information on 2021–2025 test quarters? | **Yes.** The evaluated quarters and later ones help set the boundary. | No |
| Matches Chapter III text ("global median across all … pairs") | Yes | No. It re-operationalizes "global median" at each origin. |
| Comparable with earlier reports | Yes (the 14.345 studies) | No |

**Rules for both analyses:**

- Each analysis applies one threshold per fold to the training labels, test labels, Equation 3 rule, carry-forward and class weights.
- The run computes both.
- **Designation (fixed now):**
  - **A-origin is primary.** This is the only leakage-free option on reused quarters.
  - This is **pending adviser approval**.
  - If the adviser declines, **A-global becomes primary** and is labelled "not leakage-free". No re-run is needed, because both are in the same output.
- The run is not blocked on the adviser's reply, because it is labelled exploratory and both analyses are reported.

## 3. Fixed configuration

| Item | Value |
|---|---|
| Horizon / origin | One quarter ahead. Forecast for *T* issued at 00:00 on the first day of *T*. |
| Unit | Province × quarter; 5 provinces |
| Inputs | `devprotocol_rule_l.development_frame()`: only values published before the origin. SWS per round by publication date (three supplementary 2025 rounds as inputs only; unknown-date rounds excluded). Provincial CPI dated by the WD1 proxy. Other families by documented schedules. **Missing values stay NaN** (LightGBM native handling; nothing imputed or fitted). |
| Training rows for *T* | The rows of quarters whose label was published before *T*'s origin (Rule L, development protocol) |
| Minimum window | **At least 8 eligible labelled quarters** (Chapter III Algorithm 3, counted after Rule L) |
| Test quarters (primary) | **2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4**: 7 quarters, 35 rows, with 8/9/10/11/12/13/15 training quarters |
| Excluded quarters | 2023-Q3 (7 training quarters; reported only as S5). 2025-Q2/Q3 (no label). All of 2026. |
| Learned quantities | τ_T, `scale_pos_weight` and model fits use **training rows only**. No scaling, imputation or feature selection is learned. |
| MODEL-B2 (primary model) | `LGBMClassifier(objective="binary", random_state=42, verbosity=-1, scale_pos_weight=(1−p)/p)`, with *p* = the training HIGH share. 44 inputs (`gov_c` ∩ development mask). |
| MODEL-A (comparator) | Same, without class weights. The 12 Equation 5 inputs. **Refitted per fold**; the saved artifact is not used. |
| Equation 3 rule (comparator) | HIGH if `sws_hunger + 2 × cpi_rel` (origin-known) > τ. Missing inputs fall back to the training majority (counted). |
| Carry-forward (comparator) | HIGH if the province's latest **published** stress score > τ |
| References | Always-HIGH and always-LOW |
| Seed / cut-off | 42 / 0.50. No tuning, no search, and no selection on any result. |
| Determinism | MODEL-B2 is fitted twice per fold; the predictions must be identical, or the run aborts. |
| Degenerate fold | If the training labels contain one class only, the fold is not fitted and is reported as degenerate |

**How the minimum-window interpretation affects the test quarters:**

| Reading | First qualifying fold | Test quarters | Rows | Status |
|---|---|---|---|---|
| "8 eligible quarters" | 2023-Q4 | 7 | 35 | Primary |
| Literal "8 consecutive quarters" (2022-Q1 has no label, so runs restart) | 2024-Q3 | 4 | 20 | Reported as subset **S6** from the same predictions |

The adviser should confirm which reading governs.

## 4. Sensitivities (reported, never substituted)

| ID | Change | Feature counts |
|---|---|---|
| S1 | Drop the revised inputs (ONI, drought, IBTrACS, NASA POWER) | MODEL-B2: 37 |
| S2 | Strict-protocol input mask | MODEL-B2: 18; MODEL-A: 9 |
| S4 | No supplementary 2025 SWS inputs | — |
| S5 | 2023-Q3 fold (7 training quarters) | — |
| S6 | Literal consecutive-window subset | — |

All sensitivities are computed for both threshold analyses, except S5 and S6, which use the base inputs.

## 5. Metrics and uncertainty

**Per model, analysis and sensitivity:**

- mean-quarter accuracy, plus correct and incorrect counts;
- balanced accuracy;
- weighted precision, recall and F1;
- HIGH recall, plus missed-HIGH rows and quarters;
- the test HIGH share;
- confusion matrix;
- per-quarter and per-province accuracy;
- ROC-AUC, Brier score and within-quarter AUC (fitted models);
- τ for every fold.

**Uncertainty:**

- **Headline interval:** quarter-cluster bootstrap, 10,000 draws, seed 42.
- **Clopper–Pearson** on rows and **exact McNemar** are both labelled **optimistic**, because the five provinces in a quarter share the SWS term and most inputs (n_eff ≈ 7).
- **Paired comparisons:** MODEL-B2 vs each comparator, using the bootstrap difference and McNemar.

## 6. Safety rules enforced by the runner

**Isolation:**

- It never imports `app.tasks`, `app.api`, `app.main`, `app.services`, `app.ml.training`, the quarterly pipeline, uvicorn, fastapi or apscheduler.
- It refuses to run in a process where any of them is loaded.
- It reads data only. It writes only into a new `runs/<UTC timestamp>/` folder; it refuses to reuse a folder, overwrite a file or write outside the folder.

**Labels:**

- No 2026 label can be present.
- Training-label access is limited to quarters before *T*.
- Each fold's predictions are written (without labels) **before** that fold's test labels are revealed.

**Integrity:**

- SHA-256 of every protected file is taken before and after the run; any change aborts. Protected files are:
  - `data/processed/*`, `data/supplementary/*`, `models/*`;
  - frozen forecasts and earlier experiment folders;
  - evidence, reports and the pre-registration drafts;
  - `label_generator.py`, `sws_hunger_fetcher.py` and the experimental modules.
- The output records: the configuration, the hashes of the protocol, runner and module, eligible quarters per fold, feature sets, exclusions, library versions, input provenance hashes, and the order in which labels were revealed.

## 7. Approvals still needed (they do not block this exploratory run)

| Approval | Effect if declined |
|---|---|
| Adviser: A-origin as primary (§2) | A-global is primary instead, with the same run |
| Adviser: minimum-window reading (§3) | S6 is the governing subset instead |
| Adviser: D3 respondent-population composition | Disclosed in this run; needed for any final claim |
| Adviser: WD1, WD2 and WD5 | Disclosed in this run; needed for any final claim |
| Researcher: explicit authorization to execute | **Required. The run does not start without it.** |

## 8. Limits on claims

- **Reused quarters:** every test quarter was used in earlier studies.
- **Not real-time:** inputs use proxy dates (WD1) and revised vintages (WD2).
- **Unconfirmed SWS values:** June, September and November 2025 are each confirmed by one reading only. November 2025 is the 2025-Q4 label.
- **Effective sample:** about 7 quarters. Even 7/7 correct gives a 95% lower bound of 0.59.
- **No result may be described as meeting the 75% requirement.**
