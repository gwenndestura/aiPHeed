# Addendum 1: attainable-accuracy diagnosis and one noise-targeted correction

**When frozen:** after the protocol's scoring of FIL (§4), the Stage-2 models (§5) and the long-history arm (§7), and before anything below was run. The SHA-256 is in `runner/ADDENDUM_1_SHA256.txt`.

**Status of results:** everything below is post hoc, decided after seeing the protocol results. It does not change the protocol's verdict, criteria or label.

## What the frozen protocol showed

| Model | Lead 1 ELEVATED accuracy | Persistence on the same rows |
|---|---|---|
| FIL (2021+ only) | 0.32 | 0.61 |
| FIL-LONG, untouched 2003–2020 (280 rows, 70 quarters) | 0.50 | 0.53 |

At Leads 2–4 every learned model stays within 0.50–0.58.

On level error (MAE), FIL-LONG beats persistence at Leads 1–2 on the untouched set, but MA2 is lower still.

An optimistic upper bound for an oracle that knows the true hunger level is 0.79–0.81. This bound takes the observed |H − REF| as if it were the true gap, which inflates it.

**Hypothesis:** the ELEVATED label is dominated by SWS sampling noise and unpredictable true changes, so no forecaster can reach 75% on it. The main correctable weakness in FIL is that it anchors on one noisy reading.

## A1.1 Attainable-accuracy simulation (diagnostic; no model selection)

**Model of the data.** Each area's series is simulated as a true quarterly level plus survey noise.
- **Noise variance:** R = (6/1.96)², the ±6 area margin assumed for every area before 2021.
- **Level innovation variance Q:** estimated per area from the 1998–2020 data by moments: Q = mean(ΔH²) − 2R, floored at 0.25, over consecutive quarters.

**Two level processes**
- (i) **Random walk.** E110–E113 found persistence near-optimal, so this is the main case.
- (ii) **Mean-reverting AR(1)**, with φ estimated by regressing ΔH on the lagged level minus the area mean, over consecutive pre-2021 quarters.

**The Bayes rule.** At true horizon h = k + 1 (Lead k), the rule predicts ELEVATED when the expected target minus the expected REF is greater than 0.
- Expectations come from the Kalman-filtered level at the newest observation.
- Future quarters inside REF take their expected values.

**Run:** 2,000 series × 100 quarters per area, seed 2026.

**Reported:** Bayes accuracy at Leads 1–4, alongside the 75% target.

**Interpretation, fixed in advance:** if the Bayes accuracy is below 0.75, the 75% target is unattainable for this label with this survey design, whatever the model.

## A1.2 FIL-LONG-S: noise-reduced anchors (one correction)

**Change from FIL-LONG.** Only the feature set changes. Four columns are added, each computed from data known at the issue date:

| Column | Definition |
|---|---|
| `ma2_anom` | MA2 − REF̂ |
| `ma4_anom` | Mean of the four newest known quarters − REF̂ |
| `kf_anom` | Local-level Kalman filtered level − REF̂ |
| `kf_level` | The Kalman filtered level itself |

**Kalman filter settings**
- Known per-round R from the margins.
- Q estimated from the training origin's known readings (pooled over the four areas, by moments, floored at 0.25).

**Unchanged:** the label, the target z, the grid and every rule.

**Scoring sets**
- (a) 2003–2020. This set has been used once already, for FIL-LONG, so it is **not untouched** for this variant.
- (b) 2021+.

**Reported:** the protocol §6 criteria and MAE against PERSIST and MA2 (paired cluster bootstrap).

**Sealing:** a FIL-LONG-S pass would be labelled exploratory. It is sealed with the others for prospective scoring.

**Nothing else is added.**
