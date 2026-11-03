# RELIABLE_L12: one attempt to make the food-insecurity forecast pass R1–R7 at Leads 1 and 2 (EXPLORATORY)

**Written:** 2026-11-03, before any threshold, decision or score in this folder was computed.

**Label: EXPLORATORY.**

**Evidence status, stated plainly.**
- Every target quarter scored here (2010-Q1..2026-Q3) was examined before, in HISTORY_RETRAIN, IMPROVE_V2,
  IMPROVE_V2_LEADS and OPTION_1. This is **development evidence**.
- **Exactly two candidates are tried** (C1, C2), and nothing is added later.
- Any pass must be confirmed on sealed 2027+ forecasts before it is called reliable.

**Target, unchanged:** y(q) = 1 when SWS Balance Luzon involuntary hunger H(q) > 11.3% (the quarter mean of
non-commissioned rounds), else 0; a quarter without a round has no label. It is the same definition, the same
labels file (`IMPROVE_V2/out/labels_areas.csv`, BL rows) and the same verdict window as IMPROVE_V2 and OPTION_1.

**What this does not change:**
- the frontend, `backend/`, the served model (REF+news in the `foodinsecurity` mode);
- every existing seal and ledger;
- IMPROVE_V2, IMPROVE_V2_LEADS, OPTION_1 (code and results) and every P0H4 file.

