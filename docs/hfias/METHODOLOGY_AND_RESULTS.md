# HFIAS provincial food-insecurity model (hfias-1.0): methodology and locked results

Code `backend/app/hfias/` · data `backend/data/hfias/` · protocol lock `backend/data/hfias/out/PROTOCOL_LOCK.json`
(protocol sha `5503093907c6…`, locked before any test score) · results `study_insecure.json`, `study_mod_sev.json` ·
tests `backend/tests/unit/test_hfias.py` · gate `backend/data/registry/gate_results/hfias-1.0.json`.

**Status: REJECTED by the release gate (2026-11-03). Not on the dashboard; no public route serves it.**

## 1. The decision that changed

Earlier engines learned regional SWS hunger or price proxies, because provinces were thought to have only one food-security
measurement. That was wrong. FNRI measured household food insecurity with the HFIAS in every province twice: the
2015 Food Security Survey and one ENNS round (2018 or 2019; the ENNS rolling design surveys each province once). The
provincial ENNS reports are public FNRI uploads. eNutrition is unreachable from this network (curl, browser and an
outside fetch all fail), so the 76 reports were read from Internet Archive captures of the same URLs. Each file's
source URL, capture time and sha256 are in `backend/data/hfias/raw/MANIFEST.csv`.

## 2. Target and data

| Item | Value |
|---|---|
| Primary target | Share of households food insecure (HFIAS, any level), the headline FNRI indicator, % |
| Secondary target | Moderately or severely food insecure (HFIAS), % (33 of 38 decks print the categories) |
| 2015 | FNRI 2015 FSS Appendices 1–4: 78 provinces with n, SE, CI (parsed; CALABARZON matches the verified values) |
| ENNS | 38 reports for 2018 (tables with 90% CI) and 38 for 2019 (slide decks; 5 print the headline only) |
| Panel | 52 provinces measured in both (22 in 2018, 30 in 2019); cities and NCR towns excluded (no 2015 province); Davao Occidental and Dinagat Islands created after 2015 |
| Never mixed | FIES values printed in the 2019 decks are kept in a separate column and never used in the HFIAS target |
| Workbook check | The owner workbook's ENNS "moderate-to-severe" values equal FNRI's HFIAS *moderate* category (Laguna 2018 18.3, Quezon 2019 30.3, Rizal 2019 27.5): a mislabel in the RDP results matrix |

Features (as of the issue date; release rules tested): logit of the 2015 value; 2015 poverty and subsistence (V1);
change in provincial rice, food-group and fish CPI since 2015 (A1–A3; PSA annual provincial CPI, public 15 Feb);
change in palay+corn and fisheries production (C3, C4; public 45 days after the quarter); change in SWS hunger in the
province's SWS area (H1). Not testable nationally with public data on file: C1–C2 (ENSO is the same for every
province; no provincial typhoon series), E1–E2 (no provincial labour or remittance series 2015–2019), N1 (the news
corpus covers CALABARZON only).

## 3. Protocol (locked before scoring)

- Primary test: train on the 22 provinces surveyed in 2018 and test on the 30 surveyed in 2019 (later, different
  provinces). Secondary: leave-one-island-group-out.
- Candidates: B0 no change, B1 mean change, B2 mean level, M1 ridge, M2 random forest, M3 gradient boosting, M4 LightGBM.
- Selection: lowest leave-one-out MAE inside the 2018 training rows (selected M1 ridge, LOO MAE 6.4 pp). The test was
  not used.
- HIGH = province ≥ the national value of the same round (53.9% in 2018, 64.1% in 2019).
- Acceptance: MAE ≤ 5 pp and below the best baseline; 90% coverage 0.80–0.97; accuracy ≥ 0.75; balanced ≥ 0.70;
  HIGH recall ≥ 0.60; ECE ≤ 0.10; n ≥ 20 with ≥ 10 HIGH.
- Lead k: issue k quarters before Q1 of the survey year.

## 4. Results (primary target, n test = 30, 19 HIGH)

| Lead | Selected M1 ridge MAE | No-change MAE | Accuracy | Balanced | HIGH recall | ECE | Passed |
|---|---|---|---|---|---|---|---|
| 1 | 10.37 | 7.87 | 0.67 | 0.62 | 0.79 | 0.22 | no |
| 2 | 9.41 | 7.87 | 0.67 | 0.62 | 0.79 | 0.16 | no |
| 3 | 8.90 | 7.87 | 0.60 | 0.55 | 0.74 | 0.24 | no |
| 4 | 7.81 | 7.87 | 0.67 | 0.60 | 0.84 | 0.19 | no |

- No candidate reaches MAE ≤ 5 pp; the best test MAE of any candidate is the no-change baseline (7.87).
- Unselected candidates reach 0.80 accuracy at single leads (gradient boosting, Lead 2: BA 0.77, ECE 0.07). They
  are not adopted: choosing them now would select on the test set.
- Secondary (moderate or severe; n = 25, 14 HIGH): the selected random forest has MAE 10.99 vs 8.83 no-change,
  accuracy 0.68 at Lead 1. It fails.
- Island-group CV (Lead 1, ridge): pooled MAE 13.7 pp.
- Lead 1 ablation (ridge, change in test MAE when the group is dropped): lag +1.53, poverty +0.51, H1 +0.13,
  market −0.15, climate −0.56. Poverty, the 2015 level and H1 help slightly; market and C3–C4 add noise.

**Why it fails:** the national level moved from 53.9% (2018 round) to 64.1% (2019 round). That round-level shift is
larger than the provincial differences the features explain. A model trained on one round cannot anticipate it, and
two rounds are too few to learn round-to-round dynamics.

## 5. 75% objective and horizon

- 75% accuracy on valid, independent food-insecurity outcomes: **not achieved**. The selected model scores 0.67
  (30 provinces).
- Maximum reliable horizon: **none established**. No lead passes.
- What would change this: a third HFIAS or FIES provincial round, such as the FNRI 2021 ENNS provinces or the 2023 NNS.
  It would give a second round-to-round change to learn from. These files were not in the Internet Archive capture
  and could not be reached at FNRI.
