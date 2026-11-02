# PAPER_ALIGNED: decisions on the Step 0 questions (user, 2026-11-03)

These resolve the contradictions in `STEP0_REQUIREMENTS.md` §B. They are fixed before any PAPER_ALIGNED result.
PLAN.md (Step 1) will carry them into an exact, hashed protocol.

| # | Topic | Decision |
|---|---|---|
| 1 | Study window (C4) | Follow §3.2: **2020-Q1..2026-Q3, 135 province-quarters**. Algorithm 4 holdout **2025-Q4..2026-Q3**. |
| 2 | Features (C5) | The paper's **45 → 12 selection**. The selection rule is fixed in PLAN.md before any result and computed **on training folds only**. |
| 3 | Model (C6) | **Single LightGBM** (Algorithms 3–4, Rule 2) is primary. The 0.4 / 0.4 / 0.2 blend (cutoff 0.712) is reported as **secondary only**. |
| 4 | CPI deviation and label (C8, label code) | Feature `CPI_dev` as **Eq. 5** (deviation from the rolling provincial mean). Label **Eq. 3 via `risk_score_v2.py`**: missing values blank, never 0. The legacy `label_generator.py` is used **only for the global-median sensitivity**, with `AIPHEED_ALLOW_LEGACY_LEAKY_LABELS=1` set **only for that run**, and disclosed. |
| 5 | DEPDev (C3) | **Out of the evaluation** for now. Its usability questionnaire is still prepared, marked **optional**. |
| 6 | Population density (C13) | **POPCEN 2024**. |
| 7 | Eq. 4 and Rule 7 (C18, C19) | Approved as proposed. **Eq. 4:** the mean and SD of the province's food CPI YoY over the trailing 24 months, from data before t; HIGH if the value exceeds mean + SD in two consecutive quarters. **Rule 7:** an alert when the province's forecast probability exceeds the 75th percentile of its own past published forecasts (trailing 8 quarters). |
| 8 | FNRI (C1) | **NNS 2023 only**: CALABARZON 19.1% (95% CI 17.0–21.1), FNRI 2023 NNS Food Security page. Face validity only, never a label. |
| 9 | E99 | **First bring in E99** (`origin/e99-chapter3-evaluation`) as the reference and **reproduce it exactly**, without modifying the method to make it pass. If it reproduces: report the paper's pipeline result honestly, write OBJECTIVES_STATUS.md on that basis, and write a short adviser note comparing it with the IMPROVE_V2 hunger-only model as a possible Chapter 3 amendment. **Stop before any further runs.** |
| 10 | OBJECTIVES_COMPLETION | Committed as WIP (`e7b76ab`). |
| 11 | Other recommendations | Accepted:<ul><li>run all 6 comparators;</li><li>truncate text at 512 characters;</li><li>blanks, not zeros;</li><li>STAGED forecasts stay off the public dashboard;</li><li>no automatic DSWD alerts;</li><li>LGU rankings marked "not validated" if no lead passes.</li></ul> |

No push to GitHub; local commits only. No frontend change.

## Paper wording fixes (to give the adviser)

These are places where the paper contradicts itself. The decision above follows one reading; the paper's text should
be corrected to match.

| # | Where | Current wording | Fix |
|---|---|---|---|
| W1 | §1.7 (p. 15) vs Eq. 3 legend (p. 52), §3.3.2.6 (p. 36), §3.2 (p. 30) | §1.7: news "2021 to 2025"; Eq. 3 legend: "all **120** province-quarter pairs"; §3.3.2.6: 120 rows, 2020-Q1..2025-Q4 | Use one window throughout: **2020-Q1..2026-Q3, 135 province-quarters**, with the 2025-Q4..2026-Q3 holdout (§3.2) |
| W2 | RQ5 (p. 11) | "DA Region IV-A personnel, as system evaluators, and **DEPDev Region IV-A personnel, as usability evaluators**" | Match H5, §1.7 and §3.7: **50 DA Region IV-A evaluators** assess both functional accuracy and usability (DEPDev optional, if kept at all) |
| W3 | Algorithm 5 (pp. 45–46), §3.5 (p. 60) | "**2020 census** population density" | "PSA **2024 POPCEN** population density" |
| W4 | Objective 5 (p. 13) | "DOST-FNRI NNS **2019 and 2023**" | "DOST-FNRI **NNS 2023**" (NNS 2019 used HFIAS, a different scale). Chapter 3 (p. 51) also says "NNS 2021 and NNS 2023"; align it to NNS 2023. |
| W5 | Objective 4 (p. 13) vs RQ3 and H3 (pp. 10–11) | 4 baselines vs 6 comparators | List the **six** comparators in Objective 4 as in RQ3 and H3 |
| W6 | §3.3.2.1 (p. 33), Algorithm 1 (p. 37) vs §3.2 (p. 30), §3.6 (p. 65) | 512 vs **250** characters | **512** throughout |
| W7 | §3.3.2.6 (p. 37) vs §3.6 (p. 65) | "remaining gaps will be **zero-filled**" vs "left missing rather than filled with zeros" | **Left missing** throughout |
| W8 | §3.5 and §3.6 (pp. 60, 66) vs Rule 1 (p. 48) and the state diagram (pp. 66–67) | STAGED forecasts "remain visible on the dashboard" vs "mandatory review before publication" | STAGED forecasts are **not public** until approved |
| W9 | Eq. 3 legend (p. 52) vs Rule 3 (p. 48) | "global_median … across all 120 province-quarter pairs" (uses future outcomes) | Median of the **training quarters at each forecast origin**; the global median as a sensitivity |
| W10 | Eq. 3 (p. 51) vs Eq. 5 legend (p. 53) | Two different "CPI deviation" definitions | Name them differently: the label term (deviation from the cross-province mean) and the feature `CPI_dev` (deviation from the rolling provincial mean) |
| W11 | Eq. 4 (p. 51); Rule 7 (p. 49) | Undefined CPI̅(p,24), σ_p; undefined "rolling historical threshold" | The definitions in decision 7 |
| W12 | §3.2 (p. 30), §3.5 (p. 59) vs Algorithms 3–4 and Rule 2 (pp. 41–48) | A 0.4/0.4/0.2 blend vs one LightGBM | One LightGBM as the proposed model; the blend, if kept, as a secondary comparison |
| W13 | §3.3.1.1 (p. 31) vs §3.2 (p. 30) | 17,791 vs 6,085 articles | The corpus count actually used |
| W14 | §3.7 (p. 67) | DA evaluators "label and verify training data" | The label is computed (Eq. 3), not annotated; describe their role as verifying, if any |
