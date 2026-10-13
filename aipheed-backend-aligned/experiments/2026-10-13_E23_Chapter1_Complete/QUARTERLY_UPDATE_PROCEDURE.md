# Quarterly update procedure (the single documented process)

**Code:**

- `aipheed-backend-aligned/app/quarterly/`
- CLI: `scripts/quarterly_update.py`
- configuration: `config/forecast_period.json`
- registry: `config/quarterly_sources.json`
- records: `data/quarterly_runs/<target>/forecast_record.json`
- snapshots: `data/quarterly_store/`

## The rule every cycle follows

| Item | Definition |
|---|---|
| Reference quarter R | The current dashboard quarter (now 2026-Q4) |
| Target quarter | R + 1 (now **2027-Q1**), derived and never typed separately |
| Supporting news | Articles whose **original publication timestamp, converted to Asia/Manila**, falls between the start of R (00:00 PHT) and **min(cutoff, end of R)** |
| Excluded news | Published after the cutoff (this covers all target-quarter and later news). Published before R. Duplicate URL. **Undated: quarantined, never assigned by retrieval date.** |
| Cutoff | Declared in the configuration. Default: 23:59:59 PHT on R's last day. An earlier cutoff marks the quarter "incomplete" on every output. |
| Government, SWS and CPI inputs | Used only if their recorded availability time is ≤ the cutoff. **Unknown availability = unavailable.** |
| One record | The API (`GET /api/v1/quarterly/forecast-period`), the dashboard (`/forecast-period`) and the PDF are all generated from the same record, which carries a content SHA-256. |

## Each quarter

1. **Acquire** the new files from the agencies, or from authorized APIs only.
2. **Register** each file. The SHA-256 is computed from the bytes. Record:
   - the observation period;
   - the publication/availability time;
   - the authorizer and the authorization reference.

   ```
   python -m scripts.quarterly_update register --id news_2027Q1 --kind news --path <file> --obs-start 2027-Q1 --obs-end 2027-Q1 --available-at <ISO> --authorized-by "<name>" --authorization-ref "<ref>"
   ```

   - **Revisions:** registering new bytes for an existing id requires `--revision-note`. This creates vintage n+1; earlier vintages are kept.
3. **Run:**

   ```
   python -m scripts.quarterly_update run
   ```

   The run:
   - verifies every hash;
   - checks coverage and staleness against each requirement;
   - filters news by publication time;
   - snapshots the inputs (idempotent);
   - writes the record.

   The status is one of:

   | Status | Meaning |
   |---|---|
   | `READY` | Every requirement passes, the cutoff has passed and a promoted model exists |
   | `INSUFFICIENT_DATA` | The record lists exactly what is missing |
   | `BLOCKED` | An unauthorized input or a hash mismatch |

4. **Rebuild the dashboard and PDF:**

   ```
   python -B runner/build_outputs.py ...
   ```

   Then run the tests:
   - `pytest --noconftest -c tests/pytest.ini tests/`
   - `npx vitest run`
5. **Review.** The DA administrator reviews the outputs before anything is published.
6. **Advance:**

   ```
   python -m scripts.quarterly_update advance
   ```

   This moves R to R + 1 and the target to R + 2. Re-declare the cutoff if it is not the end of the quarter.

## Late, unavailable, unauthorized or revised data

| Case | What happens |
|---|---|
| **Late** (published after the cutoff) | `NOT_AVAILABLE_BY_CUTOFF` gives INSUFFICIENT_DATA. It is never back-filled into a forecast whose origin preceded its release. |
| **Unavailable / never released** | `MISSING` or `STALE` gives INSUFFICIENT_DATA. The previous quarter's values are **not** relabelled as new. |
| **Unauthorized** | `BLOCKED`. The file's content is never read. |
| **Revised** | A new vintage with a revision note. Old vintages stay in the snapshot store, so a past forecast can be reproduced with the inputs it actually used. A forecast recomputed with revised inputs is a **retrospective** forecast and must be labelled as such. |
| **Idempotent reruns** | Identical inputs give an identical content hash, and no new history entry is written. |

## Verified behaviour (tests)

25 pipeline tests in `tests/test_quarterly_pipeline.py`, including:

- the 2027-Q1 → 2027-Q2 transition (target, news window and exclusions all advance, and the 2027-Q1 record remains reproducible);
- the publication-time boundaries at 23:59:59 and 00:00:00 PHT;
- retrieval date never used to assign a quarter;
- stale and late indicators;
- unauthorized sources;
- the cutoff not yet reached;
- an API record identical to the stored one.

**Synthetic fixtures** are written only to pytest's temporary directory.

## Current state (2027-Q1 cycle, run 2026-10-13)

**Status: `INSUFFICIENT_DATA`** (record content SHA-256 `f0c27087…`).

**Missing:**

- authorized 2026-Q4 news (none registered);
- 2026-Q3 government indicators;
- provincial food CPI;
- the SWS round (authorized data end at 2026-Q2);
- a promoted model (none met the reliability rule).

Also, the 2026-12-31 23:59:59 PHT cutoff has not been reached.
