# E137 outcome audit: HFIAS categories, denominators and uncertainty (owner decision D-2)

| Item | FNRI 2015 FSS | ENNS 2018 | ENNS 2019 |
|---|---|---|---|
| Instrument | HFIAS, 9 items (FANTA; Coates et al. 2007), replacing the Radimer-Cornell tool used 2001–2011 | HFIAS, 9 items, "situations experienced in the past month", 30-day recall | same |
| Categories | food secure, mild, moderate, severe (Appendices 1–4) | the same four, provincial monograph tables | the same four, provincial slide decks |
| Denominator | respondent households: 41,282 of 48,178 eligible (85.7 %); CALABARZON 4,328 (88.7 %) | households, by province domain | households, by province domain |
| Design | PSA Master Sample, stratified 3-stage; fieldwork 20 Jul–30 Nov 2015 | rolling ENNS (2018, 2019, 2021) over 81 provinces + 33 HUCs | same |
| Printed uncertainty | SE and 95 % CI per category | 90 % CI per category | 90 % CI per category; 5 decks print only the any-level headline |
| Moderate-or-severe | moderate + severe; SE via design effect (largest of the three printed binary-split deffs) × p(1−p)/n, capped at the sum-of-SE bound | moderate + severe; SE = conservative sum of the printed SEs (n not printed) | same; **not derivable** for the 5 headline-only decks |
| National reference | 2015 national, mod-sev 53.8 % (SE 0.5) | **pooled 2018–2019** national (dissemination deck: secure 44.0, mild 13.3, moderate 29.8, severe 13.0 → mod-sev 42.8 %) | same |

**Decision on D-2.**
* Moderate-or-severe can be derived consistently in every row except the 5 headline-only 2019 decks, which are
  marked INSUFFICIENT and dropped.
* So moderate-or-severe is the primary outcome, and any level is the sensitivity analysis.

**Findings that change the earlier analysis.**
1. **The round-printed "Philippines" values are not national trends.** Each ENNS provincial report prints a
   "Philippines" value computed from that round's own province subset: any level 53.9 % (2018) and 64.1 % (2019),
   against 56.0 % pooled. The gap that hfias-1.0 treated as a national round shift is at least partly a difference
   in sample composition. E137 uses the pooled value and keeps the round values as a sensitivity check.
2. **The owner workbook mislabels one column.** Its ENNS "moderate-to-severe" column is FNRI's *moderate* category
   (already recorded for hfias-1.0). It is not used.
3. **Moderate-or-severe has no printed SE.** Summing the two category SEs ignores their negative covariance and makes
   the interval too wide. The design-effect method is used where n is printed (2015). With it, 25 of 78 provinces
   still have a 95 % half-width above 10 pp: these are INSUFFICIENT for class metrics, but are kept through their
   soft label.
4. **Domains differ slightly between surveys.** ENNS provinces exclude HUCs, which are separate domains. Whether the
   2015 province estimates include their HUCs is not stated. This is a limitation for the 2015 → ENNS comparison.

**CALABARZON rows (primary outcome, pooled reference).**

| Province | Survey | Mod-sev % | SE | Status |
|---|---|---|---|---|
| Batangas | 2015 | 43.5 | 2.8 | LOWER |
| Cavite | 2015 | 41.8 | 2.5 | LOWER |
| Laguna | 2015 | 41.4 | 2.6 | LOWER |
| Quezon | 2015 | 48.8 | 3.4 | NOT_DISTINGUISHABLE |
| Rizal | 2015 | 41.3 | 2.8 | LOWER |
| Laguna | ENNS 2018 | 26.2 | 1.3 | LOWER |
| Quezon | ENNS 2019 | 44.0 | 2.8 | NOT_DISTINGUISHABLE |
| Rizal | ENNS 2019 | 39.1 | 3.2 | NOT_DISTINGUISHABLE |
