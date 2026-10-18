# Chapter IV material: detecting rising food stress (E58)

## 4.x Diagnosis of Missed High-Risk Quarters

The rolling-origin evaluation showed that the final LightGBM model identified only three of the ten province-quarters in which food insecurity risk rose from LOW to HIGH between the latest observed quarter and the forecast target. An analysis of each missed case found two distinct causes.

The first cause arose from the timing of the hunger data. In the four missed onsets of 2024-Q2, the price component of the model correctly estimated a high probability of food-price pressure (0.81 to 0.96). However, the latest SWS hunger round available on the issue date, 1 January 2024, showed 10.3 percent, below the 11.3 percent threshold, and this lowered the forecast. The following round, which reported a higher rate, was published three weeks after the issue date, and hunger reached 19.6 percent in the target quarter. Because SWS results are published one to two months after each survey, the hunger information available to a two-quarter-ahead forecast is three to four quarters older than the quarter being forecast.

The second cause was food-price increases that the model did not anticipate from CPI data that were seven months older than the end of the target quarter. No trigger group (rice prices, typhoons, employment, remittances, fisheries, or news coverage) consistently distinguished the missed cases from the correctly forecast ones.

## 4.x Early-Warning Rule

On the basis of this diagnosis, a two-signal early-warning rule was defined and frozen before evaluation:

| Level | Condition |
|---|---|
| ALERT | the model forecasts HIGH food insecurity risk |
| EMERGING | the model's food-price component indicates likely price pressure even though the latest, older hunger reading does not yet confirm elevated hunger |

The rule uses the same LightGBM model without retraining. Its purpose is to keep a stale hunger observation from suppressing a price warning, while stating clearly that the hunger condition is not yet confirmed.

## 4.x Early-Warning Performance

Across the same 50 province-quarters (2024-Q2 to 2026-Q3), the early-warning rule detected seven of the ten emerging high-risk events, compared with three for the model alone and none for naive persistence. It also raised HIGH-risk recall from 0.556 to 0.778 and accuracy from 0.72 to 0.78, with a false-positive rate of 0.22.

Alternative approaches did not improve detection:

| Approach | Effect |
|---|---|
| Lower cost-sensitive threshold | added false alarms without detecting more onsets |
| Training-selected threshold | flagged half of all LOW quarters |
| Class-weighted LightGBM | detected fewer high-risk quarters |
| Separate classifier of rising food prices | detected no additional onsets |

These results should be read with caution, for four reasons.

First, the early-warning rule and the original model made identical decisions in nine of the ten quarters. The entire improvement came from 2024-Q2, a single regional increase in hunger that affected four provinces at once.

Second, the 95 percent interval for onset recall spans 0.2 to 1.0.

Third, a simple rule based only on the CPI projection performed almost as well, which indicates that the gain arises from the treatment of delayed hunger data rather than from the learning algorithm.

Fourth, the three remaining missed onsets were all food-price increases that the available data did not anticipate.

In 2021 to 2023, when hunger was below the threshold, 24 of 29 province-quarters with food-price pressure did not meet the food insecurity risk definition. EMERGING warnings may therefore produce more false alarms in periods of low hunger.

## 4.x Implications for DA Region IV-A

For decision support, each warning is shown on the dashboard together with:

- its level and direction of change;
- the probabilities of price pressure and of HIGH risk;
- the target quarter;
- the latest hunger reading and its quarter;
- the leading contributing factors;
- the data status.

Warnings are presented as model warnings for review and planning, and not as official classifications. The rule is suitable for experimental use and historical demonstration. It is not yet suitable for production deployment, because its benefit rests on a single episode, and because its behaviour during periods of low hunger can only be confirmed with future quarters and with provincial food insecurity data.
