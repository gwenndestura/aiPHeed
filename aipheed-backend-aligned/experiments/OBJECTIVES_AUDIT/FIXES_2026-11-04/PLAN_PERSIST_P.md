# Probabilistic persistence baseline (PERSIST-P): pre-registration (fixed before any score, 2026-11-04)

**Scope:** Objective 4 fairness only. No candidate model is refitted; the stored C-b, C-E6 and C-B6 forecasts are
scored again against one changed comparator.

## Problem

The stored persistence baseline is `PERSIST = 1[latest published BL reading > 11.3]`, a 0/1 forecast. Its Brier score
equals its error rate (0.339), because it cannot express uncertainty. Every candidate gives probabilities, so the
comparison favours the candidates for a reason unrelated to forecasting skill. A fair persistence baseline must carry
forward the latest reading **and** its uncertainty.

## Definition (existing code, no new parameter)

PERSIST-P(t, k) = `hr_lib.pi_h4l(d, t, k)["pi"]` on the long record (`min_q=None`):
- Φ((h_last − 11.3) / σ), where h_last is the newest Balance Luzon reading published before O(t);
- σ = RMSE of latest-reading errors pooled over the four SWS areas at the true horizon (target quarter − quarter of
  h_last), from readings published before O(t) only; fewer than 8 pooled errors → hr_lib's H0 fallback.
- If no reading is known, use PERSIST's own fallback (the stored PERSIST value).

This is the same function the candidates already use as their input `pi_H4L`, so it adds no information the
candidates lack. Same origins, labels (`V.area_labels`, BL, H > 11.3), leads 1–2 and verdict quarters as the stored
families.

**Check before scoring:** PERSIST-P ≥ 0.5 gives the same call as PERSIST at every row (except where h_last = 11.3
exactly); the count of differing calls is reported.

## Tests

For each of C-b, C-E6 and C-B6:
- **Primary family (14 tests):** the stored 7 comparators with PERSIST replaced by PERSIST-P, leads 1–2; paired Brier,
  `phase_c._paired` (one-sided cluster bootstrap, `H.rp()` seed 2036), NLP-only comparators on the news era as
  stored; Holm over 14 (`run_iv2.holm`).
- **Reference:** the stored family with hard PERSIST, recomputed with the same code; it must equal the stored
  `holm_family_14` p-values (difference < 1e-9) or the run stops.

Also reported: PERSIST-P's own accuracy, Brier and AUC at leads 1–2.

## Decision (fixed)

The thesis reports PERSIST-P as **the** persistence comparator for Objective 4, and the hard 0/1 version as a
secondary line, whatever the result. If a candidate's advantage over PERSIST-P is not significant after Holm, the
thesis says so. Nothing else is changed, and no candidate is refitted or re-selected after seeing these results.

**Reported whatever the result.**
PLAN-SHA256: b3e8b02d96184aa9b806315812783344f29e57d442e356e3acd76419227588f9
