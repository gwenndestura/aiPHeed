# Input Allowlist (E13)

**Rule.** E13 opens only the five files below. Each one holds eligible data only, **through 2025-Q4 or the year 2025**. No file that also contains 2026 observations is opened. E9 to E12 read such mixed files with a read-time filter; E13 does not.

The guard (`runner/guard.py`) enforces this rule:

- It checks each file's SHA-256 before every read.
- It denies every other project path, including the production backend (except file 5), `~/.claude`, databases and models.
- It blocks sqlite3 and subprocess.
- It allows writes only inside this folder.

| # | File | SHA-256 | Content checked | How it was confirmed eligible-only | Read as |
|---|---|---|---|---|---|
| 1 | `experiments/2026-10-12_E12_SWS_Scoring_Comparison/runs/20261012T151208Z/realized_components_2021_2025.csv` | `6719baf75ad60dd47f94cfb269058354783414d7437b19a93101582432e67ce1` | 100 rows: 5 provinces × 2021-Q1..2025-Q4. Columns F, mean5, D, H, S1. | Written by E12 from reads filtered to ≤ 2025-Q4. Recorded in `E12_FILES_SHA256.txt`. The loader rejects any quarter after 2025-Q4. | Text, hash-verified |
| 2 | `…/20261012T151208Z/details.json` | `ee022c35135d86fa9ec987d52212bd9c229037b835628ef03f2e4ec281a6865c` | Only `two_layer.regional_layer_rounds` (21 SWS rounds, 2021-Q2..2025-Q4, with publication dates), `two_layer.regional_scope` and the τ0 entries are used | Written by E12. Recorded in `E12_FILES_SHA256.txt`. The loader rejects any round after 2025-Q4. | Text, hash-verified |
| 3 | `data/processed/nns_fies.parquet` (aligned) | `4f68d37626e830677a74a3f2f897e59374d3724d51298bb6a6b08e0581edb411` | 5 rows, year 2025, one regional value repeated per province | Footer statistics: year min = max = 2025, one row group. Read-time filter 2021 ≤ year ≤ 2025. | Parquet, hash-verified |
| 4 | `data/processed/lgu_poverty.parquet` (aligned) | `03c92a8db785534e305c1fcd6dfb5bc9b5e1c26fd860f9cd655387edb9ef16b7` | 142 LGU rows, year 2021 | Footer statistics: year min = max = 2021. Read-time filter as above. | Parquet, hash-verified |
| 5 | `backend/data/processed/psa_subsistence.parquet` (production, **read only**) | `389a0dee24ccb893bfbd7eb25870fecb77f4bdcf2a4fcd7a04805f3a015c7c79` | 18 rows, years 2018–2023. Only 2021 and 2023 are returned. | Footer statistics: year 2018–2023. Git blob equals HEAD (commit 23f9093, 2026-09-02). Read-time filter 2021 ≤ year ≤ 2025. | Parquet, hash-verified |

**Footer checks.** The footer statistics for files 3 to 5 were read with `pyarrow.parquet.read_metadata` before the guard existed. That reads only the file's metadata block.

## Provenance note

Files 1 and 2 were **derived by E12** from mixed files: `psa_indicators.parquet`, `features_fused.parquet` and `labels.parquet`, each read with a filter to ≤ 2025-Q4, plus small allowlisted SWS files. E13 itself opens none of those mixed files. The derived files contain no 2026 values. The hash is the evidence that their content is unchanged since E12 wrote them.

## Explicitly not used

| File or source | Reason |
|---|---|
| `psa_indicators`, `labels`, `features_fused`, `cpi_full*`, `sws_hunger*`, `panel*` (both trees) | Mixed or protected. Not needed, because file 1 has every 2021–2025 value E13 uses. |
| `data/supplementary/collection_2026-10-09/*2026H1*`, `cpi_2026_release_dates.csv` | 2026 data |
| `cpi_final_month_release_dates.csv` | Not needed: the T−2 availability rule follows from the calendar (see the protocol). Not opened. |
| E9 `input_frame.csv`, E10 `q4/*` | Not needed. The sealed Q4 forecast is left untouched. |
| Served models, `*.db`, `mlruns`, news corpus, `Claude outputs/`, lean and simplified outputs | Protected or carrier files |
| Web pages of PSA, SWS or RSSO | Not opened (they could display 2026 releases) |

## Amendment 1 (2026-10-13, 11:02 onward)

**No new data file was added.** Amendment 1 uses the same five hash-pinned files, read through the same guard (`runner/guard.py`, unchanged). In addition it reads, inside this folder:

- the sealed v1 forecasts, `runs/20261013T022702Z/predictions.csv` (SHA-256 `868581d5…`, checked before use);
- for the root tables only, the v1 comparison CSVs in the same run folder.

LightGBM 4.6.0 is used from the existing `backend/venv`. Nothing was installed.

**Still not opened:**

- `cpi_final_month_release_dates.csv` and every other release-date file that could contain 2026 rows;
- every mixed or protected file listed above.

The timing evidence in `TARGET_AND_TIMING_AUDIT.md` comes from the E9 eligibility document and the calendar rule. It does not come from those files.
