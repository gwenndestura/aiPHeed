# Objective 2: classification metrics (I–IV) and the reliable horizon (V)

**Model:** the proposed food-insecurity LightGBM as final in IMPROVE_V2: the reference arm, HISTORY_RETRAIN LightGBM (b)
for T2, carried forward and sealed (SHA-256 `94c62596…`). **Target:** SWS Balance Luzon involuntary hunger > 11.3%
(HIGH) vs ≤ 11.3% (LOW). Food prices are inputs only. Source: `IMPROVE_V2/out/results.json`. Nothing was refitted.

**Evidence status:** development evidence. Every quarter 2010–2026 was examined before.

**Scope, stated plainly.** Objective 2 I–IV speaks of "high- and low-risk **province-level** classifications". The
food-insecurity outcome that exists is **regional** (one Balance Luzon value per quarter, the same for all five
provinces). The metrics below are therefore of **one regional classification per quarter**. A province-level
food-insecurity classification cannot be scored until a provincial outcome exists: provincial FIES, or CBMS 2024 LGU
results (category (b)).

## Objective 2 I–IV: metrics (HIGH when P ≥ 0.50)

### Verdict window, targets 2010-Q1..2026-Q3, 62 quarters (43 HIGH, 19 LOW)

| Metric | Lead 1 | Lead 2 |
|---|---|---|
| **Accuracy** (I) | **0.790** | **0.790** |
| Balanced accuracy | 0.717 | 0.717 |
| **Precision** (II) | **0.812** | **0.812** |
| **Recall** (II) | **0.907** | **0.907** |
| Specificity | 0.526 | 0.526 |
| **F1** (III) | **0.857** | **0.857** |
| **AUC-ROC** (IV) | **0.702** | **0.704** |
| PR-AUC | 0.797 | 0.793 |
| **Brier** | **0.188** | **0.184** |
| Mean P / base rate | 0.696 / 0.694 | 0.692 / 0.694 |

**Confusion matrices** (rows = observed, columns = forecast):

| Lead 1 | Forecast HIGH | Forecast LOW |
|---|---|---|
| Observed HIGH (43) | 39 (TP) | 4 (FN) |
| Observed LOW (19) | 9 (FP) | 10 (TN) |

| Lead 2 | Forecast HIGH | Forecast LOW |
|---|---|---|
| Observed HIGH (43) | 39 (TP) | 4 (FN) |
| Observed LOW (19) | 9 (FP) | 10 (TN) |

The two leads have identical counts, but not identical quarters or probabilities (AUC and Brier differ).

**Reading:**
- The model finds most HIGH quarters: recall 0.91, so 4 missed in 62.
- It gives about one false alarm for every four true alarms: precision 0.81, 9 false alarms.
- It is weak at recognising LOW quarters: specificity 0.53, so only 10 of 19 LOW quarters were called LOW.
- AUC 0.70 means moderate ranking ability.

### Sub-periods (reported, no verdict)

| Window | Lead | Acc | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| 2010–2022 (48 q) | 1 | 0.729 | 0.757 | 0.875 | 0.812 | 0.700 | 0.205 | 28/9/4/7 |
| 2010–2022 (48 q) | 2 | 0.750 | 0.763 | 0.906 | 0.829 | 0.697 | 0.193 | 29/9/3/7 |
| 2023–2026 (14 q) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.126 | 11/0/0/3 |
| 2023–2026 (14 q) | 2 | 0.929 | 1.000 | 0.909 | 0.952 | 0.939 | 0.151 | 10/0/1/3 |

The 2023–2026 block is near perfect, but it has only 3 LOW quarters and 14 quarters in all.

## Objective 2 V: the furthest reliable horizon

> "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically
> determine the furthest horizon at which reliable forecasting is achievable"

### Method (as run)

1. **Walk-forward with an expanding window.** At each issue date O(t), the first day of quarter t+1, the LightGBM is refitted on every row whose target quarter was published before O(t) (origins from 1998-Q3), then forecasts Leads 1 and 2. Only data published before O(t) is used. This was tested by randomizing all later data at six origins (unchanged forecasts).
2. **Reliability rule (frozen beforehand, unchanged).** All of R1–R7 must pass:
   - R1: ≥ 10 quarters and ≥ 40 rows (one row per quarter here);
   - R2: accuracy ≥ 0.75;
   - R3: balanced accuracy ≥ 0.70;
   - R4: beats always-LOW and persistence;
   - R5: Brier below persistence and climatology (p < 0.10);
   - R6: precision and recall ≥ 0.60;
   - R7: each third ≥ 0.60 and leave-one-quarter-out ≥ 0.70.
3. **Maximum reliable lead** = the run of consecutive passes from Lead 1.

### Result: **maximum reliable lead = 0 (no reliable lead)**

| Rule | Lead 1 | Lead 2 |
|---|---|---|
| R1–R6 | all pass | all pass |
| **R7 stability** | **fails**: thirds 0.952 / **0.571** / 0.850 | **fails**: 0.952 / **0.571** / 0.850 |

- The model is right 95% of the time in the first third of the period (2010 to about 2015).
- It is right only 57% in the middle third (about 2015–2020).
- Without the 2020 phone-survey quarters it would pass at both leads. This is a sensitivity only; the rule was not changed.
- None of the three IMPROVE_V2 improvements, nor the longer-history alternatives in HISTORY_RETRAIN, passed.

**"Multiple lead times."** The food-insecurity model was tested at Leads 1 and 2. Earlier food-insecurity forecasts (E109–E112, SWS hunger) were tested at Leads 0–4, and no lead passed there either. Lead 1 already fails, so no longer lead can be reliable under the run-of-passes rule.

### Prospective confirmation: what happens next, with dates

The forecasts are sealed before their outcome exists.
- SWS publishes each round a median of **42 days** after fieldwork (2023–2026).
- 5 of 67 quarters in 2010–2026 had no round.

| When | Action | Tool |
|---|---|---|
| Done, 2026-11-03 | Lead 2 for 2027-Q1 sealed: P(HIGH) 0.860, HIGH | `IMPROVE_V2/sealed_prospective_IMPROVE_V2.csv` |
| On or after 2027-01-01 | Seal Lead 1 for 2027-Q1 and Lead 2 for 2027-Q2 | `python IMPROVE_V2/runner/seal_next.py 2027-01-01` (refreshed data in `--data`) |
| On or after 2027-04-01, 07-01, 10-01, then each quarter | Seal the next Lead 1 and Lead 2 | `seal_next.py <date>` |
| About May 2027 (2027-Q1 round published) | First score | `python IMPROVE_V2/runner/score_seal.py --sws <updated SWS file>` |
| About late 2029 | **About 10 scored quarters per lead**: first meaningful prospective comparison with persistence (accuracy, Brier) | `score_seal.py` |
| About 2037 | **40 scored quarters**: R1 can first be met on sealed quarters alone | `score_seal.py` + R1–R7 |

**Correction to IMPROVE_V2 RESULTS.md §14.**
- That file says the sealed forecast counts "after at least 10 sealed quarters are scored (R1)".
- For this one-row-per-quarter target, R1 as frozen also needs **≥ 40 rows, that is 40 quarters**. Ten quarters gives a first prospective check, not R1.
- The committed IMPROVE_V2 file is not edited (instruction); the correction is recorded here.
