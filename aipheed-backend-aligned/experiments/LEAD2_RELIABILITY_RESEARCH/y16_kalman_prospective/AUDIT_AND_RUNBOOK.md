# Y16: audit, implementation and runbook

**Plan:** `EXPERIMENT_PLAN.md`, SHA-256 `208b575464d21e41dd78447c39e4586fb7101bdb0b263f298b210b7701bd9699`, frozen 2026-10-29T14:17:41Z. It was frozen before any Y16 code was written and before any comparative run. Every Y16 script asserts this hash.

## 1. Audit of the Kalman challenger (Phase 1)

| Question | Finding |
|---|---|
| Implementation | `common/hmodels.py::kalman("BL", t, 2, (NCR, BL, VIS, MIN))` with `_series`, `_filter` and `_kfit` (Phase 2 Y2; unchanged since) |
| Data inputs | SWS rounds only, from `rlib.rounds()`: <br>BL 2021+ from `backend/data/inputs/sws_rounds.csv`; <br>NCR, VIS and MIN for all years, and BL before 2021, from `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv`. Both are read-only. |
| Sampling-error assumption | Per round, (MoE / 1.96)², using the area MoE stored per round. A missing MoE becomes 6.0. A quarter's variance is the mean round variance divided by the number of rounds. The predictive variance adds the **newest known quarter's** sampling variance, which is halved if that quarter had two rounds (a quirk kept to preserve the specification). |
| Missing data | Quarters without a round are bridged by prediction steps (state carried forward, variance grows). An area enters the φ/τ² fit only with ≥ 8 known quarters. The forecast needs ≥ 8 known BL quarters, else NaN (recorded as no forecast). |
| Training | Refitted at every issue on all rounds published before O(t). φ and τ² by maximum likelihood (Nelder–Mead, 3 fixed starts, deterministic). Each area's mean is the mean of its known quarters. **There are no tuned hyperparameters.** |
| Probability output | Φ((μ + φ^h·m − 11.3) / √(predictive variance)), with h the true horizon from the newest known quarter |
| Point-in-time | Every round is filtered by published < O(t). Tested: rounds published on or after O(t) leave both forecasts unchanged; a round published earlier changes them (positive control). |
| Historical vs operational specification | **Identical.** Y14 and Y15 called `HM.kalman` and `rlib.forecast` directly, and Y16 imports the same functions. With an empty overlay, the issued values match Y15's `dev_rows.csv` to < 1e-4 at the five origins tested. |

**Conventions noted (unchanged, so the specification is preserved):**

