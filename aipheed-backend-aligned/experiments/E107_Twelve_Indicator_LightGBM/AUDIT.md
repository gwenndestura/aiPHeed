# E107 Deliverable A: methodology audit (written before any model change)

**Date:** 2026-10-25. **Branch audited:** `aipheed/simple-methodology` @ `9433f9e` (E106), which is based on `main` @ `0239273`, the branch Render deploys from. **Work branch:** `aipheed/e107-twelve-indicator-lightgbm`, created from `9433f9e`. Untracked at the start: `docs/aiPHeed_Complete_System_Guide.docx`, `node_modules/`. Neither was touched.

**Requirement basis:** Chapter I §1.5.2 of the thesis (extract: `experiments/Lead1_Objectives_Assessment/chapter1_1_5_2_extract.txt`).
- Objective 2 names LightGBM and requires "forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable".
- Chapter I sets no accuracy threshold. The 75% figure comes from the old Chapter III Algorithm 3 and from the user's briefs. It is reported here as a reference requirement, not as a Chapter I criterion.

Every statement below was checked against code or data in this worktree. File paths are relative to the repository root.

## 1. What is served today

| Layer | What it is | Code | Output on the map |
|---|---|---|---|
| FIRI v2 | Weighted average of 12 indicator scores, each a percentile of the indicator's own earlier values. Domain weights come from correlation with later regional SWS hunger. | `backend/app/ml/inference/firi.py`, `thesis_system.py` | **Yes.** The headline number, class and drivers. |
| E56-TUNED LightGBM | Binary classifier of provincial **food-price pressure (PS)** two quarters ahead | `backend/data/e56/model/*`, `experiments/E56_LightGBM_Optimization/runner/e56_lib.py` | Only as FIRI indicator **A1** |
| E56 combined score | P_price (LightGBM) × P_hunger (I7 regional regression) | `backend/data/e58/e58_record.json` | Stored as `price_pressure_score` and in early-warning text |
| E106 simple method (this branch) | P_hunger (persistence) × P_price (LightGBM on 6 inputs) | `backend/app/ml/simple_method.py` | Not served. Read-only routes `/api/v1/simple/*`. |

## 2. Q&A on the implementation

**What exact target does LightGBM predict?**
- The served LightGBM (E56) is trained on **PS** (`PriceLGB2.fit` uses `y = fit["PS"]`).
- PS: province food CPI YoY above the province's 2021–22 P60, **or** food-minus-headline YoY above its P60, in the target quarter.
- PS is a food-price-pressure label. It is not a food-insecurity outcome.
- The combined score is evaluated on T43 = PS **and** SWS Balance Luzon hunger > 11.3%. `data/thesis/final_evaluation.json` itself states that on every evaluated row hunger was above 11.3%, so **T43 = PS on every evaluated row**.

**What are the 12 intended indicators, and where is each generated?** The authoritative list is the FIRI v2 set, `firi.LABELS`, built by `firi.raw_indicators()`:

| Code | Indicator | Raw value | Generated from |
|---|---|---|---|
| A1 | Food-price-pressure forecast | E56 LightGBM probability | E56 model |
| A2 | Headline inflation above usual | headline YoY − province 2021–22 P60 | PSA CPI (`F_now − gap_now`) |
| A3 | Wholesale rice price change | `rice_whsl_yoy` | PSA rice prices |
| V1 | Poverty and population density | 0.6 poverty + 0.4 density (min-max) | `data/inputs/lgu_vulnerability.csv` |
| C1 | PAGASA El Niño alert/advisory in force | 0/1 | `climate_watch.hazard()` |
| C2 | Typhoons within 300 km | `tc_count` | IBTrACS |
| C3 | Palay/corn production drop | −min(palay, corn YoY) | PSA |
| C4 | Fisheries production drop | −fish YoY | PSA |
| E1 | Unemployment change (national) | `ur_yoy` | PSA LFS |
| E2 | Remittance decline (national) | −remit USD YoY | BSP |
| N1 | FSSI-v3 | bias-weighted XLM-RoBERTa intensity | `app/news/pipeline_v3.fssi_v3()` |
| H1 | Regional hunger outlook above 11.3% | P(hunger > 11.3) | `thesis_system.regional_hunger()` |

