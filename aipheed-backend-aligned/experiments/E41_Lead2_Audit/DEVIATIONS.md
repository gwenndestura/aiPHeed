# E41 deviations

## D-1 (2026-10-15, before any result was produced)

The first two invocations of `runner/e41_evaluate.py` crashed in `e40_dev` with "Input contains NaN". No metric was computed or printed, `results.json` was never written, and the two empty run folders (`runs/20261015T100324Z`, `runs/20261015T100645Z`) were removed.

**Cause:** at the earliest E40 development origin (O = 2022-10-01) only four approved SWS quarters were posted, i.e. three changes. PROTOCOL 4.4 requires at least four changes, so the simulation correctly issued no forecast, but the scoring code passed the missing value to the metrics.

**Fix:** E40-label rows without a simulation forecast are withheld from all three arms (common rows), and the withheld targets are reported (`withheld_rows`, `withheld_targets`). This implements the protocol's "otherwise no forecast"; no method, threshold or setting changed.
