# Missing observations: exactly what would enable a valid evaluation

**Scope.** Every item below is **external**: nothing in E26 can create it. Nothing has been fetched, opened or filled.

**Authorization procedure, for every item:**

- Supply the file, its full SHA-256 and who authorized it, and when. E26 verifies the hash by script; it never types one.
- The file holds **only** the authorized rows: 2021 or later, and not after the authorized limit. A file with any other row is **refused, never filtered** (`backend_dev/app/quarterly/outcomes.py`).
- Each row carries a publication date, or a documented upper bound, that is not before its reference period ends.

**Priority:**

- **O1** gives a valid local evaluation as soon as it is authorized.
- **O6** is the only route to C9 (unseen quarters). It takes years.
- **O2–O5 and O7** support face validity, model specification or signals.

| # | Observations | Exact coverage | File format (adapter) | Evidence required | What becomes valid | Power / time |
|---|---|---|---|---|---|---|
| **O1** | **CBMS 2024 household FIES aggregates by city/municipality**, and CBMS 2022 where the LGU took part | **All 142 CALABARZON LGUs** in `backend_dev/data/inputs/lgu_vulnerability.csv`. **At least about 75** for 80% power at ρ = 0.3. Reference years 2022 and 2024 only. | `cbms_fies_lgu`: lgu_code (PSGC), lgu_name, reference_year, households_assessed, fies_moderate_severe_pct, source_document, publication_date | The LGU's CBMS report or the PSA RSSO IV-A turnover/presentation showing each value. The turnover or report date. The FIES scoring method (raw-score cut-off or FAO Rasch). The LGU's consent to use the aggregates (no household microdata). | **Local validation of the Objective 3 rankings** (`local_validation.attribution`). It compares aiPHeed's risk index, density only and poverty only with a measured local food-insecurity outcome, overall and within each province. LGUs with both waves also give a 2022→2024 change check. This adds evidence to SOP Q4; it does not replace the DA evaluators (H4). | 142 LGUs: power 0.97 at ρ = 0.3. 75 LGUs: 0.80. One province (about 30 LGUs): 80% only at ρ ≥ 0.5. Available now if released. |
| **O2** | **2023 NNS household FIES by province**: Batangas, Cavite, Laguna, Quezon, Rizal, and Lucena City separately | 2023–2024 fieldwork only | `fnri_provincial_fies`: province_code, survey, scale = FIES, reference_start, reference_end, prevalence_pct, n_households, publication_date (add standard errors as an extra column) | FNRI table or microdata release letter; the release date; sample size and standard error per domain | **Objective 5 face-validity anchor at province level**, in window. A 5-province ordering can only be called significant if Spearman ≥ 0.9 (`runs/local_power.json`), so it is **face validity, not a test**. | Available now if FNRI releases domain estimates |
| **O3** | **ENNS 2021-round HFIAS by domain**, only for CALABARZON domains surveyed in the 2021 round (fieldwork Jul 2021–Jun 2022) | First establish which CALABARZON domains are in the 2021 replicates (S4). If none, O3 is void. | `fnri_provincial_fies` with scale = HFIAS; **an extract holding 2021-round domains only** (the PUF mixes 2018/2019, so it is refused as is) | FNRI metadata naming the replicate year of each domain; the PUF version and SHA-256 | A second in-window provincial point (HFIAS ≠ FIES: different scale, never pooled) | As O2 |
| **O4** | **PSA subsistence incidence by province, 2021 and 2023**, with coefficients of variation | 5 provinces × 2 years | `psa_subsistence_incidence`: province_code, reference_year, subsistence_incidence_pct, cv_pct, publication_date | PSA official tables (full-year poverty statistics); release dates | An official food-related (income-based) provincial outcome: ordering and 2021→2023 direction, as face validity | 5 units: as O2 |
| **O5** | **SWS: (a)** the Balance Luzon sample size of **every production round 2021-Q1…2026-Q2**; **(b)** verified publication dates of the March and June 2026 rounds; **(c)** a codebook check of whether SWS microdata (Data Library) identify CALABARZON, and with how many respondents per round; **(d)** optional NCR, Visayas and Mindanao area series 2021-Q1…2026-Q2 | 2021-Q1…2026-Q2 only | (a) add an `n_respondents` column to the authorized SWS rounds file (the engine uses it per round); (d) `sws_area_series` | (a) each release's methodology note; (b) the release pages' dates; (c) the codebook or a written SWS reply | (a) Correct survey-noise weighting: the noise share is 0.29 at n = 600 and 0.58 at n = 300. (b) Earlier usable origins. (c) Whether a CALABARZON-specific H is possible (target change: R3). (d) Auxiliary evidence on whether the method anticipates hunger changes (4 series; R3). | (a)(b) immediate. (c) depends on SWS. (d) needs adviser approval to count. |
| **O6** | **Prospective outcomes for each sealed target, every quarter from 2026-Q4.** For each target quarter q: the **SWS production round of q** with publication-date evidence, and the **provincial food CPI YoY for the three months of q** with release dates. Plus **a seal before each outcome**: the quarterly pipeline must seal every cycle, which needs E25 `AUTHORIZATION_REQUEST.md` A1–A2 inputs at each origin. | 2026-Q4, 2027-Q1, … one quarter at a time; nothing after the authorized limit | Outcome labels recorded with `Ledger.record_outcome` (path + SHA-256 + authorized_by + authorized_on). A quarter with no production round is declared with `Ledger.record_missing` (final). | SWS release and PSA release with dates | **C9.** Under amendment A1: one look at the first year end with ≥ 12 scored dates, ≥ 5 HIGH and ≥ 5 LOW. **The E25 seal is already registered** (`runs/ledger/T1_A.jsonl`, `T2.jsonl`). | Earliest look: end of 2029 (P(evaluable) 0.74); 0.83 by 2031. P(valid accuracy claim) ≤ 0.03 for a correct model, ≤ 0.125 even with a ρ = 0.9 signal. |
| **O7** | Signals: **DROMIC/NDRRMC affected families by province and event**; **regional bottom-30% CPI**; **provincial LFS (annual)** | 2021-01 … authorized limit (2026-06 now) | `dromic_affected`; the others as indicator files | The report PDFs and release dates | A test of whether any of them anticipates regional hunger changes (none of the tested government indicators did, E25) | The horizon shows that even ρ = 0.9 leaves an accuracy claim unlikely. They can help Brier and usefulness, not the claim. |
| **O8** | **PSA 2021 municipal Small Area Estimates** (from E25 C2) | 142 LGUs, 2021 | workbook + SHA-256 (`runner/lgu_rankings.py --sae`) | PSA release | Replaces the 126 province-mean poverty substitutes in the rankings | Immediate |

## What each piece of evidence settles

| Question in the brief | Settled by | Can it be settled without new data? |
|---|---|---|
| Does aiPHeed distinguish meaningful **local** risks? | O1 (CBMS, 142 LGUs) | **No.** No local outcome is authorized. The provincial D term is transient (between-province variance 0). |
| Does it **anticipate actual changes** beyond persistence? | Development: VOI (cause 4). Unseen: O6. Specification: O5(a). | Development evidence only. A timely regional reading helps (lead 2: p = 0.031, exploratory). The status-quo information set does not. |
| Does it **generalize to unseen quarters**? | O6 + amendment A1 approval | **No.** Not before the end of 2029 at the earliest. |
| Is the regional level measured precisely enough? | O5(a) | No. Per-round n is unverified. |

## Not requested (out of window or out of scope)

- NNS 2019; ENNS 2018/2019 domains; any pre-2021 SWS, CPI or survey value.
- Any July–December 2026 value, until you authorize it.
- Household microdata with identifiers.
- DEPDev materials.
