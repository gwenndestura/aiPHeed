# Lead 2 under evidence-based CPI availability (PROTOCOL_LEAD2_ASOF_REEVAL)

| | |
|---|---|
| Protocol | `PROTOCOL_LEAD2_ASOF_REEVAL.md`, sha256 cc221596…, frozen in fd8dbc8 before any score |
| Runner | `runner/asof_reeval.py` |
| Outputs | `out/asof_reeval.json`, `out/asof_reeval_rows.csv`, `out/asof_reeval_cutoffs.csv` |
| Ledger | `data/psa_cpi_availability_ledger_20261029.csv` (new file; the owner-entered v2 ledger is not edited) |

This is a labelled diagnostic. It is **not** the addendum rule-3 re-score, which stays blocked. No candidate is adopted, served, counted or resealed.

What stays unchanged:
- Sealed CR, CR-ANC and companion files: hashes dd293e2e…, 07c99e56… and b1edb799….
- Served model: seal a498b5ef….
- R1-R7 and the adoption rule.

## 1. Decision

**Lead 2 does not meet the frozen reliability requirement under verified data availability. The maximum reliable lead is Lead 1.**

**Under verified timing, no candidate passes R1-R7 at Lead 2:**

| Candidate | Fails |
|---|---|
| P0H4-U (B0) | R6 |
| CR | R5, R6 |
| CR-ANC | R3, R6 |

**The earlier CR-ANC pass (Brier 0.132) is provisional.**
- It depends on CPI months whose release dates are not verified.
- When only verified months are used, 49 of the 65 Lead-2 evaluation rows fall back to the base cut-off.
- CR-ANC's Brier gain over B0 then shrinks from −0.036 to −0.002.

**What remains unproven:**
- **Day-10 timing.** The S-VER result is a lower bound, because a month without evidence is treated as unavailable. The day-10 result is an upper bound. The truth lies between them.
- **What would decide it.** Dated sources for the 61 owner-reported and 79 unresolved province-months.

## 2. Availability definition and evidence (Part A)

**Definition.** A province's CPI release for a month counts as available to a row only when its earliest verifiable public availability is **strictly before** the row's issue date. Further rules:
- Food and all items enter together, so there is one cut-off per province-month.
- The same rule applies to training, validation and evaluation rows.

**Kinds of date.** The ledger keeps these apart:
- reference month;
- printed release date (archived PSA page);
- Wayback capture time (independent proof the page was public);
- first repository retrieval;
- owner-reported date;
- issue date.

A later retrieval is never treated as proof that earlier access was impossible.

**Evidence classes, 180 province-months:**

| Class | Meaning | Batangas | Cavite | Laguna | Quezon | Rizal | All |
|---|---|---|---|---|---|---|---|
| V1 | archived official page; release and capture both before issue | 4 | 2 | 6 | 9 | 1 | 22 |
| V2 | archived official page; printed release before issue; captured later | 4 | 3 | 2 | 0 | 1 | 10 |
| V3 | exact food + all-items values retrieved before issue | 0 | 0 | 0 | 0 | 0 | 0 |
| P | owner-reported date before issue; no saved copy (provisional) | 17 | 12 | 11 | 9 | 12 | 61 |
| N | every dated source falls on or after the issue | 1 | 1 | 1 | 2 | 3 | 8 |
| U | no dated evidence | 10 | 18 | 16 | 16 | 19 | 79 |

**By year:**
- **Verified.** Verified months are concentrated in 2024-2025 (22 of 32).
- **2021-2023.** Mostly unresolved (63 of 90).
- **2026.** None verified.

**September 2026, all five provinces:**
- No province is verified.
- **Food YoY (0012M4ACP23).** Retrieved 2026-10-14 23:34 PHT, before the 10-15 issue.
- **All-items values and the 0012M4ACP22 index the model reads.** First retrieved 2026-10-15 (17:18 and 17:54 PHT), the same day as the issue, so they do not count.
- Because food and all items enter together, no province-month qualifies.
- **Owner-reported dates:**

