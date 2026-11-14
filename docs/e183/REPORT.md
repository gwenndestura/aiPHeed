# E183: missing-input robustness of the E168 forecast. Report

## Result in one paragraph
- **The validated model is untouched.** E168's accuracy and selected outputs are identical after the change: all 432
  rows, max difference 0.0.
- **The warning works.** Every forecast whose used inputs had to be filled is now flagged and carries a "Data
  incomplete" sentence on the dashboard. Before, this happened silently.
- **The drop is not fixed.** The fill does **not** stop the forecast from falling when trigger inputs are missing. With
  missing inputs filled by their typical training value, the forecast falls about as much as before.
- **Why.** Without its trigger inputs, the model reverts to its historical average change. That change is a decline,
  because food insecurity fell between the 2015 and 2018–2021 surveys. The current inputs (high food prices and
  unemployment) are what keep today's forecast up.
- **What would be needed.** No neutral fill can replace that information. Carrying the last published value forward is
  the natural next design, and it would need its own test.

## Checks
| Check | Result |
|---|---|
| 1. E168's 18 validation jobs through the changed code (`data/e183/out/equivalence.json`) | ✅ 432 / 432 rows, same configuration, max \|Δ\| 0.0 for `mu`, `p` and `half` |
| 2. Today's production forecast unchanged (`production_check.json`) | ✅ all 15 province × lead rows equal the production artifact; every row `data_complete` (the two missing consumption inputs are not used by the served configuration) |
| 3. Scenario S2 before vs after (`s2_before_after.csv`, `s2_summary.json`) | Real-input forecast identical before and after. Flags: 0 % → 100 % of rows with missing used inputs. Forecast level: about the same drop. |

**Check 3, Quezon at Lead 1** (real inputs: 35.5 %, P(HIGH) 0.064):

| Inputs missing | Before (read as missing) | After (filled with training median) | Flagged after |
|---|---|---|---|
| 25 % | 33.1 %, P 0.040 | 33.0 %, P 0.040 | yes |
| 50 % | 28.5 %, P 0.013 | 28.0 %, P 0.012 | yes |
| 75 % | 26.2 %, P 0.006 | 25.3 %, P 0.004 | yes |
| all triggers | 22.7 %, P 0.001 | 21.5 %, P 0.000 | yes |

The other four provinces behave the same way (`s2_summary.json`).

## What changed in the code (owner-approved)
- **New helper** `app/e168/robust.py`. Applied in `lgbm_only.task` and `serve._forecast` before `run_proc`.
- **Flag fields** (`inputs_filled`, `inputs_filled_names`, `data_complete`) are carried into the dashboard rows and the
  quarterly `live.json`.
- **Warning sentence** in `e168_system.province_row`.
- **Not changed:** the served artifact, the registry, or any validated number.

## Recommendation
- **Keep:** the warning.
- **Do not describe** the median fill as a fix for the drop.
- **Next test:** carry the last published value forward for late series, then re-run S2.
