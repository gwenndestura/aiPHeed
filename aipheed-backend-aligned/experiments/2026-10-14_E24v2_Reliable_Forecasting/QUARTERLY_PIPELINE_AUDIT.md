# Quarterly pipeline audit (E24v2 isolated copy: `backend_dev/`)

**Starting point:** the E24 pipeline (registry, snapshot store, PHT periods, news eligibility, one record shared by the API, dashboard and PDF).

**What E24v2 adds:** a forecaster that can actually produce a forecast once authorized inputs exist.

## 1. One cycle, end to end

| Step | Module | What it guarantees |
|---|---|---|
| Period | `app/quarterly/config.py`, `config/forecast_period.json` | Target = reference + 1 (derived, never typed); cutoff in Asia/Manila; a cutoff inside the target quarter is rejected |
| Inputs | `app/quarterly/registry.py`, `config/quarterly_sources.json` | Every file is registered with its SHA-256 computed from the bytes, its observation period, its availability time and its authorization. Changed bytes need a new vintage with a revision note, and old vintages are kept. |
| Requirement checks | `app/quarterly/update.py::check_requirement` | For each requirement: UNAUTHORIZED, HASH_MISMATCH, NOT_AVAILABLE_BY_CUTOFF, STALE (ends before the needed quarter) or MISSING. **New:** `"blocking": false` marks context-only inputs (supporting news). They are reported but cannot block or feed the model. |
| Forecaster (**new**) | `app/quarterly/forecaster_v2.py`, `app/quarterly/pcf_engine.py` | Reads only registered, authorized, hash-verified inputs. **Applies the publication rules row by row** (below). Returns probabilities, 80% intervals, a regional/provincial component split, signal level, evidence status, LGU ranking, input hashes and a reading guide. |
| Record | `run_update` → `write_record` | One JSON record per target quarter with a content SHA-256. Rerunning with identical inputs creates nothing new (idempotent). A change archives the previous record under `history/`. |
| **Replay (new)** | `run_update(..., replay=True)`; CLI `replay --config` | Reconstructs a past cycle from files assembled after its cutoff. File-level availability cannot be checked, so the engine's row-level rules are the only timing guard. The record is labelled `mode: REPLAY` with an explanation, is written under `replays/`, and **never becomes the live record** (`latest.json` untouched, tested). |
| API, dashboard, PDF | `app/api/v1/quarterly.py`, `runner/build_outputs_v2.py` | All read the same record. The dashboard JSON and PDFs carry the record hash. |

## 2. Publication-time rules inside the engine (origin O = 00:00 PHT, first day of the target quarter)

| Input | Usable at O iff | Code |
|---|---|---|
| SWS round | `published` < O **and** `date_type` starts with "verified". Unverified or estimated dates are unusable. | `rounds_at_origin` |
| Label (threshold, persistence) | Quarter ≤ reference − 1 **and** every definition-A round of that quarter is usable | `threshold_at` |
| Quarterly D | Quarter ≤ reference − 1 | `d_inputs_at_origin`, `d_fit` (training targets ≤ reference − 1) |
| Dnow | Months 1–2 of the reference quarter only | `dnow_panel` + `d_inputs_at_origin` |
| News | Never used by the model; displayed only if authorized and inside the window | `eligibility.py` (E24) |

**Leakage test** (`test_engine_ignores_everything_not_published_at_the_origin`). These perturbations each add +50 and leave the forecast byte-for-byte unchanged:

- D of the reference quarter and later;
- Dnow of later quarters;
- SWS rounds published after the origin;
- labels of the reference quarter and later.

## 3. Results of the two cycles run on the real authorized inputs

| Cycle | Target | Status | Why |
|---|---|---|---|
| **Live** (`config/forecast_period.json`) | **2027-Q1** (news: 2026-Q4; cutoff 2026-12-31 23:59:59 PHT) | **INSUFFICIENT_DATA**, no forecast, 0 articles | SWS rounds STALE (registered through 2025-Q4; the 2026-Q3 round is protected); label history STALE; quarterly D STALE (through 2026-Q2; 2026-Q3 protected); Dnow STALE (October–November 2026 protected); cutoff not reached. Supporting news MISSING (context only). |
| **Replay** (`config/replay_2026Q3.json`) | 2026-Q3 (cutoff 2026-06-30) | **READY**, mode REPLAY | Inputs: SWS rounds through 2025-Q4 (2026 rounds lack verified dates, so excluded), D through 2026-Q1, Dnow April–May 2026 |

**The replay equals the research seal.** Every province's P(HIGH) and price-pressure probability equals the first prospective seal (`SEAL_20261013T164218Z`) within 1e-12 (`test_pipeline_replay_equals_the_research_seal`). The pipeline and the research code therefore compute the same forecast from the same authorized inputs.

## 4. Data-sufficiency and versioning behaviour (tested)

| Situation | Behaviour | Test |
|---|---|---|
| A required input ends before the needed quarter | INSUFFICIENT_DATA; reason "STALE"; `forecast = null` | `test_pipeline_stale_input_gives_insufficient_data_and_no_forecast` |
| A file became available after the cutoff | Live: NOT_AVAILABLE_BY_CUTOFF. Replay: allowed, but labelled. | `test_live_run_rejects_files_that_became_available_after_the_cutoff_but_replay_is_labelled` |
| Input not authorized | BLOCKED; no forecast | `test_unauthorized_input_blocks` |
| Context input (news) missing | Forecast still READY; the gap is listed in `context_missing` | `test_pipeline_ready_with_nonblocking_news_missing` |
| Revised file for a source | New vintage, which needs a revision note; old vintage kept; previous record archived | E24 tests (kept, passing) |
| Missing province or forecast | Risk index null, never zero | E24 tests (kept, passing) |

## 5. Prospective seals (C9 machinery)

**What a seal is.** `runner/seal_v2.py` and `runner/seal_v2_a3.py` write forecasts for targets whose outcomes are protected and unseen, with a SHA-256 seal:

| Seal | Contents |
|---|---|
| `SEAL_20261013T164218Z` | T1: B1, B1p, PCF, PCF-S, M2; T2: B1, B1p, M1, M3, M4 |
| `SEAL_20261013T222814Z` | PCF_NOW (amendment A3) |

Both use origin 2026-07-01 and target 2026-Q3, 2026-Q4 and 2027-Q1.

**Scoring.** `runner/score_prospective.py`:

- refuses if a seal file changed;
- refuses if the outcome file is not named, with its SHA-256, in your authorization record;
- refuses if outcomes precede the sealed targets;
- pools seals across quarters;
- keeps the verdict `INSUFFICIENT_PROSPECTIVE_EVIDENCE` until ≥ 8 distinct scored origins and ≥ 5 LOW rows exist (tested).

**Every future quarter.** Run the live cycle at the cutoff. Its READY record is itself a sealed forecast, because the content hash is fixed before the outcome exists. Score it once the outcomes are authorized.

## 6. Remaining limitations (not fixable in code)

- **Live 2027-Q1 forecast.** Needs authorized 2026-Q3 SWS and CPI, October–November 2026 provincial CPI, and the cutoff to pass.
- **Provincial CPI release dates.** Use the +14-day proxy (conservative), pending RSSO verification.
- **SWS publication dates for the 2026 rounds.** Unverified, so those rounds are excluded.
- **BERTopic.** Not re-run per cycle, as in E24: it needs the unauthorized corpus. News is context-only here.
