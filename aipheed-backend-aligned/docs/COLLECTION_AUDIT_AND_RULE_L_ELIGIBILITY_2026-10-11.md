# Audit of the Collected Data and Rule L Eligibility (2026-10-11)

**This audit was read-only.**

- **Not done:** no model was trained or run, no label was rebuilt, and no observation was estimated. Production code and data, frozen forecasts, the protected evaluation protocol and the thesis chapters are unchanged. Nothing was committed or deployed.
- **Not opened:** nothing about the September or December 2026 SWS results was searched for, opened or inferred.
- **Previous reports and the collection folder are preserved.**

**Inputs:**

- `docs/DATA_COLLECTION_REPORT_2026-10-09.md`
- `data/supplementary/collection_2026-10-09/`
- earlier evidence in `evidence/2026-10-09_*`

**Outputs:** `evidence/2026-10-11_collection_audit/`:

| File | Contents |
|---|---|
| `hash_verification.csv` | Recomputed SHA-256 vs manifest |
| `cpi_tidy_vs_raw.csv`, `cpi_integrity_checks.json` | 30-value comparison with the raw OpenStat response |
| `cpi_continuity_check.csv` | 2025-Q4 stored vs 2026-Q1 collected (plausibility only) |
| `sws_2025_round_table.csv` | Every known 2025 SWS round |
| `label_components_rule_L.csv` | Each label's SWS and CPI components with dates and status |
| `input_availability_by_family.csv` | Every input family: reference period, verified date, proxy, status, strict eligibility, reason |
| `origin_eligibility_strict_vs_conditional.csv` | Per-origin eligibility under strict Rule L and under the unapproved proxies |

**Evidence tags:**

| Tag | Meaning |
|---|---|
| [V] | Verified on an original source |
| [V-single] | Original source, read once through a restricted extraction step; not yet independently re-read |
| [N] | PSA's own text via the search index (site behind Cloudflare) |
| [S] | Dated news report |
| [U] | Unverified |

---

## 1. Data-integrity findings

| Check | Result |
|---|---|
| SHA-256 of all 6 collected data files vs `COLLECTION_MANIFEST.json` | **6/6 match** |
| CPI tidy file vs raw OpenStat response | **30/30 rows matched; 0 value mismatches** |
| Series | Commodity code `2` = "01.1 – FOOD" (per the metadata snapshot), the same code `openstat_fetcher.py` uses for the label series. Year code `7` = 2026. |
| Provinces / months | Batangas, Cavite, Laguna, Quezon, Rizal × 2026-01..06 |
| Units | Year-on-year % (2018=100) |
| Missing / duplicates | 0 / 0. The raw response's `comments` field is empty (no preliminary or suppression notes). |
| Range | −0.7 to 6.9 |
| Continuity with existing records | No overlap exists (stored provincial data end 2025-Q4). Province 2026-Q1 means are on the same scale as the stored 2025-Q4 values (plausibility only, not a test). |
| SWS internal arithmetic | Moderate + severe = total for all 3 collected rounds (differences 0.0) |
| SWS April 23–28, 2025 | **Independently re-verified today [V]** on the archived original (web.archive.org capture 2025-12-26, `ART-20250627174857`): dateline "Jun 27, 2025 05:48:57 PM"; "Balance Luzon … at 17.0%"; moderate 16.5→13.9, severe 4.0→3.1; 600 Balance-Luzon respondents, ±4%; respondent statement (household heads to December 2024; registered voters January–April 11–15, 2025; adults from April 23–28, 2025) |
| SWS June and September 2025 | **[V-single].** Values and posted dates come from one restricted read of the original pages (2026-10-09). They are corroborated by the sums and by the next release restating the same figure, **but that restatement came through the same channel**. The pages are not archived under their current URLs; raw HTML was not saved. **Needs manual confirmation** (SWS PDF or page). |
| November 2025 stored value | Release page: 16.7 (12.7 + 4.0), posted 2026-01-14 [V-single]. **Matches the production table entry `(2025, "Q4", 16.7, 12.7, 4.0)`.** |
| Discrepancies found | **None.** No value was corrected. |

