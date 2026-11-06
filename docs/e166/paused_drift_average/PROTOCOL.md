# E166 protocol: AUTO + national drift nowcast (Fix 1) + top-5 averaging (Fix 4)

- **Written:** 2026-11-06, before the E166 code was run and before any E166 result existed.
- **Locking:** `python -m app.e166.drift lock` hashes this file, the code and every input file. `eval` refuses to run if any of them changed since the lock, refuses a second run, and refuses if a file is missing.
- **Owner approval is required before `lock`.**

## 1. Why

- E164 AUTO is correct on 57 of 72 Lead-1 rows (79.2 %) and fails only E156 criterion **C4**: calibration slope 0.73 [0.51, 0.88].
- E165 shrank the score using training rows only. That moved the slope to [0.56, 0.94] and did not pass.
- Two causes remain:
  - **Level:** every anchor carries the national level of the last released survey round **flat** (`Hier2.shared`, `hp.last_n`), although food insecurity moved between rounds.
  - **Spread:** AUTO picks a single best configuration, and picking a winner favours the one that fits noise most confidently.

  E166 tests one fix for each, together, in one run.

## 2. What C4 measures, and the predicted direction

- **What C4 tests:** the slope of `y_true` regressed on the forecast score `mu` (logit), pooled over all Lead-1 rows of the three rounds, with a region bootstrap (`app.e151.prov.scale_test`). It does **not** test the intercept.
- **What a level fix can do:** it moves every row of one outer round (one survey × lead cell) by the same amount, so it does not change spread within a round. **It raises the pooled slope only if the level error differs between rounds,** that is, if rounds whose scores are higher are also over-predicted more. If the level error is the same in every round, the drift fix moves only the intercept and C4 is unchanged.
- **What averaging can do:** it reduces spread within rounds. Averaging five configurations makes extreme scores less extreme, which raises the slope.
- **Prediction, written before the run:**
  - the Lead-1 slope point estimate **rises** (from 0.73);
  - the intercept of `y_true` on `mu` **rises** toward 0 (from −0.13), and the mean error (forecast − survey; E165 measured [+0.03, +0.20] logit) shrinks;
  - the 0.4–0.6 probability band moves closer to its observed rate.

  The size is not predicted. **Passing C4 is possible but not expected with confidence.**
- **Known weakness:** at the 2018 and 2019 issues only two rounds (2013, 2015) are released, so the drift rate rests on **one past change**. If that change is near zero, the drift fix does almost nothing for 47 of the 72 Lead-1 rows.

## 3. Fix 1: national drift nowcast (exact)

For every row, training or test, with issue quarter `i` and target quarter `T`, let `hp` be the `Hier2` fit on the rounds released at `i` (`app.e160.arms.Cache.get(i)`, the same fit the anchors already use):

| Symbol | Definition | Source |
|---|---|---|
| `N[s]` | national level of released round s (logit), two-way fixed effects, weights 1/(SE² + 0.02) | `hp.N` |
| `q_s` | reference quarter of round s | `M8.RQ` |
| `r(i)` | drift rate per quarter: OLS slope of `N[s]` on `q_s` over the released rounds | `hp.slope` |
| `last_q` | reference quarter of the last released round | `hp.last_q` |
| `Δ` | quarters from `last_q` to `T` | `T − hp.last_q` |

**Drift:**

```
D = clip( W · r(i) · Δ , −CAP , +CAP )      W = 0.5,  CAP = 0.5 logit
```

**Units.** `r(i)` is per quarter. `hp.slope` is `np.polyfit` of `N[s]` on the quarter indices `M8.RQ[s]` (year × 4 + quarter − 1, e.g. 2013-Q3 = 8054). `T` and `hp.last_q` are quarter indices of the same kind, so `T − last_q` is in quarters.

**One released round:** no slope exists, so **D = 0**, the flat level of E151.
- **Outer test cells:** only ENNS2018 Leads 7 and 8 (issues 2016-Q4 and 2016-Q3; only NNS2013 released). They have no test rows, because no earlier released outcome exists for training (as in E158, where Leads 7–8 have 50 rows from 2019 and 2021).
- **Training rows:** every as-of row whose target is FNRI2015 has only NNS2013 released at its issue date, so D = 0 on all of them.

**Released rounds per outer test cell:**
- ENNS2018 Leads 1–6: two (2013, 2015).
- ENNS2019 Leads 1–8: two.
- ENNS2021 Leads 1–2: four; Leads 3–6: three; Leads 7–8: two.

