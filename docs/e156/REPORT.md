# E156: audit of the E151 model, maximum reliable lead, and one locked candidate

Started at commit `44531bcb` on `pfi/e151-news-quarterly`. Production and the dashboard are unchanged. Every result below is retrospective: all rows were read by earlier work.

## Verdict

* **Lead 1 is the mandatory horizon and it does not yet pass the reliability criteria,** so the maximum reliable lead is **0**. It passes four of six criteria and fails C1 (accuracy not clearly above always-LOW at the effective sample size) and C4 (overconfident probabilities).
* **No leakage found.** With every input after the issue quarter replaced by noise, all 72 forecasts are unchanged.
* **The one locked candidate fixes calibration at every lead, but lowers accuracy (0.681) and Brier, so it is not adopted.**
* **75 % at Lead 1 is not reached honestly.** With about 46 effective independent rows, a credible 75 % needs roughly 78 % observed accuracy.

## 1. What works and what does not

| Area | Working | Not working | Where |
|---|---|---|---|
| Temporal validity | Every input used only as of its issue date; leakage test passes | Some release delays are assumptions (CPI 3 months, surveys 6 quarters) | `app/e150/model.py`, `app/e147/features.py`, `app/e151/features.py` |
| Survey anchor | Gives most of the skill over the old survey | Carries the 2021 national level forward; Batangas and Quezon read about 12 to 13 points below their surveys | `app/e151/prov.py` Hier2, Store2 |
| LightGBM adjustment | Beats persistence at Leads 1 to 5 on Brier | Overconfident (slope interval excludes 1); barely changes ranking between provinces | `prov.Res2` |
| Employment, remittances | Reach the model | **Zero contribution**; see section 3 | `app/e148/panel.py` |
| News | Pipeline built; used as inputs | No incremental value (E151, E154, E155) | `app/e151/*` |
| Dashboard | — | **E151 is not wired to any API route**; the live site serves an older model | `backend/app/api` has no E15x reference |

## 2. Leakage, sample size, generalisation

| Check | Result |
|---|---|
| Inputs after the issue quarter replaced with noise | 0 of 72 forecasts change: **pass** |
| Error variance shared within a round and region | 73 % (6 % shared across the whole round) |
| Effective independent rows | **about 46 of 72**; Lead 1 accuracy 95 % range 59 % to 85 % |
| Province held out of the LightGBM fit | 69.4 % vs 72.2 %, Brier 0.142 vs 0.137: a small loss, so the adjustment is not memorising provinces |

The first leakage run corrupted the issue quarter itself and changed every forecast. That quarter's panel row holds values already lagged to the issue date, so it is available by design; corrupting only later quarters changed nothing.

## 3. Why employment and remittances contribute nothing

* Every employment and remittance input is **the same for all provinces in a quarter** (national series).
* Training has only **14 distinct issue quarters** from 3 survey rounds, so each input has at most 14 distinct values, and all of its variance is explained by the issue quarter.
* So they can only separate rounds and quarters, never provinces, and the survey level and the lead already do that.
* `unemp_region` and `remit_q_yoy` are **100 % missing in training**: regional unemployment starts in 2021, and the quarterly remittance series does not reach the training years. They are listed as inputs but carry no information. This is a pipeline defect to disclose, not to hide.
* The fix needs **provincial or regional employment and remittance series reaching back before 2018**. None was found in public sources (E152, E154). Regional household consumption was tried (E154) and gave no gain.

## 4. All five provinces LOW

| Province | Latest survey | Anchor | Score | P(HIGH) |
|---|---|---|---|---|
| Batangas | 39.9 | 31.5 | 25.8 | 0.010 |
| Cavite | 35.5 | 36.2 | 32.8 | 0.058 |
| Laguna | 26.2 | 33.7 | 28.7 | 0.023 |
| Quezon | 44.0 | 34.9 | 30.8 | 0.038 |
| Rizal | 39.1 | 38.3 | 35.4 | 0.093 |

All five latest surveys are below 50 even at their upper margins, so LOW follows the data, not a threshold choice. The model does not favour LOW generally: it says HIGH for 68 % of Mindanao rows (actual 64 %) and 53 % of Visayas rows (actual 53 %). In Luzon it over-calls HIGH (29 % vs 9 % actual). The lower scores than surveys come from the anchor; see section 1.

## 5. Threshold sensitivity (report only; the 50 line is unchanged)

| Line | Share of rows actually HIGH | Accuracy |
|---|---|---|
| 40 | 62.5 % | 76.4 % |
| 45 | 45.8 % | 69.4 % |
| **50** | **34.7 %** | **72.2 %** |
| 55 | 26.4 % | 81.9 % |
| 60 | 11.1 % | 84.7 % |