1. **Commissioned rounds.** The BL 2021+ series includes the commissioned Stratbase-SWS 2025-Q1 round, while the NCR, VIS and MIN series exclude commissioned rounds. This matches the FIRI target R and Y14/Y15. (P0H4's "primary" series excludes commissioned rounds; that is a different convention.)
2. **Pre-2021 release dates** are rule-based (label month end + 60 days). This affects history only, not future issues.

**Erratum found.** Y14 `RESULTS.md` says the 2027-01-01 issue targets 2027-Q3. The correct target is **2027-Q2**: origin 2026-Q4 + 2. Y14 is not edited (protected); the correction is recorded in the Y16 plan.

## 2. Is the Kalman model compatible with the existing issuance workflow?

**Yes. It needs only SWS data, and it runs in about 1–3 seconds per issue.**

I **did not modify** Y14's `issue_forecast.py`, because:

- it is a Y14 research artefact whose outputs and documentation refer to it;
- changing it would alter existing Y14 results.

The smallest isolated change was a **separate Y16 issuance module**. It imports the identical model functions and leaves every existing script, format and output untouched. No production code (backend, FIRI, P0H4) was changed.

**One operational blocker, solved without touching protected data.** Future SWS rounds would normally be added to `backend/data/inputs/sws_rounds.csv`, which is protected. Y16 instead reads `data/sws_rounds_overlay.csv`:

- it is append-only;
- each row needs area, quarter, H, published date, MoE, source URL and entry time;
- it is merged **in memory**;
- rounds duplicating the project series are ignored;
- every seal records the overlay's SHA-256.

If the project series is later updated through normal maintenance, the duplicates are skipped automatically.

## 3. Files (all new, under `y16_kalman_prospective/`)

| File | Purpose |
|---|---|
| `EXPERIMENT_PLAN.md`, `PLAN_SHA256.txt`, `PLAN_FROZEN_AT.txt` | Frozen preregistration |
| `runner/kprospect.py` | Overlay, forecasts, sealing (exclusive create, `SEALS.txt` hash registry, issue window), evaluation helpers |
| `runner/issue.py` | CLI: seal one issue date. It refuses outside the window; `--dry-run` writes only to `dry_runs/` and is never valid. |
| `runner/evaluate.py` | CLI: staged evaluation. <br>Fewer than 8 resolved quarters: integrity only. <br>8–19: descriptive. <br>20: the primary analysis, run once. Each run writes a new timestamped file. |
| `data/sws_rounds_overlay.csv` | Append-only overlay (header only for now) |
| `tests/test_y16.py` | 19 tests (section 4) |
| `prospective/` | Empty. **No forecast has been issued.** |
| `dry_runs/seal_issue_2027-01-01_written_20261029T142157Z.json` + `SEALS.txt` | One demonstration dry run (`validProspective: false`). It is a preview with today's data, **not** an issuance. |

## 4. Tests

`python -m pytest -q tests -p no:cacheprovider` → **19 passed** (83.9 s).

| Area | Tests |
|---|---|
| Timing | issue → target mapping (4 cases); non-quarter-start dates rejected; Manila-date window boundaries (5 cases) |
| No future data | rounds published on or after the issue date leave both forecasts unchanged; a pre-issue round is used (positive control) |
| Overlay | duplicates of project rounds ignored; publication date required |
| Missing observations | finite probabilities in (0, 1) at issues with gaps (BL 2022-Q1; NCR/VIS/MIN 2025-Q1) |
| Reproducibility | identical output after clearing all caches |
| Historical parity | equal to Y15 KAL and H1 at 5 origins (< 1e-4) |
| Seal integrity | all fields present, plan hash, input hashes, `SEALS.txt` hash, no overwrite, refusal outside the window, dry runs excluded from evaluation, tampering detected |
| Evaluation | paired difference, sign-test arithmetic and confusion matrix on synthetic data; outcome unresolved before 120 days; staging (descriptive at 16, primary at 20) on pseudo-seals written to a temporary folder. **No metrics are asserted or reported.** |

All test writes go to pytest temporary folders. `prospective/` stayed empty.

## 5. Runbook

| When | Action |
|---|---|
| Each new SWS hunger release (any area) | Append a row to `data/sws_rounds_overlay.csv`: area, quarter (the SWS quarter label convention used in `sws_rounds.csv`), H, **published date from the release**, MoE, source URL, entry time (UTC). Never edit an existing row. |
| **2027-01-01 .. 2027-01-08 (Manila date)** | `python -B runner/issue.py --issue 2027-01-01` → target **2027-Q2** |
| 2027-04-01, 2027-07-01, 2027-10-01, … (same 8-day window) | The same command with that date. A missed window is recorded as missed, never backfilled. |
| After each target quarter + 120 days | `python -B runner/evaluate.py` (integrity or descriptive only until 20 quarters resolve) |
| About 2032-07-29 (20 resolved targets 2027-Q2 .. 2032-Q1) | Primary analysis, once. Superiority requires bootstrap p < 0.05, a 95% CI below 0 and sign test p < 0.10. All seven rules are reported for both models. **R1 fails until 40 resolved quarters** (about 2037). |

## 6. Limitations kept explicit

| Limitation | Detail |
|---|---|
| Weak prior evidence for the challenger | Holm p 0.455 (Y15); lost in the four-area test (Y2); never predicted LOW in 2021–2026 |
| Small samples | 20 quarters gives low power for a Brier difference of about 0.02. A null result at the primary analysis would not show equivalence. |
| R1 | Needs ≥ 40 rows. One regional outcome per quarter makes it unreachable before about 2037. |
| The outcome | Regional (Balance Luzon) severe hunger, not Region IV-A or provincial food insecurity. SWS sampling error is ±4–6 points. |
