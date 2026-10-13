# aiPHeed: Post-Decision Action Plan, in Dependency Order (2026-10-09)

This plan accompanies `docs/ADVISER_DECISION_PACKAGE_2026-10-09.md`. **Nothing in it has started.**

- Each step lists what it depends on, what it unblocks, and what stays blocked.
- **No step trains a model, collects data, or changes production or the thesis without the approval named in it.**
- A machine-readable register is in `evidence/2026-10-09_readiness/action_register.csv`.

---

## Step 0: Safeguards (apply now; no further approval needed)

| # | Action | Blocks until lifted |
|---|---|---|
| 0.1 | No one working on the model searches for, opens or downloads SWS September or December 2026 hunger results. Avoid general SWS web searches whose summaries could reveal them. | Any contact with 2026-Q3/Q4 outcomes |
| 0.2 | Do not extend `SWS_COVERAGE_END = (2026, 2)` or the table in `app/ml/corpus/sws_hunger_fetcher.py`, and do not run `scripts/refresh_all_sources.py` for SWS | Any automatic import of later rounds |
| 0.3 | Log any accidental exposure (date, what was seen, which quarter); downgrade that quarter to "disclosed check" | n/a |

## Step 1: Adviser decisions

**Depends on:** this package.

| Decision | Unblocks | If not approved |
|---|---|---|
| D1 provincial CPI date rule | Rule L code for labels | Use the strict rule: label not eligible (no experiment) |
| D2 revised vintages | Use of ONI, IBTrACS and NASA POWER inputs | Primary model must exclude those inputs, or no experiment |
| D3 label definition (+ respondent base) | Fixed labels and threshold, needed for any run | Nothing can be pre-registered |
| D4 2018-base date | Early-fold eligibility | Defaults to the conservative 2022-02-04 |
| D5 final-test designation | The protected evaluation protocol | Only exploratory development possible |
| D6 2026-Q4 label published in 2027 | Whether 2026-Q4 counts in the final test | 2026-Q4 dropped; at most 5 rows (2026-Q3) |
| D7 collection authorization | Steps 3a and 3b | Development runs with the gaps disclosed; the protected evaluation stays blocked |
| D8 how 75% is judged | Reporting language | Point estimate with interval, as the default disclosure |

**Still blocked:** everything below.

## Step 2: Manual source verification

**Depends on:** D3 (for items 2.1 and 2.3) and D1 (for 2.5).

| # | Item | Needed for |
|---|---|---|
| 2.1 | Respondent base in the SWS April 2025 release | D3 consequences |
| 2.2 | June, September and November 2025 SWS release dates on the pages themselves (currently [L]) | Rule L for the 2025-Q2/Q3/Q4 labels and inputs |
| 2.3 | January and February 2025 SWS release dates | Only if D3 includes them |
| 2.4 | June 2026 SWS **publication date only** | SWS input for the 2026-Q4 forecast |
| 2.5 | RSSO IV-A monthly dates | Only if D1 = option (b) |

**Unblocks:** final Rule L date tables. **Still blocked:** model code and runs.

## Step 3: Authorized data collection

**Depends on:** D7 and Step 2.2.

| # | Collection | Volume | Unblocks |
|---|---|---|---|
| 3a | SWS Balance-Luzon values: April, June and September 2025 (and January/February 2025 if D3) | 3–5 values | 2025-Q2/Q3 labels; current SWS inputs for the 2025-Q4 fold and the 2026 forecasts |
| 3b | OpenStat `0012M4ACP23`, 01.1 Food, 5 provinces, January–June 2026 | 30 values | 2026-Q3/Q4 forecast inputs; the 2026-Q1 training label |

**Collection rules:**

- Store new values in a **new** supplementary file, recording the URL, publication date and fetch time.
- **No 2026-Q3/Q4 SWS values.**
- No change to production data.

**Still blocked:** model runs until Step 4.

## Step 4: Implement Rule L and pre-register

**Depends on:** Steps 1–3. This is experimental code only, not production.

1. **Encode** Rule L (L1–L6 as decided) and the D3 label definition in `scripts/supplementary/`.
2. **Add unit tests:**
   - label publication before the forecast date;
   - SWS input publication before the forecast date;
   - per-input release checks;
   - no pre-2021 values;
   - no 2026-Q3/Q4 outcome present anywhere in the inputs.
3. **Write and hash a pre-registration** that fixes:
   - the label definition, threshold and Rule L;
   - the primary configuration (MODEL-B2) and comparators (MODEL-A configuration, the Eq. 3 rule, carry-forward of the latest published label);
   - the D2 sensitivity variant;
   - the metrics (accuracy, F1, ROC-AUC, Brier, HIGH recall, within-quarter AUC, confusion matrix);
   - the scoring script;
   - the statement that development results are exploratory.

**Approval:** the adviser approves the pre-registration. **Still blocked:** the protected evaluation until Step 6.

## Step 5: Exploratory development run

**Depends on:** Step 4 approval.

- **Run:** walk-forward on 2021–2025 under Rule L. Every comparator gets the same forecast dates and information.
- **Report:** all results, labelled **exploratory** (these quarters have been reused). Nothing selected here may be described as validated.

**Unblocks:** freezing the primary configuration for Step 6.

## Step 6: Protected 2026 evaluation

**Depends on:** D5 (and D6), Step 3b, and Step 5 complete.

1. **Produce forecasts** for 2026-Q3 (and Q4 if D6 allows) from inputs published before each forecast date. Label them **retrospective simulations**: the forecast dates have passed and the inputs are current vintages.
2. **Hash** the forecasts, configuration, inputs and code into a dated manifest, and hand the hashes to the adviser.
3. **Only then collect** the 2026-Q3/Q4 SWS Balance-Luzon values and the matching CPI, ideally by someone other than the modeller, into a separate file. The 2026-Q4 SWS round will not be published before 2027.
4. **Score once** with the pre-registered script and report every quarter, with the paired comparison against the baselines.
5. **Report 2026-Q1/Q2** only as disclosed, non-independent checks.

**What it can establish:** one untouched point estimate on at most 10 rows, with a wide interval. **It cannot establish true accuracy above 75%.**

## What stays blocked regardless

- Any change to production code, production data, the hand-curated SWS table, frozen forecasts or thesis chapters, without separate explicit approval.
- Any use of 2026-Q1/Q2 outcomes as independent evidence.
- Any retuning after 2026 outcomes are seen.
- Any claim that the thesis meets the 75% requirement on the basis of the development results or a single small test.
