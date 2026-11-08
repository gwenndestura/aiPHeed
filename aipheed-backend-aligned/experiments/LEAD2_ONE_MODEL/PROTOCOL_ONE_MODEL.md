# LEAD2_ONE_MODEL protocol (frozen before any candidate below is scored)

**Date:** 2026-10-27.

**Branch:** `aiPHeed/lead2-one-model`, from `a1ce8ce`.

**Baseline:** served P0H4, reproduced from code (`out/p0h4_reproduction.json`).

| Lead 2 baseline | Value |
|---|---|
| Rows / quarters / HIGH | 65 / 13 / 17 |
| Accuracy | 0.769 |
| Balanced accuracy | 0.635 |
| Precision / recall | 0.60 / **0.353** (TP 6, FP 4, FN 11) |
| PR-AUC / Brier | 0.418 / 0.194 |

**Evidence status.** All 2021–2026-Q3 quarters were examined by earlier experiments. Results are **development evidence**. The only untouched test is prospective: SWS 2026-Q4 onward.

## 1. What the audit (`out/audit.txt`, `out/p0h4_lead2_cases.csv`) showed

**The 11 missed HIGH rows by mechanism:**

| Rows | Mechanism | Addressable? |
|---|---|---|
| 6 | No issue-time warning: the hunger surge and/or price shock started after the issue date | **Not addressable** |
| 4 | Price risk flagged before the hunger surge (2024-Q2). The hunger reading that showed the surge came 21 days after issue. | **Addressable only if the model can learn that strong price pressure plus near-line hunger leads to HIGH** |
| 1 | The structural price projection pointed HIGH and the fitted model overrode it (2024-Q3 Quezon) | **Addressable:** structural offset |

**Mechanisms that were ruled out or limited:**
- **The product rule:** it caused no miss (13 suppressed rows, none HIGH).
- **News:** available for 1 of 11 missed rows (17% coverage), so it cannot address these misses.
- **The four-area σ:** cross-area error correlation 0.51; ≈ 22 effective errors out of 56.

**Ceiling stated before scoring.** With issue-time information, at most 5 more HIGH rows are plausibly reachable at Lead 2, i.e. **recall ≤ 11/17 = 0.65**.

## 2. Architecture of every candidate (your requirement)

**ONE LightGBM classifier**, refitted at each issue date on the stacked rows of every lead (1–15):
- **Label:** the combined target **T43c** itself, known before O(t) (`ch1_lib.known_t43c`).
- **No separate hunger model and no multiplication.** Hunger information enters only as model inputs.

**Base inputs (all candidates):**
- the 16 columns of the 12 FIRI v2 families (H1 = the family's standard regional-hunger outlook, π_H0);
- `lead`;
- the 5 Pink Sheet columns;
- `h_last`, `true_horizon`;
- Region IV-A rice and food CPI YoY at m0.

**Monotone +1:** A1_food, A1_gap, A_mom, H1, h_last.

**Grid and selection:** UNI grid (8) + regularised grid (4), chosen by inner chronological validation (last 4 training origins, log-loss). Not eligible (< 6 quarters, < 5 HIGH or < 5 LOW) → the base rate of the known labels.

| Id | Change | Targets |
|---|---|---|
| **S0** | Base inputs (= Addendum-4 U-ONE-0 with H1 = π_H0) | reference single model |
| **S1** | S0 + issue-time hunger dynamics: h_change (latest − previous BL reading), h_mean4, h_max4, margin = h_last − 11.3, run = signed count of consecutive published quarters on the same side of 11.3; latest reading and change of NCR, Visayas and Mindanao (2021+, published before O(t)) | "price before hunger" (4 rows) |
| **S2** | S1 + structural price offset: init_score = logit(clip(STRUCT_k, 0.01, 0.99)), the **price-only** structural probability (σ per lead from that origin's price-label rows). The trees learn the hunger condition and corrections. | override of the structural signal (1 row); M5 |
| **S3** | S2 with class weight fixed to "balanced" (no unweighted configurations in the grid) | recall under 26% HIGH |

**Decision variants for the selected candidate:**

| Variant | Rule | Serving status |
|---|---|---|
| **τ-inner** | Per origin, τ ∈ {0.20, 0.25, …, 0.50} maximises balanced accuracy over the inner-validation predictions of that origin's training window; then applied to its forecasts | Reported. Needs your approval to serve (the dashboard rule is 0.50). |
| **Platt** | Calibration fitted on inner-fold predictions only | Applied only if it lowers the development Lead-2 Brier |

## 3. Selection (development targets ≤ 2024-Q4; Lead 2 primary)

**Guards.** A candidate is admissible only if:
- its development Lead-2 Brier ≤ 0.2546 (P0H4's development Brier 0.2346 + 0.02);
- its development Lead-1 accuracy ≥ 0.75.

**Selected.** The admissible candidate with the highest **development Lead-2 balanced accuracy at 0.50**. Ties within 0.005 go to the lower development Lead-2 Brier, then to the order S0, S1, S2, S3.

## 4. Success criteria vs P0H4 (all 65 matched Lead-2 rows; fixed now)

**Goal (stronger target):** recall ≥ 9/17 = 0.53.

**Improvement is claimed only if all hold:**

| Criterion | Requirement |
|---|---|
| I1 | Recall ≥ 8/17 (≥ 2 more HIGH rows detected than P0H4) |
| I2 | Precision ≥ 0.50 and false-alarm rate ≤ 0.15 |
| I3 | Balanced accuracy ≥ 0.685 (P0H4 + 0.05) |
| I4 | Brier ≤ 0.204 (P0H4 + 0.010) |
| I5 | The additional detections fall in ≥ 2 distinct target quarters |
| I6 | Lead 1: accuracy ≥ 0.75, and Brier not worse than P0H4 at one-sided p < .10 |

**Reliability.** R1–R7 (FINAL_THESIS_OBJECTIVES §7) plus the LEAD2_OPTIMIZATION Addendum-2 later-block check, per lead. The maximum reliable lead is the run of consecutive passing leads from Lead 1. No "Reliable" verdict before untouched outcomes.

**Uncertainty.** Cluster bootstrap by target quarter. 13 independent hunger outcomes at Lead 2.

## 5. Leakage, replay, news and reporting

| Step | Design |
|---|---|
| Before scoring | 6-origin future-perturbation audit (SWS, CPI, regional CPI, Pink Sheet, news) for S0–S3; must be identical |
| After scoring | Historical replay at 3 origins for the selected candidate |
| News ablation | The selected candidate without N1/news columns |
| News placebo | 20 shuffles of the news columns across issue dates (seed 2030) |
| Reporting | Every candidate on the same 65 Lead-2 rows (and every lead), quarter by quarter. Baselines: P0H4, UNI-FINAL, PERSIST-SI, price-only diagnostic (π_P), hunger-only (latest reading), always-LOW |
| Blocks | Before vs from 2025-Q2 (SWS design shift), surge block, onsets |

## 6. Serving

**Nothing is served or exported to the dashboard without your approval.** If a candidate meets I1–I6 and is reliable at Lead 1, it is exported to this experiment's `out/` with its own seal, and the decision goes to you.
