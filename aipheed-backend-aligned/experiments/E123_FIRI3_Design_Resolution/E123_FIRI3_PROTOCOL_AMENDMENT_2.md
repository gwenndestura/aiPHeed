# FIRI3 protocol, Amendment 2: annual complete-year rule and supplementary scores (2026-10-31)

**Amends.** `E121_FIRI3_PROTOCOL.md` (8a431a9d…) as amended by Amendment 1 (4fd05309…). Both files stay unchanged. This file's SHA-256 is in `firi3.AMENDMENT_2_SHA256` and in `runner/AMENDMENT_2_SHA256.txt`.

**Authority.** The owner's E123 instruction:
- §3 DI-3: "if the latest complete year is unavailable at an issue date, use the most recent eligible complete year";
- §3 DI-1 and DI-2: implement two supplementary scores and a common-core score, keeping the six-indicator overall score.

## 1. Section 3.4 (rank5 features) is replaced

**Rule.** At issue O(t), take the latest reference year that:
- was published before O(t) (availability date < O(t)); and
- has values for **all five provinces**.

**Newer years.** A newer published year without all five provinces is **skipped**, not partly used, and is named in the record's note.

**Score.** (average rank − 0.5) / 5, as before.

**Statuses:**
- no published year at all: `unavailable_at_issue`;
- published years exist but none is complete: `incomplete_year`.

The reference year is always kept with the value. Annual values are never expanded into quarters.

## 2. Supplementary scores (new; the overall FIRI3 is unchanged)

| Score | Indicators | Scope | Completeness | Reading |
|---|---|---|---|---|
| **Current Conditions Score (CCS)** | FMA, AFP, CEC, FIS | Provincial and regional | ≥ ⌈2/3 × 4⌉ = 3 available | Equal mean. 0.5 = the 2021+ usual level of market, production, weather and news pressure. Chance bands as for FIRI3. **Not** a measure of hunger or household food consumption. |
| **Structural Vulnerability Score (SVS)** | EHS, PSV | Provincial only | Both available | Equal mean of two cross-province ranks. 0.5 = the middle of the five provinces. A position among provinces, not a change over time, so **no band**. |

**No regional SVS.** The regional EHS series (the national unemployment change and remittance decline) are short-term shocks, not structural conditions, and there is no regional poverty series. The regional SVS is reported `not_defined`.

## 3. Common-core scores (new; reporting only)

**Fixed core (FMA, AFP, CEC, EHS).**
- The mean of these four, computed only where all four are available.
- These are the four indicators present in the most computed provincial rows (50 of 75 in E122).
- Used to compare across quarters and provinces with one indicator set.

**Cross-province core per origin.**
- The indicators available for **all five** provinces at that origin.
- Score = their mean, computed if at least 3 indicators are common; otherwise `comparison_not_possible`.

**No filling.** A missing indicator is never filled or set to 0.

## Unchanged

- the six indicators and 34 features;
- directions, normalization, Amendment 1;
- the overall FIRI3 formula, completeness and bands;
- equal weights.
