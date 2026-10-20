# E43 — E36 + one composite feature per driver (lead 1)

Experiment only; nothing is wired into the live system.

**Run.** `runs/20261015T154200Z` (predictions SHA-256 in `E43_results.json`). Code: `runner/e43_lib.py`, `runner/e43_run.py`.

**Procedure.** E36's own walk-forward (`e36_lib.walk_forward`) runs unchanged; E43 arms are extra pools in memory.
- **Target:** S1 = H + 2D above the trailing-median τ.
- **Test quarters:** 13, 2023-Q1 to 2026-Q3 (65 rows: 53 HIGH, 12 LOW).
- **Training:** E36's training-row rule; grid G1/G4/G3/G2 with seed 36.
- **Selection:** the nested rule (lowest mean per-date Brier, tie within 0.002 goes to the simpler setting); threshold 0.5.
- **Monotone constraint:** +1 on the composites, 0 on E36's 13 inputs.

**Data.** Only the refreshed `e43/data/` files, plus `pagasa_climate.parquet` (storms) and the E31 news store (fish-kill titles), all read only.

## E36 reproduction
All 28 stored E36 arms reproduce (1,805 rows):
- **Predictions:** the largest probability difference is 5×10⁻¹¹.
- **Labels and choices:** labels are identical, and E36 picks the same setting at every quarter.
- **Headline:** **E36-repro: accuracy 0.815, Brier 0.154.**

## Composites (one per driver; higher = more stress)

At origin O(t), each composite uses data of quarter t−1 (news: quarter t). All references are expanding over 2021-Q1..t−1, pooled over provinces. No pre-2021 data, so year-on-year terms start at 2022-Q1. PR = percent rank (0–1).

| Driver | Feature | Formula |
|---|---|---|
| Climate | `CLIM` | max( PR(|rain anomaly|, NASA POWER daily), PR(IBTrACS max signal) ) |
| Fish Kill | `FISH` | max( PR(max(0, −ln(V_{t−1}/V_{t−5})), total fisheries volume), 1[fish-kill titles in quarter t] ); production is a **proxy** |
| Employment | `EMP` | 0.5·z(u_{t−1}) + 0.5·z(u_{t−1} − u_{t−5}), u = quarterly **mean** unemployment (observed quarters only) |
| OFW | `OFW` | max(0, −g_real_{t−1}), real peso remittance growth. **PROVISIONAL** (2026 from secondary reports; 2022–2025 curated split unverified) |

**Missing values (left as NaN).**
- **Test rows:** 0 of 65 for every composite.
- **Training rows at the Q4 2026 origin** (75 rows): CLIM 0, FISH 5, EMP 10, OFW 5 (the earliest quarters, where no year-on-year value exists).
- **Q4 2026 test rows:** 0.

**Leakage check.** In all 670 training and test rows, every composite's data quarter is ≤ t−1 and every reference window ends at t−1. **No problems.**

## Results (65 rows, 13 quarters)

