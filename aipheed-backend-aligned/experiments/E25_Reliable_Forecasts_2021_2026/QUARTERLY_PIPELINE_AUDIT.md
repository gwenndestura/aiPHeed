# Quarterly pipeline audit (isolated copy: `backend_dev/`)

**Scope.**

- E25 audits the quarterly update built in E23 and extended in E24/E24v2: `app/quarterly/*`, `scripts/quarterly_update.py`, `app/api/v1/quarterly.py`.
- The copy comes from commit 5113ae5 (E24v2). `backend/` and the aligned backend were not modified.
- The pipeline runs outside the E25 data guard (it is product code), but it reads only the files registered in `backend_dev/config/quarterly_sources.json`. Each file is hash-verified at every check.

## 1. What the pipeline guarantees (checked)

| Guarantee | How | Checked by |
|---|---|---|
| One record per target quarter, read by the API, the dashboard and the PDF | `run_update` writes `data/quarterly_runs/<target>/forecast_record.json`. The E25 timeline record is a single file served by `/api/v1/quarterly/e25-timeline` (integrity re-checked on every request), copied byte-identically to the dashboard, and rendered to the PDF. | `test_api_dashboard_pdf_read_one_record`, `test_api_refuses_a_tampered_record` |
| No forecast without every blocking input authorized, hash-verified, available by the cutoff and current | `check_requirement` statuses: UNAUTHORIZED, HASH_MISMATCH, NOT_AVAILABLE_BY_CUTOFF, STALE, MISSING | `test_requirement_status` (4 cases) |
| Missing data never becomes a forecast | An INSUFFICIENT_DATA or BLOCKED record carries `forecast = null` and the exact `missing` list | `test_insufficient_record_never_carries_a_forecast` |
| No forecast before the cutoff | `cutoff_reached` is required | Synthetic transition test (run before the cutoff gives INSUFFICIENT_DATA) |
| History kept; reruns idempotent | Content-hash records; the earlier record moves to `history/` | Synthetic transition test |
| Quarter transition | `ForecastPeriod.advanced()`: reference +1, target +1, every requirement quarter +1 | Synthetic transition test (2027-Q1 → 2027-Q2) |
| Publication-time rules | News by original publication time in PHT; undated news quarantined | Unchanged from E23 (E23/E24 tests) |

## 2. Defects found and fixed (details in `BUG_FIXES.md`)

| # | Defect | Status |
|---|---|---|
| F1 | D component trained from 1995-Q1 | Fixed (2021-Q1); inputs rebuilt in window |
| F2 | Authorized 2026 SWS rounds never usable | Fixed (documented upper bound) |
| F3 | My mixed-date-format bug in F2 | Fixed (found by test) |
| F4 | Evidence status claimed T2 "SUPPORTED" from the void back-cast | Fixed (E25 evidence) |
| F5 | No `indicative_only` flag | Added |
| R3 | Duplicate-news rule keeps the first copy regardless of status | Reported |

## 3. The live 2027-Q1 cycle (run 2026-10-14; clock before the cutoff)

- **Command:** `python -m scripts.quarterly_update run` from `backend_dev/`.
- **Record:** `data/quarterly_runs/2027-Q1/forecast_record.json`, content SHA-256 `6c4f4c9e442d62c1c547a849390334682363a90cfb823fe8766681bbde4dd686`.
- **Status: INSUFFICIENT_DATA. No forecast is attached.**

Missing:

- `sws_rounds: STALE`: the latest authorized round is June 2026; the September 2026 round is needed.
- `label_history: STALE`: labels end at 2026-Q2; 2026-Q3 is needed.
- `provincial_D_quarterly: STALE`: D ends at 2026-Q2; July–September 2026 CPI is needed.
- `provincial_D_now: STALE`: October–November 2026 CPI is needed (M4_21 only).
- The cutoff 2026-12-31 23:59:59 PHT is not yet reached.
- Context only (non-blocking): no authorized Q4 2026 news.

## 4. Quarterly transition with synthetic fixtures (never used in evaluation)

`test_quarterly_transition_with_synthetic_complete_inputs` builds a complete synthetic input set through 2026-Q3/Q4 in a temporary folder and registers it with computed hashes.

| Step | Result |
|---|---|
| Run before the cutoff | INSUFFICIENT_DATA |
| Run after the cutoff | READY; a forecast for all five provinces |
| Every risk block | `indicative_only = true` |
| LGU ranking | 142 LGUs |
| Earlier record | Kept in `history/` |
| `advanced()` | Moves reference and target to 2027-Q1 / 2027-Q2 and every requirement quarter by one |

## 5. What an operator must do next quarter

1. Register each newly authorized file (`python -m scripts.quarterly_update register ... --authorized-by ... --authorization-ref ...`). The hash is computed from the bytes.
2. Run the cycle after the cutoff (`run`). If anything is missing, the record says exactly what.
3. Score the sealed forecasts whose outcomes are authorized (`runner/score_sealed.py`).
4. Advance the period (`advance`).
