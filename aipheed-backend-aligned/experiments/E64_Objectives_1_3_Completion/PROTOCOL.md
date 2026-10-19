# E64 protocol: Objectives 1–3 completion

**Status:** frozen by sha256 (`runner/PROTOCOL_SHA256.txt`) before any E64 news feature is built and before any E64 candidate is scored.

**Starting evidence:** E62 final audit (57e663f) and the E56–E61 artifacts, all read-only.

**Lead-time evaluation:** run separately as E63 (session "Lead-time study for Chapter I Objective 2 V"). E64 cites E63 and does not re-run it.

## 1. Quarter-counting convention (Lead-2)

- **Predictor quarter t:** the latest quarter whose news is complete.
- **Issue date O(t):** 00:00 PHT on day 1 of quarter t+1.
- **Target:** quarter t+2. Lead-2 is counted from the predictor quarter.
  - Example: issued 2026-10-01 (in 2026-Q4), predictor quarter 2026-Q3, target 2027-Q1.
  - The target is therefore the quarter *after* the issue quarter.
- **Information allowed at O(t)** (E41 / E56 rules):
  - CPI to month 2 of t;
  - SWS rounds posted before O(t);
  - production, LFS and remittances to t−1;
  - news published in quarter t before O(t);
  - policy orders announced before O(t).
- **The other reading** ("two quarters after the issue quarter") is target t+3 = Lead-3 here. It is reported by E63, not by E64.

## 2. Rows

| Set | Content |
|---|---|
| Evaluation | Origins 2023-Q4..2026-Q1 → targets 2024-Q2..2026-Q3: 50 province-quarters, 10 quarters, 18 HIGH. These are the E57–E62 rows. |
| DEV | 2024-Q2..2025-Q3 (30 rows). The only rows used to choose among E64 candidates. |
| TEST | 2025-Q4..2026-Q3 (20 rows, 1 HIGH). Reported once, after the choice. It cannot assess HIGH detection. |
| Operational | Origins 2026-Q2 (target 2026-Q4) and 2026-Q3 (target 2027-Q1). Outcomes unknown; sealed. |

**Every one of the 50 rows had been examined before E64. All results are development evidence.**

## 3. Target

