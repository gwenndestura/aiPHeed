# Manuscript revisions: synthetic provincial food-insecurity target

> **STATUS: PENDING ADVISER APPROVAL.** Nothing here is in the manuscript yet.
> - The original Equation 3 stays in force until the adviser approves.
> - The proposed target is **not validated**; no model has been fitted to it.
> - The cut-off for the proposed target is **not yet determined**.

**Prepared:** 2026-11-05. **Technical basis:** `../OBJECTIVES_AUDIT/CB6P/TARGET_AMENDMENT_PROPOSAL.md`,
`../OBJECTIVES_AUDIT/CB6P/PROVINCIAL_NONPRICE_EVIDENCE.md`.

## Sources of the manuscript text quoted below

The full manuscript file is **not in the repository**. The quotations come only from:
- `FINAL_THESIS_OBJECTIVES/sources/chapter1_THESIS2_11_extract.txt` (Chapter I text extract, §1.2–§1.7);
- `PAPER_ALIGNED/CH3_AMENDMENT.md` (section and page map of Chapters I and III, with quoted wording: Eq. 3 and
  Table 3.4.2.3 at pp. 51–52, Eq. 5 / Table 3.4.2.4 at pp. 52–53, Algorithm 3 at pp. 41–43, Algorithm 5 at p. 46,
  Rule 4 at p. 48, §3.4.4 at p. 57).

Where the exact manuscript sentence is not available here, the row says **"locate in manuscript"**. No manuscript
wording has been invented.

**Relation to the earlier amendments in `CH3_AMENDMENT.md`:**
- Those options replaced Eq. 3 with a **regional** target (SWS BL hunger > 11.3%).
- This proposal is a further option. It keeps measured SWS hunger as the food-insecurity signal, but makes the target
  **provincial** through a measured PSA provincial ratio.
- The adviser chooses **one**.

---

## 1. Chapter I revisions

| § (page) | Current text (quoted) | Proposed text |
|---|---|---|
| 1.2 (p. 9) | "…integrates this with a composite food stress label combining SWS (Social Weather Stations) quarterly hunger data and PSA province-level food CPI deviation, anchored to the FAO SDG 2.1.2 baseline established by the DOST-FNRI ENNS…" | "…integrates this with a **synthetic provincial food-insecurity estimate**: SWS quarterly hunger data scaled by each province's PSA poverty incidence relative to CALABARZON, with PSA food CPI and other indicators used as **predictors**. Its province ordering is to be checked against the FAO SDG 2.1.2 (FIES) estimates of the DOST-FNRI ENNS/NNS…" |
| 1.2 (p. 8–9) | "…derives a validated forecast target from publicly available CPI (Consumer Price Index) data…" | "…derives a forecast target from publicly available SWS hunger and PSA poverty statistics, with CPI data used as predictors…" (do not say "validated" until §3 validation is complete) |
| 1.3 RQ1 (p. 10) | "What variables most significantly predict food insecurity risk across the provinces of CALABARZON…" | Unchanged |
| 1.3 RQ2 (p. 10) | "…furthest lead time at which aiPHeed can reliably forecast province-level food insecurity risk…" | "…reliably forecast **province-level food-insecurity risk, measured as a synthetic provincial estimate (regional SWS hunger × PSA provincial poverty ratio)**…" |
| 1.3 RQ3 / 1.4 H3 (pp. 10–11) | "…in classifying provincial food insecurity risk" | Unchanged wording; the target behind "provincial food insecurity risk" is redefined in §3.4.2 |
| 1.4, dependent variable (p. 11) | "The dependent variable is the binary food insecurity risk classification, either high or low, of a CALABARZON province in a given quarter." | "…the binary classification, high or low, of a CALABARZON province's **synthetic food-insecurity estimate Ĥ (Equation 3a)** in a given quarter." |
| 1.4 H1 (p. 11) | "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest predictors…" | Unchanged. Food CPI deviation is now **only** a predictor, so H1 tests it without the circularity of being part of the label |
| 1.5.2 Obj 2 I, II, IV (pp. 12–13) | "…high- and low-risk province-level classifications", "…high-risk provinces…", "…between high- and low-risk provinces…" | Unchanged wording; add after Obj 2: "Province-level classifications refer to the synthetic provincial food-insecurity estimate defined in §3.4.2 (Equation 3a)." |
| 1.5.2 Obj 3 (p. 13) | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | Replace "validated province-level forecasts" with "province-level forecasts (validated under the criteria of §3.4.4)". **Add:** "Because provincial poverty already enters the provincial target (Equation 3a), the LGU weights normalise poverty and density **within each province only**." |
| 1.5.2 Obj 5 (p. 13) | "…validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor." | "…check its provincial ordering against DOST-FNRI ENNS/NNS FIES estimates where provincial figures exist (2021: Batangas, Cavite) and its regional level against NNS 2023 CALABARZON (19.1%)." (No 2019 CALABARZON figure exists: `OBJECTIVES_AUDIT/OBJ5_FNRI_FACE_VALIDITY.md`.) |
| 1.7 (p. 15) | "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk, while DOST-FNRI data will provide regional food security references." | "SWS quarterly hunger data, scaled by PSA provincial poverty incidence, will be used to determine provincial food-insecurity risk (a synthetic estimate, not a direct provincial measurement); PSA food price data and other indicators will be predictors; DOST-FNRI data will be used to check the provincial ordering where provincial figures exist." |
| 1.7 (p. 15), new sentence | — | "The provincial estimates are synthetic. They assume that provincial hunger is proportional to provincial poverty relative to the region, and they change across provinces only when PSA publishes a new poverty vintage." |
| Definition of Terms | locate in manuscript | **Add:** "Synthetic provincial food-insecurity estimate (Ĥ): SWS Balance Luzon hunger multiplied by the ratio of the province's PSA poverty incidence among families to CALABARZON's, using the latest vintage published before the forecast date." |

