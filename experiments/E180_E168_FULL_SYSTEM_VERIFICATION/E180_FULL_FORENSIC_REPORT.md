# E180: full-system verification of E168 (read-only, 2026-11-07)

Audited state: branch `aiPHeed/e166-drift-average` @ a980ccc plus 4 uncommitted service files; `render.yaml`; frontend source; E168 artifacts.
Nothing was trained, refitted, tuned or modified. Findings F01-F18 with file, line, method and result: `ISSUE_REGISTER.csv`.

## 1. Scorecard
| Area | Status | Evidence | Reliability concern |
|---|---|---|---|
| E168 implementation | VERIFIED | lgbm.py / temperature.py / prov.py; lock 0 of 12 files changed | none found |
| Model reproducibility | VERIFIED | recalculation = leads.py at all 8 leads; refits reproduced 0.0 (E171-E173) | no serialized model (refit-based) |
| Statistical performance | VERIFIED (retrospective) | L1 56/72 (6/6); L2 55/72 (5/6, C1 0.6405 < 0.6528); L3 54/72; AUC 0.895 / 0.887 | 72 rows reused about 29 times; F1 0.742 |
| Target validity | VERIFIED | target = HFIAS moderate+severe >= 50 % (identical to mod_sev_pct) | survey years only |
| Temporal validity | PARTIALLY VERIFIED | rolling origin; corruption tests 0.0 | one untainted transition before 2018; data vintages (F14) |
| Provincial validity | PARTIALLY VERIFIED | provincial labels, provincial inputs, 5 provinces mapped | no provincial truth after 2021 (F07); national drivers |
| Market/Prices | VERIFIED | provincial PSA CPI inputs; 15 % of 2027-Q1 attribution | current-vintage CPI |
| Climate Stress | VERIFIED | NASA POWER, IBTrACS, PSA crops, ONI; 53 % of 2027-Q1 attribution | centroid climate; ONI global |
| Fish Production | INCORRECT (label) | c_fish_yoy is an input; 0 contribution in 17/17 quarters | labelled "Fish Kill" (F10) |
| Employment | PARTIALLY VERIFIED | LFS national series (D.national) | not provincial (F09) |
| OFW Remittance | PARTIALLY VERIFIED | BSP national series | not provincial; 1.3 % attribution |
| SHAP explainability | INCORRECT (display) | exact pred_contrib; additivity asserted | shares mis-normalised; otherPct dropped (F02) |
| NLP integration | PARTIALLY VERIFIED | 36 news inputs, 23.6 % attribution, H1 | annotations / validation missing (F05) |
| Data provenance | PARTIALLY VERIFIED | DATA_PROVENANCE_AUDIT.csv | vintages; two news corpora (F13) |
| Leakage prevention | VERIFIED | corruption 0.0; as-of rules; issue < outcome | revisions unverified (F14) |
| Geospatial accuracy | VERIFIED | 142/142 join; 5 provinces; colours by riskLevel | LGU = ranking, not forecast |
| Backend correctness | VERIFIED (local) | values, thresholds, history, report | back-forecasts flagged "actual" (F11); alerts not E168 (F12) |
| Frontend correctness | INCORRECT | numbers correct | "Price-pressure risk" (F03); Landing/About (F04); Fish Kill (F10) |
| Deployment consistency | INCORRECT (CRITICAL) | Render: main + AIPHEED_LEAD2_MODEL=thesis → chapter1 indicator | E168 not deployed (F01) |
| Thesis objective alignment | PARTIALLY VERIFIED | THESIS_OBJECTIVE_ALIGNMENT.md | NLP validation, explainability display, deployment |

## 2. Conclusions
1. **Technically correct:** the E168 model path is correct; the explainability display, frontend texts and deployment are not.
2. **Statistically reliable:** retrospectively at Lead 1 (all strict criteria) and to Lead 3 by the 75 % rule; limited by 45.5
   effective rows reused across experiments; Lead-2 strict reliability not shown.
3. **Scientifically defensible:** yes at province-survey-round level with honest wording; not as validated quarterly or municipal
   food-insecurity measurement.
4. **Operationally reliable:** no: production does not serve E168; scheduler and alerts run the older engines.
5. **Ready for thesis demonstration:** locally yes (E168 on all quarters) after the label/text fixes; on production no until F01.
6. **Ready for real-world decision support:** no: needs prospective validation on new provincial HFIAS data and an operational E168 pipeline.

## 3. Answers
1. **Implemented correctly?** Yes (lock intact, settings and path verified, results reproduced).
2. **Metrics reproducible?** Yes: identical at all 8 leads with independent code.
3. **All six at Lead 1?** Yes.
4. **All six at Lead 2?** No. C1 fails: accuracy 0.7639 exceeds the 0.6528 majority rate, but the analytic 95 % lower bound
   0.6405 (n_eff 45.55) does not; C2-C6 pass. (For information, a region-cluster bootstrap interval is [0.662, 0.863]; the frozen C1
   uses the analytic bound and is not changed.)
5. **Target valid for the thesis claims?** Yes for HFIAS moderate-or-severe at province-survey level; not for SWS/price claims shown on the Landing page.
6. **Provincial forecasting?** Yes at survey rounds; quarters between surveys and municipalities are unverified model output.
7. **Five drivers real and valid?** All five map to real inputs; market and climate provincial; employment and remittance national;
   fish is production with zero contribution and a wrong label.
8. **NLP integrated?** Yes as model input (23.6 %); its classifier is not validated in the repository.
9. **SHAP percentages correct?** The attributions are; the displayed percentages are not (F02).
10. **Dashboard consistent with backend?** Numbers yes; labels, history flags, model description and driver shares no.
11. **Deployed model E168?** No (F01).
12. **Confirmed leakage?** None confirmed; data-vintage revisions unverified.
13. **Top ten concerns:** F01 deployment; F02 driver shares; F03 card label; F04 Landing/About; F05 NLP validation; F06 Lead-2 C1;
    F07 no provincial truth after 2021; F08 reuse of the 72 rows; F09 national drivers; F11 back-forecasts shown as actual.
14. **Correct before submission:** F01, F02, F03, F04, F10, F11, and F05 (or disclose).
15. **Qualify or remove:** see THESIS_CLAIMS_RECOMMENDATIONS.md.
16. **Preserve:** E168 code and locked results, target, sealed forecast 28f2c918, leakage controls, leads.py, Algorithm 5 ranking,
    map join, thresholds, additive SHAP computation.
