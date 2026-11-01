# Addendum 1: Lead-2 food-price-pressure warning (frozen before scoring)

**What this tests.** Not the Chapter I food-insecurity risk class (T43c). It tests whether the **price part** of the
served P0H4 forecast, π_price (column `P0_price` in `FINAL_ARCHITECTURE/out/predictions.csv`), reliably forecasts the
**price part** of the label (column `price`: the province's food YoY or food-minus-headline YoY above its frozen
2021–22 P60, E40 `label_spec.json`). A pass would support "a reliable Lead-2 food-price-pressure warning", never
"Lead 2 is a reliable food-insecurity forecast".

**No new model, no tuning.** π_price is the served walk-forward output, unchanged. Threshold 0.5. Every quarter was
seen by earlier experiments (development evidence).

**Rows.** Leads 1 and 2, identical rows to the served evaluation (70 and 65). Lead 2 is the question; Lead 1 is
reported for comparison.

**Baselines (fixed now; information known at the issue date O(t), the first day of quarter t+1):**
- always-LOW and always-HIGH;
- price persistence: the same province's price label for quarter t−1 (CPI for t−1 is complete before O(t));
- price climatology: the share of price-HIGH labels among quarters ≤ t−1 for all five provinces.

**Rules (the frozen R1–R7 of FINAL_TARGET_AND_EVALUATION_PROTOCOL.md §7, adapted only in their baselines):**
R1 ≥ 10 target quarters and ≥ 40 rows; R2 accuracy ≥ 0.75; R3 balanced accuracy ≥ 0.70; R4 accuracy > always-LOW,
> always-HIGH and > price persistence; R5 Brier < price persistence and < price climatology, each with a one-sided
paired quarter-cluster bootstrap p < 0.10 (5 000 resamples, seed 2036); R6 precision ≥ 0.60 and recall ≥ 0.60 for
price-HIGH; R7 accuracy ≥ 0.60 in each third of the target quarters (numpy array_split) and leave-one-quarter-out
minimum ≥ 0.70.

**Decision.** "Reliable Lead-2 price warning (development evidence)" only if all seven pass at Lead 2. Otherwise a
negative result. Either way nothing is served without your approval. **Trials:** 1 (plus Lead 1 for comparison).
