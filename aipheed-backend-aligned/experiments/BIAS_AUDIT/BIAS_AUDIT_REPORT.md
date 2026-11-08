# Bias, trigger-composition and overfitting audit of the served aiPHeed model

**Branch:** `aiPHeed/bias-audit`, from `aiPHeed/lead2-one-model`. Not merged; not deployed. The served model is unchanged.

**Model audited.** **P0H4**, served from `backend/data/ch1_engine/` (export `LEAD2_OPTIMIZATION/runner/export_l2.py`, seal `a498b5ef`):

  P(HIGH) = π_H4 × π_P

| Term | Definition |
|---|---|
| π_P | **One** LightGBM, refitted at each issue date on the stacked rows of every lead (all 12 FIRI v2 families + lead + World Bank prices), trained on the provincial price condition |
| π_H4 | A closed-form probability that Balance Luzon hunger exceeds 11.3%, from the latest SWS reading |
| Decision | HIGH at 0.50 |

**Evaluation data.** Walk-forward over issue dates 2023-01-01..2026-07-01:
- Lead 1: 70 rows, 14 target quarters (2023-Q1..2026-Q3), 17 HIGH.
- Lead 2: 65 rows, 13 target quarters (2023-Q2..2026-Q3), 17 HIGH.

**Independence.** The hunger part of the outcome is **one regional value per quarter**. Lead 1 has 14 independent hunger outcomes, not 70; Lead 2 has 13. All uncertainty intervals are cluster bootstraps over target quarters.

**Evidence status.**
- **Tuning:** hyperparameters are chosen inside each issue date's training window only.
- **Design:** model design decisions (protocols E107–LEAD2) were made after examining these same quarters.
- **Consequence:** **no untouched test period exists.** Every result is development evidence. The first untouched outcome is SWS 2026-Q4 (about January 2027).

**Verdict:** see §1 and §12. "No problem detected" below means only that the stated test found none, not that the model is unbiased.

---

## 1. Overall verdict

| Question | Finding |
|---|---|
| Is the trigger composition correct? | **The arithmetic is correct**: additive TreeSHAP of the price LightGBM, summed by group, normalised to 100%. **Its earlier labelling was misleading**, and three defects were confirmed and fixed (§11). |
| What does it explain? | Even after the fixes, the composition explains **only the price part** of the risk. It shows **relative model influence**, not causes of food insecurity. |
| Predictive bias | **Confirmed underperformance on new HIGH onsets:** Lead 2 catches 0 of 10; Lead 1 catches 4 of 10. Causes: missing early-warning information and delayed SWS publication (§5b). **Possible calibration bias:** over-prediction for Rizal and for 2025–2026 (§8). |
| Overfitting | **Not detected at Lead 1** under the tests run (thirds, leave-one-quarter-out, chronological blocks). **Cannot be excluded**: no untouched period, and the design was informed by these quarters. **Lead 2+ does not generalise** (fails the reliability rule). |

---

## 2. Exact formula of the displayed composition (code-level)

| Step | Code | Calculation |
|---|---|---|
| 1 | `uni_lib.UniPrice.shap` → LightGBM `pred_contrib=True` | Per-row TreeSHAP contributions φ_j in **log-odds** of the price-condition model π_P, for the forecast row (province, issue date, target quarter) |
| 2 | `export_uni.rows_for` (used by `export_l2.py`) | Family SHAP s_f = Σ_{j ∈ f} φ_j. World-price columns are folded into families (`W_rice*`→A3, `W_cereal`→A1, `W_crude`→A2, `W_urea`→C3). `lead` is excluded. |
| 3 | `ch1_system.drivers` | Group value g = Σ_{f ∈ group} s_f, **signed**. Groups: market {A1, A2, A3}, climate {C1, C2, C3}, fish_kill {C4}, employment {E1}, ofw_remittance {E2}. `other_pct` = 100·(\|s_V1\|+\|s_N1\|+\|s_H1\|)/Σ_f\|s_f\| |
| 4 | `dashboard.explainability` → `_integer_shares` | pct_g = largest-remainder rounding of 100·\|g\| / Σ_{5 groups}\|g\|. The direction comes from sign(g): "increases_risk" or "protective". **Negative contributions are not discarded**: they enter by magnitude and are shown as protective (green). |
| 5 | `dashboard.explainability_region` | pct from Σ_provinces \|g\|; the direction from the mean of the signed g |

**What it measures.** How much each group moved *this* forecast's price-condition log-odds away from the model's base value, relative to the other four groups (Lundberg & Lee 2017).

**What it cannot establish:**
- causal effect;
- the share of food insecurity caused by a factor;
- predictive value on new data;
- the hunger multiplier π_H4.

The hunger multiplier carries 5–20% of the variance of log P(HIGH) (`LEAD2_OPTIMIZATION/out/validation_ablations.json`, contributor audit).

**Group size.**

