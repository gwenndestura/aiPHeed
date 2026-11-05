# Proposed food-insecurity target (for adviser decision, 2026-11-05)

**Status:** proposal only.
- **Not implemented, not fitted, not served.**
- Eq. 3, C-B6, C-B6D-E-X and all results, seals and exports are unchanged.

## 1. The limitation (evidence)

| Fact | Evidence |
|---|---|
| Eq. 3 (Ch. III): S_p,t = H_t + 2·D_p,t, HIGH if S above the cut-off | Ch. III; Ch. I 1.2 ("composite food stress label combining SWS quarterly hunger data and PSA province-level food CPI deviation") |
| H_t (SWS Balance Luzon involuntary hunger) is **regional**: identical for all five provinces | SWS publishes no provincial figure |
| D_p,t (food-CPI deviation) is therefore the **only** provincial term | Eq. 3 |
| The provincial term does **not** track measured provincial food poverty or poverty | `PROVINCIAL_NONPRICE_EVIDENCE.md` §4: mean ρ +0.09 (p 0.39) and −0.25 (p 0.80) |
| Province non-price predictors cannot fix this, because the **label** differs across provinces only by price | C-B6D-E-XA: no gain |

**Conclusion:**
- Eq. 3 cannot represent provincial food-insecurity *differences*, only provincial price pressure.
- Fixing this needs a **target amendment**, not more predictors or tuning.

## 2. Measured food-insecurity data available (verified)

| Measure | Geography | Frequency | Precision | Food insecurity? |
|---|---|---|---|---|
| SWS involuntary hunger | Balance Luzon (regional) | quarterly, 1998– | survey | **Yes:** experiential hunger |
| PSA poverty incidence among families | 5 provinces | 2018, 2021, 2023 (OpenSTAT `1F/FY/0011F3DF010`); earlier vintages in PSA releases (to acquire) | CV 10–20% | Indirect: income inability to meet basic needs, food included |
| PSA subsistence (food-poverty) incidence | 5 provinces | 2018, 2021, 2023 | **CV 17–59%** (too imprecise for a target) | Yes: income below the food threshold |
| DOST-FNRI FIES (SDG 2.1.2), the thesis anchor | region 2023 (19.1%); provinces 2021 (Batangas 29.7%, Cavite 31.7%) | irregular | survey CIs | **Yes:** the direct FI scale |

**Province-level food insecurity is measured only infrequently**, and nothing of it is quarterly. Any quarterly
provincial target must therefore be a **model-based (synthetic) estimate**, stated as such.

## 3. Recommended target (smallest amendment)

**Keep H_t, the measured food-insecurity signal. Replace the price term by a measured provincial food-insecurity
vulnerability ratio.** This is the standard **synthetic small-area estimator**: apply the regional measured rate to each
province, scaled by a measured provincial correlate.

```
Ĥ_p,t = H_t × r_p,v(t)          r_p,v = PSA poverty incidence among families of province p in vintage v
                                         ÷ the CALABARZON incidence in the same vintage
v(t) = the latest PSA full-year poverty vintage PUBLISHED before the forecast issue date O(t)
y_p,t = 1 if Ĥ_p,t > c,   c = 11.3 (the SWS cut-off already used by C-B6; adviser to confirm)
```

**Why this target:**
1. **Food insecurity stays the outcome.** Ĥ is in SWS hunger units, so every movement over time comes from measured
   hunger. No price enters the target. Food prices become **predictors** (as in C-B6), which matches the CH3 amendment
   already adopted for the regional model.
2. **Provincial differences come from measured provincial deprivation** (PSA), not prices. Quezon, the poorest province
   in every vintage, gets the highest estimate.
3. **It reuses methodology the thesis already approves.** Objective 3 already disaggregates with PSA poverty incidence.
   The amendment moves that measured provincial information into the Objective 2 target, with a published, standard
   estimator.
4. **No fabricated measurement:** Ĥ is labelled "synthetic provincial hunger estimate (regional SWS × PSA poverty
   ratio)", never "provincial hunger".
5. **It is leak-free by construction:** v(t) is the latest vintage *published* before O(t).

