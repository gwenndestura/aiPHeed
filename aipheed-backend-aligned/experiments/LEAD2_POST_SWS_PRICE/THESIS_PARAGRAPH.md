# Lead 2 with a post-SWS price cutoff: thesis-ready text

The post-SWS issue study left one limit: every remaining miss came from the food-price component, whose CPI data still stopped at the original issue date. A final variant was therefore pre-registered (protocol SHA-256 `b547e0ab…`). It kept the post-SWS issue date and refitted the served price model walk-forward, with the CPI cutoff of every training and test origin moved to the newest month available on that date (a month counts as available from the first day of the second month after it).

Everything else was unchanged: the features, tuning grid, seeds, other inputs, target, threshold and the seven criteria. Before scoring, three checks were run:

- with the original cutoff, the copied pipeline reproduced the stored price forecasts exactly at their stored precision, and the original code exactly;
- an audit of all 23 origins confirmed that no CPI month later than the issue date was used;
- randomising every later CPI value left the forecasts unchanged.

The cutoff moved by one month at 6 of the 13 test origins. At the others, the survey was released early enough that no newer CPI month existed.

On the same 65 province-quarters, the refreshed model had the best probabilities of any Lead-2 variant:

- Brier score 0.153 (95% CI 0.10–0.21), against 0.167 with the old cutoff and 0.194 at the original issue date;
- ROC-AUC 0.827.

Its classifications at 0.50 were worse. Accuracy was 0.754 and balanced accuracy 0.681, and precision and recall were both 0.529. It failed three criteria: balanced accuracy, beating persistence (it only tied at 0.754), and precision and recall.

It caught none of the seven high-risk province-quarters missed before. It also added four false alarms. Across simulated SWS sampling error, no draw passed all criteria.

The remaining misses therefore do not come from stale price data alone. They arise where a hunger probability near 0.5–0.9 is multiplied by a price probability near 0.5, which keeps the product below the 0.50 threshold.

An independent pre-2021 check of the price component was not possible, because the served price features exist only from 2021.

This was the last variant tested on the 2023–2026 quarters. **Lead 2 remains experimental.** Confirming it now depends only on forecasts sealed the day after each SWS release from 2027 (capped at 67 days after quarter end), with about ten resolved quarters (around early 2030).
