# 11 — Frozen configuration, reproducibility, sealed forecasts, scoring procedure (deliverables 16, 17)

## 1. Frozen model (`evidence/FINAL_FROZEN_CONFIG.json`)

| Item | Value |
|---|---|
| Model | FINAL (RATE + MIND) LightGBM, `final-rate-mind-1.0`, selected by the owner on 2026-11-13 |
| Procedure | `app/hcw/final_engine.fit_predict` (= research `engine_final`, `rate='lin', miss='mind', cw='balanced'`). Within each fit, on training rows only: anchor and input set chosen; 25-input selection; correlation pruning; 16-setting grid by inner GroupKFold over regions. Chosen live configuration: 3 leaves, 150 trees, learning rate 0.02, feature/bagging fraction 0.8, min child 40, L2 5 |
| Constraints and weights | Monotone signs; survey-precision × balanced class weights |
| Missing data | Median fill + missing-value flags (MIND) |
| Calibration | Raw (normal CDF of forecast / residual scale) |
| Threshold | 0.50 (HFIAS moderate+severe ≥ 50 % = HIGH) |
| Seeds | 168, 1, 2, 3, 4; mean probability |
| Training data | FNRI 2015, ENNS 2018/2019/2021 (NNS 2013 as anchor history) |
| Information cut-off | 2026-11-01 (issue 2026-Q4) |
| Served leads | 1–5 sealed (Algorithm 3 MRLT = 5). Leads 1–2 recommended for publication (report 07 §3) |
| Code and data hashes | `code_sha256`, `data_sha256` in the config file |

**The only change adopted in this study** is the by-crop harvest input refresh (report 09 §4). It is a data-currency correction:
- no model, setting or threshold changed;
- no historical row changed.

## 2. Sealed forecasts: `evidence/SEALED_FINAL_2027Q1_2028Q1.json`, sha256 `80b20aed3b3ca59d5a246f1195978a5bfdb1671b6409b7c0f189288a27967680`

- **Contents:** 25 rows (5 CALABARZON provinces × Leads 1–5; 2027-Q1 to 2028-Q1). Each row holds the official FINAL probability, class, survey baseline, gap and contributions, plus the long-gap-corrected values the preview displays, kept for transparency.
- **All 25 are LOW.** The official p(HIGH) is 0.0011–0.0072, and the forecast shares are 22–28 %.
- **Integrity:** the seal script refuses to overwrite an existing seal. Nothing earlier was overwritten. The 11-12/11-13 ENNS 2022 seals are untouched and are **not used** under this brief.

## 3. Procedure for future confirmation (pending)
1. **Wait** for the next FNRI release of *provincial HFIAS moderate + severe* percentages with SEs covering any of these provinces and quarters.
   - The HFIAS instrument is required. FIES-only releases (as in NNS 2023) **cannot** score these forecasts.
   - If FNRI publishes only FIES from now on, prospective confirmation on this target may not be possible. That is an open risk.
2. **Verify** `sha256sum SEALED_FINAL_2027Q1_2028Q1.json` = `80b20aed…7680` **before** opening the outcomes.
3. **Score once** at 0.50:
   - accuracy, precision, recall, F1, AUC (if both classes occur), Brier;
   - against persistence and always-LOW;
   - with label-uncertainty weighting from the published SEs.

   No refit, recalibration, threshold change or variant selection may happen first.
4. **Report** the result whether it passes or fails. A change motivated by the result needs a new protocol, sealed before the following round.

## 4. Reproducibility status

| Item | Status |
|---|---|
| All metrics re-computable from stored fits | Yes (scripts in this folder and in `../aiPHeed_final_reliability_20261113/scripts`) |
| Fits reproduce stored probabilities | Yes (2.2e-16) |
| Live forecasts rebuildable | Yes: `build_corrected.py` with `PREVIEW_BUILD_OUT=out_final`, `PREVIEW_CAND=<branch cand_panel>`, `AIPHEED_LIVE_ASOF=2026-11-01` |
| **Code under version control** | **No.** `aipheed_hcw/backend/app/hcw/` (including `final_engine.py` and the patched `inputs.py`) and all `research_notes/` are untracked. Committing needs owner approval |
| Environment pinned | No lock file for `C:\Users\admin\aipheed\backend\venv` |
| Side effect | Importing `app.hcw.inputs` rebuilds `data/hcw/out/cand_panel.parquet` at import time. Backups: `cand_panel_before_agfix_20261113.parquet` |
