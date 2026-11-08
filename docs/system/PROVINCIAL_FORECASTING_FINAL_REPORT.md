# aiPHeed provincial forecasting: final report (2026-11-04)

**Supersedes.** `FINAL_DECISION_REPORT_20261104.md` wherever they differ. The change is new evidence: a third
provincial HFIAS round was recovered (FNRI NNS 2013) and tested once under protocol E141-P1 (`docs/e141/PROTOCOL.md`,
lock written before scoring).

**Preserved, not modified:** E137–E140 code, locks, results and seals, and the registry production pointer (`null`).

## 1. What changed the evidence: the recovered 2013 provincial round

| Item | Finding |
|---|---|
| Source | DOST-FNRI, *Philippine Nutrition Facts and Figures 2013: Food Security* (8th NNS), Appendix 33 "Food Security Status by Province". Read from the Internet Archive copy of `fnri.dost.gov.ph/images/facts_and_figures/Food-Security-2013.pdf`; sha256 in `backend/data/e141/raw/MANIFEST.csv`. |
| Instrument | HFIAS, 9 items, 30-day recall, Coates categories (stated in the report). Same as FNRI 2015 and ENNS 2018/2019. |
| Coverage | 78 provinces (identical list to 2015), n = 35,635 households. Fieldwork 19 June – 4 December 2013, continued 16 February – 15 April 2014. |
| National reference | moderate-or-severe 50.8 % (2015: 53.8 %; ENNS pooled 2018–19: 42.8 %) |
| Uncertainty | SEs are not printed. They are approximated with the 2015 median design effect (3.17) and flagged in every row. |
| Caveat | Typhoon Haiyan (8 November 2013) struck during fieldwork |
| Other sources searched | FNRI 2021 ENNS provincial results; FNRI 2023 NNS; PSA SDG 2.1.2 FIES. Results below. |

**What the other searches found** (FNRI eNutrition and main-site archives, every URL listed, 2026-11-04):
* **2021 ENNS:** only national files.
* **2023 NNS:** regional estimates only.
* **2018 ENNS food-security PDF:** national.
* **FIES:** regional 2023 only.

**What the recovery adds.**
* The provincial panel grows from 125 to 203 province-rounds.
* There are now **two** survey-to-survey transitions for the 78 provinces measured in 2013 and 2015, plus 47 later
  ENNS rows.
* 2013 was never seen by any model.

## 2. Provincial target (audited, retained)

**What is measured** (one row per province and survey):
* HFIAS moderate-or-severe, relative to the national value of the same round;
* as a relative logit, with its survey SE;
* with a soft label q, and a status of ELEVATED, LOWER, NOT_DISTINGUISHABLE or INSUFFICIENT;
* no interpolation, and no regional values in province rows.

**Two quantities, kept apart in code and API.**
1. **Current provincial relative-risk estimate.** P(the province's measured food insecurity would be above the
   national level), from the latest public evidence.
2. **Next-round provincial forecast.** The same probability for the province's next measured round, issued before
   that round from information public at issue.
   * This is what the rolling-origin test evaluates (Lead 1 = issued one quarter before the round's reference
     quarter).
   * There is no quarterly provincial outcome, so a quarter-to-quarter forecast is **not** identifiable. The
     display-quarter output is quantity 1 carried to the display quarter, and it says so (`claim` field).

## 3. Methods compared (on the actual data)

| Method | Assessment |
|---|---|
| A. Pooled provincial learning (all Philippine provinces, CALABARZON reported separately) | **Used.** 78 provinces × 3 rounds; CALABARZON rows reported on their own. |
| B. Hierarchical or partial pooling | Tested in E138 (HIER). It helps only when same-survey neighbours are known (LOPO); with no region information it reduces to logistic regression. Kept as a reference in the evidence base. |
| C. Survey-weighted small-area estimation from microdata | **Not feasible.** No HFIAS/FIES household microdata are publicly available (the FNRI PUF pages are blocked from this network; FAO microdata require an application, which the owner has ruled out). Direct province estimates as published are used, with their SEs. |
| D. Dynamic state-space with quarterly indicators | **Not identifiable.** E138 (within-province change) and E140/E141 (quarterly-indicator ablation) show the time-varying indicators carry no measured information about provincial change, so a latent quarterly state would be driven by the model's assumptions, not by data. |
| E. LightGBM on the provincial panel | **Used.** E140 LGBM-AUTO (nested choice of linear-leaf or compact constant-leaf trees, no zero-tree option), retrained on the three rounds (E141 candidate, 600 trees). |

