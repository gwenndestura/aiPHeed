# Lead-2 reliability research: experiment plan (frozen before any run)

**Freezing.** The SHA-256 and UTC time of this file are recorded in `runner/PLAN_SHA256.txt` and
`runner/PLAN_FROZEN_AT.txt` before any script below is run. Every runner refuses to run if the hash differs.

**Folder.** Everything is local. Inputs are read only; outputs go only to `out/`. No production model is retrained or
replaced.

## 0. Why these experiments and not others

- About 20 Lead-2 variants were already scored on the same 2021–2026 quarters (`LEAD2_OPTIMIZATION`, `LEAD2_EARLY_WARNING`,
  `FIRI_LEAD2_FEASIBILITY`). Scoring more variants there would be data dredging.
- The binding failure is the **hunger** part (DATA_AUDIT §1).
- The strongest unused evidence is the **four-area SWS panel 1998–2020**. It holds the same outcome, measured the same
  way, and none of it overlaps the 2021–2026 test window.

This plan therefore:

1. Quantifies how much of the Lead-2 error is measurement noise (X1).
2. Selects a hunger forecast **using pre-2021 and other-area data only** (X2).
3. Scores the one selected method **once** on 2021–2026 (X3).

## 1. Shared definitions

- **Panel.** Area quarterly hunger H_a(q) = the mean of the non-starred rounds labelled q.
  - NCR, Visayas and Mindanao come from `sws_area_rounds_full.csv` (all years).
  - BL comes from the same file before 2021 and from `backend/data/inputs/sws_rounds.csv` from 2021 (the production
    series used by the labels).
  - **Publication:** the `published` column. Before 2021 this is the conservative rule date.
  - A quarter is **known at issue I** if it has at least one round published before I. Its known value is the mean of
    those rounds.
- **Origin and issue.** For origin quarter t, the issue date I(t) is the first day of quarter t + 1. Lead k targets
  t + k.
- **True horizon.** h = (t + k) − q_last, where q_last is the newest known quarter of that area at I(t).
- **Outcome.** y = 1 if H_a(t + k) > 11.3.

## 2. X1: label-noise ceiling (descriptive, nothing fitted)

For each BL quarter 2021–2026:

- **Standard error.** SE = (MOE / 1.96) / √r, with MOE from `area_moe_bl` and r the number of rounds.
- **Label reliability.** ρ(q) = Φ(|H − 11.3| / SE). This is the probability that the observed label equals the label
  of the true prevalence.

Reported:

- ρ per quarter;
- the mean ρ over the 17 FIRI Lead-2 target quarters and over the 13 P0H4 Lead-2 target quarters;
- the **expected accuracy of a forecaster that knew the true prevalence exactly**, which is Σρ / n. This is a ceiling
  on achievable accuracy against observed labels.

## 3. X2: hunger forecasting at the Lead-2 horizon, pre-2021 and area-held-out (selection stage)

**Evaluation rows.** Each area a ∈ {NCR, BL, VIS, MIN}, origins t with targets t + k in **2005-Q1 .. 2020-Q4**, leads
k = 1, 2. A row counts only if the target has an observed value. **No 2021+ outcome is used in X2.**

**Training at each origin.** Only pairs (q0, q0 + h) at the row's true horizon h, both known at I(t), from 1998-Q3 on.

**Models.** All use P = Φ((μ − 11.3) / max(σ, 0.5)).

