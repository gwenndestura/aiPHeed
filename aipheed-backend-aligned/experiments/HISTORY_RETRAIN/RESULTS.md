# HISTORY_RETRAIN results (EXPLORATORY)

**Plan:** `PLAN.md` (`6b9f17fb…`, commit `d9e2335`) and `PLAN_AMENDMENT_1.md` (`319ae4d2…`, commit `ee5eb3a`). Both
were committed before any label, model or baseline was computed. The runner checks both hashes.

**Status of the evidence.** Every verdict-window quarter has already been examined by earlier experiments, so these
are **development results, not a clean test**. A pass here only makes a model a **candidate for a new
preregistration scored on 2027+ quarters**. It replaces nothing: the served P0H4, the dashboard, `PREREG_LEAD2`, its
addenda and every seal are unchanged.

**Run:** 2026-11-02.
- Python 3.13.7, numpy 2.4.4, pandas 2.3.3, LightGBM 4.6.0, scikit-learn 1.7.2, PyTorch 2.9.0+cpu.
- Remittances (E2) were **not** used: no BSP file was supplied, so option (c) ran without E2, as the plan's rule
  requires.

All numbers come from `out/results.json`. Every forecast is in `out/rows.csv` and the full tables are in
`out/summary.md`.

## Step 4: the verdict in plain words

**1. Did the longer history improve accuracy on 2023–2026?**

*Chapter I target (T1), Lead 1.* Only marginally, and not consistently. P0H4, trained on 2021+ only, scored
accuracy 0.843 and Brier 0.132 on the same 70 rows.

| Model (longer history) | Accuracy | Brier | Verdict |
|---|---|---|---|
| LightGBM (c) | 0.857 | 0.128 | passes every rule (60 of 70 rows right vs 59) |
| LightGBM (b, primary) | 0.829 | 0.121 | lower accuracy; fails R6 (recall 0.53) |
| MLP (b), 10 seeds | 0.877 mean | 0.115 mean | best numbers, but only 9/10 seeds pass |

A one-row difference out of 70 is well within noise. The honest reading is "about the same as P0H4, perhaps slightly
better calibrated".

*Chapter I target (T1), Lead 2.* No. The best long-history accuracy was 0.738, against P0H4's 0.769. That is exactly
the share of LOW rows, so no model beat always saying LOW on accuracy. Brier improved slightly (LightGBM b 0.185 vs
0.194).

*Hunger-only target (T2), 2023–2026 block.* LightGBM (b) got:
- **14/14 quarters at Lead 1**, against persistence 12/14;
- **13/14 at Lead 2**, against persistence 10/14.

