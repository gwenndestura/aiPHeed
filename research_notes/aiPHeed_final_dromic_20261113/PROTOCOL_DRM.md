# PROTOCOL_DRM — DSWD DROMIC disaster impact / assistance and 2020 SAP as provincial predictors (written 2026-11-13 BEFORE any DROMIC value is compiled or merged with an outcome)

## Question
Do post-disaster impact and assistance (and conflict displacement), measured from genuine DSWD DROMIC reports published before each forecast origin,
predict whether a province's food insecurity stays high or recovers between surveys — in transitions that do not involve 2021 — and if so, do they
improve detection of absolute HIGH (HFIAS mod+sev >= 50 %) provinces against FINAL and FINAL-LG?

## Feasibility established before compiling (evidence in `evidence/SOURCES.md`)
- 2013-2015 / Typhoon Yolanda: NOT in DROMIC (its 2014-2016 archive holds 2014 TS Glenda, Luis, Mario, Ruby only; the 2015/2016 folder links return
  no listing). No provincial DSWD Yolanda assistance table was found; NDRRMC refuses automated access (HTTP 403). The requested 2013->2015 test
  therefore cannot be run with provincial assistance data, and no substitute values will be invented.
- DROMIC 2016 onward: per-event Word terminal/numbered reports with provincial tables (affected families/persons, displaced inside/outside
  evacuation centres, damaged houses totally/partially, cost of assistance DSWD/LGU/NGO/other), each dated "as of" in its file name.
- SAP 2020: no provincial table is published (only an FOI request; the owner forbids data requests). Published area coverage of the 2nd tranche only.

## Data rules
- Window for a transition = (anchor survey reference quarter, forecast origin]; T2/T3/T4 anchors are 2015-Q3; origins are the Lead-1 issue
  quarters of the ENNS 2018 / 2019 / 2021 folds. Cut-off = first day of the origin quarter.
- Events: DROMIC incident pages whose titles contain typhoon / tropical / storm / depression / LPA / low pressure / monsoon / habagat / flood /
  flashflood / landslide / shear line / trough (hydro-meteorological family), or "armed conflict" (conflict family). Event date inside the window.
- Report used per event and window: the latest report whose as-of date is before the cut-off. Province rows only (municipal rows ignored); names
  matched to the project province keys; unmatched names logged.
- Known gap (uniform, recorded): 2015-Q3 to 2015-12 events (e.g. Lando, Nona) are missing for every 2015-anchored window.
- Normaliser: PSA 2015 census population (released 2016, before every origin used).

## Features (fixed now; log1p of per-1,000-population or per-capita values, summed over events in the window)
 D1 aff        affected persons (hydro-met) per 1,000
 D2 dmg        totally damaged houses (hydro-met) per 1,000
 D3 disp       displaced persons, inside + outside ECs, cumulative (hydro-met) per 1,000
 D4 aid        cost of assistance, all sources (hydro-met), PHP per capita
 D5 aid_aff    cost of assistance per affected person (hydro-met; 0 if none affected)
 D6 conflict   displaced persons from armed conflict per 1,000
 SAP2          1 if the province (province-wide) was in the 2020 SAP 2nd-tranche coverage list; descriptive only (no historical analogue, cannot be
               learned or confirmed; not a model input in this protocol).

## Confirmation test (never uses 2021)
 Transitions T2 (2015->2018, n 22) and T3 (2015->2019, n 25). Outcome dz = change in national-relative position (logit), as in the detection study.
 Pre-specified directions: D1, D2, D3, D6 -> +dz (worsening); D4, D5 -> -dz (assistance aids recovery).
 Partial Spearman controlling for the starting relative position (and for D1 when testing D4/D5); Fisher combination over T2, T3; Holm over the
 six features. CONFIRMED = Holm p < 0.05, predicted sign, same sign in T2 and T3. Secondary (absolute-label) check: logistic association with
 staying >= 50 % among provinces starting >= 50 % in T2+T3 (reported, not decisive). T4 (2021) association reported descriptively, never used to select.

## Model step (only if >= 1 feature is CONFIRMED)
 ATTR-D = ATTR (PROTOCOL_ATTR, unchanged) + confirmed D features; HYB-D = FINAL-LG level + ATTR-D ranking. Lead 1, FINAL's folds. Evaluated on the
 absolute label (primary) and relative label, every round + pooled, all 8 metrics, confusion matrices, LG seeds, training-transition drops, against
 FINAL, FINAL-LG, HYB, ATTR. Replacement of FINAL is recommended only if HYB-D meets all 8 targets in 2018, 2019 AND 2021 and pooled, with pooled
 Brier <= FINAL-LG's, every seed. If no feature is confirmed: no new model is built and the data are reported for prospective use.
 Any pass is retrospective (2021 viewed many times) and is not independent validation. Nothing enters production or the dashboard.
