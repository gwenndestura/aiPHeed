# Defects found and fixed (E24v2)

## 0. Isolation status

**Where E24v2 changes live.** Every E24v2 change is inside `experiments/2026-10-14_E24v2_Reliable_Forecasting/`:

- `backend_dev/` is a copy of E24's isolated backend: code and config, plus derived input files in `data/inputs/`;
- `dashboard_dev/` is a copy of E24's isolated dashboard; `node_modules` is a junction to `frontend/node_modules`, used read-only.

**What was verified unchanged.** These were verified after the work:

| Item | Check | Result |
|---|---|---|
| E17 | Hash list | 0 differences of 65 files |
| E18 | Hash list | 0 of 198 |
| E23 | Hash list | 0 of 249 |
| E24 | Hash list | 0 of 347 |
| `backend/` and `frontend/` | git | No changes |

Nothing was committed, pushed, merged or deployed.

**Still pending from E23 (unchanged by E24v2).** E23 left **16 modified tracked files** and 5 new items in `aipheed-backend-aligned/`. The list and revert command are in `2026-10-14_E24_Resolve_Forecasting/BUG_FIXES.md` §0. They still await your keep/revert decision (checklist A5).

## Defects in the forecasting design or system (fixed in the isolated copy)

| # | Defect | Fix | Verification |
|---|---|---|---|
| F1 | **Published information was thrown away.** At origin O(t), E23/E24 used government data of quarter t−1 only. The first two monthly provincial CPI releases of quarter t, already public before O(t), were ignored. | **Dnow** (months 1–2 deviation) added to the D model (M4, `pcf_engine.d_fit`, `use_now`) | Back-cast on 94 unseen quarters: HB3/HB4 supported (accuracy 0.713 vs 0.617) |
| F2 | **The provincial component was trained on 2021–2025 only (≤ 20 quarters)**, although PSA publishes it from 1994 | PSA 2018-based back-cast acquired (1994–2025, ≤ 2025 only); comparability gate (max \|ΔD\| 0.039 pp vs the approved values) | `data/comparability_gate.json`, `test_comparability_gate_passed_on_the_acquired_series` |
| F3 | **"Better Brier than persistence" was trivially true**, because hard 0/1 persistence has Brier = error rate | Calibrated persistence (B1p) added as a stricter baseline. Every Brier claim in E24v2 is made against B1p. | `BASELINE_COMPARISON.csv` (`brier_p_vs_B1p`) |
| F4 | **The quarterly pipeline could never forecast** ("no promoted forecaster") | `forecaster_v2.make_pcf_forecaster`, wired into the CLI `run` and `replay` | `test_pipeline_ready_with_nonblocking_news_missing` |
| F5 | **News blocked forecasts although no model uses it** | Requirement flag `"blocking": false`; reported in `context_missing`, never used by the model | Same test |
| F6 | **Past cycles could not be reproduced end to end.** File-level availability correctly rejects files assembled later. | `replay=True` mode: labelled REPLAY, written under `replays/`, never the live record | `test_live_run_rejects_..._but_replay_is_labelled`; replay = research seal (1e-12) |
| F7 | **No route to unseen-quarter evidence.** E24's `seal_prospective.py` needs unauthorized 2026 news and government features, so it always refuses. | `seal_v2.py` / `seal_v2_a3.py` seal forecasts from authorized data only. `score_prospective.py` refuses tampering and unauthorized outcomes. | Two seals exist; `test_score_prospective_refuses_tampering_and_missing_authorization` |
| F8 | **Forecasts carried no uncertainty, component split or evidence status**, so users could not tell a weak signal from a supported one | The engine outputs P, an 80% interval, signal level (STRONG/MODERATE/UNCERTAIN), regional vs provincial contributions, and the evidence status per lead. The dashboard and PDF show "Indicative only" whenever the lead is not validated. | Vitest: "never shows the approved composite forecast as validated" |
| F9 | **The SWS round rule accepted any date.** E23's `label_published` relied on the `published` column only. | `rounds_at_origin` also requires `date_type` "verified…"; unverified 2026 rounds are excluded | `test_unverified_or_late_rounds_are_unusable` |
| F10 | **The LGU ranking's validity problem was undisclosed:** 126 LGUs are ranked by density only, and density runs opposite to poverty (ρ = −0.76 where both exist) | Per-LGU `ranking_basis`; dashboard and PDF caveat; adviser decision B9 | `runs/lgu_analysis.json`; vitest substitute-label test |
| F11 | **Provincial differentiation was presented without a measured reference** | PSA measured subsistence and poverty incidence with CIs shown beside the forecasts (labelled "measured") | Vitest `psa-rows` |

## Process errors during E24v2 (disclosed; all corrected)

| # | What happened | Effect | Correction |
|---|---|---|---|
| P1 | The first development run crashed in the noise-ceiling step: E24's lead-1 rows include 2026-Q1 targets, whose H value was not in the E12 rounds table | Incomplete run folder `DEV_20261013T164014Z` (predictions only) | H for 2026 taken from the authorized labels (H = S1 − 2D, asserted identical across provinces); folder removed; later runs reproduce each other exactly (max diff 0.0) |
| P2 | A scripted edit to `lgu_rankings_v2.py` failed its assertion, but the unedited script then ran and overwrote `LGU_RANKING_VALIDATION.csv` with the E24 layout | The deliverable was briefly in the old format; **pipeline inputs unchanged** (same SHA-256 `f0ca2c53…`) | Edit applied (output now `data_v2/lgu_vulnerability_table.csv`); deliverable regenerated by `lgu_analysis.py` |
| P3 | Synthetic test fixtures named like protected data (`*labels*`, `*panel*`) were blocked by the data guard | 4 tests failed | Fixtures renamed; **the guard was not weakened** |
| P4 | A test fixture declared its files available after that test's cutoff | 1 test failed: the pipeline correctly refused | Fixture date corrected |

## Did any fix change an earlier scientific result?

**No.**

- E23 and E24 results are untouched (hash lists verified).
- The E24 required-model predictions are re-used from their seals.
- The LGU risk index reproduces E24 to < 1e-9 given the same province probabilities (`test_lgu_table_reproduces_e24_risk_index`).
