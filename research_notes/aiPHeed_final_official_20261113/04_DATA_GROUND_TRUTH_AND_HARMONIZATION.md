# 04 — Public dataset and ground-truth audit; FNRI harmonisation and uncertainty (deliverables 4, 5)

The full audit is in `../aiPHeed_final_reliability_20261113/01_DATA_AUDIT.md`, with `GT_*.csv`. This report summarises it, corrects the 2021 SE assumption, and lists the predictor datasets.

**ENNS 2022 is excluded entirely**, as the brief requires. The earlier ENNS 2022 seals (`4ad9267f`, `71ebe142`) are not used for anything here.

## 1. Ground truth: FNRI provincial HFIAS

| Round | Provinces used | HIGH | Standard error | Use |
|---|---|---|---|---|
| NNS 2013 | 78 | 54 | Not printed; approximated (deff 3.17) | Anchor history |
| FNRI 2015 | 78 | 54 | Derived from printed category SEs | Training |
| ENNS 2018 | 22 (18 areas excluded) | 8 | Printed 90 % CIs | Fold 1, then training |
| ENNS 2019 | 25 (14 excluded) | 13 | Printed 90 % CIs | Fold 2, then training |
| ENNS 2021 | 25 (12 excluded) | 4 | **Not published** | Fold 3, then training |

- The 44 exclusions are listed with reasons in `GT_excluded_areas.csv`: cities/HUCs with no provincial predictors (36), decks printing the any-level headline only (5), and provinces absent from FNRI 2015 (3).
- **Harmonisation:** every round uses the same instrument (HFIAS, 9 items, 30-day recall, FNRI scoring after Coates et al. 2007). Moderate + severe is the sum of the printed categories.
- **Coverage caveat:** ENNS is a rolling survey covering a different subset of provinces each year. The 2019 subset was poorer than 2018, so round-level shifts are partly sample composition.

## 2. What publicly accessible FNRI data can and cannot give

| Item | Available? | Detail |
|---|---|---|
| Household responses | **No** | FNRI public-use-file pages are blocked from this network, and microdata need a data-sharing agreement. No public HFIAS microdata were found |
| Sampling weights | **No** (embedded only) | Published percentages are FNRI's own weighted estimates but cannot be re-derived |
| Provincial SEs | 2015 (derived), 2018/2019 (printed CIs) | 2013 approximated; **2021 not published** (Heat Map gives percentages only) |
| Comparable definitions | Yes, 2013–2021 | HFIAS throughout. NNS 2023 publishes FIES, a different instrument, so it is not a label |
| Valid provincial coverage | Partial | 22–25 provinces per ENNS round; CALABARZON has 5 rows in total, all LOW |

## 3. Correcting the unsupported 2021 SE assumption
The 3.0-point SE for 2021 was an assumption. It is replaced by a sensitivity analysis over the empirical range of the printed 2018/2019 provincial SEs (`scripts/se2021.py`, `evidence/GT_se2021_sensitivity.csv`):

| Assumed 2021 SE (pp) | Labels within 1.96 SE of 50 % | of which HIGH | Expected wrong-side labels | FINAL L1 2021 accuracy, label-uncertainty weighted |
|---|---|---|---|---|
| 1.30 (min observed) | 3 | 0 | 0.6 | 0.855 |
| 2.52 (median) | 4 | 0 | 1.0 | 0.840 |
| 2.92 (75th percentile) | 4 | 0 | 1.1 | 0.836 |
| 3.00 (old assumption) | 5 | 0 | 1.2 | 0.835 |
| 4.47 (max observed) | 11 | 2 | 1.8 | 0.821 |
| 5.00 (beyond observed) | 13 | 3 | 2.0 | 0.815 |

**Result:**
- Within the observed SE range, the four 2021 HIGH labels are not ambiguous. The 2021 misses are model errors, not label noise.
- Label uncertainty moves 2021 accuracy by at most about 4 points.
- Across all three test rounds, about 3.5 of 72 labels are expected to be on the wrong side of 50 % from sampling error alone. **The labels are treated as uncertain measurements, not as unquestionable truth.**

## 4. Predictor datasets (public; resolution and timing)

| Source | Indicators | Resolution | Timing used | Limitation |
|---|---|---|---|---|
| PSA CPI (OpenSTAT) | food/rice CPI, relative to national | Province, monthly | Published before the origin | Prices move largely nationally |
| PSA/BAS prices | wholesale rice, farmgate palay, fish | Province | 3-month window, 3-month lag | Gaps (missing-value flags) |
| PSA palay/corn production (2E4EVCP0) | by crop and combined, 4 quarters vs 4 before | Province, quarterly | 45-day release rule | **By-crop series refreshed 11-13** (it was stale at 2023-Q4) |
| PSA regional accounts | GRDP per person | **Region**, annual | Year Y usable from Y+1 Q3; 2024–25 estimated | Regional only |
| PSA poverty statistics | poverty, subsistence incidence | Province, triennial (2015/18/21/23) | Latest released | Slow-moving |
| PSA census | density | Province | Census + 2 years | Static |
| PSA LFS | unemployment | National/regional before 2022 | Latest released | Provincial LFS from 2022 can be used prospectively only |
| BSP remittances | — | National | — | **Not a model input** (no provincial series) |
| NASA POWER, IBTrACS, NOAA ONI | rain/soil anomalies, typhoon exposure, ENSO | Province centroid / global | As-of | Exposure is nearly static per province |
| News corpus (NLP) | XLM-RoBERTa food-stress signals, FSSI | Province or area (63 % area fallback) | 3-month window before the issue | Sparse at provincial level |
| PSA/FNRI FIES 2023, SWS hunger | — | Region / area | Context only | Not labels |
