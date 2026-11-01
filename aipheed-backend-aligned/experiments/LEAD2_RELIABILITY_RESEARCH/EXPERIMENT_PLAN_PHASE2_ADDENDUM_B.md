# Phase 2, Addendum B: world commodity prices as leading indicators of the price condition (Y10)

**Status.** Frozen (SHA-256 in `common/PLAN2B_SHA256.txt`) before Y10 is run.

**Motivation (Y8, Y9).**

- On independent years, the Lead-2 price condition is forecast no better than by persistence. Its balanced accuracy is about 0.61–0.66.
- With a perfect price condition, persistence hunger passes R2, R3 and R6 together in 90% of 13-quarter windows. With a perfect hunger condition, it does so in 10%.

The price side 5–7 months ahead is therefore the lever. The Philippines imports a large share of its rice, and fuel and fertiliser enter food costs. World prices may lead domestic retail food CPI by several months. This information is **not** in any earlier aiPHeed model.

## Data

World Bank Commodity Price Data (Pink Sheet), monthly nominal USD:

- source file `y10_world_prices/data_acquired/CMO-Historical-Data-Monthly.xlsx`;
- vintage "Updated on January 03, 2025";
- SHA-256 `bd89b83e…`.

Series used: Rice Thai 5%, Crude oil (average), Urea, Maize, Wheat US HRW, Palm oil.

- **Availability:** the Pink Sheet is published on about the 2nd–3rd business day of the following month. At O(t), the newest month used is m0(t), month 2 of quarter t, the same rule as CPI. That is conservative by about one month.
- **Vintage limitation:** the file is one vintage, not real-time vintages. Pink Sheet monthly averages are rarely revised. This is a disclosed limitation.

## Y10 design

The target, rows, training-window rule, in-fold standardisation and penalty choice, development period, comparators (PERS-BIN, PERS-PROB) and gate are **identical to Addendum A (Y8)**.

| Candidate | Definition |
|---|---|
| **LOGW** | An L2 logistic model on the condition. Features: xF = F3 − 6.25 and xG = G3 − 0.48 (the persistence part), plus 6- and 12-month log changes, at m0, of rice Thai 5%, crude oil and urea. |
| **LOGW2** | LOGW plus the 6- and 12-month log changes of maize, wheat HRW and palm oil. |

The penalty is chosen on the last 25% of training rows from {0.01, 0.03, 0.1, 0.3, 1, 3}.

## Confirmation (only if a candidate passes the gate)

The gate-passing candidate with the lowest development Brier is used, as follows:

- **Fit:** on the Region IV-A rows known at O(t).
- **Transfer:** it is applied to each province's F3 and G3 with that province's thresholds. It replaces P0_price on the official 65 Lead-2 rows and is multiplied by π_H4.
- **Scoring:** R1–R7 are applied unchanged.

This needs a Pink Sheet vintage that covers months up to 2026-02. If the vintage in hand does not cover them, the newer vintage is fetched and its hash is recorded.

The result is labelled as in Phase-2 section 5.
