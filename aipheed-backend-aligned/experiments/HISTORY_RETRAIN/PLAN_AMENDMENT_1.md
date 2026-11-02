# HISTORY_RETRAIN, Amendment 1: deep-learning models (EXPLORATORY)

**Written:** 2026-11-02, after `PLAN.md` (`6b9f17fb…`, commit `d9e2335`) and **before any label, model or baseline was
computed**. No result exists at the time of writing.

**Why this amendment exists.** The original request fixed the model list as persistence, logistic regression and
LightGBM, with "no additions later". `PLAN.md` therefore had no deep-learning model. The user asked for them on
2026-11-02, before Step 3. They are added here, before any result, so the addition cannot depend on what the results
show. Everything in `PLAN.md` stays as it is:
- targets, windows, data and release rules;
- the baselines;
- R1–R7 and the Brier criterion;
- the checks and the reporting.

**Remittances (PLAN.md §1 conditional rule).** No BSP file was in `data/raw/` when Step 3 began, so option (c) runs
**without E2**.

**Hash.** As in PLAN.md: the SHA-256 is computed over every byte before the last line, which begins
`AMENDMENT-SHA256:`.

## 1. Added models (fixed list)

| ID | Target | Inputs | Probability |
|---|---|---|---|
| **MLP** | T1 | F_b(T1) for (b), F_c(T1) for (c): the same columns as the LightGBM, including `lead` and H1 | π_H4L × π_P^MLP. The MLP replaces the LightGBM in the price part; nothing else changes. |
| **MLP** | T2 | F_b(T2) for (b), F_c(T2) for (c): the same columns as the T2 LightGBM | Direct P(T2 HIGH) |
| **GRU** | T1 | The F_b(T1) rows of the **last 8 origins** (t−7..t) for the same province and lead. Option (b) only. | π_H4L × π_P^GRU |
| **GRU** | T2 | The F_b(T2) rows of the last 8 origins for the same lead. Option (b) only. | Direct P(T2 HIGH) |

**GRU inputs.**
- Each step is the feature row as built **at its own issue date** O(t−j). Everything in it was published before
  O(t−j) < O(t), so the sequence adds no information that was unavailable at O(t).
- A row whose earliest step would precede origin 1998-Q3 is not used. GRU rows therefore start at origin 2000-Q2.

**Training rows, labels and stacking** are exactly those of the LightGBM of the same target, at every origin:
- the walk-forward rule;
- leads 1–15 stacked, with `lead` as an input;
- the T1 price condition for π_P;
- the T2 label;
- the eligibility rule and its fallback (training HIGH share, or CLIM).

The GRU additionally drops rows without 8 steps.

## 2. Architecture and training (fixed now; nothing is tuned)

| Item | MLP | GRU |
|---|---|---|
| Layers | Linear(n, 32) → ReLU → Dropout(0.3) → Linear(32, 1) | GRU(n, 16), 1 layer → last hidden state → Dropout(0.3) → Linear(16, 1) |
| Loss | binary cross-entropy (no class weights) | same |
| Optimizer | AdamW, learning rate 1e-3, **weight decay 1e-2** | same |
| Batches | 256, reshuffled each epoch by a seeded generator | same |
| Epochs | at most 200 | same |

**Preprocessing**, fitted on the fitting rows only (for the GRU, on all their steps):
- missing values are filled with the training median, then every column is standardized;
- a column with no training value, or with sd 0, is set to 0.

**Early stopping** (only earlier quarters):
- At origin t, the validation rows are the training rows whose origin is among the **last 4 training origins**. These
  are the same held-out origins as the LightGBM inner validation.
- The fitting rows are the training rows whose target q′ ≤ (the earliest of those 4 origins) − 1.
- Validation log-loss is computed after every epoch, with patience 20.
- E* is the epoch with the lowest validation log-loss.
- The network is then **refitted from scratch on all training rows for E* epochs**, with the same seed.
- If there is no validation row, or the fitting rows lack a class, E* = 50.
- No verdict-window row is ever used for fitting, validation or stopping.

**Seeds.**
- 10 seeds, s = 0..9.
- At origin t the generator seed is 1000·s + t, set for `torch`, `numpy` and `random`.
- `torch.use_deterministic_algorithms(True)`, `torch.set_num_threads(1)`, CPU only. Each run is exactly reproducible
  from `runner/dl.py`, the seed and the data.
- Library versions are recorded in `out/results.json`.

## 3. Evaluation and verdict

**Scoring.**
- Every seed is a complete walk-forward run.
- Each seed is scored on the PLAN.md verdict windows, with the same `rules()` (R1–R7), the same R1 units per target,
  the same baselines and the same Brier criterion.

**Reported for each deep model × input set × target × lead:**
- the mean, sd, minimum and maximum over the 10 seeds of accuracy, balanced accuracy, precision, recall, AUC and Brier;
- for each rule, how many seeds pass it (k/10);
- how many seeds are reliable.

**Never pick the best seed.** A deep model is called **reliable only if all 10 seeds are reliable**. A model with 1–9
reliable seeds is reported as "unstable: k/10 seeds pass" and is **not** reliable.

**"Did deep learning beat X?"** X is LightGBM, LOGIT or persistence, with the same target, lead and input set. The
answer is reported per target and lead from:
- the seed-mean Brier against X's Brier;
- the seed-mean accuracy against X's accuracy;
- the number of seeds (k/10) with a lower Brier than X.

Deep learning is said to **beat** X only if the seed-mean Brier is lower **and** at least 8/10 seeds have a lower
Brier. The Step-4 verdict states this in plain words.

AMENDMENT-SHA256: 319ae4d28b83b52875542cfcff7c689c3c05625f431d114d80c70fd99c6dd474
