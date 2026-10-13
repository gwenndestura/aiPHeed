# E8 Protocol Review, Revision r2

**Status: 2026-10-12. Review document only.** It does not replace E8 v3. E8 v1, v2, v3 and the earlier review files are unchanged. Nothing was run, scored, rescored or re-thresholded.

**Status codes:**

| Code | Meaning |
|---|---|
| **DOC** | Resolved in documentation: the corrected rule is written here and needs only adoption into the protocol text (approval EV-1) |
| **EVID** | Requires evidence that does not yet exist or was not checked |
| **APPR** | Requires a decision or approval from you |

**Sources:**

- the E8 v3 documents;
- the first review (`E8_v3_review/1_E8_V3_CONSISTENCY_REVIEW.md`, IDs such as C1 and L1);
- code read in this project (`risk_score_v2.py`, `datadriven_trainer.py`, `devprotocol_rule_l.py`);
- served-artifact metadata;
- the column header of the exposed 2026-H1 CPI file.

**No data-access guarantee and no blind-test guarantee is made anywhere in this document.**

---

## Summary

| # | Issue | Status |
|---|---|---|
| R1 | 2026-Q3 is not an untouched blind test | **DOC** (adoption: EV-1) |
| R2 | 2026-Q4 can qualify only under stated conditions | **EVID + APPR** |
| R3 | Strict release-date rule vs proxy-dated provincial CPI | **DOC** for the rule; **EVID** for verified dates |
| R4 | Served M6 threshold 10.843 vs E8 outcome threshold 14.345 | **DOC** (no threshold changed) |
| R5 | Brier only for probability outputs; a separate comparison for stress values | **DOC**; margins **APPR** (EV-2) |
| R6 | Ranking metric and its input | **DOC** |
| R7 | No allowlisted 2026-H1 food CPI index-level source | **APPR** (EV-3) |
| R8 | The prior aggregate disclosure and its consequences | **DOC** |
| R9 | What happens if Q4 is unavailable or its inputs cannot be verified | **DOC** |

---

## R1. 2026-Q3: not an untouched blind test (DOC)

**Facts:**

1. 2026-Q3 ended on 2026-09-30. The E8 design (arms, LightGBM settings, thresholds, margins) was developed on 2026-10-11 and 2026-10-12, **after the quarter ended**.
2. On 2026-10-11, one aggregate containing 2026-Q3 rows was printed from the production `panel.parquet` (see R8).
3. Some Q3 outcome components may have been published before the design work, for example July and August 2026 CPI. **Their release dates were deliberately not looked up**, so this is unknown, not established.

**Corrected rule.** 2026-Q3 is an **exposure-qualified historical simulation**:

- Its results may be reported **descriptively**, labelled "exposure-qualified".
- It **cannot** be called a blind test, an untouched test or a held-out test.
- It **cannot** support a gross-failure conclusion, an added-value statement or any performance claim.

Its outcome components (P1/P2 for Q3) stay protected until outcome collection is approved (EV-7), so the qualification does not get worse.

## R2. 2026-Q4: may qualify, only under all of these conditions (EVID + APPR)

**What makes Q4 different (established from metadata):**

- No outcome component of 2026-Q4 (October–December 2026 food CPI; any SWS round with fieldwork from 2026-10-01) can be inside any file committed or last modified before that information existed.
- The 2026-Q4 rows in production `psa_indicators.parquet` were committed on 2026-09-29, **before Q4 began**, so they cannot contain Q4 outcome values.
- **This does not establish that no Q4 outcome information has been published or seen since 2026-10-01.** That is unknown.

**Q4 qualifies as a prospective-outcome evaluation (outcome unseen at freeze, inputs historically simulated) only if every condition holds:**

