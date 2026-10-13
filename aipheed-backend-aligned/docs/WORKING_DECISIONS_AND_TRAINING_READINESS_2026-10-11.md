# Working Decisions and Training Readiness (2026-10-11)

**These are research-team working decisions, not adviser approvals.** They are adopted so development can proceed, and each is recorded with its rationale, limitations and alternatives.

- **Not done:** no model was trained, tuned or scored. No label was rebuilt and no observation estimated. The scheduler, production, frozen forecasts and thesis chapters were not touched. Nothing was committed or deployed.
- **Not accessed:** nothing about the September or December 2026 SWS results.

**Supporting tables** (`evidence/2026-10-11_working_decisions/`):

| File | Contents |
|---|---|
| `feature_eligibility_by_protocol.csv` | All 51 model inputs, development vs strict status, with basis |
| `origin_eligibility_by_protocol.csv` | Training labels per forecast origin under each protocol, with the reason for any difference and each origin's role |
| `label_definitions_for_sensitivity.csv` | The primary label definition and the separate sensitivity definitions (no values computed) |
| `feature_counts.json` | Input counts per protocol |

Built from existing records only: `evidence/2026-10-11_collection_audit/label_components_rule_L.csv`, the window frame in `scripts/supplementary/window2021_study.py`, and the source notes in the fetchers.

---

## 1. Working decisions

| # | Decision | Rationale | Limitation | Alternative |
|---|---|---|---|---|
| WD1 | **Provincial CPI publication date ≈ national release + 14 days**, labelled a **proxy** (never "verified") and used in the **development protocol only** | National dates are documented for all 20 label months. The only verified provincial date (Dec 2024) lagged national by 6 days. Lags of 0–60 days change no training-label eligibility at any quarterly origin. | Not a verification. The strict protocol cannot use it. | Read the RSSO IV-A dates by hand (19 months) |
| WD2 | **Keep revised ENSO (ONI), drought (derived from ONI), typhoon (IBTrACS) and rainfall (NASA POWER) values in development, disclosed** | They are published well before each origin; no historical vintages are stored | **Excluded from strict real-time evaluation:** CPC, NCEI and NASA document that values change after first release | Obtain archived vintages (not available) |
| WD3 | **Other inputs:** use per-value dates where verified; otherwise use a documented schedule only if it shows availability before the origin. **Unresolved inputs are excluded from the strict protocol.** | Follows L3 | Several schedules rest on examples rather than official calendars | Agency release calendars |
| WD4 | **Labels:** the existing definition (A) is primary for development. Alternatives are documented separately for sensitivity only; none built. | Avoids changing the approved target, inventing values or mixing populations silently | Definition A's 2025-Q1 label uses registered voters, and 2025-Q2/Q3 are unlabelled | Section 3 |
| WD5 | **2021 CPI (2018=100) unavailable before 2022-02-04** | PSA rebased on that date [S] | Early origins (2021-Q4, 2022-Q1) lose their 1–2 labels | n/a |
| WD6 | **Reused quarters 2022-Q4 to 2025-Q4 are exploratory only** | They were used in many earlier comparisons | No independent evidence comes from them | Protected 2026-Q3/Q4, once valid |

## 2. Step 1: scheduler safety (inspected, not executed or changed)

**What it is:** `backend/app/tasks/scheduler.py` and `backend/app/tasks/quarterly_pipeline.py`, started from `backend/app/main.py`.

- **Trigger:** cron `0 2 15 1,4,7,10 *`, Asia/Manila (`backend/app/config.py`), so **2026-10-15 02:00**.
- **Conditions:** it runs only if the `backend/` FastAPI server is running at that time (in-memory job store, 6-hour misfire grace), with `SCHEDULER_ENABLED` defaulting to `True`.
- **At inspection:** no python or uvicorn process was running (2026-10-11).

| Question | Finding |
|---|---|
| Can it retrain or promote a model? | **Yes.** The `retrain` stage trains a candidate. `promote()` **replaces `backend/models/thesis_food_insecurity_model.joblib`** (archiving the old one) if the candidate meets the Algorithm 4 targets. `publish()` clears the API caches and stages review rows in the database. |
| Can it modify data? | **Yes, within `backend/`:** upserts `psa_indicators.parquet` and `psa_rice_prices.parquet`; appends news to `corpus_geocoded.parquet` and an awaiting-review CSV; rebuilds the FSSI chain and `data/thesis/panel.parquet`; writes `data/pipeline_runs/*.json`. |
| Can it overwrite frozen evidence? | **No.** Every path is rooted at `backend/` (`ROOT = parents[2]`). There is no reference to `aipheed-backend-aligned/`, its frozen forecasts, evidence or `data/supplementary/collection_2026-10-09/`. |
| Can it change SWS coverage? | **No.** No stage fetches SWS. `SWS_COVERAGE_END = (2026, 2)` is a constant in the hand-curated fetcher and nothing edits it. |

