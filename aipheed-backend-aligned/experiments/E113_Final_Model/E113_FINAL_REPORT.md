# E113 Final report: answers to the twelve questions

**Status.** Development evidence: every quarter scored was seen in E109–E112.
- Rules frozen before scoring: `PROTOCOL_E113.md` (sha `bb255afe…`) and `ADDENDUM_1.md` (sha `24e5326b…`).
- Leakage audit passed: 560 forecasts unchanged under future-data perturbation.
- Seals: A `b53e8793…`, B `a86bcd49…`.
- Rerun everything with one command: `python runner/run_e113.py all`.

| # | Question | E113 answer | Change from E112 |
|---|---|---|---|
| 1 | Root causes resolved? | **Partly.** Resolved or partly resolved: more evaluable quarters (4-area panel), shrinkage to persistence, an explicit survey-break model, dense validated news composites, CPI aligned by release date, calibrated bands at Lead 1. **Not resolvable with these data:** the few, noisy quarters; no local outcome; no bridging round for the 2025 change; no unseen confirmation. See `E113_ROOT_CAUSE_AUDIT.md`. | Power raised from 9 to 14 quarters at Lead 1, 5 to 9 at Lead 4. Break and CPI now addressed explicitly. |
| 2 | Final methodology; why simple? | **The latest published SWS reading, with an honest 80% error band and its true horizon.** The research family "start from the latest reading and adjust it by a small, regularised amount from news, price and mean-reversion signals" was pre-registered and tested. It did not earn its adjustment, so the adjustment is zero. One input, one rule, one band. | Same adopted rule. Bands are now conformal and calibration-checked; the shrinkage family is tested and documented. |
| 3 | News contribution; measurable? | **Measurable, partly validated, no forecast contribution.** Disaster news tracks typhoons (ρ = 0.81). The direction of price news leads food-inflation changes by about two quarters (GDELT ρ = 0.70, Holm p = .016). Every news ablation, at every lead, area and regime: Holm p = 1. Real news does no better than shuffled news (p = .63). The agri-supply link did **not** replicate in GDELT out of sample (Holm p = .65). | Price news newly validated as a leading CPI signal; agri-supply replication failed |
| 4 | Forecasts actual food insecurity? | **Yes, regionally.** The outcome is SWS experienced hunger in four areas (Balance Luzon primary). CPI and poverty are not used as outcomes. **No** provincial or municipal forecast. | Unchanged |
| 5 | Beats the baselines? | **No candidate beats persistence** (all Holm p = 1.0). Persistence beats linear regression, PSA-only and NLP-only at Lead 1. The Model Confidence Set keeps almost every model at Leads 1–5. The ETS (local-level) baseline has the lowest MASE at Leads 2–3 (p = .062 at Lead 2), but it is not significant and not pre-registered as a candidate. | Same conclusion on more data, tested more strictly (MCS, wider baseline set) |
| 6 | Generalizes across quarters? | **No skill to generalize.** Per regime, shrinkage variants help slightly in falling quarters (SH-MRN −0.21 scaled at Lead 1) and hurt in surges (+0.89). Mean reversion breaks after 2025 at long leads. Persistence's own errors are largest in the 2024 surge (8–10 points). | Regime analysis now covers 4 areas and 6 leads |
| 7 | Anticipates surges? | **No.** 9 surge events at Lead 1 (rises beyond survey noise). No model meets the pre-registered alert rule (≥ 10 events, precision and recall ≥ .5, Brier better than climatology and persistence). The best record is SH-MRN at Lead 4: 4 of 10 surges caught, precision .80, recall .40. | Formal surge definition and Brier scoring added; same answer |
| 8 | Families that add value? | **None.** News (4 composites), CPI and rice, and mean reversion each fail their families (Holm p = 1). Real CPI is worse than shuffled CPI (p = .97). E112 found the same for all 12 FIRI families. | Confirmed with composites and the panel |
| 9 | Maximum reliable lead? | **None established** (R1–R4, Holm within lead, fixed sequence). The persistence band is calibrated at Lead 1 only (coverage 0.75; 0.54–0.73 beyond). | Unchanged, now with a calibration horizon of 1 |
| 10 | Objectives status | Obj 1 **Partial**; Obj 2 I–IV **Partial**; Obj 2 V **Not achieved**; Obj 3 **Not achieved**; Obj 4 **Achieved** (the comparison; the model is not superior); Obj 5 **Not achieved in E113** (needs the DA evaluation). See `E113_OBJECTIVES_ASSESSMENT.md`. | Obj 1 strengthened (price-news validation); otherwise unchanged |
| 11 | What DA IV-A can use | See "What this model can and cannot be trusted for" below and `E113_FINAL_MODEL_CARD.md` | Adds a calibrated Lead-1 band and the re-issue-on-release rule (seal B) |
| 12 | Missing evidence | (1) SWS rounds from 2026-Q4 to score seals A and B, about 8 quarters for a Lead-1 test. (2) The adviser's decision on pre-2021 SWS history. (3) CBMS 2024 LGU and FNRI provincial food-insecurity data. (4) A bridging estimate for the 2025 SWS design change. (5) National and rice CPI with PSA release dates. | Items 2, 4 and 5 newly identified |

## What this model can and cannot be trusted for

**It can be trusted for:**
- Stating where regional hunger stood at the latest SWS reading, and how far that reading is from the target quarter (true horizon).
- A Lead-1 range that contained the outcome in 75% of past cases (aimed at 80%; panel), and in 93% for Balance Luzon.
- Telling DA IV-A, honestly, that the next reading may differ by about ±7 points without any detectable warning.
- Context panels: disaster news (validated against typhoons) and price-news direction (an early sign of food-inflation upturns).

**It cannot be trusted for:**
- Predicting whether hunger will rise or fall: no method beat "no change".
- Early warning of hunger surges.
- Any lead beyond one quarter as a calibrated range.
- Any provincial, city or municipal food-insecurity level.
- Treating news or food prices as drivers of hunger forecasts.

## Appendix: complex research models

- The 12-family LightGBM (E112) was worse than persistence at every lead. It is cited, not re-fitted.
- The shrinkage family's full results are in `out/results.json`.
- ETS (local level) is the one exploratory option worth confirming prospectively at Leads 2–3. It is sealed in A and B with every other model.
