# Lead 2: final signal audit and decision

| | |
|---|---|
| Protocol | `PROTOCOL_LEAD2_FINAL_SIGNAL.md`, frozen in 6c6ab71 before any fit |
| Branch | `aiPHeed/lead2-rootcause-research` (local only) |
| Runner | `runner/final_signal.py`, stages study / fit / sens / groups |
| Deliverable builder | `runner/deliverables.py` |
| Seeds | LightGBM 2027; bootstrap 2031 |
| Input hashes | `out/study.json` → `input_sha256` |
| Unchanged | served P0H4 (a498b5ef), dashboard, T43c labels, the 65 rows, R1-R7, adoption rule, seals dd293e2e / 07c99e56 / b1edb799 |

## Decision: **B. Improvement not established.**

**Lead 1 remains the maximum supported horizon.**
- No pre-declared candidate passed its development gate, so none was fitted, selected or audited.
- The 65 inspected rows selected nothing.
- On the evidence, a reliable two-quarter forecast is not supported by the data the system holds today.
- The result also has elements of C (inconclusive):
  - the development period holds only **4 independent HIGH quarters** at Lead 2;
  - the confirmation period holds **3**;
  - the reference model's own development result depends on point-in-time-compromised training rows (§3).

## 1. Main bottleneck: the provincial price condition two quarters ahead

**Persistence is gone.**
- The target-quarter price condition differs from the last one known at issue in **48%** of Lead-2 cases.
- 73% of those changes are clear moves of more than 1 pp, not borderline cases.
- The margin's autocorrelation at the issue-to-target distance (3 quarters) is **0.05**.

**The series shifts by regime.** The mean food margin moves from +1.0 pp (2023) to −4.3 pp (2025), and the price-HIGH share from 0.85 to 0.07. There is no usable seasonality and no stable trend.

**The best issue-time forecasts are only modestly better than climatology** (DEV price Brier 0.17-0.19 vs 0.29), and **nothing holds in confirmation** on the official target.

**LightGBM itself loses information.**
- Its price part (DEV price Brier 0.273) is worse than the projection it is given, when that projection is turned into a probability with its own historical error (0.188).
- At Lead 1 the gap is 0.283 vs 0.120.
- So part of the price-part weakness is the binary LightGBM classifier on a small, regime-shifting sample, not only the series.
- This is the one finding that points to a correctable cause (see "Next attempt"). It was not turned into a candidate here, because doing so would select on the same development results.

**Food insecurity or price pressure?**
- The LightGBM component forecasts **provincial price pressure**, a proxy.
- The hunger component is the **latest regional SWS reading carried forward**.
- The repository has no provincial, independently observed food-insecurity outcome.
- So even a passing Lead-2 score would describe the composite proxy. It would not show that provincial food insecurity is predicted.

**Is the target itself stable? (not replaced)**
- The 2021-22 P60 thresholds were set in a different price regime.
- From 2024 on, the price margins sit 2.6-4.3 pp below them, so the price-HIGH share falls to 0.07 in 2026, and HIGH outcomes become rare and regime-dependent.
- A development-only alternative would use thresholds re-estimated from information available at each origin (an expanding-window P60). That would need its own frozen protocol and a new confirmation period. The official labels stay unchanged.

## 2. Indicators (`LEAD2_INDICATOR_AVAILABILITY.csv`)

All 12 indicators stay in the pipeline. Presence is not the same as information.

