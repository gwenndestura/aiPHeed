# Five trigger contributors and the four dimensions of food security: audit

**Scope.** The served thesis-mode dashboard: `AIPHEED_LEAD2_MODEL=thesis`, Chapter I engine `ch1_system`, the model served on branch `aiPHeed/lead2-optimization`.

**Evidence files** (`out/`):
- `contributor_audit_before_fix.txt` / `_after_fix.txt` (95 served province-quarters × 5 groups = 475 group rows);
- `contributor_cases.txt` (six behaviour cases);
- `family_inventory.txt`;
- `ablation_P0H0.json` (family ablations);
- `time_confound_check.txt`.

## 1. The five contributors as implemented

**Execution path:**

| Step | Where | What happens |
|---|---|---|
| 1 | `FINAL_UNIFIED_LGBM/runner/uni_lib.py: UniPrice.shap` | TreeSHAP (`pred_contrib`, log-odds) of the **price-condition LightGBM π_P** for each forecast row |
| 2 | `LEAD2_OPTIMIZATION/runner/export_l2.py` (columns inherited from `export_uni.rows_for`) | SHAP summed per FIRI family into `shap_A1`…`shap_H1` in `backend/data/ch1_engine/rows.csv`. World prices are folded into families (`W_rice*`→A3, `W_cereal`→A1, `W_crude`→A2, `W_urea`→C3). `lead` is dropped. |
| 3 | `backend/app/ml/inference/ch1_system.py: drivers()` | Family SHAP summed into five groups. `other_pct` = share of \|V1\|+\|N1\|+\|H1\| in the total. |
| 4 | `backend/app/services/dashboard.py: explainability()` | `pct` = `_integer_shares(\|group sum\|)`: largest-remainder rounding to **100% over the five groups only**. Direction from the sign. Colour from pct and direction. `status`, `statusNote`, `evidenceNote`. |
| 5 | `explainability_region()` | Sum of \|signed\| over provinces for the share; mean of the signed values for the direction |
| 6 | `frontend/src/components/LeftPanel.tsx` ("What drives this forecast?", "Trigger composition"), `RightAnalyticsPanel.tsx` (factor cards) | Shows `pct`%, label, colour, notes. **`otherPct` is not shown anywhere.** |

**The five groups:**

| Dashboard label | Families (columns) | Source / geography | Kind | Varies by |
|---|---|---|---|---|
| **Market / Prices** | A1 food-price projection (A1_food, A1_gap, A_mom, + world cereal); A2 headline inflation (+ world crude); A3 wholesale rice (+ world rice YoY and 3-month change) | PSA CPI and wholesale rice by **province**; World Bank Pink Sheet (world) | Indirect driver (affordability / supply) | province and quarter |
| **Climate Stress** | C1 El Niño alert (PAGASA, **national**); C2 typhoons within 300 km (IBTrACS, **province**); C3 palay/corn production drop (PSA, **province**; + world urea price) | mixed | Indirect driver (availability shock) | C1 quarter only; C2/C3 province |
| **Fish Kill** | C4 **fisheries production drop** (PSA, province) | province | Indirect driver (availability) | province and quarter |
| **Employment** | E1 unemployment change (PSA LFS, **national**) | national | Indirect driver (access) | quarter only (one value for all provinces) |
| **OFW Remittance** | E2 remittance decline (BSP, **national**) | national | Indirect driver (access) | quarter only |
| *not in the bars* (`otherPct`, not displayed) | V1 poverty and density (static); N1 news (FSSI-v3 and GDELT price news); H1 hunger outlook as a *feature* | province / region | V1 structural; N1 signal; H1 hunger measurement | – |
| *not in the bars at all* | **The hunger condition π_H**, which multiplies π_P into the risk probability | SWS Balance Luzon (**region**) | **Direct** hunger measurement (regional) | quarter |

**What the displayed percentage is.** A group's **relative influence on the price-condition LightGBM's log-odds** for that row, rescaled so the five groups sum to 100%.

**What it is not:**
- not a share of food-insecurity risk;
- not a share of hunger caused by the factor;
- not a weight of a separate index.

It comes from the same served model and forecast instance (verified: same rows and SHAP as the exported model). There are no manual weights.

## 2. Findings, classified

