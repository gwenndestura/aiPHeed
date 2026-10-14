# E25 idea log: ways to make the forecasts reliable, useful and accurate

**Part 1 was written before any E25 model was fitted on the real quarters.** It uses only:

- the baseline-only reachability analysis (`docs/REACHABILITY.md`);
- the synthetic power simulation (`docs/POWER_SIMULATION.md`; no observed outcome used).

**Part 2** (results, kept or rejected) is appended after the frozen run and points to the run ID.

**Chapter I items** use the wording in `docs/CHAPTER_I_TRACE.md`:

| Code | Chapter I item |
|---|---|
| O2-I…V | Objective 2 metrics (accuracy; precision and recall; F1; AUC-ROC; lead times by walk-forward) |
| O3 | Objective 3, municipal and city rankings |
| O4 | Objective 4, baselines |
| O5 | Objective 5, dashboard, ISO/IEC 25010 and the FNRI anchor |
| Q1…Q5 | Statement-of-the-problem questions |
| H1…H5 | Hypotheses |
| §1.2 | Purpose and Description |

## Part 1. Ideas, why they are valid, and simulated power

| # | Idea | Why it is valid | Chapter I item | Simulated power (synthetic) | Decision before running |
|---|---|---|---|---|---|
| 1 | **Score probabilities, not 0/1 labels**, and first compute what is reachable at all | With about 40 test rows and 8 dates, accuracy changes only where a label changes. Brier and log score are proper scoring rules and use every row. **But** against 0/1 persistence nothing helps: where persistence is right its loss is 0 under every rule, so the best p is 2^-m (m = dates on which persistence errs). | O2-I…IV, Q2, Q3, H2, H3 | Accuracy vs persistence, 8 dates: power ≤ 0.20 unless ≥ 20% of rows change and the model anticipates ≥ 75% of them (A). Brier, correct-structure forecaster: 0.20–0.50 vs B1, 0.29–0.39 vs B1p (B). Reachability (baselines only): lead 1 needs a **perfect** model (5 persistence-error dates, best p = 0.031); leads 3–6 cannot reach p < 0.05. | Implemented in every comparison. Accuracy-based C2 kept as the E24 criterion. A Brier-based alternative goes to `ADVISER_APPROVAL_REQUEST.md`. |
| 2 | **Forecast the continuous S1 = H + 2D**, then derive P(HIGH) | The label is a threshold of S1. A predictive distribution keeps the information of how close a province is to the threshold, which a 0/1 forecast discards. | O2, Q2, §1.2 | Included in B (the PCF-type forecaster is exactly this) | Implemented: the PCF family. Also scored as a continuous forecast (CRPS, MAE) against a random walk. |
| 3 | **Pool leads per forecast date** (average the per-lead differences so each date counts once) | Uses every lead without counting a date twice. Dates, not province rows, are the independent units. | O2-V, Q2, H2 | Pooling leads 1–3 raises Brier power from 0.20–0.50 to 0.38–0.70 (B). Reachability: 10 dates, 9 with a persistence error, best p = 0.002. | Implemented. Proposed as the primary design of the Brier criterion (pending approval). |
| 4 | **Use everything published at the forecast date**: CPI months 1–2 of the origin quarter (Dnow), and the supplementary SWS rounds as inputs, with and without them | Information released before the cutoff is legitimate and the most recent. The supplementary rounds are labelled and tested both ways. | §1.2 ("as reflected in newly released government data"), O2 | Not simulated separately (it changes the D and H inputs of B) | Implemented: PCF21_NOW, PCF21_SUPP, M4_21, D_HIER_NOW |
| 5 | **Two-layer model**: regional hunger H and provincial price pressure D forecast separately, then combined with uncertainty (E24v2 design), with improvements to each part | The label is 65% regional H, which is identical for the five provinces. Province differences come only from D. Separate parts give a regional-versus-provincial split that DA can read. | O2, O3 ("validated province-level forecasts"), Q4 | B (both parts). T2 (D > 0) Brier vs persistence 0.86–0.95; accuracy 0.00, because a sign-preserving model cannot beat persistence on accuracy (F). | Implemented. H part: local level (LL), mean reversion (MR), leading indicator (LI). D part: lead-specific OLS, OLS + Dnow, hierarchical. |
| 6 | **Shrinkage and hierarchy** across provinces and leads | One AR(1) for every lead, with province means shrunk toward 0 (empirical Bayes), uses many more pairs than one regression per lead. Dnow enters as a noisy measurement (Kalman update). | O2 | Covered by F (the same test; more pairs only lowers estimation noise) | Implemented: D_HIER, D_HIER_NOW, PCF21_HIER |
| 7 | **A more stable label rule** than the training-window median | Only if correctness requires it. The approved rule makes the same quarter's label depend on the origin. This is a design choice, not an error. Chapter I §1.2 says the label is "anchored to the FAO SDG 2.1.2 baseline" but gives no number. | §1.2, H2 | Not a power question. Reachability: with the pre-existing fixed threshold 14.6 (E23 sensitivity value), lead 1 has 5 LOW rows (evaluable) instead of 3. | **Not adopted as the label.** No correctness defect was found that justifies replacing the approved rule. T1 with τ = 14.6 is reported as sensitivity only, with label-model arms. |
| 8 | **Calibration, ensembles, persistence-gated blend**, all specified without outer-test outcomes | Small training windows make probabilities over- or under-confident. Averaging with calibrated persistence hedges model risk. A gate falls back to persistence when the model was worse in the training window. | O2-IV, Q3 | Not separately simulated (the gains are in Brier, as in B) | Implemented: CAL_PCF21 (temperature fitted on inner forecasts), ENS_PCF21_B1p, GATE_PCF21_B1p, ENS_M4_B1p |
| 9 | **Monthly-origin evaluation of the provincial price component** | About 35 monthly origins give far more evidence on D than 11 quarterly dates. Overlapping targets are handled by sign-flipping non-overlapping 3-month blocks. | O3, Q4 (supporting) | 0.99–1.00 for a correct AR forecaster vs sign persistence (D) | Implemented: `runner/monthly_d_eval.py` (frozen). 2021 months are excluded: their YoY needs 2020 indices, which are out of window. |
| 10 | **Noise ceiling**: how much of the label is SWS sampling noise | Sets realistic expectations. A row whose S1 is within one sampling SE of τ can flip on survey noise alone. | O2 (interpretation), H2 | Descriptive | Implemented (n = 600 and n = 300) |
| 11 | **Leading indicators for regional hunger** available 2021–2026 | If a published indicator predicted the next SWS move, the regional layer could anticipate label changes, which persistence cannot. | Q1, O2 | With 12–16 round-to-round changes: slope power 0.15–0.50 for correlation 0.2–0.4, and 0.72–0.83 only at 0.6 (E) | Implemented as one pre-specified, ridge-shrunk indicator: the change in five-province mean food inflation (PCF21_LI). No search over indicators (it would overfit 16 points). |
| 12 | **Disputed 2025-Q2/Q3 SWS rounds**: report each reading and its effect | The quarter assignment of three supplementary 2025 rounds is disputed, and the label exists only under some readings. | Data completeness, §1.2 | Reachability: readings B and C make lead 1 evaluable on the label-history row set (5 LOW of 55). Reading A (approved) does not. | Implemented: readings A (primary), B, C for the label-history arms. Never used to select. |
| 13 | **Strict publication timing for the 2026 rounds** | Their publication dates are unverified. Counting a round as available only after the file shows it was fetched rules out look-ahead; no backtest origin can use a 2026 round. | C7, §1.7 (release schedules affect timeliness) | — | Implemented (protocol §1.3) |
| 14 | **Abstention band from signal strength** ("too close to call") | DA can act on confident calls and flag close ones. Selective accuracy and Brier versus coverage measure whether confidence is meaningful. | §1.2 ("interpretable"), O5 (dashboard usefulness) | Descriptive | Implemented: risk–coverage table for FINAL vs B1 |
| 15 | **Province ranking skill** (does the forecast order the provinces by D correctly?) | Chapter I calls rankings "relative ordinal estimates". With a common regional H, the province order is the D order. | §1.2, O3, Q4 (supporting) | Not simulated; 5 provinces per date makes Spearman coarse, so this is reported as descriptive | Implemented: per-date Spearman, forecast vs persistence of D |
| 16 | **Prospective seal at a new origin** with authorized inputs only | The only route to C9 (generalization). Outcomes for 2026-Q4 and 2027-Q1 do not exist yet. | C9, O2-V | A claim needs ≥ 8 scored dates; E24 estimated 12–16 new quarters for an excellent model | Implemented: `runner/seal_e25.py` at O(2026-Q3) for every arm whose inputs are all authorized |
| 17 | **Oracle decomposition** (realized H with forecast D, and the reverse) | Shows where the forecasting difficulty lies. **Diagnostic only**: it uses the target quarter's outcome and is never a forecast. | Q1, Q2 interpretation | — | Implemented as DIAG_ORACLE_H and DIAG_ORACLE_D (never compared as candidates) |
| 18 | **Feature models with the pre-2021 cells removed** (masking) | E23/E24 used lag, accel and cpi_dev cells that carried 2020 values. The required baselines must be re-run within the window. | O4, H3, C7 | — | Implemented (protocol §1.4) |
| 19 | **Non-chronological leave-one-quarter-out** as a stability check | Shows whether conclusions depend on one quarter. It uses future quarters, so it is **never** forecasting evidence. | O2 (sensitivity) | — | Implemented for regression-type arms, lead 1, labelled NON-CHRONOLOGICAL |

