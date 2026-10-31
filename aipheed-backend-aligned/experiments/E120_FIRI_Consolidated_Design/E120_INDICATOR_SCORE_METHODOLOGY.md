# E120 indicator score methodology (Level 1 → Level 2)

**Code.** `runner/e120.py`: `level1`, `asof_dynamic`, `asof_rank5`, `indicator_scores`. Outputs:
- `out/level1_feature_scores.csv`: one row per feature × unit × origin, with value, observed period, status and score;
- `out/level2_indicator_scores.csv`.

## 1. As-of value (every feature)

**Issue date.** For origin quarter t, the issue date is O(t) = the first day of t+1.

**Dynamic features.** The value is the **latest observed quarter whose availability date is before O(t)**:
- availability rules are E119's, listed per feature in the dictionary;
- if that quarter is more than 3 quarters older than t, the feature is `stale`, not scored;
- all observations are from 2021 onward;
- every year-on-year change uses a 2021+ base, so changes start in 2022-Q1. PSA-published CPI YoY is the declared exception.

**Annual and structural features** (provincial unemployment, underemployment, poverty) take the **latest reference year published before O(t)**. The year is kept with the value. It is never spread into quarters or interpolated.

## 2. Direction (before normalization)

| Direction | Features | Transform |
|---|---|---|
| Higher = more risk | CPI food and headline YoY, rice price YoY, protein price YoY, heat anomaly, cyclone counts, unemployment and underemployment, unemployment change, poverty, FSSI, shortage-news share | x |
| Lower = more risk | All production YoY (palay, corn, vegetables, root crops, fisheries, chicken, livestock), remittances YoY | −x (scored as a drop) |
| Departure in either direction = more risk | Rainfall anomaly (drought or flood) | \|x\| |

After this step, a higher aligned value always means more risk.

## 3. Normalization

| Type | Method | Why |
|---|---|---|
| Dynamic (quarterly) | **Expanding-window mid-rank percentile**: s = (#{prior < x} + 0.5·#{prior = x}) / n. *prior* = the feature's earlier 2021+ observations available before the issue, pooled over the scope's units (5 provinces, or the one regional series). Needs n ≥ 8, else `insufficient_history`. | Unit-free, so % YoY, mm, °C and counts become comparable. Robust to small-base extremes (corn +749% is just "the highest so far"). Uses no future data. 0.5 = the usual level of 2021+. Pooling provinces keeps one scale, so provinces can be compared. |
| Annual / structural | **Mid-rank among the five provinces** for the latest published year: (rank − 0.5) / 5, giving 0.1, 0.3, 0.5, 0.7 or 0.9 | Too few years for a time percentile. Unlike min-max (FIRI v2's V1), no province is forced to 0 or 1 and the middle province sits at 0.5. |

**Not used:**
- **z-scores:** heavy tails, and too few observations to estimate a mean and SD reliably;
- **min-max:** extremes dominate it, and the bounds depend on the sample;
- **fixed anchors from 2021–22:** FIRI v1's choice, but the window is too short and stale.

## 4. Feature → component → indicator

| Step | Rule | Why |
|---|---|---|
| Component score | Mean of the available feature scores in the component | A component holds features of the *same kind* that complement each other (chicken, pork and tilapia: r 0.41, −0.03, 0.11 with each other). Averaging gives one "protein prices" reading, so the component counts once. |
| Indicator score | Mean of the available component scores | Each component (food inflation, rice, protein, cost of living) counts once. Measured near-duplicates were removed beforehand: bottom-30% CPI, retail rice, farmgate palay at province level, aquaculture, the 300 km cyclone count, rainfall total. |
| Availability | Scored only if at least half of its components (rounded up) are available | An indicator built from one of four components is not representative |
| Missing | Missing, stale or insufficient history is left out of the mean. Never 0, never filled. | The status is kept in Level 1 |

## 5. Why equal weights inside an indicator

**Data-driven weights are not identifiable inside an indicator:**
- no provincial outcome exists to learn them from;
- the regional outcome (SWS) would make the index target-derived;
- 9–100 rows per component are too few.

**Expert weights could be added later** through a documented elicitation of the 50 DA respondents (for example AHP), pre-registered.

**Equal weights at the component level are robust here.** Removing one feature changes its indicator score by:

| | Mean change | Largest |
|---|---|---|
| Provincial | 0.016–0.24 | PSV / EHS, which have only 1–2 features |
| Regional | 0.004–0.28 | — |

See `out/indicator_feature_removal.csv`.
- **Large changes** occur only where an indicator has one or two features: EHS employment, PSV poverty, FIS.
- **In multi-component indicators** the changes are small: FMA protein items 0.016–0.021; AFP palay and corn 0.033.