| # | Finding | Evidence | Class | Action |
|---|---|---|---|---|
| F1 | Statuses came from the FIRI v2 record, not the served model. **135/135** "insufficient data: none of this factor's inputs had a published value" statuses were false for the served model (Employment 45, OFW 55, Fish Kill 15, Climate 10, Market 10). | `contributor_audit_before_fix.txt` | **Incorrect implementation** | **Fixed.** Statuses now follow the exported input-availability flags of the served model: 0/475 contradictions. Regression test added. |
| F2 | The bars explain only π_P. The hunger condition, the regional SWS multiplier, appears nowhere, although it accounts for the HIGH/LOW difference in hunger-LOW quarters (accuracy 0.83 → 0.69 without it). Example: Batangas 2025-Q2, π_H 0.99: bars read "Market 100%". | `contributor_cases.txt` case 4; `validation_ablations.json` | **Misleading interpretation** (the title "What drives this forecast?" covers both terms) | **Fixed in the note.** Every province and region note now says the bars are model influence on the price estimate, rescaled to 100%, not shares of hunger, and states the hunger probability left out. Heading text not changed (approved UI). |
| F3 | "100%" excludes V1, N1 and the H1 feature, which hold a mean **22.8%** (max 88.9%) of the attribution. In Batangas/Laguna 2024-Q2 the largest push was poverty (V1, 58–67%), invisible in the bars. | case 3 | Misleading (normalisation hides part of the explanation) | **Fixed in the note:** the hidden share is now stated with its number. Adding a sixth bar would be a UI design change. Not done; recommended. |
| F4 | The region note read "In the risk index (FIRI v2)…" while the region bars pooled the served model's SHAP | code path | Incorrect label | **Fixed** (same note as F2, region scope) |
| F5 | "Employment" reflects a calendar-time confound. E1 is national (16–17 distinct values), Spearman +0.95 with time, within-year AUC 0.35 / 0.76 / 0.17. It holds 17.6% of the mean \|SHAP\| (2nd family). In the 2026-Q4 forecasts **rising** unemployment (+0.9 pts) is shown as **lowering** risk (33–38% of the bars). | `e1_investigation.txt`, case 5 | **Weakly supported / misleading direction** | Not reversed or removed (12-family rule; no evidence of a coding error). Documented. A structural prior (P4/P7) or stronger regularisation reduces its weight; not adopted under the frozen Lead-2 rule. |
| F6 | "Fish Kill" is fed by C4, a **fisheries production drop** (PSA), not fish-kill events | inventory | Misleading label | Documented. The approved label is not changed. |
| F7 | "Climate Stress" contains C3 (palay/corn production) and world urea price, which are supply and input-cost signals, not climate. In 2024-Q1 the whole +0.40 push was C3 production drops (all five provinces above one tree split, hence identical). | case 2 | Reasonable but indirectly measured; label broader than its content | Documented |
| F8 | C1 El Niño, C2 typhoons and E2 remittances have **exactly zero** influence; the model never splits on them. Their bars are always 0% and "no effect". | `ablation_P0H0.json` | Redundant / weakly supported for this target | Kept (12-family rule); reported honestly |
| F9 | Market dominates. It is the largest bar in 73/95 rows; A1 alone has 42% of the \|SHAP\|. A1, A2 and A3 overlap: removing A2 or A3 alone changes nothing significant, while removing A1 costs 0.13 accuracy at Lead 1. | ablation | Correct: this is what the model uses, not double counting by the display | – |
| F10 | Groups push in **opposite directions** in 20/95 rows; the display handles this (sign → colour, status) | case 6 | Correct | – |
| F11 | Within-group sums are signed before \|·\|, so a group with opposing families can show a small bar | code | Correct by definition (net push); disclosed in the glossary as "pushes risk up or pulls it down" | – |

**Predictive contribution (family ablation, identical rows, Holm):**
- **Significant:** only A1 (and C4 at Lead 3).
- **Hurts at Lead 3:** C3 (Holm < .001).
- **Suggestive only:** news at Lead 1 (raw p = .026, Holm .86; shuffled-news permutation p = .05).
- **Large display share, little predictive value:** a large bar does not mean predictive value. E1 shows big bars but its removal is not significant.

## 3. The four dimensions of food security

