# OLD_NEWS: results — REF + GDELT news categories (EXPLORATORY, the last attempt)

**Plan:** `PLAN.md` (SHA-256 `0914a649…7d61`, commit `8d465aa`) and `ADDENDUM_1.md` (`fc10f52f…1b50`, commit
`f289e43`; de-duplication within each file, approved before any fit).

**Evidence status:** development evidence; one candidate; the last attempt.

## Decision

**REF + G fails R5 and R7 at both Lead 1 and Lead 2.** REF+news stays the main model under the paper's 75% rule.
**The attempts to pass R1–R7 on development data are closed;** only the prospective protocol
(`../SENIOR_REVIEW/PROSPECTIVE_PLAN.md`) remains. Nothing is sealed.

## 1. The scan and the data

| Item | Value |
|---|---|
| Query | E85's `gdelt_query_v1.sql`, partitions 2015-02-18..2020-12-31 (`data/gkg_v1_2015_2020.sql`, `68eea3eb…`) |
| Cap | `maximum_bytes_billed = 1.0e12` |
| **Billed** | **995,515,957,248 bytes** (dry run 995,515,666,287), one job (`oldnews_gkg_2015_2020_0914a649_r2`) |
| Failed attempt | One earlier attempt failed with `invalidQuery` before reading data, 0 bytes: Windows `bq.cmd` cut the multi-line query at its first line break. The query is now passed on stdin |
| Rows | **119,919** (2015-02-18 23:30 to 2020-12-31 22:30 UTC); 0 exact duplicates; UTF-8 checked |
| Raw file | `backend/data/gdelt_e85/gkg_calabarzon_2015_2020.parquet` (git-ignored), SHA-256 `31945cfd…6713` |
| Retrieval | Free `bq head` paging of the destination table; the BigQuery dataset was deleted afterwards |

## 2. Feature checks (PLAN section 3, as amended)

- **The copy of E85's `load()`** (only its 2021 assertion removed) returns a frame identical to the original on the
  2021+ file.
- **The first run applied the plan's de-duplication across the two files, and failed the plan's own equality check**
  (19 of 22 quarters differ, at most 0.008). There were two causes:
  - 37 evergreen 2021+ records, e.g. Britannica "Manila", re-crawled travel pages;
  - 6 old-file records on 2021-01-01 PHT.

  It stopped before any fit. Addendum 1 (your option a) restricts de-duplication to each file, as E85 did, and drops
  the 6 boundary records.
- **With the addendum, every 2021-Q2..2026-Q3 value equals E85's stored features exactly** (0 quarters differ).
- **Coverage** (reported only; `out/coverage.json`):
  - records per quarter: 4,300–9,200 in 2015-Q2..2017-Q2; 2,300–3,500 in 2017-Q4..2020-Q4, except **2020-Q1, 10,502**
    (COVID). Mean 2018-Q1..2019-Q2: 2,988, against 5,037 in the other 2017–2020 quarters;
  - no origin has fewer than 20 records;
  - the family shares are stable across years. The exception is DISASTER, at **0.62 in 2020** against 0.30–0.42
    otherwise (the 2020 typhoon season).

## 3. Machinery check

The refit code with REF's columns reproduces the stored REF Lead-1 and Lead-2 forecasts: 226 of 226 rows, the same
configuration at every origin, max |Δp| = 1.1e-16.

## 4. Per lead (62 labelled quarters, targets 2010-Q1..2026-Q3, threshold 0.50)

