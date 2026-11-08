# Label comparability report: the owner workbook and the public food-insecurity labels

Workbook: `aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx` (owner-supplied 2026-11-03). The original is kept unchanged in
`backend/data/fi_labels/raw/owner_supplied/` (sha256 in `raw/MANIFEST.csv`). Code: `app/fi_labels/workbook.py`.
Record-level results are in `data/fi_labels/clean/owner_workbook_records_verified.csv` and the `Workbook_records` sheet of
DATA_SOURCE_AND_VALIDATION_LOG.xlsx.

## 1. Verification of the 50 records against primary sources

| Group | Records | Years | Primary source checked | Result |
|---|---|---|---|---|
| FNRI 2015 food secure | 5 | 2015 | FNRI 2015 Food Security Survey report, Appendices (PDF downloaded from FNRI) | **5 verified** (exact) |
| FNRI 2015 severely food insecure | 5 | 2015 | same | **5 verified** |
| PSA subsistence incidence, families | 15 | 2018, 2021, 2023 | PSA OpenSTAT Table 3 (downloaded) | **15 verified** |
| PSA subsistence incidence, population | 15 | 2018, 2021, 2023 | PSA OpenSTAT Table 4 (downloaded) | **15 verified** |
| ENNS severe food insecurity | 5 | 2018/2019/2021 | DEPDev CALABARZON RDP results matrix (secondary); FNRI tables blocked from this network | **unverified (secondary)** |
| ENNS moderate-to-severe | 5 | 2018/2019/2021 | same | **unverified (secondary)** |

No verified record differs from its primary source (tolerance 0.05 pp). Regional benchmarks: FNRI 2015 (verified),
FNRI 2023 FIES 19.1 % (verified via PSA SDG 2.1.2), the derived "100 − food secure" (derived from verified),
ENNS pooled 51.5 % and 2023 severe 1.7 % (unverified secondary), PIA 2025 (news report; provisional, not used).

## 2. Why the 50 records are not a training target

* **Not quarterly.** They are annual or one-off survey estimates (2015, 2018, 2019, 2021, 2023). None can be matched
  to a quarterly issue date without inventing values.
* **Different indicators.** Food secure ≠ the complement of another survey's insecurity class; severe ≠
  moderate-to-severe; subsistence incidence is **income-based food poverty**, not experienced food insecurity.
* **Different instruments.** FNRI 2015 uses HFIAS (9 items, 30-day recall, rule-based categories). The 2023 NNS uses
  FIES (8 items, 12-month recall, Rasch scale). The ENNS 2018–2021 instrument per province could not be confirmed. The
  ENNS severe values split into 1.5–2.4 % (2021) and 7.9–13.7 % (2018–2019), which looks like a change of scale between
  rounds. They must not be compared without the FNRI tables.
* **No provincial panel.** Each province has one ENNS year (Laguna 2018, Quezon and Rizal 2019, Batangas and Cavite
  2021) and one HFIAS year (2015). That gives at most two points per province, on different instruments.
* **Uncertainty.** FNRI 2015 provincial 95 % CIs are ±4–6 pp and overlap across provinces. ENNS values have no
  published SE in the workbook.

Supervised provincial forecasting needs repeated, comparable provincial outcomes over time. The workbook has none,
so **no provincial forecasting model was trained**. Nothing was interpolated or converted to household records, and
no HIGH/LOW thresholds were invented.

## 3. What the records are used for

* FNRI 2015 HFIAS provincial values serve as a **descriptive cross-check** of the LGU priority layer
  (GENERALIZATION_AND_BIAS_AUDIT.md), not for training.
* PSA subsistence incidence is a **food-poverty context indicator**, kept separate from food insecurity.
* The 2023 FIES regional value (19.1 %, CI 17.0–21.1) is a **regional benchmark** on its own instrument.

## 4. What would make provincial forecasting possible

The FNRI ENNS 2018–2021 and NNS 2023 household public-use files. With survey weights and design variables,
`app/fi_labels/hfias.py` can rebuild weighted provincial HFIAS/FIES estimates with SEs. Even then there would be
about one point per province per year, which is enough for cross-sectional validation but not for quarterly
forecasting. The files are public but blocked from this network by the FNRI firewall. They were not requested
(directive); they can be downloaded from another network into `backend/data/fi_labels/raw/fnri/puf/`.
