# Protocol validity study and amendment options (v3)

**What this is:** evidence for a decision, not the decision. Nothing frozen was changed, no model was refitted or tuned, and nothing was downloaded.

**Tags:**
- VERIFIED: computed by a command, output saved;
- INFERRED: reasoning from verified numbers or documents;
- NOT VERIFIED.

**Command:** `python -I backend/scripts/v3_protocol_validity.py`
- **Outputs** (`docs/aipheed/v3/results/`): `v3_tolerance_options.csv`, `v3_band_options.csv`, `v3_direction_options.csv`, `v3_resolution.csv`, `v3_nowcast_h1.json`, `v3_q.json`, `v3_run.txt`.
- **Rows:** the frozen S-U rows (Leads 1–4: 44 / 40 / 36 / 32), identical to MODEL_REPORT_V2.
- **Status of every number: DEVELOPMENT** (all quarters were seen before).

**How the alternatives were fixed before computing:** each rule below was written in the script before it ran, from one of three sources:
- the frozen protocol's own information-only sensitivities (lock T1: "0.5× and 2× tol; and the SE implied by the published margin at p = 0.5");
- SWS's reporting convention (the published 95 % margin);
- earlier project documents (Chapter I 11.3 %; E110 B3 > 20 % and B4 "rise > own margin").

No threshold was searched or chosen by its result.

**Oracle bound:** perfect knowledge of the current true hunger level, with the true level then moving as a random walk.
- Primary: innovation variance q = 12.26 pp²/quarter, estimated on all data (as DIAGNOSIS Q1).
- **Sensitivity:** q = 4.51, estimated only from rounds published before 2024 (the calm regime). The bound depends on which regime the future resembles, and that is unknowable in advance.

---

## Task 1: Is the frozen tolerance valid for this target?

### 1.1 Where the measurement error comes from (VERIFIED from `backend/data/forecasting/sws_area_rounds.csv`)

| Rounds | Stated area sample size and margin | Status |
|---|---|---|
| 2023-Q2 … 2026-Q3 (14 rounds) | Each row records n (300, 600 or 1 080 per area) and the area margins (±3 to ±6 pp), with the SWS release URL | **VERIFIED as recorded** in the repository. The source pages were not re-opened in this session (no web access used). |
| 2021-Q2 … 2023-Q1 (9 rounds) | ±6 pp recorded. E110 PROTOCOL.md: "Where a 2021–22 margin is not stated, ±6% (the 300-per-area design) is assumed." Only 2021-Q3 states n = 300. | **NOT VERIFIED:** 8 rounds carry an assumed margin |
| Every Lead-2 target quarter (2024-Q1 … 2026-Q3) | Published margins | VERIFIED as recorded: no target is scored against an assumed margin |

**What SWS's margin is** (INFERRED): ±4 at n = 600 and ±6 at n = 300 match 1.96 × √(0.25/n) exactly. So the published margin is the **simple-random-sample margin at p = 0.5, with no design effect**.

**NOT VERIFIED; needed:** whether SWS publishes design effects or cluster-adjusted errors (§5, item 1). I did **not** estimate measurement noise from the scored outcomes for the tolerance options. The same-quarter round-pair statistic in DIAGNOSIS Q1 (RMS z 1.84) uses outcome values, so it is cited as context only and enters no option below.

### 1.2 The frozen tolerance compared with the measurement (VERIFIED, `v3_resolution.csv`, Lead 2, 40 rows)

| Quantity | Median |
|---|---|
| Frozen tolerance, 1.645 × binomial SE at the observed p | **±3.78 pp** |
| Published 95 % margin of the target quarter | ±5.70 pp |
| Frozen tolerance ÷ published margin | **0.68** |
| SD of the difference between two independent SWS readings (latest vs target) | 3.09 pp |
| 95 % least significant difference between two readings (1.96 × that SD) | **±6.05 pp** |
| Lead-2 rows where the frozen tolerance is narrower than that difference | **40 of 40** |

**The decisive check: the "nothing changes" world.**
- Suppose true hunger did not move at all between the latest reading and the target.
- The two survey readings would still differ by more than the frozen tolerance about 23 % of the time, purely from sampling.
- So **persistence would score only 76.7 %** at Lead 2 (Leads 1–4: 76.5 / 76.7 / 77.3 / 78.2 %).
- In other words, 75 % under the frozen tolerance needs essentially constant hunger plus luck.

