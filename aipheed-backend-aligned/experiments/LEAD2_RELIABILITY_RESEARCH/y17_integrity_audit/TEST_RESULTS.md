# Y17 test results

All runs used `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. Every write went to pytest temporary directories (`%TEMP%\pytest-of-User\…`) or to `y17_integrity_audit/out/`.

## 1. Existing Y16 suite (unchanged)

```
cd y16_kalman_prospective
python -m pytest -q tests -p no:cacheprovider
19 passed in 24.55s
```

Afterwards, `prospective/` was still empty, the real overlay still header-only, and `dry_runs/SEALS.txt` still had one line.

## 2. Y17 adversarial suite

```
cd y17_integrity_audit
python -m pytest -q tests -p no:cacheprovider -rxX
36 passed, 20 xfailed in 73.18s
```

**How to read it:**

- A **pass** is sound behaviour (OK1–OK15 in `FINDINGS.md`) or a documented risk shown as present (`test_B5`, `test_D7`).
- An **xfail** asserts the *correct* behaviour and fails today. It is evidence of a confirmed defect.

Rerunning the 20 xfail tests with `--runxfail` (`out/runxfail_detail.txt`) confirmed that each fails **on its own assertion**, not on an unrelated error.

| Test | Result | Finding | Failure message (with xfail disabled) |
|---|---|---|---|
| A1 plan hash matches | pass | OK1 | – |
| A2 frozen before code (file times) | pass | OK1 | – |
| A3 changed plan rejected | pass | OK2 | – |
| A4 plan check under `python -O` | xfail | F1 | `a changed plan was accepted under python -O` (exit code 0) |
| A5 superiority rule = plan | pass | OK3 | – |
| A6 primary analysis locked | xfail | F6 | no lock in `evaluate.py` |
| B1 mapping derived, 2027–2032 (6 cases) | pass | OK4 | – |
| B2 Manila window boundaries (4 cases) | pass | OK5 | – |
| B3 invalid CLI dates (4 cases) | pass | OK6 | – |
| B4 invalid date under `python -O` | xfail | F1 | `origin_of('2027-01-02')` exit code 0 |
| B5 backdated `now_utc` through the library | pass (risk shown) | F9 | – |
| B6 on- or after-issue rounds excluded (3 cases) | pass | OK7 | – |
| B7 non-ISO date rejected | xfail | F3 | `DID NOT RAISE` (`01/12/2027` → 2027-01-12) |
| B8 tz-aware date does not leak | pass | OK7 / F3 | It fails closed with `TypeError: Cannot compare tz-naive and tz-aware timestamps`, which blocks issuance |
| C1 same functions as Y14/Y15 | pass | OK8 | – |
| C2 shared origin, target, cutoff | pass | OK7 | – |
| C3 persistence = newest reading; 11.3 edge | pass | OK9 | – |
| C4 duplicate overlay rows not double-counted | xfail | F4 | `0.9953936873834263 == 0.9983564333934437` |
| C5 deterministic across processes | pass | OK8 | – |
| D1 invalid overlay rows rejected (8 cases) | xfail | F2 | `DID NOT RAISE` (all 8) |
| D2 bad area / missing date rejected | pass | partial OK | – |
| D3 conflict with project round reported | xfail | F5 | `DID NOT RAISE` |
| D4 exact project duplicate ignored | pass | OK11 | – |
| D5 seal keeps overlay provenance | xfail | F7 | source URL absent from the seal |
| D6 input hashes cover data, overlay, code | pass | OK12 | – |
| D7 seal and registry edited together | pass (risk shown) | F8c / F9 | – |
| D8 deleted registered seal detected | xfail | F8 | `DID NOT RAISE` |
| D9 re-issue reported | xfail | F8 | evaluation shows `validSeals: 1` after two valid seals |
| E1 120-day resolution; missing → NaN | pass | OK14 | – |
| E2 paired difference, CI, sign test by hand | pass | OK13 | – |
| E3 small-sample statistics unavailable | pass | OK13 | – |
| E4 calibration reported | xfail | F10 | not present in the code |
| E5 missed issue counted | xfail | F11 | `2027-01-01` absent from the evaluation output |
| E6 edited overlay row detected | xfail | F12 | `DID NOT RAISE` |
| E7 seven rules on 20 synthetic rows | pass | OK13 | – |
| E8 primary on the first 20, descriptive below | pass | OK3 | – |

## 3. Files written by this audit

Only these, under `y17_integrity_audit/`:

- `AUDIT_PLAN.md`
- `FINDINGS.md`
- `RECOMMENDED_FIXES.md`
- `TEST_RESULTS.md`
- `tests/test_adversarial.py`
- `out/runxfail_detail.txt`

Two scratch overlays used for the timezone and ambiguous-date checks were created in the session scratchpad and deleted.
