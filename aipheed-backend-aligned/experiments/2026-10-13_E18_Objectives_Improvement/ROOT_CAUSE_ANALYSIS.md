# Root-Cause Analysis: Why the Current Model Does Not Beat Simple Baselines (E18)

**Evidence sources:**

- **E18:** run `runs/20261013T065509Z/` (`metrics.json`; replicate byte-identical)
- **Earlier experiments:** E12, E13, E17 and E17 v3 reports (cited, not regenerated)

**Ordering:** each cause is given with its evidence. They are ranked from most to least important.

| # | Cause | Evidence | Correctable? |
|---|---|---|---|
| 1 | **The target is a constructed label, and its latest value already is the best forecast.** HIGH means H + 2D > 14.6. When the latest H and D are known, the "structural rule" N1 gives **exactly the same predictions as naive persistence** (agreement 1.00 at every horizon). Any model must therefore beat a forecast that is already the label's own recent value. | E18: N1 = persistence in every fold (h = 1–5) | **No.** This is a property of the target. It can only be addressed by changing or validating the target (adviser decision). |
| 2 | **The regional term dominates, and regional hunger is not forecastable beyond its latest value.** 65% of label variance is shared by all provinces (E12). At the 2027-Q1 horizon (h = 3), no hunger model beats carry-forward on 9 origins. | E12; E18 `continuous.H\|h3` (carry-forward MAE 5.67; best alternative EWMA 5.63, fails the rule) | **No,** with the available predictors |
| 3 | **Class shift and very few LOW cases.** Training years are mostly LOW (HIGH 3/15 in 2021, 4/15 in 2022, 5/20 in 2023). Test years are mostly HIGH (18/20 in 2024, 9/10 in 2025). LOW test cases number 9 at h = 1, 3 at h = 2 and **2 at h = 3**. | E17 inventory; E18 selection records | **No.** More quarters are needed (2026-H2 onward, under authorization). |
| 4 | **The current model learns trending price *levels*, which act as a time proxy.** Its largest mean \|SHAP\| values are the food CPI **index level**, commodity levels and rice price level (h = 1 and h = 3). Those rise over time and separate "early = LOW" from "late = HIGH". It does not learn a causal signal. | E18 SHAP aggregation (M: food_cpi 0.60 / 1.07; commodity_livestock, rice_price, leafy_veg) | **Partly.** The constrained N4 (stationary features: D, H_last, F5, cpi_dev, FSSI, unemployment) uses D and H as expected, but did not beat persistence. |
| 5 | **Weak NLP signal.** The FSSI rests on 69 retained articles; two of five triggers are always zero. The NLP-only baseline is the weakest arm (accuracy 0.20–0.40). The NLP-only LightGBM has the best AUC at h = 2–3, but on 3 and 2 LOW cases. | E17 Objective 1 evidence; E18 B3 and S6 rows | **Only with more news data.** It cannot be fixed with existing data. |
| 6 | **Information timing changes the apparent accuracy.** The same model (M) scores **0.629** at E17's strict k = 1 (labels and SWS only as published) but **0.825** at E18's h = 1, where the information set includes the whole previous quarter. Most of the earlier "good" results came from information that is **not available in real time** (SWS publishes 1–15 weeks after fieldwork). | E17 `HORIZON_RESULTS.csv`; E18 `h1\|A`. The earlier 0.818 used a rule admitting unpublished labels (E17 R0). | **Yes.** It is corrected by always evaluating with timing-valid information. E18's primary h = 3 is realizable for 2027-Q1. |
| 7 | **Little provincial differentiation.** Forecasts give on average **1.25–1.6 distinct labels per quarter** across five provinces. Differences come only from D, which E13 and E17 found to regress toward zero. | E18 `mean_distinct_labels_per_quarter` | **No,** without a provincial outcome |
| 8 | **Features with unverifiable timing or zero-filled gaps** (`poverty_incidence`, zero-fill) | E17 timing audit | **Yes.** Excluded in E17 and E18. |

## Conclusion

**The poor accuracy is mainly a target and data problem, not a tuning problem:**

- the label's own recent value is the best available forecast;
- its dominant term (regional hunger) is not predictable from the available inputs;
- the test period has too few LOW cases to evaluate any classifier.

**What E18 corrected:**

- timing validity;
- the level-variable proxy, through the stationary-feature model;
- tuning on training data only.

**These corrections did not produce a model that beats persistence.**
