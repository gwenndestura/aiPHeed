# Data Availability

The approved methodology is implemented in full in this folder. This document
records what data the approved pipeline actually has, where it came from, and
which gaps remain. Nothing here proposes a methodology change.

---

## 1. The SWS hunger series — recovered 2026-09-23

### What the approved label needs

Equation 3 defines the primary training target:

```
stress(p,t)       = sws_hunger(t) + 2 · (food_cpi_yoy(p,t) − regional_mean_food_cpi_yoy(t))
label_stress(p,t) = 1 if stress(p,t) > global_median(stress) else 0
```

Section 3.3.2.6 defines the window as 120 province-quarter pairs — 5 provinces ×
24 quarters, 2020-Q1 through 2025-Q4.

### The problem, and how it was solved

SWS migrated to a new website during 2025–26. Its Hunger category holds exactly
four releases, all from December 2024 onward; the site carries 94 posts in
total. A table of 24 quarters that had previously been hard-coded here was
removed on 2026-09-01 after seven quarters were checked against press releases
and none agreed. For a time the composite label therefore covered **4 quarters,
20 of 120 rows**, which is below what Algorithms 3 and 4 can execute on.

The archive was then recovered from the Wayback Machine. The previous SWS site
(`www.sws.org.ph/swsmain/artcldisppage/`) is archived, **including its article
index** — `generalArtclSrchPage` with `swityp=3`, which is the Hunger category.
That index yields every hunger release SWS published. Each release was fetched
and its Balance-Luzon figures read from the release text.

| | Before | After |
|---|---|---|
| Quarters with an SWS figure (in window) | 4 of 24 | **19 of 24** |
| Labelled province-quarters | 20 of 120 | **95 of 120** |
| Class balance | 10 / 10 | **48 / 47** |
| Algorithm 3 (needs ≥10 quarters) | blocked | runs |
| Algorithm 4 (needs ≥13 quarters) | blocked | runs |

### How the figures were validated

Every value in `SWS_BAL_LUZON_VERIFIED` is stated outright in the release cited
beside it. Nothing is interpolated, projected, averaged across releases or
carried forward. Three independent checks were run:

1. **Against the values already verified by hand.** 2024-Q3 and 2024-Q4 were
   re-derived from the archive and matched exactly — total, Moderate and Severe
   alike (18.1 / 13.0 / 5.1 and 25.3 / 16.6 / 8.7).
2. **Internal arithmetic.** SWS reports Total, Moderate and Severe separately.
   Moderate + Severe reproduces Total to within rounding for all 23 quarters
   that publish both — **zero mismatches**. These are three independently read
   numbers per quarter, so agreement is a real check on the reading.
3. **Overlap between consecutive releases.** Each release restates the previous
   quarter's figure in its comparison sentences; these agree with that quarter's
   own release wherever both exist.

`docs/provenance/sws_hunger_sources.json` records, for every quarter, the
figures, the survey round, the source URL and the sentence the numbers were read
from.

### Quarter assignment

A round is filed under the calendar quarter it was **fielded** in. This is the
convention already used in the fetcher, and Rule 3 (No Look-Ahead Bias) requires
it: SWS's own quarter label sometimes lags the fieldwork, and filing the round
fielded 28 April – 2 May 2021 as "2021-Q1" would let a label be set by data
collected after that quarter had closed.

COVID scheduling put two rounds in one calendar quarter three times — 2020-Q3,
2021-Q2 and 2022-Q2. Both rounds are emitted and the quarter's value is their
mean, which `label_generator` already computes through its existing
`groupby("quarter").mean()`. No new logic was added for this.

### The five quarters that remain absent

