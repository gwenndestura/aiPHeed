# Reproducing E26

**Interpreter:** `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe` (Python 3.13). Run every command from the E26 folder, with `-B`.

**Guard.** Every analysis script installs the E26 data guard (`runner/guard.py`):

- reads only the pinned E25 inputs, re-verifying each SHA-256;
- writes only inside E26;
- no subprocess, no sqlite.

**Frozen rules.** Each run first checks every hash in `runner/PROTOCOL_SHA256.txt`, and stops if a protocol, amendment, log or library file has changed.

| Step | Command | Output | Time |
|---|---|---|---|
| 1 | `python -B runner/verify_e25_unchanged.py` | `runs/e25_unchanged.json` (451 E25 files and the seal, hash-only) | seconds |
| 2 | `python -B runner/root_cause.py` | `runs/root_cause.json`, `runs/voi_predictions.csv` | ~3 s |
| 3 | `python -B runner/horizon.py` | `runs/horizon.json`, `docs/HORIZON.md` (10,000 paths, seed 20261014) | ~1 min |
| 4 | `python -B runner/local_power.py` | `runs/local_power.json` (synthetic, seed 20261014) | ~40 s |
| 5 | `python -B runner/reproduce.py` | Reruns 2–4 in-process and compares output bytes → `runs/reproducibility.json` | ~2 min |
| 6 | `python -B runner/import_e25_seal.py` | `runs/ledger/T1_A.jsonl`, `T2.jsonl`, `status.json`. The import runs only if a ledger file is absent; otherwise the script only verifies and reports. | seconds |
| 7 | `cd tests` then `python -B -m pytest -q` | 38 tests (synthetic fixtures, recorded outputs, guard) | ~35 s |

**Integrity of the folder.** `E26_FILES_SHA256.txt` lists the SHA-256 of every E26 file except itself. Check it with:

```
python -B -c "import hashlib,pathlib;[print('MISMATCH',p) for h,p in (l.split(None,1) for l in open('E26_FILES_SHA256.txt',encoding='utf-8') if l.strip()) if hashlib.sha256(pathlib.Path(p.strip()).read_bytes()).hexdigest()!=h]"
```

**Not reproducible by design:**

- `runs/e25_unchanged.json` and `runs/reproducibility.json` record their run time.
- The ledger entries record their creation time.
