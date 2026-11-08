# v10 Stage 3: News feature menu (declared before any evaluation)

**Status:** declared. No news feature below has been evaluated under v10. Earlier experiments (E60, E64, E92, E116, E117) saw these data, so development results are non-confirmatory regardless.

Every window ends strictly before the issue date, through `as_of` on `published_ph`. Publication lag is 0 days (the publication timestamp is the availability time). All development news carries `RETROSPECTIVE_VINTAGE`.

**Missing means no coverage, never zero.** A cell with no article gives NaN features plus `N7_count = 0`.

| Id | Feature | Definition | Mechanism | Source for the technique |
|---|---|---|---|---|
| N1 | Food-stress share | Relevant province articles ÷ all province articles in the window; NaN if none | Stress reporting rises independent of coverage | Balashankar 2023 (FULL) |
| N2 | Topic shares | Share in price, supply, crop damage, typhoon, unemployment, relief. Topic model fitted **only on articles before the origin** | Named channels | van Wanrooij 2024 (PARTIAL: method only) |
| N3 | FSSI mean and dispersion | Confidence-weighted mean and SD of XLM-R scores among relevant articles | Severity | Project design; validation pending |
| N4 | Momentum | Change in N1–N3 over 1 and 2 months; fixed 3-month rolling mean | First differencing for stationarity | Balashankar 2023 (FULL) |
| N5 | Surprise | (N1 − trailing mean) ÷ trailing SD, past only, at least 8 months | News beyond the usual level | Project design |
| N6 | Broader-area news | N1 computed on articles with no province, kept separate | Regional or national shocks reach all provinces | Project design |
| N7 | Coverage control | Article count and source count | Stops "more news" reading as "more hunger" | Balashankar 2023 limit (FULL) |

## Selection

At most **6** news features enter any model, chosen **in-fold** by the existing stability rule (`app.forecasting.v4.models.stable`: ≥ 6 issues, |ρ| ≥ 0.30, sign stable in both halves). N7 enters only in the "with coverage controls" variant. Each feature keeps its five-group identity for SHAP.

## Timing hypotheses

| Id | Hypothesis | Test |
|---|---|---|
| i | News **leads** | News windows end before the issue, at Leads 1–4 |
| ii | News is **coincident** | Window ends at the end of the target quarter. Nowcast-only, never served as a forecast |
| iii | News adds **nothing** | Paired no-news vs with-news under the Stage 4 rule |

Binary label rule: **pending owner decision** (v9 `SPEC_RECONCILIATION.md` §e). `PREREGISTRATION.md` cannot be written before it.