**Plain answer:**
- The frozen tolerance is **valid for its stated purpose**: a forecast of the true level that lands within it cannot be told apart from the reference by the reference's own 90 % precision.
- It is **tighter than the survey can resolve when one reading is compared with another.** It is 0.68 of SWS's own margin, and narrower than the 95 % least significant difference on every Lead-2 row.
- **It also tightens as surveys improve:** larger n gives a smaller SE and a smaller tolerance, so better measurement makes the target harder, not easier (INFERRED from the formula).

## Task 2: Option table (compute, do not choose; all DEVELOPMENT)

**Columns:**
- **Oracle:** analytic bound with all-data q; in brackets, the pre-surge q sensitivity.
- **Persistence:** the latest SWS reading.
- **V2:** the v2 selected model, which is persistence (MODEL_REPORT_V2).

### (a) Frozen tolerance, 1.645 × binomial SE: baseline

| Lead | Oracle (pre-surge q) | Persistence | V2 |
|---|---|---|---|
| 1 | 0.49 (0.66) | 0.48 | 0.48 |
| **2** | **0.43 (0.60)** | **0.40** | **0.40** |
| 3 | 0.38 (0.55) | 0.36 | 0.36 |
| 4 | 0.35 (0.52) | 0.38 | 0.38 |

### (b) Tolerance derived a priori from published margins

The formulas were stated before computing; neither is fitted.
- **b1:** 1.645 × SE_pub, with SE_pub = the quarter's published margin ÷ 1.96 (rounds combined as √ΣSE²/k). This is listed in the frozen T1 as an information-only sensitivity, so it was pre-specified.
- **b2:** the published 95 % margin itself (1.96 × SE_pub), SWS's own reporting convention.

| Lead | b1 Oracle (pre-surge) | b1 Persistence = V2 | b2 Oracle (pre-surge) | b2 Persistence = V2 |
|---|---|---|---|---|
| 1 | 0.60 (0.77) | 0.57 | 0.68 (0.85) | 0.61 |
| **2** | **0.51 (0.70)** | **0.48** | **0.59 (0.78)** | **0.50** |
| 3 | 0.46 (0.64) | 0.50 | 0.53 (0.73) | 0.53 |
| 4 | 0.42 (0.60) | 0.47 | 0.49 (0.68) | 0.59 |

**Information only** (frozen T1 lists it; not proposed): 2 × the frozen tolerance gives an oracle of 0.73 (0.90) and persistence of 0.68 at Lead 2.

### (c) Categorical correctness (bands from existing documents)

| Band | Lead | Share HIGH | Majority class (hindsight) | Oracle | Persistence = V2 |
|---|---|---|---|---|---|
| **c1:** HIGH if > 11.3 % (Chapter I, served P0H4 hunger part) | 2 | **0.975** | 0.975 | 0.83 | 0.825 |
| c1 | 1 / 3 / 4 | 0.95 / 1.00 / 1.00 | same | 0.86 / 0.81 / 0.78 | 0.86 / 0.81 / 0.78 |
| **c2:** HIGH if > 20 % (E110 B3, research-defined; SWS has no official threshold) | 2 | 0.60 | 0.60 | 0.73 | **0.55** |
| c2 | 1 / 3 / 4 | 0.55 / 0.67 / 0.75 | same | 0.75 / 0.71 / 0.69 | 0.66 / 0.53 / 0.53 |

**Tercile bands:** no project document defines tercile bands as a scoring category. "High tercile" appears only as an evaluation slice. Defining terciles now would be a new, data-derived choice, so it is **not computed**.

### (d) Direction of change

| Rule | Lead | Share of rows that rose | Oracle | Persistence = V2 |
|---|---|---|---|---|
| **d1:** E110 B4, rise above the latest reading by more than the published margin | 2 | 0.375 | 0.80 | 0.625 (= share of no-rise; balanced accuracy 0.50) |
| d1 | 1 / 3 / 4 | 0.30 / 0.39 / 0.38 | 0.84 / 0.77 / 0.75 | 0.70 / 0.61 / 0.63 |
| **d2:** sign, up or down | 2 | 0.675 up | 0.58 | undefined: persistence predicts no change (scored 0.5) |

### (e) Nowcast / Lead 1 only

- **Lead 1, P-DASH:** see (a) and (b) Lead 1. Frozen oracle 0.49 (0.66), persistence 0.48.
- **h = 1, one quarter past the newest reading** (as in the frozen secondary policy P-REL), all 68 consecutive area pairs 2021–2026:

| Tolerance | Oracle (all-data q) | Persistence | Persistence if hunger never changed |
|---|---|---|---|
| (a) frozen | 0.59 | 0.49 | 0.76 |
| (b1) 1.645 × SE_pub | 0.75 | 0.63 | 0.89 |
| (b2) published margin | **0.83** | **0.74** | 0.94 |