| | REF L1 | REF L2 | **REF + G L1** | **REF + G L2** |
|---|---|---|---|---|
| Accuracy | 0.790 | 0.790 | 0.774 | 0.774 |
| Balanced accuracy | 0.717 | 0.717 | 0.705 | 0.705 |
| Precision | 0.812 | 0.812 | 0.809 | 0.809 |
| Recall | 0.907 | 0.907 | 0.884 | 0.884 |
| F1 | 0.857 | 0.857 | 0.844 | 0.844 |
| AUC | 0.702 | 0.704 | 0.692 | 0.683 |
| Brier | 0.1875 | 0.1838 | 0.1946 | 0.1974 |
| TP / FP / FN / TN | 39/9/4/10 | 39/9/4/10 | 38/9/5/10 | 38/9/5/10 |
| Middle third (2015-Q2..2020-Q4) | 12/21 | 12/21 | **11/21** | **11/21** |
| GDELT share of SHAP | — | — | 9.3% | 9.5% |
| Calls that differ from REF | — | — | 1 | 1 |
| **Rules failed** | R7 | R7 | **R5, R7** | **R5, R7** |

### R1–R7 for REF + G

| Rule | Lead 1 | Lead 2 |
|---|---|---|
| R1 | pass (62) | pass (62) |
| R2 accuracy ≥ 0.75 | pass 0.774 | pass 0.774 |
| R3 balanced ≥ 0.70 | pass 0.705 | pass 0.705 |
| R4 > 0.306 and > 0.661 | pass | pass |
| R5 Brier vs persistence; vs climatology (p < 0.10) | **fail**: −0.144 (p 0.001); −0.026 (**p 0.165**) | **fail**: −0.141 (p 0.000); −0.025 (**p 0.200**) |
| R6 precision / recall ≥ 0.60 | pass 0.809 / 0.884 | pass |
| R7 thirds ≥ 0.60; LOQO ≥ 0.70 | **fail**: 0.952 / **0.524** / 0.850; LOQO 0.770 | **fail**: same thirds; LOQO 0.770 |

## 5. What the news did

- **The GDELT columns carry 9.3–9.5% of SHAP influence**, more than the 2.8% of REF+news's corpus news. They change
  exactly **one** call at each lead, **from right to wrong**:
  - Lead 1, 2020-Q3 (BL hunger 20.8%, HIGH): REF 0.711, REF + G **0.289**;
  - Lead 2, 2020-Q4 (BL 14.4%, HIGH): REF 0.711, REF + G **0.289**.

  Both fall in the failing middle third, which drops from 12/21 to 11/21. That 2020 origin coincides with the year's
  record DISASTER share in the news (0.62).
- **Probabilities get worse overall** (Brier +0.007 / +0.014). The gain over climatology is lost: R5's p rises from
  0.096 / 0.070 to 0.165 / 0.200. That is why REF + G also fails R5, which REF passes.
- **No quarter of 2015–2019 changes.** The reversals around 11.3% that make R7 fail (`../RELIABLE_NEWINFO/STEP0_SOURCES.md`)
  are not anticipated by the news categories.

## 6. Conclusion

With RELIABLE_L12 (threshold), RELIABLE_NEWINFO (blend; rainfall) and this attempt (GDELT news over the failing
period), every planned route to R1–R7 at Leads 1 and 2 on 2010–2026 has been tried and failed.
- **The binding failure is R7's 2015–2020 third,** a property of the target (survey noise around a fixed line), not of
  missing inputs (`../SENIOR_REVIEW/AUDIT.md`).
- **Under the paper's 75% rule,** REF+news (the main model) and REF keep a Maximum Reliable Lead Time of 2.
- **The only clean test left** is the sealed prospective record (first R1–R7 verdict at about 40 labelled quarters,
  about 2037).

## 7. Files

| File | Content |
|---|---|
| `runner/fetch_gkg.py` | The scan and retrieval |
| `runner/run_refg.py` | Features, fit, score, seal |
| `out/checks_fetch.json` | Job, bytes, hashes |
| `out/checks.json` | Load copy, equality, reproduction |
| `out/coverage.json` | Coverage checks |
| `out/gdelt_features_2015_2026.csv` | The 15 regional columns |
| `out/forecasts_refg.csv` | REF + G and the REF reproduction |
| `out/results.json` | All numbers above |
| `out/fit_log.txt` | The fit log |

No seal file was written.