**Considered and not implemented**, with the reason:

| Idea | Why not |
|---|---|
| Re-acquiring 2021 monthly YoY from PSA to extend idea 9 to about 66 months | A new data acquisition; the existing in-window file supports 54 months. Listed in `AUTHORIZATION_REQUEST.md` as optional. |
| Searching many leading indicators | 16 rounds; a search would overfit. Only one pre-specified indicator is tested. |
| Deep or sequence models | Too few labelled quarters (18) |
| Re-tuning E24 arms on the same quarters | Overfits the dates already examined |
| Using pre-2021 data | Out of scope (hard rule) |
| A new label anchored to the FNRI 19.1% FIES figure | It would change the approved target, it would be chosen after seeing the data, and FIES is a different measure |

**Candidate count** (protocol §4):

- **E25 candidates:** 16 (T1: 10; T2: 6), plus 2 for the monthly evaluation.
- **Lineage, counted for multiplicity:** 4 from the earlier E25 draft (all retained here); E24: E24-F + 15 ablation arms; E24v2: 6 in-window-relevant arms.
- **Total examined on these quarters since E24:** 16 + 2 + 16 + 6 = **40** (the 4 earlier-draft candidates are among the 16).

## Part 2. Results (appended after the frozen run)

Filled in after the frozen run; see below.
