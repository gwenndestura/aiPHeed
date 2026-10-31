# E130 model comparison

## Quarterly provincial task: not run

The five-model comparison (protocol §5) needs a valid quarterly provincial target. The gate found none.

| Model | Role | Comparison status |
|---|---|---|
| M1 LightGBM regression | Proposed | Not trained (gate BLOCKED) |
| M2 Persistence | Baseline: own-province latest reference value | Not evaluable |
| M3 PSA-only | Baseline: ridge on official statistics, CPI included | Not evaluable |
| M4 NLP-only | Baseline: ridge on news and NLP features | Not evaluable |
| M5 Linear | Baseline: ridge on all features (continuous counterpart of logistic regression) | Not evaluable |

**"LightGBM beats every baseline" is therefore not established**, for MAE, RMSE, within-tolerance share and classification alike. `E130_BASELINE_COMPARISON.csv` lists every pair as not evaluable, with 0 identical rows.

## Survey-year provincial task: sealed, not yet scored

| Forecaster | Rule | Learned? |
|---|---|---|
| S1 persistence | 2023 value | No |
| S2 two-round mean | (2021 + 2023) / 2 | No |
| S3 EB-shrunk 2023 | 2023 value shrunk toward the 2023 cross-province mean, weight τ² / (τ² + SE²) | Weights from the 2023 cross-section only |
| LightGBM, PSA-only, NLP-only, linear | — | **Not fitted:** 5 training rows < 20 |

- All five provinces are scored on identical rows when the owner supplies the PSA 2025 table (`runner/score_e130.py`).
- Five rows in one fold: descriptive only.

## Most recent comparison evidence on record (not re-run)

E128, on the 20-quarter **regional** SWS target:
- LightGBM beat no baseline;
- persistence was best on the saturated 11.3 % class target;
- no model was reliable at any lead.

That is regional evidence and says nothing directly about provinces.
