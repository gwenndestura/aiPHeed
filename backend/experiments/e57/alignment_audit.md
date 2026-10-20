# Alignment audit: E53 record (Phase A, read-only)

Served with `AIPHEED_RECORD=e53 AIPHEED_MAX_LEAD=2`: 2026-Q1..Q3 are lead-1 backtests, 2026-Q4 the lead-1 forecast (E53-A1), 2027-Q1 the lead-2 forecast (E55). Values from the live API, the record (`data/e53/e53_record.json`), the frozen models and the C2 calibration parameters. Nothing was changed.

## 1. Index = mean of the five probabilities; ranking = probabilities sorted

| Quarter | Region index (API) | Mean of 5 (API) | Match | Ranking (API) | Sorted probabilities | Match |
|---|---|---|---|---|---|---|
| 2026-Q1 | 0.8913 | 0.8913 | yes | laguna 0.8926, cavite 0.8925, rizal 0.8922, quezon 0.8902, batangas 0.8891 | laguna, cavite, rizal, quezon, batangas | yes |
| 2026-Q2 | 0.7539 | 0.7539 | yes | laguna 0.8775, cavite 0.8743, quezon 0.8672, rizal 0.8427, batangas 0.3076 | laguna, cavite, quezon, rizal, batangas | yes |
| 2026-Q3 | 0.8960 | 0.8960 | yes | rizal 0.9010, cavite 0.9001, laguna 0.8997, quezon 0.8937, batangas 0.8854 | rizal, cavite, laguna, quezon, batangas | yes |
| 2026-Q4 | 0.7894 | 0.7894 | yes | rizal 0.9173, quezon 0.9169, cavite 0.9165, laguna 0.9122, batangas 0.2839 | rizal, quezon, cavite, laguna, batangas | yes |
| 2027-Q1 | 0.7978 | 0.7978 | yes | cavite 0.8200, laguna 0.8200, rizal 0.8200, quezon 0.8200, batangas 0.7091 | cavite, laguna, quezon, rizal, batangas | yes |

Province probabilities from `/provinces` equal the record's `p_high` exactly in every row. Ties: in 2027-Q1 four provinces are exactly 0.8200 (identical raw model output, see item 5); their order is by position, not by value.

## 2. Where the forecast comes from: hunger-survey inputs vs the five drivers

Exact TreeSHAP, raw model (before calibration), log-odds. `base + sum(SHAP)` is the raw log-odds; for 2026-Q4 and 2027-Q1 it is checked against the frozen model's own raw output (`model z`), for every row the C2 calibration `a * sigmoid(z) + (1 - a) * base rate` is checked against the served probability.

Shares are of the total |SHAP| on the bars' basis (the news inputs split by the topic of the titles, as the driver panel does). Groups: **SWS hunger** = H_last, H_gap, H_trend, H_margin; **last label** = y_last (the latest published HIGH/LOW, itself built from SWS + CPI); **news tone** = fssi_v2, fssi_missing; **news, no driver** = news-volume SHAP whose titles match no driver; **five drivers** = everything mapped to Market, Climate, Fish Kill, Employment, OFW (including cond_* and trig_*).

### 2026-Q1 (lead 1, backtest)

| Province | base | sum SHAP | z = base + sum | model z | raw p | calibrated p | cal. reproduced | SWS hunger | last label | news tone | news, no driver | five drivers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cavite | 2.978 | 4.907 | 7.884 | – | 0.9996 | 0.8925 | 0.8925 | 40% (+1.90) | 10% (+0.52) | 0% (+0.00) | 0% (+0.00) | 50% |
| laguna | 2.978 | 5.415 | 8.393 | – | 0.9998 | 0.8926 | 0.8926 | 36% (+1.87) | 9% (+0.52) | 0% (+0.00) | 0% (+0.00) | 55% |
| batangas | 2.978 | 2.198 | 5.175 | – | 0.9944 | 0.8891 | 0.8891 | 41% (+2.93) | 12% (+0.95) | 0% (+0.00) | 0% (+0.00) | 47% |
| rizal | 2.978 | 4.126 | 7.104 | – | 0.9992 | 0.8922 | 0.8922 | 50% (+2.08) | 13% (+0.58) | 0% (+0.00) | 0% (+0.00) | 37% |
| quezon | 2.978 | 2.570 | 5.547 | – | 0.9961 | 0.8902 | 0.8902 | 42% (+2.47) | 14% (+0.90) | 0% (+0.00) | 0% (+0.00) | 44% |

