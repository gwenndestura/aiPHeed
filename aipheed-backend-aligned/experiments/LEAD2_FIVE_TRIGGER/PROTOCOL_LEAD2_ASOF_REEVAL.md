# PROTOCOL_LEAD2_ASOF_REEVAL: Lead 2 under evidence-based CPI availability (frozen 2026-10-29, before any score)

This file's SHA-256 goes in `runner/ASOF_REEVAL_SHA256.txt`. It is committed before `runner/asof_reeval.py` is run.

## Status

- **Requested by.** The owner, 2026-10-29: re-evaluate Lead 2 using only information that was publicly available at each original forecast issue date.
- **What it is not.**
  - It is not the single re-score of `ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md` rule 3. That re-score needs every refreshed month verified, and it stays blocked.
  - Its results are a labelled diagnostic. They do not adopt, serve or count any candidate.
- **What it changes.** No criterion (R1-R7, `final.adoption_rule`), candidate column set, grid, seed, target, threshold, evaluation row or sealed file.
- **Sealed files.** The sealed prospective files are not read for fitting or tuning.

## 1. Availability definition

**Unit.** The unit is one province × reference month. Food and all-items CPI of a province-month enter together, as in `ASOF_RULE_SEPT2026.md` rule 1.

**Definition (owner, 2026-10-29).** A province-month is available for a row when the earliest *verifiable* public availability of that province's CPI release for that month is **strictly before** the row's issue date. A same-day date is not before.

Each province-month is assigned one evidence class:

| Class | Evidence | Counts as |
|---|---|---|
| V1 | An archived official PSA page whose subject is the province, or a regional page that states the province's figures, for the all-income series. Its printed release date **and** its Wayback capture time are both strictly before the issue. | verified |
| V2 | The same kind of page, with the printed release date strictly before the issue but the first capture on or after the issue. | verified (dated official source, addendum rule 1) |
| V3 | A committed repository retrieval of the exact food **and** all-items values used, timestamped strictly before the issue. | verified |
| P | An owner-reported release date strictly before the issue, with no saved copy. | provisional |
| N | Every dated source falls on or after the issue. | not available |
| U | No dated evidence. | unresolved |

Further rules for the evidence:
- **Retrieval timestamps** (V3) count only as proof that the values were public by that time. A later first retrieval is never taken as proof that earlier access was impossible.
- **Value check.** Where the archived page prints the headline (all-items) inflation, it is compared with the YoY implied by the index the model reads. The comparison is reported. Its outcome does not change the class.

## 2. Timing scenarios

These are applied identically to every Lead ≥ 2 row of the stack, covering training, inner validation and evaluation alike.

- **S-VER (verified).**
  - The refreshed cut-off starts at the base month m0.
  - It advances to m0+1, then m0+2, only while each next province-month is V1, V2 or V3 for that row's issue.
  - It stops at the first month that is not.
- **S-PROV (provisional).** As S-VER, but P also counts.
- **S-D10 (original, day-10 assumption).** The sealed CR / CR-ANC construction. It must reproduce `root_cause_rows.csv` (max abs ≤ 1e-6).

The base cut-off m0 and Lead 1 are unchanged. The timing of m0 is checked against the archived release dates and reported.

## 3. Evaluation (unchanged rules)

**Candidates.** P0H4-U (B0), CR and CR-ANC under each scenario. They are fitted by `lt_lib.run` with the frozen columns, grid and seed. The served P0H4 is shown for reference.

**Reported quantities:**
- N and HIGH count;
- accuracy, balanced accuracy, precision, recall and F1;
- Brier score;
- calibration slope and calibration-in-the-large;
- false alarms and missed HIGH;
- R1-R7;
- the adoption rule vs B0.

**Baselines.** Always-LOW, persistence and climatology.

**Labels.** Results under S-VER are labelled *verified timing*. Results under S-PROV and S-D10 are labelled *provisional*.

## 4. Trigger groups

The five groups are those named by the owner on 2026-10-29. They equal `cr_resolve.GROUPS5`:

| Group | Columns |
|---|---|
| Market / food prices | A1_food, A1_gap, A_mom, A2, A3, W_rice_yoy, W_rice_mom, W_cereal_yoy, W_crude_yoy (+ A1_*_anc for CR-ANC) |
| Climate | C1, C2, C3, W_urea_yoy |
| Employment / remittances | E1, E2 |
| News / NLP | N1, G_pri_yoy, NG_gap_price |
| Poverty / social vulnerability | V1 |

C4 (fish) and H1 (hunger outlook) are ablated and reported separately.

**Method.**
1. Each group is removed and the model is refitted chronologically at every origin, with the same selection, for B0 and for CR-ANC under S-VER.
2. The change at Leads 1 and 2 is measured as follows:
   - Brier difference, with a quarter-block bootstrap 90% CI and p (4000 draws, seed 2031);
   - Holm correction across the 5 groups;
   - changes in accuracy, recall, precision and calls.
3. The refit with all five groups removed is also reported.
4. SHAP is not used as evidence of contribution.

## 5. Diagnostics (reported, nothing selected)

| Diagnostic | Method |
|---|---|
| Overfitting | Mean training Brier vs next-origin test Brier of the price part. |
| Class bias | Predicted vs observed HIGH rate; errors by class. |
| Temporal drift | Accuracy and Brier by thirds and by year; dev (≤ 2024-Q4) vs later. |
| Province generalization | Leave-one-province-out: for each province the model is trained without that province's rows at every origin and predicts only that province. Compared with the in-sample fit. |
| Label quality | HIGH rows by quarter; distinct HIGH quarters; hunger readings within 1 point of the 11.3 line; the regional (Balance Luzon) hunger component shared by all five provinces. |
| Food insecurity vs price pressure | Accuracy of the hunger part and of the price part against their own components; oracle swaps (true hunger × model price, model hunger × true price); errors attributed to each part. |
| Leakage | CPI vintage (archived headline vs final-vintage implied YoY); 2012=100 vs 2018=100 base by issue date; threshold window vs first evaluation issue; news timestamps vs issue; SWS publication vs issue. |

## 6. Decision

- **Lead 2 is reliable only as the frozen protocol defines it:** a candidate passes R1-R7 at Lead 2, and any non-B0 candidate also passes the adoption rule.
- **What can support a reliability claim.** Only S-VER results.
- **Provisional results.** S-PROV and S-D10 results are reported as provisional and cannot establish reliability.
- **Improvements** are ranked by their measured effect in this run and in the earlier frozen runs. No new candidate is selected here.
