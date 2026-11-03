# SENIOR_REVIEW, Step 1: bug audit of the REF+news food-insecurity model (read only)

**Scope.** The served REF+news model (OPTION_1) and its scoring, on targets 2010-Q1..2026-Q3, Leads 1–2.

**Method.** `runner/audit.py` recomputes each quantity independently from the raw inputs (the SWS round table, the
IMPROVE_V2 pooled table and the stored forecasts) and compares it with what the pipeline used (`out/audit.json`).
Nothing was refitted, tuned or re-thresholded, and no existing file was written.

**Correction during the audit.** The first run flagged A3 as a BUG. That was an error in **my check**: it put a
straddling round in the quarter where its fieldwork ends. It now uses the quarter where fieldwork starts, as SWS names
its surveys, and the four straddling rounds are listed in A3's evidence, not hidden.

## Verdict: no bug found that could have lowered the score

13 checks pass and 4 are notes. **Step 2 does not apply**, so nothing was fixed or re-run.

| # | Check | Result | Evidence |
|---|---|---|---|
| A1 | Commissioned rounds excluded | PASS | The file holds 115 rounds, none commissioned; `load()` drops any that are flagged. All 115 BL values are loaded |
| A2 | Label = quarter mean of non-commissioned rounds; y = H > 11.3 (strict) | PASS | Recomputed for 106 quarters: max difference 0.0, 0 label mismatches. Nine quarters have two rounds and are averaged (e.g. 2020-Q3: 17.8 and 23.8 → 20.8). H = 11.3 exactly (2004-Q3, 2017-Q1, 2022-Q4, 2023-Q2) is LOW, as "> 11.3" requires |
| A3 | Round → quarter = the quarter in which fieldwork starts | PASS | 0 mismatches in 115 rounds. Four rounds straddle a quarter boundary (2022-09-29/10-02, 2023-06-28/07-01, 2023-09-28/10-01, 2024-06-23/07-01), all after 2021 |
| A4 | BL values against the independent E114 extraction of SWS's release tables | PASS | 112 rounds compared, max difference 0.0. Three were not matched by label; two of them are label formats with equal values ("May 21" 15.7; "Apr 25**" 17.0). The third is A6 |
| A5 | Verdict quarters without a label | NOTE | 2016-Q1, 2020-Q1, 2021-Q1, 2022-Q1 and 2025-Q1 have no SWS round in the tables. They are skipped, never imputed: 62 of 67 quarters are scored |
| A6 | Quarter of each round against E114 | NOTE (source ambiguity) | One disagreement. The 2022-09-29/10-02 round (BL 9.6) is labelled "Oct 22" (Q4) in SWS's release table, but SWS and the press call it the Q3 2022 survey ([ABS-CBN](https://news.abs-cbn.com/news/10/30/22/29-million-filipino-families-went-hungry-in-q3-2022), [Manila Times](https://manilatimes.net/2022/11/02/news/sws-hunger-rate-hardly-moved-in-q3/1864735)). The served file uses Q3. If moved, 2022-Q3 would become unlabelled and 2022-Q4 = mean(9.6, 11.3) = 10.45, still LOW: at most one quarter of the 2021–2026 third changes, and the failing 2015–2020 third is untouched |
| B1 | SWS release dates before 2021: "label month end + 60 days" | NOTE (conservative, documented) | 92 rounds use the rule, 23 have recorded dates. In the evidence file (`E114_Final_Run/data/sws_release_date_evidence.csv`), six releases have day counts, from 8 days before to 43 days after the label month end; four more have only a month and fall within 31 days. All are earlier than the 60-day rule, so **the rule cannot leak**. With a 43-day lag instead, **0 verdict origins** would gain a reading, because O(t) is the first day of a quarter. So the rule is not too strict in practice either |
| B2 | Hunger inputs only from rounds published before O(t) | PASS | 113 origins: `sws_newest_published` < O(t), `h_last` equals the latest known reading, and no reading from a later quarter |
| B3 | CPI, ONI and Pink Sheet cut at month 2 of quarter t | PASS | Month 2's values (PSA CPI about day 5, NOAA ONI about days 5–10, World Bank Pink Sheet about days 2–3 of the following month) are out before O(t) = day 1 of month 4. Month 3 would leak; month 1 alone would be too strict |
| B4 | Production and typhoons | PASS | Palay, corn and fisheries use quarter t−1 (PSA releases about 6–8 weeks after the quarter). Typhoon counts use quarter t, which ended at O(t). Later IBTrACS revisions are a data-vintage caveat, not a timing error |
| B5 | News: published before O(t) only; NaN, not 0, before 2021 | PASS | No E112 quarter was published after its O(t). 0 non-NaN and 0 zero news values before 2021; news present on 345 of 345 rows from 2021 on |
| C1 | Target = origin + lead | PASS | Holds on all 1,695 table rows, 4,155 forecast rows and 1,695 SHAP rows |
| C2 | Each scored forecast paired with its target quarter's label | PASS | 62 rows, 0 mismatches |
| C3 | Hunger features recomputed | PASS | 226 rows at Leads 1–2: `h_last` and the true horizon (target minus newest known quarter) equal the recomputation |
| C4 | Column list and NaN handling | PASS | 28 columns: 19 REF columns + 8 news columns + lead. LightGBM treats NaN as missing, so before 2021 the model splits on the other inputs only. This is the documented design (IMPROVE_V2 PLAN §5) |
| D1 | R1–R7 recomputed independently | PASS | Independent tools: sklearn balanced accuracy, chronological thirds, LOQO, and the original `pd.concat` cluster bootstrap (seed 2036, 5,000 draws). They reproduce every stored pass/fail, accuracy, balanced accuracy, AUC and Brier exactly. Lead 1: thirds 0.952 / **0.571** / 0.750 (2010-Q1..2015-Q1, 2015-Q2..2020-Q4, 2021-Q2..2026-Q3; sizes 21, 21, 20); LOQO 0.754; R5 vs CLIM −0.0254, p 0.171. Lead 2: thirds the same, R5 vs CLIM −0.0234, p 0.208 |
| D2 | Code matches `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7 | PASS | R1 counts; R2 ≥ 0.75; R3 (recall + specificity)/2 ≥ 0.70; R4 > ALWAYS-LOW and > PERSIST-SI; R5 one-sided paired cluster bootstrap, p = share of resampled differences ≥ 0, < 0.10 against both; R6 ≥ 0.60 both; R7 chronological thirds ≥ 0.60 and LOQO ≥ 0.70. With one row per quarter, the cluster bootstrap is an ordinary bootstrap of quarters |

## What this means

The R3, R5 and R7 failures of REF+news are **not caused by a pipeline error**. Labels, timing, alignment and scoring
all check out against independent recomputations and the protocol text.

The two notes that touch the data, A6 (one ambiguously named 2022 round) and B1 (the conservative pre-2021 release
rule), cannot move the failing 2015–2020 third.

The causes remain those documented earlier:
- **R7:** quarter-to-quarter reversals near the line in 2015–2020 (`../RELIABLE_NEWINFO/STEP0_SOURCES.md`);
- **R3:** HIGH said too often;
- **R5:** no significant gain over climatology. The news columns do not help: REF without news passes R3 and R5.
