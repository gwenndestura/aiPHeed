# NEWS_V2: improving REF+news by fixing how news enters the model (EXPLORATORY)

**Written:** 2026-11-03, before any candidate below was fitted or scored. Requested by you ("improve the accuracy of
REF + news").

**Label: EXPLORATORY.**

**Evidence status, stated plainly.**
- Every target quarter (2010-Q1..2026-Q3) was examined before. This is development evidence.
- **The two candidates were designed after seeing** that REF+news loses to REF only in the news era
  (`../PHASE2_INVESTIGATION.md` §5): pre-2021 identical; 2021+ accuracy 0.750 vs 0.850 (L1), 0.737 vs 0.842 (L2).
- **Exactly two candidates; nothing added later.** Any gain must be confirmed on sealed 2027+ forecasts.

**What this does not change:** the frontend, `backend/`, the served model, every existing result and seal, and every
other experiment folder. Those are read or imported read only. Nothing is pushed.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`.
`runner/run_news_v2.py` refuses to run if it changed. (Not committed: no commit authorization.)

## 1. The two candidates

Both are **REF+news with only the news columns replaced.**
- The same target: SWS BL hunger > 11.3%.
- The same 19 REF columns + `lead`.
- The same training rows, eligibility, 8-setting grid, inner chronological selection, LightGBM settings and seed.
- The same origins (1998-Q3..2026-Q3), stacked training leads 1–15 and test Leads 1–2.
- The fit is OPTION_1's `_origin` with the column list swapped.

**Anomaly.** For a news column x at origin t:

  z(x, t) = (x(t) − mean(x over origins t−8..t−1)) / sd(same), with ddof = 1.

- Only past origins' values are used. Each was itself published before its own issue date, so before O(t).
- z is NaN if fewer than 4 past values are non-missing, or if sd = 0.
- Before 2021, all news is NaN, as now.

| Candidate | News columns (replacing the 8 raw news columns of REF+news) | Why |
|---|---|---|
| **C-a "anomalies"** | z of each of the 8: `N1R`, `G_pri_yoy` and the six E112 shares | Removes the corpus's collection growth (about 5-fold 2021→2026) from levels and shares (Phase 2 cause 2) |
| **C-b "FSSI anomaly only"** | z(`N1R`) alone: one column, the paper's bias-corrected FSSI (Objective 1) | One parameter for about 20 news quarters instead of 8 columns of splits (Phase 2 cause 1) |

## 2. Checks before scoring (nothing is scored if one fails)

1. **Machinery.** The refit code with the REF+news columns reproduces the stored OPTION_1 REF+news Lead-1 and Lead-2
   forecasts (max |Δp| ≤ 1e-12, the same configuration at every origin).
2. **Leakage.** For every origin t, z(·, t) is unchanged when all news values at origins > t are replaced by random
   numbers (seed 2036, 5 repetitions).

## 3. Scoring and decision (fixed now)

**Scoring.**
- The OPTION_1 frame; the frozen R1–R7 via `hr_lib.evaluate`; targets 2010-Q1..2026-Q3; Leads 1 and 2 separately.
- **Reported per candidate and lead:**
  - accuracy, balanced accuracy, precision, recall, F1, AUC, Brier;
  - every R1–R7 value;
  - Algorithm 3 at Leads 1–8: the Maximum Reliable Lead Time under the 75% rule, to show whether Lead 3+ changes;
  - the same metrics on the **news-era quarters only** (origins ≥ 2021-Q1);
  - the SHAP share of the news columns.
- **Comparison.** Brier difference against **REF+news** and against **REF**: one-sided paired cluster bootstrap by
  quarter (seed 2036, 5000 draws), Holm across the two candidates within each lead and comparator.

**Decision.**
- **"Improves REF+news"** only if, at **both** Lead 1 and Lead 2, the candidate's Brier is lower than REF+news's with
  Holm p < 0.10 **and** its accuracy is not lower than REF+news's.
- **"News adds value"** only if, at both leads, it also beats **REF** on Brier with Holm p < 0.10.
- If both candidates qualify for a claim, the one with the lower mean Brier (Leads 1–2) is named. If neither qualifies,
  REF+news is unchanged.
- **R1–R7 are reported, not relaxed.** A candidate that improves REF+news but still fails R1–R7 is reported as such.
- No serving change and no seal here. Adopting a candidate needs your decision and a revision of the prospective
  protocol before any 2027 outcome.

## 4. Outputs

| File | Content |
|---|---|
| `runner/run_news_v2.py` | `features`, `fit`, `score` |
| `out/news_anomalies.csv` | The z columns per origin |
| `out/checks.json` | Plan hash, reproduction, leakage |
| `out/forecasts.csv` | The candidates and the reproduction rows |
| `out/results.json` | §3 |
| `RESULTS.md` | In plain words |
PLAN-SHA256: 0705ab68f4f1691cfe028b6d22996fcf2c271ba51315444ebbfce35df8aa5b60