Mean of the five provinces: SWS hunger + last label 53%, news tone + news without a driver 0%, five drivers 47%. Signed values (log-odds) in brackets.

### 2026-Q2 (lead 1, backtest)

| Province | base | sum SHAP | z = base + sum | model z | raw p | calibrated p | cal. reproduced | SWS hunger | last label | news tone | news, no driver | five drivers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cavite | 2.465 | 2.078 | 4.543 | – | 0.9895 | 0.8743 | 0.8743 | 31% (-0.32) | 14% (+0.68) | 6% (+0.05) | 1% (+0.03) | 50% |
| laguna | 2.465 | 2.786 | 5.251 | – | 0.9948 | 0.8775 | 0.8775 | 27% (-0.24) | 16% (+0.82) | 4% (+0.23) | 2% (+0.11) | 50% |
| batangas | 2.465 | -5.519 | -3.054 | – | 0.0450 | 0.3076 | 0.3076 | 16% (+0.04) | 18% (-1.61) | 1% (+0.12) | 2% (+0.17) | 63% |
| rizal | 2.465 | 0.231 | 2.696 | – | 0.9368 | 0.8427 | 0.8427 | 24% (-0.11) | 13% (+0.78) | 4% (+0.24) | 1% (+0.05) | 58% |
| quezon | 2.465 | 1.311 | 3.776 | – | 0.9776 | 0.8672 | 0.8672 | 23% (+0.19) | 18% (+1.14) | 4% (+0.24) | 1% (+0.05) | 53% |

Mean of the five provinces: SWS hunger + last label 40%, news tone + news without a driver 5%, five drivers 55%. Signed values (log-odds) in brackets.

### 2026-Q3 (lead 1, backtest)

| Province | base | sum SHAP | z = base + sum | model z | raw p | calibrated p | cal. reproduced | SWS hunger | last label | news tone | news, no driver | five drivers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cavite | 2.794 | 2.676 | 5.470 | – | 0.9958 | 0.9001 | 0.9001 | 16% (+0.99) | 5% (+0.29) | 20% (-1.26) | 2% (-0.14) | 57% |
| laguna | 2.794 | 2.549 | 5.343 | – | 0.9952 | 0.8997 | 0.8997 | 27% (+1.41) | 15% (+0.80) | 3% (+0.15) | 1% (+0.03) | 54% |
| batangas | 2.794 | 0.800 | 3.593 | – | 0.9732 | 0.8854 | 0.8854 | 23% (+1.79) | 11% (+0.84) | 2% (+0.15) | 1% (-0.10) | 64% |
| rizal | 2.794 | 3.131 | 5.925 | – | 0.9973 | 0.9010 | 0.9010 | 24% (+1.14) | 8% (+0.39) | 9% (-0.43) | 5% (-0.25) | 54% |
| quezon | 2.794 | 1.462 | 4.256 | – | 0.9860 | 0.8937 | 0.8937 | 16% (+0.72) | 10% (+0.46) | 25% (-1.12) | 0% (+0.01) | 48% |

Mean of the five provinces: SWS hunger + last label 31%, news tone + news without a driver 14%, five drivers 56%. Signed values (log-odds) in brackets.

### 2026-Q4 (lead 1, forecast)

