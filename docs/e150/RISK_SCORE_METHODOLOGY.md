# What each score means

## 1. Estimated food-insecure households (%)

Modelled estimate of HFIAS any-level prevalence on a logit scale, then converted to a percentage. Selected arm A-H:

    mu = S(T) + L(p) + w(p) × D(p)

| Term | Definition |
|---|---|
| S(T) | Shared level. Two-way fixed effects on released rounds, weighted by 1/(SE² + 0.02), which removes differences in which provinces each round sampled; carried to T by its fitted slope |
| L(p) | Structural level. LightGBM on poverty, subsistence, poverty gap, density, food threshold and Radimer 2011; target = position relative to S; cross-fitted so the prediction comes from a model that excluded the province's region |
| D(p) | Precision-weighted mean of (measured relative position − out-of-fold L) over the province's released rounds, with variance SE² + σ² |
| w(p) | τ² / (τ² + 1/Σ(1/v)), where τ² is the permanent province variance from pairs of rounds |

**A-G adds** a LightGBM residual trained on as-of survey forecast errors, using all five trigger groups and the response signal, with monotone constraints where theory gives a sign (for example food CPI up cannot lower risk). It may learn no residual.

**A-Hh adds** loading × h(p, T). h is a LightGBM trained on 147 measured SWS area-quarters, predicting change in area hunger beyond a history-only version of the same model, then evaluated on the province's own inputs. The loading is a non-negative ridge fit on survey errors.

**Is this prevalence?** On development rows, yes by the locked test: slope 1.10 [0.69, 1.37], coverage 0.87. On the pool, slope 1.05. On 2021 alone, 0.85. It is an estimate, and no survey was run in the quarter it describes.

## 2. P(HIGH)

P(HIGH) = Φ(mu / σ), the probability that prevalence is ≥ 50 %, with σ the root-mean-square of as-of survey errors (0.46 on the logit scale live). On the pool, ECE is 0.034.

**On the holdout it was overconfident:** ECE 0.28, Brier 0.26. That test used a smaller σ (0.316), which may have contributed; this was not separately tested. So treat extreme probabilities with care.

## 3. HIGH or LOW

**HIGH if estimated prevalence ≥ 50 %, otherwise LOW,** as approved by the panel. It applies on this calibrated scale only. Because all five current intervals include 50 %, none of the current classes is firm.

## 4. Uncertainty interval

mu ± q90, with q90 the 90th percentile of absolute as-of survey errors (conformal-style), converted to percentage points. Pool coverage is 0.89.

The interval covers survey-quarter forecast error. It doesn't separately prove accuracy for a quarter with no survey.

## 5. Approach B risk score (not selected)

100 × P(prevalence ≥ 50) from a LightGBM classifier, Platt-calibrated in region-grouped folds. It is an index of risk, **not a prevalence**. It is reported as a sensitivity value only. It identified no LOW province on the pool, and its live scores (56 to 74) point in a different direction from A-H, so it shouldn't be shown as if it were a percentage of households.

## 6. LGU priority

Priority = P(HIGH) of the province × vulnerability, with vulnerability = 0.6 × poverty percentile + 0.4 × density percentile across 142 LGUs. A ranking aid, **not a municipal measurement or a probability**.

## 7. How DA should read this

* "39.8 %" means: the model's estimate for that quarter from past surveys and current indicators. **No household was interviewed for it.**
* Look at the interval first, then the class.
* Compare it with the province's last measured value and its date.
* SHAP values explain the model's arithmetic, not causes.
