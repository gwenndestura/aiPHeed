# LEAD2_CPI_REFRESH protocol: refresh the price inputs at the SWS re-issue (frozen before scoring)

**Branch:** `aiPHeed/lead2-lgbm-tuning`. **Written:** 2026-10-28. The SHA-256 goes in `runner/CPI_REFRESH_SHA256.txt`. Both are committed before `runner/cpi_refresh.py` scores anything.

**Unchanged:**
- the T43c target and labels;
- the S-AB timing (Lead 1 at quarter start; Leads ≥ 2 re-issued after the SWS release, at the latest day 1 of month 3);
- the evaluation rows; R1-R7, the 0.50 cut and `final.adoption_rule`;
- the 21 model columns (12 indicator families, five trigger groups);
- the P0H4-U LightGBM recipe (8-configuration grid, inner chronological selection, seed 2027, monotone A1/A_mom);
- served artifacts and seals.

## 1. Evidence motivating the test

- **The price part is the Lead-2 limit under schedule B.** FR1 oracle: with the true price condition, schedule-B Lead 2 reaches 0.938; with the true hunger condition, only 0.677. §17.3: 3 of the 7 misses and 3 of the 6 false alarms are price moves after the issue.
- **The SWS re-issue refreshes only the hunger part** (FR3, P0H4-U, `sws_reissue.py`). At every re-issue date PSA has published **one or two more CPI months** than at the quarter start (`out/cpi_refresh_features_audit.json`: 840 Lead-2+ stack rows +1 month, 770 rows +2 months), but the price inputs still stop at month 2 of the origin quarter.
- **This has never been tested.** Every earlier schedule-B variant was "hunger part only".
- **Statistical rationale.** The flat projection's error grows with the distance from the last observed month to the target months (random-walk variance, `e41_lib.var_factor`). Observing 1-2 more months shortens that distance and should reduce the price-condition error at Leads ≥ 2. This is the same information the deployed re-issue already waits for.

## 2. Candidate CR (the only one)

- **Inputs.** For every stack row with Lead ≥ 2, the three CPI columns `A1_food`, `A1_gap`, `A_mom` are recomputed at that row's own schedule-B issue date (`runner/cpi_refresh_features.py`):
  - Same E107 flat projection and `ch1_lib` momentum, with the cut-off month m0 replaced by m0r, the newest month published before the issue date.
  - Availability rule (E113 day-10 rule): month m counts as published from day 10 of month m + 1. This is conservative against PSA's first-week release.
  - With m0r = m0 the builder reproduces the stack to 3.2e-9.
  - All other columns keep their quarter-start values. Lead-1 rows are unchanged.
- **Training and prediction** use these refreshed rows wherever Lead ≥ 2.
  - A training row's re-issue date (≤ day 1 of month 3 of quarter t′ + 1) always precedes the origin at which it is used, so training stays cut-off-safe.
  - The test rows' refreshed values exist at the re-issue date. The model can therefore be fitted at quarter start and applied at the re-issue, as the deployed job does.
- **Probability.** P = π_H (S-AB) × π_P, HIGH at 0.50.
- **Not run:** refreshing only the test rows while training on quarter-start values. That mixes two information sets in one model.

## 3. Evaluation and decision (unchanged rules)

- **Baselines:** B0 = P0H4-U from `out/final_rows.csv`; the served P0H4 for reference.
- **Metrics:** by Lead 1-4, accuracy and 90% CI, balanced accuracy, HIGH precision / recall, TP/FP/FN/TN, Brier and Δ vs both baselines, persistence and climatology comparisons, thirds, leave-one-quarter-out, DEV (targets ≤ 2024-Q4) and later-quarter (2025-Q2..2026-Q3) blocks.
- **Adoption:** `final.adoption_rule` vs B0, exactly. Lead 2 is called reliable only if R1-R7 all pass.
- **Stopping rule:** this is the last candidate. If CR is not adopted, P0H4-U is retained and the experiment ends.
- **If adopted:** it becomes the research candidate only. The served model, seal and dashboard change only with the researchers' authorisation. The deployed re-issue would then also need its price part refreshed.

## 4. Not allowed

Changing the release rule, columns, grid, target, timing, rows or criteria after scoring; a second variant; selection on later-quarter rows; pushing, merging, enabling production flags or changing served artifacts.