| Province | base | sum SHAP | z = base + sum | model z | raw p | calibrated p | cal. reproduced | SWS hunger | last label | news tone | news, no driver | five drivers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cavite | 2.795 | 3.212 | 6.007 | 6.007 | 0.9975 | 0.9165 | 0.9165 | 9% (-0.13) | 17% (+0.87) | 6% (+0.30) | 1% (-0.02) | 66% |
| laguna | 2.795 | 1.952 | 4.747 | 4.747 | 0.9914 | 0.9122 | 0.9122 | 11% (-0.27) | 17% (+0.88) | 7% (+0.11) | 1% (-0.05) | 63% |
| batangas | 2.795 | -5.062 | -2.267 | -2.267 | 0.0939 | 0.2839 | 0.2839 | 10% (-0.26) | 30% (-2.18) | 2% (+0.14) | 1% (-0.01) | 58% |
| rizal | 2.795 | 3.921 | 6.716 | 6.715 | 0.9988 | 0.9173 | 0.9173 | 10% (-0.18) | 16% (+0.85) | 6% (+0.30) | 0% (-0.01) | 69% |
| quezon | 2.795 | 3.474 | 6.269 | 6.269 | 0.9981 | 0.9169 | 0.9169 | 9% (-0.19) | 16% (+0.87) | 6% (+0.30) | 1% (-0.03) | 68% |

Mean of the five provinces: SWS hunger + last label 29%, news tone + news without a driver 6%, five drivers 65%. Signed values (log-odds) in brackets.

### 2027-Q1 (lead 2, forecast)

| Province | base | sum SHAP | z = base + sum | model z | raw p | calibrated p | cal. reproduced | SWS hunger | last label | news tone | news, no driver | five drivers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cavite | 1.673 | 2.396 | 4.069 | 4.069 | 0.9832 | 0.8200 | 0.8200 | 14% (+0.34) | 0% (+0.00) | 0% (+0.00) | 2% (+0.06) | 84% |
| laguna | 1.673 | 2.396 | 4.069 | 4.069 | 0.9832 | 0.8200 | 0.8200 | 14% (+0.34) | 0% (+0.00) | 0% (+0.00) | 2% (+0.06) | 84% |
| batangas | 1.673 | -1.210 | 0.463 | 0.463 | 0.6137 | 0.7091 | 0.7091 | 11% (+0.34) | 0% (+0.00) | 0% (+0.00) | 2% (+0.06) | 87% |
| rizal | 1.673 | 2.396 | 4.069 | 4.069 | 0.9832 | 0.8200 | 0.8200 | 14% (+0.34) | 0% (+0.00) | 0% (+0.00) | 2% (+0.06) | 84% |
| quezon | 1.673 | 2.396 | 4.069 | 4.069 | 0.9832 | 0.8200 | 0.8200 | 14% (+0.34) | 0% (+0.00) | 0% (+0.00) | 2% (+0.06) | 84% |

Mean of the five provinces: SWS hunger + last label 13%, news tone + news without a driver 2%, five drivers 84%. Signed values (log-odds) in brackets.

**Check:** base + sum(SHAP) reproduces the model's raw log-odds (max difference 1.6e-04, from the 4-decimal rounding of the stored contributions) and the calibration reproduces every served probability (max difference 4.9e-05). Between 13% and 63% of a forecast's |SHAP| lies outside the five drivers; the explainability response does not say how much (the static note only says 'part of the forecast'), and `otherPct` is computed by the engine for provinces but not returned by the API, and not computed for the region.

## 3. How the region driver shares are computed, and whether they match the region index

**Current rule** (`explainability_region`): for each driver, the region share is the pooled |group SHAP| (raw-model log-odds) summed over the five provinces; the direction is the sign of the sum of the provinces' signed contributions; `signedContribution` is their mean. No probability enters.

**The region index** is the mean of the five *calibrated probabilities* (item 1).

