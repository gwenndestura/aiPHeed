# Authorization allowlist (generated from run 20261013T152113Z manifest; hashes computed by the guard, not typed)

The allowlist is imported programmatically from the E17 and E18 guards. Every file is re-hashed before each read. The January–June 2026 sources carry your 2026-10-13 authorization (E18 `DATA_AUTHORIZATION_RECORD.md`).

**Nothing from July 2026 onward is authorized, and no 2026 news is authorized.**

| File | Pinned by | Expected = actual SHA-256 | Match | Authorized 2026 source | Read-time row filter |
|---|---|---|---|---|---|
| -backend-aligned\config\governing_model.json | E17+E18 | `c9697b6b920cdf32986b422ea9c48533db72b7b1632dae221f4200dd2557dcc1` | True | False | None |
| -backend-aligned\data\processed\features_fused.parquet | E17+E18 | `0080dd5c3cafd82e68a6baa198c6d37894890e4fd9eeb44a72e34e3a2fda1292` | True | False | ['quarter', '2021-Q1', '2025-Q4'] |
| -backend-aligned\data\processed\lgu_census.parquet | E17 | `705cece6a8855f9fc8e9d2d4447d47dc067f5de0e4b717e75325593be19ec778` | True | False | None |
| -backend-aligned\data\processed\lgu_poverty.parquet | E17 | `03c92a8db785534e305c1fcd6dfb5bc9b5e1c26fd860f9cd655387edb9ef16b7` | True | False | ['year', 2021, 2025] |
| -backend-aligned\data\processed\nns_fies.parquet | E17 | `4f68d37626e830677a74a3f2f897e59374d3724d51298bb6a6b08e0581edb411` | True | False | ['year', 2021, 2025] |
| -backend-aligned\data\processed\topic_proportions.parquet | E17 | `c8cc63e39390e3f4589f5e3e533a364f5d30b448f17ea8f163122f006f2b7907` | True | False | ['quarter', '2021-Q1', '2025-Q4'] |
| -backend-aligned\data\supplementary\collection_2026-10-09\cpi_2026_release_dates.csv | E18 | `9a7d4805708d1dab59a32593980bbb72698ad0c96ed9ceb9f836a08b9fdbf5c2` | True | True | None |
| -backend-aligned\data\supplementary\collection_2026-10-09\provincial_food_cpi_yoy_2026H1_raw.csv | E18 | `57f09e91149be56f0602d63dad40216d3fc38d01e66499e07f110d1b2fd2e6e9` | True | True | None |
| -backend-aligned\experiments\2026-10-12_E12_SWS_Scoring_Comparison\runs\20261012T151208Z\details.json | E17+E18 | `ee022c35135d86fa9ec987d52212bd9c229037b835628ef03f2e4ec281a6865c` | True | False | None |
| -backend-aligned\experiments\2026-10-12_E12_SWS_Scoring_Comparison\runs\20261012T151208Z\realized_components_2021_2025.csv | E17+E18 | `6719baf75ad60dd47f94cfb269058354783414d7437b19a93101582432e67ce1` | True | False | None |
| \backend\data\processed\sws_hunger.parquet | E18 | `64701ed66981697ddf2d7b083a0de4e7a14f004e349878703bfc784145d434c4` | True | True | ['quarter', '2026-Q1', '2026-Q2'] |

## Integrity assertions in the run

- {'assert': 'components <= 2025-Q4', 'rows': 100, 'violations': 0}
- {'assert': 'rounds <= 2025-Q4', 'rows': 21, 'violations': 0}
- {'assert': 'features_fused <= 2025-Q4', 'rows': 100, 'violations': 0}
- {'assert': 'sws_2026 <= 2026-Q2', 'rows': 10, 'violations': 0}
- {'assert': 'CPI 2026 = 2026-01..2026-06, 30 rows', 'ok': True}
- {'assert': 'SWS 2026 stratum balance_luzon', 'ok': True}
