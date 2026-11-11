# E196 confirmation test on ENNS 2022 (fixed before any 2022 label is seen). Local only.

Written 2026-11-11. Purpose: an independent, one-time test of whether E196 really improves on E184. The 72 historical
outer rows cannot settle this: they are small and were reused across E151–E196.

## Sealed forecasts
- `backend/data/e184/out/sealed_enns2022.json`: E184, the pre-registered model, sealed 2026-11-10.
- `backend/data/e196/out/sealed_enns2022.json`: E196 (this seal).
  - Both use the same frames, from `app.e168.enns2022_seal`.
  - E196's file records the SHA-256 of E184's seal and reproduces E184's sealed probabilities (rank-1 configuration,
    draws 17901–17905).
- **The SHA-256 of each seal is recorded when it is created.** Neither file may be regenerated or edited afterwards.
  If a seal is missing or its hash differs, the test is void.

## Labels
- **Source:** DOST-FNRI ENNS 2022 provincial results, HFIAS moderate + severe, with standard errors, in the same
  definition as `data/hfias/clean/enns_hfias.csv`.
- **Comparable rows only:**
  - provinces, not cities;
  - the same HFIAS definition;
  - reference year 2022.
  - Rows that fail the comparability check are listed and excluded before scoring. Exclusions are based on the label
    source only, never on forecast errors.
- **Truth:** y_high = the estimate ≥ 50 %; q_true = Φ(logit-scale estimate / SE), as in `e158/out/oof.csv`.

## The test (run once, Leads 1 and 2, on the same rows for both models)
1. **Primary: Brier difference, E196 − E184, pooled over Leads 1–2.** 95 % region-cluster bootstrap CI (2,000 draws,
   seed 2022). Both leads of a province stay in one region cluster.
2. **Secondary:**
   - accuracy, false alarms and misses per lead;
   - exact McNemar per lead (Holm over the 2 leads);
   - pooled accuracy difference with a region-cluster CI.

## Verdict (wording fixed now)
- **"E196 confirmed better than E184"** only if the primary CI upper bound is < 0 **and** pooled accuracy is ≥ E184's.
- **"E196 confirmed at least as good"** if the primary CI includes 0 and pooled accuracy is ≥ E184's − 1 province.
- **Otherwise "E196 not confirmed; E184 stays".**
- The 80 % target is reported per lead but does not change the verdict.
- No re-fitting, no threshold change and no row selection based on results. The test is reported whatever it shows.