| Quarter | Why |
|---|---|
| 2020-Q1 | No round fielded. The pandemic mobile-phone surveys begin in May 2020; the preceding round is December 2019. |
| 2021-Q1 | The round SWS labels *First Quarter 2021* was fielded 28 April – 2 May 2021, so it falls in 2021-Q2. |
| 2022-Q1 | The round SWS labels *First Quarter 2022* was fielded 19–27 April 2022, so it falls in 2022-Q2. |
| 2025-Q2 | No hunger round published; the series runs March 2025 straight to November 2025. |
| 2025-Q3 | Same. |

These stay absent and are never estimated. `label_generator` drops them, and the
median threshold of Equation 3 is taken over the 95 surviving rows, which keeps
the class split balanced by construction.

---

## 2. A property of the approved label worth recording

SWS publishes hunger at the Balance-Luzon stratum, not by province. The
`sws_hunger(t)` term of Equation 3 is therefore **identical across all five
CALABARZON provinces in a given quarter**. The proposal acknowledges this: the
SWS component "will lack province-level resolution, as it reports only across
four broad geographic domains; CALABARZON provinces will be treated as part of
Balance Luzon, introducing aggregation error that is acknowledged."

A consequence follows arithmetically: within a single quarter, the only term
varying across provinces is `2 · (food_cpi_yoy(p,t) − regional_mean(t))`. All
province-level discrimination in `label_stress` comes from food CPI deviation.

A previous implementation treated this as grounds to withhold `food_cpi_yoy`
from the model. That is a methodology change, and this folder does not make it:
Equation 5 names `CPI_dev(t)` as a model input and Section 3.3.2.7 retains food
CPI deviation among the final twelve features, so the model receives it, as
approved. The baselines in `evaluator.py` receive it too, so the comparison
stays fair. `pct_total_hunger` itself is excluded from the feature matrix, which
the proposal's own design implies.

The property is recorded here rather than acted on. It belongs in the
limitations discussion, not in a silent code-level deviation.

---

## 3. Article scores

`corpus_geocoded.parquet` previously carried `food_insecurity_score` values from
a superseded gate — 250-character premise, maximum over five of the ten
hypotheses, plus an added 0.20 margin. Those are not Algorithm 1 scores, and the
FSSI built on them is not the approved FSSI.

The corpus was rescored under the restored Algorithm 1 — 512-character premise,
maximum entailment probability over all ten bilingual HungerGist hypotheses,
0.30 as the only threshold — using the real `joeddav/xlm-roberta-large-xnli`
model. The pass was checked against `classifier.score_article` before the corpus
was written, so the rescoring path cannot have diverged from the module the
pipeline uses.

Result: **1,684 articles rescored, 558 clear the 0.30 threshold (33.1%)**,
against 196 under the superseded gate — a 2.8x increase in retained articles.
That is the expected direction: a maximum over ten hypotheses cannot be lower
than a maximum over five of them, the premise is twice as long, and the 0.20
margin gate that rejected articles regardless of score is gone. Equation 2's
`N` — the retained article count per province-quarter — rises accordingly, so
the FSSI is computed over materially more evidence than before.

---

## 4. Other quantity differences

These are ordinary quantity differences. The methodology producing them is
unchanged, and the task permits the amounts to differ from the proposal.

| Quantity | Proposal | Actual |
|---|---|---|
| Articles collected | 17,791 | 6,085 |
| Articles geocoded to a province | — | 1,684 (1,111 inside 2020-Q1–2025-Q4) |
| Province-quarter cells with ≥1 article | 119 of 120 | 119 of 120 |
| Cells flagged LIMITED_SIGNAL (<5 articles) | 77 of 119 | 30 of 119 |
| Province alias lookup entries | 92 | 135 |
| Government datasets | ~2,732 | all approved sources present |
| LGUs in the vulnerability table | 142 | 142 |
| Labelled province-quarters | 120 | 95 |

None of these changes a method. The corpus is collected by the same three
fetchers over the same window with the same URL-hash deduplication; geocoding
uses the same three-stage PSGC matching at the same fuzzy threshold of 85; the
LIMITED_SIGNAL rule is the same five-article cut.
