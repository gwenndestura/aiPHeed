# Y18 fix report: Y16 prospective record-keeping repaired before the first issue

**Scope.** The fixes X1–X7 from `RECOMMENDED_FIXES.md`, plus the evaluation items (F6, F10, F11, F12, F14, F16–F18) that can be implemented without changing the registered primary analysis.

**Unchanged:**

- the model specification;
- forecast values (parity < 1e-4 with Y15);
- target, horizon, threshold, schedule;
- the registered primary test;
- the seven rules.

## 1. Preconditions recorded before editing

`out/y18_before.json` (taken 2026-10-29 UTC) records:

- git HEAD `0da2f7a`, branch `aiPHeed/system-fixes`;
- the `git status`;
- tracked-diff SHA-256 `ce2c6d05…` (11 modified files, per-file hashes);
- the 6 untracked backend test files;
- hashes of all Y14/Y15 files (51), the shared model files, all Y16 files (11) and all Y17 files.

The plan hash was verified: `208b5754…6bd9699`.

## 2. Statistical amendment (frozen before any evaluator change)

`y16_kalman_prospective/BOOTSTRAP_AMENDMENT.md`:

- SHA-256 **`d8e855fa44ad67289a4aaff65a443d49c07141c042de25d6f2fc4a0946883649`**;
- frozen **2026-10-29T23:18:31Z** (`BOOTSTRAP_AMENDMENT_SHA256.txt`, `BOOTSTRAP_AMENDMENT_FROZEN_AT.txt`);
- byte-identical copy and hash file in `y17_integrity_audit/`.

**Frozen before any outcome existed.** No valid seal exists, and the first target (2027-Q2) resolves on 2027-10-28 at the earliest. The evaluator was changed only afterwards, and it enforces this hash.

**Content:**

- the registered primary analysis is unchanged;
- a moving-block bootstrap sensitivity analysis is added, fully specified: L = 4, non-circular, B = 5000, seed 2036, percentile CI, n ≥ 8;
- it is reported next to the primary result;
- it **can never turn a failed primary result into a pass**; a primary pass is reported as "not robust" if the block test fails;
- calibration, missed issues and overlay verification are defined as supplementary registered reporting items;
- procedural safeguards: primary lock, refused re-issues, clock source, attestation status.

## 3. Fixes implemented, each demonstrated by passing regression tests (`REGRESSION_TESTS.md`)

| Fix | Status | What changed (file / function) |
|---|---|---|
| **X1** explicit errors | **Done** | No `assert` remains in `runner/*.py` (AST-checked). Named exceptions: `IntegrityError`, `OverlayError` (a `ValueError`), `IssueWindowError`, `ReissueError`; `ValueError` for issue dates. Covers `plan_sha` and the new `amendment_sha`, `origin_of` (strict ISO, quarter start), `read_overlay`, `load_seals`, `issue_seal`, `evaluate`. Verified under `python -O`. |
| **X2** strict overlay | **Done** | `read_overlay`: exact header; no blanks or surrounding whitespace; area set; `YYYY-Qn`; finite H in [0, 100]; MoE in (0, 15]; `published` ISO date only, a real date, ≥ quarter start, ≤ entry date; `entered_utc` `YYYY-MM-DDTHH:MM:SSZ`; `https://` URL. Errors name the row (and file line) and field. **No ambiguous date is ever interpreted.** The cutoff is applied per issue: rows on or after the issue date are excluded and listed in the seal. |
| **X3** duplicates and conflicts | **Done** | Inside the overlay, exact duplicates, conflicting values, and the same value with a different date are rejected. Against the project series, a different value under the same key, or the same value under another date, is rejected. An exact duplicate is ignored and reported. A legitimate additional round is accepted under the frozen rule (the quarter mean of all rounds) and reported in the seal (`overlayReport`). On failure nothing is installed. |
| **X4** provenance in the seal | **Done** | The seal records: `overlayRowsUsed` (all fields, URLs), `overlaySnapshotSha256` (canonical JSON), `overlayRowsExcludedByCutoff`, `overlayReport` (includes the overlay file SHA-256), the input file hashes (kept), plan and amendment hashes, `modelVersion` (+ `evaluate.py`, `attest.py`), `environment` (Python, numpy, scipy, pandas, sklearn, OS name, optimise flag), `clockSource`. Seals are never rewritten, and later overlay additions do not affect them. |
| **X5** registry reconciliation | **Done** | `reconcile()` reports missing files, unregistered files, hash mismatches, malformed and duplicate registry lines, and re-issues. `load_seals` stops on any inconsistency. `issue_seal` refuses to issue into an inconsistent registry and refuses re-issues. Nothing is ever recreated. **Stated limit:** someone who rewrites seal and registry consistently is not detectable locally; only the external attestation protects against that. |
| **X6** attestation (local part) | **Done** | `issue_with_log` writes `attestations/<seal>.attestation.txt` (a one-line payload with issue, target, seal SHA-256, plan and amendment hashes, write time) and appends `status: pending` to `ATTESTATIONS.log`. `runner/attest.py` records `completed` or `unavailable`, with method and evidence required; `pending` is never set by hand and never inferred. Evaluation reports the status. **Nothing is transmitted:** no networking module is imported. The manual same-day procedure is in `attest.py` and `RUNBOOK_Y18_ADDENDUM.md`. |
| **X7** attempt log | **Done** | `issue_with_log` (used by `issue.py` for real issues) appends every attempt to `ISSUE_ATTEMPTS.log` as JSON lines: UTC time, requested date, result `failed` or `sealed`, error type and message, versions. No credentials, user name or host name. The original exception is re-raised unchanged; a logging failure is attached as a note and never masks it. A non-canonical overlay for a real issue is refused and logged. Dry runs are separate and never logged as attempts. A failure creates no seal and never enters evaluation. |
| F6 primary lock | **Done** | `lock_primary`: `out/PRIMARY_ANALYSIS.json` is created once (exclusive). An identical rerun is accepted; a differing rerun raises and nothing is overwritten. |
| F10 calibration | **Done (supplementary)** | `calibration()`: 5 equal-count bins; logistic slope and intercept if n ≥ 10 and both classes, else "unavailable". Labelled supplementary. |
| F11 missed issues | **Done (supplementary)** | `missed_issues()`: scheduled dates from 2027-01-01 whose window has closed without a valid seal. Failed attempts are listed next to them. |
| F12 overlay verification | **Done** | `verify_overlay()`: every row used by a valid seal must still exist unchanged, or the evaluation stops |
| F14 serial dependence | **Done via Amendment 1** | `block_paired()`, reported as `sensitivity_blockBootstrap` with `reportedVerdict`. The primary is unchanged. |
| F16 versions | **Done** | `environment` in seals and attempt logs |
| F17 overlay path | **Done** | `issue.py` refuses non-default overlays for real issues |
| F18 Manila date | **Done** | `evaluate.main` uses the Manila date |

