# RELIABLE_L12: results (EXPLORATORY)

**Plan:** `PLAN.md`, SHA-256 `666cec5b…a8aa` (commit `c37136a`). It was run exactly as written: `runner/run_l12.py`
with `check`, `leak`, `score` and `seal`.

**Evidence status:** development evidence. Every target quarter 2010-Q1..2026-Q3 was examined before. **Two
candidates were tried**, and nothing was added. Any pass would have needed confirmation on sealed 2027+ forecasts.

## Decision

**No candidate passes all of R1–R7 at both Lead 1 and Lead 2.** Under the fixed selection rule (PLAN §4), REF+news
stays the main model under the paper's 75% rule (Maximum Reliable Lead Time 2), unchanged. **Nothing is sealed.**

## 1. Checks (all passed before scoring)

- **Reproduction.** At Leads 1–2, C1 (REF) and C2 (REF+news) equal the stored IMPROVE_V2 forecasts: 226 of 226 rows
  each, max |Δp| = 0.0 (`out/checks.json`).
- **Leakage** (`out/leakage.json`), passed for both candidates at both leads:
  - (a) every training forecast has origin < t and a target label published before O(t);
  - (b) τ is identical in 20 repetitions in which every label not yet published at O(t) is randomized;
  - (c) the 2026-10-01 threshold uses labels up to 2026-Q2 only, all published before that date.

## 2. The thresholds (`out/thresholds.csv`)

| | Lead 1 | Lead 2 |
|---|---|---|
| τ over the verdict origins | 0.46 at every origin | 0.49 (12 origins), 0.52 (26), 0.53 (28), 0.68 (3) |
| Training forecasts per origin | 41–104 | 40–103 |
| Origins at the 0.50 default | 0 | 0 |

**C1 and C2 get the same thresholds.** Before 2021 the news columns are empty, so REF+news gives exactly REF's
probabilities at every origin up to 2020. The threshold training sets consist mostly of those forecasts.

**The thresholds change no call.** In all four candidate–lead cases, 0 of 62 calls differ from the 0.50 calls. No
verdict-window probability lies between 0.453 and 0.530, and the chosen thresholds fall inside that gap (or, at 0.68,
on origins with no probability between 0.50 and 0.68). Every classification metric therefore equals its 0.50 value. The
probabilities, and with them Brier, AUC and R5, cannot change by construction (PLAN, "already known").

## 3. Per lead (62 labelled quarters, targets 2010-Q1..2026-Q3)

| | C1 REF, L1 | C1 REF, L2 | C2 REF+news, L1 | C2 REF+news, L2 |
|---|---|---|---|---|
| Accuracy | 0.790 | 0.790 | 0.758 | 0.758 |
| Balanced accuracy | 0.717 | 0.717 | 0.693 | 0.693 |
| Precision | 0.812 | 0.812 | 0.804 | 0.804 |
| Recall | 0.907 | 0.907 | 0.860 | 0.860 |
| F1 | 0.857 | 0.857 | 0.831 | 0.831 |
| AUC | 0.702 | 0.704 | 0.688 | 0.674 |
| Brier | 0.1875 | 0.1838 | 0.1952 | 0.1988 |
| TP / FP / FN / TN | 39 / 9 / 4 / 10 | 39 / 9 / 4 / 10 | 37 / 9 / 6 / 10 | 37 / 9 / 6 / 10 |

### R1–R7 with values

| Rule | C1 L1 | C1 L2 | C2 L1 | C2 L2 |
|---|---|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass (62) | pass (62) | pass (62) | pass (62) |
| R2 accuracy ≥ 0.75 | pass 0.790 | pass 0.790 | pass 0.758 | pass 0.758 |
| R3 balanced ≥ 0.70 | pass 0.717 | pass 0.717 | **fail 0.693** | **fail 0.693** |
| R4 > always-LOW (0.306) and > persistence (0.661) | pass | pass | pass | pass |
| R5 Brier < persistence and < climatology, p < 0.10 | pass: −0.151 (p 0.000); −0.033 (p 0.096) | pass: −0.155 (p 0.000); −0.039 (p 0.070) | **fail**: −0.144 (p 0.000); −0.025 (**p 0.171**) | **fail**: −0.140 (p 0.000); −0.023 (**p 0.208**) |
| R6 precision and recall ≥ 0.60 | pass 0.812 / 0.907 | pass | pass 0.804 / 0.860 | pass |
| R7 each third ≥ 0.60, LOQO min ≥ 0.70 | **fail**: thirds 0.952 / **0.571** / 0.850; LOQO 0.787 | **fail**: same | **fail**: thirds 0.952 / **0.571** / 0.750; LOQO 0.754 | **fail**: same |
| **All R1–R7** | **no** | **no** | **no** | **no** |

**C1 at Lead 1 passes R5 only narrowly.** Its p against climatology is 0.096, just under the 0.10 cut-off.

## 4. Reading

- **The binding failure is R7.** The middle third of the window, 2015-Q2..2020-Q4, scores 0.571 for both models (12
  of 21 quarters correct), below the 0.60 rule.
- **A threshold rule cannot fix it.** The errors there are confident wrong calls, not borderline ones: no forecast
  sits near 0.50. Moving the threshold within 0.46–0.68 changes nothing.
- **C2 also fails R3 and R5,** as the plan stated before running. A threshold cannot change R5.
- **REF (no news) remains the stronger of the two models** on every metric of this window. It is one rule (R7) away
  from R1–R7 at both leads. REF+news is three rules away.
- **This was the one planned attempt.** Under the plan, no further variant is tried in this folder.

## 5. Files

| File | Content |
|---|---|
| `runner/run_l12.py` | The run |
| `out/checks.json` | Reproduction and input hashes |
| `out/leakage.json` | Leakage tests |
| `out/thresholds.csv` | τ(t, k) for both candidates |
| `out/results.json` | All numbers above, the selection and this plan's hash |

No seal file was written.
