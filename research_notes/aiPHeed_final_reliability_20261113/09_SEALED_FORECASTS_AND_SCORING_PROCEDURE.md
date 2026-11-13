# 09 — Sealed forecast artifacts and prospective scoring procedure

## 1. Was FINAL frozen and were 2027-Q1 to 2028-Q1 forecasts sealed? **No.**
- PROTOCOL_REL §Freezing allows a freeze and a new seal only if G1–G10 pass at Lead 1.
- Lead 1 fails G3: 2021 HIGH recall is 1/4.
- So FINAL was **not** frozen as a validated model, and **no 2027-Q1–2028-Q1 seal was created.**
- Sealing an unvalidated model under the "validated" label would misstate its status.

## 2. Existing prospective seals (unchanged, re-verified 2026-11-13)

| Seal | Contents | sha256 | Status |
|---|---|---|---|
| `aiPHeed_hcw_final_optimization_20261112/evidence/sealed_enns2022_candidates.json` | FINAL (and BASE / IMPUTE / RATE) forecasts for ENNS 2022: 78 provinces, Leads 1–2. Probabilities, classes, issue details. FINAL L1: 10 HIGH / 68 LOW | `4ad9267fdc8256bbc8fb2eaff85a4e63b0fa299744e18176ff9765741c494c3a` | Sealed 2026-11-12 09:11 UTC, before any 2022 outcome was available locally |
| `aiPHeed_final_7of7_20261113/evidence/sealed_enns2022_final_mix.json` | FINAL, FINAL-ET and FINAL-ETMIX for ENNS 2022 | `71ebe1428251980911c55a8a11e565be798684781d217ee3d1457bba4f1d2370` | Sealed 2026-11-12 23:45 UTC |

The live 2027-Q1/Q2 experimental issue (`aipheed_hcw/backend/data/etmix/out/live.json`, built 2026-11-13) is **not a seal**: it is uncommitted and unhashed. It holds FINAL probabilities, classes and exact TreeSHAP explanations for the five CALABARZON provinces.

## 3. Procedure for the next FNRI provincial survey
1. **Obtain** FNRI provincial HFIAS moderate + severe percentages, with SEs or CIs, for the round. The likely source is the 2022 ENNS follow-up (20 provinces / HUCs) or a later round.
   - Use HFIAS only.
   - **Never use FIES or Radimer.**
   - Record the source file and its sha256.
2. **Verify the seal before opening the outcomes.** `sha256sum sealed_enns2022_candidates.json` must equal `4ad9267f…c3a`.
3. **Match** provinces with the same key normalisation as `app/e147/labels.py`. List every unmatched area with its reason, using the categories in `01_DATA_AUDIT.md` §3.
4. **Score once** at the sealed 0.50 cut-off, Lead 1 and Lead 2 separately:
   - accuracy, HIGH precision, recall and F1, macro F1, BA, PR-AUC, Brier;
   - against always-LOW and persistence (the province's latest released round at the seal date);
   - with province-bootstrap CIs.
   - Re-use `scripts/rel_eval.py`'s `core`, `calib` and `paired` functions unchanged.
5. **Apply the PROTOCOL_REL gates** G1–G8 to the new rows. G9 does not apply, because there is one round.
   - Report the expected number of wrong-side labels from the published SEs.
   - Report the result whether it passes or fails.
6. **No refit, re-threshold or variant selection** may happen before step 5 is written up.
   - If the result motivates a change, write a new protocol and seal it before the following round.
7. **Freezing:** only if step 5 passes and G3's per-round recall holds, freeze FINAL as follows:
   - commit `app/hcw/final_engine.py`, the fold builder and the data hashes;
   - tag the commit;
   - then seal the next issue (2027-Q1 to 2028-Q1, Leads 1–5) with probabilities, classes, TreeSHAP explanations, the training cut-off, configuration strings and sha256.
