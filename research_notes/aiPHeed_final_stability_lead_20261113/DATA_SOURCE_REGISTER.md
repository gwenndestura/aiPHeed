# Data-source register (this study)

All model data are those of FINAL, unchanged.
- Full register with release rules: `../aiPHeed_final_standalone_20261113/evidence/R1_source_register.md`.
- Integrity checks (10/10 pass): `../aiPHeed_final_standalone_20261113/evidence/R1_R2_integrity.json`.

No new data entered any model in this study. Sources checked for the five-group audit, not used in any fit:

| Source | Coverage | First release | Usable for the 2018 / 2019 / 2021 folds? |
|---|---|---|---|
| PSA Annual Provincial Labor Market Statistics (https://psa.gov.ph/statistics/labor-force-survey/node/165789) | 117 provinces and HUCs, 2018–2020; annual thereafter | 27 Jan 2022 | No (after every origin); yes for future forecasts |
| PSA Survey on Overseas Filipinos (2020 special release) | Region; OFW characteristics | Annual | No provincial series exists |

**Survey release rule:** a round is usable 6 quarters after its reference quarter (`app/e150/model.py released`, `Pn.ANCHOR_LAG = 6`).

**Elapsed-time variable of FINAL-ET:** target quarter − reference quarter of the latest round released at the origin. It is computed from that rule alone; no outcome is read.
