# Thesis-safe wording (E25)

**Basis:** the frozen E25 run (`runs/20261014T002026Z`; repeat byte-identical).

**Rules for use:** every sentence below is supported by it. Keep the qualifiers. "Development evidence" means every quarter was examined before E25.

## May be claimed (with the qualifiers shown)

1. "aiPHeed produces quarterly, province-level probabilistic forecasts of the composite food-stress label (S1 = SWS regional hunger + 2 × provincial relative food inflation), with an 80% interval, a regional-versus-provincial breakdown, and an explicit information cutoff."
2. "On the 2023-Q4 to 2026-Q1 development quarters, the probabilistic component forecaster (PCF21) had a lower Brier score than naive persistence when leads 1–8 were pooled per forecast date (8 of 10 dates better; one-sided sign-flip p = 0.027, not significant after Holm adjustment across seven baselines, p = 0.082). Its accuracy was the same as persistence's (0.875 at lead 1)."
3. "No model, including the proposed LightGBM, beat naive persistence on accuracy at any lead on the approved label."
4. "On these quarters, 37 of the 40 lead-1 test rows were HIGH, so a constant 'always HIGH' rule had 92.5% accuracy and the lowest Brier score of any forecaster. Accuracy above 75% therefore does not indicate skill on these quarters."
5. "The difficulty lies in the regional SWS hunger level. Inserting the realized regional level (a diagnostic, not a forecast) would have raised lead-1 accuracy to 97.5% (39 of 40). Inserting the realized provincial component instead gives 85.0%."
6. "For the exploratory provincial price-pressure indicator (a province's food inflation above the five-province mean), a regression on the latest two months of provincial CPI and the last quarter's value (M4_21) was correct for 76.4% of province-quarters against 65.5% for persistence at lead 1 (11 development dates; p = 0.031; Brier 0.186 vs 0.345). This is not a food-insecurity outcome and has not been tested on unseen quarters."
7. "Municipal and city rankings for all 142 LGUs follow the approved formula and are deterministic. 126 LGUs use a labelled province-mean poverty substitute, so their within-province order reflects population density only. Where both exist, density runs opposite to poverty (Spearman −0.76, 16 LGUs)."
8. "Forecasts for 2026-Q4 and 2027-Q1 were sealed (SHA-256 recorded) before any outcome existed; they will be scored only after the outcomes are authorized."
9. "The furthest reliable lead time could not be established: no lead met the evaluability requirement (at most 3 LOW test rows)."

## Must NOT be claimed

| Do not write | Why |
|---|---|
| "aiPHeed forecasts food insecurity with X% accuracy" (any X) | Accuracy is dominated by the HIGH base rate; always-HIGH beats every model on Brier |
| "aiPHeed outperforms the baselines" / "beats persistence" (unqualified) | Not on accuracy; on pooled Brier only before Holm adjustment; never better than always-HIGH |
| "The forecasting objective was achieved" / "C1–C9 were met" | C2–C6 are not met; C9 is not assessable |
| "Reliable up to k quarters ahead" | No lead is evaluable or reliable |
| "FSSI / food CPI deviation are among the strongest predictors" (H1 rejected) | H1 is not testable. Descriptively, FSSI ranks 5th by SHAP but permuting it does not hurt; cpi_dev ranks 19th. |
| "H1, H2 or H3 is supported or rejected" | Not testable (fewer than 5 LOW rows at every lead) |
| "H4 or H5 is supported" | Awaiting genuine DA Region IV-A responses |
| "Validated on unseen data" / "generalizes" | No unseen authorized quarter has been scored |
| "The score is a food-insecurity rate" / "province X is food insecure" | The score is a constructed composite; rankings are relative ordinal estimates |
| "Municipal poverty estimates for all 142 LGUs" | Only 16 LGUs have one |
| "The 2027-Q1 forecast" (as if available) | Its inputs are not yet authorized or published; the record is INSUFFICIENT_DATA |
| Anything from the E24v2 back-cast (1995–2020) | Out of the study window; void |
| A second evaluator agency | DA Region IV-A personnel are the only participants |

## Suggested sentence for the limitations section

"The evaluation quarters (2023-Q4 to 2026-Q2) coincided with high regional hunger, so the approved label was HIGH for 37 of 40 lead-1 province-quarters. With so few LOW cases, accuracy cannot distinguish a skilful model from a constant forecast, and the predeclared evaluability rule (at least 5 LOW rows) was not met at any lead. All reported comparisons are development evidence. The sealed prospective forecasts will provide the first test on unseen quarters once their outcomes are published and authorized."
