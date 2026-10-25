# Final recommendation

## 1. Verdict

**The 75% target was not reached, and with this outcome it cannot be.**

**The model.** The required LightGBM (all 12 families, dated news, chronological evaluation, leakage-audited) was built and tested exactly as pre-registered.

**Performance on 2021–2026 (ELEVATED accuracy)**

| Lead | FIL | Latest-reading baseline |
|---|---|---|
| 1 | 0.32 | 0.61 |
| 2 | 0.40 | — |
| 3 | 0.44 | — |
| 4 | 0.50 | — |

**Performance on 70 untouched quarters (2003–2020).** The same method trained on 22 years of SWS history scores 0.50–0.55, which is chance.

**Why.** A simulation of a perfect forecaster gives a ceiling of 0.58–0.64 at Lead 1. Whether hunger next quarter is above its recent average is set by new shocks and survey noise that no available indicator anticipates.

**No reliable lead time exists** under the frozen rule.

**What would not be legitimate**
- Changing the label, the threshold or the test quarters to reach 75%.
- Calling persistence's 0.61 "the model's" accuracy.

## 2. Methods to keep in the thesis

| Role | Method | Status |
|---|---|---|
| Proposed model (Objective 2) | FIL, the 12-family LightGBM | Evaluated. Fails the target; reported honestly. |
| Hunger outlook shown to users | **The latest SWS reading per area**, with its age and an error range. E113's conformal band is calibrated at Lead 1 only. | Simplest; no method beat it on 2021+ |
| Supporting level evidence | FIL-LONG, which beats the latest reading at Leads 1–2 on untouched data (MAE 4.22 vs 4.57, p = .031; 4.52 vs 4.87, p = .009). A two-reading average does better (4.14, 4.34). | Secondary arm, flagged for adviser approval (pre-2021 data) |
| Economic access, by province | PSA food-price squeeze (food inflation above headline inflation); persistence outlook 70% at Lead 1 and 63% at Lead 2 | Supporting indicator, **not** hunger |
| News | A dated, de-duplicated "what has happened since the last survey" panel | Descriptive; no forecast value |

## 3. What DA Region IV-A can responsibly use

**Use**
1. **The latest SWS hunger reading for Balance Luzon.** Always state the survey month and that it is about 3 months old at issue. For the next quarter, expect the reading to move by about ±4–6 points without warning.
2. **The provincial PSA food-price squeeze** (Cavite, Laguna, Batangas, Rizal, Quezon) as an economic-access signal. It is usually right about next quarter (70%), but it does not indicate hunger.
3. **The news panel** as situational awareness: disasters, crop and supply problems, assistance since the last survey. These track hunger in the same period.

**Do not use**
1. ELEVATED probabilities or "risk forecasts" as predictions of whether hunger will rise.
2. Any lead time claim.
3. Any provincial or municipal hunger figure. None is measured; the FIRI v2 rankings are unvalidated vulnerability estimates.
4. News or food prices as evidence that hunger will rise.

## 4. Evidence still missing

| Gap | Why it matters | Source |
|---|---|---|
| A local food-insecurity outcome measured repeatedly | Needed to validate provincial or municipal forecasts (Objective 3), and could have predictable variation | CBMS 2024 LGU food-security aggregates; PSA provincial FIES |
| More outcome quarters with real-time news | Required to test any news lead properly | Prospective SWS rounds; a real-time news archive from now on |
| Adviser decision on pre-2021 SWS history | The secondary arm and its untouched test use it | Adviser |
| Prospective confirmation | The only untouched test of the 2021+ method | Seal `c73a0709…`, scored from SWS 2026-Q4 (around January 2027) |

## 5. Delivered in this run

- **Branch:** `aiPHeed/final-food-insecurity-lightgbm` (from `1baca5e`). E107–E114 are preserved. Nothing is merged, deployed or served.
- **Experiment folder:** `aipheed-backend-aligned/experiments/FINAL_FOOD_INSECURITY_LIGHTGBM/`
  - Protocol `86de5c8c…`, plus Addendum 1 (`e21dfe9c…`) and Addendum 2 (`705f58d2…`), each frozen before it was run.
  - Nine reports.
  - Prediction-level CSVs, the feature map and the data-source record.
  - The runner and the prospective scorer.
- **Tests:**
  - `backend/tests/unit/test_final_fi_lgbm.py`: 13 passed.
  - Full backend suite: 763 passed, 18 skipped, 0 failed (`out/backend_test_suite.txt`).
