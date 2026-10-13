# Adviser-decision and data-authorization checklist

## A. Your file-by-file data authorization

| # | Item | What it unlocks |
|---|---|---|
| ☐ A1 | 2026-Q4 news file(s) with original publication timestamps (path + SHA-256), collected after the 2026-12-31 23:59:59 PHT cutoff | Supporting news for the 2027-Q1 forecast |
| ☐ A2 | 2026-Q1…Q3 news and government feature files (path + SHA-256) | Prospective sealed forecasts (`runner/seal_prospective.py`) and the 2027-Q1 feature vector |
| ☐ A3 | 2026-Q3 provincial food CPI and the September 2026 SWS round | **Only after** the 2026-Q3/Q4 forecasts are sealed (they are labels) |
| ☐ A4 | PSA 2021 SAE workbook (`2018 - 2021 SAE_with PSGC_noHUC.xlsx`), downloaded by you in a browser (psa.gov.ph blocks automated access) | LGU ranking v2: `python -B runner/lgu_rankings_v2.py --sae <path> --sae-year 2021` |
| ☐ A5 | Decision on the 16 modified tracked files E23 left in `aipheed-backend-aligned/` | Keep, or revert (`BUG_FIXES.md` §0) |

## B. Adviser decisions (Chapter I leaves these undefined)

| # | Decision |
|---|---|
| ☐ B1 | **Reliability rule** for Objective 2-V / H2 (E23/E24 provisional rule: ≥ 8 origins, ≥ 5 per class, AUC bootstrap lower bound > 0.5, Brier better than persistence with Holm p < 0.05) |
| ☐ B2 | **"Favorable" and "consistent"** for H4/H5 (`instruments/DECISION_RULES.md`) |
| ☐ B3 | **Label threshold:** training-window median (primary in E23/E24) vs the fixed 14.6 |
| ☐ B4 | Whether **supplementary SWS rounds** (2025-Q2/Q3, different respondent base) may define labels |
| ☐ B5 | Whether the **exploratory T2 target** (relative food-price pressure) may be reported as a secondary provincial indicator |
| ☐ B6 | **Chapter I wording:** the "44%" figure (DOST-FNRI reports 31.4%); Objective 4 vs H3 baseline counts; the NNS 2019 anchor (not verifiable, HFIAS); SOP Q5's withdrawn second evaluator group |
| ☐ B7 | **Prospective holdout plan:** E24-F plus the two post-hoc candidates are frozen; the first valid test needs ≥ 8 new authorized quarters (≥ 12–20 for adequate power) |

## C. Participants

| # | Step |
|---|---|
| ☐ C1 | Approve and administer the DA Region IV-A questionnaire (`instruments/`) to the 50 evaluators |
| ☐ C2 | Export the Google Form CSV and run `instruments/score_responses.py` (refuses rows without consent; never imputes) |

## D. Deployment and dependencies

| # | Item |
|---|---|
| ☐ D1 | Deploy the dashboard (not done) |
| ☐ D2 | Fix the 20 npm vulnerabilities in `frontend/` (not done; outside the isolated copy) |
| ☐ D3 | Promote a model (none qualifies) |