These are on different scales. A province whose raw output is saturated (raw p 0.99+) can carry large log-odds SHAP that barely change its probability, so the current rule lets it dominate the region panel while it hardly moves the index. Converting each province's contributions to their effect on that province's probability (scale each by (sigmoid(z) - sigmoid(base)) / (z - base), which makes them add up exactly to its raw probability minus the base probability) and averaging over the five provinces gives contributions that add up exactly to the region index's change from its base (the C2 calibration is linear, so it scales all of them by the same `a`).

| Quarter | Driver | Current: share, direction | Probability scale: share, direction (contribution to the mean raw p) |
|---|---|---|---|
| 2026-Q1 | market | 66%, increases | 66.3%, protective (-0.0077) **(direction differs)** |
| 2026-Q1 | climate | 4%, increases | 4.0%, increases (+0.0016) |
| 2026-Q1 | fish_kill | 3%, protective | 3.1%, protective (-0.0000) |
| 2026-Q1 | employment | 26%, increases | 26.0%, increases (+0.0102) |
| 2026-Q1 | ofw_remittance | 1%, increases | 0.6%, increases (+0.0002) |
| 2026-Q2 | market | 63%, protective | 69.5%, protective (-0.1668) |
| 2026-Q2 | climate | 6%, increases | 4.9%, increases (+0.0141) |
| 2026-Q2 | fish_kill | 15%, protective | 12.9%, protective (-0.0100) |
| 2026-Q2 | employment | 16%, increases | 12.3%, increases (+0.0351) |
| 2026-Q2 | ofw_remittance | 0%, increases | 0.3%, increases (+0.0008) |
| 2026-Q3 | market | 49%, protective | 52.6%, protective (-0.0185) |
| 2026-Q3 | climate | 5%, increases | 3.9%, increases (+0.0034) |
| 2026-Q3 | fish_kill | 10%, increases | 9.6%, increases (+0.0006) |
| 2026-Q3 | employment | 36%, increases | 33.5%, increases (+0.0293) |
| 2026-Q3 | ofw_remittance | 0%, protective | 0.4%, protective (-0.0003) |
| 2026-Q4 | market | 60%, increases | 63.6%, protective (-0.0653) **(direction differs)** |
| 2026-Q4 | climate | 5%, protective | 5.0%, protective (-0.0089) |
| 2026-Q4 | fish_kill | 14%, protective | 12.0%, protective (-0.0197) |
| 2026-Q4 | employment | 19%, increases | 18.1%, increases (+0.0347) |
| 2026-Q4 | ofw_remittance | 2%, protective | 1.3%, protective (-0.0024) |
| 2027-Q1 | market | 75%, increases | 76.3%, protective (-0.0100) **(direction differs)** |
| 2027-Q1 | climate | 0%, increases | 0.5%, increases (+0.0010) |
| 2027-Q1 | fish_kill | 2%, increases | 1.5%, increases (+0.0030) |
| 2027-Q1 | employment | 22%, increases | 20.9%, increases (+0.0412) |
| 2027-Q1 | ofw_remittance | 1%, protective | 0.7%, protective (-0.0015) |

**Finding: inconsistent.** In 2026-Q1, 2026-Q4 and 2027-Q1 the current panel says Market / Prices *raises* the region's risk, while on the index's own scale it *lowers* it: Cavite, Laguna, Rizal and Quezon are saturated (raw p 0.98-0.999), so their positive Market log-odds barely move their probabilities, while Batangas (raw p 0.09-0.61) is pulled down by Market. In 2026-Q4 the region index (0.789) is 0.089 *below* its base, and Market accounts for most of that; the current panel shows Market as the main factor raising it. The equal-weight mean of the province shares (an alternative that ignores probabilities) differs from the pooled shares by at most 4.4 points and does not fix the direction. -> B3.

## 4. Share and direction of every driver; 0% drivers labelled `increases_risk`

