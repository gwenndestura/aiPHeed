# News predictive value

**Pre-specified hypothesis (protocol §9):** price news helps at Leads 2–3, where the CPI base effect runs out.
**Test:** CH1-LGBM with and without its three news columns (N1 FSSI-v3, G_pri_yoy, NG_gap_price), same rows; Brier
difference by quarter-cluster bootstrap; Holm across leads. A placebo (news shuffled across quarters) checks that any
gain is not chance.

## Result (audited inputs)

| Lead | With news | Without | Brier (with − without) | Holm p | Reading |
|---|---|---|---|---|---|
| 0 | 0.850 | 0.850 | −0.0001 | 0.38 | no effect |
| 1 | 0.914 | 0.914 | +0.0004 | 0.38 | no effect |
| 2 | 0.583 | 0.700 | +0.035 | 0.032 | **news hurts** |
| 3 | 0.520 | 0.640 | +0.072 | < 0.001 | **news hurts** |
| 4 | 0.575 | 0.675 | +0.018 | 0.14 | no significant effect |

Placebo (first run): Lead 1 p 0.13, Lead 2 p 0.98, so real news did no better than shuffled news.

**Regional FSSI (Addendum 2).** Provincial FSSI-v3 exists in only 17% of province-quarters. A regional version (all
admitted CALABARZON headlines) covers all 16 evaluation quarters but gives no gain at any lead (best: Lead 2, −0.008,
Holm p 0.055).

## Conclusion

The hypothesis is rejected. News describes what is happening now (it tracks concurrent hunger and prices) rather
than what will happen next. It stays in the model because the thesis requires all 12 families, it is neutral at the
reliable horizon (Lead 1), and the dashboard shows it as **context** with its kind (price, supply, assistance, jobs),
not as a forecast driver.