**Threat to evaluation integrity:** none for the aligned evaluation evidence. **There is a threat to the thesis-documented `backend/` system:** an unattended run could replace its served model and change its data. That changes what the thesis describes, and any comparison against "MODEL-A as served".

**Smallest protective action (recommended; not done):** set `SCHEDULER_ENABLED=false` in the `backend/` environment before the server next starts (a configuration flag, no code change). Re-enable it after the evaluation freeze. If a run is wanted, the existing CLI flag `--no-promote` prevents model replacement.

## 3. Labels (WD4): definitions kept separate

`label_definitions_for_sensitivity.csv`:

| Definition | Rule | Labels 2021–2025 | Population issue | Status |
|---|---|---|---|---|
| **A, primary for development** | Fieldwork quarter; mean of two rounds where there are two; 2025-Q1 = March only; 2025-Q2/Q3 unlabelled | 16 | 2025-Q1 = **registered voters**, unlike the 2021–24 household heads | Exists (unchanged) |
| A-adult (sensitivity) | A + 2025-Q2 = mean of the two adult rounds (Apr 23–28, Jun 25–29) + 2025-Q3 = Sep | 18 | Adds adult-respondent labels; the Apr 11–15 registered-voter round is excluded | Not built |
| D (sensitivity) | Household-head-comparable rounds only | 14 | Most comparable; drops 2025-Q1 and 2025-Q4 | Not built |
| C (sensitivity) | Latest round per quarter | 16 (2021-Q2 and 2022-Q2 change) | One round per label | Not built |
| B | Mean of all rounds, including Jan, Feb and Apr 11–15, 2025 | n/a | Needs unauthorized values with [U] dates | **Blocked under Rule L** |

**Respondent changes** (SWS releases): household heads through December 2024, registered voters January to April 11–15, 2025, adults from April 23–28, 2025. No two populations are combined without being flagged.

## 4. Step 2: eligibility under the two protocols

### 4.1 Inputs (`feature_eligibility_by_protocol.csv`): 51 inputs