The left-panel card ('Why is this province at risk?', `RiskDriversCardBody`) and the right-panel SHAP card (`ShapDriverList`) both read the same `/explainability` response (same query key), and the narrative is built from the same list, so share and direction are identical on both sides for every row below (no other dashboard endpoint returns driver directions).

| Quarter | Scope | Market | Climate | Fish Kill | Employment | OFW |
|---|---|---|---|---|---|---|
| 2026-Q1 | cavite | 59% up (red) | 9% up (yellow) | 3% down (yellow) | 28% up (red) | 1% up (yellow) |
| 2026-Q1 | laguna | 81% up (red) | 1% up (yellow) | 3% down (yellow) | 15% up (yellow) | 0% up (yellow) |
| 2026-Q1 | batangas | 73% down (green) | 2% up (yellow) | 2% up (yellow) | 23% up (red) | 0% up (yellow) |
| 2026-Q1 | rizal | 37% up (red) | 9% up (yellow) | 7% down (yellow) | 46% up (red) | 1% up (yellow) |
| 2026-Q1 | quezon | 64% down (green) | 3% up (yellow) | 3% up (yellow) | 29% up (red) | 1% up (yellow) |
| 2026-Q1 | CALABARZON | 66% up (red) | 4% up (yellow) | 3% down (yellow) | 26% up (red) | 1% up (yellow) |
| 2026-Q2 | cavite | 48% up (red) | 12% up (yellow) | 17% down (yellow) | 23% up (red) | 0% up (yellow) |
| 2026-Q2 | laguna | 56% up (red) | 6% up (yellow) | 14% down (yellow) | 23% up (red) | 1% down (yellow) |
| 2026-Q2 | batangas | 77% down (green) | 4% up (yellow) | 11% down (yellow) | 8% up (yellow) | 0% up (yellow) |
| 2026-Q2 | rizal | 61% down (green) | 5% up (yellow) | 18% up (yellow) | 16% up (yellow) | 0% up (yellow) |
| 2026-Q2 | quezon | 55% down (green) | 5% up (yellow) | 18% up (yellow) | 21% up (red) | 1% up (yellow) |
| 2026-Q2 | CALABARZON | 63% down (green) | 6% up (yellow) | 15% down (yellow) | 16% up (yellow) | 0% up (yellow) |
| 2026-Q3 | cavite | 51% up (red) | 7% up (yellow) | 11% down (yellow) | 31% up (red) | 0% down (yellow) |
| 2026-Q3 | laguna | 47% down (green) | 4% up (yellow) | 9% up (yellow) | 40% up (red) | 0% down (yellow) |
| 2026-Q3 | batangas | 69% down (green) | 1% up (yellow) | 6% up (yellow) | 24% up (red) | 0% down (yellow) |
| 2026-Q3 | rizal | 32% up (red) | 7% up (yellow) | 13% up (yellow) | 47% up (red) | 1% down (yellow) |
| 2026-Q3 | quezon | 27% up (red) | 7% up (yellow) | 18% down (yellow) | 47% up (red) | 1% down (yellow) |
| 2026-Q3 | CALABARZON | 49% down (green) | 5% up (yellow) | 10% up (yellow) | 36% up (red) | 0% down (yellow) |
| 2026-Q4 | cavite | 58% up (red) | 3% up (yellow) | 14% down (yellow) | 23% up (red) | 2% down (yellow) |
| 2026-Q4 | laguna | 51% up (red) | 9% down (yellow) | 18% down (yellow) | 19% up (yellow) | 3% down (yellow) |
| 2026-Q4 | batangas | 66% down (green) | 5% down (yellow) | 11% down (yellow) | 17% up (yellow) | 1% down (yellow) |
| 2026-Q4 | rizal | 57% up (red) | 7% down (yellow) | 15% up (yellow) | 19% up (yellow) | 2% down (yellow) |
| 2026-Q4 | quezon | 67% up (red) | 1% down (yellow) | 12% down (yellow) | 18% up (yellow) | 2% down (yellow) |
| 2026-Q4 | CALABARZON | 60% up (red) | 5% down (yellow) | 14% down (yellow) | 19% up (yellow) | 2% down (yellow) |
| 2027-Q1 | cavite | 73% up (red) | 0% up (yellow) | 2% up (yellow) | 24% up (red) | 1% down (yellow) |
| 2027-Q1 | laguna | 73% up (red) | 0% up (yellow) | 2% up (yellow) | 24% up (red) | 1% down (yellow) |
| 2027-Q1 | batangas | 79% down (green) | 1% up (yellow) | 1% up (yellow) | 18% up (yellow) | 1% down (yellow) |
| 2027-Q1 | rizal | 73% up (red) | 0% up (yellow) | 2% up (yellow) | 24% up (red) | 1% down (yellow) |
| 2027-Q1 | quezon | 73% up (red) | 0% up (yellow) | 2% up (yellow) | 24% up (red) | 1% down (yellow) |
| 2027-Q1 | CALABARZON | 75% up (red) | 0% up (yellow) | 2% up (yellow) | 22% up (red) | 1% down (yellow) |

