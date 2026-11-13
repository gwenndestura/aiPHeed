# Dashboard trigger groups for FINAL: evidence-based recommendation (analysis only; nothing implemented)

**Scope.** This analyses **FINAL** (research model). The served dashboard runs **E196**, whose inputs differ (E168 feature set plus regional consumption; it has a national remittance input). A dashboard serving E196 needs its own audit. No dashboard change was made.

## Evidence (all on the unchanged FINAL model)

| Measure | What it shows | File |
|---|---|---|
| Selection and gain | Which inputs the 110 fits actually used (training-only) | `evidence/G3_input_inventory.csv`, `G_group_evidence.json` |
| **Withholding ablation** | The fitted model predicts every fold-lead (3 rounds × Leads 1–8, 576 forecasts) with one group missing. **Outcome-free:** probability change, class flips | `evidence/G1_withhold_ablation.csv` |
| **Retraining ablation** | FINAL refitted without one group, Lead 1, each round: performance change on the reused rows | `evidence/G2_retrain_ablation_L1.csv` |
| Round and lead consistency | Gain by round and by lead; flips by round | `G_group_evidence.json` |

## Results

| Group | Gain share Lead 1 (2018 / 2019 / 2021 fold) | Gain share Leads 3–8 | Withheld: mean probability change / flips (of 576) / rounds with flips | Retrained without, Lead 1: Δ balanced accuracy / Δ AUROC / flips | Geography |
|---|---|---|---|---|---|
| **Regional accounts (GRDP, consumption)** | 0.52 / 0.52 / **0.00** | 0.49–0.52 | **0.094 / 92 / 3** | **−0.106** / −0.019 / 14 | Regional |
| **Market and prices** | 0.15 / 0.15 / 0.42 | 0.15–0.17 | 0.041 / 15 / 3 | −0.053 / −0.020 / 7 | Provincial |
| **Poverty and social vulnerability** | 0.26 / 0.26 / **0.00** | 0.25–0.26 | 0.040 / 26 / 3 | −0.011 / +0.007 / 1 | Provincial |
| **Agriculture and fish production** | 0.07 / 0.07 / 0.07 | 0.06–0.07 | 0.031 / 18 / 3 | −0.033 / −0.006 / 6 | Provincial |
| Climate | 0.00 / 0.00 / 0.00 | 0.00–0.02 | 0.003 / **0** / 0 | −0.060 / +0.006 / 3 (see note) | Provincial (ONI national) |
| News / NLP | 0.00 / 0.00 / **0.51** | ≈ 0 | 0.001 / **0** / 0 | 0.000 / 0.000 / 0 | National / area / provincial |
| Employment | 0 | 0 | 0 / **0** / 0 | 0 / 0 / 0 | National |
| OFW remittances | not an input | not an input | n/a | n/a | n/a |

**Climate note.** Withholding the climate inputs never changes a forecast. Retraining without them shifts *which* other inputs are selected, and in this one Lead 1 run that lowered recall. That is a model-selection side effect, not evidence that climate information drives forecasts. The two ablations disagree, so climate's contribution is **unstable and unsupported**.

**News note.** In the 2021 fold, news indices carry training gain (0.51 at Leads 1–2). But withholding or removing them changes no forecast in any round. Gain without forecast effect means the inputs fit training noise or are fully substituted.

## Decision

| Group | Decision | Reason |
|---|---|---|
| **1 Regional economy (PSA regional accounts: GRDP per capita, household consumption)** | **Include. Label it regional**, never provincial | Largest effect on every measure; consistent in the 2018 and 2019 folds and at all leads. **Limitation:** unused in the 2021 fold at Leads 1–2, and it varies only between regions |
| **2 Market and prices** | **Include** | Effect in all three rounds and all leads; provincial data |
| **3 Poverty and social vulnerability (poverty and subsistence incidence, density)** | **Include, with a limitation** | 26 flips across all rounds when withheld. Partly redundant with regional economy when retrained. Unused in the 2021 fold at Leads 1–2 |
| **4 Agriculture and fish production** | **Include** | Moderate but consistent effect in all rounds; provincial. Replaces the current "Fish Production" bar, which shows only part of this group |
| Climate stress | **Exclude as a forecast trigger.** It may be shown as context, clearly marked "not a factor in this forecast" | Zero forecast effect under withholding; contradictory retraining evidence; selected inputs carry about 0.1–2 % gain |
| Employment | **Exclude** | Never selected; zero effect; national-only data. **Data gap:** PSA provincial labour statistics start with a January 2022 release (usable prospectively) |
| OFW remittances | **Exclude** | Not a FINAL input (excluded by design); no provincial series exists |
| News / NLP | **Exclude as a forecast trigger** | No forecast effect. It stays a research output (FSSI, topics), not a displayed driver |

**Result: four evidence-supported groups for FINAL.** Neither the original five nor the brief's five is supported as stated. Three of those five (climate, employment, remittances) do not influence FINAL's forecasts.

## How each displayed group moves a forecast
FINAL forecasts the **change** in risk since the anchor survey. The monotone constraints enforced in training (`Pv.SIGN`, `H.NEW_SIGN`) fix the direction of each effect:

| Group | Effect on risk |
|---|---|
| **Regional economy** | Higher regional GRDP per capita relative to other regions → lower risk change (sign −1). Consumption level enters unconstrained |
| **Market and prices** | Faster food or rice CPI inflation (`cpi_food_3m`, `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_since`) and higher local rice prices relative to the region (`l_rice_rel`) → higher risk change (+1). Food CPI relative to national is unconstrained |
| **Poverty and social vulnerability** | Higher poverty and subsistence incidence → higher risk change (+1). Density is unconstrained |
| **Agriculture and fish production** | Higher palay, corn and agricultural production growth → lower risk change (−1). Fisheries production growth enters with +1, as constrained in the pipeline (as built; it should be reviewed) |

A bar's share on the dashboard should be computed from FINAL's own per-forecast contributions (TreeSHAP) summed over each group's **selected** inputs. A group with no selected input must never be shown as a contributor.

## Not implemented
- The dashboard is unchanged and still serves E196.
- **Implementing these groups requires:**
  - your approval;
  - a decision on which model the dashboard serves;
  - the thesis text changing from "five triggers" to the evidence-supported groups (Chapter III currently names five).
