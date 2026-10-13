# E15 Integrity Report (2026-10-13; work 10:43–10:53 local)

**Hashes and access are different things.** Matching hashes show that file **contents are unchanged**. They are **not** evidence that a file was never read. Evidence about reads comes only from the E15 guard's access log, which covers E15's own Python processes.

## 1. Allowlist

Hash-pinned in `runner/guard.py`. Each loader asserts that no row or record refers to a quarter after 2025-Q4.

| File | SHA-256 | Used for |
|---|---|---|
| E12 `runs/20261012T151208Z/realized_components_2021_2025.csv` | `6719baf7…432e67ce1` | F (input), plus E12's D and S1 (reproduction checks only) |
| E12 `runs/20261012T151208Z/details.json` | `ee022c35…281a6865c` | SWS rounds, scope, τ0 |
| E13 `runs/20261013T022702Z/metrics.json` | `4234d060…78820ed4` | Sizing the prospective protocol |
| E13 `runs/20261013T022702Z/scored_rows.csv` | `94e16df4…e2364bc7` | Sizing H2 |

**What the guard blocks:**

- **Data files:** no parquet is read, and every parquet entry point is blocked. Any other project file, the production backend, `~/.claude`, databases, models and the E10 sealed forecast are all denied.
- **Processes:** subprocess and sqlite3 are blocked.
- **Writes:** allowed only inside E15.
- **During the work:** one allowlist entry was first typed with a wrong hash suffix. It was corrected before any run; the guard would have refused the file anyway. All four hashes were re-verified against the files before use.

## 2. What ran and what it opened (access logs)

| Process | Files opened | Result |
|---|---|---|
| `runner/size_prospective.py` (`runs/sizing_20261013T024522Z`) | The 4 allowlisted files | Quarter counts for the prospective protocol |
| `runner/run_e15.py`, run `20261013T024905Z` and replicate `20261013T025153Z` | The 2 E12 files | Prototype output. All runtime checks passed. The replicate is **byte-identical** (JSON, 3 CSVs, checks). |
| `runner/render_mock_report.py` | Only this experiment's output JSON | `TWO_LAYER_MOCK_REPORT.md` |
| Synthetic tests (twice) | None (synthetic fixtures; guard decisions tested without opening data) | 22 passed, both times |

**No guard denial occurred.** No protected 2026 file, cache, log or derived value was opened. The data-gap inventory used only code docstrings and project documents. **No data was fetched and no web page was opened in E15.**

## 3. Frozen files

| File | SHA-256 | Frozen |
|---|---|---|
| `PROSPECTIVE_VALIDATION_PROTOCOL.md` | `1069bcb38a8ed93c40766b07888555064b050cdee4ea2e6431986bd958d19181` | 10:46:43, before any prototype output. Re-verified unchanged at the end. The runner checks it before building. |

## 4. Verification and changes

| Check | Result |
|---|---|
| 865 recorded hashes: protected baseline, E1–E7, served model metadata, 54 production files, E8 v1/v2 | **865/865 match.** Identical to the E13-start result. |
| E9, E10 (both lists), E11, E12 and E13 file hash lists | **0 failures.** E9–E13 are unchanged. |
| Files modified since 10:43:02 outside E15 (excluding `backend/venv`, `node_modules`, `.git`) | **None** |
| Production backend, frontend, served models, classifications, dashboard, thesis chapters | Unchanged |
| Scheduled tasks `aipheed` and `aipheed-auditing` | Still **disabled** |
| Git during E15 | **No commit or push in E15.** HEAD `eee269b` on `backend+frontend`; 23 status entries; `.git/index` unchanged. |

**One Git change happened earlier the same day, before E15 started, at your request.** The E13 folder was pushed to the new branch `e13-da-predictive-accuracy` (commit `5f7765f`, local and remote equal). E15 is not in that branch.

## 5. Limitations

1. **The prototype shows measured values, not forecasts.** It is not connected to any API.
2. **Mixed series in the regional layer:**
   - **What it uses:** all 21 SWS rounds, including 3 supplementary 2025 rounds that the earlier production series recorded as absent.
   - **How they are handled:** they are flagged `series: supplementary`. Legacy S1 uses production rounds only.
3. **The quarter counts for the prospective protocol** come from E13's retrospective results on quarters that had already been examined. They are probably optimistic, so the half-effect counts are reported too.
4. **Unverified items in the data-gap inventory:**
   - **Outcome sources:** CBMS coverage, provincial LFS availability, and wholesale successor tables for staples other than rice.
   - **FNRI provincial design:** the search summaries were not checked against FNRI's primary tables.
5. **Not verifiable:** reads by other sessions or people.
