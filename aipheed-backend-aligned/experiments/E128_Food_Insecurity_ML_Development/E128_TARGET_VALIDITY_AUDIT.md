# E128 target validity audit

## 1. What target exists

| Item | Finding |
|---|---|
| Source | SWS involuntary hunger, **Balance Luzon** area estimate. Verified non-commissioned rounds, `FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv` (23 rounds, each with its publication date and source URL). |
| Frequency | Quarterly survey; 1–2 rounds per quarter |
| Geography | Balance Luzon, all of Luzon outside Metro Manila. CALABARZON is part of it, but **there is no SWS estimate for CALABARZON, any province, or any LGU**. |
| Reference period | "In the past 3 months" before fieldwork. The quarter is that of fieldwork. |
| Publication | 1–3 months after fieldwork (for example, 2026-Q3 fieldwork 21–27 Sep, published 2026-10-14) |
| Missing quarters | 2021-Q1, 2022-Q1, 2025-Q1 (no non-commissioned round). The 2025-Q1 Stratbase-commissioned round is excluded. |
| **Independent observations** | **20 quarters** (2021-Q2 .. 2026-Q3). Nothing in 2021–2026 can enlarge this. |
| Sampling error | Area margin of error about **±6 points** (`area_moe_bl`). A quarter-to-quarter difference needs about ±8.5 points to be significant. The median absolute change between consecutive known quarters is 2.35 points. |

## 2. The levels that are and are not supported

| Level | Supported? | Reason |
|---|---|---|
| Regional (Balance Luzon as a proxy for Region IV-A) | **Yes, as a proxy** | Direct measurement of the area that contains CALABARZON |
| Province | **No** | No provincial label. Copying the regional value to five provinces makes 5 copies of one observation. |
| LGU (142) | **No** | Same |
| T43c province-quarter class (Chapter I) | **Not admissible under E128** | Its hunger condition is the regional SWS value copied to every province. Its province part is the food-price condition, itself a predictor family (A1), so a model would partly predict its own input. |
| FIES 2023 CALABARZON | Context only | Annual, descriptive; the PUF has no FIES food-insecurity items (E-series audit) |
| FIRI3 / FIRI v2 | No | Composite indices, not outcomes (E128 §2) |

**So E128's supervised prediction level is regional.** No provincial or LGU accuracy can be claimed.

## 3. Class definition

**SWS defines no high/low hunger category**, so any binary class is a project definition.

### T1, primary (frozen before E128): HIGH = y > 11.3

- 11.3 is the hunger term of the Chapter I T43c label, frozen 2026-10-15 (E40 `label_spec.json`).
- It is the 60th percentile of the 2021–22 rounds. It was **not chosen in E128**, and not for accuracy.

### T4, secondary sensitivity (pre-registered): HIGH = y > mean of the last ≤ 4 known quarters at the issue date

- It measures above recent usual.
- It uses no constant.
- It is noisy relative to the ±6 margin of error.

### Rejected while auditing (from class balance and noise only; no model fitted)

| Candidate | Reason |
|---|---|
| Above the as-of median of all earlier quarters | Late window 11 HIGH / 1 LOW |
| Rise vs the latest reading | Below the sampling error in most quarters |

## 4. Class distribution (`E128_TARGET_CLASS_DISTRIBUTION.csv`)

| | T1 | T4 |
|---|---|---|
| Independent quarters | 20 (13 HIGH, 7 LOW) | 18 (10 HIGH, 8 LOW) |
| Outer evaluation rows, Lead 1 | 13 (11 HIGH, **2 LOW**) | 11 (8 / 3) |
| Lead 2 | 8 (8 / **0**) | 8 (5 / 3) |
| Lead 3 | 7 (7 / **0**) | 7 (5 / 2) |
| Lead 4 | 6 (6 / **0**) | 6 (4 / 2) |

## 5. Verdict

**T1 is valid in definition but saturated in time.**
- Every quarter from 2023-Q4 to 2026-Q3 is HIGH (11 in a row).
- All 7 LOW quarters fall in 2021-Q3 .. 2023-Q3, which is mostly before enough training data exists.
- So the outer evaluation contains 2 LOW rows at Lead 1 and **none** at Leads 2–4.
- Discrimination (balanced accuracy, AUC, LOW-class recall) **cannot be evaluated** beyond Lead 1. Under T1, "always HIGH" and persistence are near-perfect after 2023 by construction.

**Was training stopped?** No, because the target itself is defensible and the protocol was frozen before fitting. Instead:
- the protocol requires criteria that cannot be evaluated to count as **not passed**;
- T4 was pre-registered to test discrimination where both classes exist.

This is the target limitation E51 already recorded ("thesis label saturated"). The 2023–2026 data confirm it again.

## 6. What a valid stronger target needs (outside E128's authority)

- Provincial or LGU hunger or FIES measurements with dates: CBMS, FNRI ENNS, or DA/DSWD administrative data.
- Or many more regional quarters. Pre-2021 SWS history is outside the owner's 2021+ study window.
