# E51 deviations from PROTOCOL.md

## D-1: symmetric guard in E38's inner threshold rule (2026-10-17, before any E51 result existed)

**Why:** the first E51 run stopped with an error inside `e38_lib.threshold`; no metric was produced or seen. On a candidate target whose prior dates contain no HIGH row, the per-class mean of the HIGH rows is empty (NaN). The rule's maximisation then has no candidate and fails.

**Background:** E38's rule already returns 0.5 when there are fewer than 3 LOW rows. It had no HIGH-side guard because its own label never lacked HIGH rows.

**Change (in `runner/e51_compare.py` only; E38's code is untouched):** with fewer than 3 HIGH prior rows, return 0.5, the same as the LOW guard. Every case the original rule handles goes through the original function unchanged.

**Applies to:** every target, including EQ3-T. It cannot change EQ3-T's result unless its prior dates lacked HIGH rows, which they do not (49/55 HIGH).

The aborted run's partial output (one per-target rows file written before the error, never summarised or inspected) is kept unmodified in `runs/aborted_20261017T130911Z/`.