| Arm | New | Accuracy (95% CI) | Brier | Log loss | AUC | Bal. acc. | Brier diff vs E36 (95% CI) | McNemar p | Sign-flip p (Holm) | Result |
|---|---|---|---|---|---|---|---|---|---|---|
| **E36-repro** | 0 | 0.815 (0.738–0.892) | 0.154 | 0.508 | 0.850 | 0.822 | — | — | — | reference |
| E43-all4 **(PROVISIONAL)** | 4 | 0.708 (0.600–0.831) | 0.174 | 0.550 | 0.811 | 0.756 | +0.020 (−0.007, +0.047) | 0.016 | 0.898 (1.000) | fail (accuracy) |
| E43-noOFW | 3 | 0.738 (0.631–0.862) | 0.156 | 0.503 | 0.844 | 0.807 | +0.002 (−0.022, +0.027) | 0.125 | 0.536 (1.000) | fail (accuracy) |
| **E43-all4-fixed (PROVISIONAL)** | 4 | 0.831 (0.723–0.923) | 0.153 | 0.656 | 0.876 | 0.864 | −0.002 (−0.061, +0.073) | 1.000 | 0.482 (1.000) | **pass** (non-inferior) |
| E43-CLIM | 1 | 0.815 (0.738–0.892) | 0.157 | 0.516 | 0.850 | 0.822 | +0.002 (−0.000, +0.007) | 1.000 | 0.875 (1.000) | **pass** (non-inferior) |
| E43-FISH | 1 | 0.723 (0.615–0.831) | 0.167 | 0.497 | 0.842 | 0.766 | +0.013 (−0.007, +0.035) | 0.031 | 0.855 (1.000) | fail (accuracy) |
| **E43-EMP** | 1 | **0.862 (0.785–0.938)** | **0.124** | 0.541 | 0.855 | 0.851 | **−0.030 (−0.069, +0.007)** | 0.375 | 0.100 (0.697) | **pass** (non-inferior) |
| E43-OFW **(PROVISIONAL)** | 1 | 0.785 (0.677–0.892) | 0.161 | 0.531 | 0.848 | 0.836 | +0.007 (−0.013, +0.030) | 0.625 | 0.746 (1.000) | fail (accuracy) |
| B1 persistence | – | 0.877 | 0.123 | 1.700 | 0.860 | 0.860 | | | | baseline |
| B2 LR combined | – | 0.862 | 0.120 | 0.531 | 0.840 | 0.818 | | | | baseline |
| B3 LR government | – | 0.846 | 0.102 | 0.420 | 0.866 | 0.809 | | | | baseline |
| B4 LR news | – | 0.708 | 0.198 | 0.581 | 0.658 | 0.692 | | | | baseline |
| B5 LightGBM government | – | 0.846 | 0.145 | 0.452 | 0.870 | 0.841 | | | | baseline |
| B6 LightGBM news | – | 0.677 | 0.195 | 0.576 | 0.736 | 0.673 | | | | baseline |
| always-HIGH | – | 0.815 | 0.185 | 2.551 | 0.500 | 0.500 | | | | diagnostic |

**How to read the columns.**
- **Brier difference:** arm minus E36, per date (negative favours the arm). The CI is a paired date-cluster bootstrap (2,000 resamples, seed 20261014).
- **Sign-flip:** one-sided p for a Brier improvement; Holm-corrected across the 7 E43 arms.

**Adoption (rule fixed before results).** Passing (non-inferior) arms in preference order: **E43-all4-fixed (PROVISIONAL)**, E43-EMP, E43-CLIM.
- **Improvement:** **no arm "IMPROVES on E36"**; the smallest Holm-adjusted p is 0.697 (E43-EMP).
- **Why all4-fixed ranks first:** the first preference key ("more drivers with non-zero SHAP") puts E43-all4-fixed (5 drivers) ahead of E43-EMP (2). But its Climate and OFW contributions are tiny (see below).

## Driver contributions

**Mean |SHAP| per driver over the 65 evaluation rows** (log-odds per row; share of the total in brackets):

| Arm | Market | Climate | Fish Kill | Employment | OFW | Other (hunger, y_last, news, FSSI) |
|---|---|---|---|---|---|---|
| E36-repro | 1.732 (50.1%) | 0 | 0 | 0 | 0 | 1.726 (49.9%) |
| E43-all4 (PROVISIONAL) | 1.584 (52.5%) | 0 | 0.390 (12.9%) | 0.287 (9.5%) | 0.083 (2.7%) | 0.672 (22.3%) |
| E43-noOFW | 1.706 (47.0%) | 0.002 (0.1%) | 0.496 (13.6%) | 0.421 (11.6%) | — | 1.006 (27.7%) |
| **E43-all4-fixed (PROVISIONAL)** | 3.611 (50.6%) | 0.005 (0.1%) | 0.991 (13.9%) | 0.729 (10.2%) | 0.206 (2.9%) | 1.596 (22.4%) |
| E43-CLIM | 1.717 (50.1%) | **0** (never split on) | — | — | — | 1.707 (49.9%) |
| E43-FISH | 1.470 (58.3%) | — | 0.331 (13.1%) | — | — | 0.721 (28.6%) |
| **E43-EMP** | 2.701 (53.3%) | — | — | 0.850 (16.8%) | — | 1.520 (30.0%) |
| E43-OFW (PROVISIONAL) | 1.618 (45.9%) | — | — | — | 0.283 (8.0%) | 1.627 (46.1%) |