| Province | Owner date | Class |
|---|---|---|
| Cavite | 10-12 | P |
| Laguna | 10-13 | P |
| Batangas | 10-13 | P |
| Rizal | 10-15 | N |
| Quezon | 10-16 | N |

- The sealed forecasts (issue 10-15) are unaffected as records and remain scored as published.

**How the unresolved dates affect the evaluation:** these are the S-VER vs S-PROV vs S-D10 differences in section 3.

**Value check: archived headline inflation vs the final OpenSTAT vintage.**
- 26 of 29 pages that print a headline rate equal the published final-vintage YoY.
- 3 differ beyond rounding:

| Province-month | As released | Final vintage |
|---|---|---|
| Cavite 2025-03 (regional page) | 1.5% | 1.1% |
| Batangas 2025-06 | 1.4% | 1.3% |
| Quezon 2025-06 | 1.8% | 1.7% |

- So the model's final-vintage CPI is not always the value that was public at the time. The differences are small, but this is a real vintage risk.

**Base cut-off m0 (used by B0 and Lead 1).**
- 35 of 36 archived pages for m0 months were released before the quarter-start issue.
- The exception is Batangas 2025-02. Its only archived page is a 2025-04-24 article, 55 days after the month ended. That is not proof of a late release, but the timing is unverified.
- Median archived lag: 8 days after month end.

## 3. Lead 2 performance (Part B)

**Data:** 65 rows, 17 HIGH, 13 target quarters (2023-Q2 to 2026-Q3). The 17 HIGH rows fall in only 7 distinct quarters.

**Baselines:**

| Baseline | Accuracy | Brier | Recall | False alarms | Missed HIGH |
|---|---|---|---|---|---|
| always-LOW | 0.738 | 0.262 | 0 | 0 | 17 |
| persistence | 0.723 | 0.277 | 0.647 | 12 | 6 |
| climatology | 0.738 | 0.228 | 0 | 0 | 17 |

**Results:**

| Candidate | Timing | Acc | Bal acc | Prec | Recall | F1 | Brier | FA | Missed | Cal. slope | R1-R7 fails | Adoption rule fails |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0H4 (served) | base m0 | 0.769 | 0.635 | 0.600 | 0.353 | 0.444 | 0.194 | 4 | 11 | 0.47 | R3 R5 R6 | – |
| P0H4-U (B0) | base m0 | 0.800 | 0.732 | 0.625 | 0.588 | 0.606 | 0.167 | 6 | 7 | 1.04 | R6 | – |
| CR | **verified** | 0.815 | 0.742 | 0.667 | 0.588 | 0.625 | 0.171 | 5 | 7 | 1.08 | R5 R6 | new FA > new hits; L1 fails R6 |
| CR-ANC | **verified** | 0.769 | 0.692 | 0.562 | 0.529 | 0.545 | 0.165 | 7 | 8 | 1.04 | R3 R6 | 8 of 9 conditions |
| CR | provisional (owner dates) | 0.815 | 0.742 | 0.667 | 0.588 | 0.625 | 0.145 | 5 | 7 | 1.40 | R6 | 3 conditions |
| CR-ANC | provisional (owner dates) | 0.800 | 0.770 | 0.600 | 0.706 | 0.649 | 0.149 | 8 | 5 | 1.20 | none | precision −0.025; FA > hits |
| CR | provisional (day 10) | 0.800 | 0.751 | 0.611 | 0.647 | 0.629 | 0.147 | 7 | 6 | 1.50 | none | new FA > new hits |
| CR-ANC | provisional (day 10) | 0.800 | 0.770 | 0.600 | 0.706 | 0.649 | 0.132 | 8 | 5 | 1.46 | none | precision −0.025; FA > hits |

**Reproduction.** The day-10 rows reproduce `root_cause_rows.csv` to within 5e-7, and the day-10 stack matches exactly.

**Cut-offs at the 65 Lead-2 evaluation rows (months beyond m0):**

