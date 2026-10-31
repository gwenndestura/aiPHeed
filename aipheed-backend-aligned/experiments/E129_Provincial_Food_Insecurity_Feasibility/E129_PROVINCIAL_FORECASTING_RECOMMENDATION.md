# E129 provincial forecasting recommendation

**Owner Addendum 1 (2026-10-31).** Provincial food CPI is a **predictor**, so layer 1 below is **not adopted as a target**. Validation uses the owner's references:
- PSA subsistence incidence (provincial food deprivation);
- FNRI FIES (household food insecurity);
- SWS Balance Luzon (regional hunger).

See `E129_ADDENDUM_1_OWNER_VALIDATION_DATA.md`. The layer table is kept as the record of options considered.

**The provincial scope is kept, with honest names.** It is a three-layer design. No layer claims provincial food-insecurity forecasting accuracy until a measured provincial outcome exists.

| Layer | Target | Status | Claim allowed |
|---|---|---|---|
| 1. Provincial food-price pressure forecast | Provincial food CPI YoY, continuous; Leads 1–4 | **Data sufficient.** 5 × 23 quarters; R1 attainable (55–70 rows). Needs a frozen protocol and owner approval of A-R2c / A-R4p. | "Forecast of provincial food-price pressure"; skill vs per-province persistence |
| 2. Provincial risk index | FIRI3 (existing, frozen) | Built (E121–E127); first prospective issue 2027-01-01 | "Relative risk index"; not measured FI |
| 3. Regional hunger reference | SWS Balance Luzon | E128: no reliable lead. Prospective log continues. | Regional hunger outlook |
| 4. Provincial / LGU outcome validation | CBMS 2024 FIES; ENNS 2021 / 2022 | **Data not held** | When obtained: cross-sectional agreement of layer 1–2 rankings with measured FI |

## Evidence-based expectations for layer 1

**Province-specific deviations decay fast** (autocorrelation 0.74, 0.55, 0.29, −0.05 at Leads 1–4):
- province differentiation is plausible at Leads 1–2;
- unlikely at Lead 3;
- absent at Lead 4.

The common component, regional inflation, dominates, and E-series results show it is hard to predict two quarters ahead (LEAD2 root-cause II: price crossings in 48 % of Lead-2 cases).

**Lead 2 is evaluable** (13 quarters, 65 rows), but reliability must be earned against per-province persistence.

## Next step before any model training

1. **Owner decisions**
   - Approve the layer-1 target name and definition (food-price pressure, not food insecurity).
   - Approve or reject amendments A-R1p, A-R2c, A-R4p, A-R7p.
   - Decide on the pre-2021 SWS regional track.
2. **Data requests** (owner signatures; drafts exist in E87). These are the only route to a provincial food-insecurity target:
   - A: PSA CBMS 2024 FIES by LGU;
   - B: FNRI 2022 ENNS provincial FIES and coverage;
   - C: SWS microdata with respondent province.
3. **CPI release-date verification** for the 148 unverified province-months (P / U / N classes).
4. **Then** freeze an E130 protocol for layer 1. It trains the five models (LightGBM, persistence, PSA-only, NLP-only with provincial news volume only, LR) under `E129_VALIDATION_DESIGN.md`.

## Do not

- Do not call layer-1 skill "food insecurity forecasting".
- Do not copy SWS to provinces.
- Do not use FIRI3 / FIRI v2 as labels.
- Do not train before step 1.