**Which indicators enter the LightGBM feature matrix?** The E56 schema (`backend/data/e56/model/feature_schema.json`) has 30 columns.
- **Present** (same raw series): A2 (via `F_now` and `gap_now`), A3, C2, C3, C4, E1, E2.
- **Related but different:**
  - C1: E56 uses NOAA ONI `enso`, not the PAGASA advisory.
  - N1: E56 uses the five news trigger shares and the headline count, not FSSI-v3.
- **Absent:**
  - A1 is the model's own output.
  - V1 enters only in configurations with `pov="AS"`; served configuration 23 has `pov=null`, so it does not.
  - H1 is not a LightGBM input. Hunger enters through the separately multiplied I7 regression.
- **Result:** at most 7 of the 12 families are LightGBM inputs.
- **Extra columns outside the 12:** rice-policy dummies, interactions, `aqua_yoy`, `under_yoy`, `fx_yoy`, `remit_php_yoy`, `enso_l2`, `tc_count_l1`.
- The System Guide reports that the saved 2027-Q1 booster makes **no split on any news column**.

**Which indicators are used only in FIRI or the dashboard?** V1, C1 (PAGASA), N1 (FSSI-v3) and H1 are used only in FIRI. A1 exists only because the LightGBM output is fed into FIRI.

**Usable observations.**
- SWS production rounds (`definition_A = True`) cover **19 quarters** (2021-Q2..2026-Q3). 2021-Q1, 2022-Q1, 2025-Q2 and 2025-Q3 have no production round.
- Three supplementary 2025 rounds conflict with `docs/DATA_AVAILABILITY.md`; E13 recorded the disagreement.
- T43 on production rounds: **95 province-quarter rows, 18 HIGH (19%)**. HIGH quarters: 2021-Q2 (2), 2023-Q4 (3), 2024-Q2 (4), 2024-Q3 (1), 2024-Q4 (3), 2025-Q1 (4), 2026-Q2 (1).
- Regional outcome R (hunger > 11.3%): 19 quarters, 12 HIGH. **Every quarter from 2023-Q4 to 2026-Q3 is HIGH.**
- The five provinces share one hunger value per quarter, so the number of independent outcome observations is the number of quarters, not rows.

**What split is implemented, and is the evaluation chronological?**
- E56 and E106 use a rolling origin with an expanding window. Each origin trains on labels complete before its issue date.
- E56 selects its configuration per origin from 72 candidates by embargoed forward log-loss on training quarters only (nested).
- FIRI v2 weights are walk-forward.
- The older MODEL-A path (`backend/THESIS_CONNECTION.md`) used a single blind 2025 holdout on a CPI-only label.
- No random shuffling was found in the current paths.

**Which quarters were used for training, tuning, threshold selection and testing?**
- E56 Lead-2 evaluation rows: 2024-Q3..2026-Q3 (45 rows, 9 quarters, all-round labels).
- Threshold: fixed at 0.5.
- Tuning: nested within origins.
- There is **no untouched historical quarter**. Every quarter through 2026-Q3 was scored repeatedly in E38–E106.

**Were evaluation outcomes consulted during feature engineering or model selection?** Yes, across experiments. Examples recorded in the experiment memory and reports:
- E51/E52 switched the target to PS after the thesis label saturated.
- The E56 search space was built after the E55 results.
- The E58 early-warning rule was designed after E56's misses.
- FIRI v2 candidate C3 was chosen among candidates on evaluation outcomes.
- E106 Addendum 1 (SM-B) was designed after SM failed.

Within one experiment, the selection was usually nested. Across experiments, the same quarters drove successive design choices, so **every reported accuracy carries selection bias**.

