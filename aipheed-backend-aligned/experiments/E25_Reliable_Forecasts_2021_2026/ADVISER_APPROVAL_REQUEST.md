# Adviser approval request: acceptance criteria and other researcher-declared rules

**For:** the thesis adviser.

**Why this request exists.** Chapter I defines no numeric success threshold and does not define "reliable". The criteria C1–C9 were declared by the researchers in E24. E25 shows, before fitting any model, that some of them cannot be met by **any** model on the authorized data (`docs/REACHABILITY.md`). It therefore proposes alternatives.

**Status of the proposals:**

- They were written into the frozen protocol **before** any E25 model was fitted.
- They are reported beside the original criteria.
- **No result is reported as meeting the goal under a proposed criterion unless you approve it.**

## 1. Why some original criteria are unreachable on this data

**Primary target (approved label S1 = H + 2D > τ), lead 1:**

- **Data:** 8 forecast dates and 40 province rows: 37 HIGH and 3 LOW.
- **Persistence errors:** naive persistence is wrong on 5 rows, one on each of 5 dates.
- **Why a proper scoring rule cannot rescue the comparison with 0/1 persistence:** on a date where persistence is right its loss is 0 under every scoring rule (accuracy, Brier, log score), so a model can only tie there.
- **Best attainable p:** therefore **2^-5 = 0.031**, and it requires a **perfect** model (all 5 changes anticipated, no new error).
- **Other leads:** at leads 3–6 the best attainable p is 0.0625 or larger, so C2 cannot be met at all.
- **C6 and H1–H3:** at every lead there are at most 3 LOW rows, while the E23 evaluability rule needs 5. C6 and the tests of H1–H3 are therefore unreachable regardless of the model.
- **Pooling leads:** pooling leads per date gives 10 dates, 9 of them with a persistence error, so the best attainable p is 0.002. This is the only design with real power (`docs/POWER_SIMULATION.md`: 38–70% for a correctly specified probabilistic forecaster, against 20–50% at lead 1 alone).

## 2. Original and proposed criteria, side by side

All criteria apply to FINAL_T1 = PCF21 on the approved label. Results are from the frozen run `20261014T002026Z` and are development evidence.

| # | Original (E24, unchanged) | Result | Proposed (pending approval) | Result under the proposal |
|---|---|---|---|---|
| 1 | C1: accuracy > 0.75 (lead 1) | **Met** (0.875). **Meaningless:** always-HIGH scores 0.925 and persistence 0.875 on the same rows. | P1: pooled Brier lower than both no-skill references (always-HIGH, training climatology) | **Not met.** Always-HIGH 0.090 beats PCF21 0.122 (per-date pooled Brier). |
| 2 | C2: beats the strongest baseline on accuracy (sign-flip p < 0.05) and not worse on Brier | **Not met.** Ties persistence (0.875 vs 0.875, p = 1.0). | P2: on pooled leads (each date once), Brier better than the strongest baseline by pooled Brier, sign-flip p < 0.05 | **Met on the raw p** (vs persistence: 8 of 10 dates better, p = 0.027). **Not met after Holm** across B1–B6 + B1p (p = 0.082). |
| 3 | C3: balanced accuracy ≥ 0.60 and above the strongest baseline's | **Not met** (0.779 = persistence's) | P3 = C3 | Not met |
| 4 | C4: more dates better than worse, and leave-one-date-out ≥ 0 for every date | **Not met** | P4: the same on pooled Brier | **Met** (8/2; every leave-one-out difference favors PCF21) |
| 5 | C5: correct on more label-change rows than wrong on unchanged rows | **Not met** (0 of 5 changes anticipated) | P5 = C5 | Not met |
| 6 | C6: E23 reliability rule (evaluable with ≥ 5 LOW; AUC bootstrap lower bound > 0.5; Brier better than persistence, p < 0.05) | **Not met; unreachable** (3 LOW rows) | P6: lead reliable iff ≥ 8 dates, Brier below both persistence and calibrated persistence (each p < 0.05, Holm across leads), and \|mean p − mean y\| ≤ 0.10 | **Not met.** Lead 1: p = 0.109 vs persistence; calibration-in-the-large −0.18. |
| 7 | C7: no leakage | **Met** | P7 = C7 | Met |
| 8 | C8: reproducible | **Met** (second run byte-identical) | P8 = C8 | Met |
| 9 | C9: generalizes to unseen quarters | **Not assessable** | P9 = C9 | Not assessable (seal scoring needs authorized outcomes) |

**Under either set, the T1 forecasting goal is NOT met.**

## 3. Other decisions that need your approval

| # | Decision | Proposal |
|---|---|---|
| D1 | Adopt P1–P6 in place of C1–C6 for the thesis? | Approve only together with the statement that always-HIGH, a no-data rule, has the lowest Brier on these quarters |
| D2 | "Reliable lead" and "maximum reliable lead time" (Objective 2-V, SOP Q2, H2), undefined in Chapter I | The E23 rule (C6) or P6. **Under both: none.** |
| D3 | Evaluability (≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW) | Keep (it guards against claims from 2–3 LOW rows) |
| D4 | Primary SWS reading (A: production rounds only) | Keep A. Readings B/C (disputed 2025 rounds) are reported as sensitivity. They make lead 1 evaluable on the label-history set but do not change any verdict. |
| D5 | Label threshold: the training-window median (approved) or a fixed anchor | Keep the approved median. Only 2 of 75 cells change with the origin. Chapter I's "anchored to the FAO SDG 2.1.2 baseline" gives no number. |
| D6 | Whether the exploratory provincial target T2 (D > 0) may be reported as **supporting** evidence for the provincial layer (never as the food-insecurity outcome) | At lead 1, M4_21 meets C1–C8 on 11 examined dates (accuracy 0.764 vs persistence 0.655, p = 0.031; Brier p = 0.003). This is development evidence only. |
| D7 | H4/H5 decision rules (`instruments/DECISION_RULES.md`) | Approve before any DA response is collected |
