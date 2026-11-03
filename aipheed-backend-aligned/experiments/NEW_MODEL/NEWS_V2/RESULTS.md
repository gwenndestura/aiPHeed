# NEWS_V2: results (EXPLORATORY)

**Plan:** `PLAN.md`, SHA-256 `0705ab68…5b60`, fixed before any fit. Not committed (no authorization).

**Evidence status:**
- development evidence;
- two candidates, designed after Phase 2 showed where REF+news loses;
- any gain must be confirmed on sealed 2027+ forecasts.

**Checks:**
- **Leakage:** randomizing all future news leaves every anomaly unchanged (5 repetitions).
- **Machinery:** the refit code reproduces the stored REF+news at Leads 1–8: 904 of 904 rows, the same configuration
  everywhere, max |Δp| = 1.1e-16.

## Decision (fixed rule, PLAN §3)

**Neither candidate formally "improves REF+news" at both leads.**
- Their **accuracy** rises (C-b from 0.758 to **0.790** at both leads).
- The Brier gain is significant at Lead 2 (Holm p 0.060) but **not at Lead 1** (Holm p 0.348).

**Neither adds value over REF** (no news): Holm p 0.71–0.73. REF+news is unchanged under the rule.

## Per lead (62 labelled quarters, 2010-Q1..2026-Q3)

| | REF | REF+news | **C-a** (8 anomaly columns) | **C-b** (FSSI anomaly only) |
|---|---|---|---|---|
| **Lead 1** accuracy | 0.790 | 0.758 | 0.774 | **0.790** |
| Balanced accuracy | 0.717 | 0.693 | 0.705 | 0.717 |
| Precision / recall | 0.812 / 0.907 | 0.804 / 0.860 | 0.809 / 0.884 | 0.812 / 0.907 |
| F1 | 0.857 | 0.831 | 0.844 | 0.857 |
| AUC | 0.702 | 0.688 | 0.702 | 0.702 |
| Brier | 0.1875 | 0.1952 | 0.1885 | **0.1874** |
| Rules failed | R7 | R3, R5, R7 | R5, R7 | **R7** |
| News-era accuracy (20 q) | 0.850 | 0.750 | 0.800 | 0.850 |
| **Lead 2** accuracy | 0.790 | 0.758 | 0.774 | **0.790** |
| Balanced accuracy | 0.717 | 0.693 | 0.705 | 0.717 |
| F1 | 0.857 | 0.831 | 0.844 | 0.857 |
| AUC | 0.704 | 0.674 | 0.704 | 0.704 |
| Brier | 0.1838 | 0.1988 | 0.1848 | **0.1837** |
| Rules failed | R7 | R3, R5, R7 | R7 | **R7** |
| News-era accuracy (19 q) | 0.842 | 0.737 | 0.789 | 0.842 |

**News share of SHAP in the news era:** C-a 2.8% (L1) / 3.0% (L2), C-b 0.1% / 0.1% (REF+news: about 16%).

**Brier difference (candidate − comparator), Holm across the two candidates:**

| Comparator | Lead 1 | Lead 2 |
|---|---|---|
| vs REF+news | C-a −0.0067, C-b −0.0078 (both Holm p 0.348) | C-a −0.0141, C-b −0.0151 (both Holm p **0.060**) |
| vs REF | C-a +0.0010, C-b −0.0001 (Holm p 0.726) | C-a +0.0010, C-b −0.0001 (Holm p 0.709) |

**Algorithm 3 (75% rule).** The Maximum Reliable Lead Time is **2 for every model**. Lead 3 accuracy: REF 0.726,
REF+news 0.694, C-a 0.710, C-b 0.726.

## What this shows

1. **The accuracy loss of REF+news is a construction problem, and it is fixable.**
   - Replacing the raw news levels and shares by anomalies against their own past removes most of the news-era loss
     (C-a: 0.75 → 0.80 at Lead 1).
   - Reducing news to the FSSI anomaly removes all of it (C-b: 0.85, the same as REF).
2. **But the fix works by switching news off, not by making it informative.**
   - C-b's news column carries 0.1% of SHAP, and its forecasts equal REF's to within 0.0001 Brier.
   - C-a keeps news at about 3% and is slightly *worse* than REF.
   - **No construction tested makes news add measurable value** (consistent with E85, OPTION_1 and OLD_NEWS).
3. **R1–R7.** C-b fails only R7 (as REF does). C-a fails R5 and R7 at Lead 1 and R7 at Lead 2. Neither passes at both
   leads.

## Options for you (no change has been made)

| Option | What it means |
|---|---|
| **Adopt C-b as the main model** | Thesis-aligned: it keeps the NLP component (the paper's FSSI, bias-corrected, as an anomaly), and it recovers REF's accuracy (0.790 at both leads). It must be stated honestly that the NLP input carries about 0.1% of influence and does not improve the forecast. It does not formally pass the fixed rule (Lead 1 Brier not significant), so adopting it is **your and your adviser's decision**, recorded as such, with a revised prospective protocol sealed before any 2027 outcome |
| Keep REF+news | Unchanged, accuracy 0.758 |
| Adopt REF (no news) | 0.790, simplest; the NLP objective is then answered as "evaluated, no predictive value" |
