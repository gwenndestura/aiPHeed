# Y17 audit plan: adversarial integrity audit of Y16

**Scope.** `y16_kalman_prospective/`: `EXPERIMENT_PLAN.md` (sha `208b5754…`), `runner/kprospect.py`, `runner/issue.py`, `runner/evaluate.py`, `tests/test_y16.py`, `data/sws_rounds_overlay.csv`. Also the model code it imports read-only: `common/hmodels.py` (`kalman`, `_series`, `_filter`, `_kfit`) and `runner/rlib.py` (`rounds`, `known`, `forecast`, `pairs`, `issue`, `observed`).

**Rules for the audit:**

- Nothing in Y16, Y14, Y15, shared code or protected data is modified.
- No real seal is issued. Every write goes to a pytest temporary directory or to `y17_integrity_audit/out/`.
- The real overlay is only read.
- No model is fitted for selection. No historical comparison is run beyond calls already made by Y16's own parity test.

## Method

| Audit | What | How |
|---|---|---|
| A Preregistration | hash match; freeze before code; enforcement; plan ↔ code agreement (target, 0.50, horizon, schedule, superiority rule, one-time primary analysis) | Independent SHA-256; file timestamps; reading the code; tests with a modified plan in a temporary copy, including under `python -O` |
| B Timing | issue → origin → target mapping; Manila window boundaries; invalid dates through the CLI; backfilling; strict "published < O(t)"; date parsing and timezones | Unit tests at the second-level boundaries; subprocess CLI calls; synthetic overlays with ambiguous, tz-aware and future dates |
| C Parity and leakage | same functions and specification as Y14/Y15; conventions; future rounds ignored; earlier rounds used; determinism; same origin and target for both models | Code reading; tests with synthetic overlays; repeated calls |
| D Overlay and provenance | required fields; value ranges; impossible dates; duplicates and conflicts; provenance in the seal; input hashes; tamper resistance of seals and the registry | Synthetic overlays in temporary directories; seal and registry manipulation in temporary directories |
| E Evaluation | resolution rule; missing outcomes, missed issues and missing forecasts; pairing; metric and test arithmetic; direction of d and the CI; bootstrap dependence; one-time primary analysis; small-sample handling; disappearance of failures | Synthetic seals and outcomes in temporary directories; hand-computed expectations |
| F Reproduction | Y16's 19 tests plus the Y17 adversarial tests | pytest with `-p no:cacheprovider` and no bytecode |

**Classification of each finding:**

- confirmed defect, potential risk, or design limitation;
- severity: critical, high, medium, low or informational;
- whether a fix is required before the first valid issue (2027-01-01).

**How defects are tested.** A test for a confirmed defect asserts the *correct* behaviour and is marked `xfail(strict=True)`. It fails today, as evidence of the defect. Once the defect is fixed it will XPASS, and the strict marker makes the suite flag it for review.
