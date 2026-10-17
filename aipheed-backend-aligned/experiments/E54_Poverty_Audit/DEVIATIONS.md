# E54 deviations from the frozen PROTOCOL.md

None of the deviations below changes a label, row, poverty value, encoding, arm, grid, selection rule or decision rule.

| ID | What | Effect |
|---|---|---|
| D-1 | C2 lists **B-clim** among the comparators. It is in E44's `COMPARATORS` and is present on the S44/EXT rows, but section 3 did not name it. | Reported only. It is not part of any E54 decision, which compares every arm with R. |
| D-2 | The C3 repeat was started a second time on its own (`runs/c3_20261017T150746Z`). The first parallel launch failed in the shell before Python started, and no run directory was written. | None. The repeat's `predictions.csv` is byte-identical to run 1's. |
| D-3 | `tests/test_decisions_recomputed_from_rows` compares the paired-Brier values recomputed from the CSV rows with those stored in `results.json` within 1e-12, not exactly. The differences are about 3e-18, from CSV round-off, the same issue as E53 D-2. | Test only. |