---

## 2. Chapter III revisions

### 2.1 §3.4.2 Target definition (pp. 51–52): replacement text

> **3.4.2 Forecast target**
>
> **Equation 3 (original, retained for reference).** The composite stress score is S_p,t = H_t + 2·D_p,t, where H_t is
> SWS hunger and D_p,t is the province's food CPI inflation deviation from the regional mean. A province-quarter is HIGH
> when S_p,t exceeds the median of all province-quarter scores.
>
> **Equation 3a (proposed replacement: PENDING ADVISER APPROVAL)**
>
> Ĥ_p,t = H_t × ( P_p,v(t) / P_R,v(t) )
>
> y_p,t = 1 if Ĥ_p,t > c, else 0
>
> **Where:**
> - H_t is SWS involuntary hunger in Balance Luzon in quarter t: the quarter mean of non-commissioned rounds. A
>   quarter without a round has no label.
> - P_p,v is PSA full-year poverty incidence among families of province p in vintage v.
> - P_R,v is the CALABARZON regional incidence in the same vintage.
> - v(t) is the latest vintage whose official PSA release date precedes the forecast issue date O(t).
> - c is the classification cut-off, to be fixed from the training period before evaluation (§2.4).
>
> **Ĥ is a synthetic small-area estimate**, not a measurement of provincial hunger. All of its change over time comes
> from measured SWS hunger. The differences between provinces come from measured PSA poverty.

**Why Equation 3 is replaced (evidence for the adviser):**
- In Equation 3, H_t is identical for all provinces, so provinces differ only through the food-price term D.
- An independent check found that D does not track PSA's measured provincial subsistence or poverty incidence
  (2018, 2021, 2023: mean ρ +0.09, p 0.39; −0.25, p 0.80; `PROVINCIAL_NONPRICE_EVIDENCE.md`).
- The all-period median also uses future data (CH3_AMENDMENT §1).

### 2.2 Table 3.4.2.3 (target variables): proposed replacement rows

| Symbol | Variable | Source | Geography | Frequency | Role |
|---|---|---|---|---|---|
| H_t | Involuntary hunger, % of families | SWS | Balance Luzon | quarterly | Target component (measured) |
| P_p,v | Poverty incidence among families, % | PSA full-year poverty statistics (OpenSTAT `1F/FY/0011F3DF010`: 2018, 2021, 2023; earlier vintages from PSA releases) | province | every 2–3 years | Target component (measured) |
| P_R,v | Same, CALABARZON | same | region | same | Target component (measured) |
| Ĥ_p,t | Synthetic provincial food-insecurity estimate | Equation 3a | province | quarterly | **Target (synthetic)** |
| y_p,t | HIGH/LOW | Ĥ vs c | province | quarterly | Label |

### 2.3 Eq. 5 / Table 3.4.2.4 (predictors, pp. 52–53): changes

- **Food CPI deviation D_p,t moves from the target to the predictors**, with the same as-of rule: CPI months ≤ issue
  month − 2.
- **All existing predictor groups stay:** hunger history, food and headline CPI, rice prices, world prices, climate
  (ONI, typhoons), crops, fisheries, rice stocks, employment (national LFS), OFW remittances (national BSP) and news
  (FSSI).
