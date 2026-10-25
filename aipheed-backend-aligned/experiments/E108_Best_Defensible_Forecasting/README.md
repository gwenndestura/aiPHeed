# E108: factored LightGBM on the 12 aiPHeed indicators, Leads 1–4

**Branch:** `aiPHeed/e108-best-defensible-forecasting` (from E107 `4ed6b27`). **Status:** evaluated; not served; dashboard unchanged.

**Result.**
- **Forecast:** P = (SWS regional hunger outlook) × (LightGBM provincial food-price-pressure probability on all 12 indicators).
- **Lead 1:** accuracy 0.892, balanced accuracy 0.865, AUC 0.917 over 13 quarters. It fails only the recent-four-quarters check, so it is **inconclusive**.
- **Leads 2–4:** not reliable.
- **No reliable lead time is established.**
- Regional hunger is not forecastable beyond its latest reading.

| Deliverable | File |
|---|---|
| A. Root-cause report (why E107 fails) | `ROOT_CAUSE.md` |
| B. Revised methodology (with workflow diagram) | `METHODOLOGY.md` |
| C. Indicator audit (registry, verification, contribution) | `INDICATOR_AUDIT.md` |
| D. Model comparison | `MODEL_COMPARISON.md` |
| E. Maximum reliable lead-time decision | `MAX_LEAD_DECISION.md` |
| F. Thesis-ready results | `THESIS_RESULTS.md` |
| G. Reproducibility and integration | `REPRODUCIBILITY.md` |
| Protocol (hash-frozen before scoring) | `PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt` |