## Q4 2026 (origin 2026-10-01; uses 2026-Q2 data, 2026-Q3 news)

| Model (chosen setting) | Batangas | Cavite | Laguna | Quezon | Rizal | **CALABARZON** |
|---|---|---|---|---|---|---|
| E36 (COMB × G2) = served | 0.169 | 0.983 | 0.989 | 0.986 | 0.981 | **0.822** |
| E43-all4-fixed (PROVISIONAL; COMB_all4 × G2) | 0.058 | 0.995 | 0.998 | 0.997 | 0.999 | **0.810** |
| E43-EMP (COMPACT_EMP × G2) | 0.065 | 0.997 | 0.997 | 0.997 | 0.997 | **0.811** |
| E43-CLIM (COMB_CLIM × G2) | 0.151 | 0.988 | 0.987 | 0.990 | 0.985 | **0.820** |
| E43-all4 (PROVISIONAL; nested chose COMB_all4 × G2 here) | 0.058 | 0.995 | 0.998 | 0.997 | 0.999 | **0.810** |

**CALABARZON SHAP shares at Q4 2026** (sum of |SHAP| per group over the five provinces ÷ total; each row adds to 100%):

| Model | Market | Climate | Fish Kill | Employment | OFW | Other |
|---|---|---|---|---|---|---|
| E36 | 38.7% | 0% | 0% | 0% | 0% | 61.3% |
| E43-all4-fixed (PROVISIONAL) | 37.7% | 0.2% | 14.0% | 11.0% | 0.5% | 36.6% |
| E43-EMP | 56.7% | 0% | 0% | 15.6% | 0% | 27.7% |
| E43-CLIM | 42.0% | 0% | 0% | 0% | 0% | 58.0% |
| E43-all4 (PROVISIONAL) | 37.7% | 0.2% | 14.0% | 11.0% | 0.5% | 36.6% |

**Composite values at Q4 2026.**
- **CLIM:** 0.84–0.91 in every province (2026-Q2 rainfall was far below normal).
- **FISH:** Laguna and Rizal = 1.0 (fish-kill titles published in 2026-Q3), Quezon 0.36, Cavite and Batangas 0.
- **EMP:** 0.53 (national).
- **OFW:** 0 (real remittance growth was positive).

## Caveats
- **The selected arm is not a tuned model.** E43-all4-fixed uses E36's served setting (COMB × G2) at every date. That setting was picked with hindsight, so this arm is not the product of the nested procedure. With the same pipeline, E42's diagnostic "E36 COMB × G2 fixed" (no drivers) scored accuracy 0.862 and Brier 0.132. Adding the four composites to that fixed setting made it worse (0.831, 0.153). Its Brier interval (−0.061 to +0.073) is also too wide to say anything.
- **Two drivers barely register.** Climate is used almost nowhere: 0.1% of SHAP, never split on in E43-CLIM, and unused even though CLIM is high at Q4 2026. OFW gets 0.5–2.9% on provisional data.
- **Fish Kill and Employment do carry a share** (10–17%). The Fish Kill composite on its own lowers accuracy (0.723).
- **E43-EMP is the strongest single result.** Brier 0.124 vs 0.154 and accuracy 0.862 vs 0.815 confirm E42's employment finding with the composite. But it is not significant after correction (Holm p 0.70; the CI includes 0), and it rests on one national series.
- **Not fresh data.** These 13 quarters have been examined since E25; this is development evidence, not validation.

## Verdict
Under the rule fixed beforehand, three arms are non-inferior to E36: E43-all4-fixed (PROVISIONAL), E43-EMP and E43-CLIM. **None improves on E36** (smallest Holm-adjusted p = 0.70). The rule's preference selects **E43-all4-fixed**, where 5 of 5 drivers have non-zero SHAP. But only **three get a real share**: Market (~38–51%), Fish Kill (~14%) and Employment (~10–11%). Climate (≤ 0.2%) and OFW (≤ 3%, provisional data) are essentially zero. It is **not safe to propose for the live system**: the selected arm depends on unverified OFW data and a hindsight-fixed setting, and it scores worse than E36 run with that same fixed setting. The most credible candidate for a prospective (next-quarter) check is **E43-EMP**, after BSP primary data and a regional unemployment series are in place.
