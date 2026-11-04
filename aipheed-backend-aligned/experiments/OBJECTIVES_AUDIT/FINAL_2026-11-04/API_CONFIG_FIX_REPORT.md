# `/api/v1/config` fix report (authorized local backend correction)

## Defects (food-insecurity mode, `AIPHEED_MAP_MODEL=foodinsecurity`)

1. **`indicator.horizon` and `indicator.caveat`** were hard-coded C-b text:
   - "Maximum Reliable Lead Time 2 quarters";
   - "Lead 1 = that quarter, Lead 2 = the next quarter";
   - "R7: 2015-2020 accuracy 0.57".

   `indicator.definition` said "one LightGBM". The C-E2 demo therefore displayed C-b's reliability.
2. **`servingModel.model` and `modelPerformance`** reported **FIRI v2** (thesis_system) in this mode, for both the C-b
   and C-E2 demos.
3. **`horizon().why_not_longer`** always said "Lead 3", which is wrong for C-E2 (its first failing lead is 4).

## Source traced

- `backend/app/ml/inference/foodinsecurity_system.py`: the `INDICATOR` dict and `horizon()`.
- `backend/app/services/dashboard.py`: `serving_model()` and `model_performance()`, which read `THESIS.*`.

## Change

Backups are in `OBJECTIVES_AUDIT/backup/backend_2026-11-04/`.

- **`foodinsecurity_system.py`:**
  - `INDICATOR` is now built by `indicator()` from the served `evaluation.json`: served leads, MRLT, the first failing
    lead and its accuracy, failed rules per served lead, the model id, `news_effect_text`, and the optional
    `model_description` / `sources_extra`.
  - It is exposed as `INDICATOR` through a module `__getattr__`, so every caller is unchanged.
  - A missing or invalid evaluation gives `evaluationAvailable: false` and an explicit "unavailable" statement.
  - New `model_performance()` and `serving_model()` return the served model's id, plan hash, seal, MRLT, served leads,
    issue date and per-lead metrics.
  - `horizon()` uses the first failing lead.
  - **No metric is written in code.**
- **`dashboard.py`:** in food-insecurity mode, `serving_model()` and `model_performance()` delegate to the served
  module. Other modes are unchanged.
- **`runner/export_ce2.py`** (research export):
  - evaluates leads through the first failing lead (adds Lead 4);
  - adds `model_description`, `sources_extra` and the ablation sentence.
  - `rows.csv` is byte-identical, so **inference is unchanged.**

## Not changed

Production configuration (`render.yaml`, Dockerfile), C-b's export, models, seals, ledgers and frontend files are
unchanged (`PROTECTED_FILE_INTEGRITY_REPORT.md`).

## Live check (C-E2 demo, port 8001)

- **horizon:** "served: Lead 2 = the next quarter. … Maximum Reliable Lead Time of 3 quarters; Lead 4 fails the 75%
  rule (0.645) … R1-R7 failed: Lead 2: R3, R7".
- **servingModel:** `ALLBASE-CE2`, plan a1b469da…, MRLT 3, served leads [2], issued 2026-10-01, target 2027-Q1, lead 2.
- **modelPerformance:** `ALLBASE-CE2`, MRLT 3; no FIRI text.

## Tests (`backend/tests/integration/test_foodinsecurity_config_metadata.py`, 5 new; all pass)

1. C-b export → MRLT 2, "Lead 3 fails … (0.726)", model NEWS_V2-CB.
2. C-E2 export → MRLT 3, "Lead 4 fails … (0.645)", no C-b text ("Time of 2 quarters", "0.57", "NEWS_V2-CB", "one
   LightGBM"), consistent ids and plan hash, no FIRI.
3. `/api/v1/config` endpoint returns the derived metadata.
4. Missing, invalid or incomplete evaluation → explicit unavailable result.
5. Forecast probabilities unchanged by the metadata code.

The existing food-insecurity and thesis tests (54) still pass.
