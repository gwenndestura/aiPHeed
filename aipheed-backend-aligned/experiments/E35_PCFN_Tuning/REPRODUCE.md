# Reproducing E35

`PY` = `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe`. Run every step from `E35_PCFN_Tuning/`.

All reads go through the E32 data guard, re-pointed at E35. Writes outside E35 (and the OS temp directory) raise an error, and protected locations cannot be opened.

| # | Command | Expected |
|---|---|---|
| 1 | `PY -B runner/e35_preserve.py check` | `changed 0, missing 0, added 0` (97 files) |
| 2 | `PY -B runner/e35_verify.py` | 7 × PASS (rewrites `verification/VERIFICATION.json` with identical content) |
| 3 | `PY -B runner/e35_tune.py` | A new `runs/<stamp>/` whose 7 files are byte-identical to `runs/20261015T005446Z/` (`cmp`); prints `4a82209511478709 b911a85375a00667` and `verdict: NO IMPROVEMENT` |
| 4 | `PY -B -m pytest -c tests/pytest.ini tests` | 14 passed |
| 5 | in `../E32_New_Model`: `PY -B -m pytest -c tests/pytest.ini tests` | 16 passed |

**After step 3,** move the new run directory out of `runs/` (for example to `runs/repro_<stamp>`). `test_runs_are_byte_identical` compares the two named runs only.

**Do not re-run `runner/e35_freeze.py`.** The prospective record is frozen once, and the script refuses to overwrite it.
