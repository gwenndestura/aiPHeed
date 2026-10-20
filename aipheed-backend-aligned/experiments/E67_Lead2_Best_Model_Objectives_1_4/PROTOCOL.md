# E67 protocol: Lead-2 goal test, five-trigger ablation and missing-data audit

**Date:** 2026-10-20
**Branch:** `best-model-objectives-1-4-lead2`, created from `aiPHeed/best-model-methodology-review` @ 1ac3444.
**Frozen before any E67 arm is scored.** The SHA-256 of this file (LF-normalised) is in `runner/PROTOCOL_SHA256.txt`, and every runner checks it.
**Requirement basis:** Chapter I §1.5 and §1.7, verbatim in `E25_Reliable_Forecasts_2021_2026/thesis_source/CHAPTER_I_verbatim.txt` (source `THESIS 2 (11).pdf`, sha256 88dd0b62…, still the newest thesis file in Downloads on 2026-10-20).
**User requirements of this task (not Chapter I criteria):** Lead-2 operational horizon; accuracy greater than 75% together with class-sensitive metrics and a valid protocol.

## 0. Evidence status, declared before scoring

Every evaluation row below (targets 2024-Q2..2026-Q3, 10 origins, 50 province-quarters) has already been examined by E56–E66. Nothing scored in E67 is unseen evidence. E67 results are **development evidence**, and no E67 result may be called "validated". The first independent test is the frozen 2026-Q4 and 2027-Q1 forecasts (E56/E58/E64 seals), which E67 does not touch.

Data window: 2021-Q1 to the authorized limit of 2026-10-14. No pre-2021 row is loaded (frame starts 2021-Q3, inherited from E53/E56).

## 1. Fixed design (inherited, unchanged)

- Origins: the 10 E57 origins t = 2023-Q4..2026-Q1 (issue dates 2024-01-01..2026-04-01), target t+2.
- Forward origins, reported but not scored: 2026-Q2 (target 2026-Q4) and 2026-Q3 (target 2027-Q1).
- Model procedure: E56-TUNED. That is P(T43) = P_hunger × P_price, with nested per-origin selection over the 72 E56 configurations by embargoed forward log-loss on training targets only (`e56_lib.tuned_forecast`).
- Labels: T43 (primary, approved), with PS (provincial food-price pressure) reported as a secondary reading. Thresholds are the frozen 2021–22 E40 spec. No threshold is changed in E67.
- Scorer: `E66_Best_Methodology_Review/runner/e66_lib.py` (`metrics`, `paired`, `holm`), unchanged.

## 2. R1: five-trigger-group ablation at Lead-2 (new)

The arms re-run the E56-TUNED procedure at every origin with one trigger group removed from **both** parts, price and hunger. Search space, folds, seeds and tie-breaks are E56's.

| Arm | Groups used |
|---|---|
| A0 | all (must reproduce the sealed E57 `E56_p` to 1e-9 on all 50 rows; otherwise E67 stops) |
| X_climate | all minus climate |
| X_fish | all minus fish_kill |
| X_employment | all minus employment |
| X_ofw | all minus ofw_remittance |
| X_news | all minus news (government data only) |
| M_only | market (+ rice-policy block) only |

If a group's removal leaves the hunger part with no columns, the hunger part uses the remaining groups (`market` is never removed).

**Effect rule:** a group is said to **help** Lead-2 forecasting only if removing it makes Brier worse with a quarter-cluster 95% CI above 0 and a quarter sign test p < 0.05 (Holm over the six ablations). It is said to **hurt** under the mirror condition. Otherwise its effect is "not distinguishable from zero". Accuracy and balanced accuracy differences are reported but are not the rule.

**Contribution:** for A0 at every origin (including the forward origins), the price part's exact TreeSHAP is reported per group: mean |contribution| on the five test rows and the number of tree splits on the group's features.

## 3. R2: coverage and missing-data audit (new)