| # | Condition | Evidence needed | Status |
|---|---|---|---|
| Q4-a | Protocol text, evaluation code and margins are approved and **hashed before** any Q4 outcome information is available | Hash records with timestamps | **APPR** (EV-1, EV-2) |
| Q4-b | Forecasts are generated and **frozen (hashed, read-only) before** the first Q4 outcome component is published | Freeze manifest timestamp, compared after collection with the documented first-release dates | **EVID**: first-release dates are unknown and must not be looked up now. The SWS Q4 fieldwork and publication dates are unknown. October CPI is *expected* in early November under PSA's documented first-week practice (a schedule, not a verified date). **Freezing before any of these is the only safe course; the later the freeze, the weaker the claim.** |
| Q4-c | **No one involved** sees any Q4 outcome before the freeze | Process evidence only: deny-list, session rules, scheduled-task decision | **EVID**, and **it cannot be proven.** Hash checks show that files did not change, not that nothing was read. The scheduled tasks remain enabled (risk R1–R5). |
| Q4-d | Input release dates at C4 (2026-10-01) are documented | Release-date evidence per input (see R3) | **EVID.** Currently proxy-dated (provincial CPI), schedule-dated (national series) or uncited (poverty). |

**Outcome classification:**

- All four conditions hold, with verified input dates: **"prospective-outcome evaluation, inputs verified"**.
- Q4-a to Q4-c hold, but inputs are only proxy-dated: **"prospective-outcome evaluation, inputs proxy-dated (unverified)"**. No leakage-safe claim.
- Any of Q4-a to Q4-c fails, or cannot be evidenced: Q4 is **exposure-qualified**, the same as Q3.

**Q4 is not guaranteed to be a valid blind test.**

## R3. The strict release-date rule vs proxy-dated provincial CPI (DOC; verified dates EVID)

**The conflict.** v3 H1 says a value is usable "only if its publication date is documented". v3 H2–H4 then use provincial CPI inputs and training labels whose dates are **estimates**: the national release date plus 14 days (WD1, `PROXY_DAYS = 14`). Read literally, H1 removes every provincial-CPI input and every training label except 2024-Q4, so no model arm could be trained.

**Corrected rule (two tiers):**

| Tier | Rule |
|---|---|
| **Eligibility** | A value may be used only if a **dated** availability is recorded and falls strictly before the cutoff. The date may come from: (a) a **verified** release (a dated primary or archived source); (b) an **estimated** date from a pre-stated rule (WD1 proxy: national + 14 days; documented schedule lag in `SCHEDULE_DAYS`); or (c) a month-level date with no cited source (poverty). A value with no date is excluded. A value is **never** treated as available because it appears in a dataset. |
| **Verification status** | A simulation using **any** estimated (b) or uncited (c) date is labelled **"inputs proxy-dated (unverified)"** and excluded from leakage-safe claims. Only (a) counts as verified. |

| Input family | Current status |
|---|---|
| SWS March 2026 round (2026-05-12) | **Verified** |
| SWS November 2025 round | Verified (single source) |
| SWS June 2026 round | **No date**, so excluded |
| Provincial food CPI (except 2024-Q4) | **Estimated** (WD1 proxy) |
| National series | **Estimated** (schedule) |
| 2023 poverty | **Uncited** month ("August 2024") |

Upgrading to "verified" needs dated RSSO IV-A releases (EVID). To avoid any exposure, these can be collected **after** outcome collection (EV-6/EV-7). Verifying later can only confirm or downgrade the status; it cannot change frozen forecasts.

## R4. Served M6 threshold 10.843 vs E8 outcome threshold 14.345 (DOC; no threshold changed)

**Facts (served metadata and code):**

- Both served artifacts (`data/revised/*_meta.json`) use **τ = 10.84335**, as of 2023-10-01, from 8 labelled quarters.
- E8 defines its outcome event at **τ = 14.345**, as of 2026-07-01, from 16 labelled quarters.
- **Both are the median stress of the labels published before their as-of date** (`risk_score_v2.reference_threshold`).
- The event is strict: HIGH if stress > τ (`classify`).

**Resolution, with no rescoring and neither threshold altered:**

