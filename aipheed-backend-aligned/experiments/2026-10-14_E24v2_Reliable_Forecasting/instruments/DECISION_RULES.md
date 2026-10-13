# Predeclared decision rules for H4 and H5 (written before any response is collected)

Chapter I does not define "favorable" or "consistent". The rules below are the researchers' proposal and need **adviser approval before data collection**. They must not be changed after any response is seen.

## Data handling

| Situation | Rule |
|---|---|
| Valid response | Consent given (CONSENT = "Yes"), and at least 80% of the rated items answered. |
| Missing items | Left missing. Never imputed. |
| Characteristic score per respondent | Mean of that respondent's answered items in the part (FS, AC, US). |
| Minimum respondents | ≥ 30 valid responses are needed before any decision. Otherwise the result is "insufficient responses". |

## H5. Favorable ISO/IEC 25010 ratings

**Null hypothesis.** aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings.

**Reject H5 only if, for EACH of FS, AC and US, both conditions hold:**

1. **Typical rating.** The median respondent characteristic score is ≥ 4.0 ("agree").
2. **Above neutral.** A one-sided Wilcoxon signed-rank test of respondent scores against 3.0 (neutral) gives p < 0.05, after Holm adjustment across the three characteristics.

**Also reported, descriptively:**

- the mean, SD and 95% bootstrap CI for each characteristic;
- the per-item distribution;
- Cronbach's α per part.

**Partial result.** If one or two characteristics pass, report which ones. H5 as a whole is not rejected.

## H4. Ranking consistency with evaluator assessments

**Null hypothesis.** The disaggregated rankings will not be consistent with DA Region IV-A evaluators' assessments.

### Primary measure: top/bottom agreement

For each valid respondent and their province:

- `hits_top` = the number of their three "most vulnerable" LGUs (RK2) that fall in the system's top third of that province's ranking;
- `hits_bottom` = the number of their three "least vulnerable" LGUs (RK3) that fall in the system's bottom third;
- `agreement` = (hits_top + hits_bottom) / 6.

Under random ranking, the expected agreement is about 1/3.

**Reject H4 only if both conditions hold:**

1. **Agreement test.** A one-sided Wilcoxon signed-rank test of respondent agreement against 1/3 gives p < 0.05.
2. **Typical rating.** The median RK1 rating is ≥ 4.0.

### Reported alongside

- Per-province results.
- Agreement **under a density-only ordering**. 126 of 142 LGUs carry a province-mean poverty value, so most within-province order comes from population density; this shows how much of any agreement density alone would give.
- The RK4 open-ended themes.

### Ranking version

The ranking shown must be the one recorded in the session log. It must be identical for all respondents of a province.

## What is NOT allowed

- Simulated, imputed or researcher-entered responses.
- Dropping respondents after seeing their answers. Exclusions use only the validity rules above.
- Changing the thresholds above after data collection begins.
