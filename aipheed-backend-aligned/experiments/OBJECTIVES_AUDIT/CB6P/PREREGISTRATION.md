# C-B6P pre-registration: C-B6 as a province-quarter forecast (Chapter III Eq. 3) with employment and OFW remittances (fixed 2026-11-04, before any fit)

**Development evidence.** Owner request: make C-B6 forecast per province-quarter as Chapter I/III state, and add
employment (E1) and OFW remittances (E2) as inputs. C-B6 (served, regional) is unchanged unless the team and adviser
decide otherwise after these results. Nothing is served automatically; no frontend change.

## Label (Chapter III Eq. 3, leak-free threshold)

- S(p, q) = H_BL(q) + 2 x D(p, q)
  - H_BL(q): SWS Balance Luzon hunger, quarter mean of non-commissioned rounds (`iv2_lib.area_labels`, area BL).
  - D(p, q): province p's PSA food CPI year-on-year (quarter mean of the three months, PSA-published,
    `E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv`) minus the mean of the five provinces.
- y(p, q) = 1 when S(p, q) > THR.
- **THR = median of S over the 2021-Q1..2022-Q4 province-quarters with a label** (fixed rule; the paper's all-period
  median uses test outcomes and violates Rule 3). Same principle as C-B6's 11.3% (2021-22 percentile). Disclosed:
  2021-22 quarters are also scored.
- Quarters before 2021-Q1 (no provincial CPI): BL rows with D = 0 by definition, so S = H_BL, y = H_BL > THR.

## Availability (as-of rules)

- Origin t, issue date O(t) = first day of quarter t+1 (`hr_lib.issue`).
- PSA CPI month m is usable at O(t) when m <= issue month - 2 (m_avail), as served (`psa_newest_month`).
- A province label (p, q) is known at O(t) when the BL label of q is known (`iv2_lib.known_labels`) and all three
  CPI months of q are <= m_avail.

## Inputs (26)

- C-B6's 23 exactly (`PC.CB + ST1, ST2`, same table and files).
- **E1** employment: national unemployment change (`hr_lib._e1`, already in the table).
- **E2** OFW remittances: personal-transfers decline (`ce_model.e2_series`, `out/ce_features.csv`).
- **D1** province price deviation known at O(t): mean of D over months m_avail-2..m_avail. NaN on BL history rows.

## Model (C-B6's procedure)

- LightGBM, `hr_lib.lgbm_select` (inner chronological folds) over `hr_lib.GRID`, settings, seed unchanged.
- Training at origin t: rows with t' < t, q <= t-1 and a label known at O(t):
  BL rows for q < 2021-Q1; five province rows for q >= 2021-Q1. Same eligibility and fallback as C-B6.
- Test: five province rows per lead from origin t. Origins 2020-Q1..2026-Q3, leads 1-8.
- Threshold 0.50.

## Arms

| Name | Definition |
|---|---|
| **C-B6P** | the model above, 26 inputs |
| C-B6P-noE | same, without E1 and E2 (ablation: does employment/OFW help?) |
| C-B6-R | served C-B6 regional probability (`out/cb6_fits.csv`), same for all five provinces |
| PERSIST | last province label known at O(t) (BL history label if none) |
| LOGIT | `hr_lib.logit` on C-B6P's 26 inputs, same rows |

## Evaluation

- Sample: province-quarters with q >= 2021-Q1 and a label, leads 1-2 (Algorithm 3: leads 1-8).
- Metrics (Objective 2): accuracy, balanced accuracy, precision, recall, F1, AUC-ROC, Brier.
- Algorithm 3: furthest lead L with accuracy >= 0.75 at every lead 1..L.
- Paired Brier, C-B6P minus each other arm, cluster bootstrap by target quarter (B 5000, seed 2036), one-sided p;
  Holm over the 8 tests (2 leads x 4 arms).

## Acceptance (as Chapter III; all required to recommend serving)

1. Accuracy >= 0.75 and F1 >= 0.75 at Leads 1 and 2; AUC-ROC >= 0.80 at Lead 1.
2. Brier better than PERSIST, LOGIT and C-B6-R at both leads, Holm p < 0.05.
3. Leakage check: changing every CPI month > m_avail leaves D1 unchanged.
4. Team and adviser approval.

E1/E2 are judged by C-B6P vs C-B6P-noE (reported, not a gate). **Reported whatever the result. No variant after
seeing results.**
PLAN-SHA256: e6405536be4f4ff56900db86bdd5d5b65c8744a7d7034d4cf7b776f951c5352b
