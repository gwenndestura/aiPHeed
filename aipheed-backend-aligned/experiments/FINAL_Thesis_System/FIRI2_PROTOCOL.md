# FIRI v2 optimization: pre-registered protocol

**Date:** 2026-10-20 (final optimization task).
**Freezing:** this file is written and hashed (`runner/FIRI2_PROTOCOL_SHA256.txt`, LF-normalised) **before any candidate below is scored**. The runner refuses to run if the hash differs.
**Already examined, disclosed:**
- FIRI v1 results on T43 and on the regional SWS outcome (`FIRI_PROTOCOL.md`, `firi_evaluation.json`);
- the label-free and label-based diagnostics in `out/firi2_diagnostics/` (run 2026-10-20 before this protocol).

All 2022-Q2..2026-Q3 outcomes have therefore been seen, so every result below is **development evidence**. The independent test is prospective (§7).

## 1. Problems the candidates address (from the diagnostics)

| # | Problem | Evidence (label-free unless stated) | Addressed by |
|---|---|---|---|
| P1 | Fixed 2021–2023 anchors saturate when the regime changes | E1 scores 1 on 100% of evaluated Lead-2 rows (the recovery years set P90 = −1.07 points); A2 scores 0 on 60%; E2 mean 0.80 | expanding-window percentile normalization (C1) |
| P2 | Correlated national/regional time series are counted as separate domains | Spearman E1–H1 0.66, E1–E2 0.55; C1, C2, E1, E2, H1 are identical for all provinces | redundancy-adjusted domain weights (C2) |
| P3 | Equal weights ignore how strongly each domain relates to the only direct food-insecurity observation | regional SWS hunger (Balance Luzon) is observed every quarter; walk-forward weights can use only outcomes posted before each issue | evidence weights, walk-forward, shrunk to equal (C3) |
| P4 | News is excluded only because the fixed window had 3 FSSI values | 20 SUFFICIENT FSSI-v3 province-quarters in 2022-Q4..2026-Q3 | expanding normalization admits N1 once 8 earlier values exist (C1–C3) |

## 2. Candidates (all have no parameter fitted to provincial labels)

Shared by every candidate:
- the v1 indicators, raw values, directions, statuses and missing rules (`firi.raw_indicators`);
- the domain = mean of its available indicator scores;
- at least 4 domains;
- HIGH at index ≥ 0.50 on the unrounded index;
- the LGU index = province index × the approved LGU vulnerability.

