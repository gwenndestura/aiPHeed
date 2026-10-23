# E103: verifying and decomposing the E102 FB2 gain. Pre-registered protocol

**Date:** 2026-10-23. **Branch:** `main` @ `0239273`. Production unchanged; E100–E102 files are read or imported, never modified (their SHA-256 are checked before and after the run). Outputs go to `out/` only.
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`, LF-normalised) before any arm below is scored.

**Already examined (disclosed):** every E102 result (FB1, FB2, FB2-noH with a 3-domain minimum, T1-B, the A-share sensitivity, FB2 drop-one ablation incl. FB2 without the price domain, trained models, descriptive correlations). New in E103 and not yet scored: SERVED-noA2, SERVED-A1only, FB2-noREL, FB2-noPERS, LVL-only, PERS-only, REL-only price domains; FB2-noH with a 4-domain minimum; FB2-noH with equal weights; the PERS threshold/window and trailing-base sensitivity; the period split; the permutation test. All outcomes (SWS 2022–2026-Q3) were seen before: **development evidence only**. Sealed quarters (2026-Q4, 2027-Q1) have no outcome yet and are not scored.

## 1. Reproduction gate (before any new arm)

SERVED and FB2 regional values recomputed in E103 must equal `E102/out/regional_lead{1,2}.csv` (max abs difference < 1e-9), and their accuracy and Brier must equal E102 `results.json` (0.889 / 0.180 at Lead 1, 0.941 / 0.189 SERVED and 0.941 / 0.162 FB2 at Lead 2, as stored). Otherwise the run stops.

## 2. Arms (index; C3 walk-forward evidence weights recomputed per arm and lead, exactly as E102)

Price domain A = mean of the listed available scores (pct = mid-rank percentile among all provinces' values at strictly earlier origins, ≥ 8):

| Arm | Domain A | Purpose |
|---|---|---|
| SERVED | A1, A2, A3 | baseline |
| S-noA2 | A1, A3 | remove headline inflation only |
| S-A1only | A1 | remove headline and rice change |
| S-noA | no domain A (≥ 3 domains) | remove the price domain |
| FB2 | A1, pREL, pPERS | E102 candidate |
| FB2-noREL | A1, pPERS | |
| FB2-noPERS | A1, pREL | |
| LVL-only | pLVL | food price level only |
| PERS-only | pPERS | persistence only |
| REL-only | pREL | burden only |
| FB2-noH4 | FB2 without domain H, ≥ 4 domains (the arm E102 intended) | no SWS input |
| FB2-noH3 | FB2 without domain H, ≥ 3 domains (the arm E102 reported) | no SWS input |
| FB2-noH-EQ | FB2 without domain H, ≥ 3 domains, **equal** domain weights | no SWS input and no SWS-fitted weights |
| Baselines | ALWAYS, P0 (H1, latest posted SWS), CLIM | |

**Evaluation quarters:** per lead, the quarters where SERVED is computable (Lead 1: 18, Lead 2: 17, as E102). Every arm is scored on exactly those quarters; an arm not computable on all of them is reported with its count and excluded from the decision.

## 3. Statistics

Per arm: accuracy (Wilson 95% CI), balanced accuracy, HIGH and LOW recall, Brier, calibration-in-the-large, calibration slope (logistic regression of y on logit(clip(score, 0.01, 0.99)), when both classes exist). Paired vs SERVED and vs other named arms: mean quarter Brier difference d; bootstrap 95% CI (2,000 draws, seed 2026); **exact sign-flip permutation p** for mean d (all 2^n patterns); sign test counting only |d| > 1e-12. Periods (by target): **transition** = through 2023-Q4; **2024+** = 2024-Q1 onward; mean d and quarter wins per period.

## 4. Indicator checks and sensitivity (reported, never used to select)

- Overlap: Spearman among A1, A2, A3, pLVL, pREL, pPERS (province rows) and among the regional raw LVL, REL, PERS, A2.
- PERS threshold {3, 4, 5, 6}% × window {2, 4, 6} quarters inside FB2.
- Trailing-base burden REL8 = 100 × ((food / all)(t−1) / mean of (food / all) over t−8..t−1 − 1), ≥ 4 quarters, inside FB2 in place of REL (addresses the 2021-Q1 base and the trend).
- 4% rationale: the ceiling of the BSP inflation target band (3.0% ± 1.0 point). It is a policy band for headline inflation, applied here to food inflation: a convention, not a food-security threshold.

## 5. Separate evaluations (reported side by side, never pooled)

(a) index with SWS input vs SWS; (b) index without SWS input (FB2-noH4, FB2-noH3, FB2-noH-EQ); (c) trained models: E102 model arms re-audited (per-origin training size, class balance, first forecast, test-set classes), **no new trained model**; (d) production LightGBM price forecast: on its own price label (`final_evaluation.json`) and, separately, vs SWS (E102).

## 6. Decision rule (fixed now; Lead 2 primary)

- G1: FB2 vs SERVED: CI below 0 **and** permutation p < 0.05.
- G2: FB2 vs S-A1only **and** vs S-noA: mean d < 0 **and** permutation p < 0.10 for each.
- G3: FB2 − SERVED mean d ≤ 0 in both periods.
- G4: Lead 1 FB2 vs SERVED CI not entirely above 0.
- **Adopt FB2 as a candidate FIRI revision for prospective testing:** G1 ∧ G2 ∧ G3 ∧ G4.
- **Reject FB2:** FB2 − SERVED mean d ≥ 0 (not reproduced), or ¬G2 with FB2's Brier ≥ the lower of S-A1only and S-noA (the gain is attributable to removing indicators, not to REL/PERS). The removal arm with the lowest Brier is then reported as the experimental alternative, under the same "experimental only" status.
- **Retain FB2 as an experimental alternative** otherwise.
In every case SERVED stays in production; no result here is a validated future forecast until sealed quarters are scored.

## 7. Not done

No new data, no pre-2021 data, no trained model fitted, no threshold other than 0.5 for the class, no served file changed, no E102 output touched.
