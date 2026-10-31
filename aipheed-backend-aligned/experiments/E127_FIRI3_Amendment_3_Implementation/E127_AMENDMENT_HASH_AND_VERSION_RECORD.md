# E127 amendment, hash and version record (FIRI3 change log)

| Version | Protocol / amendment | SHA-256 | Change | Approved | Record |
|---|---|---|---|---|---|
| 1.0 | E121 protocol | 8a431a9ddb1efc0515e1b539924562b65119649edf44dfac8e4c878c2bf4b717 | Six-indicator FIRI3 | owner (E121) | `E121_FIRI3_Implementation/` |
| 1.1 | Amendment 1 | 4fd05309c3dee0800693e9a12b92ed112aebef35f9a219a8a620c88860050549 | Change-type series need a 2021+ comparison base (40 CPI rows rejected) | owner-confirmed (E123) | `E122_Data_Cutoff_Audit/` |
| 1.2 | Amendment 2 | 8b5f729cc34790e00dbadbc5ce02bfd050ca31dc665fd049bff9e38675f7711b | Latest complete annual year; CCS / SVS / common core | E123 instruction | `E123_FIRI3_Design_Resolution/` |
| **1.3** | **Amendment 3** | **4095ad4c2788a9203a7d6ee37dab92560c9705e14e7f6db621228183d7d5bcbb** | **Verified zero-storm PAR quarters recorded as 0** (2023-Q1, 2024-Q1, 2025-Q1); uncovered quarters stay missing | **owner (E127 §1)** | `E127_FIRI3_Amendment_3_Implementation/` |

## Amendment 3 summary

| Item | Detail |
|---|---|
| Reason | E114 built the PAR series with `groupby(q).size()`, so quarters without storms were absent. The as-of rule then used an older quarter's count. |
| Evidence | E126: no Western Pacific track point at all in the three quarters (E114 WP file); the E125 last-3-years file agrees for 2024-Q1 and 2025-Q1; no entry under the box or the official PAR outline |
| Zero vs missing | Zero only for quarters the file covers completely. A quarter not covered stays missing. Nothing is filled. |
| Historical effect | 9 regional FIRI3 scores, max \|Δ\| 0.041987, 1 band change (2025-Q2: above usual → usual or below); **0 provincial changes** |
| 2026-Q4 effect | Regional PAR percentile 0.7105 → 0.7500 (same count of 7) |
| Implementation commit | `abac0c8` (data layer, version constants, configuration, tests); E127 final commit (documentation) |

## Files and hashes after E127

| Item | SHA-256 |
|---|---|
| `firi3.py` (v1.3) | d8298024541f48ae9a472179c836fc1428ebae7fd83e58a24e47ab616d8e2cd1. Previous: c55224e3… (v1.2 with C-E126-1), b04658a4… (v1.2) |
| **Active** frozen configuration `E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.json` (canonical JSON) | **64a7d7df1a20530737e075b053bfcb6358ea7e78dcc4170261d605d235110b71** |
| Superseded configuration `E124_FROZEN_VALIDATION_CONFIGURATION.json` (v1.2) | 8973ca661cfcd68d41d7d1c9eb033adcdf3454723a7253294a8343f70d2178f0 (unchanged) |
| `firi.py` (FIRI v2) | 0e583131… (unchanged) |

**The v1.3 configuration** keeps the v1.2 features, weights, aggregation, completeness and bands. A test checks field by field. It adds `amendment_3`, `inputs_builder` and `supersedes`.

**v1.2 outputs** stay available for comparison: E123, E124 and E125 outputs and snapshots, and the E126 proposal files.