'up' = `increases_risk`, 'down' = `protective`; (colour) = the API's `color`.

**0% drivers labelled `increases_risk` (11):** 2026-Q1 laguna ofw_remittance; 2026-Q1 batangas ofw_remittance; 2026-Q2 cavite ofw_remittance; 2026-Q2 batangas ofw_remittance; 2026-Q2 rizal ofw_remittance; 2026-Q2 CALABARZON ofw_remittance; 2027-Q1 cavite climate; 2027-Q1 laguna climate; 2027-Q1 rizal climate; 2027-Q1 quezon climate; 2027-Q1 CALABARZON climate. They are tiny positive values (or exactly 0: the engine labels `v >= 0` as increases_risk) shown as a 0% bar that 'raises' risk. -> B1.

## 5. Province spread: raw model probability vs calibrated probability

| Quarter | a (shrink) | raw p per province | calibrated p per province | raw range | calibrated range | ratio | raw log-odds range |
|---|---|---|---|---|---|---|---|
| 2026-Q1 | 0.65 | cav 0.9996, lag 0.9998, bat 0.9944, riz 0.9992, que 0.9961 | cav 0.8925, lag 0.8926, bat 0.8891, riz 0.8922, que 0.8902 | 0.0054 | 0.0035 | 0.65 | 3.22 |
| 2026-Q2 | 0.6 | cav 0.9895, lag 0.9948, bat 0.0450, riz 0.9368, que 0.9776 | cav 0.8743, lag 0.8775, bat 0.3076, riz 0.8427, que 0.8672 | 0.9498 | 0.5699 | 0.60 | 8.31 |
| 2026-Q3 | 0.65 | cav 0.9958, lag 0.9952, bat 0.9732, riz 0.9973, que 0.9860 | cav 0.9001, lag 0.8997, bat 0.8854, riz 0.9010, que 0.8937 | 0.0241 | 0.0156 | 0.65 | 2.33 |
| 2026-Q4 | 0.7 | cav 0.9975, lag 0.9914, bat 0.0939, riz 0.9988, que 0.9981 | cav 0.9165, lag 0.9122, bat 0.2839, riz 0.9173, que 0.9169 | 0.9049 | 0.6334 | 0.70 | 8.98 |
| 2027-Q1 | 0.3 | cav 0.9832, lag 0.9832, bat 0.6137, riz 0.9832, que 0.9832 | cav 0.8200, lag 0.8200, bat 0.7091, riz 0.8200, que 0.8200 | 0.3695 | 0.1109 | 0.30 | 3.61 |

