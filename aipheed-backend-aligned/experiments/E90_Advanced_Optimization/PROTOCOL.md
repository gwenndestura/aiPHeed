# E90 protocol: rice-led hunger-change component and warning tier (frozen before scoring)

**Branch.** `e90-advanced-optimization` (from e89-model-optimization at b9222ac).

**Freezing.** This file is hashed into `PROTOCOL.sha256` and committed before any E90 arm is scored.

## 1. Diagnostic that motivates E90 (`onset_diagnostic.csv`/`.json`; computed before this protocol)

**Measure.** Hunger change dH = SWS hunger in the target quarter − the latest SWS reading posted before the forecast
origin. It is compared with the five-province means of each driver's origin-time features.

| Driver feature | Lead 1 (n) | Lead 2 (n) |
|---|---|---|
| Rice CPI YoY at the origin | ρ = +0.79 (16), p < 0.001 | ρ = +0.71 (15), p = 0.003 |
| Rice 3-month momentum | — | ρ = +0.69 (16), p = 0.003 |
| Unemployment change, typhoons, remittances, fisheries, palay, ENSO | none significant | none significant |

**Mechanism.** Rice is the main staple: 23–26% of food CPI in these provinces. Its price rise erodes households'
purchasing power, and hunger rises with a delay. This is consistent with the 2023–24 surge, which came after the
2023 rice price spike.

**Disclosure (selection).** The predictor (rice CPI YoY) was chosen after seeing this full-period correlation, which
covers the evaluation quarters. Walk-forward fitting prevents leakage in the coefficients, but not in the choice of
predictor. **E90 results are therefore selection-informed development evidence.** Only the sealed prospective quarters
can validate them.

## 2. Arms (Leads 1 and 2; same 65 rows; all walk-forward)

### HUN-RICE

1. **Hunger change.** dH(t'→t'+k) = a + β · rice_yoy(t') is fitted by OLS on the pairs available at O(t): origins t'
   whose target SWS round was posted before O(t) and whose rice YoY is known.
   - β is constrained to ≥ 0 and shrunk toward 0 by n/(n + 4).
   - The fit requires at least 6 pairs; otherwise the random walk is used (a = 0, β = 0).
2. **Forecast hunger.** Ĥ = H_last + a + β · rice_yoy(t).
3. **Probability.** P(H > 11.3) = Φ((Ĥ − 11.3) / s), where s = max(the random-walk sd for the gap, the training
   residual RMSE).
4. **T43 probability.** P(T43 HIGH) = P(H > 11.3) × the S-COV price probability (E89, unchanged).

### WARN (secondary; does not change classification accuracy)

A three-level warning on the HUN-RICE probability:

| Level | Rule |
|---|---|
| HIGH | p ≥ 0.5 |
| WATCH | τ ≤ p < 0.5 |
| LOW | p < τ |

τ is chosen at each origin from {0.15, 0.20, …, 0.45}. It maximises F2 (recall-weighted) of "HIGH or WATCH" on earlier
rows whose labels were published before O(t). The default is 0.3 when there are fewer than 3 such quarters.

**Reported:** recall and precision of HIGH-or-WATCH, false alarms, and missed HIGH.

## 3. Evaluation (unchanged rules)

**Rules.** The E83 PASS rule and the pre-set generalization criteria.

**Comparisons.**
- current models: Lead 1 S-SIM 0.846 (and the hybrid 0.877, post-hoc); Lead 2 S-COV 0.800;
- persistence and always-LOW.

**Breakdowns.**
- by province;
- ordinary versus worsening quarters ("worsening" = SWS hunger rose by 3 points or more from the last posted
  reading);
- coverage.

**Promotion.**
- No quarter-level losses outweighing gains against the current model.
- Better pooled Brier.
- Better HIGH recall.

All three are required.
