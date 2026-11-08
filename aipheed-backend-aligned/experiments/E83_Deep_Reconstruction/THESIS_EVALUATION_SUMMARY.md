# aiPHeed — thesis-ready evaluation summary (E83, 2026-10-21)

## What was tested

- **Models.** Every candidate model and every required baseline was scored on the same out-of-sample forecasts.
- **Forecasts.** 13 target quarters (2023-Q1 to 2026-Q3) × 5 provinces = 65 forecasts per lead. Each forecast used
  only data published before its issue date.
- **Target.** The approved target T43 (regional SWS hunger above 11.3% **and** high provincial food-price pressure).
- **Pre-registration.** The plan was frozen before any result (PROTOCOL.md).

## Results

| Lead (issued at the start of the quarter after the data quarter) | Best model | Accuracy | Balanced accuracy | HIGH caught | Beats baselines? |
|---|---|---|---|---|---|
| 0 — the quarter just ended (nowcast) | structural model | 0.82 | 0.75 | 62% | no: the "current state" rule is better (0.92) |
| 1 — the current quarter | structural model (pre-registered) | **0.85** | 0.75 | 56% | yes on every measure, but not significant with 13 quarters (p = 0.105) |
| 1 — the current quarter | hybrid LightGBM + structural (exploratory) | **0.88** | 0.83 | 75% | yes, p = 0.098; chosen after seeing results, so it awaits the sealed test |
| 2 — the next quarter (thesis "Lead-2") | structural model, own threshold | 0.71 | 0.58 | 31% | **no** (always-LOW scores 0.75) |
| 3 | — | ≤ 0.58 | < 0.5 | ≤ 12% | no |

## What this means

- **The > 75% Lead-2 goal is not demonstrated, and the 80% target is not reached.**
- **The longest lead with real skill is Lead 1.** Its post-hoc hybrid reaches 88%. It needs prospective confirmation:
  the forecasts are sealed and hashed (1331d498…).
- **Since 2023-Q4 the approved label has been a food-price-pressure label.** Hunger was above 11.3% in every quarter.
  In 2025–26 hunger rose while food inflation fell, so the label turned LOW while measured hunger peaked. Provinces
  differ only through their food prices.
- **News does not improve the forecasts.** This was tested with headlines, lawfully recovered lead text (730
  articles) and de-duplicated event features.
- **Prices carry the predictive signal.** Climate, agriculture and employment add little on their own. Employment and
  remittances are national.
- **The 142 city and municipality values are planning estimates.** They are derived from the province estimate, not
  measured local rates. 25 of them rest on imprecise PSA poverty estimates and are flagged.

## Limitations to state in the defense

- 13 evaluable quarters and one regional hunger series.
- No provincial or municipal food-insecurity outcome: CBMS 2024 and provincial FIES are not available to the project.
- News was collected after the fact. Most publishers block or disallow automated access to article text.
- The post-hoc models reuse the evaluated quarters. Only the sealed 2026-Q4 to 2027-Q2 forecasts can validate them.
