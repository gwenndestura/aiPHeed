# E83 data dictionary

All inputs are restricted to 2021-01 .. data published by 2026-10-14. O(t) = first day of quarter t+1. Target T43 is a constructed proxy (PROTOCOL section 2), not an observed food-insecurity rate. FNRI FIES (NNS 2025: CALABARZON 22.6% moderate or severe, region only, secondary reporting) is an external face-validity reference only; no municipal outcome exists.

| Variable | Driver | Source | Geography | Frequency | Value used at origin O(t) | Transformation | Expected sign | Role | Missing (Lead-2 eval origins) | Limitation |
|---|---|---|---|---|---|---|---|---|---|---|
| `F_last` | D1 prices | PSA CPI food YoY (OpenSTAT 0012M4ACP22) | province | monthly | quarter t-1 mean (complete) | mean of 3 published YoY | + | predictor | 0% | - |
| `F_now` | D1 prices | PSA CPI food YoY | province | monthly | months 1-2 of quarter t | mean of 2 published YoY | + | predictor | 0% | month 3 not yet published at O(t) |
| `gap_now` | D1 prices | PSA CPI food and all-items YoY | province | monthly | months 1-2 of quarter t | food minus headline YoY | + | predictor | 0% | - |
| `mom3` | D1 prices | PSA CPI food index | province | monthly | m0 vs m0-3 | 100 x log change | + | predictor | 0% | - |
| `F_hat_k` | D1 prices | PSA CPI food index | province | monthly | index to m0; base months 12 earlier | base-effect projection of target-quarter YoY (12-month drift) | + | predictor | 0% | drift misses policy and weather breaks |
| `G_hat_k` | D1 prices | PSA CPI food and all-items index | province | monthly | index to m0 | projected food minus headline YoY | + | predictor | 0% | - |
| `D_now` | D1 prices | PSA CPI food YoY | province | monthly | months 1-2 of quarter t | F_now minus five-province mean | + | predictor | 0% | relative only |
| `rice_whsl_yoy` | D1 prices | PSA wholesale rice prices | province | monthly->quarter | quarter t-1 | YoY % of quarter mean | + | predictor | 7% | wholesale, not retail |
| `tariff_yoy_regime` | D1 prices (policy) | EO 62 s.2024 (lawphil) | national | event | announced before O(t) | share of target months whose YoY compares post-cut with pre-cut | - | predictor | 0% | events list ends 2025-12 |
| `import_suspension_share` | D1 prices (policy) | EO 93/102 s.2025 | national | event | announced before O(t) | share of target months in force | -/+ | predictor | 0% | events list ends 2025-12 |
| `price_ceiling_share` | D1 prices (policy) | EO 39 s.2023 | national | event | announced before O(t) | share of target months in force | - | predictor | 0% | - |
| `food_emergency_share` | D1 prices (policy) | DA DC 3 s.2025 | national | event | announced before O(t) | share of target months in force | - | predictor | 0% | end date = stated window |
| `tc_count` | D2 climate | NOAA IBTrACS tracks (not PAGASA) | province (300 km) | event | quarter t | count of tropical cyclones within 300 km | + | predictor | 0% | exposure, not observed damage; 2026-Q3 incomplete |
| `tc_max_signal` | D2 climate | IBTrACS / PAGASA signal bands | province | event | quarter t | max wind-signal band | + | predictor | 0% | exposure |
| `tc_severe` | D2 climate | IBTrACS | province | event | quarter t | severe-cyclone flag | + | predictor | 0% | exposure |
| `enso` | D2 climate | NOAA CPC ONI | global index | monthly | quarter t-1 | El Nino 1 / neutral 0 / La Nina -1 | + (El Nino) | predictor | 0% | not local |
| `palay_yoy` | D3 agriculture | PSA palay production (OpenSTAT) | province | quarterly | quarter t-1 | YoY % | - | predictor | 0% | observed output, not damage |
| `corn_yoy` | D3 agriculture | PSA corn production | province | quarterly | quarter t-1 | YoY % | - | predictor | 0% | - |
| `fish_yoy` | D3 agriculture | PSA fisheries production | province | quarterly | quarter t-1 | YoY % | - | predictor | 0% | - |
| `aqua_yoy` | D3 agriculture | PSA aquaculture production | province | quarterly | quarter t-1 | YoY % | - | predictor | 0% | - |
| `ur_last` | D4 household economy | PSA LFS unemployment rate | national | monthly | quarter t-1 | quarter mean | + | predictor | 0% | national only; no provincial monthly LFS |
| `ur_yoy` | D4 household economy | PSA LFS | national | monthly | quarter t-1 | change vs t-5 | + | predictor | 0% | national only |
| `under_last` | D4 household economy | PSA LFS underemployment | national | monthly | quarter t-1 | quarter mean | + | predictor | 0% | national only |
| `remit_usd_yoy` | D4 household economy | BSP OFW cash remittances | national | monthly | quarter t-1 | YoY % | - | predictor | 12% | national only |
| `fx_yoy` | D4 household economy | BSP USD/PHP | national | monthly | quarter t-1 | YoY % | + | predictor | 0% | - |
| `H_last` | Hunger history (target component) | SWS Balance Luzon involuntary hunger | region | quarterly survey | latest round posted before O(t) | level % | + | lagged outcome | 0% | sampling error approx. +/-4-5 pp (Balance Luzon) |
| `H_chg` | Hunger history | SWS | region | quarterly | latest two posted | difference | + | lagged outcome | 0% | - |
| `H_age` | Hunger history | SWS | region | quarterly | latest posted | quarters since the reading | ? | data-quality | 0% | - |
| `news_market` | D5 news (v0, E40) | Google News RSS headlines | province | daily | quarter t, published before O(t) | share of articles hitting the trigger lexicon | + | predictor | 0% | headline-only; collected 2026-10-14 retroactively |
| `news_climate` | D5 news (v0) | as above | province | daily | as above | share | + | predictor | 0% | as above |
| `news_n` | D5 news (v0) | as above | province | daily | as above | article count | ? | coverage | 0% | corpus growth |
| `n3_fssi` | D5 news (E64 N3) | headlines + XLM-R intensity | province | daily | quarter t before O(t) | FSSI-v3 | + | predictor | 34% | - |
| `n3_market_rw` | D5 news (E64 N3) | headlines, classifier v2 | province | daily | before O(t) | recency-weighted count (30-day half-life) | + | predictor | 0% | not volume-normalised |
| `ev_adv_prices` | D5 news (E83 N2 events) | headlines + lead text where recovered | province shrunk to region (kappa 5) | daily | quarter t before O(t) | adverse events per 100 collected articles, severity-weighted | + | predictor | 0% | sparse: ~6 relevant articles per province-quarter |
| `ev_net_all` | D5 news (E83 N2) | as above | as above | daily | as above | adverse minus improving events, all drivers | + | predictor | 0% | as above |
| `ev_net_all_d` | D5 news (E83 N2) | as above | as above | daily | quarters t and t-1 | change in net adverse events | + | predictor | 0% | as above |
| `ld_cov` | D5 news (E83 N1 lead text) | publisher lead text (DA, BusinessWorld, DSWD FO4A, SunStar) | region | daily | before O(t) | share of relevant articles with recovered lead | ? | coverage | 0% | lead text mostly government press releases |
| `sim_p` | Structural (all) | derived from CPI and SWS | province | - | O(t) | Monte Carlo P(T43 HIGH at t+k) | + | derived estimate | 6% | independence of hunger and price assumed |
