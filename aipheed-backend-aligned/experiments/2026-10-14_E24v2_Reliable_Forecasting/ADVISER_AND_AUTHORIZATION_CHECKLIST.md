# Adviser decisions and data authorizations (E24v2)

## A. Your file-by-file authorizations

| # | Item | What it unlocks |
|---|---|---|
| ☐ **A1** | **SWS Balance Luzon hunger history**, every round from 1998 to 2020 (no later row): `quarter,H,published,source`. Downloaded by you in a browser; SWS pages were not opened here because they can show the protected 2026 rounds. Give the path + SHA-256 in an authorization JSON. | **The pre-registered T1 back-cast (amendment A2): the fastest route to evidence that the approved composite forecast generalizes (C9).** Run `runner/run_bx_t1.py`. |
| ☐ A2 | 2026-Q3 and 2026-Q4 outcomes: September and December 2026 SWS rounds, July–December 2026 provincial CPI (path + SHA-256) | Scoring of the two blind prospective seals (`runner/score_prospective.py`). A claim still needs ≥ 8 scored origins. |
| ☐ A3 | October–November 2026 provincial CPI, the September 2026 SWS round with its publication date, and the 2026-Q3 labels | The live 2027-Q1 forecast at the 2026-12-31 cutoff |
| ☐ A4 | PSA 2021 municipal SAE workbook (`2018 - 2021 SAE_with PSGC_noHUC.xlsx`), downloaded in a browser (psa.gov.ph returns 403 to scripts) | Municipal poverty for the 126 LGUs now ranked by density only (`runner/lgu_rankings_v2.py --sae`) |
| ☐ A5 | Keep or revert the 16 tracked files E23 modified in `aipheed-backend-aligned/` | Clean checkout (instructions in E24 `BUG_FIXES.md` §0) |
| ☐ **A6** | **Confirm the authorization basis for the public PSA tables acquired in E24v2:** provincial CPI 1994–2025 and provincial subsistence/poverty incidence 2018/2021/2023 (`DATA_ACQUISITION_REGISTER.md`). All are pre-2026 official statistics, inside Chapter I §1.7's scope. | Keeps the back-cast results (HB1–HB4) usable in the thesis |
| ☐ A7 | Publication dates of the March and June 2026 SWS rounds, if you can verify them | Those rounds enter the H model at the 2026-07-01 origin; they are excluded for now |

## B. Adviser decisions (Chapter I does not define these)

| # | Decision |
|---|---|
| ☐ B1 | **Reliability rule** for Objective 2-V / H2. Provisional E23 rule: ≥ 8 origins, ≥ 5 per class, AUC lower bound > 0.5, Brier better than persistence (Holm p < 0.05). **E24v2 shows the "better than persistence" part is trivially met by any calibrated model.** Recommend comparing with *calibrated* persistence (B1p). |
| ☐ B2 | "Favorable" and "consistent" for H4/H5 (`instruments/DECISION_RULES.md`) |
| ☐ B3 | Label threshold: training-window median (primary) vs fixed 14.6 |
| ☐ B4 | Whether supplementary SWS rounds may define labels. E24v2 uses them only in an exploratory model variant, never as labels. |
| ☐ B5 | Whether **relative provincial food-price pressure** (D > 0) may be reported as a **secondary provincial indicator**. It is now validated on 94 unseen quarters (accuracy 0.713 vs persistence 0.617). It is not a food-insecurity outcome. |
| ☐ B6 | Chapter I wording issues carried over: the "44%" figure; Objective 4 vs H3 baseline counts; NNS 2019 anchor; SOP Q5's withdrawn second evaluator group |
| ☐ B7 | Prospective holdout plan: score the seals every quarter; a claim needs ≥ 8 origins |
| ☐ **B8** | **Whether the probabilistic component forecaster (PCF) may replace or complement the LightGBM model as the operational forecaster.** Chapter I names LightGBM. PCF is a statistical model that does not use news. On development data PCF is among the best-calibrated arms (Brier 0.104 vs persistence 0.125), but it is not significantly more accurate than persistence. **The required LightGBM comparison (H3) is unchanged.** |
| ☐ **B9** | **LGU vulnerability weights.** Where both are known, density and poverty are strongly negatively related (ρ = −0.76, n = 16), so the approved 0.6·poverty + 0.4·density index mixes opposing signals. Decide whether to keep density, and with what sign or weight, once the SAE workbook is in. |

## C. Participants (unchanged)

| # | Step |
|---|---|
| ☐ C1 | Administer the DA Region IV-A questionnaire (`instruments/`) to the 50 evaluators |
| ☐ C2 | Export the Google Form CSV and run `instruments/score_responses.py` (no imputation; consent required) |

## D. Deployment

| # | Item |
|---|---|
| ☐ D1 | Deploy the dashboard (not done) |
| ☐ D2 | The 20 npm vulnerabilities in `frontend/` (outside the isolated copy; not touched) |
| ☐ D3 | Promote a model. **None qualifies**: the forecasting goal is not met. |
