# E138: results and methodological recommendation (2026-11-04)

**Protocol.** E138-P1 (`PROTOCOL.md`), locked before any E138 fit to real outcomes, then run once.

**Files** (all in `backend/data/e138/out/`):
* `results.json`
* `oof_*.csv`
* `calabarzon.json`
* `sealed_prediction.json` (sha256 `e324433c…`)

**Status.**
* E137 is untouched (still rejected).
* E138's selected model `e138-where-lrp-1.0` is **REJECTED** by its pre-registered gate.
* Production stays `null`, and the dashboard is unchanged.
* **All numbers are development evidence.** The rows were already examined in hfias-1.0 and E137.

---

## 1. What the evidence supports, in one table

| Question | Finding | Strength |
|---|---|---|
| Do indicators carry information about **WHERE** risk is elevated? | Yes. Poverty statistics separate measured-elevated from measured-lower provinces in unseen regions (LR-P AUC 0.83; RR-P 0.85). | Moderate. CI vs the national base rate just touches 0 (+0.006). |
| Is that information more than "which region"? | **Mostly no.** The regional base rate under leave-one-province-out has EB 0.177 and AUC 0.96. No poverty-only model beats it. Poverty + a region effect (HIER) beats it: HIER-PMC −0.014 [−0.026, −0.001]; HIER-P −0.011 [−0.026, +0.006]. | Region membership carries most of the signal. |
| Beyond the previous survey? | No significant gain on the 47 re-surveyed provinces. All intervals include 0 and are wide (n = 47). | Underpowered. |
| Do market or climate add information? | **No.** Every nested set (PM, PC, PMC) is no better than P under LORO. Density makes it worse (+0.020 [+0.005, +0.036]). | Consistent across schemes. |
| Does LightGBM help? | **No.** The strongly regularised LightGBM is the worst indicator model in every scheme (LORO AUC 0.69–0.70; vs LR-P +0.023). | Clear. |
| Transfer across island groups? | **Fails for every model** (best: ridge AUC 0.70; logistic models 0.13–0.43). The poverty–food-insecurity relation differs between Luzon, Visayas and Mindanao. | Clear. |
| **WHEN:** do time-varying indicators explain measured change? | **No.** 62 % of the 2015 → ENNS changes are inside survey error. Prediction from indicator changes is 19 % *worse* than "no change". No indicator survives the Holm correction except cyclone frequency, and that has the wrong sign (below). | Clear negative. |
| Layer T (regional SWS timing) | No incremental value over persistence at any lead (FI6, locked). Independent evaluation is only possible prospectively. | Clear negative. |
| CALABARZON differentiation | **Structural similarity.** All five provinces are below or level with the national value in every survey. Quezon is highest but not statistically distinct (details in section 5). | Clear. |

## 2. WHERE: controlled comparison (125 rows, identical folds)

Expected Brier score (EB, lower is better) / AUC on decisive rows (40 ELEVATED vs 22 LOWER).

| Model | LORO | LOPO | ISLAND | V2 (2015 → ENNS) |
|---|---|---|---|---|
| NAT, national base rate | 0.258 / — | 0.247 / — | 0.371 / — | 0.239 / 0.50 |
| REG, regional base rate | 0.258 / — (no same-region rows) | **0.177 / 0.963** | 0.371 / — | 0.173 / 0.863 |
| PERS, previous survey (ENNS rows) | 0.195 / 0.766 | 0.195 / 0.766 | 0.202 / 0.735 | 0.193 / 0.769 |
| LR-P1, subsistence only | 0.232 / 0.817 | 0.218 / 0.865 | 0.353 / 0.02 | 0.207 / 0.797 |
| **LR-P**, poverty, subsistence, gap (selected) | 0.217 / 0.828 | 0.205 / 0.869 | 0.334 / 0.13 | 0.184 / 0.840 |
| LR-PD, + density | 0.237 / 0.757 | 0.207 / 0.873 | 0.329 / 0.31 | 0.203 / 0.772 |
| LR-PA, + previous survey | 0.218 / 0.794 | 0.204 / 0.849 | 0.306 / 0.35 | — |
| LR-PMC, + market + climate | 0.228 / 0.820 | 0.202 / 0.918 | 0.334 / 0.42 | 0.192 / 0.818 |
| LR-ALL | 0.224 / 0.839 | 0.198 / 0.903 | 0.332 / 0.43 | — |
| RR-P, continuous ridge | **0.211 / 0.847** | 0.206 / 0.861 | **0.254 / 0.68** | 0.177 / 0.840 |
| RR-ALL | 0.212 / 0.882 | 0.198 / 0.914 | 0.259 / 0.70 | — |
| HIER-P, + region effect | = LR-P | **0.166 / 0.975** | = LR-P | **0.139 / 0.938** |
| HIER-PMC | = LR-PMC | **0.163 / 0.972** | = LR-PMC | 0.137 / 0.932 |
| GB-PMC, LightGBM | 0.239 / 0.699 | 0.221 / 0.822 | 0.358 / 0.04 | 0.232 / 0.531 |
| GB-ALL, LightGBM | 0.240 / 0.685 | 0.222 / 0.803 | 0.357 / 0.04 | — |

