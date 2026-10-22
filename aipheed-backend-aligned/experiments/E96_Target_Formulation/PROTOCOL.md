# E96 protocol: target validity, formulation, the false-alarm mechanism and signal availability (frozen before scoring)

**Branch.** `e96-target-formulation`, from `e95-root-cause-breakthrough` (115be91). Production unchanged: by the user's
decision the dashboard stays on FIRI v2.

**Freezing.** This file and `runner/run_e96.py` are hashed into `PROTOCOL.sha256` and committed before the run.

## 1. Outcome inventory (from the repository; no new data, by instruction)

| Source | What it measures | Geography | Time resolution | 2021–2026 coverage | Status |
|---|---|---|---|---|---|
| SWS involuntary hunger (`sws_rounds.csv`, `sws_hunger.parquet`) | **Measured** food insecurity: experienced hunger | Balance Luzon only. The provincial rows are `stratum_inherited`, i.e., the same regional value repeated. | Quarterly | 19 posted quarters (2025-Q2/Q3 missing) | Usable as a **regional** outcome |
| FNRI FIES (`nns_fies.parquet`; E87 `fnri_fies_observations.csv`) | **Measured** moderate-or-severe food insecurity | 2021: Batangas, Cavite, Lucena. 2023 and 2025: CALABARZON region only. | Every 2–4 years | 5 values | Face validity only; no time series |
| CBMS 2024 | Household food-security items | LGU | One round | Not in repository | Unavailable |
| PSA CPI (food, headline, rice) | A **contributing condition** (affordability), not food insecurity | Province | Monthly | Full | Input; the T43 price part |
| Climate, employment, remittances, news, poverty | **Contributing conditions** | Province or region | Mixed | Full | Inputs |

**What this means for the target.**
- **No measured provincial food-insecurity series exists in the data.** A provincial measured target cannot be
  constructed without fabrication, which is not done.
- **The defensible measured target is regional SWS hunger,** continuous, observed quarterly.
- **T43 stays the original target:** regional hunger condition × provincial price pressure, a proxy.

## 2. Questions and arms

### Q1: Formulation. Is the measured outcome better forecast as a continuous level than as a state?

- **Target.** Regional SWS hunger H(t+K), one row per target quarter (13 quarters, 2023-Q1..2026-Q3).
- **Model.** The selected arm's hunger component: the linear-tree LightGBM hunger-change regressor, pooled over K, with
  news and direction features. Its point forecast is Ĥ.
- **Baselines.**
  - random walk: the last posted reading;
  - climatology: the mean of the posted quarters.
- **Reported.**
  - RMSE and MAE;
  - Holm-adjusted one-sided per-quarter sign-flip tests on squared errors;
  - threshold accuracy (H > 11.3) against persistence;
  - **deterioration events** (H rises by at least 3 points over the last posted reading): events, predicted, hits and
    false alarms.

### Q2: The false-alarm mechanism (T43; all K)

**M-U96-POV.** The E94 framework plus the required poverty group: PSA SAE 2021 provincial mean, centred, known from
2025-01-01.

**M-U96-DECAY.** M-U96-POV with cumF4 replaced by an **inflation memory**:
- **mem_h:** the exponentially decayed mean of past food YoY relative to threshold, half-life h quarters.
- **memdir_h:** the same memory, set to 0 while food YoY has fallen over the last two origins (dF2 < 0).
- **Choosing h.** h ∈ {1, 2, 4} is chosen **per origin** by inner chronological validation: log-loss on the last 3
  training label quarters. The default is 2 when the inner split lacks both classes.

**Hypothesis.** Inflation memory that decays, and switches off once inflation turns down, keeps 2023–24 detection while
removing the 2025 false alarms.

### Q3: Signal availability (T43; all K)

Each of the five required groups is dropped in turn from the selected arm (both components). News is dropped only in
this ablation.

| Group | Features |
|---|---|
| Market / food prices | rice, world, momentum, changes, projections, policy, memory |
| Climate stress | ENSO, typhoons, their runs |
| Employment, remittances, OFW | unemployment change, underemployment, remittances, their changes |
| News / NLP | ten indicators, their changes and sums |
| Poverty and vulnerability | pov |

The current price state relative to thresholds is kept in every ablation.

## 3. Selection and rules (unchanged)

**Selection.** The lower mean Brier over K = 1..3 on targets 2023-Q1..2024-Q4, between M-U96-POV and M-U96-DECAY.

**PASS.** The E83 rule at every K.

**Validated K.** The E91 rule. Ablations are never selectable.

**Comparisons.** E94 (= E93 LINDIR = E95 BASE), S-COV and all E83 baselines on the same 65 rows per K.

**Q1 results are a separate research target.** They are not combined with T43.

**Disclosure.** This is the thirteenth experiment on these 13 quarters (development evidence). Only the sealed
2026-Q4..2027-Q2 are unseen.

### Q4: News must contribute (added before any scoring, at the user's mandatory requirement)

**News audit** (`runner/news_audit.py` → `news_audit.json`, `news_audit_quarters.csv`; descriptive, made before this
section):

| Finding | Value |
|---|---|
| Admitted articles 2021-Q1..2026-Q3 | 664 |
| De-duplicated events | 558 (1.19 articles per event) |
| Lead text available | 12.5% of articles (the rest are titles only) |
| Attributed to a province | 44% |
| Admitted per quarter, 2021–22 | 2–21, out of 150–320 collected |
| Collection volume over the period | grows about 5× |

- **Practical consequence:** before the 2023 surge, the model had almost no news history to learn from.
- **A visible lead:** adverse *supply* events peaked at 13 in 2023-Q2, two quarters before the 2023-Q4 onset.
- **No new collection,** by the user's deadline instruction: only the existing corpus is used.

**News representations** (otherwise identical arms on the Stage-A-selected variant):

| Representation | Inputs |
|---|---|
| none | `M-U96-DROP-news`, the Q3 ablation |
| n3 | The ten N3 indicators plus their changes and sums (the current framework) |
| imp | n3 plus de-duplicated, severity-weighted event rates per 100 collected articles, known before O(t), for prices, climate, supply and household; a food-access index (supply + household + prices) and its 2-origin persistence; relief/response events; **novelty** z-scores of the regional rates against their history before t (at least 4 past origins) |
| int | imp plus four interactions: food-access × hunger gap; supply × rice acceleration; climate × ENSO run; relief × hunger gap |

**Two-stage selection.**
1. Stage A chooses POV or DECAY (the n3 representation).
2. The final arm is the news representation (n3 / imp / int) with the lowest mean Brier over K = 1..3 on 2023–24.
   No-news is never selectable.

**Reported for news.**
- Per K, the paired per-quarter Brier gain of each news arm over no-news: mean, quarters better or worse, and a
  one-sided sign-flip p.
- Q1 measured-hunger results with and without news.
- **Counterfactuals** with the selected representation: news set to training medians at the K = 2 and K = 1 origins of
  2023-Q4 and 2024-Q2, and at K = 1 of 2025-Q4; the change in P(T43) and P(hunger).
