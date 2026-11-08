# E169: How to make the LightGBM model reliable (analysis, 2026-11-06)

**Scope:**
- **Diagnostic only.** No model was refitted, no gate was changed, and production is untouched (E158).
- **Inputs:** the saved E168 out-of-sample rows (Lead 1, n = 72).
- **Code:** `backend/app/e169/{rel_analysis,shift_signal}.py`
- **Outputs:** `backend/data/e169/out/`
- **Labelled diagnostics:** "ORACLE" rows use test outcomes. They are ceilings, never a model.

## 1. Where E168 stands
| | Result | Gate |
|---|---|---|
| Accuracy | 75.0 % (54/72) | **C1 needs 56/72** |
| Calibration slope | 0.76 [0.54, 0.89] | **C4 needs the CI to include 1** |
| Mean error | 7.6 points | n/a |

## 2. What the error is made of
| Source | Size (logit SD) | Fixable with available data? |
|---|---|---|
| **Round-wide shift** (the whole survey round higher or lower than expected) | 0.19 (21 % of squared error) | Not with any signal we hold; see section 3 |
| **Region-wide shift within a round** | **0.30, the largest** | Only with provincial or regional data that has real variation |
| Province-specific | 0.21 | Partly |
| Survey sampling noise | 9 % of squared error | Not needed |

**Survey noise is not the limit.**
- A forecaster that knew each province's true prevalence would score about **95 %**, and would pass C1 every time.
- So the target is predictable in principle. **The model is missing information, not hitting a noise floor.**

**Mean error by round:**

| Round | Mean error | Slope |
|---|---|---|
| ENNS 2018 | +6.8 points | 0.99 |
| ENNS 2019 | +3.9 points | 0.86 |
| ENNS 2021 | −1.3 points | 0.70 |

## 3. What would fix C1 and C4 (oracle ceilings)
| If the model had known… | Accuracy | C1 | Slope [95 %] | C4 |
|---|---|---|---|---|
| Nothing extra (E168) | 75.0 % | ❌ | 0.76 [0.54, 0.89] | ❌ |
| **Each round's national shift** | **80.6 % (58/72)** | ✅ | 0.87 [0.70, 0.99] | ❌ |
| The national shift and the within-round spread | 83.3 % (60/72) | ✅ | 1.00 [0.78, 1.14] | ✅ |

**The single piece of information that would make C1 pass is the national food-insecurity level at the time of the survey.**

**Is that shift visible in data we already have?** It was tested with SWS area hunger, using values published as of each forecast date (`sws_shift_signal.json`). It is not:
- **SWS moved in the opposite direction to HFIAS.** In 2021 SWS hunger rose (COVID), while provincial HFIAS fell.
- The correlation of the SWS change with the HFIAS change is −0.33 (rows) and −0.42 (region-rounds).
- **Adding the SWS change lowers accuracy from 75.0 % to 68.1 %.**
- SWS measures a different construct (involuntary hunger) and must not be used to anchor HFIAS levels.

## 4. How much the gate itself can tell us with 72 rows
**Simulation:** a model that **is** calibrated (slope 1, no bias), with E168's error structure (round, region and province), scored 600 times on the same 72 rows.

| Model error | C1 passes | C4 passes | Both pass |
|---|---|---|---|
| Same as E168 | 79 % | 79 % | **62 %** |
| 25 % smaller | 90 % | 79 % | 72 % |
| 50 % smaller | 99 % | 78 % | 78 % |

**Two facts follow:**
1. **E168's failure is not proof that it is unreliable, and a pass would not be proof that it is.** With 72 rows from 3 rounds, the test is too small to separate the two.
2. **C4 rejects a truly calibrated model about 21 % of the time, whatever its accuracy.** The cause is the region-cluster bootstrap over about 17 regions and 3 rounds.
   - The gate stays as fixed. It is not changed after results.
   - Whether a corrected C4 should be **pre-registered for future, untouched rounds only** is an owner and adviser decision.

**How many test rows C1 needs, at the same effective-n rule:**

| Accuracy | Test rows needed |
|---|---|
| 75.0 % (E168) | **122** |
| 76.4 % | 89 |
| 78 % or more | 72 |

## 5. Why tuning on the 72 rows is not the answer
- E168 is **2 rows** short of C1. A small tweak chosen by looking at these rows would make it pass.
- That is exactly the overfitting the owner ruled out. Every one of the 72 rows has been read by more than 10 experiments (E151–E168).
- **A reliable claim requires one of two things:**
  - outcomes the model has never seen; or
  - inputs that carry information the model lacks today (sections 2 and 3).

## 6. The plan to make it reliable (in order of impact)
| # | Action | Fixes | What it needs |
|---|---|---|---|
| 1 | **More test rows:** the missing ENNS 2018/2019/2021 provinces and ENNS 2022 provincial HFIAS (E166/E158 already sealed) | C1 directly (122 rows makes 75 % pass); a 4th round for C4 | FNRI provincial HFIAS tables |
| 2 | **Provincial food prices** (PSA retail prices by province, monthly, 2012–2021). Market is the only group that helps today, and only at time level, because its inputs are national/regional | The region-wide shift (the largest error) | PSA OpenSTAT, "Retail prices of selected agricultural commodities by province" |
| 3 | **A national HFIAS-type anchor between survey rounds.** SWS is the wrong construct. Test the FAO/PSA FIES national series (SDG 2.1.2) **as-of only**, the same way as SWS above | The round-wide shift (C1 per the oracle) | `fi_labels/clean/published_fies_psa_sdg212.csv` plus the FAO annual series |
| 4 | **Provincial palay/rice and corn production** (PSA, quarterly). E117: palay was the one input that improved Lead 1 | Province-specific error | PSA OpenSTAT, crops by province |
| 5 | **Pre-register E169-LGBM before any new outcome:** the same constrained LightGBM plus items 2–4, a frozen protocol, then a seal. **Accept only on new or untouched rows** | Credibility of the claim | Items 1–4 |

**Ruled out:** news (no out-of-sample value), SWS level transfer (wrong sign), more LightGBM tuning on the 72 rows (selection optimism, E161), and copying national employment or remittances into provinces.

> **Update (E169 tests, `E169_NEW_SIGNAL_TESTS.md`):**
> - **#2 is already in the model.** E168 uses PSA provincial food and rice CPI, farmgate palay and wholesale rice. The market inputs are provincial, not national/regional as stated above.
> - **#3 is not usable.** No FIES value for the Philippines existed before the 2018-Q1 or 2019-Q1 origins. For 2021 it moved the wrong way.
> - **#4 (palay) is already in.**
> - **Only #1, new HFIAS outcomes, remains.**

## 7. Decision
- **E168 stays "improved but not accepted"**, and E158 stays in production.
- **The route to a reliable LightGBM is information plus untouched test rows, not tuning.**
- **First step:** provincial retail prices (#2) and the FIES as-of test (#3). Both can be done with public data, and #3 needs no new download.
