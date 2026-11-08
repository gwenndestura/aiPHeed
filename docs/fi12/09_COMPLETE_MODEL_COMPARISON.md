# Deliverable 9. Complete model comparison

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

| Model | Target | Data source | Geography | Methodology | Lead time | MAE/RMSE | Metrics | Baseline improvement | Reliability | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| Served P0H4 | B: T43c proxy (regional hunger × provincial price) | SWS BL + PSA CPI + 12 FIRI families | province (price) × region (hunger) | LightGBM × closed-form hunger | L1 reliable on T43c [F] | n/a (probability) | T43c L1 acc 0.843, BA 0.776 [F]; PSA 2023 ρ 0.55 (n 5) | beats PERSIST-SI on T43c; no provincial baseline comparison possible beyond 2023 | T43c Lead 1 only | keep; label as proxy |
| P0H4-U / CR / CR-ANC / UNI-FINAL / CH1-LGBM / E108 | B | same family | same | variants | L1 [F] | n/a | PSA 2023 ρ: P0H4-U 0.55, CR 0.46, CR-ANC 0.15, UNI 0.55, CH1 -0.36, E108 -0.21 | none | none on provincial outcomes | no challenger better |
| FI10 (L1 selection) | D: provincial food-price pressure | PSA provincial CPI + 5 trigger groups | province | pooled LightGBM | none adopted [F] | n/a | price L1 BA 0.725 [F]; food poverty pooled ρ -0.43; FNRI 2015 ρ -0.20 | ties damped persistence on price; below every food-poverty baseline | price: provisional | keep as price pressure only |
| FI9 C0 | C: regional SWS hunger | SWS BL | Balance Luzon | damped persistence | L1 provisional [F] | conformal interval | acc 0.823, BA 0.714 [F] | below naive persistence | regional only | keep, provisional |
| Naive persistence (SWS) | C | SWS BL | Balance Luzon | latest reading | L1 (FI7 rules) [F] | — | acc 0.871, BA 0.743 [F] | is the baseline | best regional | reference |
| FI11 | C | SWS + 5 triggers | Balance Luzon | ridge/LightGBM/logit/RF | none [F] | — | L1 BA 0.746 [F] | not better than naive | none | rejected |
| FNRI 2015 severe ranking (baseline) | B (as predictor) | FNRI 2015 | province | static ranking | — | — | food poverty pooled ρ 0.32 | best ranking baseline; not significant | — | context |
| Regional prior-wave value (baseline) | B levels | PSA | CALABARZON | constant | — | MAE 1.10 (2021), 0.80 (2023) | — | best 2023 level | — | context |

## Winners by target
| Target | Best | Why |
|---|---|---|
| A. Direct provincial food insecurity | **None can be identified** | No model has historical forecasts for a verified, distinguishable observation |
| B. Provincial food poverty | **No model.** Best simple reference: FNRI 2015 severe ranking (ranks) and regional prior-wave value (levels) | Neither is significant; nothing beats them |
| C. Regional SWS hunger | **Naive persistence** (FI9 C0 is the served, provisional variant) | Earlier studies [F] |
| D. Food-price pressure | **FI10 pooled LightGBM** (Lead 2 provisional) | Earlier studies [F] |
| Overall methodology | **Two separate, honestly labelled layers** (regional measured hunger outlook + provincial price-pressure and vulnerability context) | Deliverable 10 |

No model is declared a winner across incompatible outcomes.
