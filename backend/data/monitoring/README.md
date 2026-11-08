# Monitoring indicators: PSA LFS (provincial) and PSA SOF (regional)

**Added 2026-11-06** from the owner's workbook `PSA_LFS_SOF_aiPHeed_feature_data.xlsx` (sha256 `75698ea4…9931`). The values are copied unchanged. The sources are the PSA CALABARZON regional office (Labor Market Statistics 2023; Annual 2025 LFS preliminary) and PSA SOF special releases 2021–2025, with the URLs in each row.

| File | Level | Years | Content |
|---|---|---|---|
| `calabarzon_provincial_lfs_2021_2025.csv` | **Province** (5 CALABARZON) | 2021–2023, 2025 (2024 not transcribed) | Employment rate; unemployment and underemployment 2022–2023 |
| `calabarzon_provincial_lfs_2025_extra.csv` | Province | 2025 (preliminary) | LFPR, unemployment and underemployment where PSA stated them |
| `calabarzon_regional_sof_2021_2025.csv` | **Region IV-A** | 2021–2025 (2025 preliminary) | CALABARZON share of national OFWs; national remittance totals |
| `psa_lfs_sof_use_notes.csv` | n/a | n/a | Owner's usage rules |

## Use: monitoring only, not a model input (yet)
- **It cannot be validated in back-tests.**
  - The latest historical forecast date is 2021-Q2 (ENNS2021, Lead 1).
  - The earliest value here (annual 2021 LFS) was published in 2022.
  - So **no historical forecast could have used it**, leaving zero training rows. This is the same problem that made `unemp_region` empty.
- **Coverage is CALABARZON only.** The model learns from 77 provinces; a feature present for 5 cannot be learned.
- **SOF is regional and annual** (an April–September reference). It is joined to provinces only as an explicitly regional value and never interpolated to quarters.

**Legitimate uses now:**
1. Dashboard trigger-group indicators for employment (provincial) and OFW exposure (regional), with their sources.
2. A future model input, once a provincial HFIAS round after 2022 exists to validate against.

**Not independently re-verified against PSA tables:** PSA blocks scripted access.
