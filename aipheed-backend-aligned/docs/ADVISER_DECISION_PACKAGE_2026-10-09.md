# aiPHeed: Adviser Decision Package (2026-10-09)

**Purpose:** four methodology decisions are needed before any timing-valid (Rule L) experiment can be defined. This package sets them out with options, consequences and the evidence behind them.

- Every **recommendation** is marked as such. **None is an approved decision.**
- **Nothing has been implemented:** no labels, features, production code, frozen forecasts or thesis text were changed, no data was collected, and no model was run.

**Supporting files:**

- `docs/READINESS_REPORT_2026-10-09.md`
- `docs/LABEL_DEFINITION_DECISION_NOTE_2026-10-09.md`
- `docs/RULE_L_FINAL_AND_PROTECTED_EVALUATION_PLAN_2026-10-09.md`
- `evidence/2026-10-09_readiness/*.csv` (including the new `d1_d4_sensitivity_and_corrections.csv`)

**Action plan:** `docs/POST_DECISION_ACTION_PLAN_2026-10-09.md`.

---

## 0. What re-checking the evidence changed

| Earlier claim (READINESS_REPORT) | Re-check | Status |
|---|---|---|
| "19 stored SWS rounds 2021–2025 (17 [V] + 2 [L])" | The reconciliation table holds **18** rounds: **17 [V]** (archived SWS page or media-release file) and **1 [L]** (November 2025, from SWS's listing) | **Corrected** |
| "Provincial CPI released 5–8 days after national in three cases" | Only **December 2024** has both dates documented: national 2025-01-07, RSSO IV-A provincial 2025-01-13, so **+6 days**. The February and April 2025 regional conference dates exist, but their national release dates were not verified. | **Downgraded to one verified case** |
| 2025 respondent bases (household heads → registered voters → adults) | Rests on a **search-index excerpt** of the SWS April 2025 release, not on the opened page | **Still needs verification** |
| D1 changes which labels are usable | Tested: provincial lags of **0–60 days** give **identical** eligible labels at every quarterly origin, 2021-Q3 to 2026-Q4 | **New finding: D1 has no practical effect on current labels** |
| D4 changes which labels are usable | Differs only at the 2021-Q4 origin (1 vs 0 labels) and the 2022-Q1 origin (2 vs 0) | **Confirmed: early training folds only** |

Everything else checked out against the cited files:

- the 20 national CPI release dates, each with a dated source in `cpi_final_month_release_dates.csv`;
- the 17 [V] SWS dates;
- poverty releases 2022-08-15 and 2024-08-15;
- the 2018 CPI rebasing on 2022-02-04;
- the missing 2025 rounds;
- the 2026-Q1/Q2 exposure.

## 1. Decision table

| ID | Question | Options | Consequences | **Recommendation (not a decision)** | Evidence still needed |
|---|---|---|---|---|---|
| **D1** | Which date counts as the provincial CPI publication date in Rule L? | (a) National release + a fixed buffer (e.g. +14 days). (b) The actual RSSO IV-A provincial release date for each month. (c) The national release date. | Tested lags of 0–60 days produce **identical training-label eligibility at every quarterly origin**, because the SWS date binds or the gap never crosses a quarter start. (b) requires about 20 dates read by hand (the site is behind Cloudflare). (c) understates the observed provincial lag. | **(a) national + 14 days**, documented as conservative: it covers the one verified case (+6 days) and changes no eligibility. Upgrade to (b) if those dates are obtained. | Optional: per-month RSSO IV-A conference dates. Not needed for (a). |
| **D2** | May the model use current, revised data in place of the values available at each forecast date? | (a) Accept, documented as a limitation. (b) Exclude series known to be revised (ONI, IBTrACS, NASA POWER) from the primary model. (c) Reconstruct as-published vintages. | No source in the project stores as-published vintages. **ONI values can change up to 2 months after first release** (CPC). **IBTrACS recent records are provisional** (NCEI). **NASA POWER's near-real-time values are later replaced** by MERRA-2. Every input is published at least about 2 months before it is used. Revisions are a **point-in-time limitation, not leakage of outcomes**. (c) is not feasible with current sources. | **(a) accept and document,** plus a **pre-registered sensitivity check** that drops ONI, IBTrACS and NASA POWER features, run in the same experiment. | None for (a). For (c): archived vintages, which are not available. |
| **D3** | How is a quarter's SWS label composed (round count, respondent population)? | See Section 2: options A–E from the decision note | Changes labels, the global-median threshold and comparability | **No definition is recommended** (this is the adviser's call). Process recommendation: whichever definition is chosen, **pre-register it before any run**, and report results under one alternative as a sensitivity analysis. | Verify the 2025 respondent bases on the opened SWS releases. January and February 2025 release dates are needed if they are included. |
| **D4** | When were 2021 CPI values (2018=100) public? | (a) 2022-02-04, the rebasing release. (b) Treat the earlier 2012-base releases as equivalent. | Affects only the **2021-Q4 and 2022-Q1 origins** (0 vs 1–2 eligible labels). All later origins are identical. (b) needs evidence that 2012-base and 2018-base YoY values match, which is not available. | **(a) 2022-02-04,** the conservative and documented choice | None for (a) ([S] ABS-CBN 2022-02-04 on the rebasing) |

