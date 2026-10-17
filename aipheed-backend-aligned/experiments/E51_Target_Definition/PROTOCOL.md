# E51 protocol: target-label audit and defensible Lead-2 targets (frozen before any E51 model score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, from 8def3a3.
**Freeze:** SHA-256 (LF) in `runner/PROTOCOL_SHA256.txt`, committed with code and tests before any model is scored on any candidate target. Run once, then a byte-identical repeat.

## 0. Evidence status and what was looked at before writing this

**Every 2021–2026 quarter has been examined (E36–E50). No E51 result is on unseen quarters.**

**Label audit, done before this protocol** (no model scores):
- Thesis Eq. 3 S1 = H + 2D. D has mean zero across the five provinces each quarter, so the quarterly mean of S1 is H exactly.
- S1 − 2D equals the published SWS H in all 19 quarters, so alignment is exact.
- 70% of S1's variance is between quarters (regional hunger) and 30% within quarters (provincial price deviation).
- Mean S1 was about 11 in 2021–2023 and 20–21 in 2024–2026.
- The global median, 15.47, gives HIGH in 7/50 rows in 2021–2023 and 40/45 in 2024–2026.
- **Diagnosis:** a real level shift in SWS hunger, combined with one threshold applied across it. It is not a calculation defect.

## 1. Candidate targets (fixed now)

| ID | Definition | Meaning of HIGH | Indicators | Needs SWS? |
|---|---|---|---|---|
| **EQ3-G** | S1 > the median of all 2021–2026 province-quarters (thesis text) | composite stress above the whole-period median | SWS H + provincial D | yes |
| **EQ3-T** | S1 > the median S1 of labelled quarters posted before the origin (E38) | above the recent past | same | yes |
| **T43** | H > 11.3 AND (food YoY > the province's 2021–22 P60 OR food − headline > P60) (E43/E46) | concurrent elevated hunger and provincial price stress | SWS H; PSA food and headline CPI | yes |
| **PS** | food YoY > the province's 2021–22 P60 OR food − headline > P60 | provincial food-price pressure (not hunger) | PSA CPI only | no |
| **RQ** | S1(p,q) > the median S1 of the five provinces in the same quarter (equivalently D > the within-quarter median D): 2 of 5 HIGH per quarter | relatively higher composite stress than the other provinces that quarter (relative priority, not absolute risk) | thesis Eq. 3 components | no (H cancels) |
| **YW** | S1(p,q) > S1(p,q−4) | composite stress worse than a year earlier | SWS H + D | yes, both quarters |

**None of these is verified household food insecurity.** All are exploratory proxies. EQ3-G/EQ3-T are the thesis's label; the others need adviser approval.

## 2. Defensibility criteria (fixed now; they do not use any model score)

| Criterion | Requirement |
|---|---|
| **C1 relevance** | expresses the thesis composite (SWS hunger + provincial CPI deviation), or a component of it the dashboard reports separately |
| **C2 provincial content** | ≥ 25% of the label's variance lies within quarters (the label distinguishes provinces) |
| **C3 balance in the recent period** | both classes ≥ 25% of 2024–2026 rows |
| **C4 as-of computability** | the label of a past quarter can be computed with no information from after that quarter's publication |
| **C5 sample** | ≥ 8 eligible Lead-2 evaluation quarters |

**The most defensible target** is the one meeting all five. If several do, C1 decides, then C5. If none does, the closest is reported with the failing criterion named.

## 3. Arms per target (Lead-2; issue 00:00 day 1 of quarter t+1; E38 evaluation machinery)

| Arm | Description |
|---|---|
| **LGBM** (best justified LightGBM) | E38's procedure unchanged: COMB/COMPACT/COMB_T5 × grid pool, nested selection on prior dates, prior shift, inner threshold. Its labels (training, `y_last`, prior rate, evaluation) are replaced by the target's. For EQ3-T this is E38 itself. |
| **LR** (simple statistical baseline) | logistic regression (E36 `lr_predict`) on the COMPACT inputs with the target's `y_last`; decision 0.5 |
| **PERSIST** | the latest label of that target available at the origin |
| **HIGH / LOW** | always-HIGH / always-LOW |
| **E46** | I7 for T43; I7's own P(price signal) ≥ 0.5 for PS. Rows from 2024-Q2 on only. |

**Rules:**
- **Evaluation dates:** E38's `eval_dates` rule applied to each target's labels (target labelled, ≥ 10 training rows, both classes).
- **Training rows:** E38's rule (target quarters whose SWS rounds were posted before the origin). This also applies to the CPI-only targets, a documented limitation.
- **Within a target, arms are compared on identical rows.** Accuracies are not compared across targets.

## 4. Metrics and reporting

- Accuracy (date-cluster CI), balanced accuracy, recalls, precision, F1, Brier, AUC, confusion matrix, share of HIGH calls, by quarter.
- The number of independent quarters and of rows.
- Temporal prevalence of each target by year.

## 5. Candidate status

- **Accepted for development:** an arm meets the development target on a target only if its accuracy ≥ 0.75, balanced accuracy ≥ 0.70 with both recalls ≥ 0.60, and its Brier score beats persistence, always-HIGH and always-LOW on identical rows.
- **Not accepted:** historical results remain development evidence, and acceptance stays prospective.
- **No serving change:** the production default and every frozen forecast are unchanged.

## 6. Reproductions (section 6 of the task)

From committed predictions:
- E36 lead 1: 53/65, AUC 0.850; persistence and always-HIGH as in E36's run;
- E38 lead 2: 39/55;
- E46 I7: 0.800 on 35 rows.
