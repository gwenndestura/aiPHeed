# E130 provincial bias and generalization

No model was trained, so no model's bias could be measured. This file records the biases a provincial model would inherit from the reference and the predictors. These are the reasons per-province results would be fragile.

## 1. Reference observations per province

| Province | PFDR values held | Real change 2021→2023 (90 %) | Next round |
|---|---|---|---|
| Batangas | 2 (2021, 2023) | no (+0.4) | not published (latest is 2023) |
| Cavite | 2 | yes, marginal (−1.6, z −1.88) | not published (latest is 2023) |
| Laguna | 2 | no (−1.1) | not published (latest is 2023) |
| Quezon (excl. Lucena) | 2 | yes (−5.7, z −4.74) | not published (latest is 2023) |
| Rizal | 2 | yes (+1.7, z +2.40) | not published (latest is 2023) |

**Generalization across provinces cannot be assessed.** Each province has one change, and pooled metrics would mostly reflect Quezon's, which carries 83 % of the squared change.

## 2. Which province would dominate

**Quezon 2021 (6.6 %) is the only high-deprivation province-year.** It is 1 of 10 values, and it drives:
- the 2021 heterogeneity (Cochran's Q = 29.6, p < 0.0001);
- most of the 2021→2023 change variance.

In 2023 the provinces are statistically indistinguishable (Q = 6.35, p = 0.17).

## 3. Risk-level bias

With one high value in ten, a model would be fitted almost entirely to the low range of 0.8–2.6 %.

**Expected bias:**
- it would underestimate any return to Quezon-2021 levels, the "sharp increase" case the brief asks about;
- it would overstate precision in the low range, where the CVs are largest (up to 62 %).

The observed ordering also **reversed** between rounds (Spearman −0.82; stability p = 0.022). A model that learned the 2021 province order would rank 2023 backwards.

## 4. Bias in the predictors

| Predictor issue | Evidence | Consequence |
|---|---|---|
| News coverage differs by province | Admitted articles per quarter: Cavite 4.0, Batangas 2.6, Quezon 1.7, Laguna 1.5, Rizal 1.1. 46 % of province-quarters have none. FSSI v3 is missing in 56.5 %. | News would speak mainly for Cavite. Rizal, the 2023 highest, is the least covered. |
| Typhoon exposure is nearly uniform | Local (100 km) counts are identical across provinces in 82 % of quarters and zero in 73 % | Climate shocks cannot differentiate provinces |
| Remittances and ONI are national | Identical for all provinces | No provincial information |
| Employment is annual | Provincial LFS is 4–7 quarters old at Lead 2 | Slow, stale provincial signal |
| Food CPI is mostly common | 74.7 % common; deviations keep autocorrelation 0.54 at two quarters | The only frequent, genuinely provincial signal. It also ranked the 2021→2023 PFDR changes (Spearman 0.90, N = 5, partly mechanical). |

## 5. Plan for a future run (protocol §8–§9)

- Report per-province rows, MAE and skill against its own persistence; N6 requires no province below 0.
- Report errors by reference range: low (< 1.5 %), middle (1.5–3 %) and high (≥ 3 %).
- Report hits on increases beyond sampling error.
- Add a province-held-out supplement.
- Never claim generalization from pooled metrics alone.
