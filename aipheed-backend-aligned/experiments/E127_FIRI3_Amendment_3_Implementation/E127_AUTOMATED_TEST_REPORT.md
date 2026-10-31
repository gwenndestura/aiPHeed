# E127 automated test report

**Full backend suite.** Run from `backend/` with `python -m pytest tests -q`, after the implementation commit `abac0c8`:

| Result | Count |
|---|---|
| Passed | **1183** |
| Failed | **0** |
| Skipped | **18** (the long-standing "E34 superseded" tests; **not counted as passed**) |

**Baseline at E126:** 1172 passed, 0 failed, 18 skipped. E127 adds 11 tests and updates 3 earlier ones (see `E127_REGRESSION_TEST_REPORT.md`).

**Note.** A first attempt to run the suite in the background reported "no tests ran" (nothing was collected), so it was **not** counted. The suite was rerun in the foreground; the counts above are from that run.

## Restrictions checked by the suite

| Restriction | Check |
|---|---|
| FIRI v2 unchanged | `firi.py` hash and score regression |
| Real store and registry unchanged | No forecast; one blocked event; next id `FIRI3-1.3-2026-Q4` |
| v1.2 records intact | E124 configuration, E126 proposal hash, E121–E126 outputs (read only) |
