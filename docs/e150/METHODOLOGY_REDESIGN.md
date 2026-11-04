# E150 methodology redesign

**Experiment:** E150, branch `pfi/e150-risk-scoring`. **Protocol:** `PROTOCOL.md`, locked before any metric, with two fix-only deviations. **Production:** unchanged.

## 1. Why earlier forecasts were weak (measured, `data/e150/out/diagnosis.json`)

| Possible cause | Finding | Verdict |
|---|---|---|
| Too few training observations | 532 rows, but only **125 independent outcomes across 3 rounds** | **Main cause** |
| Unreliable labels | **42 % of measured change variance is survey noise** | **Main cause** |
| Excessive reliance on persistence | Change correlates −0.45 with position relative to region, which is largely regression to the mean | **Real, now modelled** |
| Weak or stale inputs | Provincial CPI was annual and stale after 2018; within-round correlation of inputs with change at most 0.13 | **Real, partly fixed** |
| Inadequate temporal training variation | Target is identical across leads of one outcome; 2 to 3 rounds cannot teach time dynamics | **Real, addressed by learning response from SWS** |
| Excess regularization | Static because trees find nothing to split on; 71 % of quarter changes under 0.01 logit | Secondary |
| Wrong feature timing | Release rules applied | Not the cause |
| Poor geographic differentiation | Within-CALABARZON signal is genuinely weak | Real, unresolved |

## 2. Research basis

Full evidence database: `docs/e145/LITERATURE_EVIDENCE.csv`.

| Method | Source | Experimental support | Decision |
|---|---|---|---|
| Survey-anchored ML, trained where surveys exist | Martini et al. 2022, 10.1038/s43016-022-00587-8; Lentz et al. 2019, 10.1016/j.worlddev.2019.06.008 | Measured on held-out surveys | **Used** |
| Area-level shrinkage for noisy survey estimates | Fay and Herriot 1979, 10.1080/01621459.1979.10482505; Efron and Morris 1973, 10.2307/2284155 | Long-established | **Used** |
| Spatio-temporal small-area models | Marhuenda et al. 2013, 10.1016/j.csda.2012.09.002; Kopp et al. 2026, arXiv 2608.14314 | Yes, with repeated rounds per area | **Partly:** too few rounds for a full model |
| Mixed-frequency aggregation | Ghysels et al. 2006, 10.2139/ssrn.885683 | Macroeconomics | **Used** as since-anchor inputs |
| Learning from a cheap frequent signal to inform a sparse accurate one | Kennedy and O'Hagan 2000, 10.1093/biomet/87.1.1 | Computer experiments; **my application to food security is new and unproven** | **Tried** as the SWS response |
| Conformal intervals | Lei et al. 2018, 10.1080/01621459.2017.1307116 | Theory and simulation | **Used** (residual quantile) |
| Proper scoring, calibration | Gneiting and Raftery, 10.21236/ada454828 | Standard | **Used** |
| TreeSHAP | Lundberg et al. 2020, 10.1038/s42256-019-0138-9 | Standard | **Used**, descriptive |
| Deep sequence models | Herteux et al. 2024 | Need daily labels | **Rejected:** not enough data |
| Heavy ensembling | n/a | Would overfit 125 outcomes | **Rejected** |

Papers marked by DOI were verified to exist through Crossref. Not all were read in full; the database marks how far.

## 3. Selected structure

    logit(prevalence) = shared level + province structural level + shrunk measured deviation + loading × quarterly response + LightGBM residual

Each part addresses a diagnosed problem:

* **Shared level** corrects for rounds sampling different provinces.
* **Structural level** (LightGBM, cross-fitted by region) gives each province a prior from a model that never saw its region.
* **Shrunk deviation** handles survey noise and regression to the mean.
* **Quarterly response** is learned on 147 measured SWS area-quarters, then applied to each province's inputs. SWS is never a provincial label.
* **LightGBM residual** carries the five trigger groups, with theory-signed monotone constraints.

## 4. Approach A versus B

| Lead 1 | A, prevalence (A-H), pool n = 72 | B, risk score, pool n = 72 |
|---|---|---|
| Accuracy | 0.847 | 0.806 (identical to always-HIGH) |
| LOW recall | 0.286 | **0.000** |
| AUC | 0.786 | 0.621 |
| Brier | 0.119 | 0.153 |
| Calibration slope (measured on predicted) | 1.05 | n/a, not prevalence |

**Decision: Approach A.** On development rows its slope (1.10, interval 0.69 to 1.37) includes 1 and coverage is 0.87, which meets the pre-set test, so its percentages may be read as estimated any-level prevalence. The 50 % line therefore applies to a matching scale. B never identified a LOW province, so a separate risk index adds nothing here.

## 5. What the evidence selected, and the problem it creates

The locked rule selected **A-H**, because the quarterly response and residual slightly worsened Brier on 2018 and 2019 (0.107 for A-H, 0.110 A-Hh, 0.124 A-G).

**A-H does not use market, climate, employment or remittance inputs, and gets no quarterly signal from the response (survey-fitted loading 0).** That conflicts with your thesis requirements. Only **A-G** uses all five groups (see `OBJECTIVE_COMPLETION_MATRIX.md`). Which to carry forward is your decision, and it should be fixed before the next test.

## 6. Defect found after scoring

The structural level uses absolute poverty, which fell nationally by 2023, on top of a shared trend that already declines. This double-counts, and it explains the collapse at leads 3 to 6 on 2021 and very low live values. A post-hoc correction (`app/e150/posthoc_relative.py`, relative inputs) gives more plausible live values (40 to 44 %) but worsens LOW recall on the pool (0.07). It is **not adopted**, and every row it was scored on has been read, so it can't be validated here.
