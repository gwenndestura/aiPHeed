# Training readiness (after publication-date and geography restrictions)

Counts come from `out/audit.json`. Row counts are not sample sizes. Every count below is of independent observations.

| Task | Usable examples | Independent units | Classes | Untouched evaluation available? | Verdict |
|---|---|---|---|---|---|
| **Lead 1 regional hunger** (SWS by area) | 106 quarters × 4 areas (424 area-quarters; 7 quarters have no round) | ~106 quarters; the 4 areas share national covariates | continuous level; "above usual" ≈ 41-59% | 2013-2020 already used by E114 and E116. **Only prospective quarters are untouched.** | **trainable**: level skill over persistence shown (E114/E116), from hunger history |
| **Lead 2 regional hunger** | same | same | same | same | **trainable for levels**. No HIGH/probability skill. No domain adds information (E116). |
| **Lead 1 provincial T43c** | 70 rows | **14 hunger quarters**; 7 HIGH quarters | 17 HIGH / 53 LOW | none: all inspected | **not a provincial outcome**. The price half is circular with A1/A2. |
| **Lead 2 provincial T43c** | 65 rows | **13 hunger quarters**; 7 HIGH quarters | 17 HIGH / 48 LOW | none | **insufficient**: R6 passes in only 19-45% of quarter resamples for every candidate |
| **Provincial food-insecurity forecasting** | 0 | no time-varying provincial outcome | — | — | **not supported** |
| **All five domains contributing** | — | — | — | — | **not supportable now**: employment and OFW are national (OFW 2021+ only); news 83% missing; rainfall absent |

## Why more rows would not fix this

- **The provincial stack copies regional and national values.** A model trained on 65 rows learns from 13 hunger observations.
- **Class balance (Lead 2):** 17 HIGH rows, in 7 HIGH quarters. A one-row change decides R6.
- **Temporal validation is feasible for the regional target** (rolling origin since 1999). The only untouched evaluation left is future SWS rounds.

## Is the dataset ready?

**Ready:**
- A **regional Lead-1 and Lead-2 hunger level** model.
- **Provincial vulnerability profiling** (V1, subsistence, FIES snapshots).

**Not ready:**
- **Provincial food-insecurity forecasting at Lead 1 or Lead 2.**
- **Any claim that all five domains contribute.**

**What would move this:**
1. Release dates and as-published vintages (CPI refresh months, production, LFS).
2. Regional or provincial quarterly LFS.
3. The BSP OFW series from 1989.
4. A provincial food-insecurity outcome with repeated rounds (CBMS, FNRI).
5. New SWS rounds for untouched evaluation.