**Definitions.** FAO, *Food Security*, Policy Brief Issue 2, June 2006, citing the World Food Summit 1996: food security exists when all people, at all times, have physical and economic access to sufficient, safe and nutritious food.

| Dimension | FAO definition |
|---|---|
| Availability | Sufficient quantities of food of appropriate quality, from domestic production or imports |
| Access | Adequate resources (entitlements) to acquire appropriate foods |
| Utilization | Utilization through **adequate diet, clean water, sanitation and health care** |
| Stability | Access at all times, without risk from sudden shocks or cyclical events |

**Coverage matrix:**

| Dimension | Families that support it, and the mechanism | Measurement | Verdict |
|---|---|---|---|
| **Availability** | C3 palay/corn and C4 fisheries production drops (provincial supply); A3 wholesale rice price and world rice/cereal prices (market supply and import cost); C1/C2 (shocks to production) | Provincial production and prices: **indirect** (no food stock, supply or distribution data) | **Indirect proxy** |
| **Access** (economic) | A1/A2 food and headline inflation (affordability); E1 unemployment, E2 remittances (income; national only); V1 poverty (static 2021); **SWS hunger** (the experience of not having enough to eat, an access-failure outcome; regional) | Prices provincial; income national; poverty static; hunger regional | **Partly measured.** Hunger is a direct but regional outcome; drivers are indirect. Household income and expenditure are not integrated. |
| **Utilization** | **None.** No diet quality, nutrition (stunting, wasting), water, sanitation or health input. | – | **Not measured** |
| **Stability** | Quarterly YoY changes and shock events (C1, C2, price YoY); the forecast itself is about the coming quarters | Time-varying drivers only; no measure of the stability of access | **Indirect** (and C1, C2 have no influence on the model) |

**Data that exists but is not integrated:**

| Source | Status | What it could add | Limits |
|---|---|---|---|
| FNRI FIES (Food Insecurity Experience Scale) | In the repository (`E87_Outcome_Gap`, `e22`) | An access-outcome check | 2021: Batangas 29.7, Cavite 31.7, Lucena 26.2; 2023/2025: regional only |
| PSA Family Income and Expenditure Survey 2023 PUF | Read 10-27 | Provincial food share of spending, bottom-30% shares (all 5 provinces + Lucena) | One year; indirect access evidence |
| Utilization data | Not in the repository | Diet quality, nutrition, WASH | Would need FNRI ENNS/NNS provincial tables, PSA NDHS (regional) or CBMS 2024 LGU WASH/food items. Availability for 2021+ at provincial level is **unverified** and requires data requests. |

**What can only be validated with more data.** Utilization at any level, and access/hunger at provincial or LGU level (FNRI provincial FIES; CBMS 2024).

## 4. Verdicts

**The five contributors: partially supported, with indirect or incomplete measurement.**
- **Supported:** they are computed correctly from the served model's own SHAP for the right forecast instance (additive, no manual weights, no separate score), and they respond to the actual inputs (cases 1–6).
- **Incorrect, now fixed:** the statuses (F1, F4).
- **Explained in the notes:** the interpretation as drivers of the *risk* (F2, F3).
- **Remaining misleading elements, documented and not changed under the no-UI-change rule:** the "Fish Kill" and "Climate Stress" labels, and the Employment direction driven by a time confound (F5–F7).
- **Correct reading:** relative model influence on the food-price part, not percentages of food insecurity.

**The four dimensions: not adequately measured.**

| Dimension | Coverage |
|---|---|
| Availability | indirect |
| Access | partly measured; only regionally as an outcome |
| Stability | indirect |
| **Utilization** | **not measured at all** |

The dashboard should not claim to cover all four dimensions. A credible five-trigger display does not mean the model has validated food-insecurity forecasting.

## 5. Recommendations (need your approval; UI text or design)

1. Rename the heading to "What moves the food-price part of this forecast" and add the hidden share and the hunger term as their own rows.
2. Rename "Fish Kill" to "Fisheries production" and "Climate Stress" to "Climate and crop production".
3. If the thesis or a later dashboard lists the FAO dimensions, state "Utilization: not measured". The dashboard on this branch makes no dimension claim; the E71/E72 FAO-dimension breakdown is on another branch.