| Timing | m0 | m0+1 | m0+2 |
|---|---|---|---|
| Verified | 47 | 10 | 8 |
| Owner dates | 18 | 30 | 17 |
| Day 10 | 0 | 40 | 25 |

**Why each candidate fails:**
- **B0** fails R6 by one row: recall 10/17 = 0.588 < 0.60.
- **CR-ANC (verified)** reaches recall 0.529 and precision 0.562. Without the refreshed months, its anchored projections add nothing over B0.
- **CR-ANC (provisional)** passes R1-R7, but fails the adoption rule on precision and on false alarms: 8 false alarms vs 5 missed HIGH, and its new false alarms outnumber its new hits.

**Calibration.** In the large, all candidates over-forecast by +0.06 to +0.09. Under day-10 timing the CR slopes are 1.4-1.5, which means under-confident spread.

**Class bias.** Every candidate's predicted HIGH rate is within 0.05 of the observed rate (0.262).

**Leakage checks:**

| Check | Finding |
|---|---|
| SWS hunger | Uses only rounds published before the issue (by construction). |
| News | Every dated item (1,575 rows) precedes the issue. |
| Price thresholds | The 2021-22 P60 window ends 2022-12. That month was released 2023-01-06, before the first Lead-2 issue (2023-01-20). |
| CPI base year | 375 of 1,725 stack rows (training only) were issued before the 2018=100 series is shown public (first archived 2022-06-07), yet use 2018=100 values. No evaluation row is affected. This remains the pending 2012=100 vintage decision. |
| Vintage revisions | See section 2. |

## 4. Trigger groups and diagnostics (Part C)

**Method.**
- Each group is removed and the model is refitted at every origin.
- Δ Brier is ablated minus full, so positive means the group helps.
- Uncertainty is a 90% quarter-block bootstrap CI.
- p is one-sided ("helps"), with Holm correction over the 5 groups.

**Lead 2:**

