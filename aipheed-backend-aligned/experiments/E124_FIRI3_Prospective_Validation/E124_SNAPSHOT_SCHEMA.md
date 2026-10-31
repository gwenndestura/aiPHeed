# E124 snapshot schema (append-only store, `runner/store.py`)

```
store/
  registry.jsonl                                   append-only events: attempt_blocked | issued | correction | observation
  forecasts/<forecast_id>/
    snapshot.json                                  written once
    feature_trace.csv                              written once
    manifest.json                                  content hash + file hashes
    corrections/C###.json, C###_feature_trace.csv  corrections, never replacing the original
    observations/O###_<date>.json                  later recomputations (stability / revisions / new information)
```

**`forecast_id`** = `FIRI3-<version>-<origin>`, for example `FIRI3-1.2-2026-Q4`. Each origin has one forecast per version. A new methodology version gives a new id, and never overwrites.

## `snapshot.json`

| Field | Content |
|---|---|
| `forecast_id`, `origin`, `target_observation_period`, `issue_date`, `issue_time` | Metadata (issue at 00:00 PHT, +08:00) |
| `firi3_version`, `protocol_sha256`, `amendment_1_sha256`, `amendment_2_sha256`, `config_sha256` | Methodology identity |
| `source_sha256` | SHA-256 of every source file used |
| `input_log` | Rows rejected (pre-2021, Amendment 1 base) |
| `units[]` | One record per province and the region (below) |
| `feature_trace_sha256` | Hash of `feature_trace.csv` |
| `created_utc`, `issued_on` | Wall-clock fields, **excluded from the content hash** |

**`units[]`** (one per unit):
- `scope`, `unit`;
- `firi3`, `band`, `status`;
- `indicators_available`, `indicators_defined`, `completeness_pct`, `indicators_used`, `indicators_missing`;
- `verification_share`, `loo_min`, `loo_max`;
- `indicator_scores` (all six; null when unavailable);
- `ccs`, `ccs_band`, `ccs_status`;
- `svs`, `svs_position`, `svs_status`;
- `fixed_core`, `cross_core`, `cross_core_indicators`;
- `firi_v2` (the served value, when one exists).

## `feature_trace.csv` (one row per feature × unit)

| Group | Columns |
|---|---|
| Identity | origin, issue_date, scope, unit, series_unit, feature, series, indicator, component, dataset |
| Values | raw_value, aligned_value (the processed value), source (series @ unit) |
| Timing and status | period, avail_date (publication or rule date), status (verified / rule_unverified / missing / stale / insufficient_history / unavailable_at_issue / incomplete_year) |
| Scoring | prior_n, score, direction, transform, normalization, note (e.g. "newer incomplete year(s) skipped") |
| Decision | `eligibility` (scored / not scored), `exclusion_reason` |

## Hashes

- **`content_sha256`** = SHA-256 of canonical JSON: sorted keys, floats rounded to 12 digits, NaN → null, all fields except the wall-clock ones.
- **Reproducible:** the same origin, inputs and configuration give the same hash (`Store.reproduce`).
- **`manifest.files`** = SHA-256 of each stored file. `Store.verify` checks both.

## Records

| Record | Contents |
|---|---|
| **Correction** (`C###.json`) | correction_id, reason, date, original_content_sha256, corrected_content_sha256, and the full corrected snapshot. The original stays in place and must pass verification first. |
| **Observation** (`O###_<date>.json`) | `forecast_stability` (original unchanged + hash); `data_revision_sensitivity` (features whose same period now has a different value); `prospective_measurement` (features now using a later period, and availability changes); unit-level issued vs later FIRI3 / band / indicator set; per-feature change type |
