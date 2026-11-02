# LEAD2_PERSIST_BLEND: M3 with price persistence (EXPLORATORY)

**Written:** 2026-11-02, before this candidate was computed or scored.

**Authorised by** the user, who lifted for this one study the rule "no re-selection using the 2023–2026 quarters".

**Label: EXPLORATORY.** The 65 Lead-2 rows (13 target quarters, 2023-Q2..2026-Q3) have already been scored by at least seven Lead-2 variants: P0H4, M0, M2, A1, A2, M3 and the M3 rule exploration. A pass here is a post-hoc candidate for a pre-registration addendum judged on sealed 2027+ quarters only. **It can never be called reliable from these rows.**

**What this does not change:** the served model, the dashboard, `backend/data`, `PREREG_LEAD2.md` and its addenda, and the seals. The runner writes only `out/` in this folder.

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`.

## 1. Why this candidate (disclosed before scoring)

Results already seen on these rows:
- **M3** (`LEAD2_MIDQUARTER_UPDATE`, plan `6b5bff74`) scored 11/8/6/40 and failed R6 only: precision 0.579 and recall 0.647.
- In an earlier split-target check in this project (2026-11-01/02, not saved to the repository), on the provincial price target at Lead 2, persistence of the newest price condition reached accuracy 0.677, against 0.646 for the price model.
- The baseline metrics of PERSIST-SI at the M3 date were also seen in the M3 results.

**The idea.** Average the M3 price model with the province's newest price condition, so that a price spike already under way is not forgotten. A false alarm raised by the model alone is damped when prices are calm now.

**Only one candidate is scored.** The weights are fixed and nothing is tuned.

## 2. Candidate B (fixed exactly)

| Item | Definition |
|---|---|
| Issue date, target, rows | As M3: D(t) = the first day of the second month of quarter t+1; target t+2; the 65 rows of `LEAD2_MIDQUARTER_UPDATE/out/rows.csv` |
| Hunger part h | `pi_H4_m3` (unchanged) |
| Model price part m | `P0_price_m3` (unchanged) |
| Price persistence s | 1 if the province's newest three CPI months available at D(t) show the price condition, else 0. The cutoff is `SI.cpi_newest(D(t))`, and the condition is the price half of `persist_clim_at` (`LEAD2_POST_SWS_ISSUE/runner/score.py`): mean food YoY > the province's food threshold, or mean (food − all-items) YoY > its gap threshold (`L.e40_spec()`). If fewer than three months exist for food or all items, s is missing |
| Blended price part | p = 0.5 × m + 0.5 × s; p = m when s is missing |
| Probability | B = h × p |
| Decision | HIGH when B ≥ 0.50 |

## 3. Evaluation (unchanged rules)

- **Rules.** R1–R7 as frozen, computed by `P0H4_LEAD12_REVIEW/runner/reproduce.py` `rules()`. The baselines are the M3-date baselines already in the rows: PERSIST-SI = `PERSIST_m3`, CLIM = `CLIM_m3`, plus ALWAYS-LOW. The bootstrap resamples target quarters (seed 2036, 5000 draws).
- **Reported:**
  - the confusion matrix, accuracy, balanced accuracy, precision, recall, AUC and Brier;
  - every rule with its value;
  - each target quarter;
  - the same metrics for M3, for reference.
- **Wording of the outcome:**
  - If all seven pass: "B passes R1–R7 in-sample (post-hoc, exploratory)". It becomes a candidate for a sealed 2027+ test, not a reliable forecast.
  - If any rule fails: "B fails", with the rules named.

## 4. Leakage check (before scoring)

For every origin, the runner asserts that:
- the newest CPI month used for s is ≤ `SI.cpi_newest(D(t))`;
- that month is available by D(t), from the first day of month M+2;
- the three months are exactly cutoff − 2, cutoff − 1 and cutoff.

PLAN-SHA256: 98770618971afac2725c6fa2a65f183f7e3fe20b1b89f4dfe6332604ea8e5aca
