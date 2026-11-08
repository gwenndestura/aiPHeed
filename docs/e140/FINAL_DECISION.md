# E140: the zero-tree problem and final decision (2026-11-04)

**Run record.**
* Protocol E140-P1 (`PROTOCOL.md`), locked before the run. Run once.
* Results: `backend/data/e140/out/results.json`, `diagnostics.json`, `oof_*.csv`.
* E139 is preserved unchanged and used as the baseline (same target, rows, folds and thresholds).
* All results are development evidence.

## Decision: **C, not achievable with the current data**

* **What improved.** The LightGBM trees now learn real structure and give the best point estimates of any model:
  * LORO (unseen region): EB 0.182, AUC 0.96, accuracy 0.87, ECE 0.04.
  * Against the previous survey (persistence), they are significantly better.
* **Why the decision is still C.** They fail the pre-registered requirement that trees beat the linear prior with
  confidence: −0.010, 95 % CI [−0.031, +0.012].
* **Island transfer collapses** (AUC 0.35 on an unseen island group).
* **Production and the dashboard stay unchanged.** In the registry, `e140-lgbm-native-1.0` is rejected and
  `production` is `null`.

## 1. Why E139 selected zero trees (diagnosis, `diagnostics.json`)

| Possible cause | Evidence | Verdict |
|---|---|---|
| Too few independent observations | 125 rows, 62 decisive, 16 regions, 8.3 rows per feature | **Contributing.** The CI width (SE 0.011) is the binding limit. |
| Too little variation in the target | var(y) 0.271; the prior explains 43 %; the residual is 0.154, of which survey error is only 22 % | Not the cause: there is residual variance to learn |
| Too much dependence on the linear prior / the residual-learning design | Trees on the prior's residual worsen out-of-fold Brier at every count (10–300: 0.194–0.201 vs 0.192) | **Main cause.** The prior already holds all the feature signal, and no feature explains its residual (\|ρ\| ≤ 0.23, Holm p ≥ 0.17). |
| Step functions unsuited to a near-linear signal | Trees without the prior keep improving with more trees (0.257 → 0.206) | **Contributing.** Constant-leaf trees needed many trees and a compact feature set. |
| Loss or weighting | Huber and unweighted fits give the same curves | Ruled out |
| Over-restrictive constraints | min_child_samples 5 gives the same curve | Ruled out |
| Uninformative quarterly indicators | No time-varying feature explains the residual. Removing all six makes no difference (below). | Confirmed |
| Region-specific structure | 31 % of the residual is between regions; 9 % between island groups | **Real, but only partly learnable from features** |

## 2. The controlled improvement and the four-way comparison

**The candidate, LGBM-AUTO.**
* Inside each training fold it chooses, by nested inner CV, between:
  * **linear trees** (LT): all features + island group;
  * **compact constant-leaf trees** (GBC): poverty, history, island group, food CPI, cyclones; learning rate 0.02.
* Zero trees are not allowed.

**Trees chosen per fold.**

| Scheme | Choices |
|---|---|
| LORO (16 folds) | GBC × 300 in 8, GBC × 100 in 6, LT × 100 in 1, LT × 30 in 1 |
| LOPO (78 folds) | GBC × 100 in 63, LT × 30 in 9, GBC × 300 in 6 |
| **Final fit** | **GBC, 100 trees** |

**Results by scheme.** EB / AUC / accuracy (decisive rows) / ECE / training gap.

| Model | LORO (unseen region) | LOPO (unseen province) | ISLAND | V2 2015 → ENNS | TFWD 2015+18 → 19 |
|---|---|---|---|---|---|
| 1. Linear prior alone (E139 = prior) | 0.192 / 0.915 / 0.774 / 0.066 / 0.018 | 0.185 / 0.933 | **0.221 / 0.787** | 0.177 / 0.840 | 0.148 / 0.857 |
| 2a. LightGBM, no prior, linear trees | 0.194 / 0.933 / 0.839 / 0.038 / 0.044 | 0.170 / 0.957 | 0.314 / 0.332 | 0.171 / 0.923 | 0.148 / 0.971 |
| 2b. LightGBM, no prior, constant leaves | 0.182 / 0.960 / 0.871 / 0.041 / 0.039 | 0.167 / 0.976 | 0.279 / 0.545 | 0.183 / 0.818 | 0.142 / 0.943 |
| 3. LightGBM with prior (30 trees forced) | 0.212 / 0.901 / 0.806 / 0.136 / 0.051 | 0.200 / 0.930 | 0.254 / 0.703 | 0.203 / 0.806 | 0.165 / 0.886 |
| 4. Best E139 reference, RR-F | 0.193 / 0.941 / 0.871 / 0.060 / 0.030 | 0.184 / 0.953 | 0.234 / 0.784 | 0.177 / 0.849 | **0.128** / 0.871 |
| **LGBM-AUTO (candidate)** | **0.182 / 0.960 / 0.871 / 0.039 / 0.039** | 0.170 / 0.975 | 0.307 / 0.353 | 0.171 / 0.923 | 0.148 / 0.971 |

