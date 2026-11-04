# Objective 5: FNRI face validity, source verification and adviser decision record

## 1. Source verification (two independent repository records)

| Figure | `backend/data/e22/nns_fies_verified.json` (E22, read 2026-10-13) | `E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv` (read 2026-10-21) | Agree? |
|---|---|---|---|
| NNS 2023 CALABARZON, moderate or severe FIES | 19.1% (95% CI 17.0–21.1), 2023 NNS infographic 2, p. 2 | 19.1% (16.9–21.3), p. 48 | **Value yes; CI differs** (two FNRI documents print different intervals) |
| ENNS 2021 Batangas | 29.7% (90% CI 27.3–32.2) | 29.7% (27.3–32.2), deck p. 53 | Yes |
| ENNS 2021 Cavite | 31.7% (27.0–36.4) | 31.7% (27.0–36.4), deck p. 53 | Yes |
| ENNS 2021 City of Lucena | — | 26.2% (23.6–28.9) | Single record |
| FNRI Updating Survey 2025 CALABARZON | — | **22.6%** (no regional CI printed), p. 7 | Single record |
| **NNS 2019 CALABARZON** | **Not published.** The ENNS 2018–2019 rolling sample covered 2 CALABARZON provinces; FIES reported nationally only (44.2%) | Not present | **Does not exist** |

The source PDFs are not stored in the repository: only their URLs, pages and retrieval dates are. A reviewer can
re-check each figure from the URLs in the two files.

## 2. Are the constructs comparable?

**No, only loosely.**

| | FNRI | aiPHeed |
|---|---|---|
| Measure | FIES: moderate or severe food insecurity among households over the past 12 months, annual | SWS involuntary hunger ("experienced hunger and had nothing to eat") among families, quarterly; forecast = P(> 11.3%) |
| Geography | Region IV-A; provinces or HUCs where sampled | Balance Luzon |

FIES includes milder deprivation, which is why its levels (19–32%) exceed SWS hunger (9–18%). The comparison is
therefore limited to **direction and ordering**.

## 3. Face-validity results

| Anchor | FNRI | aiPHeed (C-b, stored walk-forward forecasts, Lead 1) | Consistent? |
|---|---|---|---|
| 2021 → 2023 | Batangas 29.7%, Cavite 31.7% (2021) → region 19.1% (2023): falling | 2021: HIGH 4 of 4 (P 0.64–0.91); 2023: LOW 3 of 4 (P 0.31–0.61); SWS BL 12.6% → 11.2% | **Yes** |
| 2023 → 2025 | 19.1% → 22.6%: rising | 2025: HIGH 4 of 4 (P 0.54–0.74); SWS BL 18.2% | **Yes** |
| Province ordering 2021 | Cavite (31.7) > Batangas (29.7); intervals overlap | Province score Batangas 0.610 > Cavite 0.536 (2023 poverty weights, 2026-Q4 issue) | **No**, but not informative: overlapping CIs, different years, 2 provinces |

## 4. Proposed correction (needs adviser approval; the thesis text is not changed here)

> Objective 5 names "DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures". No 2019 CALABARZON regional figure
> was published (the 2018–2019 ENNS rolling sample covered two CALABARZON provinces and reported FIES nationally).
> The face-validity anchors are therefore:
> - the **2023 NNS** regional figure (19.1%);
> - the **2021 ENNS** provincial figures for Batangas, Cavite and the City of Lucena;
> - the **2025 FNRI Updating Survey** regional figure (22.6%).
>
> They are compared by direction and ordering only, because FIES and SWS hunger measure different constructs.

**Decision needed:** approve this wording and the anchor set, or keep 2023 only. **No 2019 value is substituted.**
