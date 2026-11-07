# E180: aiPHeed forensic audit, executive report (2026-11-07)

Scope: branch `aiPHeed/e166-drift-average` @ a980ccc with the four uncommitted service fixes; `render.yaml`; frontend source.
Method: read-only source inspection, in-process API calls, independent metric recomputation. Nothing in the system was modified.

## Bottom line
The **E168 model is technically sound and scientifically defensible at survey-round level**: a real HFIAS food-insecurity target, no
detected leakage, results reproduced exactly, beats every baseline, reliable to Lead 3 by the study's 75 % rule. **The system around it is not
yet consistent with it:** production serves an older model (CRITICAL), the dashboard labels and texts describe the retired price-pressure
target, the driver percentages use a non-required method that hides about 20-38 % "other" attribution, and the NLP labels are unvalidated in
the repository. It **runs**, but its **demonstrated** reliability is retrospective, survey-round level, on 72 repeatedly used rows.

## Scorecard
| Area | Status | Evidence | Main limitation |
|---|---|---|---|
| Target validity | VERIFIED | target = HFIAS moderate+severe >= 50 % (matches mod_sev_pct exactly) | survey years only; no quarterly truth |
| Model reliability | PARTIALLY VERIFIED | E168 reproduced exactly; locked; leakage 0.0 | 72 rows reused about 29 times; n_eff 45.5 |
| Predictive accuracy | VERIFIED (retrospective) | L1 77.8 %, L2 76.4 %, L3 75.0 %; AUC 0.895 | F1 0.742 < 0.75; C1 fails at Lead 2 |
| Temporal generalisation | PARTIALLY VERIFIED | rolling origin over 3 rounds | one untainted transition before 2018; no forward validation |
| Provincial validity | PARTIALLY VERIFIED | provincial labels and provincial inputs | national drivers shared; between-survey quarters unverified |
| Five-driver validity | PARTIALLY VERIFIED | market, climate provincial | employment and remittance national; "Fish Kill" = production with 0 contribution |
| NLP integration | PARTIALLY VERIFIED | news = 23.6 % of 2027-Q1 attribution; H1 supported | classifier unvalidated (n_annotated 0) |
| Explainability | INCORRECT (method) | exact LightGBM pred_contrib for the served model | shares normalised over five groups; otherPct dropped |
| Data provenance | PARTIALLY VERIFIED | sources inventoried (DATA_PROVENANCE_AUDIT.csv) | data vintages not reconstructed |
| Leakage prevention | VERIFIED | corruption tests 0.0; as-of rules | revisions in current-vintage series |
| Backend correctness | VERIFIED (local) | values, thresholds, LGU ranking | overlay disabled under the Render env |
| Frontend correctness | INCORRECT | values correct | "Price-pressure risk", Landing/About text, "Fish Kill" |
| Geospatial accuracy | VERIFIED | 142/142 join; 5 provinces | municipal values are rankings, not forecasts |
| Deployment reliability | INCORRECT (CRITICAL) | render: main + AIPHEED_LEAD2_MODEL=thesis → Chapter I model | E168 not in main |
| Reproducibility | VERIFIED | E168 reproduced in E171-E173 (0.0); recompute.py | full test suite rewrites a tracked file |

## Ratings
- **Scientifically defensible:** yes for E168 at survey-round level with honest wording; no for SIMPLE as the thesis model (post hoc).
- **Statistically reliable:** partly. Lead 1 passes every strict check; Leads 2-3 pass the 75 % rule only; small, reused evaluation set.
- **Technically correct:** model path yes; explainability method and frontend text no.
- **Operationally reliable:** no. Production does not serve E168; E168 history is not regenerated automatically.
- **Ready for thesis demonstration:** after fixes 1-3 in RECOMMENDATIONS_AND_PRIORITY.md (local demo works today on E168).
- **Ready for real-world decision support:** no. Needs prospective validation on new provincial HFIAS data and the deployment fix.

## Direct answers
1. **Genuinely forecasting food insecurity?** Yes. E168 forecasts HFIAS moderate-or-severe food insecurity at province-survey level. The
   production deployment does not run it, and the dashboard text still describes a price-pressure index.
2. **Reliable enough for the thesis?** Yes, as retrospective evidence: Lead 1 strict pass, Leads 1-3 at >= 75 %, all baselines beaten,
   provided the limits are stated (72 reused rows, C1 at Lead 2, F1).
3. **E168 or SIMPLE?** E168 is better supported. SIMPLE's +4 at Lead 2 is post hoc, threshold-margin, one-round, less seed-stable,
   with worse Brier and AUC.
4. **Learns food-insecurity signals?** Partly verified. It learns survey errors relative to each province's last survey from climate
   (53 % of 2027-Q1 attribution), prices (15 %), news (24 %) and national labour/remittance series. Attribution is association, not cause.
5. **Five drivers real inputs?** Market and climate: yes (provincial). Employment and remittance: yes but national. Fish: an input with zero
   contribution, mislabelled "Fish Kill".
6. **NLP meaningfully integrated?** Yes in the model (23.6 %, H1); unvalidated as a classifier in the repository.
7. **Provincial predictions justified?** At survey-round level, yes; between survey rounds and for municipalities, they are model
   outputs and rankings without ground truth.
8. **Dashboard consistent with backend?** Numbers yes (locally); labels, model description and driver shares no; production no.
9. **Top ten issues:** I01 production model; I04 driver-share method; I02 risk-card label; I03 Landing/About text; I05 NLP validation
   missing; I06 reused 72 rows / Lead-2 C1; I07 no quarterly ground truth; I08 national drivers; I09 Fish Kill label / zero contribution;
   I10 two news counts (see ISSUE_REGISTER.csv).
10. **Fix before submission:** I01, I04, I02/I03/I09, I05 (or state it as unvalidated), and the thesis wording on reliability and SIMPLE.
11. **Claims to remove or qualify:** "price-pressure"/SWS target text; "provincial employment/remittance"; "fish kill"; "quarterly
    provincial validation"; any validated-NLP claim; any SIMPLE superiority claim; municipal "forecasts" → rankings.
12. **Correct, do not change:** E168 model and locked results, the HFIAS target, sealed forecast 28f2c918, leakage controls,
    C1-C6 code, Algorithm 5 LGU ranking, map join, threshold configuration.

Detailed evidence: the 15 other files in this folder.
