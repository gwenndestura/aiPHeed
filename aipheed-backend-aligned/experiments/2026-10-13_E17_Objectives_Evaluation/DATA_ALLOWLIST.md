# Data Allowlist (E17)

**How it is enforced.** The guard is `runner/guard.py`, copied from E13 with the allowlist replaced. It does the following:

- checks each file's SHA-256 before every read;
- reads parquet only through a column-projected scan with a read-time filter that enforces the 2021–2025 window;
- denies every other project file, the production backend, `~/.claude`, databases and models;
- blocks subprocess and sqlite3;
- allows writes only inside this folder.

**Every file was checked from parquet footer statistics** (metadata only) to contain **no row after 2025-Q4 or 2025**.

| # | File | SHA-256 | Footer range (rows) | Use |
|---|---|---|---|---|
| 1 | E12 `runs/20261012T151208Z/realized_components_2021_2025.csv` | `6719baf7…432e67ce1` | 2021-Q1..2025-Q4 (100) | S1 (label), F, D, H |
| 2 | E12 `runs/20261012T151208Z/details.json` | `ee022c35…281a6865c` | Rounds 2021-Q2..2025-Q4 (21) | SWS rounds with publication dates |
| 3 | `data/processed/features_fused.parquet` (aligned) | `0080dd5c…a2fda1292` | **2020-Q1..2025-Q4 (120)**; read 2021-Q1..2025-Q4 (100) | The implemented 45-feature matrix plus `cpi_dev` |
| 4 | `data/processed/topic_proportions.parquet` | `c8cc63e3…06f2b7907`* | 2020-Q1..2025-Q4 (116); read 2021+ | Objective 1 coverage only |
| 5 | `data/processed/lgu_poverty.parquet` | `03c92a8d…db9ef16b7` | 2021 (142) | Objective 3 |
| 6 | `data/processed/lgu_census.parquet` | `705cece6…be19ec778` | Static 2020 census (142); no time column | Objective 3 |
| 7 | `data/processed/nns_fies.parquet` | `4f68d376…581edb411` | 2025 (5 rows, one regional value) | Objective 5 (availability of NNS figures) |
| 8 | `config/governing_model.json` | `c9697b6b…d2557dcc1` | Configuration text | Identifies the current implementation's target, inputs, timing and settings |

\* Full hashes are in `runner/guard.py`.

## A correction to earlier records

**E13's allowlist listed `features_fused.parquet` as mixed or protected.** Its footer shows the maximum quarter is 2025-Q4. Its schema has 45 features plus `province_code`, `quarter` and `cpi_dev`, with **no label and no forward-looking column**. It is therefore eligible, and is used here. Earlier experiments (E9, E12) read it with a ≤ 2025-Q4 filter that removed nothing.

## Not opened

| File or source | Reason |
|---|---|
| `fssi_quarterly.parquet`, `trigger_proportions.parquet` | Footer shows rows up to **2026-Q3** (mixed). Their ≤ 2025 values are already inside `features_fused`. |
| `psa_rice_prices.parquet` | Rows up to 2026-Q3 (mixed) |
| `labels.parquet`, `psa_indicators.parquet`, `sws_hunger*`, `cpi_full*`, `panel*`, `feature_provenance.json`, the news corpus, `bias_weights` | Mixed, protected or carrier files. Labels come from file 1. |
| Served models (`lgbm_best.pkl` and others), `*.db`, `mlruns` | Protected |
| `Downloads/aipheed_trend_all-provinces_2025-Q1_to_2026-Q2.pdf`, `Downloads/DA_Quarterly_Report_2026_Q3.pdf` | May show 2026 values. **Not opened.** |
| Thesis chapters other than Chapter I | Per your instruction |