| Indicator | Varies by province / quarter | Lead-2 missing | Availability | Information |
|---|---|---|---|---|
| A1 / A2 CPI | yes / yes | 9% / 0% | verified for m0 (35/36) | market group: L2 DEV +0.005 [−0.025, +0.033]; CONF +0.074 [+0.040, +0.107] |
| A3 rice | yes / yes | 27% | assumed lag | (market group) |
| V1 poverty | yes / **no** (5 values) | 0% | **violation**: SAE 2021 and POPCEN 2024 were published 2024-25; no earlier vintage is in the repository, so no origin before 2025 had these values | not established (L2 DEV +0.001). A structural profile, **not a time-varying early-warning signal** |
| C1 El Niño | **no** / yes (2 values) | 0% | verified | climate: not established; possible noise in L2 CONF (−0.010) |
| C2 typhoons, C3 production | yes / yes | 4% / 22% | plausible / assumed | (climate) |
| C4 fisheries | yes / yes | 22% | assumed | reported separately |
| E1 unemployment, E2 remittances | **no** / yes (18 values) | 22% | assumed | not established. National values only, so they repeat one value per quarter across provinces |
| N1 news | yes / yes | **83%** | verified | NaN exactly when admitted headlines < 5. Coverage by origin year: 0% (2021), 5%, 10%, 35%, 20%, 40% (2026): collection-calendar driven. Possible noise in L2 DEV (−0.011) |
| H1 hunger outlook | **no** / yes | 9% | verified | target component |

**Climate.** Its lack of value appears at both leads and in both periods. With only 4 DEV HIGH quarters, seasonal or provincial dependence cannot be tested reliably.

## 3. Point-in-time resolution

| Issue | Finding | Effect |
|---|---|---|
| 600 training rows use the 2021-22 thresholds before they could be computed (includes the 375 pre-2018=100 rows) | Without them, **no development origin has enough training rows** | B0's development result depends on these rows. In CONF without them: L2 Brier 0.169 vs 0.156; L1 0.124 vs 0.123 |
| Assumed lags of A3, C3, C4, E1, E2 | No dated releases are saved. If each is one quarter later: | L2 DEV Brier 0.189 vs 0.177, recall 1/11 vs 5/11. B0's Lead-2 development skill is fragile to the unverified lags |
| V1 timing | Later-published constant | It enters only through province ordering. Its whole contribution is bounded by its ablation (≤ 0.002) |
| Derived features | Ridge training targets and the error histories behind each σ are all before the origin (asserted and tested). N1 follows its definition. | — |

## 4. Trigger contributions (`LEAD2_TRIGGER_CONTRIBUTIONS.csv`)

**Setup.** Model B0 (no candidate was selected). Each group is refitted out at every origin. Quarter-block 90% CI, Holm correction across 5 groups.

**Lead 2, Δ Brier when the group is removed (positive = group helps):**

| Group | DEV | CONF |
|---|---|---|
| Market / food prices | +0.005 [−0.025, +0.033] | **+0.074 [+0.040, +0.107]**, Holm p < 0.001 |
| Climate | −0.000 | −0.010 [−0.019, −0.002] (possible noise) |
| Employment / remittances | −0.001 | +0.009 [−0.000, +0.028] |
| Poverty / vulnerability | +0.001 | +0.002 |
| News / NLP | −0.011 [−0.020, −0.002] (possible noise) | −0.002 |

**Reading the table.**
- Only market prices adds measurable out-of-sample value, and only in the later period. Its DEV interval spans zero.
- The other groups are included in the model, but their predictive value is not established.
- No group's importance was inflated.

## 5. Next attempt: what data or signal is missing

1. **An untouched confirmation period.**
   - About 6 or more new scored quarters, beginning with the sealed prospective forecasts.
   - Any new candidate must be frozen before those outcomes exist.
   - The 65 rows cannot provide independent evidence.
2. **Verified release dates.**
   - For the CPI refresh months: 61 owner-reported and 79 unresolved.
   - For the lagged indicators A3, C3, C4, E1 and E2. Their lags move B0's own development result.
3. **As-of vintages.**
   - 2012=100 CPI for 2021 training rows.
   - Pre-2024 poverty estimates (SAE 2018) for V1.
4. **A pre-registered price-part redesign**, tested on (1):
   - probability-from-projection (M0) or damped trend (M4);
   - origin-available thresholds as a separately labelled development target.
   - Both showed DEV promise here but were not pre-declared, and neither held in CONF on T43c.
5. **Provincial, timely leading series.** Provincial labour and remittance data, station rainfall, and denser news coverage. Without them, four of the five groups cannot separate provinces or anticipate price moves.

**Lead 2 should not be described as reliable** until a candidate frozen in advance passes R1-R7 and the adoption rule on genuinely prospective quarters.