| Group | Columns |
|---|---|
| Market | 9 (A1_food, A1_gap, A_mom, A2, A3, 4 world prices) |
| Climate | 4 |
| Fish kill, employment, remittance | 1 each |

Summing more columns can raise a group's total; §5 tests whether this drives Market's share.

---

## 3. The 12 families: source, resolution, timing, model use, display

**Sources:** `LEAD2_OPTIMIZATION/out/family_inventory.txt`. **Missing share** is measured on Lead-2 rows.

| Family | Source | Geography | Available at issue | Missing | Model use | Displayed in |
|---|---|---|---|---|---|---|
| A1 food-price projection | PSA CPI (OpenSTAT 0012M4ACP22) | province | months ≤ month 2 of t | 9% | π_P (strongest) | Market |
| A2 headline inflation | PSA CPI | province | months 1–2 of t | 0% | π_P | Market |
| A3 wholesale rice | PSA wholesale prices | province | quarter t−1 | 27% | π_P | Market |
| V1 poverty and density | PSA SAE 2021, POPCEN 2024 | province (static) | treated as static; **published 2025** (timing exception) | 0% | π_P | hidden "other" share |
| C1 El Niño alert | PAGASA ENSO alert system | **national** | items before O(t) | 0% | π_P (**never split on**) | Climate |
| C2 typhoons within 300 km | IBTrACS (NOAA NCEI) | province | quarter t | 4% | π_P (never split on) | Climate |
| C3 palay/corn production drop | PSA | province | quarter t−1 | 22% | π_P | Climate |
| C4 fisheries production drop | PSA | province | quarter t−1 | 22% | π_P | "Fish Kill" |
| E1 unemployment change | PSA LFS | **national** | quarter t−1 | 22% | π_P | Employment |
| E2 remittance decline | BSP | **national** | quarter t−1 | 30% | π_P (**never split on**) | OFW Remittance |
| N1 news (FSSI-v3, GDELT price news) | RSS + XLM-RoBERTa; GDELT | province | headlines before O(t) | **83%** | π_P | hidden "other" share |
| **H1 regional hunger** | SWS Balance Luzon (non-commissioned rounds) | **region** (one value for all 5 provinces) | rounds published before O(t) | 9% | **(a)** the multiplier π_H4 (closed form); **(b)** the H1 feature inside π_P | (b) in the hidden "other" share; (a) **not in the bars**, now stated in every driver note (§11) |

**H1 is not double-counted.** Its feature SHAP is in `other_pct` only. The multiplier is outside the SHAP decomposition and is named in the note.

**All 12 families are in the pipeline, but not all are used.** C1, C2 and E2 receive zero SHAP and zero ablation effect: the trees never split on them (§5).

**The user's grouping differs from the implementation.** Your list (Climate = C1–C4; Employment and remittances; News; Poverty) is not what the dashboard shows. The implementation has Climate = C1–C3, Fish Kill = C4, separate Employment and OFW groups, and News, Poverty and the H1 feature only in the undisplayed `otherPct`. Both groupings were tested (§5).

---

## 4. Bias categories (separate verdicts)

| Category | Evidence | Verdict |
|---|---|---|
| **A. Trigger-composition bias** | Market holds 68% of bar share (sd 31 points across quarters). Its dominance survives held-out ablation and permutation (§5), so it is **not** a display artefact. But the display (i) dropped V1, N1 and the H1 feature (mean 22.8%, max 88.9% of attribution) from the 100%; (ii) omitted the hunger multiplier; (iii) took statuses from another model. Employment's SHAP share (15.8%) exceeds its held-out value (§5). | **Confirmed defects (fixed); possible over-display of Employment** |
| **B. Predictive bias** | Onsets missed (Lead 2 0/10, Lead 1 4/10). Over-prediction: Rizal +0.20 (90% CI 0.14–0.26, Lead 2), 2025–26 +0.14 to +0.17, adult-base period +0.16 (0.07–0.24). | **Confirmed underperformance on onsets; possible calibration bias by province and period** |
| **C. Data and measurement bias** | Regional hunger reused for 5 provinces; national E1, E2, C1 shared by all provinces and LGUs; V1 static and published after early origins; news covers 17% of rows; SWS design change 2025-Q2; SWS n = 600 BL (±4%) or 300 alternating vs a 0.0–2.6-point distance to the 11.3 line in borderline quarters | **Confirmed limitations** (data, not code) |
| **D. Model selection and overfitting** | Hyperparameters in-window. Design informed by the same quarters (E107–LEAD2). Lead 1 stable (thirds 0.88 / 0.76 / 0.90; leave-one-quarter-out min 0.83); Lead 2 not. | **Possible concern** (no untouched test); not detected at Lead 1 by the tests run |
| **E. Interpretation bias** | Before the fix: "What drives this forecast?", the glossary's "how each input contributed… adding up to 100%", and municipal values called a "likelihood of food insecurity". SHAP is not causal (Lundberg & Lee 2017). | **Confirmed (fixed: text)** |
| **F. Target bias** | T43c = regional hunger AND provincial price condition. It equals the price condition in 80–92% of evaluation rows; 8 of 17 Lead-2 HIGH rows sit within 0.5 points of a price threshold. The price model's label is built from the same CPI series as A1. | **Confirmed structural advantage for the market group** (by design, not an error) |