**Alternative (sensitivity only):** r from subsistence incidence. Its CVs reach 59%, so it is not recommended as primary.

**Not recommended:**
- Additive forms (H + κ·(pov_p − pov_R)) need an arbitrary κ.
- Interpolating poverty between vintages invents values.

## 4. How forecasts follow (no new model needed)

- **The validated regional hunger forecast already gives** μ_H and σ_H. Under the amended target:
  `P(y_p,t = 1) = Φ((μ_H − c / r_p,v(t)) / σ_H)`.
  - Five distinct province forecasts.
  - The province ordering comes from measured poverty ratios.
  - The timing comes from the regional hunger forecast.
- **Price, employment, OFW, climate, production and news stay predictors of H**, in the existing regional LightGBM.
- **A province price-pressure indicator** (D) can still be **shown beside** the forecast as context (as the dashboard's
  price band already is), never inside the target.

## 5. Methodology implications (need adviser approval)

| Item | Change |
|---|---|
| Ch. III Eq. 3 | S = H + 2D → Ĥ_p,t = H_t × r_p,v(t), y = 1[Ĥ > c] |
| Ch. I 1.2 text ("composite … food CPI deviation") | Food CPI becomes a predictor; the target = SWS hunger scaled by PSA provincial poverty |
| H1 (FSSI and food CPI deviation among the strongest predictors) | Unchanged as a hypothesis; tested by SHAP on the regional hunger model |
| Objective 3 | Unchanged. LGU rankings stay vulnerability-weighted. **Note:** province poverty would then enter both the target and the disaggregation weight; the LGU step should use within-province normalisation only (as now), not re-weight by the province poverty ratio |
| The cut-off c | 11.3 (2021–22 BL 60th percentile, leak-free) instead of the all-period median; adviser to confirm |
| Wording | "Provincial food-insecurity risk (synthetic estimate)"; never "measured provincial hunger" |

## 6. Data still to acquire before any experiment

| Data | Why | Source |
|---|---|---|
| PSA provincial poverty incidence among families for **2006, 2009, 2012, 2015** | Labels and forecasts for 2013–2020 origins need the vintage published before each O(t) | PSA full-year poverty releases (provincial tables) |
| **Publication dates** of every vintage (2006–2023) | Defines v(t); avoids leakage | PSA press releases (official dates, to verify, not assumed) |
| FNRI ENNS/NNS provincial FIES (any years) | Independent validation | DOST-FNRI |

## 7. Validation plan (fixed before any fit; to be pre-registered with PLAN-SHA256)

1. **Construct validity, independent of the target:**
   - Spearman ρ between r_p,v and FNRI provincial FIES wherever both exist for the same year;
   - report n and CIs;
   - currently 2021, Batangas vs Cavite: poverty 4.3 vs 7.1, FIES 29.7 vs 31.7, the same order. **This is n = 2:
     indicative, not evidence.**
2. **Forecast evaluation:**
   - walk-forward, Leads 1–2, the frozen R1–R7, Algorithm 3;
   - baselines: persistence, the three logistic variants, the single-source LightGBM ablations;
   - all on identical province-quarters;
   - C-B6D-E-X (Eq. 3) reported alongside **as a different target**, not as a competitor on the same labels.
3. **Sensitivity:**
   - r from subsistence incidence;
   - r from the mean of all published vintages (less sampling noise);
   - c ± 1 point.
4. **Prospective:** seal the amended-target forecasts before the 2027 SWS releases.
5. **Claim rule:** "provincial food-insecurity forecast (synthetic)". "Validated" only if step 1 reaches p < 0.05 on
   independent FIES data.

## 8. Limitations to state

- **Province differences are structural:** they change only when PSA publishes a new vintage, every 2–3 years. All
  quarter-to-quarter change comes from regional hunger.
- **Ratio sampling error:** CV 10–20%. Provincial ranks vary across vintages (e.g. Laguna 2.7% → 6.9% → 5.4%).
- **Proportionality assumption:** the synthetic estimator assumes provincial hunger scales with provincial poverty
  relative to the region. It is testable only against FIES data.

## 9. Files

- **Added:** `TARGET_AMENDMENT_PROPOSAL.md` (this file).
- **Nothing else changed.**