They are read only (`sys.dont_write_bytecode = True`). Everything new is written under
`aipheed-backend-aligned/experiments/RELIABLE_L12/`. Nothing is pushed to GitHub; commits are local only.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`.
`runner/run_l12.py` refuses to run if the file changed after hashing.

**Known cause** (OPTION_1/RESULTS.md): at threshold 0.50 the model says HIGH too often and misses LOW quarters.
- Balanced accuracy is 0.693.
- Accuracy in the middle third (2015–2020) is 0.57.

**What is already known before running** (from stored results, so it is stated here, not discovered later):
- A decision threshold changes the HIGH/LOW calls only. **It cannot change the probabilities**, and so it cannot change
  the Brier score, the Brier comparisons of R5 or the AUC.
- **REF+news (C2) fails R5 at 0.50:**

  | Lead | Brier vs climatology | p |
  |---|---|---|
  | 1 | −0.025 | 0.171 |
  | 2 | −0.023 | 0.208 |

  It therefore **cannot pass R1–R7 under any threshold**. C2 is run anyway, as instructed, and reported.
- REF (C1) at 0.50 fails R7 only (IMPROVE_V2/RESULTS.md: Lead 1 and Lead 2 accuracy 0.790). Whether a threshold can fix
  R7 without breaking R2, R3, R4 or R6 is not known.

**Read before writing this plan:**
- `OPTION_1/RESULTS.md` and `runner/run_option1.py` (the score frame);
- `IMPROVE_V2/PLAN.md` §2, §6 (baselines, verdict window);
- `HISTORY_RETRAIN/runner/hr_lib.py` (`evaluate`, `rp`);
- `P0H4_LEAD12_REVIEW/runner/reproduce.py` (the frozen `rules()`; it classifies at a hard-coded 0.50).

**What was seen before this plan:**
- every published IMPROVE_V2, IMPROVE_V2_LEADS and OPTION_1 result;
- the column layouts of `IMPROVE_V2_LEADS/out/forecasts_leads.csv` (REF, PERSIST, CLIM, origins 1998-Q3..2026-Q3, leads
  1–15) and `OPTION_1/out/forecasts_refnews.csv` (REF+news, same origins).

No threshold was computed.

## 1. Forecasts (nothing refitted)

The stored walk-forward forecasts are used as they are, so the model settings, grid, seed, issue dates and leads are
IMPROVE_V2's by construction:

| Candidate | Probabilities | File (SHA-256 recorded and checked) |
|---|---|---|
| **C1** | REF (no news), `name == "REF"` | `IMPROVE_V2_LEADS/out/forecasts_leads.csv` |
| **C2** | REF+news, `name == "REF+news"` | `OPTION_1/out/forecasts_refnews.csv` |

**Check before scoring.** At Leads 1–2 both must equal the stored IMPROVE_V2 forecasts (`IMPROVE_V2/out/forecasts.csv`)
bit for bit (max |Δp| ≤ 1e-12), or nothing is scored. Fallback forecasts (the training HIGH share) are kept, as in
IMPROVE_V2.

## 2. The threshold rule (the only change, the same for C1 and C2)

**Separately for each candidate, each lead k ∈ {1, 2} and each origin t,** the threshold τ(t, k) is chosen as follows.

**Training forecasts.** The same candidate's walk-forward forecasts at the same lead k, from origins t′ < t, whose
target quarter q′ = t′ + k has a BL label **published before O(t)**. O(t) is the first day of quarter t+1, the issue
date. "Published" uses `iv2_lib.known_labels(d, t, lab)`: a quarter's label counts only when all its non-commissioned
rounds were published before O(t), the rule IMPROVE_V2 uses for training labels.

**Default.** τ = 0.50 when there are fewer than 20 training forecasts. It is also 0.50 when the training forecasts
contain only one class, because balanced accuracy is then undefined.

**Choice.**
- τ is the value on the fixed grid {0.01, 0.02, …, 0.99} that maximizes the balanced accuracy of the call
  "HIGH when p ≥ τ" on the training forecasts.
- **Ties** go to the grid value closest to 0.50, then to the lower value.

**Call.** HIGH when p(t, k) ≥ τ(t, k).

**Nothing else is tuned:** no recalibration, no new inputs, no change to the probabilities.

**Leakage test** (run first; nothing is scored if it fails):
- **(a) Inputs.** For every (t, k), every training forecast used has origin < t and a target label published before
  O(t). This is asserted row by row.
- **(b) Perturbation.** All BL labels **not** published before O(t) are replaced by random labels (seed 2036, 20
  repetitions). τ(t, k) must be identical in every repetition, at every origin.
- **(c) Timing.** The threshold for the 2026-10-01 issue uses no label of 2026-Q3 or later unless it was published
  before 2026-10-01.

## 3. Scoring (verdict window: targets 2010-Q1..2026-Q3, labelled quarters only)

This is the OPTION_1 frame (`run_iv2.frame`, BL labels, with the PERSIST-SI, CLIM and ALWAYS-LOW baselines unchanged).
The frozen `rules()` is used **unedited**, in two passes:

| Pass | Column given to `rules()` / `hr_lib.evaluate` | Taken from it |
|---|---|---|
| **Decision** | 1.0 if p ≥ τ(t, k) else 0.0. Because 1.0 ≥ 0.50 exactly when p ≥ τ, the frozen 0.50 classifier reproduces the τ-call | R1, R2, R3, R4, R6, R7; accuracy, balanced accuracy, precision, recall, F1, TP/FP/FN/TN |
| **Probability** | p itself | R5 (Brier vs PERSIST-SI and vs CLIM, one-sided cluster bootstrap by quarter, seed 2036, 5000 draws); AUC; Brier |

**Reported per candidate and lead:**
- accuracy, balanced accuracy, precision, recall, F1, AUC, Brier;
- each of R1–R7 with its values and pass or fail;
- the distribution of τ over the verdict origins (min, median, max, share of origins at the 0.50 default);
- the same at 0.50 as the reference.

## 4. Selection rule (fixed now)

1. A candidate counts as **reliable only if it passes all of R1–R7 at both Lead 1 and Lead 2**.
2. If both pass, the one with the lower Brier score (the mean of the Lead-1 and Lead-2 Briers) is chosen. If they tie,
   C2 is chosen, because the thesis title requires news.
3. If neither passes, **REF+news stays the main model under the paper's 75% rule** (Maximum Reliable Lead Time 2),
   unchanged.

**A chosen candidate is a finding, not a deployment.** Serving it needs a separate plan and your approval. The
backend is not changed here.

## 5. Seal (only if a candidate is chosen)

**What is sealed.** The chosen candidate's forecasts issued 2026-10-01 (origin 2026-Q3):
- 2026-Q4 at Lead 1, and 2027-Q1 at Lead 2;
- each with its probability, τ(2026-Q3, k), class and the newest SWS round used.

These are the latest issuable forecasts. The 2027-01-01 issue cannot be computed before its data exist.

**Where.** A **new** file, `RELIABLE_L12/sealed_prospective_L12.csv`, with its SHA-256 in a new
`RELIABLE_L12/SEAL_LEDGER.md`. No existing seal is touched.

**Labels.** Both files say "sealed after the development results were known; prospective, not an independent test of
them".

**If no candidate is chosen,** nothing is sealed.

## 6. Outputs

| File | Content |
|---|---|
| `runner/run_l12.py` | `check`, `leak`, `score`, `seal` |
| `out/thresholds.csv` | τ(t, k) for both candidates, with the number of training forecasts |
| `out/leakage.json` | Leakage tests (a)–(c) |
| `out/results.json` | §3 per candidate and lead, the selection of §4, the input hashes and this plan's hash |
| `RESULTS.md` | The numbers, the decision and the evidence statement above, in plain words |
PLAN-SHA256: 666cec5bad74e289e29156bbaa991caaee303ada4b63d6086e63324a074ca8aa