## 4. Results (E141, locked, run once)

**U. Untouched 2013 round** (78 provinces, 35 decisive: 28 elevated, 7 lower). Models are trained exactly as the
served E140 candidate and predict 2013 from features as of 2013.

| Model | EB | AUC [95 % CI] | Accuracy | HIGH recall | Precision | ECE | Confusion (TP / FP / TN / FN) |
|---|---|---|---|---|---|---|---|
| **LightGBM (E140)** | **0.158** | 0.936 [0.70, 1.00] | 0.829 | 0.821 | 0.958 | **0.139** | 23 / 1 / 6 / 5 |
| Linear prior | 0.158 | 0.990 | 0.943 | 0.964 | 0.964 | 0.080 | 27 / 1 / 6 / 1 |
| Ridge, all | 0.163 | 0.944 | 0.914 | 0.929 | 0.963 | 0.096 | — |
| PSA-only (poverty logistic) | 0.162 | 0.990 | 0.914 | 0.964 | 0.931 | 0.079 | — |
| National base rate | 0.227 | 0.500 | 0.800 | 1.000 | 0.800 | 0.091 | — |

* **LightGBM vs the national base rate:** −0.069 [−0.110, −0.025]. It ties the prior and PSA-only.
* **What this establishes:** independent, measured-outcome validation that indicator-based provincial relative-risk
  estimates rank provinces correctly in a period no model saw.
* **What it does not establish:** LightGBM is miscalibrated there (ECE 0.14), and the simple models do as well or
  better.

**R. Rolling-origin survey-round forecasting** (Lead 1; 125 target rows; 62 decisive).

| Origin | Train on | Predict |
|---|---|---|
| O1 | 2013 | 2015 |
| O2 | 2013 + 2015 | 2018 |
| O3 | 2013 + 2015 + 2018 | 2019 |

| Model | Pooled EB | AUC | Accuracy | HIGH recall | Precision | ECE |
|---|---|---|---|---|---|---|
| **LightGBM** | 0.194 | **0.964** [0.90, 1.00] | **0.903** | 0.875 | **0.972** | **0.040** |
| Region's previous level | **0.190** | 0.926 | 0.806 | 0.825 | 0.868 | 0.063 |
| Linear prior | 0.203 | 0.917 | 0.774 | 0.775 | 0.861 | 0.085 |
| Ridge, all | 0.203 | 0.930 | 0.806 | 0.750 | 0.938 | 0.072 |
| PSA-only | 0.206 | 0.908 | 0.790 | 0.800 | 0.865 | 0.066 |
| Persistence (previous round) | 0.207 | 0.856 | 0.806 | 0.850 | 0.850 | 0.131 |
| Logistic, all | 0.229 | 0.898 | 0.758 | 0.700 | 0.903 | 0.155 |
| National base rate | 0.250 | 0.451 | 0.645 | 1.000 | 0.645 | 0.069 |

**LightGBM − reference, expected Brier score [95 % cluster-bootstrap CI].**

| Reference | Difference |
|---|---|
| Persistence | −0.013 [−0.040, +0.014] |
| Region's previous level | +0.004 [−0.029, +0.042] |
| Linear prior | −0.010 [−0.023, +0.006] |
| PSA-only | −0.012 [−0.031, +0.005] |
| Logistic | −0.035 [−0.071, +0.003] |
| National base rate | **−0.056 [−0.110, −0.009]** |

**By origin (EB).**

| Origin | LightGBM | Persistence | Region's previous level |
|---|---|---|---|
| O1 | 0.224 | 0.214 | 0.212 |
| O2 | 0.147 | 0.207 | 0.140 |
| O3 | 0.141 | 0.187 | 0.164 |

* LightGBM confusion (pooled): TP 35, FP 1, TN 21, FN 5.
* Trees selected: O1 linear trees × 30; O2 constant-leaf × 300; O3 constant-leaf × 100.

**Contributor groups (ablation on the R folds, removing one group from LightGBM).**

