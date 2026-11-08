# E135 overfitting and generalization report

**Design rule.**
- Every influence decision in X-NSD, X-SEL, X-GREG, X-STACK and X-COMB was made inside the walk-forward, from errors on targets published before each issue.
- Their S-U and S-E132 results are therefore **out-of-sample for the decision procedure itself**.
- The menu of procedures was designed after E133/E134 (disclosed). X-EXCL is post-hoc and cannot be selected.

## Did adaptive influence generalize? No.

**Lead 2, P-DASH:**

| Model | S-U within (40) | S-U MAE | S-E132 within (28) | S-E132 MAE |
|---|---|---|---|---|
| HFM-X (fixed, full influence) | **0.50** | 4.87 | 0.43 | 4.96 |
| X-RED (fixed, reduced) | 0.475 | 4.79 | **0.54** | **4.35** |
| X-NSD (nested prior) | 0.35 | 5.36 | 0.50 | 4.56 |
| X-SEL (nested selection) | 0.40 | 5.54 | 0.43 | 5.27 |
| X-GREG (nested group shrinkage) | 0.43 | 5.48 | 0.46 | 5.32 |
| X-STACK (nested HFM-X / SEAS-LLM weight) | 0.33 | 6.02 | 0.43 | 5.21 |
| X-COMB | 0.30 | 6.07 | 0.39 | 5.53 |

**Why adaptive influence failed: unstable choices that chase the last regime** (`out/e135_nested_choices.csv`):
- **X-SEL** dropped A (market) at the 2023-Q1 and 2023-Q2 issues, because drivers had not helped in calm 2021–22. It re-added A only from 2023-Q4 and kept V and aR in place of E and N.
- **X-NSD** chose the strongest shrinkage (prior SD 0.25) for every issue from 2023-Q2 to 2024-Q3, exactly the surge window. Its surge-period agreement is 0.00, against HFM-X's 0.56.
- **X-STACK** gave SEAS-LLM full weight (w = 0) during the 2023-Q4 … 2024-Q2 issues, again exactly the surge.
- **Stability rule** (modal choice in ≥ 2/3 of issues): **no** nested procedure is stable at any lead. At Lead 2 the modal shares are:

  | Procedure | Modal share |
  |---|---|
  | X-SEL | 0.31 |
  | X-NSD | 0.46 |
  | X-STACK | 0.46 |
  | X-COMB | 0.54 |

**Interpretation.** With about 10–20 past rows, past errors mostly reflect the previous regime. A procedure that learns "which information to trust" from them turns drivers off just before they become useful. This is overfitting to the recent past, and it cannot be fixed with 2021+ data alone.

## Overfitting of fixed configurations

| Check | Evidence |
|---|---|
| Parameters | HFM-X 10, FULL7 12, X-RED 10 (same structure, tighter prior), for 80 area-quarters |
| More drivers → worse | FULL7 against HFM-X: Lead-2 MAE 5.39 against 4.87 |
| Tighter prior → steadier | X-RED improves S-E132 (0.43 → 0.54; MAE 4.96 → 4.35) and keeps S-U MAE (4.79). It loses one S-U row (0.50 → 0.475). |
| Looser prior (SD 2) | Worse (E133 sensitivity: 0.40) |

## Generalization by regime (Lead 2 within; rows: pre-surge 28, surge 16, post-break 24)

| Model | Pre-surge | Surge 2024 | Post-break 2025+ |
|---|---|---|---|
| HFM-X | 0.50 | **0.56** | 0.46 |
| X-RED | **0.71** | 0.31 | 0.58 |
| SEAS-LLM | 0.64 | 0.06 | **0.71** |
| X-EXCL | 0.61 | 0.50 | 0.46 |
| X-NSD | 0.54 | 0.00 | 0.58 |

**By area** (S-U, Lead 2):

| Area | HFM-X | X-RED |
|---|---|---|
| Metro Manila | 0.8 | 0.8 |
| Balance Luzon | 0.6 | 0.3 |
| Visayas | 0.4 | 0.4 |
| Mindanao | 0.2 | 0.4 |

**Conclusion.** No configuration generalizes across regimes and areas. Reduced influence (X-RED) trades surge accuracy for calm-period accuracy, so it is not uniformly better.