## 4. Not resolved, and why

| Item | Why it remains |
|---|---|
| **F8c / F9: consistent local rewrite** | Not solvable by local code. Mitigated by the same-day external attestation, which needs the researcher to choose a recipient or service. Its status is `pending` until recorded, and nothing was sent. |
| **F13: claimed publication dates** | Format, consistency and plausibility are now enforced, and each used row's source URL is sealed for later audit. Whether a date is *true* still requires a human to check it against the SWS release. |
| Library `now_utc` parameter | Kept for tests. Seals made with it are marked `caller-supplied` and refused by the real evaluation. |
| F15, F19 (design limitations: low power; R1 unreachable before about 2037; commissioned-round convention) | Preregistered. Changing them would break the preregistration. |
| Original Y17 adversarial file | Left unchanged as evidence. It now shows 16 XPASS(strict) (fixed), 8 failures (fixtures now invalid or new exception types) and 4 XFAIL (now refused by the new protections). Every case is explained in `REGRESSION_TESTS.md` section 3. |

## 5. Exact changed-file list

All paths are under `LEAD2_RELIABILITY_RESEARCH/`.

| File | Change |
|---|---|
| `y16_kalman_prospective/runner/kprospect.py` | modified (X1–X7, F6, F10–F12, F14, F16) |
| `y16_kalman_prospective/runner/issue.py` | modified (X7 logging, F17, attestation output) |
| `y16_kalman_prospective/runner/evaluate.py` | modified (Amendment 1 support, integrity stops, supplementary items, primary lock, F18) |
| `y16_kalman_prospective/runner/attest.py` | **new** (X6) |
| `y16_kalman_prospective/tests/test_y16.py` | modified (fixtures and exception types; see `REGRESSION_TESTS.md` section 1) |
| `y16_kalman_prospective/BOOTSTRAP_AMENDMENT.md`, `BOOTSTRAP_AMENDMENT_SHA256.txt`, `BOOTSTRAP_AMENDMENT_FROZEN_AT.txt` | **new** (frozen amendment) |
| `y16_kalman_prospective/RUNBOOK_Y18_ADDENDUM.md` | **new** (operator steps) |
| `y17_integrity_audit/FIX_REPORT.md`, `REGRESSION_TESTS.md`, `BOOTSTRAP_AMENDMENT.md`, `BOOTSTRAP_AMENDMENT_SHA256.txt` | **new** |
| `y17_integrity_audit/tests/test_regression_y18.py` | **new** |
| `y17_integrity_audit/out/y18_before.json`, `y18_after_comparison.json`, `y18_adversarial_rerun.txt`, `y18_adversarial_reasons.txt`, `y18_adversarial_fixture_failures.txt` | **new** (evidence) |

**Not changed:**

- `EXPERIMENT_PLAN.md`, `PLAN_SHA256.txt`, `PLAN_FROZEN_AT.txt`, `AUDIT_AND_RUNBOOK.md`;
- `data/sws_rounds_overlay.csv` (header only);
- the `dry_runs/` files;
- the Y17 `AUDIT_PLAN.md`, `FINDINGS.md`, `TEST_RESULTS.md`, `RECOMMENDED_FIXES.md` and `test_adversarial.py`;
- all of Y14, Y15, `common/` and `runner/rlib.py`.

## 6. Before / after integrity comparison (`out/y18_after_comparison.json`)

| Check | Result |
|---|---|
| HEAD / branch | `0da2f7a` / `aiPHeed/system-fixes`, unchanged |
| `git status --short` | identical |
| Tracked diff SHA-256 and per-file hashes (11 user-modified files) | identical |
| Untracked backend test files (6) | identical |
| `backend/data` | no diff |
| Y14 and Y15 files (51) | identical |
| Shared model code (`hmodels.py`, `p2lib.py`, `cov.py`, `rlib.py`) | identical |
| Y16 plan, plan hash, freeze time, runbook, overlay, dry-run files | identical |
| Y17 pre-existing files | identical |
| `prospective/` | **empty**: no seal, no attempt log, no attestation |
| Real overlay | header only |
| `__pycache__` in the research tree | none |