Notes:
* Overfitting gaps are ≤ 0.05 for all linear models in LORO. HIER's gap is 0.07–0.09 in LORO, where it has no region
  effect to use.
* The NAT and REG AUCs are not meaningful: their predictions are constant within each fold.

**Selection (frozen one-SE rule).**
* Best: RR-P (EB 0.211).
* LR-P1 is 0.020 above it (SE 0.012), so it was not chosen.
* **LR-P** is 0.005 above it (SE 0.006): **selected**.
* Coefficients (standardised logit): poverty +1.20, subsistence −0.51, poverty gap +0.33. Poverty, subsistence and
  gap are collinear, so the signs of the individual coefficients should not be interpreted.

**Gate for LR-P.**

| Check | Result |
|---|---|
| G1 beats national with confidence | **fail** (CI [−0.091, +0.006]) |
| G2 beats regional base rate (LOPO) | **fail** (+0.028 [−0.016, +0.073]) |
| G3 AUC 0.828 [0.62, 0.96] | pass |
| G4 BA 0.726, recall 0.725, precision 0.829 | pass |
| G5 ECE 0.053 | pass |
| G6 island transfer | **fail** (AUC 0.13) |
| G7 overfitting gap 0.024 | pass |
| G8 non-inferior to persistence | **fail** (CI upper +0.115; underpowered) |
| G9 across surveys (AUC 0.84) | pass |
| G10 sensitivity (any-level AUC 0.89; round reference 0.86) | pass |
| G11 robust to missing non-poverty data | pass (n/a: poverty only) |
| G12 confirmatory | pending (sealed) |

**Structural validity horizon.** Leads 0, 2 and 4 give identical scores (EB 0.217), because the poverty inputs do
not change within a year. A 2015-based estimate still ranked the 2018/2019 measurements well (V2 AUC 0.84). These
are structural estimates. **They carry no forecasting lead**, and none may be displayed.

## 3. WHEN: within-province change, 2015 → ENNS (47 provinces)

**Size of change.** 18 of 47 changes are significant. The other 62 % are inside survey error.

**Leave-one-region-out weighted MSE of Δy.**

| Predictor | MSE |
|---|---|
| zero change | 0.200 |
| mean change | 0.203 |
| mean reversion | 0.202 |
| ridge on indicator changes | **0.239** (19 % worse than zero change) |

**Spearman correlations with Δy.**
* Food CPI change: +0.32 (p 0.034; Holm 0.34). Not significant after correction.
* All other market, agriculture, rainfall and poverty changes: |ρ| ≤ 0.25, Holm p ≥ 0.95.
* Cyclones per year between the surveys: **−0.45 (Holm 0.018)**. Provinces hit by more cyclones *improved*
  relative to the nation.
  * Mean reversion (ρ with y₂₀₁₅ = −0.09) does not explain this.
  * The likely explanation is post-Haiyan (2013) recovery and assistance in the Visayas between the 2015 and ENNS
    rounds. That is a confounded association, not a usable timing signal. It is reported, not used.
* **Conclusion:** no evidence that market, climate or poverty movements anticipate changes in provincial food
  insecurity.

## 4. Layer T (regional SWS timing; locked FI6 / FI6-N, FI6 Lead k+1 = Lead k)