Accuracy rises at 55 and 60 because HIGH becomes rare and LOW is easy to guess. **Changing the line after seeing this would be choosing the result. It is reported for the adviser only.**

## 6. Maximum reliable lead

Criteria fixed in `docs/e156/LEAD_RELIABILITY_CRITERIA.md` before this run.

| Lead | Rows | Accuracy | F1 | AUC | Brier | vs persistence (95 %) | Slope (95 %) | Criteria passed | Status |
|---|---|---|---|---|---|---|---|---|---|
| **1** | 72 | 72.2 % | 0.655 | 0.855 | 0.138 | −0.075 [−0.134, −0.024] | [0.52, 0.97] | 4 of 6 | **Fail** (C1, C4) |
| 2 | 72 | 72.2 % | 0.667 | 0.849 | 0.140 | [−0.128, −0.025] | [0.47, 0.88] | 4 of 6 | Fail |
| 3 | 72 | 70.8 % | 0.644 | 0.837 | 0.146 | [−0.130, −0.020] | [0.46, 0.89] | 4 of 6 | Fail |
| 4 | 72 | 75.0 % | 0.679 | 0.819 | 0.152 | [−0.119, −0.013] | [0.43, 0.89] | 4 of 6 | Fail |
| 5 | 72 | 70.8 % | 0.632 | 0.809 | 0.154 | [−0.125, −0.001] | [0.42, 0.82] | 4 of 6 | Fail |
| 6 | 72 | 66.7 % | 0.571 | 0.786 | 0.160 | [−0.122, +0.007] | [0.42, 0.84] | 2 of 6 | Fail |
| 7 | 50 | 52.0 % | 0.478 | 0.677 | 0.208 | [−0.057, +0.054] | [0.34, 0.98] | 1 of 6 | Fail |
| 8 | 50 | 56.0 % | 0.522 | 0.727 | 0.194 | [−0.077, +0.045] | [0.42, 0.99] | 1 of 6 | Fail |

* **Mandatory Lead 1: fails.** **Maximum reliable lead: 0.** **First failing lead: 1.**
* Leads 1 to 5 beat persistence on Brier; that benefit ends at Lead 6.
* Why it declines: the anchor ages, and quarterly inputs carry little information about where provincial survey levels will be. Only three rounds and about 46 effective rows are available.
* Brier here is the survey-uncertainty-weighted version; earlier tables used the hard-label version (0.172 at Lead 1).

## 7. The locked candidate

`docs/e156/CANDIDATE_PROTOCOL.md`: a slope correction fitted only on each round's training rows.

| Lead 1 | E151 | Candidate |
|---|---|---|
| Accuracy | 72.2 % | 68.1 % |
| HIGH recall / LOW recall | 0.76 / 0.70 | 0.84 / 0.60 |
| F1 | 0.655 | 0.646 |
| AUC | 0.855 | 0.850 |
| Brier | 0.138 | 0.151 |
| Slope interval | [0.52, 0.97], fail | [0.61, 1.25], **pass** |
| Criteria passed | 4 | 5 |

It fixes calibration at every lead, but accuracy and Brier get worse, so under the rule fixed in advance **it is not adopted.** Training slopes were 0.67 (2018, 2019) and 0.80 (2021): the model is consistently overconfident.

## 8. Release gates

| Gate | Status | Reason |
|---|---|---|
| 1. Data integrity | **Pass, with caveats** | No leakage; no fabricated rows; some release delays assumed |
| 2. Forecast validity | **Pass** | True Lead 1, chronological, reproducible |
| 3. Model performance | **Fail** | Lead 1 fails C1 and C4; 72.2 %, below 75 % |
| 4. Five-group integration | **Partial** | All five reach the model; employment and remittances contribute nothing; two inputs are 100 % missing in training |
| 5. NLP validation | **Partial** | Labels 69 %; no incremental value |
| 6. Inference consistency | **Fail** | E151 is not connected to the dashboard or API |

**Not ready for deployment.**

## 9. What would change the result

1. **More provincial survey rounds:** the binding constraint. At about 46 effective rows, small real gains cannot be shown.
2. **Provincial or regional employment and remittance history before 2018,** so those groups can separate provinces.
3. **Scoring the sealed forecasts** as SWS and any new HFIAS round are published.

No further model search on these rows is planned: E151 to E156 have covered the justified options, and more looks would only fit these 72 rows.

## Files

`backend/app/e156/{audit,leads,candidate}.py`, `backend/data/e156/out/{audit.json, feature_usage.csv, lead_reliability.json, candidate_results.json, candidate_oof.csv}`, `docs/e156/{LEAD_RELIABILITY_CRITERIA, CANDIDATE_PROTOCOL, REPORT}.md`.