**Every anchor is shifted by D:** H, RP, OH and RSS, in training rows and test rows alike, each row with its own `i` and `T`. The residual learners are then fitted to `e = y − (anchor + D)`, exactly as AUTO does.

**The inputs are only values released before the issue date.**
- They are the national levels of released rounds, with release at reference quarter + 6 (`M.released`), and the elapsed time.
- **SWS hunger change and food CPI change are not used in D.** With one to four past national changes, a coefficient on them cannot be estimated without inventing a number. SWS and HFIAS changes agreed weakly (E151: Spearman 0.27, n = 9). Food CPI already enters the model as `cpi_since`.

**Shrinkage and the one-change case:**
- `W = 0.5` is a fixed weight toward zero, the midpoint between E151's flat level (W = 0) and E150's full trend (W = 1). It applies identically whether one past change (2013→2015) or several are available.
- `CAP = 0.5` logit (about 12 points at the 50 line) limits extrapolation over long gaps, where E150 collapsed.
- Neither number is tuned, before or after the run.

## 4. Fix 4: averaging (exact)

- **Ranking:** AUTO's 36 configurations are ranked by their inner score, the weighted SSE on training rows (section 5). The order is ascending, and **ties are broken by position in AUTO's menu** (stable sort, earlier first).
- **Averaging:** the **top 5** are averaged **with equal weights** (1/5 each). Each configuration enters with its own calibration choice (identity or inner linear), as AUTO does for its single winner.
  - **Fewer than 5:** if fewer than 5 configurations can be fitted (an exception during fitting), all fitted configurations are averaged with equal weights and the count is reported. The menu has 36 entries, so this is not expected.
- **Probability:** `sd` and the 90 % range come from `app.e164.auto.scale` on the training errors `y − mean(top-5 inner OOF scores)`, and P(HIGH) = Φ(mu / sd).
- **HIGH line:** HIGH = `mu ≥ 0` (50 %), unchanged. **Unlike E165, averaging can change classes,** so accuracy can fall.

## 5. AUTO ranks configurations on training rows only

From `backend/app/e164/auto.py` (commit `cf054c8`):

```
112    tr = tr.reset_index(drop=True)
113    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
114    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
116    for a, l, f in menu(kind):
124                oof[i_te] = atr[i_te] + LEARNERS[l](FS[f]).fit(d).predict(tr.iloc[i_te])
125        sse_id = float(np.sum(w * (y - oof) ** 2))
131        sse_cal = float(np.sum(w * (y - cal) ** 2))
132        res.append({"cfg": (a, l, f), "sse": min(sse_id, sse_cal), "calib": sse_cal < sse_id, "oof": cal if sse_cal < sse_id else oof, "oof_id": oof})
137    best = min(res, key=lambda r: r["sse"])
140    mu = ate if l == "NONE" else ate + LEARNERS[l](FS[f]).fit(tr.assign(e=y - atr)).predict(te)
```

- `y` and `w` (line 113), the folds (114), the out-of-fold scores (124) and the score (125, 131) use only `tr`. `tr` comes from `M.Pipeline(...).tr` (line 169): error rows of rounds released before the issue date.
- The test rows `te` enter only at line 140, to make the forecast, after the choice at line 137. **`te["y_true"]` is never read in `run_procedure`.**
- E164's leakage control (unreleased rounds replaced by random values) changed AUTO by 0.0.
- E166 keeps this ranking unchanged and only replaces `min` (line 137) by the top-5 average.

## 6. Run and controls

- **Leads:** 1 to 8, for ENNS2018, ENNS2019 and ENNS2021, with the E158/E164 row definitions. Rows are dropped only where no round is released, as in E158.
- **Four variants per row, from two procedure calls:**

| Variant | Drift | Configurations | Role |
|---|---|---|---|
| AUTO-R | no | top 1 | **Reproduction** of E164 (Leads 1–4) |
| AVG | no | top 5 | Ablation, descriptive |
| DRIFT | yes | top 1 | Ablation, descriptive |
| **E166** | **yes** | **top 5** | **Tested model** |

- **Reproduction:** AUTO-R must equal E164's committed `mu_AUTO`, with max absolute difference < 1e-6 on Leads 1–4. Otherwise the run is **void**.
- **Leakage:** at Lead 1, E166 is re-run with unreleased survey rounds replaced by random values (as E164). E166 must change by < 1e-9. Otherwise the run is **void**.

## 7. Pass rule (fixed now)