**Related decisions also pending** (recorded earlier; listed so nothing is lost):

| ID | Decision |
|---|---|
| D5 | Designate 2026-Q3/Q4 as the protected final evaluation, and 2026-Q1/Q2 as disclosed, non-independent checks |
| D6 | Whether a 2026-Q4 label published in 2027 counts as within the 2021–2026 window |
| D7 | Authorize collecting the missing 2025 SWS rounds and January–June 2026 provincial CPI |
| D8 | How the 75% target is judged (point estimate or lower bound) |

## 2. The quarterly SWS label (D3): consequences only

| Feature of the data | Where it occurs | Consequence |
|---|---|---|
| **Labels built from different numbers of rounds** | Two rounds averaged: 2021-Q2, 2022-Q2. One round: every other stored quarter. 2025-Q1 uses 1 of 3 available rounds. | An average of two rounds is a less noisy measure than a single round, so labels differ in reliability by quarter. A label is published only when its **last** round is (Rule L). |
| **Different respondent populations** [verification pending] | Household heads through December 2024; registered voters January–April 2025 (Stratbase-SWS, including the March 2025 round that sets 2025-Q1's label); adults from the April 23–28, 2025 survey | 2025 values may not be comparable with 2021–2024 values. 2025 includes high readings that also shift the **global-median threshold (14.345)**. |
| **Missing rounds** | Not collected: April and June 2025 (2025-Q2), September 2025 (2025-Q3), January and February 2025 | 2025-Q2/Q3 have **no label**, so there are fewer training rows and test quarters. The rounds are also missing as **inputs**, so forecasts made after their publication used an older SWS value. That is under-information, not leakage. |
| **Quarter assignment** | By fieldwork date (the existing convention), not SWS's own "First Quarter" naming | The current convention follows Rule 3. SWS's naming would let a label be set by data collected after the quarter ended. |

**Options A–E** (detail in the decision note):

| Option | Definition |
|---|---|
| A | Keep the current definition |
| B | Average every round fielded in the quarter |
| C | Use the latest round only |
| D | Use only rounds with a comparable respondent population |
| E | Use SWS's own quarter naming (conflicts with Rule 3) |

**No missing value has been estimated or inferred.**

## 3. Outstanding actions by type

**Adviser approval required:**

- D1–D4.
- D5–D8.
- Approval of the experiment pre-registration (to be drafted after the decisions).

**Manual source verification required** (no download; psa.gov.ph and rsso04a are behind Cloudflare, so a person must read them):

1. SWS April 2025 release: the respondent-base statement (D3).
2. SWS release pages for June 2025 (2025-08-15), September 2025 (2025-11-05) and November 2025 (2026-01-14): confirm the [L] dates on the pages.
3. January and February 2025 Stratbase-SWS hunger release dates (only if D3 includes them).
4. The June 2026 SWS round's **publication date only** (its value is already exposed). Needed to fix the SWS input for the 2026-Q4 forecast.
5. Optional (D1 option b): RSSO IV-A provincial CPI conference dates for about 20 months.

**Data collection requiring authorization (D7):**

1. Balance-Luzon hunger values for April, June and September 2025 (and January and February 2025 if D3 includes them), each recorded with its source URL and publication date.
2. Provincial food CPI from OpenStat `0012M4ACP23`, 01.1 Food, Batangas, Cavite, Laguna, Quezon and Rizal, **January–June 2026**: 30 values.

**Protected evaluation safeguards (apply now):** Section 4.

## 4. Safeguards

**Against leakage:**

1. Rule L (L1–L6), as decided, is implemented in **experimental code only**, with unit tests:
   - no training label published on or after the forecast date;
   - no SWS input published after the forecast date;
   - every input checked against its documented release date or release practice;
   - no value with a reference period before 2021.
2. The global-median threshold and the label definition are fixed in the pre-registration before any run.

**Against test-set reuse:**

3. Results on 2022-Q4 to 2025-Q4 are reported as **exploratory development** only. They have been reused across many earlier studies.
4. **One primary configuration and the comparators are fixed before the protected evaluation.** Comparators: MODEL-A configuration, the Eq. 3 rule, and carry-forward of the latest published label. No selection, tuning or threshold change after 2026 outcomes are seen.
5. 2026-Q1/Q2 are reported only as **disclosed, non-independent checks**.

**Against exposure of September or December 2026 SWS results:**

6. Nobody working on the model opens, searches for or downloads SWS September or December 2026 hunger results, including general SWS web searches whose summaries could reveal them. **Any accidental exposure is logged, and the affected quarter is downgraded to "disclosed check".**
7. Do not extend the hand-curated table in `app/ml/corpus/sws_hunger_fetcher.py` beyond `SWS_COVERAGE_END = (2026, 2)`, and do not run `scripts/refresh_all_sources.py` for SWS, until the forecasts are frozen.
8. **Freeze before collection.** SHA-256 hashes of the forecasts, configuration, inputs and code go to you or the adviser before any 2026-Q3/Q4 outcome is collected. The outcomes are then collected, ideally by someone other than the modeller, into a separate file, and **scored once** with a pre-written script.

## 5. Exploratory development vs defensible final evaluation

| | Exploratory development | Defensible final evaluation |
|---|---|---|
| Data | 2021–2025 labelled quarters, walk-forward under Rule L | 2026-Q3/Q4 outcomes not yet seen, scored once against frozen forecasts |
| Purpose | Choose and debug a configuration; compare against baselines | Estimate performance on outcomes unseen during development |
| Status of the data | Already used repeatedly; results are **optimistic and not independent** | Untouched, **if** the safeguards hold |
| Size | 8 test quarters (40 rows), 5 provinces sharing most inputs | **At most 2 quarters (10 rows)** |
| What it can show | Whether a model is plausible and how it compares with simple baselines | One untouched point estimate, with a very wide interval |
| What it cannot show | Generalization | That true accuracy is above 75% (even 10/10 would not establish it, because rows within a quarter are not independent) |

**No result from either stage is expected to establish 75% accuracy with confidence.** That would need many more independent quarters than 2021–2026 provides.

## 6. Claims that still require verification

| Claim | Basis now | What would verify it |
|---|---|---|
| 2025 respondent populations | Search-index excerpt of the April 2025 release | Read the SWS release pages |
| June, September and November 2025 publication dates | SWS listing via search index [L] | Read the SWS release pages |
| Provincial CPI lag (+6 days) | One case (December 2024) | Further RSSO IV-A dates (optional under D1a) |
| Per-observation release dates for rice, LFS, BSP and DOE | Documented release practice and examples [S]/[N], not per value | Agency release calendars (sites blocked to automation) |
| "Quezon" CPI excludes Lucena City | Lucena listed separately in OpenStat metadata [V]; exclusion assumed | PSA CPI technical notes |
| Absence of SWS hunger rounds fielded in 2021-Q1 or 2022-Q1 | Inferred from SWS's "First Quarter" surveys being fielded in April | The SWS archive index (Wayback index was offline 2026-10-09) |

---

### Source references

The full citations are in `docs/READINESS_REPORT_2026-10-09.md` (Sources section) and `evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv`. Key items:

- **Provincial CPI lag:** [RSSO IV-A April 2025 press-conference notice](https://rsso04a.psa.gov.ph/sites/default/files/attachment-dir/2025-0400-PR17%20April%202025%20Inflation%20Report%20Press%20Con.pdf); the December 2024 regional release of 2025-01-13 (search-index excerpt); national release [Philstar 2025-01-07](https://www.philstar.com/business/2025/01/07/2412479/inflation-hits-29-december-ends-2024-32)
- **Rebasing:** [ABS-CBN 2022-02-04](https://news.abs-cbn.com/business/02/04/22/january-inflation-at-3-percent-psa-shifts-to-2018-as-base-year)
- **Revisions:** [CPC ONI page](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php); [NCEI IBTrACS v4r01](https://www.ncei.noaa.gov/node/1660); [NASA POWER data sources](https://power.larc.nasa.gov/docs/methodology/data/sources/)
- **SWS rounds:** `evidence/2026-10-09_data_audit/sws_round_publication_dates_v2.csv` (archived SWS pages, for example `ART-20250627174857`; media releases `pr20250114`, `pr20250329`, `pr20260512`)