**LGBM-AUTO minus reference, expected Brier score [95 % cluster-bootstrap CI].**

| vs | LORO | LOPO | ISLAND | TFWD |
|---|---|---|---|---|
| Linear prior | −0.010 [−0.031, +0.012] | −0.015 [−0.037, +0.006] | **+0.087 [+0.020, +0.164]** | +0.001 [−0.051, +0.057] |
| RR-F | −0.011 [−0.032, +0.007] | −0.013 [−0.031, +0.003] | +0.073 [+0.006, +0.149] | +0.020 [−0.032, +0.063] |
| Prior + forced trees | **−0.030 [−0.057, −0.003]** | **−0.029 [−0.052, −0.006]** | +0.053 | −0.017 |

**Robustness of the gain over the prior (LORO).**
* Dropping any single region from scoring: the gain stays negative (−0.015 to −0.004).
* Dropping one island group or one survey round: the gain reverses in some cases (up to +0.012 and +0.004).
* So the gain is consistent across regions, but it depends on which island groups and survey rounds are in the
  scored set.

## 3. Gate (E139 thresholds plus the tree requirement)

| Check | Result |
|---|---|
| T1 trees selected | pass (final: 100 trees; trees in every fold) |
| **T2 trees beat the linear prior (CI < 0)** | **fail**: −0.010 [−0.031, +0.012] |
| G1 beats the national base rate | pass |
| **G2 beyond the region's previous level** | **fail**: [−0.095, +0.027] |
| G3 non-inferior to the previous survey | **pass**, and significantly better: [−0.136, −0.024] |
| G5 AUC 0.96 [0.90, 0.99], BA 0.87, recall 0.875, precision 0.92 | pass |
| G6 ECE 0.039 | pass |
| G9 forward in time (TFWD AUC 0.97) | pass |
| G4 not worse than the best benchmark | pass |
| G7 overfitting gap 0.039 | pass |
| **G8 island transfer** | **fail** (AUC 0.35) |

## 4. Forecasting

* **The quarterly indicators add nothing.** LGBM-AUTO without the six time-varying indicators (CPI YoY, rainfall,
  cyclones over 4 quarters, agriculture and fisheries YoY) scores:
  * on ENNS rows: +0.004 [−0.010, +0.018];
  * on TFWD: −0.001 [−0.004, +0.002].
* There is no quarterly forecasting skill. The maximum validated forecasting horizon remains **none**.
* What the model can do is anticipate the next survey's measured relative position from the previous one plus
  structural indicators. That is a survey-to-survey estimate, not a quarterly forecast.

## 5. Exact missing evidence that blocks success

1. **More independent measured rounds** (T2, G2).
   * The tree gain over the prior has SE 0.011. Confirming the observed −0.010 needs an SE of about 0.005, roughly
     **4–5 times the current number of independent observations**.
   * Each additional national provincial HFIAS/FIES round adds about 80 rows. Candidates: FNRI ENNS 2021 provincial
     reports, NNS 2023 provincial estimates, PSA 2026 FIES.
2. **Province-level drivers that explain island-group differences** (G8).
   * The trees use the island group itself, which cannot be learned for an unseen island group.
   * Province-level measures of remoteness or market access, conflict or displacement, and household expenditure or
     dietary patterns would be needed to replace that proxy.
   * Not relevant within Luzon (CALABARZON's own island group), but the gate requires it.
3. **A measured outcome more frequent than every 3–4 years**, for any quarterly forecast. With HFIAS rounds 3–4
   years apart, a quarterly lead cannot be validated in principle.
4. **Provincial employment, remittance and news series covering the survey years.** Without them, these groups
   cannot be tested as inputs (as in E139).

## 6. Status of the system

* **Not in production.** Registry `production: null`. The public outlook says `validation_pending`. The dashboard is
  unchanged.
* **Kept for review (admin routes):** E139's outputs. These include the 2026-Q4 provincial structural estimates
  with uncertainty, and all 142 LGUs labelled as municipal vulnerability.
* **Sealed predictions** for confirmation against the next provincial round: E138 `e324433c…`, E139 `0bcb5584…`.
* **Tests:** full backend suite **849 passed** (6 new E140 tests).
* **Files:**
  * new: `backend/app/e140/` (`diagnose`, `model`, `evaluate`, `gate`), `backend/tests/unit/test_e140.py`,
    `backend/data/e140/`, `docs/e140/`;
  * changed: `backend/app/registry/catalog.py` and `backend/data/registry/registry.json`.