| Id | Mean μ | σ |
|---|---|---|
| **RW** (persistence; the served H4 analogue) | H_a(q_last) | RMS of pooled h-step changes |
| **CLIM** | – (P = share of the area's known quarters above 11.3) | – |
| **MR** (pooled mean reversion) | m_a + β_h (H_a(q_last) − m_a), where m_a is the mean of the area's known quarters and β_h is a no-intercept OLS on pooled pairs of (H(q0 + h) − m_a) on (H(q0) − m_a), clipped to [0, 1] | RMS residual of that fit |
| **MRF** (MR + national food inflation) | MR + γ_h (F(m0(q0 + 1)) − F̄), with F the national food CPI YoY at month 2 of the quarter after q0 (at the real origin: F(m0(t))), and β_h, γ_h fitted jointly by OLS with no intercept on the pooled pairs. F̄ is the mean over the training pairs. | RMS residual |

MRF needs at least 20 training pairs, otherwise it falls back to MR. MR and RW need at least 8 pairs, otherwise the
row is skipped for all models.

**Two fits:**

- **pooled:** all four areas' pairs;
- **area-held-out:** for BL rows, β, γ and σ are fitted on NCR, Visayas and Mindanao pairs only. m_a is still BL's own
  known mean.

**Metrics.** These are reported for (a) all four areas pooled and (b) BL only, pooled-fit and area-held-out:

- n, positives;
- accuracy, balanced accuracy, precision, recall, specificity, F1;
- AUC, Brier, confusion matrix;
- onsets caught (y = 1 after the area's previous quarter had y = 0);
- MAE of μ against the observed level;
- a paired Brier difference against RW, with a one-sided quarter-cluster bootstrap p (5,000 draws, seed 2036).

**Selection rule (applied once, mechanically).**

1. Between MR and MRF, the one with the lower Lead-2 Brier on (a) is chosen.
2. It **passes the gate** if, at Lead 2:
   - its Brier on (a) beats RW with p < 0.10;
   - its Brier on BL area-held-out is below RW's.

Only the chosen model goes to X3, whether or not it passes the gate. The gate result is reported with it.

## 4. X3: one confirmation on 2021–2026 (scored once)

The X2-selected model, refitted at each 2021+ origin on all pairs known at I(t) (four areas, 1998+), gives π_new(t, k)
for BL.

- **X3a, the hunger condition alone.**
  - **Rows:** the 17 FIRI Lead-2 targets 2022-Q3..2026-Q3 (origins 2022-Q1..2026-Q1).
  - **Compared on identical rows with:** RW, the served H4 term (`pi_H4` from the P0H4 review rows where present), and
    FIRI v2 (from `FIRI_LEAD2_FEASIBILITY/out/firi_l2_rows.csv`).
  - **Metrics:** as in X2, plus R2–R7 as applied in `FIRI_LEAD2_FEASIBILITY/PROTOCOL.md`.
- **X3b, P0H4 with the hunger term replaced.**
  - **Formula:** P = π_new × P0_price on the identical P0H4 review rows (70 at Lead 1, 65 at Lead 2), label T43c, threshold
    0.50, **R1–R7 exactly as frozen** (`P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules`).
  - **Recommendation:** only if Lead 2 passes all seven **and** Lead 1 still passes all seven.
  - **Status:** even then, development evidence (these quarters were seen), using pre-2021 data, so adoption needs your
    scope revision and prospective confirmation.
- **Reproduction first.** Before X3, the runner reproduces the P0H4 baseline at Leads 1 and 2 (it must equal
  11/5/6/48 and 6/4/11/44) and the FIRI baseline (11/0/1/5).

## 5. Safeguards

- **No 2021+ outcome enters X2,** whether in fitting, selection or gating.
- **Every training pair at every origin is published before the issue date.** The runner asserts this.
- **CPI is used only at months ≤ m0.**
- **No threshold other than 0.50.** No refitting after seeing X3. No further variants.
- **Bootstrap:** quarters are the clusters. Province rows are not treated as independent hunger observations.

## 6. What would count as Lead 2 being reliable

A forecast meets this standard only if all of the following hold:

1. it passes R1–R7 at Lead 2 (and Lead 1 still passes) on rows not used for any selection;
2. it passes X2's gate on pre-2021 and area-held-out data;
3. the result is confirmed **prospectively** on at least 10 sealed quarters that include at least one hunger regime
   change.
