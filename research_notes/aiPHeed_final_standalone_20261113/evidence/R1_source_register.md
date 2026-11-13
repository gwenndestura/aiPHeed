# FINAL (RATE + MIND): source register (Rule 1g)

All sources are genuine published Philippine or international public data. "Release rule" is the rule the pipeline uses to decide whether a value was available at a forecast origin. It is enforced in code: `app/e150/model.py released()`; as-of panels `local_panel_asof.parquet`. These rules are checked by the pipeline tests re-run on 2026-11-13: `test_e151`, `test_e152`, `test_e175_target_scaling`, `test_hcw_engine`, `test_hcw_final_engine` (26 passed).

| Input family (dashboard group) | Source | Geography | Reference period | Release / availability rule in the pipeline |
|---|---|---|---|---|
| **Outcome and anchor:** HFIAS moderate+severe | DOST-FNRI: NNS 2013 (Appendix 33); FNRI 2015 Food Security Survey (Appendices 1–4); ENNS 2018, 2019 provincial dissemination decks; ENNS 2021 FNRI Heat Map export | Province | Survey reference quarter (2013-Q3, 2015-Q3, 2018-Q3, 2019-Q3, 2021-Q3) | Usable 6 quarters after the reference quarter. 2021 provincial SEs are not published: an assumed 3.0 points is used for weights and q only. |
| Food and rice CPI (market) | PSA OpenStat provincial CPI | Province | Monthly | As-of price panel (published months only; the E152 window never reads recent months) |
| Local food and rice prices, terms of trade (market) | PSA price series | Province / region | Monthly | As-of panel |
| Rainfall, soil moisture anomalies (climate) | NASA POWER | Province centroid | Monthly | Months completed before origin |
| Tropical cyclones (climate) | IBTrACS (NOAA) | Track points within province buffer | Event | Tracks before origin |
| ENSO (climate) | NOAA ONI | National / global | Monthly | Published months |
| Unemployment, income growth (employment) | PSA LFS; PSA regional accounts | National / region (no provincial variation in 2018 and 2019 training rows) | Quarterly / annual | Released before origin |
| Poverty, subsistence, poverty gap, density (poverty and social vulnerability) | PSA official poverty statistics; PSA census population and land area | Province | Three-yearly / census | Latest released round before origin |
| Agriculture and fish production (not a dashboard group) | PSA palay, corn, fisheries production | Province | Quarterly | 45 days after quarter end, or first seen online |
| News event and topic indices (counted inside groups) | GDELT, newspaper archives, Google News titles; XLM-RoBERTa events, BERTopic topics (DA-validated dataset) | Province / area / national | Quarterly windows | Stories published before origin (test_e151 window check) |
| OFW remittances | BSP | National | Monthly / quarterly | **Not an input of FINAL's 77 feature-set inputs** |

**Missing data.** MIND: training-median fill plus a "was missing" flag for each input missing in some training rows. Statistics come from training rows only. Missing-input rates by fold are in `R1_missingness_L1.csv`.

Three inputs are entirely missing in some folds' training rows, so they carry no information there:
- `ag_dev3y` and `ag_pc` (2018 and 2019 folds);
- `unemp_region` (all folds).