- **Label national series as national;** they are not province-specific.

### 2.4 Cut-off c: not yet determined

- 11.3% is the 2021–22 60th percentile of **Balance Luzon** hunger. It has **not** been shown to be appropriate for Ĥ.
- **Proposed rule (to pre-register):** c = a fixed percentile of Ĥ over the 2021–22 province-quarters, computed before
  any evaluation, with sensitivity at c ± 1 point.
- **Alternatively,** keep 11.3% for comparability with the regional model.
- **The adviser chooses; the choice is recorded before fitting.**

### 2.5 Data-availability rule (new paragraph in §3.4.1 or §3.4.2)

> **Publication-date restriction.** At each forecast issue date O(t) (the first day of quarter t + 1), the target and
> predictors may use only data published before O(t):
> - SWS rounds by their release date;
> - PSA CPI up to month 2 of quarter t;
> - PSA poverty vintage v(t), the latest vintage whose **official release date** is before O(t).
>
> A vintage is never used for an origin before its release, even when its reference year is earlier. The release dates
> of every vintage used are listed in an appendix table, taken from the PSA press releases.

**Required before use:** the PSA release dates for the 2006, 2009, 2012, 2015, 2018, 2021 and 2023 full-year
provincial poverty statistics, and the 2006–2015 provincial values. These are **not yet in the repository**.

### 2.6 Assumptions and limitations (add to §3.4.2 and §1.7)

1. **Proportionality:** provincial hunger relative to the region is assumed equal to provincial poverty relative to the
   region. Testable only against FIES data.
2. **Structural provincial differences:** they change only when a new PSA vintage is released, every 2–3 years. The
   quarterly dynamics are regional.
3. **Sampling error:** provincial poverty CVs are 10–20%. Ranks vary between vintages (e.g. Laguna 2.7% → 6.9% →
   5.4%).
4. **Balance Luzon ≠ CALABARZON:** H is Balance Luzon (all Luzon outside Metro Manila).
5. **Not an official classification**, consistent with §1.7.

### 2.7 Algorithm 3, §3.4.4 and Rule 4 (pp. 41–48, 57)

- **Algorithm 3** is unchanged (75% mean fold accuracy), applied to y_p,t from Equation 3a, reported with R1–R7.
- **Rule 4 / Algorithm 5 (LGU disaggregation):** within-province min-max normalisation only (poverty 60%, density 40%),
  multiplied by the province probability from Equation 3a. The province poverty ratio is **not** applied a second time.

### 2.8 Validation plan (new subsection under §3.4.4)

1. **FNRI construct check:**
   - Spearman ρ between P_p,v / P_R,v and DOST-FNRI provincial FIES (moderate or severe) for each year where at least
     3 provinces have FIES;
   - report n and both sources' confidence intervals;
   - currently only 2021 Batangas and Cavite exist (the same order as poverty; n = 2, not evidence).
2. **Forecast evaluation:**
   - walk-forward, Leads 1–2, R1–R7, Algorithm 3;
   - baselines (persistence; three logistic regression variants; single-source LightGBM ablations) on identical
     province-quarters.
3. **Sensitivity:** P from subsistence incidence; P averaged over the published vintages; c ± 1.
4. **Prospective:** forecasts sealed before the 2027 SWS releases.
5. **Claim rule:** describe as "synthetic provincial food-insecurity forecast". Use "validated" only if step 1 is
   significant at α = 0.05 on independent FIES data.

---

## 3. Consistency checklist (to tick when the adviser approves)

- [ ] Ch. I §1.2, §1.4 dependent variable, §1.7: the target described as Equation 3a, synthetic.
- [ ] Ch. III §3.4.2: Equation 3 retained as original; Equation 3a added; Table 3.4.2.3 replaced.
- [ ] Eq. 5 / Table 3.4.2.4: food CPI deviation listed as a predictor.
- [ ] §2.4 cut-off c decided and recorded before fitting.
- [ ] §2.5 PSA release-date table added (data to acquire first).
- [ ] Obj 3 / Rule 4 / Algorithm 5: within-province normalisation only.
- [ ] Obj 5: FNRI wording corrected (no 2019 regional figure).
- [ ] Every "validated" claim removed until §2.8 step 1 succeeds.

## 4. Files

- **Added:** `PAPER_ALIGNED/TARGET_AMENDMENT_MANUSCRIPT_REVISIONS.md` (this file).
- **The original Chapter I extract and `CH3_AMENDMENT.md` are not modified.**
