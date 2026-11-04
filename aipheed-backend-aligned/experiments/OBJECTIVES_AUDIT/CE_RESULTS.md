# C-E results: C-b + employment (E1) + OFW remittances (E2)

Pre-registration `CE_PREREGISTRATION.md` (`bde69c08…f10f`). Runner `runner/ce_model.py`; outputs `out/ce_*`.

**Development evidence** (17th historical attempt).

## Pre-checks

- C-b refit reproduces 904 / 904 rows exactly.
- E2 unchanged when future remittance values are randomized.
- **Coverage:** E1 from 2006-Q3 (72% of origins); E2 from 2000-Q3 (93%).

## Results (62 quarters)

| | Accuracy | Balanced | F1 | AUC | Brier | Failed | 2015–20 third |
|---|---|---|---|---|---|---|---|
| C-b L1 | 0.790 | 0.717 | 0.857 | 0.702 | 0.187 | R7 | 0.571 |
| C-E L1 | 0.774 | 0.705 | 0.844 | 0.708 | 0.194 | R5, R7 | 0.571 |
| C-b L2 | 0.790 | 0.717 | 0.857 | 0.704 | 0.184 | R7 | 0.571 |
| C-E L2 | 0.774 | 0.705 | 0.844 | 0.725 | 0.187 | R7 | 0.571 |

**Against C-b:**
- Brier +0.006 (p 0.89) at Lead 1 and +0.004 (p 0.79) at Lead 2;
- 1 call changed per lead.

**Baselines:** 6 of 14 comparisons significant. **MRLT 2.**

**Gates:**

| G1 | G2 | G3 | G4 | G5 | Adoption |
|---|---|---|---|---|---|
| ✗ | ✗ | ✗ | ✓ | ✗ | **No** (slightly worse than C-b) |

## Do employment and remittances contribute?

| Input | Mean SHAP share | Forecasts where it is non-zero |
|---|---|---|
| E1 (unemployment change) | 4.3% | 37 of 62 |
| E2 (remittance decline) | 1.2% | 40 of 62 |

**Latest forecasts** (origin 2026-Q3, targets 2026-Q4 and 2027-Q1):
- **Market 52%, past hunger 48%;** climate, fisheries, employment and remittances **0%**.
- **Why:** the walk-forward model selection, which uses earlier quarters only, chose the simplest setting at the latest
  origins: depth 1 (one split per tree), 50 trees. Such a model uses only the two strongest inputs.
- Forcing deeper trees so that every group gets a share would mean choosing the model for its appearance, not its
  evidence. That is not done.

## Conclusion

- **Employment and OFW remittances can be put into the forecast with real data.** They then contribute in about 60%
  of past forecasts, but they make the forecast slightly worse.
- **C-b stays the main model** under the pre-registered rule.
- Serving C-E is a team and adviser decision, and the rule does not support it.