**Finding.** The C2 shrinkage is linear (p' = a p + (1 - a) base rate), so it scales every difference between provinces by exactly `a` (0.60-0.70 at lead 1, 0.30 at lead 2) and never reorders or merges provinces. It does not turn 0.95/0.80 into 0.89/0.89. The near-identical values (e.g. 2026-Q4: 0.9122-0.9173, 2026-Q1: 0.8891-0.8926) come from the raw model already being saturated: log-odds differing by 2-3 units (e.g. Laguna 4.75 vs Rizal 6.72 in 2026-Q4) map to raw probabilities 0.991 vs 0.999. The four identical 0.8200 values in 2027-Q1 are four identical raw outputs (the lead-2 model puts those provinces in the same leaves), not a calibration effect.

**Proposal (not implemented; calibration unchanged):** (a) show the ranking's tie-break from the raw log-odds margin, which still separates saturated provinces (e.g. 2026-Q4 Rizal 6.72 > Quezon 6.27 > Cavite 6.01 > Laguna 4.75), labelled as 'model margin, uncalibrated'; or (b) a pre-registered experiment replacing linear shrinkage with a log-odds calibration (Platt / temperature scaling fitted on earlier dates only), judged on the same 65 rows (Brier, balanced accuracy). Either needs approval; neither changes a served probability today.

## 6. Bar colour in the left panel (read-only)

`frontend/src/components/LeftPanel.tsx:277` (`RiskDriversCardBody`) maps the API's `color`: `red` -> `--risk-high` (red), `green` -> `--risk-low`, anything else -> `--risk-moderate`. The backend `trigger_color` (`backend/app/services/dashboard.py`) returns `yellow` for any share <= 20% *whatever its direction*, `red` above 20% when increasing, `green` above 20% when protective. In `index.css`, `--risk-low` is yellow (45 93% 55%) and `--risk-moderate` is orange (#F5A623); there is no green.

**Q4 2026 Employment** (CALABARZON): 19%, `increases_risk`, color `yellow` -> drawn orange (`--risk-moderate`), the same orange as Fish Kill (14%, protective) and Climate (5%, protective). So the colour does not contradict Employment's direction outright, but it does not show it: below 20% an increasing and a protective driver look the same, and Employment changes colour between provinces on size alone (Cavite 23% red, Laguna 19% orange, both increasing). A large protective driver is drawn yellow (`green` -> `--risk-low`), not green. Report only; no frontend change made.


## Phase B (backend only; applied after this audit)

- **B1** (`app/api/v1/insights.py`, `svc.nonzero_triggers`): the `/explainability` response omits drivers whose
  share rounds to 0%; the remaining shares are unchanged and still sum to 100. The service functions still return
  all five drivers, so the PDF/report tables keep printing "0%".
- **B2** (`e31_engine.five_trigger_drivers` returns the |SHAP| outside the five drivers by source;
  `svc.attribution_sentence`): the note opens with this forecast's own split, e.g. "Regional hunger survey (SWS)
  inputs and the latest published label: 31% of this forecast; news tone and news that matches no driver: 11%;
  the five drivers below explain the remaining 58%." It replaces the general "part of the forecast also
  depends on ..." sentence. The basis is |SHAP|, the same as the bars'.
- **B3** (`svc.explainability_region`, `svc._prob_scale`): each province's contributions are multiplied by
  (sigmoid(z) - sigmoid(base)) / (z - base) before pooling. Shares = pooled |scaled contribution|; direction = sign
  of their sum; `signedContribution` = their mean, i.e. the contribution to the mean uncalibrated probability.
  The linear C2 calibration scales all of them by `a`, so the shares and directions are those of the regional
  index. Province panels are unchanged. The default e49 record is affected too: CALABARZON 2026-Q4 changes from
  Market 65% increasing / Climate 33% / Fish Kill 2% to Market 72% / Climate 26% / Fish Kill 2%, all protective.
- Calibration (item 5) and the frontend colour rule (item 6): not changed.
