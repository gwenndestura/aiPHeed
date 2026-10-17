# E50: why climate stress appeared to dominate the five triggers

**Branch:** `e46-lead2-policy`, after E49 (f1431f4). **Date:** 2026-10-17. No model was refitted; probabilities and frozen forecasts are unchanged.

## Direct answer

**Climate was not the dominant contributor.** Its apparent dominance came from a **defect in the explanation design**, not from the model, the data or the price calculation.

**The defect:**
- The E46 attribution credited each group only with its ridge **residual correction**.
- The model's main price input, the **base-effect projection of food inflation and of the food-minus-headline gap built from PSA CPI**, was treated as the baseline and credited to no group.
- So **market/prices were heavily under-represented**, and the residual corrections of climate and the national proxies (employment, OFW) looked largest.

**With a complete, consistent attribution** (every group's inputs moved to their training mean, market including the CPI projection), over all 50 served province-quarters:

| | Market ranked first | Market's mean share | Climate ranked first | Climate's mean share |
|---|---|---|---|---|
| Before (served) | 10 | 10.5% | 15 | 34% |
| After | **47** | **82%** | **1** | 8.5% |

The latest regional SWS hunger level, which is not a trigger, accounts for 17% on average and is now reported separately as "other".

**The fix changes only the explanation.** The forecast probabilities are identical (50/50 checked).

## 1. How contributions were computed (trace)

**Model** (E46 I7, `e46` flag):
- p = P(hunger > 11.3) × P(price signal);
- F̂ = base-effect food projection + ridge residual;
- Ĝ = base-effect gap projection + ridge residual;
- Ĥ = latest SWS level + hunger ridge.

**Served method before E50** (`build_record_e46.py`):
- per group, Δlog-odds of p when that group's ridge contributions (z · coefficient, i.e. relative to the training mean of the residual inputs) are removed from F̂, Ĝ and Ĥ;
- the base projections and the SWS level stayed fixed and were attributed to nobody.

**Dashboard percentages:**
- each contributing group's |Δlog-odds| ÷ the sum over contributing groups (integer split), with the sign shown as raises or lowers;
- the denominator and signs were correct; the omission was the whole problem.

**Region:** the five provinces' attributions pooled.

## 2. Climate and market feature audit

| Group | Inputs in the price residuals | Inputs in the hunger ridge | Province-varying? | Cutoff (E47 audit) | Missing handling |
|---|---|---|---|---|---|
| Climate | tc_count, tc_count_l1, enso, enso_l2, palay_yoy, corn_yoy, enso×mom3, tc_l1×palay (8) | enso, enso_l2, tc_count, tc_count_l1, palay_yoy (5) | typhoons and production yes; ENSO no | typhoons ≤ t; production and ENSO ≤ t−1, all published before issue | median + missing flag, training only |
| Market | F_hat_M1, F_now, D_now, gap_now, rice_whsl_yoy + policy (residual), **plus the base-effect food and gap projections** (the model's core price inputs) | F_now (1) | yes | CPI through month 2 of t (18-day minimum margin) | same |

- No leakage, duplication-by-mistake or feature-order mismatch was found: additivity holds to 1.8e-15 and the refits reproduce to 1e-9 (E47).
- **Why climate's residual weight looked large:** it has 8 + 5 inputs, including interactions, against market's 5 + 1. Its residual ridge correction is therefore spread over more terms, and its effect on the *residual* appears large relative to the market residual. That says something about the residual, not about the total price dependence.

## 3. Comparison over all 50 province-quarters (`runs/attribution_audit.json`)

**Ranked first:**

| Method | Market | Climate | Employment | OFW |
|---|---|---|---|---|
| Served before E50 (residual only) | 2 | 16 | 14 | 18 |
| Complete reference (E50) | **47** | 1 | 2 | 0 |
| Refit without the group's residual inputs* | 20 | 12 | 14 | 4 |

\* Refit-drop removes only residual inputs; the base projection cannot be dropped as a trigger. At origins where the residual was "none", refit-drop changes nothing (rows of 0).

- **Mean share before:** market 10%, climate 34%, employment 17%, OFW 18%, fish 5%.
- **Mean share after:** market 82%, climate 8.5%, employment 5%, OFW 3%, fish 1.5%.
- **By province after:** market ranks first in 47/50, and in every province except one or two quarters each.
- Before, the leading group shifted erratically between climate, employment and OFW, quarter to quarter, which pointed to an unstable explanation rather than stable model behaviour.

**Quezon (log-odds effect, after / residual-only before):**

| Quarter | Market | Climate | OFW | Hunger level ("other") |
|---|---|---|---|---|
| 2026-Q2 | −0.51 / +0.06 | −0.18 / −0.18 | +0.02 | 5% |
| 2026-Q3 | **+1.22** / +0.04 | −0.15 / −0.15 | +0.08 | 35.5% |
| 2027-Q1 forecast | **−2.32** / +0.07 | +0.14 | | 3.5% |

## 4. E38 vs E46 explanations

- **E38 (production):** the inputs are price deviation and SWS hunger. Climate, fisheries, employment and OFW are not model inputs and are shown as "not used in this forecast". **Market is 100%** of the five-group share.
- **E46:** now attributed with the complete method above.
- The two methods differ (TreeSHAP on a classifier vs a reference-mean log-odds effect on a component model), so their percentages are not directly comparable.

## 5. Controlled diagnostics (fixed models; synthetic, not forecasts)

- **±1 SD on each province's market residual inputs** moves p modestly, e.g. Quezon 2026-Q3 0.861/0.843. The same for climate gives 0.856/0.849. Both residuals are small corrections.
- **The large price dependence sits in the CPI base projection:** moving it to its training mean changes log-odds by −2.3 to +3.4 across quarters.
- **Refit-drop** agrees that market's residual matters most where residuals were selected (20/50).
- **The latest SWS level** dominates only where hunger is near its threshold (2024-Q4/2025-Q1 targets).

## 6. Correction (code)

**`backend/scripts/build_record_e46.py`:**
- `full_attribution()`: every group's inputs go to the training mean; market includes the base food and gap projections; the SWS level goes to `otherContribution` / `other_pct`.
- The status rule applies to the total market effect.
- The old residual-only effect is kept as `residualOnlyLogOddsEffect`, with `baseProjectionFoodPoints` / `baseProjectionGapPoints`.
- A record-level `attributionMethod` is added.

**`backend/app/api/v1/insights.py`:** an E46-specific explanation note (method, reference, "not causes and not shares of food insecurity").

**`backend/data/e46/e46_record.json`:** rebuilt. Probabilities unchanged; frozen 2027-Q1 file unchanged (sha `5592d53e…`).

**Test:** `test_e50_market_attribution_includes_the_cpi_projection`:
- market carries its base projection;
- the other groups are unchanged;
- "other" is in [0, 100];
- market leads in the majority (a measured result);
- the note text.

## 7. Metrics (unchanged: explanation-only change)

**I7 on T43, development:**

| Accuracy | Balanced | HIGH recall | LOW recall | Brier | AUC |
|---|---|---|---|---|---|
| 0.800 | 0.684 | 0.44 | 0.92 | 0.174 | 0.735 |

**75% with meaningful HIGH/LOW discrimination is not met.**

## 8. Tests and live verification

| Suite | Result |
|---|---|
| Backend (`backend/venv/Scripts/python.exe -m pytest -q`) | **368 passed, 18 skipped, 0 failed** |
| Frontend (`npx vitest run`) | **45 passed** |

**Live** (API restarted, `e46`):
- Quezon market 67% (lowers) in 2026-Q2, 83% (raises) in 2026-Q3, 91% (lowers) in 2027-Q1;
- region 2027-Q1 market 91%;
- the new note is shown;
- 142 municipalities banded, news 10 articles, target 2027-Q1.

The production default (E38) is unchanged.

## 9. Files

- **New:** `E50_Trigger_Attribution/runner/e50_attribution_audit.py`, `runs/attribution_audit.json`, this report.
- **Modified:** `backend/scripts/build_record_e46.py`, `backend/data/e46/e46_record.json`, `backend/app/api/v1/insights.py`, `backend/tests/integration/test_e46_corrected_candidate.py`.
- **Commit:** see git log; nothing pushed.