1. **E8 scores every arm only against the E8 outcome event (stress > 14.345).** Every model arm, including the M6 procedure (A3/A4), is **refitted inside E8** on training labels defined at 14.345. "A4 M6 as served" is renamed **"A4 M6 procedure, refitted at τ_E8"**.
2. **The served artifacts (τ = 10.843) are not evaluated by E8.** Their HIGH/LOW calls must not be compared with E8 outcomes. Any descriptive look at them uses their own τ and is labelled as such.
3. **The served dashboard keeps τ = 10.843.** Whether to change it is a separate decision (DB-1); it is not proposed here.
4. **Thesis text** must name the threshold behind each claim: "served classification: τ = 10.843 (as of 2023-10-01)"; "E8 evaluation: τ = 14.345 (as of 2026-07-01)".

## R5. Brier only for probabilities; a separate comparison for stress values (DOC; margins APPR)

| Output type | Arms | Metrics |
|---|---|---|
| **Probability** (classifier fits) | A1c, A2c, A3c, A4c | **Brier score.** Quarter mean over provinces with a probability; INSUFFICIENT_DATA rows are excluded from the mean and their count reported. Reference: the uninformative constant p = 0.5 (Brier 0.25). Also HIGH/LOW calls at p ≥ 0.50. |
| **Predicted stress** (regressor fits and stress-type baselines) | A1r, A2r, A3r, B1 (last published stress), B3 (SWS input + 2 × `cpi_rel`), B4 (SWS input) | **Regional-level error** = \|mean predicted stress − observed quarter mean\|. The observed mean equals SWS_T, because the provincial deviations d sum to zero. **Province MAE.** HIGH/LOW calls at predicted stress > 14.345. |
| **Fixed calls** | B5 (always HIGH, always LOW) | Number of correct calls only |

**Brier is never computed for B1, B3, B4 or B5.** Correct-call counts are comparable across all arms, but they are descriptive (5 provinces per quarter).

**Gross-failure margins proposed for approval (EV-2).** These replace v3 §8.1's Brier-vs-B1 criterion.

| Criterion | Rule | Justification |
|---|---|---|
| G-P (probability arms) | Quarter Brier > 0.25 + 0.10 = **0.35** | Clearly worse than an uninformative forecast |
| G-S (stress arms) | Regional-level error worse than B4 by more than **6.0 points** | Recorded Balance-Luzon sampling errors for the 2025 rounds are ±4% (n = 600) and ±6% (n = 1,200 nationwide; the June 2025 file) |
| G-R (ranking) | **≤ 3** concordant pairs out of 10 | See R6 |

## R6. Ranking metric (DOC)

| Element | Definition |
|---|---|
| What is ranked | **Predicted stress** from the regressor fits (A1r–A3r) and the stress-type baselines (B1, B3). B2 ranks by `cpi_rel`. **Predicted probabilities are not used for ranking.** Shallow trees give tied probabilities, and the null distribution assumes untied scores. |
| Observed target | Observed provincial deviation d(p, T) within the quarter. Within a quarter this gives the same order as observed stress, since SWS_T is common to all provinces. |
| Metrics | Concordant pairs out of 10 (ties count ½); Kendall τ-b; whether the top province was identified |
| Null reference | For untied scores and 5 provinces, P(≤ 3 concordant) = 29/120 = 0.24. Ties in predicted stress are reported. If any occur, the null reference is marked approximate. |
| No ranking ability by construction | B4 and B5 |

## R7. No allowlisted 2026-H1 food CPI index-level source (APPR)

**Fact (column header checked):**

- The only allowlisted 2026-H1 CPI file, `provincial_food_cpi_yoy_2026H1_raw.csv`, contains **`food_cpi_yoy_pct_raw` only**.
- `food_cpi` (index level) is in A2 (v3 §2) and in M6's provincial-government group (`datadriven_trainer.GROUPS["GP"]`).
- Its 2026-Q1/Q2 input values therefore have **no approved source**.

**Not allowed:**

- inferring index levels from year-on-year values;
- using `cpi_full.parquet` (a potential carrier);
- leaving the column structurally missing at forecast time while it is present in training.

**Decision needed (EV-3), choose one:**

1. **Drop `food_cpi` (index level) from A2 and from A3's pool before the freeze.** Recommended: it keeps all year-on-year features, and `cpi_rel`, `cpi_dev` and the year-on-year lags are unaffected.
2. Approve a new, date-limited collection of the January–June 2026 index-level series from the same OpenStat table, with the same safeguards as the 2026-10-09 collection, hash-recorded.

