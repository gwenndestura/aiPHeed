# E141: a third provincial HFIAS round (FNRI NNS 2013). Protocol E141-P1

**Code and lock.**
* Code: `backend/app/e141/` (`nns2013.py`, `acquire.py`, `panel.py`, `evaluate.py`).
* Lock: `backend/data/e141/out/PROTOCOL_LOCK.json`, holding the hashes of this file, `panel.py`, `evaluate.py`,
  `nns2013.py` and the thresholds.
* The lock is written before any E141 model is scored on real outcomes. The pre-lock smoke test used shuffled labels.

**Earlier work is untouched.** E137–E140 code, locks, results and seals are imported read-only. The served E140
candidate is evaluated exactly as trained.

## 1. The recovered evidence

**Source.**
* DOST-FNRI, *Philippine Nutrition Facts and Figures 2013: Food Security* (8th National Nutrition Survey).
* Appendix 33, "Percentage Distribution of Food Security Status by Province, Philippines: 2013".
* URL: https://www.fnri.dost.gov.ph/images/facts_and_figures/Food-Security-2013.pdf, read from the Internet Archive
  (`web.archive.org/web/2020id_/…`).
* sha256 in `backend/data/e141/raw/MANIFEST.csv`.

**Comparability with FNRI 2015 and ENNS 2018/2019.**
* Same instrument: HFIAS, 9 items, 30-day recall, Coates et al. (2007) categories. The report states that HFIAS
  replaced the Radimer/Cornell tool from the 2013 NNS.
* Unit: household.
* Sample: PSA/NSO master sample (2009 LFS), 80 provinces, n = 35,635.
* Fieldwork: 19 June – 4 December 2013, continued 16 February – 15 April 2014. Reference quarter: 2013-Q3.
* National value: secure 34.1, mild 15.1, moderate 34.1, severe 16.7, so moderate-or-severe = 50.8 %.
* 78 provinces parsed, with category sums 99.99–100.01. They match the FNRI 2015 province list exactly. Isabela City,
  Cotabato City and the NCR districts are excluded.

**Standard errors.**
* **Not printed.** They are approximated as sqrt(deff × p(1−p)/n), with deff = 3.17, the median FNRI 2015 province
  design effect for the same split.
* This is an assumption. It is flagged in every row (`se_imputed = True`).

**Known caveat.** Typhoon Haiyan (8 November 2013) struck during fieldwork. The Eastern Visayas values may partly
reflect its immediate effects.

**Disclosure.** While parsing, the 2013 table was viewed, including the CALABARZON rows. The models scored in test U
were fixed before this, so viewing could not change them. The test R architectures are E140/E139's, unchanged.

## 2. Target

Unchanged (E137): HFIAS moderate-or-severe relative to the national value of the same round, as a relative logit
with SE and a soft label. For 2013 the reference is 50.8 % (SE 0.5).

## 3. Tests

**U: untouched round (structural risk estimation).**
* The served E140 candidate and its references are trained exactly as served: E140 rows, Lead 1.
* They predict the 78 provinces of 2013, using features as of 2013 at Lead 1, with no earlier survey.
* **No model in this project has used 2013.** This is the first fully independent measured-outcome test of the
  provincial risk models.
* It tests generalisation to an unseen period, not forecasting (2013 precedes the training rounds).

**R: rolling-origin survey-round forecasting at Lead 1.** Issued one quarter before the target round's reference
quarter, with the previous measured round known.

| Origin | Train on | Predict |
|---|---|---|
| O1 | 2013 | 2015 (78 provinces) |
| O2 | 2013 + 2015 | 2018 (22) |
| O3 | 2013 + 2015 + 2018 | 2019 (25) |

* LightGBM is E140's LGBM-AUTO, with nested inner selection inside each training set.
* **References:** linear prior, ridge, logistic (all features), PSA-only (poverty logistic), persistence (previous
  round), REGPREV (the region's previous round), NAT.
* An NLP-only baseline **cannot** be built: there is no news outside CALABARZON for 2013–2019.
* **Disclosure:** the 2015 and ENNS targets were examined in E137–E140 development, so R is development evidence with
  a new, untouched earliest round.

**Group ablation (R folds).** Each run removes one group from LightGBM:
* market;
* climate;
* poverty;
* history;
* geography (island group);
* the six time-varying "quarterly" indicators.

## 4. Pre-registered criteria (`evaluate.T`)

**Test U.**

| Check | Rule |
|---|---|
| U1 | LightGBM EB below NAT and below PSA-only |
| U2 | AUC ≥ 0.75 with region-bootstrap 95 % lower bound ≥ 0.60 |
| U3 | ECE ≤ 0.10 |

**Test R** (pooled over O1–O3).

| Check | Rule |
|---|---|
| R1 | EB below persistence (95 % CI upper bound < 0) and below REGPREV (CI upper bound < 0); not worse than the best simple model by more than one bootstrap SE; AUC ≥ 0.75; HIGH recall ≥ 0.60; precision ≥ 0.60; ECE ≤ 0.10 |
| R2 | EB below persistence at every origin |
| R3 | **LightGBM trees justified:** EB below the linear prior, with CI upper bound < 0 |

**Decisions.**
* **Survey-to-survey provincial forecast validated (development + untouched):** U1–U3, R1 and R2 all pass.
* **LightGBM adoption** additionally requires R3. If R3 fails, the validated forecasting model is the best simple
  model, and LightGBM stays a candidate.
* **What any validation covers:** forecasts of a province's *next measured* relative position, issued one quarter
  before the measurement. It does not cover quarter-to-quarter change between surveys.