**Incidental exposure, disclosed:** the archived April 2025 release text also states the Balance-Luzon figure for the **April 11–15, 2025** (registered-voter) round. That value was **not recorded** in any file and is not used.

## 2. SWS rounds in 2025 and undecided label questions (`sws_2025_round_table.csv`)

| Round | Published | Evidence | Balance-Luzon value | Respondents | Stored | Label use |
|---|---|---|---|---|---|---|
| January 2025 (Stratbase-SWS) | [U] | n/a | Not retrieved (not authorized) | Registered voters [V] | No | Undecided (D3) |
| February 2025 (Stratbase-SWS) | [U] | n/a | Not retrieved | Registered voters [V] | No | Undecided (D3) |
| March 15–20, 2025 (Stratbase-SWS) | 2025-03-29 | [V] `pr20250329` | 24.0 (stored) | Registered voters [V] | Production table and labels | Currently used for 2025-Q1; retention undecided (D3) |
| **April 11–15, 2025** | **[U]** | Cited in the April 23–28 release [V] | **Not retrieved** | Registered voters [V] | No | **Unresolved (D3)** |
| April 23–28, 2025 (SWS: "First Quarter 2025") | 2025-06-27 | [V] (archived dateline) | 17.0 | Adults [V] | Supplementary | Undecided; 2025-Q2 label not defined |
| June 25–29, 2025 | 2025-08-15 | [V-single] | 15.3 | Adults [V-single] | Supplementary | Undecided; 2025-Q2 label not defined |
| September 24–30, 2025 (SWS: "Third Quarter 2025") | 2025-11-05 | [V-single] | 23.8 | Adults | Supplementary | Undecided; 2025-Q3 label not defined |
| November 24–30, 2025 | 2026-01-14 | [V-single] + news | 16.7 (stored) | Adults | Production table and labels | Currently used for 2025-Q4 |

**Open label decisions (adviser; D3):**

- **2025-Q1:** March only, or January + February + March. All are registered-voter rounds.
- **2025-Q2:** which of April 11–15 (registered voters; date [U]), April 23–28 and June (adults) count.
- **Respondent-population change:** whether the January–April 2025 registered-voter rounds are comparable with the household-head and adult series.
- **2025-Q3:** a single adult round, September.
- **Constraint from Rule L:** any option that includes a round with an [U] publication date (January, February, April 11–15) cannot produce an eligible label under strict L4 until that date is verified.

## 3. Provincial CPI publication dates: verified vs unverified

| Label month | National release | Provincial (RSSO IV-A) release | Status |
|---|---|---|---|
| December 2024 | 2025-01-07 [S] | **2025-01-13** [N] | **Provincial verified (the only one)** |
| The other 19 final months, June 2021 – June 2026 | Documented [S/N] (`evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv`) | **Unverified** | National only |
| January–June 2026 (collected) | 2026-02-05, 03-05, 04-07, 05-05, 06-05, 07-07 [S] | **Unverified** | National only |

**No national date was substituted for a provincial date.** The proxy rule (D1a, national + 14 days) remains **unapproved**. It is shown below only as a conditional scenario.

## 4. Revised Rule L eligibility

### 4.1 Inputs (`input_availability_by_family.csv`)

| Input | Under strict Rule L (no proxy approved) | Reason |
|---|---|---|
| SWS rounds as inputs | **Eligible** when the verified publication date is before the forecast date; 21 rounds (2021–2025) dated | Rounds with [U] dates excluded (L4) |
| News (FSSI, triggers) | **Eligible** | Article timestamps |
| Poverty incidence | **Eligible** after 2022-08-15 / 2024-08-15 | Verified releases |
| Provincial food CPI (labels and features, including the collected 2026 values) | **Ineligible** | Provincial publication date unverified |
| Regional CPI, rice, LFS, BSP, DOE, Brent, FX | **Ineligible** | Release practice documented, but no per-value date or official calendar (L3) |
| ONI, IBTrACS, NASA POWER | **Ineligible** | Same as above, plus revised vintages (D2) |

### 4.2 Training labels per forecast origin (`origin_eligibility_strict_vs_conditional.csv`)