| Group (owner's five) | B0 Δ Brier [90% CI] | B0 Holm p | Δ recall | CR-ANC-verified Δ Brier [90% CI] | Holm p |
|---|---|---|---|---|---|
| Market / food prices | +0.037 [+0.009, +0.063] | 0.069 | −0.18 | +0.039 [+0.008, +0.072] | 0.101 |
| Climate | −0.005 [−0.010, −0.001] | 1.0 | 0 | +0.000 [−0.001, +0.002] | 0.90 |
| Employment / remittances | +0.004 [−0.001, +0.012] | 0.95 | 0 | +0.002 [+0.000, +0.006] | 0.12 |
| News / NLP | −0.007 [−0.014, −0.000] | 1.0 | 0 | −0.007 [−0.014, −0.001] | 0.97 |
| Poverty / vulnerability | +0.002 [−0.005, +0.010] | 1.0 | +0.06 | +0.008 [−0.004, +0.022] | 0.45 |
| All five removed | +0.031 [+0.003, +0.057] | – | −0.24 | +0.033 [+0.001, +0.066] | – |

**What the ablation shows.**
- **Market / food prices** is the only group with a material Lead-2 contribution. Even it is not significant after Holm correction (0.069 for B0, 0.101 for CR-ANC).
- **Climate and news** slightly *worsen* Lead 2. Their CIs include or approach zero.
- **Employment, remittances and poverty** are not established.
- **At Lead 1**, news (+0.011, Holm 0.055) and employment (+0.007, Holm 0.055) help B0 marginally.
- **No group is removed.** All 12 indicators stay in the agreed scope, and removing a group because of this table would be selecting against the evaluation.

**Food insecurity or price pressure?** The target is regional SWS hunger HIGH × provincial price-condition HIGH.

| Measure | B0 | CR-ANC verified | CR-ANC day-10 |
|---|---|---|---|
| Hunger part (latest SWS reading) accuracy | 0.846 | 0.846 | 0.846 |
| LightGBM price part accuracy vs price label | 0.600 | 0.569 | 0.723 |
| Price label always-LOW rate | 0.600 | 0.600 | 0.600 |
| Errors caused by the price part alone | 13 of 13 | 14 of 15 | 10 of 13 |
| Oracle: true price × model hunger | 0.938 | 0.938 | 0.938 |
| Oracle: true hunger × model price | 0.677 | 0.646 | 0.800 |
| Correlation of p with hunger label / price label | 0.38 / 0.11 | 0.34 / 0.14 | 0.25 / 0.36 |

- **Where the Lead-2 discrimination comes from.** Mostly from the latest regional hunger reading, which is persistence of observed food insecurity.
- **The LightGBM price part is the binding constraint.**
  - With base-timing or verified CPI it is **no more accurate than always-LOW on the price label** (0.600 vs 0.600).
  - It shows skill only with the refreshed day-10 CPI (0.723), and that timing is unverified.
  - So at Lead 2 the model forecasts price pressure weakly. Its food-insecurity signal is the hunger term carried forward.
- **Price-pressure caveat.** The price condition is a proxy and is not described as confirmed food insecurity.

**Overfitting.**
- The price part's mean training Brier vs next-origin test Brier is 0.188 vs 0.222 for B0, and 0.180 vs 0.218 for CR-ANC (verified). That is a moderate, stable gap.

**Temporal drift.**
- B0 accuracy by thirds is 0.84 / 0.65 / 0.90. The weak middle third (2024) holds the known 2024-Q2 regime break.

**Province generalization (leave-one-province-out, Lead 2).**
- Overall Brier is unchanged:
  - B0: 0.166 left out vs 0.167 in-sample.
  - CR-ANC verified: 0.160 vs 0.165.
- Rizal has no HIGH rows at Lead 2. Batangas is the most province-specific (accuracy 0.92 → 0.77 for B0).
- There is no sign that the model memorises provinces.

**Label quality.**
- **Concentrated HIGH outcomes.** The 17 HIGH rows sit in 7 quarters (2023-Q4 3, 2024-Q2 4, 2024-Q3 1, 2024-Q4 3, 2025-Q2 3, 2025-Q3 2, 2026-Q2 1).
- **Shared hunger term.** Hunger is one Balance Luzon value shared by all five provinces, so errors cluster by quarter. For example, 2023-Q4 is missed in 3 provinces by every candidate.
- **Readings near the line.** Two target quarters sit within 1 point of 11.3: 2023-Q2 (11.3, exactly on the line) and 2023-Q3 (10.3).
- **What this does to R6.** R6 turns on one row. The effective sample for HIGH is about 7 quarters.

## 5. Ranked improvements (Part D, by measured impact)

1. **Verify the CPI release dates (owner action; largest measured effect).**
   - The verified-to-day-10 gap is the whole CR-ANC gain: Brier 0.165 → 0.132, and recall 0.53 → 0.71.
   - 61 province-months have owner-reported dates without saved copies, and 79 have no dated evidence (2021-2023 mostly, and 2026).
   - Only these can turn the provisional pass into a verified one. Even then, CR-ANC still fails the adoption rule.
2. **The price part is the bottleneck.**
   - Perfect price knowledge would lift Lead-2 accuracy from 0.80 to 0.94. Perfect hunger knowledge would not help (0.68).
   - Any defensible gain must come from earlier or better provincial price information, not from the other trigger groups. Those add ≤ 0.008 Brier at Lead 2.
3. **False alarms from price reversals** (6-8 per candidate) block the adoption rule. The earlier frozen remedies did not fix them: CR-T thresholds, CR-WCAL recalibration and CR-CAL all failed.
4. **Sample size.** With about 7 HIGH quarters, a one-row difference decides R6. More scored quarters, including the sealed prospective forecasts as their outcomes are published, are the only legitimate way to tighten this.
5. **Vintage hygiene.** Use as-released CPI where the archive differs (3 of 29 pages), and resolve the 2012=100 decision for 375 training rows. The measured effect is likely small.

**No further experiment was run.** Every remaining variant would be chosen after seeing these Lead-2 results, which the frozen rules forbid. The next legitimate steps are the owner's date verification (then the single addendum re-score) and prospective scoring of the sealed forecasts.
