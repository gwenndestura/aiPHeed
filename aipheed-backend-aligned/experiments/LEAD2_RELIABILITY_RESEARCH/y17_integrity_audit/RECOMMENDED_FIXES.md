# Y17 recommended fixes (proposals only; nothing has been changed)

Every fix below is confined to `y16_kalman_prospective/runner/` (plus a separately hashed amendment file).

**None of them changes:**

- the target, horizon or threshold;
- the model specification;
- the statistical tests, or the seven rules.

The frozen `EXPERIMENT_PLAN.md` and its hash stay as they are.

**Procedure after the fixes:**

1. Rerun the Y16 tests and the Y17 tests. Each fixed defect's `xfail(strict=True)` test will XPASS. Remove the marker after review.
2. Record the new code hashes. Seals already record `modelVersion`.

## Must do before the first valid issue (2027-01-01)

| Fix | Findings | Smallest change |
|---|---|---|
| **X1** | F1 | Replace each integrity `assert` with an explicit `raise` (`ValueError` / `RuntimeError`) in `plan_sha`, `origin_of`, `read_overlay`, `load_seals` and `evaluate`. At the start of `issue.py` and `evaluate.py`, refuse to run when `sys.flags.optimize > 0`. |
| **X2** | F2, F3 | In `read_overlay`, validate every row, and reject the whole file on any failure, with the row number: <br>• `area` ∈ {NCR, BL, VIS, MIN}; <br>• `quarter` matches `^\d{4}-Q[1-4]$`; <br>• 0 ≤ H ≤ 100; <br>• 0 < MoE ≤ 15; <br>• `published` matches `^\d{4}-\d{2}-\d{2}$` (ISO date only, no time or timezone), is a real date, is ≥ the first day of the quarter and ≤ the entry date; <br>• `source_url` starts with `https://`; <br>• `entered_utc` is ISO-8601 with `Z`. |
| **X3** | F4, F5 | In `install_overlay`: <br>• reject duplicate (area, quarter, published) rows inside the overlay; <br>• reject a row whose (area, quarter, published) matches a project round with a different H; <br>• return a list of rows that add a further round to an existing quarter, so it can be written to the seal. |
| **X4** | F7, F5b | In `issue_seal`, write into the seal the full overlay rows **actually used** (published < O(t)), with their source URLs and entry times, plus any "added round to an existing quarter" notes. Keep the overlay hash. |
| **X5** | F8 | In `load_seals`: <br>• fail if any registry line has no file, if any seal file has no registry line, or if a hash mismatches (explicit `raise`); <br>• return **all** valid seals per issue date. `evaluate` must report re-issues (`reissued: {issue: [files]}`) and use the first by write time, as registered. |
| **X6** | F9 | **Procedure, not code.** On the issue day, send the seal's SHA-256 (from `SEALS.txt`) to a party outside the machine, and record the receipt in `prospective/ANCHORS.txt`. Options: an email to the thesis adviser or committee, an OSF/AsPredicted timestamped note, or a public RFC 3161 timestamping service. Choosing among these is a user decision. Optionally, make `issue.py` refuse a `now_utc` override (library-only path) for non-dry runs. |
| **X7** | F11 (failure log) | Wrap `issue.py` so that any exception during a non-dry issuance appends a line (issue date, UTC time, exception) to `prospective/ISSUE_FAILURES.txt` before re-raising |
| X8 | F16, F17 | Record `sys.version` and the numpy, scipy and pandas versions in the seal. Refuse non-dry issues when `--overlay` is not the default overlay path. |

## Before the first evaluation run (first outcome resolves about 2027-10-28)

| Fix | Findings | Smallest change |
|---|---|---|
| X9 | F11 | `evaluate`: enumerate the registered schedule from 2027-01-01 to today. Report `missedIssues` (no valid seal) and `issueFailures` (from X7). |
| X10 | F12 | `evaluate`: for each seal, compare the overlay rows recorded in the seal (X4) with the current overlay. Any changed or removed row means an integrity failure, and the evaluation stops. |
| X11 | F6 | `evaluate`: when ≥ 20 quarters resolve, write `out/PRIMARY_ANALYSIS.json` with `open(..., "x")`, including the target list and an input hash. Later runs must recompute and **refuse** if the result differs, or else report only "primary already locked". |
| X12 | F10 | `evaluate`: add calibration (5 equal-count bins; logistic calibration slope when n ≥ 10 and both classes; otherwise `"unavailable"`) to the descriptive and primary outputs |
| X13 | F14 | **Formal amendment**, separately hashed **before any outcome is seen**: add a moving-block bootstrap (block 4 quarters) of the paired Brier difference as a **reported sensitivity**. The registered primary test is unchanged. |

## Not recommended

- Changing the model, the threshold, the target or the primary test.
- Adding further challengers.
- Altering the commissioned-round convention (F19). Any of these would break the preregistration.