---

## 5. Group-level experiments (identical rows; refit on training data only; `out/group_ablation.json`, `out/permutation_importance.json`)

### Held-out group ablation

**Method.** Retrain π_P without the group at every issue date, then multiply by π_H4.

**Metric.** Brier of P(HIGH). Positive difference = the model is *better without* the group. 90% cluster-bootstrap CI; Holm-adjusted across 10 groups × 2 leads.

**Full model:** Lead 1 accuracy 0.843, Brier 0.132; Lead 2 accuracy 0.769, Brier 0.194.

| Without | Lead 1: acc, TP/FP, Brier Δ [90% CI], Holm p | Lead 2: acc, TP/FP, Brier Δ [90% CI], Holm p |
|---|---|---|
| **Market (A1–A3 + world prices)** | 0.729, 6/8, **−0.052 [−0.089, −0.022], p < .001** | 0.692, 1/4, −0.032 [−0.055, −0.009], p .43 |
| Climate (C1–C3) | 0.857, 11/4, +0.007 [−0.000, +0.017], p 1.0 | 0.769, 6/4, +0.004 [+0.001, +0.007], p .51 |
| Fish kill (C4) | 0.829, 10/5, −0.003, p 1.0 | 0.785, 6/3, +0.001, p 1.0 |
| Employment (E1) | 0.829, 11/6, −0.005 [−0.013, −0.001], p .71 | 0.769, 6/4, −0.002, p 1.0 |
| OFW remittance (E2) | 0.843, 11/5, 0.000, p 1.0 | 0.769, 6/4, 0.000, p 1.0 |
| News (N1) | 0.800, 8/5, −0.011 [−0.024, −0.002], p .43 | 0.785, 6/3, +0.004, p 1.0 |
| Poverty (V1) | 0.871, 11/3, +0.003, p 1.0 | 0.785, 7/4, −0.002, p 1.0 |
| H1 feature (diagnostic; the multiplier kept) | 0.871, 13/5, +0.007, p 1.0 | 0.754, 7/6, −0.008, p 1.0 |
| Climate C1–C4 (your grouping) | 0.843, 10/4, +0.005, p 1.0 | 0.785, 6/3, +0.005 [+0.001, +0.010], p .98 |
| Employment + remittances E1–E2 (your grouping) | 0.829, 11/6, −0.007 [−0.015, −0.001], p .42 | 0.785, 6/3, −0.003, p 1.0 |

### Held-out permutation importance

**Method.** The trained per-origin models are kept. A group's values are shuffled **across issue dates within each province**, 20 times (seed 2031). This follows the held-out recommendation of the scikit-learn guide.

**Metric.** Mean Brier increase ± sd; the share of shuffles that are worse.

| Group | Lead 1 | Lead 2 |
|---|---|---|
| **Market** | **+0.069 ± 0.025, 100% worse** | **+0.032 ± 0.019, 95% worse** |
| Employment | +0.0024 ± 0.0020, 90% | +0.0016 ± 0.0014, 65% |
| Fish kill | +0.0008, 60% | −0.0017, 15% |
| Climate | −0.0002, 30% | +0.0003, 40% |
| News | −0.0002, 20% | +0.0003, 70% |
| H1 feature | −0.0022, 0% | +0.0029, 100% |
| OFW remittance, poverty | 0 (unused, or static per province, so not testable by within-province shuffling) | 0 |

### SHAP composition on the 95 served rows (`out/composition.json`)

**Mean bar share:**

| Group | Share |
|---|---|
| Market | 68.1% |
| Employment | 15.8% |
| Fish kill | 10.0% |
| Climate | 6.0% |
| OFW | 0.03% |

**Stability across target quarters** (sd of the share): Market 31.0, Employment 24.4, Fish kill 19.8, Climate 14.7 points. The top group changes 4 times across quarters.

### What the three methods agree on

| Finding | Evidence |
|---|---|
| **Market dominance is supported by held-out evidence**, not produced by the display | SHAP, ablation and permutation all rank Market first |
| **Group size does not explain it** | In the family ablation (LEAD2_OPTIMIZATION) only **A1** has a Holm-significant effect; A2 or A3 alone do not. Market columns are only moderately correlated (Spearman A1_food–A1_gap 0.72, world cereal–crude 0.77, others ≤ 0.55). |
| **Employment is over-displayed** relative to its held-out value | 15.8% of bars vs +0.002 Brier on permutation, not Holm-significant. E1 is a calendar-time confound: national, Spearman +0.95 with time, within-year AUC 0.35 / 0.76 / 0.17. |
| **Fish kill (C4) is over-displayed** | 10% of bars, with no held-out effect |
| **Climate carries no predictive information here, and may slightly hurt** | Lead-2 Brier is better without it (CI excludes 0; not Holm-significant). C1 and C2 are never split on. |
| **News: no demonstrated contribution** | Ablation suggests a Lead-1 benefit (raw CI excludes 0, Holm .43), but permutation shows the trained model barely uses it (worse in 20% of shuffles); 83% of rows lack news |
| **Poverty (V1) acts as a province identifier** | Static per province; SHAP variance between provinces 0.040 vs within 0.050. A +0.05 change moves π_P by up to 0.36 and flips 2 classes (§6). |

