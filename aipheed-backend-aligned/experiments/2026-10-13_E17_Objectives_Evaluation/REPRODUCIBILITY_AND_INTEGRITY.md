# Reproducibility and Integrity (E17)

**Hashes and access are different things.** Matching hashes show contents are unchanged, not that files were never read. Read evidence comes only from the guard's access logs, for E17's own processes.

## 1. Order of work (2026-10-13, local time)

| Time | Step |
|---|---|
| 11:37 | Folder created (first named E16; renamed **E17** when your separate "E16 Task A" brief arrived, before any output existed). Chapter I extracted from `THESIS 2 (10).pdf` (sha256 `88dd0b62…`). |
| 11:38–11:42 | Chapter III passages were read **before** your instruction to use Chapter I only. They are **not saved and not used as requirements.** The 0.75 figure appears only for information, because your earlier brief named it. |
| 11:42 | Input inventory: structure and classes, no models (`runs/inspect_20261013T034224Z/`) |
| **11:44:34** | **Protocol frozen:** `EVALUATION_PROTOCOL.md` `e719338e…`, `OBJECTIVE_EVIDENCE_MAP.md` `4b4fdcd5…`, `DATA_TIMING_AUDIT.md` `f5071dc3…` (`runner/PROTOCOL_SHA256.txt`). Both runners check them. |
| 11:47 | `run_e17.py` primary (`runs/20261013T034704Z`). Predictions sealed (`SEAL.json`) before labels were joined. |
| 11:48 | `run_supporting.py` (`runs/supporting_20261013T034830Z`) |
| 11:49 | Replicates `runs/20261013T034910Z` and `runs/supporting_20261013T034941Z`: **all compared outputs byte-identical** (8 + 4 files) |

## 2. Tests and runtime checks

| Check | Result |
|---|---|
| `tests/test_e17_synthetic.py`, 15 tests: news t and government t−1 timing; government NaN (not 0) at 2021-Q1; SWS feature only from rounds published before the origin; the label-publication rule; strict training never contains unpublished labels (R0 does, as intended); persistence uses the latest published label; single-class training gives a constant prediction; confusion, accuracy, precision and AUC; bootstrap identity; 7 guard decisions | **15 passed** (`tests/pytest_output.txt`) |
| Runtime future-perturbation check (every test fold, primary and S-T0): every feature after the origin, every unpublished label and every SWS round published after the origin set to 999 or flipped; predictions of all six arms unchanged | **All passed** |
| Single-class training folds | 0 |
| Allowlist hashes at the start and end of each run | Identical |
| Guard denials | None |

## 3. How to rerun

```
cd aipheed-backend-aligned/experiments/2026-10-13_E17_Objectives_Evaluation
../../../backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
../../../backend/venv/Scripts/python.exe -B runner/run_e17.py            # add --deliverables to rewrite root CSVs
../../../backend/venv/Scripts/python.exe -B runner/run_supporting.py
```

| Item | Value |
|---|---|
| Interpreter | `backend/venv` (Python 3.13.2, pandas 2.3.3, numpy 2.4.4, LightGBM 4.6.0, scikit-learn 1.8.0) |
| Seeds | LightGBM 42; bootstrap 20261013 |
| Inputs | The 8 hash-pinned files in `DATA_ALLOWLIST.md` |

## 4. Preservation checks (end of E16/E17)

| Check | Result |
|---|---|
| 865 recorded hashes: protected baseline, E1–E7, served model metadata, 54 production files, E8 | **865/865 match.** Identical to the E13-start result. |
| E9, E10 (both), E11, E12, E13 (v2), E15 and E16 file lists | **0 failures** |
| Files changed outside E16 and E17 since 11:30:30 (excluding venv, node_modules, .git) | **None** |
| Git | No commit or push. HEAD `eee269b` on `backend+frontend`; 23 status entries; `.git/index` unchanged. |
| Scheduled tasks | Both still **disabled** |
| Thesis PDF | Read only (sha256 unchanged). The two Downloads PDFs that may show 2026 values were **not opened**. |

## 5. Unresolved items

1. **SWS release-date records disagree.** `timing_audit.py` has 2025-Q4 released on 2026-05-12; E12's verified per-round record has 2026-01-14. E17 uses E12's.
2. **The supplementary 2025-Q2 and 2025-Q3 SWS rounds** have an unresolved quarter assignment. They affect only the supporting H analysis. Labels use production rounds only.
3. **Provincial CPI publication dates** are proxies.
4. **Poverty timing in `features_fused`** does not match the release schedule.
5. **The recorded 0.818 accuracy** was not reproduced. It depends on 2020 data and a training rule that admits unpublished labels.
6. **Reads by other sessions or people** cannot be verified.
