# E130 target uncertainty audit (PFDR v1)

All numbers come from `out/reference_uncertainty.json`. These are sampling errors of PSA's survey estimates; model error is a separate quantity.

## 1. Values and their precision

| Province | 2021 (CV %) | 2023 (CV %) | SE 2021 / 2023 (pp) | 90 % interval 2023 | Tolerance 2023 (pp) |
|---|---|---|---|---|---|
| Batangas | 1.0 (33.9) | 1.4 (33.6) | 0.34 / 0.47 | 0.63–2.17 | 0.77 |
| Cavite | 2.4 (28.8) | 0.8 (62.3) | 0.69 / 0.50 | 0.00–1.62 | 0.82 |
| Laguna | 2.4 (24.3) | 1.3 (34.6) | 0.58 / 0.45 | 0.56–2.04 | 0.74 |
| Quezon (excl. Lucena) | 6.6 (17.4) | 0.9 (39.5) | 1.15 / 0.36 | 0.32–1.49 | 0.59 |
| Rizal | 0.9 (34.0) | 2.6 (24.6) | 0.31 / 0.64 | 1.55–3.65 | 1.05 |

- CVs range from 17.4 % to 62.3 %.
- Tolerances (1.645 × SE) range from 0.50 to 1.89 pp.

## 2. Which changes are real

Test: z = Δ / √(SE₂₀₂₁² + SE₂₀₂₃²).

| Province | Δ 2021→2023 (pp) | z | Beyond sampling error at 90 % / 95 % | Minimum detectable change (80 % power, pp) |
|---|---|---|---|---|
| Quezon | −5.7 | −4.74 | yes / yes | 2.99 |
| Rizal | +1.7 | +2.40 | yes / yes | 1.76 |
| Cavite | −1.6 | −1.88 | yes / no | 2.12 |
| Laguna | −1.1 | −1.49 | no / no | 1.83 |
| Batangas | +0.4 | +0.69 | no / no | 1.44 |

- **3 of 5 changes exceed sampling error at 90 %, 2 at 95 %.** This matches E129 (Quezon and Rizal real; Cavite marginal).
- Quezon's change makes up **83 %** of the sum of squared changes (32.5 of 39.3 pp²). Any pooled statistic is dominated by one province.

## 3. Do the provinces differ?

| Round | Cochran's Q (df 4) | p | Between-province SD (pp) | Mean sampling SE (pp) | Signal-to-noise (√τ² / SE) |
|---|---|---|---|---|---|
| 2021 | 29.6 | < 0.0001 | 2.32 | 0.68 | 1.79 |
| 2023 | 6.35 | 0.17 | 0.72 | 0.49 | **0.73** |

**In 2023 the provinces are not distinguishable beyond sampling error.** The 2021 differences come mostly from Quezon.

## 4. Rankings

| Item | Result |
|---|---|
| P(highest province), 2021 | Quezon 0.999 |
| P(highest province), 2023 | Rizal 0.904; Batangas 0.052; Laguna 0.035; Cavite 0.007; Quezon 0.003 |
| Spearman, 2021 order vs 2023 order | **−0.82** (the order reversed) |
| Rank-stability test | If each province's true value were the same in both rounds, a correlation this low would occur with p = **0.022**. The reordering is more than sampling noise: provincial food deprivation genuinely moved. |

PSA itself does not publish provincial rankings when confidence intervals overlap (PSA poverty technical notes).

## 5. Other measurement issues

**Vintage.** The 2021 values held are the 2024-08-15 vintage. The original 2022 release is not held, so a point-in-time forecast issued between 2022 and 2024 cannot be reconstructed exactly.

**Construct coherence.**
- PFDR 2023 and the FIES food share 2023 disagree on the provincial ordering (Spearman −0.20).
- FNRI FIES 2021 cannot separate Batangas from Cavite (the CIs overlap).

**Required forecast precision.** To place 75 % of predictions inside the tolerance, the forecast error against the true value must have SD ≤ 1.022 × SE (`E130_SCORE_AGREEMENT_ANALYSIS.md`). On 2023 precision that means:

| Province | Required SD (pp) |
|---|---|
| Batangas | 0.48 |
| Cavite | 0.51 |
| Laguna | 0.46 |
| Quezon | 0.36 |
| Rizal | 0.65 |

Persistence over the last interval missed by **2.1 pp MAE**.

## 6. Model error vs measurement error

An observed error against the reference is (forecast − truth) − (reference − truth). With independent errors:

E[error²] = model error² + SE²

So even a perfect forecast misses by the reference's SE on average. That is why:
- the tolerance is set to the reference's own 90 % interval;
- prediction intervals for the *observed* reference must include SE_next.

Both are written into the protocol (§4, §7).
