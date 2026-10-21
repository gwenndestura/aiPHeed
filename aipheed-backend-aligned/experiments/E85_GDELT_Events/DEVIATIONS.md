# E85 deviations from PROTOCOL.md

## D1 — V1 GKG columns, to fit the free query quota (2026-10-21, before any row was seen)

- **What happened.** The frozen query (V2Themes, V2Locations, V2Counts; 1.073 TiB) was refused before scanning:
  `403 quotaExceeded`, "free query bytes scanned". Project aipheed-gdelt has no billing account, so it runs on the
  monthly free tier, and part of this month's tier appears to be used already. Nothing was scanned or billed.
- **Change.** `runner/gdelt_query_v1.sql` uses the V1 columns Themes, Locations and Counts, aliased to the V2 names.
  The filters and the date window are identical. The dry run gives 0.543 TiB.
- **What V1 loses.** Character offsets inside the text. Theme codes, location names, the country code and the
  count types are the same.
- **What is unchanged.** Features, arms and rules.
