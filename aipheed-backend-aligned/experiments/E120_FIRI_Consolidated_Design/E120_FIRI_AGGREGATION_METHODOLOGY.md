# E120 FIRI aggregation methodology (Level 2 → Level 3)

**Code.** `runner/e120.py` `firi()`. Output: `out/level3_firi_equal.csv`.

## 1. Formula

**FIRI(u, t)** = Σ w_i · S_i(u, t) / Σ w_i over the indicators i available for unit u at origin t, with **w_i = 1** (equal weights; see `E120_WEIGHTING_ANALYSIS.md`).

- **Provincial FIRI:** the six indicators, each from provincial observations only.
- **Regional FIRI:** five indicators (no PSV), from Region IV-A, CALABARZON or national series.

**Interpretation.** Every indicator score is either:
- a percentile against the indicator's own 2021+ history, where 0.5 = the usual level; or
- a cross-province mid-rank, where 0.5 = the middle province.

So **FIRI 0.5 means "risk evidence at its usual level"**. Values above 0.5 mean more pressure than usual, or worse placement among the provinces. FIRI is a relative index, **not a probability** of food insecurity.

**Decomposition.** Because 0.5 is every indicator's middle, FIRI − 0.5 = Σ w̃_i (S_i − 0.5). Each indicator's push up or down is reported, the same explanation property as FIRI v2.

## 2. Completeness and unavailable indicators

**Minimum completeness.** At least ⌈2/3 × the number of defined indicators⌉ must be available:
- provincial: 4 of 6;
- regional: 4 of 5.

Otherwise the FIRI is `not computable`: shown as unavailable, never imputed.

**Missing indicators** are left out, and the weights are renormalized over the available ones. **The number and names of the missing indicators travel with the score.**

**Result:**

| Scope | Computable | Rows by number of indicators |
|---|---|---|
| Provincial | 75 of 115 province-quarters (65%) | 4 indicators: 54; 5: 13; 6: 8 |
| Regional | 10 of 23 quarters (from 2024-Q2) | — |

The early quarters are not computable for three reasons:
- year-on-year changes need a 2021+ base;
- percentiles need 8 earlier values;
- the regional series is a single unit.

## 3. Confidence information (reported with every score)

1. **Completeness:** indicators available / defined, with the list of missing ones.
2. **Chance band.** If each available indicator sat at a random usual level, the mean of k scores would vary with SD = √(1/12)/√k. That is 0.144 for k = 4 and 0.118 for k = 6. A score inside 0.5 ± 1 SD cannot be told apart from usual.
3. **Verification share:** the share of contributing features whose release date is verified rather than rule-based. Currently mainly cyclones, FSSI, GDELT, poverty and SWS dates.
4. **Leave-one-indicator-out range:** how far the score moves without each indicator (`out/sensitivity.csv`).

## 4. Risk classification

**The current FIRI v2 rule** is HIGH at ≥ 0.50.
- Under percentile scoring, 0.50 is the historical middle *by construction*. HIGH therefore means only "above the usual level".
- In the served history, 81% of province rows were HIGH. That was driven by the H domain (regional hunger, the same for all provinces) and SWS-derived weights.

**The 0.50 line is not validated against any provincial outcome** (none exists). It is not defensible as a "high food insecurity" threshold.

**Recommended bands.** Statistical, not outcome-tuned:

| Band | Rule (k = available indicators) | Meaning |
|---|---|---|
| Usual or below | FIRI < 0.5 | Evidence at or below its 2021+ usual level |
| Above usual | 0.5 ≤ FIRI < 0.5 + SD_k | Above the middle, but within chance variation |
| Elevated | 0.5 + SD_k ≤ FIRI < 0.5 + 1.645·SD_k | Beyond one chance SD |
| High | FIRI ≥ 0.5 + 1.645·SD_k | Beyond what 95% of chance combinations reach (one-sided) |

**Offline result** (`out/summary.json`):

| Band | Provincial (75 computable) | Regional (10 computable) |
|---|---|---|
| Usual or below | 42 | 6 |
| Above usual | 30 | 4 |
| Elevated | 2 | 0 |
| High | 1 | 0 |

**The bands are meant to be rare.** "High" requires several indicators to be well above usual *at the same time*. The bands were derived from the chance distribution before looking at the classification counts, and no threshold was searched.

**Validated thresholds need an outcome.** Use regional SWS for the regional FIRI, or CBMS / FNRI FIES at province level when obtained. That comparison must be pre-registered and must not feed back into the weights.