**E166 passes only if all of these hold at Lead 1:**
1. E156 criteria C1, C2, C3, C4, C5 and C6 all pass, computed by the unchanged `app.e156.leads.evaluate`;
2. at least **55 of 72** rows are correct;
3. the Brier point estimate is not worse than AUTO's (E166 − AUTO ≤ 0);
4. the reproduction and leakage checks pass.

**C1 is stricter than the 55/72 floor.**
- C1 needs the lower 95 % bound of accuracy, at the effective sample size n_eff = 72 / (1 + 0.8 × 0.726) ≈ 45.6, to exceed the majority rule (65.3 %).
- 55/72 (76.4 %) gives a lower bound of 64.1 %, which **fails** C1.
- **56/72 (77.8 %)** gives 65.7 %, which passes.
- So 55/72 can meet the accuracy floor and still fail C1.

**If E166 passes:**
- it replaces AUTO as the release candidate;
- the maximum reliable lead is whatever `LD.evaluate` reports;
- its 2027-Q1 forecast is sealed with `live`;
- it is **not deployed** until a sealed forecast is scored.

**If it fails:** AUTO stays as the release candidate and E158 stays as the thesis model.

## 8. Reported whatever the outcome

- **For E166, AUTO-R, AVG and DRIFT, Leads 1–8:**
  - accuracy, precision, HIGH and LOW recall, F1, AUC, Brier;
  - C1–C6 and the maximum reliable lead;
  - **calibration slope and intercept, each with a 95 % region-bootstrap interval** (2,000 draws);
  - 90 % range coverage.
- **The drift D** for every outer cell, with r(i) and Δ.
- **The top-5 configurations** for every outer cell.
- **Lead-1 comparisons, E166 against:** AUTO (E164), E158, GNT (E151), **GOV**, NEWS, LR, LR_NEWS, PSA, PERS and the anchor.
  - Each comparison gives the class metrics and the Brier difference with its 95 % region-bootstrap interval.
  - E158 and the E151 arms are compared at every lead; AUTO at Leads 1–4, where it exists.
- **The Lead-1 reliability table** (5 probability bins) for E166 and AUTO.

## 9. Disclosure: every earlier attempt on these 72 Lead-1 rows

| Experiment | Lead-1 accuracy (correct of 72) | Note |
|---|---|---|
| E151 required model (GNT) | 72.2 % (52) | Base |
| E151 D5 locked attempt | 75.0 % (54) | Dropped three groups on two rounds |
| E152 prices, rainfall, regional drift | 69.4 % (50) | |
| E153 tuning with overfitting controls | 69.4 % (50) | |
| E154 frozen 11-input model | 72.2 % (52) | |
| E155 SunStar headlines | 72.2 % (52) | |
| E156 locked calibration candidate | 68.1 % (49) | Fixed C4, lost accuracy |
| E157 three-group model | 69.4 % (50) | Five sources ranked: farmgate 70.8, wholesale rice 68.1, NASA rainfall 72.2, consumption 73.6, SunStar 72.2 |
| E158 thesis model | 73.6 % (53) | |
| E159 ranking test | 73.6 % (E158) | Ordering only |
| E160 arms | RP 69.4 %, RP+R 72.2 %, OH+R 77.8 % (56) | OH+R not adopted |
| E161 nested selection | 72.2 % (52) | 77.8 % was selection optimism |
| E162 SS priority method | — | Ordering only |
| E163 candidates | C1 69.4 %, C2 70.8 %, C3 69.4 %; nested 70.8 % | None passed |
| E164 AUTO | 79.2 % (57) | Passes A1–A8; fails C4 |
| E165 AUTO + shrink | 79.2 % (57) | Classes identical; fails C4 |

More than 25 models or arms have been scored on these rows. **The design of E166 was chosen knowing these results,** including E150's slope 1.05 with a full trend, E151's slope about 0.7 with a flat level, and E165's failure. Any pass is therefore retrospective and optimistic.

**E166 is the last retrospective attempt on these rows.** If it fails, no further model or calibration is tried on them. Reliability is then claimed only from the prospective scoring of sealed forecasts (`docs/e154/SCORING_PROTOCOL.md`: E158 `f69e7a02`, AUTO `cbfb61dc`, and E166's if sealed), or from a new provincial survey round.

## 10. Not allowed after the lock

Changing W, CAP, the drift formula, K = 5, the weights, the tie rule, the menu, the HIGH line or the pass rule; dropping rows, rounds, leads or provinces; re-running.