| Group | Effect on EB [CI] | Verdict |
|---|---|---|
| Poverty and vulnerability | +0.020 [−0.013, +0.056] | largest effect, not significant |
| Geography (island group) | +0.013 [−0.002, +0.030] | not significant |
| Measured history | −0.002 | no added information |
| Market | −0.001 | no added information |
| Climate | −0.003 | no added information |
| All six time-varying (quarterly) indicators | −0.004 [−0.013, +0.005] | no added information |
| Employment and remittances | — | no provincial series; not testable |
| News and NLP | — | no news outside CALABARZON for 2013–2019; not testable |

**CALABARZON (8 measured target rows in R).**
* Every row is LOWER or not distinguishable from national.
* LightGBM puts Quezon highest in 2015 (0.52; measured not distinguishable) and in 2019 (0.41; q = 0.66).
* It puts Laguna lowest (2018: 0.08; measured LOWER).
* On the untouched 2013 round, the model ranks Quezon (0.46) and Batangas (0.42) above Cavite (0.09), Laguna and
  Rizal (0.18). Measured: Quezon and Rizal not distinguishable; the other three LOWER.

**Gate E141-P1.**
* **Passed:** U1, U2, R1 classes, R1 calibration, R1 not worse than the best simple model.
* **Failed:**
  * U3 (calibration on 2013);
  * R1 vs persistence;
  * R1 vs the region's previous level;
  * R2 (persistence wins at O1);
  * R3 (trees vs prior).
* **The survey-to-survey forecast is NOT validated.** LightGBM trees are NOT justified over the linear prior.

## 5. What can now be claimed

1. **Validated independently:**
   * Provincial food-insecurity relative risk can be estimated from official indicators. All indicator models reach
     AUC 0.94–0.99 on an untouched round and beat the base rate.
   * This is the strongest result aiPHeed has, and it is provincial.
2. **Not validated:**
   * forecasting the next measured round better than the previous survey or the region's previous level;
   * any quarter-to-quarter provincial forecast;
   * LightGBM being better than the linear prior.
3. **No incremental information:** market, climate, history-beyond-poverty and every quarterly indicator.

## 6. System state

* **Candidates, admin only, flagged `CANDIDATE_NOT_APPROVED`:**
  * E140 (two rounds);
  * **E141 (three rounds, 600 trees).** Display quarter 2027-Q1:

    | Province | P(elevated) | 90 % interval | Class |
    |---|---|---|---|
    | Laguna | 0.03 | 0.03–0.47 | LOW |
    | Cavite | 0.05 | 0.04–0.66 | UNCERTAIN |
    | Batangas | 0.10 | 0.05–0.52 | UNCERTAIN |
    | Rizal | 0.14 | 0.07–0.61 | UNCERTAIN |
    | Quezon | 0.25 | 0.11–0.55 | UNCERTAIN |

  * Explanations are exact TreeSHAP. Poverty, history and geography lower the risk for all five provinces.
  * 142 LGU priority rows, carrying the candidate status.
* **Public:** `/api/v1/final/food-insecurity/outlook` returns `validation_pending` with each candidate's own check
  count. The dynamic quarter is in `/api/v1/quarters`.
* **Prospective register** (`data/registry/prospective_provincial.jsonl`): four write-once seals (E138, E139, E140,
  E141). Scoring: `python -m app.registry.prospective_provincial score <round.csv>` against NAT, PERS and REGPREV.
  The template is `data/registry/provincial_round_TEMPLATE.csv`.
* **Production decision: CANDIDATE IMPLEMENTED — VALIDATION PENDING.**
  * The production pointer stays `null`.
  * The pre-registered forecast gate failed. Its structural-estimation checks (U1, U2) passed, but no release rule for
    a structural-only product was registered before the run, so none is applied after it.

## 7. Exact remaining evidence

1. **A provincial HFIAS round after 2019** (FNRI ENNS 2021 provincial tables, or a later NNS with provincial HFIAS).
   * Fields: province, p, se_p, national ref, instrument.
   * It scores the four sealed models against persistence and the region's previous level immediately.
   * The forecast claim needs LightGBM's EB below both, with CI excluding 0, on at least 20 provinces.
   * Holder: DOST-FNRI (the ENNS 2021 provincial reports are not online).
2. **Design-based SEs for 2013:** the printed table has none. FNRI's 2013 NNS technical report, or its microdata,
   would replace the approximation.
3. **For a quarterly provincial forecast:** a provincial food-insecurity measurement at least every quarter (none
   exists in the Philippines today).
4. **For employment and news as provincial inputs:** provincial labour and remittance series covering 2013–2019, and a
   nationally geocoded news archive covering the survey years.