- **Reference: T43, unchanged.** HIGH iff the mean SWS hunger of the quarter (all rounds) > 11.3 AND (provincial food YoY > its 2021–22 P60 OR food-minus-headline YoY > its P60). It is preserved as the served target.
- **Descriptive alternatives only**, never used to choose a model or a configuration:
  - **T43-F:** hunger > 11.3 AND food YoY > P60 (no gap condition);
  - **T43-HL:** hunger > 11.3 AND (food YoY > P60 OR gap > P60 OR headline YoY > the province's 2021–22 headline P60).
- **Reported for each alternative:** base rate, agreement with T43, and the E56 / final-candidate scores. No provincial hunger label is built from regional data.

## 4. Improved news (N3), built by the backend module `app/news/pipeline_v3.py`

**Corpus:**
- the E31 store (`backend/data/news_e31/articles.jsonl`) plus the E60 store (copied unchanged to `backend/data/news_e60/articles.jsonl`);
- de-duplicated by `article_key`;
- dates from 2021-01-01 to 2026-10-14.

**Relevance and trigger:** E60 classifier v2, copied byte-identical to `app/news/classifier_v2.py`. Its sha256 must equal E60's `CLASSIFIER_V2_SHA256.txt` (`327f9431…`).

**Province:** the collector's geocoder attribution (`geo_province_code`). Relevant articles without a province are "national".

**Syndication:** the earliest copy of each cluster (same normalised title within 3 days, any outlet) is kept; this is the FSSI-v2 rule.

**FSSI-v3:**
- Equation 2 (bias weight × mean intensity) on admitted articles: v2-relevant, province-attributed, de-syndicated;
- intensity = XLM-RoBERTa-large-XNLI, model key `…|v2-noguard`;
- status SUFFICIENT (≥ 5), LIMITED_SIGNAL (1–4) or NO_USABLE_EVIDENCE (0);
- **never zero-filled.**

**N3 features at origin t:** from admitted articles of quarter t, published before O(t), per province.

| Column | Definition |
|---|---|
| `n3_cov` | log1p(number of admitted province articles) |
| `n3_<k>_rw` (k = market, climate, fish_kill, employment) | Σ exp(−ln2 · age_days / 30) over the province's admitted articles of trigger k, with age measured to O(t) |
| `n3_nat_<k>_rw` (k = market, employment, ofw_remittance) | the same over admitted *national* (unattributed) relevant articles; one value for all provinces |
| `n3_src` | number of distinct outlets among the province's admitted articles |
| `n3_fssi` | FSSI-v3 of (province, t); NaN if NO_USABLE_EVIDENCE |

This makes **12 columns**. A zero count means "no admitted article"; coverage is carried by `n3_cov`. FSSI is NaN when there is no evidence.

## 5. Candidates

All candidates are rolling-origin, refitted at every origin, and use the same E56 72-configuration search, nested chronological selection inside training, and the same hunger part (I7 ridge), unless stated.

| ID | Inputs | Selection |
|---|---|---|
| A | government only (E56 columns without `news_*`) | per origin (E56) |
| C | government + original E40 news (= E56) | per origin |
| D | government + N3 | per origin |
| E | government + N3 + history (`hist_ps_last`, `hist_ps_share4`, E60 definitions) | per origin |
| A-S | as A | **stable:** at origin t, the configuration with the lowest mean inner log-loss across all origins s ≤ t (each origin's inner scores use only its own training data) |
| D-S | as D | stable |
| B | N3 only: L2 logistic regression (NaN → training median plus a missing indicator) × the same hunger part | — |

**References** (read from sealed files, not re-run): E56 (E57 sealed), E58-EW, E60-A, E60-C, B-PROJ, persistence, majority as of the issue date, climatology as of the issue date.

**Hunger component:** the served ridge vs the E61 random walk (H2), reported for the final candidate as a component result. It is never mixed into the selection.

## 6. Selection rule (DEV only)

1. Compute the DEV Brier of P(HIGH) for A, A-S, C, D, D-S and E.
2. The lowest DEV Brier is chosen **only if** it beats A's DEV Brier by at least 0.005. Otherwise the simpler candidate is kept, in the order A, A-S, C, D, D-S, E.
3. The final candidate is then reported on all 50 rows and on TEST against every reference.

## 7. Claims and their evidence rules

| Claim | What it requires |
|---|---|
| "Improved news improves forecasting" | D (or D-S) vs A (or A-S): 50-row paired Brier with a quarter-cluster bootstrap 95% CI that excludes 0, **and** a quarter sign test p < 0.05 |
| "Stable selection reduces jumps" | Mean \|ΔP\| between consecutive origins per province lower for X-S than X, **and** Brier not worse (CI includes or is below 0) |
| "Better than baselines" | Paired Brier vs persistence, majority and climatology, with the same CI and sign-test rule |
| 75% development goal | Accuracy of P(HIGH) ≥ 0.5 on 50 rows, reported with its quarter-cluster CI. A warning-form accuracy is reported separately and is never presented as the probability's accuracy. |

**Also reported:** accuracy, balanced accuracy, precision, recall and F1 for HIGH and LOW, confusion matrix, Brier, log loss, calibration bins and slope, onsets detected, false alarms, missed HIGH cases, by province and by quarter, configuration switches, and the news split counts.

## 8. Not allowed

- choosing by TEST or by the 50-row results;
- changing thresholds, the target or the decision line after seeing scores;
- dropping quarters;
- pre-2021 data;
- data after the issue date for any origin;
- re-sealing or editing E56–E63 files;
- changing the production default (E38).

## 9. Serving

- The final candidate is served as `AIPHEED_LEAD2_MODEL=e64`. The record is built by `backend/scripts/build_record_e64.py`, which uses the same backend news module as the experiment.
- The dashboard news feed under e64 uses the N3 corpus and classifier v2.
- **E38 remains the default.**
- The 2027-Q1 e64 forecast is sealed write-once, with its inputs, outputs, components, explanations and news IDs.