But 14 quarters cannot pass R1, and its Brier (0.126 at Lead 1, 0.151 at Lead 2) is **higher** than the served hunger
term PIH scored in LEAD2_FOODINSECURITY (0.090 and 0.137; that study's Lead-2 window has one fewer quarter). Its
probabilities are therefore less sharp than P0H4's hunger term, even though the HIGH/LOW calls were right.

**2. Does any model pass at Lead 2?**

**No.** No model is reliable at Lead 2 for either target under the frozen rules.
- **T1:** every model fails R2, R3, R5 and R6.
- **T2 (2010–2026, 62 quarters):** LightGBM (b) comes closest.
  - It passes R1–R6, and beats ALWAYS-HIGH and persistence on Brier (p 0.008 and p < 0.001).
  - It **fails R7**: accuracy in the middle third of the quarters (about 2015–2020) is 0.571, below 0.60.
  - So it is **not reliable**.
  - Disclosed sensitivity, which does not change the verdict: with the two 2020 phone-survey quarters removed, it
    would pass every rule at both leads.

**3. Does any model beat simply copying the latest SWS reading?**

**Yes on the long T2 record, and yes for the price-aware LightGBM on T1 Lead 1. Not by itself enough to be reliable.**
- On T2 2010–2026, LightGBM (b) beats persistence clearly at both leads: accuracy 0.790 vs 0.661, Brier 0.188 vs
  0.339, p < 0.001.
- On T1 Lead 1, LightGBM (c) beats PERSIST-SI: 0.857 vs 0.743, Brier p 0.018.
- In the short 2023–2026 T2 block, persistence is strong (0.857 at Lead 1). The LightGBM is more accurate there, but on
  only 14 quarters.

**4. Did deep learning beat LightGBM, logistic regression and persistence?**

**Deep learning did not beat LightGBM, except the MLP on T1 Lead 1, and no deep model is reliable anywhere.** The
Amendment-1 rule: a model beats another only if its seed-mean Brier is lower **and** at least 8/10 seeds are lower.

| | vs LightGBM | vs logistic regression | vs persistence |
|---|---|---|---|
| T1 Lead 1 | **MLP (b) beats** (10/10 seeds). GRU (b) and MLP (c) do not. | All beat | All beat |
| T1 Lead 2 | None beats (MLP b 7/10 seeds, short of 8) | All beat | All beat |
| T2 Lead 1 | None beats (0/10 seeds for both) | None beats (2/10) | All beat |
| T2 Lead 2 | None beats (0–1/10) | All beat | All beat |

**Reliability over the 10 seeds** (reliable only if all 10 seeds pass):

| Model | T1 Lead 1 | T1 Lead 2 | T2 |
|---|---|---|---|
| MLP (b) | 9/10, unstable (seed 4 fails R6) | 0/10 | 0/10 |
| GRU (b) | 3/10 | 0/10 | 0/10 |
| MLP (c) | 3/10 | 0/10 | 0/10 |

**Candidates for a new preregistration on 2027+ quarters.** These are candidates only; they do not replace P0H4.
- **T1 Lead 1:** LightGBM (c) is the only model that passed everything.
  - MLP (b) is a close second, with the best Brier but 9/10 seeds.
  - Caveat: (c) treats the news columns as missing before 2021, so part of what it learns is "news present means
    recent years". Its pass is weaker evidence than a (b) pass would be.
- **T2 at Lead 1 and Lead 2:** LightGBM (b) is the strongest long-history model, but it failed R7, so it is not a
  candidate under the frozen rule. A new preregistration would have to keep R7 unchanged and test it on 2027+ quarters.
- **Nothing at T1 Lead 2.**

## Results by target and lead (verdict windows)

**Reading the tables:**
- (b) = long-history inputs (primary). (c) = (b) + LFS, provincial rice wholesale, and news (NaN before 2021), from
  origin 2011-Q2.
- Deep models show the 10-seed mean.
- "Reliable" = R1–R7 all pass AND Brier is below ALWAYS-HIGH and below persistence.

### T1 Lead 1: targets 2023-Q1..2026-Q3, 70 province-rows, 14 quarters, HIGH share 0.243

| Model | Acc | Bal | Prec | Rec | AUC | Brier | Fails | Brier vs ALWAYS-HIGH / persistence (p) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **P0H4 (served, 2021+)** | 0.843 | 0.776 | 0.688 | 0.647 | 0.867 | 0.132 | — | — | reliable (earlier) |
| PERSIST (PERSIST-SI) | 0.743 | 0.670 | 0.474 | 0.529 | 0.670 | 0.257 | R2–R6 | −0.500 (0.000) / itself | no |
| LOGIT (b) | 0.529 | 0.589 | 0.300 | 0.706 | 0.747 | 0.299 | R2–R7 | −0.459 (0.000) / +0.041 (0.644) | no |
| LGBM (b) | 0.829 | 0.727 | 0.692 | 0.529 | 0.918 | 0.121 | R6 | −0.636 (0.000) / −0.136 (0.014) | no |
| LOGIT (c) | 0.614 | 0.605 | 0.333 | 0.588 | 0.713 | 0.251 | R2–R7 | −0.506 (0.000) / −0.006 (0.462) | no |
| **LGBM (c)** | **0.857** | 0.826 | 0.684 | 0.765 | 0.908 | 0.128 | none | −0.629 (0.000) / −0.129 (0.018) | **RELIABLE** |
| MLP (b), 10 seeds | 0.877 ± 0.017 | 0.807 | 0.791 | 0.671 | 0.907 | 0.115 ± 0.002 | R6 in 1 seed | all seeds lower | 9/10, not reliable |
| MLP (c), 10 seeds | 0.816 ± 0.026 | 0.730 | 0.637 | 0.565 | 0.823 | 0.158 | R3, R5, R6 in some seeds | — | 3/10 |
| GRU (b), 10 seeds | 0.797 ± 0.031 | 0.704 | 0.594 | 0.524 | 0.860 | 0.137 | R2–R4, R6 in some seeds | — | 3/10 |
| ALWAYS-LOW | 0.757 | 0.500 | – | 0.000 | – | 0.243 | R3–R7 | | no |

LGBM (c), rule by rule:
- R4: 0.857 > 0.757 and 0.743.
- R5: vs PERSIST-SI −0.129 (p 0.018); vs CLIM −0.064 (p 0.002).
- R6: precision 0.684, recall 0.765.
- R7: thirds 0.88 / 0.92 / 0.75; leave-one-quarter-out minimum 0.846.

### T1 Lead 2: targets 2023-Q2..2026-Q3, 65 rows, 13 quarters, HIGH share 0.262

| Model | Acc | Bal | Prec | Rec | AUC | Brier | Fails | Verdict |
|---|---|---|---|---|---|---|---|---|
| **P0H4 (served)** | 0.769 | 0.635 | 0.600 | 0.353 | 0.625 | 0.194 | R3, R5, R6 | not reliable (earlier) |
| PERSIST | 0.677 | 0.591 | 0.389 | 0.412 | 0.591 | 0.323 | R2–R7 | no |
| LOGIT (b) | 0.662 | 0.695 | 0.419 | 0.765 | 0.629 | 0.271 | R2–R7 | no |
| LGBM (b) | 0.738 | 0.595 | 0.500 | 0.294 | 0.626 | 0.185 | R2–R6 | no |
| LOGIT (c) | 0.631 | 0.503 | 0.267 | 0.235 | 0.513 | 0.286 | R2–R7 | no |
| LGBM (c) | 0.738 | 0.633 | 0.500 | 0.412 | 0.600 | 0.200 | R2–R6 | no |
| MLP (b), 10 seeds | 0.772 ± 0.015 | 0.644 | 0.602 | 0.376 | 0.638 | 0.184 | R3 and R6 in every seed, R5 in 9 | 0/10 |
| MLP (c), 10 seeds | 0.698 | 0.560 | 0.387 | 0.271 | 0.469 | 0.236 | | 0/10 |
| GRU (b), 10 seeds | 0.725 | 0.603 | 0.467 | 0.347 | 0.587 | 0.198 | | 0/10 |
| ALWAYS-LOW | 0.738 | 0.500 | – | 0 | – | 0.262 | | no |

### T2 Lead 1: targets 2010-Q1..2026-Q3, 62 quarters, HIGH share 0.694 (R1 in quarters)

| Model | Acc | Bal | Prec | Rec | AUC | Brier | Fails | Brier vs ALWAYS-HIGH / persistence (p) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| PERSIST (latest SWS) | 0.661 | 0.594 | 0.750 | 0.767 | 0.594 | 0.339 | R2–R5, R7 | +0.032 (0.715) / itself | no |
| LOGIT (b) | 0.710 | 0.629 | 0.766 | 0.837 | 0.759 | 0.193 | R2, R3, R5, R7 | −0.114 (0.016) / −0.146 (0.001) | no |
| **LGBM (b)** | **0.790** | 0.717 | 0.812 | 0.907 | 0.702 | **0.188** | **R7 only** | −0.119 (0.009) / −0.151 (0.000) | **no** |
| LOGIT (c), 56 q | 0.571 | 0.465 | 0.659 | 0.763 | 0.589 | 0.318 | R2–R5, R7 | | no |
| LGBM (c), 56 q | 0.625 | 0.534 | 0.698 | 0.789 | 0.662 | 0.221 | R2–R5, R7 | | no |
| MLP (b), 10 seeds | 0.687 ± 0.032 | 0.570 | 0.730 | 0.872 | 0.675 | 0.197 | R2, R3, R7 in every seed | | 0/10 |
| MLP (c), 10 seeds, 56 q | 0.643 | | | | | 0.219 | | | 0/10 |
| GRU (b), 10 seeds | 0.676 ± 0.031 | 0.564 | 0.727 | 0.853 | 0.694 | 0.197 | R2, R3, R7 in every seed | | 0/10 |
| ALWAYS-HIGH | 0.694 | 0.500 | 0.694 | 1.000 | – | 0.306 | R2, R3, R5, R7 | | no |

LGBM (b), the rules it was closest on:
- R7: thirds 0.952 / **0.571** / 0.850 (21, 21 and 20 quarters); leave-one-quarter-out minimum 0.787.
- R5: vs persistence −0.151 (p 0.000); vs CLIM −0.033 (p 0.096).

### T2 Lead 2: targets 2010-Q1..2026-Q3, 62 quarters, HIGH share 0.694

| Model | Acc | Bal | Prec | Rec | AUC | Brier | Fails | Verdict |
|---|---|---|---|---|---|---|---|---|
| PERSIST | 0.661 | 0.594 | 0.750 | 0.767 | 0.594 | 0.339 | R2–R5, R7 | no |
| LOGIT (b) | 0.661 | 0.624 | 0.775 | 0.721 | 0.670 | 0.234 | R2–R5, R7 | no |
| **LGBM (b)** | **0.790** | 0.717 | 0.812 | 0.907 | 0.704 | **0.184** | **R7 only** (thirds 0.952 / 0.571 / 0.850) | **no** |
| LOGIT (c), 55 q | 0.673 | 0.657 | 0.788 | 0.703 | 0.676 | 0.261 | R2, R3, R5, R7 | no |
| LGBM (c), 55 q | 0.564 | 0.476 | 0.659 | 0.730 | 0.646 | 0.223 | R2–R5, R7 | no |
| MLP (b), 10 seeds | 0.674 ± 0.040 | 0.559 | 0.725 | 0.856 | 0.667 | 0.202 | | 0/10 |
| MLP (c), 10 seeds, 55 q | 0.658 | | | | | 0.215 | | 0/10 |
| GRU (b), 10 seeds | 0.702 ± 0.042 | 0.595 | 0.744 | 0.870 | 0.700 | 0.193 | | 0/10 |
| ALWAYS-HIGH | 0.694 | 0.500 | 0.694 | 1.000 | – | 0.306 | | no |

## Secondary windows (reported, no verdict)

**T2, 2023–2026 block (14 quarters; R1 cannot pass).** Accuracy and Brier:

| Model | Lead 1 | Lead 2 |
|---|---|---|
| PERSIST | 0.857, Brier 0.143 | 0.714, Brier 0.286 |
| LOGIT (b) | 0.786, Brier 0.111 | 0.714, Brier 0.177 |
| LGBM (b) | **1.000**, Brier 0.126 | **0.929**, Brier 0.151 |
| LGBM (c) | 0.643 | 0.643 |
| MLP (b) | 0.764 | 0.693 |
| GRU (b) | 0.757 | 0.714 |
| ALWAYS-HIGH | 0.786, Brier 0.214 | 0.786, Brier 0.214 |

**Development walk-forward, 2010–2022 (48 quarters).**
- **T1:** every model fails at both leads. The best Lead-1 accuracy is LOGIT (b) at 0.725, against ALWAYS-LOW 0.679.
  The Lead-1 LGBM (b) recall is 0.29. Before 2021 the price condition rests on PSA's back-cast CPI.
- **T2:** LGBM (b) gives 0.729 (Lead 1) and 0.750 (Lead 2), failing R2/R3/R5 and R3/R5 respectively. Persistence gives
  0.604 and 0.646.

The 2023–2026 results are better than 2010–2022 for every model. This is partly because the recent period is
persistently HIGH.

## Known-break sensitivities (evaluation set only; the verdict is unchanged)

| Window | Result |
|---|---|
| **T2, without the 2020 phone rounds (S1, 60 quarters)** | LGBM (b) **would pass every rule at both leads**: 0.800 / Brier 0.185 at Lead 1, 0.817 / 0.174 at Lead 2. |
| **T2, without 2025-Q2+ adult respondents (S2, 56 quarters)** | LGBM (b) fails at Lead 1 (0.768) and would pass at Lead 2 (0.768, Brier 0.190). |
| **T2, without both (S3, 54 quarters)** | LGBM (b) fails at Lead 1 (0.778) and would pass at Lead 2 (0.796). |
| **T1, S2 and S3** | Only 8 (Lead 1) or 7 (Lead 2) quarters remain, so R1 fails for every model. LGBM (c) 0.900 and LGBM (b) 0.800 at Lead 1. |

T2's R7 failure therefore depends partly on the 2020 phone-survey quarters, which fall in the middle third. This
**does not change the frozen verdict.** It is a reason to keep R7 unchanged in any 2027+ preregistration rather than
to relax it.

## Fallbacks

Forecasts that fell back to the training HIGH share or CLIM are all option (c), at origins before its training history
was eligible:

| Target | Last fallback origin |
|---|---|
| T1 | 2012-Q4 (LOGIT 2013-Q1) |
| T2 LGBM and MLP | 2015-Q2 |
| T2 LOGIT | 2018-Q1 |

No verdict-window T1 forecast is a fallback. T2 (c) fallbacks are inside the 2010–2026 window and are counted in its
scores. Options (b), PERSIST and GRU had none.

## Deviations and disclosures (all made without changing any model, forecast or rule)

1. **Fidelity check 8.1(b) tolerance.**
   - **Problem:** `pi_H4` in `FINAL_ARCHITECTURE/out/predictions.csv` is stored with 6 decimals, so the planned
     |diff| < 1e-9 against the CSV was impossible. The first build stopped on it, at diff 4.7e-7.
   - **Fix:** the check now compares against the served function (`LEAD2_OPTIMIZATION a3.h4`, with H0 fallback) at
     1e-9, where max diff = 0.0, and against the CSV rounded to 6 decimals, where it is exact.
   - All other checks passed as planned: T1 labels 100/100 equal, PERSIST-SI 135/135 equal, SWS 2021+ equal, regional
     CPI equal, and leakage perturbation at 7 origins equal.
2. **Option (c) scored on the rows it has.**
   - The first scoring pass gave (c) no T2 verdict score, because (c) has no 2010 forecasts (it starts at 2011-Q2).
     PLAN §8.5 says (c)'s count is reported whatever it is.
   - Each model is now scored on its non-missing rows, with the baselines on the same rows: 56 quarters at Lead 1, 55
     at Lead 2.
   - The re-scoring changed no previously scored entry. This was checked: 0 of all entries differ.
3. **Bootstrap speed.** The frozen `rules()` code is imported unchanged, but its `boot_quarters` (5,000 `pd.concat`
   draws) took about 2 hours. It was replaced at run time by an exact equivalent:
   - the same generator, seed, quarter order and draws;
   - the row mean computed from per-quarter sums.

   `rules()` with the replacement was checked equal to `rules()` with the original on three real frames before scoring
   (`fastBootEqualsOriginal` in `results.json`). The plan's own Brier-criterion bootstrap uses the same equivalent
   (max diff 1.7e-16 against the original).
4. **Never-HIGH baselines.** `rules()` crashes formatting an undefined precision when a forecast never says HIGH. For
   ALWAYS-LOW, and for CLIM on T1, the same thresholds are restated in `hr_lib._rules_no_high`, with R6 failing by
   definition. No model needed this path.
5. **Option (c) start.** The plan's 2011-Q2, not "~2005": PSA's provincial rice wholesale series starts in 2010-01.
6. **Remittances.** BSP returned HTTP 403, and no file was supplied. (c) ran without E2.
7. **Back-cast CPI.** Pre-2018 prices are PSA's later recalculation on the 2018 basket, not the figures published at the
   time. Pre-2021 SWS release dates are estimated (label month end + 60 days).
8. **Multiplicity.** 4 classical arms and 3 deep arms (× 10 seeds) per target and lead were scored on the same
   quarters. One pass among them (LGBM (c), T1 Lead 1) is what chance alone could sometimes produce. That is why it is
   only a candidate for 2027+.

## Reproduction

```
cd aipheed-backend-aligned/experiments/HISTORY_RETRAIN/runner
python acquire.py          # already done; data/fetch_log.json has sources, dates and SHA-256
python run_hr.py build     # tables, labels, PLAN section 8 checks -> out/checks.json
python run_hr.py fit       # PERSIST, LOGIT, LGBM -> out/forecasts_classic.csv
python dl.py 6             # MLP and GRU, 10 seeds, deterministic -> out/dl/ (one job re-run gives byte-identical output)
python run_hr.py score     # out/results.json, out/rows.csv
python summarize.py        # out/summary.md
```

**Repository checks:**
- Full backend test suite: **987 passed, 18 skipped, 0 failed**.
- `git diff --stat` shows that nothing outside `HISTORY_RETRAIN/` was changed by this work. The modified backend files
  listed by `git status` were already modified before this experiment began.
