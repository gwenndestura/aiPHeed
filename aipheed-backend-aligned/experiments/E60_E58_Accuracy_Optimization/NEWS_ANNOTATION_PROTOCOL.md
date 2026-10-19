# News annotation protocol (E60)

**Written before any article is sampled or labelled.**

## 1. Purpose

The protocol measures whether the news pipeline itself works:
- relevance;
- trigger category;
- province attribution;
- dates;
- repeats.

It does so **separately** from whether news improves the forecast.

## 2. Unit and fields

**Unit:** one article as stored (title, link, publisher domain, publisher publication date). The corpus has **no body text**. Google News RSS gives titles only, so annotation is from the title, the domain and the date. Where a title is insufficient, the label is "cannot tell".

| Field | Values |
|---|---|
| `relevant` | 1 = describes or reports a condition, event or measure bearing on household food access in CALABARZON or a CALABARZON province (prices, supply, crop or fishery damage, jobs or income, remittances, relief because of a shock); 0 = otherwise; 9 = cannot tell |
| `trigger` | market / climate / fish_kill / employment / ofw_remittance / other_food (relevant but none of the five, e.g. nutrition programme) / none |
| `province_true` | PSGC code of the CALABARZON province the article is about; `REGION` (CALABARZON-wide); `NATIONAL` (Philippines-wide, no CALABARZON focus); `OTHER` (outside CALABARZON, e.g. Quezon City or Rizal Park); `UNKNOWN` |
| `kind` | event (something happened) / announcement (a government or agency measure) / forecast (a projection or warning) / opinion / unrelated |
| `event_in_title_date` | an event date stated in the title (YYYY-MM or blank); otherwise blank |
| `repeat` | 1 if the title reports the same event as an earlier sampled title (same event, other outlet) |

**Common false positives to label 0 (irrelevant):**
- restaurant or food promotions;
- recipes, festivals, tourism;
- ordinary crime;
- political stories that mention rice or prices only in passing;
- sports;
- "Rizal" the national hero, Rizal Park, Quezon City;
- generic national inflation releases with no provincial bearing. These are labelled `relevant=1`, `province_true=NATIONAL`, so they count as relevant but not provincially attributable.

## 3. Sampling (seeded, before annotation)

- **Frame:** strata A, C and D are drawn from the E31 corpus (8,320 titles); stratum B is drawn from the E60 trigger corpus (N2) once its collection is complete. Both cover 2021-01-01..2026-09-30. Duplicates are removed by `article_key`.
  - *Amendment, recorded before any sampling:* the E60 collection runs for several hours, so A/C/D are sampled and annotated first.
- **Strata** (seed 60), each split 50/50 at random into **DEV** and **EVAL**:

| Stratum | Size | What it covers |
|---|---|---|
| A | 60 | the deployed keyword classifier fires (any trigger) |
| B | 40 | the E60 trigger queries returned it, but the deployed classifier does not fire (a potential recall gap) |
| C | 30 | E31 corpus, no keyword hit (negatives, background) |
| D | 20 | geographically ambiguous: no province attributed, or the title mentions Quezon City, Rizal Park or Jose Rizal |

- **Total:** 150 titles, 75 DEV and 75 EVAL.
- The **EVAL half is annotated first** and frozen (sha256 recorded) **before** any classifier change is written. DEV is used to develop classifier v2. EVAL is used once, to compare v1 and v2.

## 4. Annotator

**The annotator is Claude (AI), working from the title, domain and date only. It is not a human annotator.**
- Every label is marked `annotator=claude-ai`.
- The researcher (or a DA IV-A reviewer) should verify the EVAL file before the figures are cited. The column `human_verified` is left blank for that purpose.
- No label is invented beyond what the title supports.

## 5. Metrics

**On EVAL, for classifier v1 (deployed keywords) and v2 (E60):**
- relevance precision, recall and F1;
- per-trigger precision and recall (support permitting);
- province-attribution accuracy against `province_true`, on CALABARZON-relevant rows.

**Error analysis:** the most common false-positive and false-negative patterns.

Small supports (n < 10) are reported as counts, not rates.