### What each option supports

| Option | Claim it supports | What it cannot support | Still answers "forecast numerical food insecurity at Lead 2"? |
|---|---|---|---|
| (a) frozen | "Forecasts match SWS within the survey's 90 % sampling half-width" | Nothing more. Its own ceiling is 43–60 %, and even a no-change world gives only 77 %. | Yes: the original question, with an unattainable bar |
| (b1) 1.645 × SE_pub | Same, measured with SWS's published margin instead of the observed-p SE | 75 % at Lead 2: oracle 0.51 (0.70) | Yes, numerical; the bar stays below 75 % even in the calm regime |
| (b2) published margin | "Forecasts fall within SWS's own published margin of error" | 75 % at Lead 2 except in a calm regime: oracle 0.59 (0.78). Persistence reached 0.50. | Yes, numerical. Achievable only if hunger stays calm, and no model has shown it. |
| (c1) 11.3 % band | "Correct HIGH/LOW class" | Anything. 97.5 % of rows are HIGH, so persistence (0.825) loses to always-HIGH (0.975). The label is saturated (as already found in E48 and E51). | **No:** a class, and a degenerate one |
| (c2) 20 % band | "Correct side of 20 %" | 75 %: oracle 0.73; persistence 0.55 < majority 0.60 | No: categorical, research-defined threshold |
| (d1) rise > margin | "Detects significant rises" | Any skill today: persistence's 0.625 is the no-rise base rate (balanced 0.50) | No: an event, not a level |
| (d2) sign | "Direction of change" | 75 %: oracle 0.58 | No |
| (e) h = 1 with the published margin | "One-quarter-ahead outlook within SWS's margin" | **Lead 2** | **No:** it answers Lead 1 / nowcast, not Lead 2 |

**Bottom line of Task 2** (INFERRED from the VERIFIED table):
- **No option makes 75 % at Lead 2 attainable in the all-data regime.**
- **Only (b2), the published margin, crosses 75 % at Lead 2, and only under calm-regime dynamics (0.78).** Even there, the best existing forecaster scored 0.50 on the development rows.
- Options that look high, c1 and d1, do so only through degenerate base rates.
- 75 % is within the oracle's reach for a **one-quarter nowcast scored against the published margin** (0.83; persistence 0.74). That would change the objective from Lead 2 to Lead 1.

## Task 3: Legitimacy checklist