| Id | Normalization of continuous indicators (A2, A3, C2, C3, C4, E1, E2, N1) | Domain weights |
|---|---|---|
| **C0** | FIRI v1, frozen anchors (served before this task) | equal |
| **C1** | **Expanding-window mid-rank percentile.** s = (#{prior < x} + 0.5 · #{prior = x}) / n_prior, where *prior* = the indicator's values at origins strictly earlier than the current origin (from 2021-Q1). National/regional series (C2, E1, E2) contribute one value per origin; provincial series pool all provinces. Needs n_prior ≥ 8, else the indicator is missing (status `insufficient_history`), never 0. A1, V1, C1 and H1 are already 0–1 and used as they are. | equal |
| **C2** | as C1 | **redundancy-adjusted:** w_d ∝ 1 / (1 + Σ_{d′≠d} max(0, ρ_dd′)), where ρ_dd′ = Spearman correlation of domain scores over province rows at origins strictly earlier than the current one (≥ 8 earlier origins, else equal weights). Weights renormalised over the available domains. |
| **C3** | as C1 | **evidence weights (walk-forward):** for each domain, ρ_d = Spearman correlation between the regional mean domain score at past origin t′ and the observed SWS Balance Luzon hunger level at t′ + lead. Only pairs whose outcome round was **posted before the current issue date** count. Raw weight max(ρ_d, 0), normalised; shrunk to equal: w = n/(n+8) · w_ρ + 8/(n+8) · w_equal, where n = usable pairs. Fewer than 6 pairs, or every ρ_d ≤ 0 → equal weights. |

**LightGBM post-processing checks** (food-price-pressure score only; reported, served only if they pass §5.3):

| Id | Rule |
|---|---|
| **L1** | Walk-forward Platt recalibration of the sealed E56 probability: at each origin, a logistic regression of T43 on logit(p) over sealed rows whose label quarter was known at that issue (≥ 15 rows, else raw p) |
| **L2** | Walk-forward threshold: the threshold maximizing balanced accuracy over the same known rows (grid 0.05..0.95, step 0.05; ≥ 15 rows, else 0.5) |

## 3. Evaluation data (identical for every candidate)

| Outcome | What it is | Use |
|---|---|---|
| **R (primary)** | Observed SWS involuntary hunger, Balance Luzon, above 11.3% at t + lead (the direct food-insecurity observation; regional). The same outcome series as FIRI v1 (`firi_regional_outcome.csv`). | The regional mean index per origin is the score. Origins 2021-Q4..2026-Q1 for Lead 2 (targets 2022-Q2..2026-Q3); 2021-Q4..2026-Q2 for Lead 1; 2021-Q4..2025-Q4 for Lead 3. Compared on the quarters where **every** candidate is computable. |
| **R-prov (secondary)** | The same regional outcome against each province's class (5 rows per quarter, quarter-clustered) | Reported |
| **T43 (agreement only)** | The food-price-pressure label (E57 / E63 rows) | Reported as agreement with a price label, **never** as food-insecurity accuracy, never used for selection (it shares sources with A1/A2) |

**Baselines on R:**
- always-elevated (majority);
- climatology (share of elevated outcomes posted before the issue);
- **H1 alone** (the regional hunger outlook: P(> 11.3%) from the latest posted round, the naive-persistence analogue);
- the LightGBM's own hunger part (E56 P_hunger regional mean, where sealed).

**Metrics:**
- accuracy (Wilson 95% CI), precision, recall, F1, both class recalls, AUC-ROC, Brier (the index used as a score; not a calibrated probability), confusion matrix;
- Spearman correlation with the observed hunger level;
- paired quarter Brier differences vs each baseline, with a quarter bootstrap 95% CI (2,000 draws, seed 2026) and a two-sided sign test.

## 4. Leakage controls

- Every indicator uses only data published before the issue date (as v1).
- Normalization, redundancy and evidence weights use strictly earlier origins.
- Evidence weights use only outcome rounds posted before the issue date.
- The outcome at t + lead is never an input.

## 5. Selection rule (applied once, mechanically)

1. **Eligibility (label-free):**
   - computable on ≥ 90% of the R quarters at Lead 2;
   - no continuous indicator with ≥ 90% of evaluated Lead-2 rows at a single bound (0 or 1);
   - share of HIGH province rows at Lead 2 between 10% and 90% (not automatic HIGH or LOW).
2. **Among eligible candidates:**
   - highest Lead-2 R accuracy on the common quarters;
   - ties → lower Lead-2 R Brier;
   - then lower Lead-1 R Brier;
   - then the simpler candidate, in the order C1 < C2 < C3.
3. **Keep C0 instead of the winner if the winner is worse than C0 on Lead-2 R accuracy.**
4. **LightGBM checks L1/L2** replace the served price part only if, on the 50 Lead-2 rows:
   - the paired Brier difference vs raw E56 has its 95% CI below 0 and sign p < 0.05 (L1);
   - or balanced accuracy is higher with the CI of the paired difference above 0 (L2).

   Otherwise they are reported only.
5. **Claims:**
   - The selected method is called the estimated food-insecurity risk index (FIRI v2 if C1–C3 wins).
   - Its R accuracy is reported as accuracy against the **regional** hunger outcome, not provincial food-insecurity accuracy.
   - The > 75% goal is "met on R" only if the Lead-2 R accuracy is > 0.75 **and** above always-elevated and H1 alone; otherwise "not demonstrated".

## 6. What is not done

No candidate is tuned on T43. No threshold other than 0.50 is tried for the index. No observation is dropped except where a candidate is not computable (reported). No pre-2021 data is used.

## 7. Prospective (independent) test

The selected index for targets **2026-Q4** (issue 2026-07-01) and **2027-Q1** (issue 2026-10-01) is sealed with SHA-256 in `out/firi2_sealed_prospective.csv` before either SWS round is posted. It is scored when the SWS 2026-Q4 and 2027-Q1 rounds are published.
