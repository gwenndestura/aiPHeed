# E131 selected solution

## The design: two layers, each scored against independent measurements

| Layer | Target (independent measurement) | Model | Forecast | Validation |
|---|---|---|---|---|
| **1. Quarterly food-insecurity forecasting** | SWS involuntary hunger, % of families; 4 areas, including Balance Luzon (which contains CALABARZON) | **LLM**: a measurement-aware local-level model whose observation noise is fixed to each round's published sampling error | Leads 1–4 on the dashboard clock (`target.py`), with 80 % intervals | Walk-forward (development) plus the **prospective seal** (`sealed/E131_PROSPECTIVE_SEAL.csv`, sha256 `92b5535f…`), scored as SWS publishes |
| **2. Provincial food deprivation** | PSA subsistence incidence (PFDR), 5 provinces, at survey years | Survey-year forecasters (E130 seal) plus the price-versus-income decomposition | The next PSA provincial round | When PSA publishes it |
| Provincial quarterly display | None (no measurement exists) | Balance Luzon LLM forecast × provincial relative food deprivation | Labelled **model-based** estimates (`sealed/E131_PROVINCIAL_MODEL_BASED_SEAL.csv`, sha256 `ed8393e9…`) | Only at PSA survey rounds |

## Why LLM

LLM is chosen by the frozen selection rule: the highest Lead-2 share within tolerance under the dashboard issue rule.

| Model | Lead-2 within tolerance | Lead-2 MAE (points) |
|---|---|---|
| **LLM** | **0.50** | **4.70** |
| LGBM-H | 0.46 | 5.93 |
| LGBM-ALL | 0.39 | 6.13 |
| NLP-ONLY | 0.39 | 5.46 |
| PSA-ONLY | 0.36 | 7.26 |
| RIDGE-ALL | 0.32 | 6.51 |
| PERSIST (baseline) | 0.46 | 5.28 |

On these shared rows LLM passes 4 of the 7 reliability rules at Lead 2:
- **Passes:** it beats every baseline on MAE and RMSE; beats persistence and climatology on squared error (p = 0.096); no area falls below persistence; 80 % coverage is 0.86.
- **Fails:** data sufficiency (7 shared quarters), agreement (0.50 < 0.75) and stability.

It also has only two parameters, both estimated from the data available at each issue date. That suits a series this short.

## What it is not

- **Not validated:** it fails N2 (agreement) at every lead and N1 on the shared rows.
- **Not provincial.** Provincial outputs are model-based and say so.
- **Not a five-trigger model.** The trigger groups did not improve it (`E131_TRIGGER_CONTRIBUTION_REPORT.md`). That is reported honestly, not forced.

## Assumptions and limitations

| Item | Detail |
|---|---|
| Sampling error | From the published margins at the observed proportion, without design-effect inflation |
| Area covariates | Unweighted means of the area's regions |
| Covariates in the release-anchored policy | Use quarter-start values |
| Respondent base | Changed in 2025 (household heads → adults). The model absorbs it as level noise, without special handling. |
| Provincial scaling | Assumes hunger is proportional to subsistence incidence within Balance Luzon. That assumption is untested and sensitive to the deprivation measure. |