| Option | Fixed before outcomes? | Derived from measurement properties? | Applicable to unseen data only? | Comparable to baselines? | Risk of being read as goal-post moving |
|---|---|---|---|---|---|
| (a) frozen | Yes (E131, 2026-10) | Yes (binomial SE, observed p) | Already applied to development data | Yes | None (it is the original) |
| (b1) 1.645 × SE_pub | **Yes:** listed in frozen T1 as a sensitivity before any score | Yes (published margin) | Yes, if an amendment says so | Yes, same rows and baselines | **Low to moderate.** Pre-listed, but promoting a sensitivity to primary after seeing failure is a change of rule. |
| (b2) published margin | SWS's convention predates the project. This study only computed it; it was not in the frozen protocol. | Yes (SWS's own margin) | Yes, if an amendment says so | Yes | **Moderate.** Defensible (it is the survey's own resolution), but it is adopted after the frozen rule failed and is 1.5 × wider. |
| (c1) 11.3 % | Yes (Chapter I) | No (policy threshold) | Yes | Degenerate (always-HIGH wins) | **High:** passes by saturation |
| (c2) 20 % | Yes (E110) | No | Yes | Yes | High: research-defined, and not numerical |
| (d1) rise > margin | Yes (E110 B4) | Partly (uses the margin) | Yes | Base rate dominates | High |
| (d2) sign | Not in any document | No | Yes | Persistence undefined | High |
| (e) h = 1 / Lead 1 | Lead 1 and P-REL are frozen (E1) | n/a | Yes | Yes | **Moderate:** honest, but it abandons the Lead-2 objective |

## Task 4: Amendment template

`docs/aipheed/v3/PROTOCOL_AMENDMENT_DRAFT.md`: a **draft, not active**. It has blanks for the chosen metric, its justification, adviser sign-off and an effective date, and it applies to sealed/future quarters only. Original-protocol results are always reported alongside.

## Task 5: Data path (ranked; nothing downloaded)

| Rank | Measurement | Expected gain | What it can change | Exact access steps |
|---|---|---|---|---|
| 1 | **SWS round documentation:** area sample sizes, margins and any design effect, for 2021-Q2 … 2023-Q1 and all later rounds | No forecast gain. **High validity gain:** it settles Task 1 (whether noise exceeds the binomial SE) without using outcomes, and replaces the 8 assumed ±6 margins. | Tolerance validity; options (b1)/(b2) | 1. For each round, open the SWS release at sws.org.ph (Social Weather Reports; the URLs are in the `source` column of `sws_area_rounds.csv`). 2. Copy the "Survey Background" paragraph: sample size per area, margin of error. 3. Ask SWS whether design effects are published: SWS Survey Data Library, or an email request to SWS, citing student research. 4. Add the values with their source URLs and re-run `v3_protocol_validity.py`. |
| 2 | **PSA regional quarterly Labor Force Survey** (unemployment, underemployment by region) | **Uncertain, modest.** It is the only untested leading-signal candidate. National unemployment change showed ρ ≈ 0.09–0.11 with future hunger change (DIAGNOSIS Q3), so a large gain is not expected (INFERRED). To reach 75 % it would have to explain ≈ 85 % of the 3-quarter change variance. | Leading signal (Lead 2) | 1. Go to PSA OpenSTAT (openstat.psa.gov.ph) → Labor and Employment → Labor Force Survey → the regional quarterly tables. 2. Export CSV for 2021 onward (study window W1). 3. Record each quarter's PSA press-release date (psa.gov.ph, LFS releases) as the availability date for `as_of`. 4. Register the hypothesis in a new pre-registration before testing (Q3 design). |
| 3 | **CBMS 2024 FIES** (provincial, municipal) | No Lead-2 gain: annual or one-off, not quarterly. **Essential** for any provincial or LGU claim (`AWAITING_GROUND_TRUTH` today). | Provincial measurement, validation | 1. Write a formal data request to the PSA (CBMS Service / PSA Regional Statistical Services Office IV-A), signed by your adviser, stating purpose, variables (FIES items, province and municipality codes) and data-privacy safeguards. 2. Expect a data-sharing agreement. 3. Alternatively, request from each LGU's CBMS focal office. |
| 4 | DOST-FNRI ENNS food-insecurity estimates | None for Lead 2 (irregular, regional) | Validation reference | FNRI ENNS reports (enutrition.fnri.dost.gov.ph); request regional tables from FNRI |
| 5 | Higher-frequency prices (DA Bantay Presyo, PSA rice prices) | Low: market CPI showed no repeatable signal (Q3) | Context | DA price monitoring pages; PSA OpenSTAT price tables |

## Recommendation (a RECOMMENDATION, not a decision)

1. **Keep the frozen protocol as the primary, reported result:** Lead 2 not achieved, 40 %; oracle ≤ 0.43–0.60. Changing it now would be read as moving the goal-posts, and the evidence says no legitimate re-scoring rescues Lead 2.
2. **If an amendment is wanted, the most defensible candidate is (b2), the published SWS margin, applied only to sealed/future quarters,** with (a) always reported beside it.
   - **Justification:** it is the survey's own resolution, the frozen tolerance is narrower than the 95 % least significant difference on every row, and it is set without any outcome.
   - **State plainly:** even under (b2), 75 % at Lead 2 is reachable only if hunger stays calm (oracle 0.59 / 0.78), and no current model has done it (0.50).
3. **If the thesis objective may be restated, the only honest place a 75 % claim could live is a one-quarter nowcast scored against the published margin** (oracle 0.83; persistence 0.74 in development). It would still have to be confirmed on unseen quarters.
4. **Reject c1, c2, d1 and d2 as the primary objective:** they pass through saturation or base rates, or stop being numerical forecasts.
5. **Do data item 1 (SWS round documentation) first.** It costs no download authority beyond reading SWS's own pages, and it settles the validity question without outcome data.

## Decisions only you and your adviser can make

1. Whether to amend the scoring rule at all, or report the frozen result as the finding.
2. If you amend: which metric (b1, b2 or another), and that it applies to future quarters only.
3. Whether the thesis objective stays "Lead 2" or is restated as a Lead-1 nowcast.
4. Whether to change the 75 % figure itself. This study does not propose one; any new figure must be justified independently of these results.
5. Authorising external data: SWS documentation, regional LFS, a CBMS request (signed by the adviser).
6. Adviser sign-off on the amendment template and its effective date.

## Hash re-verification at the end

VERIFIED (`v3/results/v3_hashes.txt`), all unchanged; the lock, pre-registration and seal tests ran 7 passed:

| Item | SHA-256 |
|---|---|
| `PROTOCOL_LOCK.md` | `8bae6962…dd0d3` (equals the stored value) |
| `PREREGISTRATION.md` (LF-normalised) | `90ad51a9…a691b` |
| v2 seal | `e88f7bb2…25d7` |
