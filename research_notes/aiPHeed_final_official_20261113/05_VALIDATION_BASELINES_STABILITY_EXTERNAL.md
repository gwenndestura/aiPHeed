# 05 — Chronological validation by round, baselines, stability, external plausibility (deliverables 6, 8, 12, 15)

All numbers are reproduced from the stored fits. Details are in `../aiPHeed_final_reliability_20261113/` reports 02, 03, 05 and 07.

**Evidence type: (1) retrospective historical validation**, except where stated. The 72 outcomes were reused during development, so this is not independent validation.

## 1. By survey round (Lead 1)

| Round | n | HIGH | Accuracy | HIGH recall | HIGH precision | Always-LOW | Persistence |
|---|---|---|---|---|---|---|---|
| 2018 | 22 | 8 | 0.864 | 8/8 | 0.73 | 0.636 | 0.591 |
| 2019 | 25 | 13 | 0.840 | 11/13 | 0.85 | 0.480 | 0.760 |
| 2021 | 25 | 4 | 0.880 | **1/4** | 1.00 | **0.840** | 0.520 |

By class (pooled): HIGH F1 0.800; LOW F1 0.894; macro F1 0.847.

**By province:** 14 of 16 regions are at 0.75 or above. The two below are:
- **Bicol, 2/5:** false alarms in Camarines Norte and Sorsogon 2018, plus the Masbate 2021 miss.
- **Northern Mindanao, 3/5:** the Lanao del Norte and Misamis Oriental 2019 misses.

See `REL_by_province_L1to5.csv` and `REL_by_region_L1.csv`.

## 2. Baselines (Lead 1, identical rows; paired bootstrap)

| Model | Accuracy | F1 (HIGH) | Macro F1 | AUC | PR-AUC | Brier | FINAL ΔBrier [95 % CI] |
|---|---|---|---|---|---|---|---|
| **FINAL** | **0.861** | **0.800** | **0.847** | **0.898** | **0.846** | **0.123** | — |
| Always-LOW | 0.653 | 0 | 0.395 | — | 0.347 | 0.347 | −0.224 [−0.338, −0.112] |
| Persistence | 0.625 | 0.640 | 0.624 | 0.827 | 0.705 | 0.253 | −0.130 [−0.197, −0.069] |
| PSA-only logistic | 0.556 | 0.600 | 0.550 | 0.762 | 0.675 | 0.274 | −0.150 [−0.211, −0.088] |
| NLP-only logistic | 0.639 | 0.594 | 0.634 | 0.703 | 0.611 | 0.244 | −0.121 [−0.183, −0.063] |
| Logistic regression | 0.611 | 0.600 | 0.611 | 0.803 | 0.689 | 0.320 | −0.197 [−0.288, −0.116] |

**FINAL adds genuine information beyond "repeat the last survey".**
- It is significantly better than persistence on Brier and accuracy at every lead from 1 to 5.
- Persistence finds more HIGH provinces (0.96 vs 0.80) but at precision 0.48.

**Calibration (Lead 1):**
- ECE 0.080; mean p − rate +0.046; slope 1.25; Cox p 0.41.
- The 0.4–0.5 probability bin over-forecasts.

## 3. Stability (evidence type 2)

| Test | Result | Overall accuracy stable? | HIGH detection stable? |
|---|---|---|---|
| Five seeds | L1 0.847–0.861; L5 0.736–0.806 | Yes at L1–4 | Yes at L1 |
| Survey-round removal (2021 fold) | accuracy 0.72–0.88 | Yes (≥ 0.70) | **No:** 2021 recall 1/4 to 3/4, up to 8 flips |
| Unseen provinces (own rows removed) | 0.847 accuracy, recall 0.76 | Yes | Mostly (−1 HIGH) |
| Province-cluster bootstrap | L1 accuracy CI [0.778, 0.931]; recall CI [0.615, 0.947] | Yes | Wide |
| Threshold 0.30–0.70 | stable 0.50–0.60; recall collapses above 0.60 | — | Fixed at 0.50 |

**Overall accuracy is stable; HIGH-risk detection is not.** It depends on which rounds are in training and on long-gap extrapolation.

## 4. External plausibility (evidence type 3: context only, never labels; ENNS 2022 not used)
- **FIES 2023, CALABARZON:** 19.1 % (CI 17.0–21.1), the lowest of the regions. Every FINAL CALABARZON forecast is LOW:
  - retrospective 2018/2019/2021: p 0.009–0.114;
  - sealed 2027-Q1 to 2028-Q1: p ≤ 0.007.

  This is consistent, but it cannot test HIGH detection.
- **Excluded:** the 11-13 reliability study also compared FIES 2023 by region (ρ 0.835) and PSA poverty 2023 (ρ 0.60) with FINAL's ENNS 2022 forecast table. **Under this brief's exclusion of ENNS 2022, those two comparisons are withdrawn here and not relied on.**
- **PSA provincial poverty 2021 vs the 2021 test round (25 provinces):** FINAL's forecasts track poverty (ρ 0.87) more closely than the observed HFIAS does (ρ 0.55). This shows plausibility, not skill: the model leans on structural poverty more than the outcome does.
- **SWS Balance Luzon hunger:** it rose from about 11 % (2022) to about 21 % (2026), while FINAL's CALABARZON forecasts are near zero. Different measures; flagged, not adjudicated.
- **Live forecast vs current data:** with the refreshed harvest inputs, the 2027-Q1 CALABARZON shares are 23–28 %. That is well below the 50 % HIGH line and consistent with the 2015–2021 surveys (all CALABARZON provinces LOW).

## 5. Which forms of evidence exist

| Evidence | Status |
|---|---|
| Retrospective historical validation | **Established** (72 province-rounds, 3 rounds, leakage-free computation) |
| Stability and sensitivity | **Established**, with HIGH-detection instability documented |
| External contextual plausibility | **Established** (FIES, poverty, SWS) |
| Independent prospective validation | **Not established.** Pending the next eligible FNRI provincial HFIAS round (report 11) |
