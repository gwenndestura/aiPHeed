# OLD_NEWS, Addendum 1: de-duplication within each file (amends PLAN.md section 3)

**Written:** 2026-11-03, after the 2015–2020 scan and the failed feature check (commit `bb0478f`), and **before any
model was fitted or scored**. It was approved by you as option (a). PLAN.md (SHA-256 `0914a649…7d61`) is unchanged
except for this one rule.

## Why

PLAN.md section 3 contradicted itself. It said "concatenate the two frames and re-apply E85's de-duplication across
them", and it also required the rebuilt 2021-Q2..2026-Q3 features to equal E85's stored values exactly. Applied as
written, the run gave 19 of 22 quarters with differences up to 0.008 (`out/checks.json`), for two reasons:

1. **De-duplication across the two files** dropped **37 records of 2021+** whose `DocumentIdentifier` also occurs in
   2015–2020. They are evergreen pages that GDELT re-crawls (e.g. Britannica "Manila", travel blogs on Taal, LA Times
   archive pages). E85 de-duplicated within its own file only, so it kept them.
2. **6 records of the 2015–2020 file** fall on 2021-01-01 in Philippine time, the last 8 hours of 2020 in UTC. E85's
   2021-Q1 did not contain them.

## The amended rule (replaces the de-duplication sentence of PLAN.md section 3)

- The 2015–2020 file is loaded with the verbatim `load()` copy, which already de-duplicates **within** that file
  (earliest record per `DocumentIdentifier`). Its records dated **on or after 2021-01-01 PHT are dropped**: they
  belong to E85's window and E85's file.
- The 2021+ file is loaded with E85's `load()`, unchanged.
- The two frames are concatenated **without any de-duplication across them**: each file follows E85's own rule, as
  E85 did.
- Everything else in PLAN.md is unchanged, including the requirement that 2021-Q2..2026-Q3 equal E85's stored features
  (max |Δ| ≤ 1e-9).

## What was known when this was written

- **The amended rule makes 2021-Q2..2026-Q3 equal E85 exactly.** This was checked by computing features only; no
  model was fitted.
- **The 2015–2020 feature values exist** (from the failed run, in `out/gdelt_features_2015_2026.csv` of commit
  `bb0478f`). They were not used for any choice: no candidate, setting or rule was changed beyond the de-duplication
  above.
- **No forecast, metric or R1–R7 value of REF + G existed.**
ADDENDUM-SHA256: fc10f52f0d0984c29eded70e70ca46bc4f3b45353b5772db59e5446a0d411b50