| Family (inputs) | Development protocol | Strict real-time protocol | Why they differ |
|---|---|---|---|
| News: FSSI, triggers, counts (12) | Use | Use | n/a |
| SWS: known value, change, age (3) | Use | Use; 3 rounds [V-single] need confirmation | n/a |
| Regional CPI: headline, food-minus-headline (4) | Use | Use (2021 values only from 2022-02-04) | n/a |
| ECB FX (1), FRED Brent (1) | Use | Use (daily; ≥ about 90 days' margin) | n/a |
| Poverty (1) | Use | Use (2022-08-15; 2024-08-15) | n/a |
| **Provincial CPI and derived: food_cpi, YoY and lags, cpi_dev, cpi_rel (7)** | Use via **proxy** | **Exclude** | Provincial date verified for 1 of 20 months; a proxy is not verification |
| Wholesale RMR (3) | Use (about 35-day schedule) | Exclude | Schedule seen only through PhilRice-hosted PSA metadata plus one example |
| LFS unemployment (3) | Use (practice) | Exclude | One dated example, no calendar |
| BSP remittances (3) | Use (practice) | Exclude | Pattern from 5 examples, no calendar; hand-curated |
| DOE diesel / gasoline (4) | Use | Exclude | Hand-curated, no per-value dates, 15 rows missing |
| ONI (1), drought alert (1, derived from ONI), IBTrACS typhoons (2), NASA POWER rainfall (3) | Use (revised; disclosed) | Exclude | Values differ from what was available historically (WD2) |
| Retail rice from psa_indicators (2) | **Exclude** | Exclude | OpenStat retail table covers 2012–2021 only; source of 2022–2025 values unresolved |
| **Usable** | **49 of 51** | **22 of 51** | n/a |

### 4.2 Training labels per origin (`origin_eligibility_by_protocol.csv`, definition A)

| Origins | Development: labels (rows) | Strict: labels | Role |
|---|---|---|---|
| 2021-Q4, 2022-Q1 | 0 | 0 | Training only |
| 2022-Q2, 2022-Q3 | 3 (15) | 0 | Training only |
| 2022-Q4 → 2025-Q1 | 4 → 13 (20 → 65) | **0** | **Exploratory** (reused) |
| 2025-Q2, 2025-Q3 | 14, 15 | 1 | Exploratory |
| 2025-Q4 | 15 (+2025-Q2 under A-adult) | 1 | Exploratory |
| 2026-Q1, 2026-Q2 | 15, 16 (+2025-Q2/Q3 under A-adult) | 1 | Disclosed check (outcome exposed) |
| 2026-Q3, 2026-Q4 | 16 (+2) | 1 | Protected final evaluation (**not yet valid**) |

**Every difference between the protocols has one cause:**

- Every label needs its quarter's final-month **provincial** CPI.
- That date is verified only for December 2024 (2025-01-13), so strictly only label 2024-Q4 qualifies, and only from the 2025-Q2 origin.
- The development protocol bridges the gap with WD1's proxy.

## 5. Step 3: training readiness

**An exploratory development experiment is supported by the eligibility table:**

- **Development protocol:** 49 inputs; 7–15 eligible training quarters (35–75 rows) at the eight exploratory origins 2023-Q3 to 2025-Q4; 16 at the 2026 origins.
- **Its results would be exploratory**, because the quarters have been reused and WD1/WD2 apply.

**A strict real-time evaluation is not supported:**

- **At most 1 eligible training label at any origin** under the strict protocol, and 22 usable inputs.
- **This includes the protected 2026-Q3/Q4 evaluation if it must meet the strict protocol.** If it is run under the development protocol, it must be reported with WD1/WD2 disclosed.

### Minimum requirements for the exploratory development experiment

| Category | Items |
|---|---|
| **Already available** | Definition A labels (16). Window frame with K1–K4 and rule W. National CPI dates (WD1 proxy basis). SWS rounds 2021–2025 with dates, including the 3 supplementary 2025 rounds as **inputs**. 2026 provincial CPI (raw). News, poverty, regional CPI, FX, Brent; plus the revised and practice-timed inputs under WD2/WD3. |
| **Needs manual source verification** | SWS June, September and November 2025 values and dates [V-single]. For a strict protocol only: 19 RSSO IV-A provincial CPI dates; official release calendars (PSA rice and LFS, BSP, DOE); the June 2026 SWS publication date (2026-Q4 input). |
| **Needs authorization** | (1) **Encoding WD1–WD6 and refined Rule L in experimental code** (not production) with unit tests, including feeding the supplementary SWS rounds into the experimental frame. (2) Building the separate sensitivity labels (A-adult, C, D). (3) Running the experiment. (4) Any change to the `backend/` scheduler setting. |
| **Must be excluded from strict evaluation** | Provincial CPI and its 6 derived inputs; wholesale rice; LFS; BSP; DOE; ONI and drought; IBTrACS; NASA POWER; retail rice (also excluded from development) |

**A defensible final evaluation is not possible yet.**

- **For development use:** it requires the protected 2026-Q3/Q4 freeze-then-collect procedure. It yields at most an untouched point estimate on ≤ 10 rows, which **cannot establish true accuracy of 75% or more**.
- **For a strict real-time claim:** it additionally needs the 19 provincial CPI dates.

## 6. Recommended next smallest task (awaiting your authorization)

**Implement the working decisions in experimental code only, with tests, and draft the pre-registration. Do not train or score.**

1. **Rule L enforcement** in a new `scripts/supplementary/` module: label publication = later of the last SWS round and the provincial CPI date (proxy flag for development); per-round SWS inputs, including the three supplementary 2025 rounds; the WD5 2018-base cut-off; and per-feature protocol masks from `feature_eligibility_by_protocol.csv`.
2. **Unit tests:**
   - no training label published at or after the origin;
   - no SWS input published after the origin;
   - strict-protocol masks exclude the listed inputs;
   - no pre-2021 values;
   - no 2026-Q3/Q4 outcome is present.
3. **A draft pre-registration**, to be hashed:
   - definition A as the primary label, with A-adult, C and D as sensitivities;
   - MODEL-B2 as primary; comparators MODEL-A configuration, the Eq. 3 rule and the latest-published-label baseline;
   - the metrics;
   - the statement that results are exploratory.

**Separately and immediately (your call):** set `SCHEDULER_ENABLED=false` for `backend/` before 2026-10-15 if the served model should not change unattended.

**Waiting for explicit authorization before doing either.**
