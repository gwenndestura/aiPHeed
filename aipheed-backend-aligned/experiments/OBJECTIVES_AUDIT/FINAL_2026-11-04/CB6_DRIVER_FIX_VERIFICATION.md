# C-B6 risk-driver / explanation correction: before-and-after verification (2026-11-04)

**Scope:** explanation text and tests only.
- No model was refitted. No prediction, feature, threshold, label, origin, baseline or rule changed.
- No demo was restarted. Nothing was committed or deployed.

## 1. Defects found and corrected (backend explanation logic, `app/ml/inference/foodinsecurity_system.py`)

**Backup:** `backup/backend_2026-11-04/foodinsecurity_system_before_driver_fix.py`.

| # | Where | Before (C-B6) | After |
|---|---|---|---|
| 1 | `reliability_text` (forecast narrative) | "…but fails the stricter reliability rules R1-R7 ()": an empty list, and false (C-B6 passes all seven) | "…and passes the stricter reliability rules R1-R7 (development evidence)" |
| 2 | `reliability_sentences` | "it fails the stricter rules ." (empty), and "Lead 3 failed …" hard-coded (wrong for C-E2 and C-E6, whose first failing lead is 4) | The pass/fail clause comes from each lead's own result. The stopping lead comes from the evaluation (C-B6: Lead 3, 0.742; C-E6: Lead 4, 0.677; C-b: Lead 3, 0.726) |
| 3 | `identity().evidenceStatus` | Always "fails R1-R7" | "passes R1-R7" or "fails R1-R7", from the lead's own result |

**Unchanged where the rules fail:** for C-b, C-E2 and C-E6 the existing wording ("but fails the stricter reliability
rules R1-R7 (R7 (stability))", and so on) is identical.

## 2. Driver bars (checked, no change needed in the calculation)

| Acceptance criterion | Result for C-B6 (`foodinsecurity_engine_cb6`) |
|---|---|
| Every bar has a number | `pct` for all five groups (API field); e.g. 2027-Q1: Market 80, Fish Kill 16, Climate 4, Employment 0, OFW 0 |
| From actual C-B6 SHAP | Each quarter's own C-B6 TreeSHAP per group (stored in `rows.csv`), in the served "relative" view |
| Sum to 100 | Yes, at every quarter (tested) |
| 0 only when the contribution is actually 0 | Employment and OFW are not C-B6 inputs. Their SHAP is exactly 0.0 in every row (tested), with status `no_model_input` |
| Direction | The sign of each group's contribution (tested) |
| Rice stocks | A separate group (`shap_supply` in `rows.csv`). Not merged into any of the five; named with its share in the narrative. **How to display it is a decision for you (§5)** |

## 3. Regression checks

| Check | Before → after |
|---|---|
| 29 artifacts: C-B6, C-E6, C-E2, C-b forecasts; results; served exports; baseline forecasts (IMPROVE_V2, h3); all pre-registrations; metrics report (`integrity/driver_fix_before.sha256`) | **29/29 identical** |
| 200 protected files (seals, ledgers, C-b export, models, production config, frontend, thesis PDFs) | **200/200 identical** |
| Live demo API (8081 C-E2, 8082 C-E6, 8083 C-B6; Quezon 2026-Q3/Q4, 2027-Q1: bars, status, score) | **Identical** (`integrity/driver_fix_api_before.txt` = `_after.txt`) |
| Metrics recomputed from the forecasts (C-b, C-E2, C-E6, C-B6 × 2 leads) | 8/8, difference 0.0 |
| HIGH/LOW calls, 7-baseline families, R1–R7 | Unchanged: the result files are byte-identical |
| Backend full suite | 1,022 → **1,024 passed** (+2 new tests), 18 skipped, 0 failed |
| Dashboard / API targeted suite | 89 passed, 8 skipped |

**New tests** (`tests/integration/test_foodinsecurity_config_metadata.py`):
- the reliability text follows each model's own rules (C-b, C-B6, C-E6);
- the C-B6 bars sum to 100, non-inputs are exactly 0 with `no_model_input`, and directions match the SHAP signs.

**A defect in my first version of the test, fixed:** it leaked a cached C-B6 explanation into two later tests. The test
now clears the served-model caches before and after itself.

## 4. Thesis evidence

No experiment, result, pre-registration, registry, plan or report was modified.

## 5. Your decisions (2026-11-04) and what was done

| Decision | Action |
|---|---|
| **Employment / OFW in C-B6: "Show 0% only"** | `frontend/src/components/LeftPanel.tsx`: the "not a model input" side text is removed for `no_model_input` rows; the existing "0%" number stays. Backup: `backup/LeftPanel_before_0pct.tsx`. The "not used in this forecast" note for inputs that round to 0% is unchanged |
| **Rice stocks: "Keep as now"** | No change |

**After the frontend edit:**
- **Frontend tests:** 87 passed. TypeScript: no errors.
- **Hot reload:** all three dev servers now serve the edited module.
- **Visible effect on C-B6 only:** C-E2 and C-E6 have no `no_model_input` rows (live API check). Only 8083 (C-B6) shows the
  change.
- **Protected manifest:** only `frontend/src/components/LeftPanel.tsx` differs (the approved change). The other
  199/200 files, and 29/29 model, forecast and baseline artifacts, are identical.

## 6. Options that were put to you (kept for the record)

1. **Showing a number (0%) instead of the text "not a model input" for Employment and OFW in C-B6.** The API already
   sends `pct: 0`, but the dashboard card replaces it with the text. Changing that needs a frontend edit
   (`LeftPanel.tsx`). All three running dev servers serve the same frontend source, so the edit would immediately change
   the 8081 and 8082 demos too. You asked that the running demos not change.
2. **Showing rice stocks as a contribution group:**
   - a sixth bar: a frontend change, and you rejected an extra row earlier;
   - including it in the 100% while showing only five bars: the five would then sum to less than 100;
   - or keeping it as now: excluded from the five bars and stated in the text.
