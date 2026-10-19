# E61: E58 low-forecast investigation (2026-10-19)

**Read first:**
- `FINAL_REPORT.md` (the consolidated report: candidates, root causes, drift and combination, feature defects, target validity, news, dashboard, loading speed);
- `NEWS_PIPELINE_USE_AUDIT.md` (did the improved news reach the model).

**Protocols**, each frozen before its candidates were scored:
- `PROTOCOL.md`: sha256 `9d38d8e7…`, in `runner/PROTOCOL_SHA256.txt`;
- `PROTOCOL_ADDENDUM_1.md`: sha256 `243d619e…`, in `runner/ADDENDUM_1_SHA256.txt`.

## Reproduce

Run from `backend/` with `venv/Scripts/python.exe -B <script>`. Every script verifies the E57/E58 seals.

| Script | Output |
|---|---|
| `runner/a1_reproduce.py` | 2027-Q1 from served API, artifacts, frozen file and retrain → `tables/a1_*`, `out/a1_reproduce.json` |
| `runner/a2_calibration_joint.py` | calibration, low-probability cases, joint-probability audit → `tables/a2_*`, `out/a2_calibration_joint.json` |
| `runner/a3_missed_high.py` | the 8 E56 false negatives re-run with TreeSHAP → `tables/a3_missed_high_cases.csv` |
| `runner/a4_targets.py` | target-definition comparison and price levels → `tables/a4_*`, `out/a4_targets.json` |
| `runner/a5_features.py` | feature and timing audit → `tables/a5_feature_audit.csv`, `out/a5_features.json` |
| `runner/c1_predict.py` | candidates C1–C4 sealed (write-once) → `sealed/candidates.csv`, `sealed/operational_2027Q1.json` (+ sha256) |
| `runner/c2_score.py` | frozen selection rule and comparison → `tables/c2_*`, `out/c2_score.json` |
| `runner/a6_truncation.py` | leakage test of C2/C3/C23/C4 at all origins → `tables/a6_truncation_test.csv` |
| `runner/d1_predict.py` | addendum arms D1–D3, K1–K2, FA-*, hunger H0–H2, C0 split counts, sealed → `sealed/addendum1*.csv` |
| `runner/d2_score.py` | addendum scoring → `tables/d2_*`, `out/d2_score.json` |

## Code changed outside this folder

Working tree only; not committed.

| File | Change |
|---|---|
| `backend/app/services/dashboard.py` | E61 summary parts and caveat |
| `backend/app/schemas/public.py` | `components`, `caveat` |
| `backend/app/ml/inference/e41_lead2.py` | record cache |
| `backend/tests/integration/test_e61_forecast_context.py` | new tests |
| `frontend/src/test/summarySentence.test.tsx` | new test: the existing paragraph shows the sentence; no new element |

**Not changed:** `RightAnalyticsPanel.tsx` and `apiTypes.ts` equal HEAD. The collapsible box added earlier was reverted at your request.

**Not mine:** `insights.py` and the E46 D-1 lines in `e41_lead2.py` were another session's uncommitted edits, left as found.

**Served text evidence:** `out/served_sentence_laguna_2027Q1.txt`.