### Does Market mask other useful signals? (`out/conditional_ablation.json`)

**Method.** Each group is ablated inside a model retrained **without Market**.

**No-market model.** Lead 1 accuracy 0.729, Brier 0.185; Lead 2 0.692, 0.226.

| Group | Brier change when also removed, Lead 1 / Lead 2 [90% CI] |
|---|---|
| Climate | **+0.002 [+0.0005, +0.0037]** / +0.001: better without it |
| Fish kill | −0.005 [−0.015, +0.003] / −0.006 [−0.015, +0.004] |
| Employment | −0.007 [−0.018, +0.001] / −0.004 [−0.013, 0.000] |
| OFW | 0.000 / +0.002 |
| News | −0.003 / −0.001 |
| Poverty | +0.010 [−0.004, +0.025] / −0.003 |
| H1 feature | −0.001 / 0.000 |

None is Holm-significant.

**Market does not hide a useful signal.** With Market gone, no other group becomes a reliable contributor. They do not substitute for it; they mostly add nothing.

### Fair-share checks (`out/fair_share.json`)

**Method.** Recomputed TreeSHAP of the per-origin models, Leads 1–2. Shares are of total |SHAP|, including the `lead` column.

| Group | Columns | Share of total \|SHAP\| | Per column | sd across origins |
|---|---|---|---|---|
| Market | 9 | 0.273 | 0.030 | 0.142 |
| Poverty V1 | 1 | 0.064 | **0.064** | 0.037 |
| Employment E1 | 1 | 0.032 | 0.032 | 0.065 |
| Fish kill C4 | 1 | 0.027 | 0.027 | 0.055 |
| News N1 | 3 | 0.023 | 0.008 | 0.029 |
| Climate C1–C3 | 4 | 0.016 | 0.004 | 0.037 |
| H1 feature | 1 | 0.013 | 0.013 | 0.035 |
| OFW E2 | 1 | 0.000 | 0.000 | 0.000 |
| *`lead` (horizon)* | 1 | *≈ 0.55* | – | – |

**Reading.**
- **Group size:** per column, Market is not larger than Employment or Fish kill. Its 68% bar share is helped by summing 9 columns. Held-out evidence (ablation, permutation, the A1-only family ablation) nevertheless confirms that A1 is genuinely the decisive input, so its first rank is justified; its *size* on the bar is inflated by group size.
- **Missingness** does not distort shares on the evaluation rows: every group's inputs are present on 100% of them. Earlier missingness (22–30%) falls in 2021–22 training rows.
- **The `lead` input** carries about 55% of the price model's attribution (the horizon shifts the base rate). The export drops it from the composition. This is defensible, because it is not an indicator, but it was undisclosed and is now listed here.

### Contributor by contributor

**What the columns mean:**
- **Scientific relevance:** the food-security role, with its source.
- **Predictive value:** held-out evidence on these 14/13 quarters.
- **Displayed share:** mean bar % on the 95 served rows.

