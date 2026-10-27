# Using PSA food CPI and SWS hunger only as validators: result

**Branch:** `aiPHeed/system-fixes`, local. The protocol `PROTOCOL_VALIDATOR_ONLY.md` (SHA-256 `b3ec9c9c`) was frozen before scoring. The served model (P0H4) is unchanged.

## What was tested

One LightGBM model, trained on the served label T43c (SWS hunger above 11.3% AND an unusual provincial food-CPI rise), with no input computed from PSA food CPI or from SWS.

| Removed inputs | Count | Detail |
|---|---|---|
| From food CPI | 6 columns | food CPI projection, gap and momentum; regional food and rice CPI; world cereal prices (family A1) |
| From SWS | 15 columns | hunger outlook and readings; the other SWS areas; time since the newest round; the SWS-dated news window |
| Built from those sources | – | the hunger multiplier and S3's food-CPI baseline |

The kept inputs are:
- headline CPI;
- wholesale rice prices;
- poverty and density;
- El Niño status, typhoons, rice and corn harvests, fisheries production;
- unemployment and remittances;
- news (FSSI-v3 and the GDELT price-news share);
- world rice, oil and fertilizer prices.

Two arms were run:
- **V0** uses all the kept inputs;
- **V1** also drops headline CPI and world oil prices.

Both use the same issue dates, training rows, grid and reliability rule (R1–R7) as P0H4 and S3.

## Result: no reliable lead

**All leads, on the same rows** (Lead 1 = 70 province-quarters, Lead 2 = 65, Lead 3 = 60):

| Model | Lead 1 accuracy | Lead 1 HIGH recall | Lead 1 Brier | Lead 1 AUC | Lead 2 accuracy | Lead 3 accuracy | Maximum reliable lead |
|---|---|---|---|---|---|---|---|
| **V0 (validator-only)** | 0.714 | 6/17 = 0.35 | 0.197 | 0.66 | 0.662 | 0.633 | **none** |
| **V1 (also without headline CPI)** | 0.757 | 6/17 = 0.35 | 0.179 | 0.71 | 0.692 | 0.650 | **none** |
| Always predicting LOW | 0.757 | 0/17 | 0.243 | – | 0.738 | – | – |
| P0H4 (served) | 0.843 | 11/17 = 0.65 | 0.132 | 0.87 | 0.769 | 0.717 | 1 |
| S3 | 0.857 | 11/17 = 0.65 | 0.112 | 0.83 | 0.738 | 0.650 | 1 |

**Lead-1 Brier differences** (model minus comparator; negative means the validator-only model is better):

| | vs always-LOW | vs persistence | vs climatology | vs P0H4 | vs S3 |
|---|---|---|---|---|---|
| V0 | −0.046 (p .47) | −0.060 (p .30) | −0.005 (p .98) | **+0.064 (p .018)** | **+0.085 (p < .001)** |
| V1 | −0.063 (p .25) | −0.078 (p .18) | −0.022 (p .61) | +0.047 (p .08) | **+0.068 (p < .001)** |

**Failed criteria at Lead 1:**
- V0 fails R2–R7;
- V1 fails R3–R7: it is no better than always predicting LOW, and it finds only 6 of 17 HIGH cases.

## Reading

Without PSA food CPI and SWS as inputs, the remaining government and news indicators cannot forecast the Chapter I risk label:
- at Lead 1, accuracy is at or below always predicting LOW;
- at Leads 2–3, AUC is below 0.5;
- no baseline is beaten significantly.

The served model's skill comes from those two sources:
- the latest SWS reading;
- the projected food CPI.

Both are also the sources of the label. So under the strict "validators only" rule, the study has **no reliable forecast horizon on 2021–2026 data.** This answers Statement of the Problem 2 honestly, but it changes Hypothesis 2: it would not be rejected.

## Choices this leaves

1. **Adopt the strict rule.** Serve V1 (or no forecast) and report no reliable horizon. The dashboard would show forecasts that are no better than always LOW.
2. **Keep P0H4 served, and state the deviation in Chapter III.**
   - The latest published SWS reading and the food CPI projection are used as inputs. Both are known before the issue date, like the naive-persistence baseline the thesis already includes.
   - The label they help predict is a future quarter's value, not the same value.
3. **Middle option.** Keep both sources out of the government-indicator set, but use them only in the way Objective 4's naive-persistence baseline does: disclosed as a persistence component. This is option 2 with different wording, and needs the adviser's agreement.

This decision belongs to the researcher and the adviser. It is not a modelling question that more tuning can solve: the protocol allows no further tuning rounds.

## Reproduce

From `VALIDATOR_ONLY/runner`, run `python run_validator.py score` with the backend venv. It writes `out/predictions.csv` and `out/results.json`. The protocol must already be frozen (`freeze`).
