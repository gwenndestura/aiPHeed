# E129 SWS regional target limitation

## What SWS provides

| Item | Fact |
|---|---|
| Published geography | Four areas: NCR, Balance Luzon, Visayas, Mindanao. CALABARZON is inside Balance Luzon, with Central Luzon, Ilocos, Bicol, MIMAROPA and others. |
| 2021+ observations | 20 quarters with a non-commissioned round (2021-Q2 .. 2026-Q3) |
| Precision | BL margin of error ±4 (1,500-respondent rounds) to ±6 (1,200) (E110) |
| Provincial breakdown | **None published.** Microdata in the SWS Survey Data Library would code respondent province. |
| Estimated respondents | About 100–230 CALABARZON respondents per round, about 20–75 per province. This is an estimate from the BL margins and population shares; the actual microdata are not held. |
| Implied precision | About ±11 to ±22 points per province-round. Hunger itself ranges 9–25 %. |
| Access | Request C (E87) was drafted and never sent. It needs the owner's signature. |

## Why E128's target cannot validate provincial forecasts

- **One observation per quarter.** One Balance Luzon value per quarter cannot tell Cavite from Quezon.
- **Copies are not data.** Assigning it to the five provinces creates 5 rows carrying 1 observation. Any provincial accuracy computed on such rows measures the regional forecast five times. It inflates sample size about 5× and says nothing about provincial differences.
- **T43c inherits this.** Its "provincial" HIGH is the regional hunger condition × the provincial price condition. All provincial variation comes from prices, so its provincial accuracy is a price-condition accuracy.
- **Balance Luzon is not CALABARZON.** It is a proxy even regionally.

## Kept

- SWS stays the **regional reference**: the regional prospective log (OUTCOME_GAP_RESOLUTION Track A) and E128's regional evaluation.
- **It is never copied to provinces.**

## Can SWS become provincial?

- **Only through microdata, which are not held.**
- Even then, quarterly province estimates would be dominated by sampling error.
- Pooling 4 rounds per province-year gives about 80–300 respondents (about ±6 to ±11). That yields a 5-province × about 5-year annual panel (2021–2025): 25 province-years.
- That is a possible *future* validation target, after access and a design-based estimation protocol (weights, design effect, small-area method) are approved.
