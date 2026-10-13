# Reproducibility, Integrity and Limitations (E17 v3)

**Hashes show file identity, not that a file was never read.** Read evidence comes only from the guard's access logs (`runs/*/integrity_log.json`).

## 1. Order of work (2026-10-13, local time)

| Time | Step |
|---|---|
| 11:54 | Folder and guard created (allowlist: 3 eligible files). Chapter I extraction copied from E17. Footer-only scan of the files holding 2026 rows, for the authorization list. |
| **11:56:22** | **Frozen:** `FROZEN_CANDIDATES_AND_SELECTION_RULE.md` (`71b7baec…`) and `PHASE0_HORIZON_AND_INFORMATION_GAP.md` (`6dbf798e…`), in `runner/PROTOCOL_SHA256.txt`. The runner checks both before starting. |
| 11:58 | Run `runs/20261013T035829Z` (predictions sealed in `SEAL.json` before scoring; root `METRICS_SUMMARY.csv`) |
| 11:58 | Replicate `runs/20261013T035855Z`: all 5 output tables **byte-identical**; the forecast JSON is identical apart from its timestamp |

## 2. Tests and assertions

| Check | Result |
|---|---|
| `tests/test_v3_synthetic.py` (12): information-cutoff invariance; carry-forward, mean and drift formulas; damped Theil–Sen; training pairs respect the horizon; F and D cutoff and the zero baseline; the selection rule (including a "lucky quarter" case and a late-half failure); 6 guard decisions | **12 passed** |
| Runtime assertions (`integrity_log.json`) | Allowlist hashes match at the start and end; no quarter after 2025-Q4 in components (100 rows), SWS rounds (21) or `features_fused` (100); unemployment identical across provinces in every quarter; future-perturbation at every h = 5 origin returns identical outputs |
| Guard denials | None |

## 3. Preservation (end of E17 v3, 12:00)

| Check | Result |
|---|---|
| 865 recorded hashes | **865/865 match.** Identical to the E13-start result. |
| E9, E10 (×2), E11, E12, E13 (v2), E15, E16 and E17 file lists | **0 failures** |
| Files changed outside E17 v3 since 11:54:36 | **None** |
| Git | No commit or push. HEAD `eee269b`; 23 status entries; `.git/index` unchanged. |
| Scheduled tasks | Disabled (checked at 11:51; not touched since) |
| 2026 data | **None opened.** The authorization list was built from file names and footer row ranges only. |

## 4. How to rerun

```
cd aipheed-backend-aligned/experiments/2026-10-13_E17v3_Improved_Models_2027Q1
../../../backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
../../../backend/venv/Scripts/python.exe -B runner/run_v3.py        # --deliverables rewrites METRICS_SUMMARY.csv
```

Inputs: the 3 hash-pinned files in `DATA_AUTHORIZATION_AND_ALLOWLIST.md`. Python 3.13.2, pandas 2.3.3, numpy 2.4.4. No random seeds are needed: every candidate is deterministic.

## 5. Limitations

1. **Too few origins at the required horizon** (3 for H; 5 for F and D), all previously explored. **Exploratory only.**
2. **No 2026 holdout** (no authorization). The forecast uses a January 2026 information set at h = 5.
3. **Disputed quarter assignment** of the three supplementary 2025 SWS rounds. Two of the three H origins at h = 5 are those quarters.
4. **Provincial CPI publication dates are proxies,** so the F and D forecasts are not operationally valid.
5. **Uncertainty is not quantified.**
6. **The thesis risk classifier cannot be forecast for 2027-Q1** without unauthorized 2026 inputs.
7. **No independent provincial food-insecurity outcome exists.** Nothing here forecasts food insecurity.