| Target (origin) | Eligible labels: **strict** | Eligible labels: **if D1a + D4 approved** (rows) | Additional after D3 | Latest SWS input (verified date) |
|---|---:|---:|---|---|
| 2022-Q2 | 0 | 3 (15) | n/a | Dec 2021 |
| 2023-Q3 | 0 | 7 (35) | n/a | Mar 2023 |
| 2023-Q4 | 0 | 8 (40) | n/a | Jun 2023 |
| 2024-Q1 | 0 | 9 (45) | n/a | Sep 2023 |
| 2024-Q2 | 0 | 10 (50) | n/a | Dec 2023 |
| 2024-Q3 | 0 | 11 (55) | n/a | Mar 2024 |
| 2024-Q4 | 0 | 12 (60) | n/a | Jun 2024 |
| 2025-Q1 | 0 | 13 (65) | n/a | Sep 2024 |
| 2025-Q2 | **1** (2024-Q4) | 14 (70) | n/a | Mar 2025 |
| 2025-Q3 | 1 | 15 (75) | n/a | **Apr 23–28, 2025 (supplementary)** |
| 2025-Q4 | 1 | 15 (75) | 2025-Q2 | **Jun 2025 (supplementary)** |
| 2026-Q1 | 1 | 15 (75) | 2025-Q2, 2025-Q3 | **Sep 2025 (supplementary)** |
| 2026-Q2 | 1 | 16 (80) | 2025-Q2, 2025-Q3 | Nov 2025 |
| 2026-Q3 | 1 | 16 (80) | 2025-Q2, 2025-Q3 | Mar 2026 (exposed value; legitimate as an input) |
| 2026-Q4 | 1 | 16 (80) | 2025-Q2, 2025-Q3 | Mar 2026 (June 2026 date [U]) |

**How to read the table:**

- **Under strict Rule L there is effectively no training data.** Only the 2024-Q4 label (eligible from the 2025-Q2 origin) has a verified provincial CPI date. Almost every government input is also strictly ineligible.
- **The collected rounds help only if a proxy is approved.** They update the SWS input at three origins, and after D3 they would add up to two labels (10 rows).
- **The 2026-Q1 label (exposed) is excluded** from all counts.

## 5. Protection of the evaluation

- **Nothing about September or December 2026 SWS was accessed.**
- **The `backend/` quarterly scheduler (first automatic run 2026-10-15)** refreshes PSA indicators, rice and news. It **does not fetch SWS** (`backend/app/tasks/quarterly_pipeline.py`). Both repositories' SWS tables are hand-curated and frozen at `SWS_COVERAGE_END = (2026, 2)`. The remaining risk is a manual increase of that constant (the fetcher even prints an "extend hint"). That should stay prohibited until the protected forecasts are frozen.
- **Previously reused quarters (2022-Q4 to 2025-Q4) remain exploratory.**
- **Data completeness says nothing about predictive accuracy.**

## 6. Recommendation

**The project is not ready for an authorized model experiment.**

- **Under strict Rule L**, provincial CPI publication dates are verified for only 1 of 20 label months, and government inputs lack per-value dates. That leaves **no usable training set** (0 eligible labels before 2025-Q2).
- **The data needed for an experiment are now in hand and verified.** They become usable once these adviser decisions are made:
  1. **D1a:** approve "national release + 14 days" as the provincial CPI publication proxy (a sensitivity check already showed it changes no eligibility for lags of 0–60 days). The alternative is to have a person obtain RSSO IV-A dates for 19 months.
  2. **L3b / D2:** accept documented release practice, and revised vintages, for the government and climate inputs.
  3. **D3:** decide the 2025 label composition (including how to handle the April 11–15 and January/February registered-voter rounds).
  4. **D4:** accept 2022-02-04 for 2021 CPI values.
- **Before treating the collected values as fully verified, confirm by hand:**
  - the June and September 2025 SWS values and dates [V-single];
  - the November 2025 date [V-single].
- **With those decisions, the project would be READY WITH DOCUMENTED LIMITATIONS** for an **exploratory** development experiment (14–16 training quarters at recent origins). The protected 2026-Q3/Q4 evaluation still needs the freeze-then-collect procedure. It can provide at most an untouched point estimate on ≤ 10 rows, **not** evidence of ≥ 75% accuracy.

**Stopping here for your approval.**
