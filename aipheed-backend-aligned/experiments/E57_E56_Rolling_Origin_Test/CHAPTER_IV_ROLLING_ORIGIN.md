# Chapter IV material: rolling-origin reliability of the final model (E57)

## 4.x Reliability Across Historical Quarters

To determine whether the final LightGBM model generalizes across time, it was re-executed at every historical forecast origin that the available data supports. Each forecast was produced two quarters ahead using only information published before its issue date, and it was sealed before the corresponding outcome was compared. This yielded ten target quarters, from 2024-Q2 to 2026-Q3, covering 50 province-quarters. Earlier quarters could not be evaluated because the study period begins in 2021, which leaves too little training history before 2024.

Across all ten quarters the model achieved an accuracy of 72.0 percent, a balanced accuracy of 0.684, a HIGH-risk recall of 0.556, and a LOW-risk recall of 0.812. Quarter-level accuracy ranged from 20 percent to 100 percent, with a median of 80 percent, and six of the ten quarters reached 75 percent. The 95 percent interval for accuracy, computed by resampling whole quarters, was 0.58 to 0.84.

The model outperformed naive persistence and the training-period majority class in Brier score, and both differences excluded zero. Its advantage over a climatology-based probability and over the previous LightGBM version was not statistically demonstrated.

Performance was uneven across conditions:

| Condition | Accuracy |
|---|---|
| Food stress falling | 0.80 |
| Food stress rising | 0.53 |
| Later quarters | 0.84 |
| Earlier quarters | 0.60 |

When food stress was rising, the model detected only 4 of 10 HIGH-risk province-quarters. Its weakest quarter (2024-Q2) coincided with a sharp increase in regional hunger, from 10.3 to 19.6 percent, that had not yet been published on the issue date. In the later quarters, where almost no province was at HIGH risk, a rule predicting LOW for every province was slightly more accurate than the model.

Within each quarter, the model's ordering of provinces (within-quarter AUC 0.706) was no more informative than each province's own historical frequency of HIGH risk (0.765). Quezon was ranked highest in eight of ten quarters, and Cavite was the least accurately forecast province (0.40).

These results indicate that the model forecasts the persistence and easing of food-price-driven risk reasonably well, but does not yet reliably anticipate increases in risk, which is the primary purpose of an early-warning system. The 75 percent goal was therefore not met across all evaluable quarters. With only ten quarters available, this conclusion is indicative and not definitive, and it will be tested further against the frozen forecasts for 2027 as their outcomes are published.