**Missing values, substitutions, publication delays.**
- Inputs are cut at the issue date by `e41_lib.Data.cut()` (CPI through month 2 of quarter t; SWS rounds posted before the issue).
- E2 is missing after 2025-Q4: the series was not acquired beyond that.
- N1 has a value for only 20 of 115 province-origins (status SUFFICIENT).
- C2 is incomplete for 2026-Q3.
- V1 uses 2021 SAE and 2024 POPCEN at every origin. This is a disclosed timing deviation: these were published around 2025.
- Real-time vintages were not reconstructed. Values are the latest published, and later revisions of production or LFS data cannot be excluded.
- Lucena's poverty value is a substitute.

**Reproducibility gap.**
- The E41–E56 feature chain reads three files (`pagasa_climate`, `bsp_macro`, `psa_rice_prices`) from `aipheed-backend-aligned/data/processed/`. That folder is **untracked on every branch** and exists only in the main checkout (`C:\Users\admin\aipheed`).
- E106 concluded that "the monthly CPI panel used by E56 is not in any branch". This is **incorrect**: the monthly index and YoY files are tracked (`E41_Lead2_Audit/data_acquired/`, `E40_SWS_CPI_Tiers/data_acquired/`). Only the three extra files were missing.
- E107 copies those three files byte-for-byte into `E107_Twelve_Indicator_LightGBM/data_inputs/`, with SHA-256 hashes.

## 3. Do the existing reports support their claims?

| Claim | Where | Finding |
|---|---|---|
| "Furthest reliable lead = Lead 2" (E56 0.756 at Lead 2) | `docs/methodology/SIMPLE_METHODOLOGY.md` (E106) | **Not supported.** 0.756 is 34/45, Wilson CI roughly 0.62–0.86. Balanced accuracy is 0.726. No significance test was required. The labels were rebuilt and agree with the served T43 on only 37/45 rows. All quarters had been examined. The served `final_evaluation.json` (E63 rule) states "no lead meets the reliability criterion". The two documents contradict each other. |
| LightGBM forecasts "food-insecurity risk" | E56 record, guide | Its training target is price pressure. On evaluated rows T43 = PS, so the evidence is evidence about **price pressure**. |
| FIRI Lead-2 accuracy 0.941 vs the regional outcome | System Guide §9 | Always-elevated scores 0.706. H1 alone had a lower Brier. The FIRI weights are fitted to the same SWS outcome. The guide itself discloses this. |
| "Uses 12 indicators" | Guide, dashboard | True for **FIRI**. False for LightGBM (at most 7 families, section 2). |

## 4. Defects and risks found

1. **Indicator gap:** LightGBM, the model the objectives name, does not use V1, C1 (PAGASA), N1 or H1.
2. **Target mismatch:** the model is trained on a price label and described as forecasting food-insecurity risk.
3. **No untouched test period:** all historical quarters have been examined, so retrospective results are development evidence only.
4. **Contradictory reliability verdicts:** E106 says Lead 2; E63 / `final_evaluation.json` says none.
5. **Untracked inputs:** the E56 chain depends on files outside git (fixed for E107 by copying them, with hashes).
6. **Tiny effective sample:** 19 outcome quarters and 18 HIGH T43 rows. A tree model with 30 inputs (E56) is at high risk of overfitting.
7. **Outcome series ambiguity:** E56/E106 used all rounds, including the three disputed supplementary rounds. The served hunger input uses production rounds only.
8. **Legacy contradiction:** `label_generator.py` (old MODEL-A path) is still self-contradictory (methodology audit 2026-09-04). It is not on the served path.

## 5. Consequences for the redesign (E107)

- Put **all 12 families** into one LightGBM. Represent A1 by its non-learned structural inputs rather than another model's output (section 4 of the protocol).
- Keep the Chapter I target (T43), but call it what it is: a **composite food-insecurity risk proxy**.
- Test the same pipeline separately on the **only observed food-insecurity outcome** (R, regional SWS hunger).
- Evaluate Leads 1–4 with one rolling-origin design and a reliability rule fixed before scoring. Include significance and a quarter-generalization check.
- Hold out the last four outcome quarters until all decisions are fixed.
- Seal the forecasts for future quarters as the only genuinely unseen test.
