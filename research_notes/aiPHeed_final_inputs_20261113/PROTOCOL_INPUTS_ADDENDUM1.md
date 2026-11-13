# PROTOCOL_INPUTS addendum 1 (written 2026-11-13 before the arms below are fitted or scored; base protocol sha 4cb830c6 unchanged)

New official data: PSA OpenSTAT regional accounts by industry, Agriculture, forestry and fishing (AFF), all 17 regions, 2000-2025
(backend/app/hcw/grdp_industry.py -> backend/data/hcw_official/raw/psa_grdp_aff_by_region.csv). REGIONAL values: every province takes its
region's value. Release rule: year Y usable from Q3 of Y+1 (the existing hh_grdp_* rule, app.e154.model.available_year).
  aff_g      AFF real growth (%), constant 2018 prices, latest usable year. Monotone sign -1 (sector growth -> lower risk).
  aff_share  AFF share of GRDP (%), current prices, latest usable year. Sign 0.

Arms (same engine, folds, leads, seeds, evaluation and decision rule as the base protocol; they join the same comparison):
  N-AFF    B0 + aff_g, aff_share in the candidate pool.
  N-ALL    N-OFF + aff_g, aff_share in the candidate pool.
  N-ALL-F  N-ALL with every official column forced in (N-OFF-F set + aff_g, aff_share).