## R8. The prior aggregate disclosure and its consequences (DOC)

**What happened (from the v2 §4 disclosure, carried into v3 §4):**

- On 2026-10-11, one aggregate was printed from production `data/thesis/panel.parquet` (a P3 file): the **2026-Q1 to Q3 `label_cpi` HIGH share, 0.93**.
- A quarter list was also printed.
- No row values were reported as viewed.

**What it reveals:**

- `label_cpi` is the production label: food CPI index above its trailing 24-quarter mean + 1σ in two consecutive quarters.
- The aggregate mixes exposed Q1/Q2 rows with protected Q3 rows.
- It says that most 2026-Q1 to Q3 rows were `label_cpi` HIGH, which is consistent with the index-trend artifact found earlier (an earlier session record notes `label_cpi` was HIGH for 100% of 2024 rows; not re-verified).
- It reveals **no Equation 3 component directly**: neither SWS_Q3 nor the provincial year-on-year gap d.
- Its information about the E8 outcome is **limited but not zero**, and cannot be quantified.
- The provenance of the Q3 rows (partial or placeholder) is unknown.

**Consequences for claims:**

1. 2026-Q3 is exposure-qualified (R1).
2. Design choices made on or after 2026-10-11 (E3 settings, E4–E7, the scoring redesign, E8) cannot be shown to be independent of the aggregate. They are disclosed as made after it.
3. The aggregate contains **no 2026-Q4 rows**, and no Q4 outcome data existed when the source file was committed. It does not by itself affect Q4.
4. The disclosure must appear in the thesis methods and limitations text wherever E8 results are reported.

## R9. If Q4 is unavailable or its inputs cannot be verified (DOC)

**No fallback converts an incomplete test into a valid result.**

| Situation | What E8 reports | What it may **not** claim |
|---|---|---|
| Q4 outcome not published before the thesis is finalized | No blind evaluation result. Frozen Q4 forecasts preserved with hashes for a later addendum. Q3 exposure-qualified, descriptive only. | Any performance, gross-failure or added-value conclusion |
| Q4 freeze cannot be evidenced as earlier than the first Q4 release (Q4-b), or outcome exposure is suspected (Q4-c) | Q4 reclassified as exposure-qualified, descriptive | Any blind-test wording |
| Q4 outcome available, conditions Q4-a to Q4-c met, inputs proxy-dated | "Prospective-outcome evaluation, inputs proxy-dated (unverified)", **single quarter**. G-P, G-S and G-R reported as **single-quarter indications**, not gross-failure conclusions. | Leakage-safe performance; gross failure as established; added value |
| As above, with inputs verified | "Prospective-outcome evaluation, inputs verified", single quarter. Same single-quarter limits. | Added value (that needs ≥ 8 blind quarters); significance; "best model" |
| Q4 inputs cannot be dated at all for an arm | That arm is excluded from the Q4 evaluation and the exclusion reported | — |

**Effect on v3.** v3 assumed two blind quarters. Under r2 there is **at most one candidate blind quarter (2026-Q4)**, and its status is conditional. The v3 requirement that gross failure hold "in both blind quarters" can no longer be met. Gross failure therefore becomes **not assessable as a conclusion**; only single-quarter indications are possible.

---

## Other open items carried over from the first review

| ID | Item | Status |
|---|---|---|
| C2 | v3 H8 states the design preceded any Q3/Q4 outcome; that is false for Q3 (R1, R8) | **DOC** (correct H8 on adoption) |
| C5, C6 | Rice and national-series wording in the leakage checklist §A | **DOC** (follow approval-checklist defaults) |
| L2 | Descriptive check on exposed quarters is undefined for training quarters | **APPR** (define origins, or limit to 2026-Q1/Q2) |
| P1 | "No forecast exists for 2026-Q3/Q4" overclaims; production prediction files are unchecked carriers | **DOC** (narrow the wording) |
| S6 | Which system the thesis documents (production `backend/` vs the isolated backend) | **APPR** |
| P11 | At least 11 test files load carriers (risk map §1) | **APPR** (T-1/T-2 in the approval checklist) |