| Contributor (families) | Food-security role and source | Predictive value (held out) | Displayed | Limits (resolution, timing, change) | Displayed contribution justified? |
|---|---|---|---|---|---|
| **Market** (A1 food-price projection, A2 headline, A3 rice, + world prices) | **Access**, through affordability: FAO 2006; FAO SOFI 2025, *Addressing high food price inflation for food security and nutrition* (doi 10.4060/cd6008en) | **Strong.** Ablation: Lead-1 Brier +0.052 [0.022, 0.089], Holm < .001. Permutation: +0.069, worse in 100%. A1 alone carries it; A2 and A3 add nothing alone. | 68% | Province, monthly, ≤ 2 months old at issue. The target's price leg is built from the same CPI: a **structural advantage**. | **Rank justified; magnitude inflated by 9 columns. Not a causal share.** |
| **Climate** (C1 El Niño, C2 typhoons, C3 palay/corn) | **Availability** and **stability** (production shocks): FAO 2006; SOFI 2018 edition on climate (theme as listed on FAO's flagship page); IBTrACS (doi 10.25921/82ty-9e16) for C2 | **None.** C1 and C2 are never split on. The model is slightly *better without* the group (Lead-2 Brier +0.004 [0.001, 0.007]; also within the no-market model). | 6% | C1 national and binary (rarely changes); C2 province, quarterly; C3 province, one quarter late. Shocks are few in 2021–26. | **Displayed above its predictive value.** Relevant in principle; not useful in this model and period. |
| **Fish Kill** (C4 fisheries production drop) | **Availability**, aquatic foods: FAO SOFIA 2026 (doi 10.4060/cd8357en) | **Not demonstrated.** Ablation n.s.; permutation ±; in the no-market model −0.005 [−0.015, 0.003]. Only Lead 3 is significant (family ablation, LEAD2_OPTIMIZATION). | 10% | The label says "Fish Kill"; the data is a production drop | **Over-displayed, and mislabelled** |
| **Employment** (E1 unemployment change) | **Access** (income): FAO 2006; SOFI 2019 edition on economic slowdowns (theme as listed) | **Weak:** Lead-1 Brier −0.005 [−0.013, −0.001], Holm .71; permutation +0.002 (90%) | 16% | **National** (one value for all provinces), Spearman +0.95 with time: **calendar-time confound**; rising unemployment is shown as lowering risk | **Over-displayed (~5× its held-out value). The direction is not interpretable.** |
| **OFW Remittance** (E2) | **Access** (household income) | **None** (never split on) | 0% | National; quarterly | **Honestly shown as 0** |
| **News** (N1: FSSI-v3, GDELT price news) | **Early warning:** Balashankar, Subramanian & Fraiberger 2023, *Science Advances* 9(9):eabm3449 (doi 10.1126/sciadv.abm3449). In 21 countries, news signals improved district-level food-crisis forecasts up to 12 months ahead. | **Not demonstrated here.** Served model: Lead-1 raw gain, Holm .43–.86, shuffle p .05; single model: none (p .65). Coverage 17% of Lead-2 rows. | hidden ("other") | Province; sparse (83% missing on Lead-2 rows) | **Hidden share acceptable given no demonstrated value.** Its absence from the bars must not be read as "news is irrelevant". |
| **Poverty / vulnerability** (V1 poverty and density) | **Access** (entitlements) and vulnerability: FAO 2006; PSA SAE 2021 | **None** (ablation n.s.). Permutation is not testable (static per province). | hidden ("other") | **Static** per province, published 2025 (timing exception). Acts as a **province identifier**: the highest per-column SHAP (0.064); +0.05 moves π_P by up to 0.36. | **The hidden share obscures the largest per-column influence.** It works as a province effect, not a time-varying driver. |
| **H1** regional hunger | **Outcome measure** (experience of hunger, access failure): SWS; FAO 2006 | **As the multiplier π_H4: decisive** (removing all hunger information: Lead-1 accuracy 0.843 → 0.686). **As a feature inside π_P: none** (ablation n.s.). | multiplier: named in the note with its value; feature: hidden | **Regional** (one Balance Luzon value for all provinces); published 2–8 weeks after fieldwork; design change 2025-Q2 | **The hunger term is the second half of the forecast but is not a bar.** The note states it (§11); a visual element would represent it better. |

### Is the "other" share honest?

**Before the fix.** No. V1, N1 and the H1 feature (mean 22.8%, max 88.9% of attribution) and the hunger multiplier were invisible, and the five bars claimed 100%.

**After the fix.** The notes state the hidden share and the hunger probability in numbers. That is accurate, but text only.

**Defensible composition (proposal; UI design, needs your approval):**
- six rows: Market, Climate and production, Fisheries production, Employment and remittances, **Poverty and vulnerability**, **News**;
- plus a separate **Regional hunger condition** line showing π_H;
- a footnote that the horizon (`lead`) is excluded;
- all labelled "relative model influence".

No weights would change. This is a display decision, not a model change.

---

## 5b. Why new HIGH onsets are missed (served P0H4; `out/onsets.txt`)

**Lead 2:** 10 onsets (a province LOW in q−1, HIGH in q), in 4 target quarters. 0 caught.

| Onsets | What switched on | Failed component | Cause |
|---|---|---|---|
| 2023-Q4 Batangas, Laguna, Quezon | hunger | both | No early warning: newest SWS 8.7, price projection −5 to −8 at issue 2023-07-01 |
| 2024-Q2 Batangas, Cavite, Laguna, Quezon | price | **hunger** (π_H4 0.40); price correct (0.68–0.80) | **Delayed publication:** the surge reading was published 21 days after issue |
| 2024-Q4 Cavite, Laguna; 2026-Q2 Cavite | price | price | No issue-time price warning |

**Ruled out:**
- **Probability combination:** caused 0 misses. 13 rows had both components ≥ 0.5 with the product < 0.5, none HIGH.
- **Target definition, partly:** 6 of the 11 Lead-2 misses are price conditions decided within 0.5 points of the threshold (+0.02 to +0.49). Label noise at that margin is below what a forecast made 5–7 months ahead can resolve.

**Lead 1:** onsets 4 of 10 caught.

**Sustained HIGH, Lead 2:** 3 of 4 caught. The miss (2024-Q3 Quezon) is a price-model override of a positive structural signal. A single LightGBM with a structural offset (LEAD2_ONE_MODEL S2/S3) catches it.

---

## 6. Overfitting, stability and sensitivity

**Quarter by quarter.** `LEAD2_ONE_MODEL/LEAD2_ONE_MODEL_REPORT.md` §5 (Lead 2) and `LEAD2_OPTIMIZATION/LEAD2_FINAL_REPORT.md` §5 (blocks).

| Check | Lead 1 | Lead 2 |
|---|---|---|
| Thirds | 0.88 / 0.76 / 0.90 | 0.72 / 0.70 / 0.90 |
| Leave-one-quarter-out minimum | 0.83 | 0.75 |
| Surge block 2023-Q4..2024-Q4 | 5/11 HIGH caught | 1/11 |
| Later block 2025-Q2..2026-Q3 | 6/6 | 5/6 |

**Input sensitivity** (`out/sensitivity.csv`; 4 latest origins, Leads 1–2; 40 rows per input):

| Input change | Largest change in π_P | HIGH/LOW flips |
|---|---|---|
| A1_food ±0.5 | 0.10 | 0 |
| A1_gap +0.5 | **0.31** | 1 |
| A2 +0.5 | 0.004 | 0 |
| A3 +2 | 0.03 | 0 |
| E1 +0.2 | 0 | 0 |
| C3, C4 +5 | ≤ 0.005 | 0 |
| H1 +0.05 | 0 | 0 |
| **V1 +0.05** | **0.36** | 2 |

**Reading.**
- **A1_gap** is sensitive as expected: the label's gap leg sits at that threshold.
- **V1 sensitivity is implausibly high** for a static poverty/density index. The shallow trees split on V1 as a province identifier. This is a **possible overfitting / geographic-memorisation concern**.

---

## 7. Target-dependence audit

**Construction.** T43c = [BL hunger > 11.3] AND [food YoY > P60, or food − headline > gap P60]. Verified exactly against Chapter I and from raw data (100 labels, 20 hunger quarters; `LEAD2_OPTIMIZATION/out/target_verification.txt`, `hunger_label_reconstruction.txt`).

**Mechanical price dependence.**
- Since 2023-Q4 hunger has been above 11.3 in every quarter, so T43c = price condition in 80% (Lead 1) to 92% (Lead 3) of rows.
- The price model π_P is trained on the price condition, which is computed from the same PSA CPI series that A1 projects.
- **Market's advantage is therefore structural** (by design of the target), not evidence that food prices cause food insecurity.

**Components separately** (`LEAD2_OPTIMIZATION/out/validation_ablations.json`):

| Component | Lead 1 |
|---|---|
| Price condition: served π_P | accuracy 0.614, AUC 0.67 |
| Price condition: A1 structural rule | accuracy 0.914, AUC 0.93 |
| Hunger condition (π_H, 14 quarters) | 12 correct, AUC 0.96, the same as latest-reading persistence |

**Combined proxy vs single components.** Full model 0.829 / 0.769 (Lead 1 / Lead 2). Without any hunger information: 0.686 / 0.631. Hunger-only: 0.514 / 0.431.

**The proxy is not observed food insecurity at any province or LGU.**

---

## 8. Geographic and temporal audit

**Resolution.**
- Province: A1–A3, C2–C4, V1, N1.
- National: C1, E1, E2.
- Regional: H1.

**LGU values.** The province probability re-weighted by poverty (60%) and density (40%); 141 of 142 LGUs have a municipal poverty estimate, and Lucena uses a province substitute. LGU values are **not** separately observed or validated.

**Calibration-in-the-large**, Lead 2 (mean p − observed rate; 90% CI; 13 quarters per province):

| Province | Calibration | Accuracy | FN / FP | HIGH |
|---|---|---|---|---|
| Cavite | +0.07 [−0.14, +0.29] | 0.62 | 3 / 2 | 3 |
| Laguna | −0.06 [−0.28, +0.17] | 0.62 | 3 / 2 | 5 |
| Quezon | −0.10 [−0.31, +0.11] | 0.77 | 3 / 0 | 6 |
| **Rizal** | **+0.20 [+0.14, +0.26]** | 1.00 | 0 / 0 | **0** |
| Batangas | +0.06 [−0.16, +0.25] | 0.85 | 2 / 0 | 3 |

At Lead 1, Rizal is +0.19 [0.14, 0.25].

**By period, Lead 2:**

| Period | Calibration | Missed HIGH |
|---|---|---|
| Household-head SWS base (< 2025-Q2; 7 quarters, 11 HIGH) | −0.07 [−0.28, +0.13] | 10 |
| Adult base (≥ 2025-Q2; 6 quarters, 6 HIGH) | **+0.16 [+0.07, +0.24]** | 1 |

**Reading.**
- The later period is easier: hunger stayed high and there were no hunger onsets. The model over-predicts there.
- **Outcome-defined groups** (onset −0.78; exit to LOW +0.36) are biased by construction: they select on the result. They are reported as miss rates, not as calibration evidence.
- **Province results share one regional hunger outcome per quarter.** Provinces differ only through prices, so per-province metrics are not independent evidence about provincial hunger.

---

## 9. Food-security dimensions

**Source.** FAO (2006), *Food Security*, Policy Brief Issue 2 (§10).

| Dimension | Coverage |
|---|---|
| Availability | **indirect** (C3, C4 production; A3 and world prices; C1, C2 shocks, but these are unused by the model) |
| Access | **partly**: SWS hunger (a regional outcome); A1/A2 prices; E1/E2 national income proxies; V1 static poverty |
| Utilization | **not measured** (no diet, nutrition, water, sanitation or health data) |
| Stability | **indirect** (time-varying shocks only) |

The five dashboard groups are a presentation structure, not a substitute for the four dimensions. Details: `LEAD2_OPTIMIZATION/FIVE_CONTRIBUTORS_AND_DIMENSIONS_AUDIT.md`.

---

## 10. Sources (verified 2026-10-27; what each supports)

| Source | Verified details | What it supports here | What it does not support |
|---|---|---|---|
| Collins GS, Moons KGM, Dhiman P, et al. **TRIPOD+AI statement**: updated guidance for reporting clinical prediction models that use regression or machine learning methods | *BMJ* 2024; 385:e078378. doi:10.1136/bmj-2023-078378. PMID 38626948 (verified via PubMed; bmj.com blocked automated access) | Reporting checklist: development and evaluation data, discrimination **and** calibration, validation design. Justifies reporting both, plus sample sizes and the absence of an external test. | It is a reporting guideline. It does not show that aiPHeed is unbiased. Clinical origin. |
| Wolff RF, Moons KGM, Riley RD, et al. **PROBAST**: a tool to assess the risk of bias and applicability of prediction model studies | *Ann Intern Med* 2019; 170(1):51–58. doi:10.7326/M18-1376. PMID 30596875. Four domains (participants, predictors, outcome, analysis), 20 signalling questions (Europe PMC abstract) | Structures §4: predictors available at the time of prediction (C, D); outcome definition and its independence from predictors (F: the target shares the CPI series with A1); analysis (D: overfitting, no untouched validation) | Designed for diagnostic and prognostic **health** models. Applied by analogy; domains such as "participants" map to province-quarters only loosely. |
| Moons KGM, Damen JAA, Kaul T, et al. **PROBAST+AI** | *BMJ* 2025; 388:e082505. doi:10.1136/bmj-2024-082505. PMID 40127903 | Extends the risk-of-bias assessment to machine-learning models (LightGBM here) | Same clinical-origin caveat |
| Lundberg SM, Lee S-I. **A Unified Approach to Interpreting Model Predictions** | arXiv:1705.07874 (2017); "To appear in NIPS 2017" | The trigger bars are additive per-prediction attributions of the model output (local explanation) | The abstract makes no causal claim, and SHAP does not validate accuracy. Hence the wording "relative model influence, not causes". |
| scikit-learn developers. **Permutation feature importance** (User Guide 5.2, v1.9.1) | https://scikit-learn.org/stable/modules/permutation_importance.html | Held-out permutation importance (§5); the warnings that correlated features share importance and that impurity (MDI) importance is biased toward high-cardinality features. Hence §5 uses ablation and permutation, not impurity importance. | No universal rule for group weights. **No source gives "correct" trigger-group percentages**; none were invented. |
| FAO. **Food Security**, Policy Brief Issue 2 (June 2006) | https://www.fao.org/fileadmin/templates/faoitaly/documents/pdf/pdf_Food_Security_Cocept_Note.pdf (text extracted and read) | The four dimensions, with utilization defined through diet, clean water, sanitation and health care (§9) | – |
| Social Weather Stations. Third Quarter 2026 Social Weather Survey media release on hunger (14 Oct 2026) | In the repository (`E114_Final_Run/data/raw/…`), text read | Question wording (family experienced hunger and had nothing to eat in the past three months); 600 respondents in Balance Luzon with ±4% margin (300 and ±6% for the other areas); face-to-face; adults 18+ | – |
| Balashankar A, Subramanian L, Fraiberger SP. **Predicting food crises using news streams** | *Science Advances* 2023; 9(9):eabm3449. doi:10.1126/sciadv.abm3449. PMID 36867695 (Europe PMC) | Why News is a scientifically relevant early-warning family: news signals improved district-level food-crisis forecasts up to 12 months ahead in 21 countries | That aiPHeed's news adds value: it did not here (coverage 17%) |
| FAO. **The State of Food Security and Nutrition in the World 2025**: *Addressing high food price inflation for food security and nutrition* | doi:10.4060/cd6008en (FAO flagship page) | The Market group's role: food-price inflation affects access to adequate food | Any specific weight for prices |
| FAO. **SOFI** editions listing (2018: climate; 2019: economic slowdowns and downturns) | FAO flagship-publications page (edition themes as listed; full reports not read) | The general relevance of the Climate and Employment groups | Their usefulness in this model (not shown) |
| FAO. **The State of World Fisheries and Aquaculture 2026** | doi:10.4060/cd8357en (FAO flagship page) | Aquatic foods' role in food security: the relevance of C4 | That C4 is a "fish kill" measure |
| NOAA NCEI. **IBTrACS** v04r01 | doi:10.25921/82ty-9e16; Knapp et al. 2010, *BAMS*, doi:10.1175/2009BAMS2755.1 | C2 typhoon tracks | – |
| PSA OpenSTAT CPI 0012M4ACP22; PSA SAE 2021; POPCEN 2024; LFS; BSP OFW remittances; PAGASA ENSO alert system; FNRI ENNS 2021 provincial dissemination | Identifiers and URLs recorded in the repository data inventory. The PSA site refused automated access today (HTTP 403); PAGASA's monitoring page exists. FNRI ENNS URL recorded in `E87_Outcome_Gap`. | Source, geography and timing columns of §3 | **Not re-verified online today.** Treat as repository-recorded provenance. |

---

## 11. Corrections

**Kept separate from any model change.** No model change was made.

**Previous branch `aiPHeed/lead2-optimization` (`9f7218e`): backend, served-model statuses and notes.**

| Defect | Fix | Before → after | Tests |
|---|---|---|---|
| Statuses came from the FIRI record | Computed from the served model's input availability | **135 → 0** false statuses | `test_api_ch1_risk.py::test_trigger_statuses_follow_the_served_models_own_inputs` |
| Notes did not say the bars cover only the price part, without the hunger multiplier and without the hidden share | Province and region notes rewritten | – | `::test_trigger_note_says_the_bars_explain_only_the_price_part` |

**This branch: text only (authorised).**

| File | Before | After |
|---|---|---|
| `frontend/src/components/LeftPanel.tsx` | "What drives this forecast?" / "Trigger composition" | "Relative model influence" / "Relative influence by trigger". Valid in both thesis and FIRI modes. Checked in the running app: both stay on one line, as before. |
| `frontend/src/components/GlossaryPanel.tsx`, SHAP | "explains how each input contributed… adding up to 100%" | Shares of the model's push rescaled to 100%; not the percentage of food insecurity caused; in the Chapter I forecast they explain the food-price part, and the note gives the hunger condition |
| `frontend/src/components/GlossaryPanel.tsx`, Risk Level | "likelihood of food insecurity in a province or municipality" | Province: probability of the Chapter I risk class, not a measured hunger rate. Municipality: a priority ranking, not a measured or forecast rate. |
| Regression test | – | `frontend/src/test/driverWording.test.tsx` |

**Not changed** (documented; would alter the approved UI or the model):
- adding V1, N1 and H1 as visible bars;
- the "Fish Kill" label (it is C4 fisheries production);
- Employment's over-display;
- C1, C2, E2 bars that are always 0;
- the Rizal and 2025–26 over-prediction.

Test results are in the closing summary.

---

## 12. Thesis-ready conclusion

aiPHeed's served forecast is a combination of two parts, evaluated walk-forward on 14 (Lead 1) and 13 (Lead 2) independent target quarters, 2023–2026, with no untouched test period:
- one LightGBM, trained across all leads, that predicts the provincial food-price condition from 12 indicator families;
- a closed-form probability that Balance Luzon hunger exceeds 11.3%.

**What the evidence establishes:**
- **Lead 1:** the forecast of the Chapter I food-insecurity-risk proxy beats price-only and hunger-only baselines (accuracy 0.843 vs ≤ 0.757).
- **Market dominance is real predictive reliance**, not a display artefact: confirmed by held-out ablation (Lead-1 Brier +0.052, Holm p < .001) and permutation (+0.069). Part of it is structural, because the target's price leg is computed from the same CPI series.
- **The dashboard composition is arithmetically correct additive SHAP.** It describes relative model influence on the price part only, not causes of food insecurity. Three labelling and status defects were found and corrected.

**What the evidence cannot establish:**
- that the model is unbiased;
- reliable forecasting beyond one quarter;
- the detection of new HIGH-risk onsets (0 of 10 at Lead 2, mostly because the information did not exist or was published after the issue date);
- any municipal or provincial food-insecurity outcome;
- the utilization dimension of food security.

**Remaining concerns:**
- possible over-prediction for Rizal and for 2025–2026;
- V1 acting as a province identifier;
- Employment shown far above its held-out value.

**By contributor:**

| Contributor | Scientific relevance | Predictive value here | Display |
|---|---|---|---|
| Market | relevant | demonstrated | first rank right, magnitude inflated by 9 columns |
| Climate, Fish kill, Employment, OFW | relevant | not demonstrated | Climate, Fish kill and Employment over-displayed |
| News | relevant (Balashankar et al. 2023) | not demonstrated (17% coverage) | hidden |
| Poverty | relevant | acts as a province effect | hidden, with the highest per-column influence |
| H1 hunger condition | decisive as the multiplier | – | outside the bars |

Market does not mask other useful signals: none becomes useful when Market is removed.
