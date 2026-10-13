# Test results (E24v2, executed 2026-10-14)

## Python: `pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` → **68 passed**

| File | Tests | Covers |
|---|---|---|
| `test_e24v2.py` (**new**) | 19 | See the breakdown below |
| `test_quarterly_pipeline.py` (E24, re-run against the modified `update.py`) | 26 | PHT quarters, cutoff, eligibility, authorization, vintages, idempotence, stale/late/missing data, 2027-Q1 → 2027-Q2, API = record. **No regression from the E24v2 changes.** |
| `test_e24_additions.py` (E24) | 10 | NLP stage, validation, PSGC/SAE ingestion, ranking labels and ties, P-block leakage, E24 seal refusal |
| `test_e23_lib.py` (E23/E24) | 6 | Statistics vs brute force / scikit-learn |
| `test_disaggregator_fix.py` (E24) | 2 | Missing province → unavailable, not zero |
| `test_score_responses.py` (E24) | 5 | DA questionnaire scorer (synthetic responses inside the test only) |

**What the 19 new tests cover:**

- **PCF maths:**
  - the Kalman filter equals the precision-weighted mean;
  - the forecast variance grows with the gap;
  - targets in the past are rejected;
  - the D model recovers a known coefficient;
  - signal levels.
- **Leakage:** these perturbations each add +50 and leave the forecast byte-identical:
  - D of the reference quarter and later;
  - later Dnow;
  - SWS rounds published after the origin;
  - labels of the reference quarter and later.
- **Publication rules:** unverified or late rounds are unusable; the threshold uses only published labels.
- **Pipeline paths:**
  - READY with news missing, because news is non-blocking;
  - STALE gives INSUFFICIENT_DATA with no forecast;
  - a file available after the cutoff is rejected live, while the replay is labelled and never becomes the live record;
  - an unauthorized input gives BLOCKED.
- **Real authorized inputs:**
  - the pipeline replay equals research seal 1 within 1e-12;
  - the live 2027-Q1 cycle is INSUFFICIENT_DATA with 0 articles;
  - the LGU table reproduces E24's risk index (< 1e-9).
- **Prospective scoring refuses:**
  - an unauthorized hash;
  - a tampered seal.

  It also returns INSUFFICIENT_PROSPECTIVE_EVIDENCE with fewer than 8 origins (synthetic outcomes in `tmp_path` only).
- **Acquisition guard:** refuses year ≥ 2026 in the request and in the response (no network used); the gate passed and the manifest hashes match.
- **T1 back-cast runner (A2):** refuses an unauthorized file and any row after 2020; dry run on a synthetic SWS fixture.

## Frontend (`dashboard_dev/`): `npx vitest run` → **21 passed** (4 files)

`src/test/e24v2.test.tsx` (**7 new**) checks the **actual** `e24v2_dashboard.json`:

- **Live cycle:** 2027-Q1, consistent labels, INSUFFICIENT_DATA, no forecast.
- **Replay:** labelled REPLAY and READY; 5 provinces; probabilities in [0,1] with valid intervals; 142 LGUs.
- **The approved composite forecast is never shown as validated:** every T1 evidence status is NOT_ESTABLISHED, and each row shows "Indicative only".
- **"Goal NOT met"** while any criterion is unmet or C9 is not assessable.
- **Seals:** listed with full 64-hex hashes and pending status.
- **Substitutes:** every province-mean substitute is labelled "density only".

**Rendered page (jsdom + Testing Library):**

- banner and status;
- missing inputs;
- replay label;
- 5 province rows with "Indicative only";
- "Goal NOT met";
- 4 confirmatory hypotheses;
- 142 ranking rows, filtering to 41 for Quezon;
- 15 PSA measured rows.

**E24's own 6 frontend tests still pass** (the old page remains at `/forecast-period-e24`).

**Type check and build:**

- `npx tsc --noEmit -p tsconfig.app.json`: **no errors in E24v2 files**. The 6 reported error lines are all in the pre-existing, unchanged `src/data/mockData.ts`.
- `npx vite build --outDir dist-e24v2`: succeeds (chunk-size warning only).

**Served check** (vite preview, port 8101): `/forecast-period`, `/e24v2_dashboard.json` and both PDFs return HTTP 200 with the correct content types.

**PDF text** (pdfminer) contains:

- the target, news, cutoff and mode lines;
- the status and missing inputs;
- the province table (replay);
- the criteria;
- the back-cast summary;
- the seal hashes;
- the limitations.

**Not inspected visually.** No browser automation is installed, so the page was not looked at.

## Reproducibility

| Check | Result |
|---|---|
| Back-cast re-run (`BX_20261013T223930Z` vs `BX_20261013T163710Z`) | **Byte-identical**: predictions (seal `b59d5e95…`, 27,840 rows), `results_BX.json` (every permutation p-value), and `metrics_BX.csv` |
| Development re-run (`DEV_20261013T222827Z` vs `DEV_20261013T164041Z`) | Max abs diff **0.0** on all 3,080 common rows |
| Prospective seals recomputed (`--verify`) | `ac8babbc…` and `356cc22f…` **identical**; no new seal written |
| Pipeline replay vs research seal | Equal within 1e-12 (test) |
| Dashboard JSON rebuilt after re-registration | Identical SHA-256 (`3967d03f…`) |
| E24 required-model predictions | Re-used from E24's seals (hash re-verified on every read) |

## Integrity

| Check | Result |
|---|---|
| E17, E18, E23, E24 hash lists | **0 differences** (65 / 198 / 249 / 347 files) |
| `backend/`, `frontend/` | No git changes |
| Thesis PDF | SHA-256 `88dd0b62…` re-verified; Chapter I text identical to E23 |
| Acquisition | No year ≥ 2026 requested or returned (asserted); raw responses hashed in the manifest |
| Comparability gate | Passed (max \|ΔD\| 0.039 pp vs E12; published YoY median \|Δ\| 0.023 pp) |
| Leakage assertions in every fold (back-cast, development, seals) | Pass |

## Not run, and why

| Test | Reason |
|---|---|
| T1 back-cast on real data | Needs your SWS 1998–2020 file (A1); only the synthetic dry run was executed |
| Prospective scoring on real outcomes | 2026-Q3+ outcomes are protected |
| PSA SAE ingestion on the real workbook | psa.gov.ph returns 403 to scripts (not bypassed) |
| Full backend suites (`aipheed-backend-aligned/tests`, `backend/tests`) | Their `conftest.py` loads databases, models and mixed files that are not authorized (as in E24) |
| Real-browser visual check | No browser automation installed |
