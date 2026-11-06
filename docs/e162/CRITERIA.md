# E162: evidence-based provincial priority. Criteria fixed before results.

Written 2026-11-06.

## Owner decision recorded
The owner's E162 prompt restores **E158 as the province-ordering baseline**, revoking the E160 adoption of RP+R after E161. The HIGH/LOW classification model stays E158.

## What has been seen
- E159 to E161 results for E158, PERS, RP, OH, RP+R and OH+R on the 72 Lead 1 rows, including their ranking measures.
- **Not seen:** any ranking measure for the E151 arms **SS** (state space) and **FH** (Fay–Herriot). Their forecasts exist in `data/e151/out/prov_oof.csv` and were designed in E151, before the ranking problem was raised.
- No untouched evaluation period remains: 2018, 2019 and 2021 have all been read. **Every result here is retrospective.**

## Revised method: separate level from priority
- **Absolute risk and class:** E158, unchanged.
- **Relative provincial priority:** **SS**, pre-specified because it is the only existing method that does all of the following:
  - It uses each province's own same-instrument (HFIAS) survey history, with sampling error.
  - It adds uncertainty for survey age: a local-level Kalman filter, with variance per year `q` chosen by predictive likelihood on released rounds only.
  - It shrinks toward a hierarchical prior from province poverty (PSA), with between-province variance estimated by moments.
- **No new arm is built.** FH (the same model with `q` = 0) is reported as a comparator.

## Ranking measures (Lead 1)
1. **Within-region pairwise concordance:** the E159 pairs and bootstrap (seed 159, region-round clusters).
2. **Within-round Spearman and Kendall:** all provinces in the round.
3. **Most vulnerable province:** top-1 hit in region-rounds with 3 or more provinces.
4. **Position error:** mean |predicted rank − observed rank| within region-round, divided by (n − 1).
5. **Per-round concordance:** within-region concordance computed separately for 2018, 2019 and 2021.
6. **Effective sample size:** pairs and region-round clusters.

## Gates for SS as the priority method
- **P1:** within-region concordance, 95 % interval lower bound > 0.5.
- **P2:** Spearman > 0 in all 3 rounds.
- **P3:** robustness across rounds. Concordance ≥ 0.5 in each of the 3 rounds.
- **P4:** shuffled control.
  - Each province's survey history is reassigned to another province in the same region (3 seeds: 1, 2, 3; regions with one province keep their own). The poverty prior stays real.
  - Real − shuffled concordance must have a 95 % interval lower bound > 0. This shows that the province's own history carries the ordering.

**Reported, not gated:**
- **Nested selection:** choose among {E158, RP, OH, FH, SS} by concordance on 2 rounds, score on the 3rd. If the nested result is more than 0.05 below the best single arm, flag OVERFIT-SELECTION.
- **Bias:** position error and signed error (predicted % − observed %) by:
  - island;
  - observed class;
  - number of released rounds for the province (≤ 2 vs 3 or more);
  - survey age (`gap_q` above vs at or below the median).

  Bootstrap 2,000 draws, seed 162, region clusters. **A non-significant result is not proof of no bias;** cells with n < 10 are marked "too small".

## 2027-Q1 display rule
- If SS passes P1 to P4, it supplies the provincial priority. Otherwise E158 does, labelled "order not validated".
- **P(highest):** 10,000 draws per province, seed 162.
  - For SS, the draws are independent normals with the Kalman state variance.
  - For E158, the E160 rule applies: sd × sqrt(1 − 0.726).
- **"Quezon ranks first" is shown only if all three hold:**
  - (a) the priority method passed P1 to P4;
  - (b) P(Quezon highest) ≥ 0.80;
  - (c) the direct same-instrument comparative evidence (rounds that measured all five provinces together) is consistent.

  Otherwise the display says **"most likely highest, X %"**, or lists the provinces without ranks.
- The same rule applies to every province.

## LGU priority
- **LGU-v2 (E160) is kept:** tier by class, then vulnerability (0.6 poverty + 0.4 density), with no probability multiplier.
- The provincial priority from the method above does not enter it, because the priority is uncertain.
- A **poverty-only sensitivity list** is shown for the owner's open weighting decision. It is not adopted.

## Not allowed
- Adding arms, changing gates, the 0.80 rule or seeds after results.
- Any province-specific adjustment.
- Changing the threshold.
- Mixing FIES and HFIAS.
- Changing production, the dashboard or the API.
