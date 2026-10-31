# E123 final recommendation

## Outcome: **READY WITH WARNINGS**

FIRI3 v1.2 (E121 protocol + Amendment 1 + Amendment 2) can proceed to prospective validation from origin 2026-Q4 (issue 2027-01-01) with these warnings:
- three features have assumed (unverified) availability dates;
- Batangas 2024 underemployment is unverified;
- most scores sit within chance variation of 0.5;
- the overall provincial ranking is mainly structural.

**No methodological revision is required** for the prospective record. The supplementary scores address interpretation without changing the index.

**FIRI v2 stays served.** Nothing was deployed, pushed or merged.

## Answers

1. **Are all six indicators still defensible?**
   - **Yes.** All six are computed from eligible 2021+ data, are point-in-time valid, and have near-independent scores.
   - PSV and EHS rest on **unverified availability dates** (assumptions). FIS is often unavailable at province level (14 of 115).

2. **Does separating current conditions and structural vulnerability help?**
   - **Yes.** FIRI3's provincial ranking is fairly fixed (Kendall W 0.44; Batangas top 9 of 15) because EHS explains 67% of between-province differences.
   - The CCS ranking changes with conditions (W 0.10; top spread across four provinces). The SVS is almost fixed (W 0.95).
   - Showing both prevents a structural rank from being read as current food conditions. The CCS does **not** measure hunger or household food consumption.

3. **How many scores support the supplementary scores?**
   - **CCS:** 75/115 provincial (2023-Q1+), 10/23 regional (2024-Q2+).
   - **SVS:** 25/115 provincial (2025-Q3+, when PSV becomes available); regional not defined.

4. **Does the common-core score improve comparability?**
   - **Yes, as a check.** It identifies rows that cannot be compared, and shows that 13% of provincial quarter-to-quarter change comes from indicator availability.
   - **Coverage:** fixed core 75/115 provincial and 9/23 regional; cross-province core 80/115.
   - **Agreement:** it closely tracks FIRI3 (ρ 0.90 / 0.99), and band agreement is 97–99%.

5. **Which publication dates remain unverified?**
   - **Verified (4):** cyclones within 100 km, cyclones in PAR, FSSI-v3, GDELT.
   - **Provisionally eligible (27):** documented release rules, no archived dates.
   - **Unverified (3):** EHS unemployment, EHS underemployment, PSV poverty. Their dates are assumptions.
   - **Ineligible:** 0.
   - **No archived evidence could be retrieved in this phase** (PSA 403; Internet Archive offline).

6. **Is Batangas underemployment verified?**
   - **Partly.** The values enter FIRI3 correctly.
   - **2023 (31.0%):** corroborated by a PSA Region IV-A release, seen in search results; the document returned 403.
   - **2024 (39.5%) and 2025 (21.1%):** not verified.
   - **Publication dates:** unknown.

7. **Are FSSI and GDELT inputs point-in-time valid?**
   - **Yes.** Both reproduce exactly from raw 2021+ records published before each issue: FSSI Δ = 0 in all 115 rows; GDELT Δ < 1e-12.
   - **Limits:** a general pretrained NLI model, relevance rules written on 2021–26 articles, and the GDELT query vintage.

8. **Which indicators dominate?**
   - **No indicator dominates the score level** (mean shares 0.18–0.23).
   - **Between provinces, EHS dominates** (67%; FMA 22%).
   - **Regionally, EHS** (national shocks) has the largest share (0.33) and the largest removal effect (30% band changes).

9. **Stable under weighting and missingness?**
   - **The score level: yes.** Reasonable weight changes move it by 0.003–0.03 on average. Redundancy-adjusted weights change 2.7% of bands.
   - **The bands: no**, under large shifts. Structure 2/3 changes 35% of bands, and removing EHS changes 24%.
   - **Indicator availability** shifts single provinces by up to about 0.1 (13% of provincial change).
   - **88% of provincial scores are within chance variation of 0.5.**

10. **Is the prospective protocol ready?**
    - **Yes.** The module, immutable snapshots, observation records and the FIRI v2 comparison are in place and tested.
    - **No prospective snapshot exists yet.** The first can only be issued on or after 2027-01-01.

11. **Does FIRI3 stay separate from the thesis ML comparison?**
    - **Yes.** No model was trained.
    - The LightGBM vs persistence, PSA-only, NLP-only and logistic-regression comparison remains a separate experiment.
    - FIRI3 is not used as a label.

12. **Proceed or revise?**
    - **Proceed to prospective validation**, reporting FIRI3 with the CCS, SVS, common core, band and leave-one-out range.
    - **Before adoption** (a separate owner decision), resolve:
      - PSA release dates (EHS, PSV, and the rule-based features);
      - Batangas 2024/2025 values;
      - whether the CCS should be the headline provincial "conditions" reading.

## Owner decisions

| Item | Recommendation |
|---|---|
| Amendment 2 (complete-year rule; CCS / SVS / common core) | **Confirm.** Applied under E123 §3 DI-1/2/3. Reversible: E122 results and snapshots are kept. |
| Headline presentation | Show the CCS beside FIRI3 for provincial comparisons (display decision; dashboard unchanged) |
| Data requests | PSA provincial LFS tables with dates; PSA SAE 2021 release date; PSA release calendars (via the owner) |
| First prospective issue | On or after 2027-01-01, after refreshing the inputs |
