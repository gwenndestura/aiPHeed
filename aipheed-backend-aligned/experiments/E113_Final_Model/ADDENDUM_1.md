# E113 Addendum 1: implementation details left unspecified by PROTOCOL_E113 (written before any scoring)

No E113 model had been run or scored when this was written. These items fill gaps in the protocol; they change no metric, test, criterion or selection rule.

1. **Missing feature values.** A feature that is unavailable at O(t) is set to 0, i.e. "no adjustment", in training and in prediction. This covers:
   - news YoY before 2022-Q1 (no quarter four back);
   - a news quarter not yet complete;
   - the CPI before 2021-03;
   - rice YoY before 2022-Q2.

   Zero is the persistence value by construction (§2). The share of zero-filled values per feature over the evaluation origins is reported.
2. **P-FOOD and P-DFOOD use the latest two available CPI months** (at a standard issue date, months 1–2 of quarter t). P-DFOOD subtracts the mean of the two months three months earlier.
3. **DAMP ties.** The smaller φ wins, i.e. the one closer to persistence.
4. **AR1 ρ.** Pooled least squares through the origin of (h_i+1 − m_a) on (h_i − m_a), using the gap-1 pairs of consecutive known readings at O(t). Here m_a is the mean of the area's known readings at O(t). ρ is clipped to [0, 1]. The forecast uses the regime anchor of §2 and g = true horizon. With fewer than 4 gap-1 pairs, ρ = 1 (persistence).
5. **REP-C / REP-G** use the raw agri_supply share YoY (E112 definition), not the N-SUP composite. Lag 0; same SH fitting otherwise.
6. **Leakage test, news part.** Headlines are assigned to quarters by publication date, and quarter t ends the day before O(t). A headline dated on or after O(t) therefore cannot be in quarter t. The future-data test perturbs all news quarters > t, plus quarter t whenever its last headline is not before O(t). It also asserts in code that every used quarter's last headline precedes O(t).
7. **Eligibility of the SH and LR fits** also requires at least 4 pairs per feature column (12 pairs already satisfies this for SH-FULL's 8 features only if ≥ 32 pairs). Below that, the fit is still made: ridge is well-posed. For **LR**, an origin with fewer pairs than features + 2 gives LR = RW.

   This is the only effect of the item on LR; it does not change eligibility.