| Lead | LightGBM accuracy / HIGH recall / AUC / Brier | Persistence |
|---|---|---|
| 0 | 0.839 / 0.27 / 0.69 / 0.129 | **0.871 / 0.55 / 0.74 / 0.116** (passes FI6's rule) |
| 1 | 0.806 / 0.00 / 0.47 / 0.163 | does not pass |
| 2–3 | 0.79 / 0.09–0.18 / 0.52–0.60 / 0.155–0.160 | does not pass |

* News (FI6-N) improves the Lead-0 Brier score by −0.0099 [−0.021, −0.002] over the government-only model. It does
  not change HIGH/LOW calls, and it does not beat persistence.
* **Layer T shows no incremental value and must not enter provincial scores.**
* Independent tests are prospective only: the sealed FI5 forecast (`350ffe4f…`) and the FI6 forecast for 2026-Q4 to
  2027-Q3, scored after SWS publishes those quarters.

## 5. CALABARZON differentiation

**Measured food insecurity (FNRI 2015 HFIAS moderate-or-severe).**

| Province | % | SE |
|---|---|---|
| Quezon | 48.8 | 3.4 |
| Batangas | 43.5 | 2.8 |
| Cavite | 41.8 | 2.5 |
| Laguna | 41.4 | 2.6 |
| Rizal | 41.3 | 2.8 |

* Cochran's Q = 4.0 (df 4), p = 0.41: the five provinces are not statistically distinguishable.
* Quezon vs each of the others: p = 0.08–0.23.
* ENNS: Laguna 2018 26.2 % (LOWER); Quezon 2019 44.0 % and Rizal 2019 39.1 % (both not distinguishable from
  national).

**Independent PSA indicators (published SEs).**

| Indicator | Quezon vs the other four |
|---|---|
| Poverty 2018 | 13.5 % vs 3.9–11.4 %; significant except vs Batangas |
| Poverty 2021 | 21.6 % vs 6.3–10.1 %; all p < 0.001 |
| Poverty 2023 | 10.2 % vs 6.7–8.5 %; significant only vs Cavite |
| Subsistence (families) 2023 | 0.5 %; Rizal is highest at 1.5 % |

**Model.** LR-P, PSA 2023 statistics, 500 region-cluster bootstrap refits:

| Province | P(elevated) | 90 % interval |
|---|---|---|
| Quezon | 0.33 | 0.13–0.62 |
| Cavite | 0.22 | 0.08–0.54 |
| Laguna | 0.22 | 0.09–0.55 |
| Batangas | 0.21 | 0.08–0.55 |
| Rizal | 0.20 | 0.09–0.56 |

* Quezon ranks first in 82 % of refits. But P(Quezon > Rizal) = 0.83, so **no province is distinct** under the
  pre-registered 0.95 rule.

**Conclusion.**
* Quezon's higher vulnerability is supported by the independent PSA poverty series in 2018 and 2021, and weakly in
  2023. It is not statistically established in measured food insecurity.
* The other four provinces cannot be told apart.
* Honest dashboard wording would be: "structurally similar, below the national level; Quezon somewhat higher". It
  would not show five different risk classes.

## 6. Five contributor groups

| Group | Nationwide data for the training years | Incremental information | Status |
|---|---|---|---|
| Poverty and social vulnerability | yes (PSA poverty, subsistence, poverty gap; census density) | yes: it is the signal (masking it raises EB by +0.042) | **supported** |
| Market and affordability | yes (provincial CPI, food threshold) | none (PM vs PD: no gain) | available, **not informative** |
| Climate and agriculture | yes (NASA POWER, IBTrACS, PSA production) | none for WHERE. For WHEN, cyclones show a confounded sign. | available, **not informative** |
| Employment and purchasing capacity | **no**: OpenSTAT LFS is national; no provincial series before 2021 | not testable | **context only** |
| News and NLP | **no**: the archive is CALABARZON-only; GDELT starts in 2017 | regional Lead-0 Brier gain only (FI6-N) | **context only** |

No nationally comparable provincial employment or news source exists for 2014–2019 on any public endpoint
reachable here (PSA OpenSTAT; the BSP and psa.gov.ph pages sit behind bot checks). These two groups must not be
presented as model inputs.

## 7. Recommended methodology (what the evidence can support)

1. **Present WHERE and WHEN separately.**
   * WHERE: a structural relative-risk estimate with uncertainty, and **no forecast lead**.
   * WHEN: monitored indicators and the regional SWS reading, shown as **context, not forecasts**.
2. **Structural model: poverty-based and region-aware.**
   * The development evidence favours poverty + a region effect anchored on measured surveys (HIER-P/HIER-PMC: LOPO
     EB 0.163–0.166, V2 AUC 0.93–0.94). It is the only family that beats the regional base rate.
   * It was **not** the pre-registered selection (selection used LORO, where HIER has no region effect). So it has
     to be tested as a new pre-registered candidate (E139): LOPO primary, HIER-P with the same gate. Its
     confirmatory evidence would come from a sealed prediction.
   * LightGBM is not justified at n = 125. It should not be the structural engine, and the reason is the measured
     evidence, not preference.
3. **No forecast lead.** The maximum reliable forecasting lead remains **none**:
   * for WHEN within provinces (section 3);
   * for Layer T (section 4).
4. **Confirmatory testing.**
   * `sealed_prediction.json` holds P(elevated) for 78 provinces from PSA 2023 statistics (LR-P), sha256
     `e324433c…`.
   * It is scored when the next provincial FI round appears. Its metrics are expected Brier score and AUC, against
     NAT, REG and PERS.
5. **DA usefulness.** Within CALABARZON, the defensible output is "similar, below national; Quezon somewhat higher",
   plus the municipal **vulnerability** ranking (PSA SAE poverty × density), labelled as vulnerability, not forecast.

## 8. Files

* **New code:** `backend/app/e138/` (`models`, `where`, `when`, `evaluate`, `calabarzon`, `gate`).
* **New tests:** `backend/tests/unit/test_e138.py`.
* **New data:** `backend/data/e138/` (raw PSA Table 3, lock, results, seal).
* **New docs:** `docs/e138/`.
* **Changed:** `backend/app/registry/catalog.py` (adds `e138-where-lrp-1.0`) and `data/registry/registry.json`
  (rejected).
* **Unchanged:** E137, the production route, the frontend.
