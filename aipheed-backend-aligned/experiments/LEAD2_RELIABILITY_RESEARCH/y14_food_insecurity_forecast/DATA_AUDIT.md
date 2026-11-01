# Y14 data audit: food-insecurity outcomes and driver signals

**Acquired:** 2026-10-29, PSA OpenSTAT API (`runner/acquire.py`; raw files and `data_acquired/manifest.json` with URL, query, UTC time and SHA-256).

**Reused, read-only:** `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/` (CPI, ONI, IBTrACS, LFS, SWS four-area rounds) and `backend/data/inputs/` (SWS 2021+, LGU vulnerability).

**Point-in-time construction:** `runner/indicators.py` → `out/indicators.csv`. No outcome is read there.

## 1. Outcomes

| Series | File (SHA-256 prefix) | Coverage obtained | Verdict |
|---|---|---|---|
| SWS involuntary hunger, four areas | `sws_area_rounds_full.csv` (existing) + `backend/data/inputs/sws_rounds.csv` (2021+) | 1998-Q3 .. 2026-Q3, quarterly with gaps | **Primary outcome.** Release dates: verified for 2021+. Before 2021: label month end + 60 days (E114 rule; 11 checks found lags of −8 to 43 days, so the rule is conservative). |
| FIES moderate or severe food insecurity (SDG 2.1.2) | `fies_sdg212_region.csv` (4ae91823) | Region IV-A: **1 value** (19.1%); Philippines: 3 values | Not usable as a time series |
| Subsistence incidence, families, by province | `subsistence_families_2006_2015.csv` (fb4ac043), `subsistence_families_2018_2023.csv` (8c0ec320) | 2006, 2009, 2012, 2015, 2018, 2021, 2023 | Not usable as a Lead-2 target. CALABARZON provinces 2018/2021/2023 range 0.2–4.7%, with CV 17–59% (e.g. Laguna 2018: 0.2%, CV 59%). |

## 2. Driver signals (FIRI v2 indicators and the point-in-time analogs used for 1997+)

Lag rule: the newest reference period allowed at issue date O(t), the first day of quarter t + 1.

| Driver label | FIRI key: served indicator | Analog used here (1997–2026) | Observation or proxy | Lag rule at O(t) | Coverage of the analog |
|---|---|---|---|---|---|
| **Market / Prices** | A1: LightGBM price-pressure probability | – | – | – | **Unavailable before 2021** (model trained on 2021+) |
| | A2: provincial headline inflation vs P60 | Region IV-A all-items CPI YoY, mean of m0−2..m0 | Observation, at **regional** level | CPI: m0 (month 2 of quarter t) | 1997–2026 |
| | A3: wholesale rice price YoY | Region IV-A **retail** rice CPI YoY at m0 | **Proxy** (retail, not wholesale) | m0 | 1997–2026 |
| **Climate Stress** | C1: PAGASA El Niño alert in force | ONI of the season ending m0−1 ≥ 0.5 | **Proxy**: an ONI threshold, not the official alert. No alert history exists before 2021. | ONI: early next month | 1997–2026 |
| | C2: typhoons within 300 km of the province | Tropical cyclones in the PAR, quarter t−1 | **Proxy**: national PAR count, not province distance | Real time | 1997–2026 |
| | C3: palay/corn production drop | −min(palay YoY, corn YoY), Region IV-A, quarter t−1 | Observation (regional) | PSA, about 6 weeks after quarter end. Pre-2021 dates **not verified**. | 1997–2026 |
| **Fish Kill** | C4: fisheries production drop | −(total fisheries volume YoY), Region IV-A, quarter t−1 (`fisheries_volume_subsector.csv`, 1f914e33) | **Proxy.** Fisheries production is **not** fish-kill incidents. No historical BFAR fish-kill incident series was found in the project or on OpenSTAT. | Same as C3 | 1997–2026 |
| **Employment** | E1: unemployment change (national) | National LFS unemployment, YoY difference | Observation, **national** (not provincial) | Newest round ≤ m0 − 2 | **2006-Q3** – 2026 (LFS quarterly rounds before 2021; definitions revised April 2005) |
| **OFW Remittance** | E2: remittance decline (national) | – | – | – | **Unavailable.** The BSP OFW remittance file returned HTTP 403 to automated download. It was not circumvented. OpenSTAT has only remittances as a % of GDP (annual). **Manual download needed** (bsp.gov.ph → Statistics → External → OFW remittances). |
| (News) | N1: FSSI-v3 | – | – | – | Unavailable before 2017 (GDELT); not reconstructed |
| (Vulnerability) | V1: poverty and density | Constant = regional mean of served V1 (0.41) | Static structural profile | – | Constant in time, so it cannot forecast change |
| (Hunger) | H1: regional hunger outlook | RW probability P(BL > 11.3 at t+2), four-area pooled horizon σ (Phase 1 `rlib.forecast`) | Derived from observed hunger | SWS rounds published before O(t) | 1999-Q4 – 2026 |

**Indicators that are national or regional, not provincial:** A2, A3, C1, C2, C3, C4 (regional) and E1 (national). Any provincial variation in the served FIRI comes from A1, A2, C2, V1 and N1, and none of these has a provincial outcome to validate it.

**Correlated indicators:** A2 and A3 (both CPI); C3 and C4 (both production in the previous quarter). FIRI averages within domains, which limits double counting.

## 3. Gaps that limit a Lead-2 food-insecurity forecast

1. **No observed food-insecurity outcome below Balance Luzon level, and nothing more frequent than quarterly.** This is the binding gap.
2. OFW remittances: blocked download (manual step).
3. Fish-kill incidents: no historical series (proxied by production).
4. Pre-2021 release dates for production and fisheries are not verified. The rule (quarter t−1 at O(t), i.e. ≥ 3 months after quarter end) is a bound.
5. CPI, production and fisheries are single current vintages, not real-time vintages.