For every trigger-group feature, R2 reports:
- the NaN share and the exact-zero share in the training frames and the test rows at each origin;
- the geographic level (provincial / regional / national) and cadence;
- the latest observed period at the 2027-Q1 issue (2026-10-01).

It flags any feature where an absent observation is encoded as 0. A **sensitivity** run (not served, does not change a sealed forecast) re-runs A0 at the 2026-Q3 origin with `tc_count` of the incomplete quarter 2026-Q3 set to NaN (D-E66-5).

## 4. R3: the Lead-2 accuracy goal test (pre-registered)

**Readings tested** (all on the same 50 rows; probabilities and decisions from sealed files or E66 `r1_rows50_all_arms.csv`):

| Reading | Description |
|---|---|
| E56 | P(HIGH) ≥ 0.5 |
| EW | E58 two-signal reading, P_price ≥ 0.5 |
| BPROJ | CPI-projection rule |
| R1 arms | the R1 ablation arms |

**Baselines:** persistence, majority (always LOW), climatology, province climatology.

**Goal G ("legitimate Lead-2 accuracy above 75%")** is met by a reading only if **all** of the following hold:

| Criterion | Requirement |
|---|---|
| G1 | accuracy on T43 > 0.75 |
| G2 | balanced accuracy ≥ 0.70, HIGH recall ≥ 0.60 and LOW recall ≥ 0.60 |
| G3 | accuracy minus majority-baseline accuracy has a quarter-cluster bootstrap 95% CI above 0 (2,000 draws, seed 67), and the same against persistence |
| G4 | the model and decision rule were specified before the evaluation rows were inspected |
| G5 | the target is the approved T43 (not PS) |

**G4 coding, fixed now from the experiment records:**
- E56 (the E55 structure with E56 tuning) was tuned on 45 of these rows (E56 reported its 0.778 on them), so its G4 is **partial**.
- EW was designed after E58 diagnosed E56's misses on these rows: G4 **no**.
- BPROJ was defined in E58 as a benchmark: G4 **no**.
- The R1 ablation arms: G4 **partial** (E56 procedure).

**Outcomes:**
- A reading that meets G1–G3 and G5 but fails G4 is reported as **"above 75% on development rows only; not a legitimate demonstration"**.
- Meeting all of G1–G5 is still development evidence, because the rows were seen (section 0).
- Uncertainty: the Wilson interval and the quarter-cluster bootstrap interval of accuracy are reported. McNemar exact tests (two-sided) against the majority class and against persistence are also reported.

## 5. R4: El Niño trace (reproduction plus the R1 forward origins)

R4 reproduces E66 r5 for targets 2026-Q3, 2026-Q4 and 2027-Q1 per province, adding the climate-group and news-group contributions from R1 at the forward origins. It also reports how P_price at 2027-Q1 changes when the climate group is removed (X_climate) and in the D-E66-5 typhoon sensitivity.

PAGASA items come from E65 `sources/SOURCES.md` and `enso_context.PAGASA_ENSO`. Any new PAGASA item is fetched only from pagasa.dost.gov.ph, recorded with its date, and used only for issue dates after it. No PSA, BSP or SWS "latest" searches are made.

## 6. Selection rule for serving (frozen)

- The served numbers stay E56-TUNED / E58-EW (record `data/e58/e58_record.json`) unless an R1 arm is better than A0 by the effect rule of section 2, measured on Brier against T43, with G2 not worse. If one is, it is reported as a candidate for the next record build and **not** served in E67, because a new record would alter frozen forecasts.
- E67 serving (`AIPHEED_LEAD2_MODEL=e67`) is the E66 layered system plus:
  - (a) the R2 coverage and missing-data disclosure;
  - (b) the measured R1 trigger-group effects;
  - (c) the model identity.

  All of these go into existing text fields and one optional API field. There are no new UI elements, colours or legends, and the production default (E38) is unchanged.

## 7. What E67 will not do

- No change of label, threshold, horizon or evaluation rows.
- No forcing of HIGH for El Niño.
- No overwrite of any sealed or frozen file of E38–E66.
- No production default switch.
- No deployment.
