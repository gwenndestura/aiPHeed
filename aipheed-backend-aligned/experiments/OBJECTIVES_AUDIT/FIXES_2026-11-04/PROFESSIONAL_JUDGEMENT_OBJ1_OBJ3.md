# Professional-judgement decisions for Objectives 1 and 3 (2026-11-04)

**Instruction (project owner):** no human labelling and no adviser weighting decision. Resolve both from credible
published references, using professional judgement.

**Basis:**
- the Chapter I objectives, quoted verbatim from `OBJECTIVES_COMPLETION/REQUIREMENTS.md`;
- the project's own evidence files;
- the references in §4.

No served file, model, forecast or dashboard text is changed by this record.

---

## 1. Objective 3: LGU weighting (decisions D3.1–D3.4)

> Objective 3: "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated
> province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights."

### D3.2 Weighting: **keep Option A (0.6 poverty + 0.4 density), with a sensitivity analysis**

**Reasoning:**

1. **The objective prescribes the inputs.** Chapter I names "poverty incidence and population density". Options B
   (poverty only), C (poverty + number of poor) and D (two separate ranks) would each change an approved objective.
   An objective is not changed after the results are known when the existing method can be defended.
2. **Each input has a recognised role in the risk framework.**
   - The IPCC treats risk as arising from hazard, **exposure** and **vulnerability**, with vulnerability defined as
     "the propensity or predisposition to be adversely affected" [R3].
   - INFORM, the JRC's operational risk index, keeps exposure and vulnerability as separate dimensions. It notes that
     there is no risk without exposure, however severe the hazard [R2].
   - In aiPHeed, the forecast probability is the hazard term, PSA poverty incidence is the vulnerability term, and
     population density is the exposure term (people concentrated per km² who rely on markets hit by a price shock).
     **The thesis should name density as the exposure component, not as a vulnerability measure.**
3. **Poverty gets the larger weight.**
   - PSA poverty incidence is the official, design-based measure of economic vulnerability (Census Empirical
     Best/Bayes SAE, with published CVs) [R4].
   - FAO reports that food insecurity is more prevalent among rural populations [R5]. Density, which marks urban
     municipalities, should therefore not dominate.
   - Giving poverty 60% and density 40% keeps vulnerability primary.
4. **The weights are a declared value judgement, not an estimate.** The OECD/JRC Handbook states that weights reflect
   judgement. It warns that correlated indicators can double-count. It recommends uncertainty and sensitivity analysis
   so readers can see how much rankings depend on the weights [R1].
   - Here poverty and density are **negatively** correlated (Spearman −0.53), so they do not double-count.
   - The cost is that dense, less-poor towns rise (Taytay, Lipa). The thesis must state this openly.
5. **Sensitivity is already computed and is reported, not hidden** (`LGU_WEIGHTING_ADVISER_DECISION.md`,
   `OBJ3_DECISION_RECORD.md`). Kendall τ against the served ranking:

   | Alternative weighting | τ |
   |---|---|
   | Poverty only | 0.71 |
   | 0.8 / 0.2 | 0.82 |
   | Density as protective | 0.46 |

   - The top-10 mean poverty is 19.3% under A and 25.3% under poverty only.
   - The median 90% rank interval is 51 places, so rankings are indicative bands, not exact positions.

**Thesis wording (Chapter III / IV):**

> "Following the IPCC risk framework (hazard × exposure × vulnerability) and the JRC INFORM approach of treating
> exposure separately from vulnerability, each LGU's relative risk combines the forecast probability with PSA 2021
> poverty incidence (vulnerability, weight 0.6) and 2024 POPCEN population density (exposure, weight 0.4), each
> min-max normalised within the province. The weights are a declared judgement, as recommended by the OECD/JRC
> Handbook. In CALABARZON, density is negatively correlated with poverty (ρ = −0.53), so the 0.4 exposure weight
> raises dense urban LGUs. A sensitivity analysis (poverty only: τ = 0.71; 0.8/0.2: τ = 0.82) and 90% Monte Carlo
> rank intervals (median width 51 places) are reported, and rankings are presented as indicative."

### D3.1 Province score: **keep the served province factor (option b) as a documented deviation**

- The forecast target is regional (SWS Balance Luzon), so Eq. 6 as written would give all five provinces the same
  probability.
- With within-province min-max scaling, Eq. 6 would also erase every between-province difference.
- Scaling the regional probability by official PSA provincial poverty (relative to the poorest province) restores a
  documented, official basis for province differences. The HIGH/LOW class stays regional, so no provincial
  classification is claimed.
- **Disclosure for Chapter III:**

  > "The forecast is regional; province scores are the regional probability weighted by PSA provincial poverty
  > incidence. This is a disaggregation, not a provincial forecast."

### D3.3 Uncertainty display: **recommend rank bands; not implemented**

- Rank bands (top 10 / 11–30 / rest) follow the Handbook's advice to communicate uncertainty [R1].
- Adding them is a dashboard design change, which stays with the project owner (standing rule: no UI design changes).
  Until then, the 90% rank intervals are reported in Chapter IV.

### D3.4 Data vintages: **PSA 2021 SAE + POPCEN 2024, with one disclosure**

- These are the official vintages integrated and verified in the project.
- **Disclosure:** PSA presented the 2023 city and municipal poverty estimates on 16 February 2026 [R4b]. The thesis
  should say that the 2021 SAE was the vintage integrated before the analysis was frozen.
- Re-running with 2023 SAE would be an update. It needs the owner's approval to download new data.

### Objective 3 status after these decisions

- **Achieved as written:** rankings for all 142 LGUs, using PSA poverty incidence and population density.
- **Remaining qualification:** the source forecasts are regional and validated on development data only, not
  "validated province-level forecasts" in the prospective sense.
- **H4** (agreement with DA evaluators) is tested by the Objective 5 survey.

---

## 2. Objective 1: NLP validation without human labelling

> Objective 1: "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction
> and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food
> insecurity risk patterns per province-quarter from a Filipino-English news corpus."

### What the objective requires, and what exists

| Requirement | Evidence | Met? |
|---|---|---|
| Tier 1: zero-shot XLM-RoBERTa on Filipino-English news | `joeddav/xlm-roberta-large-xnli`; every stored score verified as model output (`NLP_VALIDATION_REPORT.md`) | Yes |
| Tier 2: BERTopic topics | Time-safe BERTopic at 19 origins; T2 makes topics thematic (place-name topics 55% → 0%) (`FIXES_REPORT.md`) | Yes |
| Bias-corrected FSSI | Eq. 1 coverage weights; anomaly form `z_N1R` | Yes |
| Latent risk patterns per province-quarter | `out/obj1_topic_proportions_timesafe.csv` | Yes, with coverage gaps: 46% of province-quarters have no articles |
| Filipino-English corpus | 9,667 headlines, multilingual encoder | Yes |

**Judgement:** Objective 1 asks for a pipeline to be **designed** and to **produce** the FSSI and the patterns. It does
not require a labelled accuracy figure. The objective is **achieved as written**. Human labelling would be an extra
quality check, not a requirement.

### Why the pipeline is credible without local labels

1. **The model is externally benchmarked.**
   - Zero-shot classification by textual entailment is an established, benchmarked method [R7].
   - XLM-R was trained for cross-lingual transfer and outperformed mBERT by 13.8 points of average XNLI accuracy [R8].
   - XNLI is the standard cross-lingual NLI benchmark (15 languages) [R9].
   - The model used is XLM-R large fine-tuned on XNLI for exactly this zero-shot use.
2. **The validation used in this field is predictive (criterion) validation.** The reference study on news-based
   food-crisis prediction (Balashankar et al., Science Advances 2023) validated its news indicators by whether they
   improved forecasts of the official food-insecurity classification (IPC) [R10]. aiPHeed ran the same kind of test:
   - news changes 0 of 62 forecasts;
   - Brier gain is 0.001;
   - FSSI vs next-quarter hunger: ρ 0.45, p 0.19, n 10.

   This is a valid, reportable result: **H1 is not rejected**. FSSI is not among the strongest predictors.
3. **External convergent check:** disaster news correlates with typhoon counts, ρ = 0.81 (E112,
   `OBJECTIVES_COMPLETION/REQUIREMENTS.md`).
4. **Topic coherence is interpreted with the literature in view.**
   - Automated coherence (NPMI) often disagrees with human judgement and overstates differences between models [R11].
   - Headlines are short texts with sparse word co-occurrence, which depresses co-occurrence scores [R12].
   - T2's mean NPMI of −0.15 (positive, +0.01, on the full 2026-Q3 corpus) is therefore reported as a limitation.
     Topics are used for description and monitoring only.
   - BERTopic is the method named in Chapter I [R13].

### Limitation that must be stated

The main methods reference is clear that automated text methods "require extensive and problem-specific validation"
[R6]. Without local labels, aiPHeed **cannot report** relevance precision or recall, sentiment accuracy, or geocoder
accuracy on its own corpus.

**Chapter IV wording:**

> "Classifier accuracy was not measured on a locally labelled sample. Validity rests on the model's published
> cross-lingual benchmarks, temporal safeguards, a convergent check against typhoon counts (ρ = 0.81), and a
> criterion test against the forecast target, in which news added no material predictive value."

### Objective 1 status

- **Achieved as written.**
- **H1 not rejected:** FSSI is not among the strongest predictors.
- **Stated limitations:** no local labelled accuracy; coherence below the pre-registered NPMI rule; coverage gaps.

---

## 3. Updated status (all five objectives)

| Objective | Status | Remaining qualification |
|---|---|---|
| 1. NLP pipeline | **Achieved as written** | No local accuracy figure; H1 not rejected; coherence and coverage limits |
| 2. Forecasting | **Partially achieved** | Development evidence only; prospective seals from 2027-01-01 |
| 3. Spatial rankings | **Achieved as written** | Source forecast regional; rank uncertainty wide; H4 via survey |
| 4. Baselines | **Partially achieved** | Not proven better than fair persistence or the logistic baselines (`FIXES_REPORT.md`) |
| 5. System and evaluation | **In progress** | 50 DA Region IV-A responses |

---

## 4. References

- **[R1]** OECD and European Commission JRC (2008). *Handbook on Constructing Composite Indicators: Methodology and
  User Guide.* OECD Publishing.
  https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html
  - JRC 10-step guide, Step 6 Weighting: https://knowledge4policy.ec.europa.eu/composite-indicators/10-step-guide/step-6-weighting_en
- **[R2]** European Commission JRC, Disaster Risk Management Knowledge Centre. *INFORM Risk methodology.*
  https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Risk/Methodology
- **[R3]** IPCC (2020). *The concept of risk in the IPCC Sixth Assessment Report* (Reisinger et al.), and the AR6 WGII
  glossary.
  - https://www.ipcc.ch/site/assets/uploads/2021/02/Risk-guidance-FINAL_15Feb2021.pdf
  - https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Annex-I.pdf
- **[R4]** Philippine Statistics Authority. *Highlights of the 2021 City and Municipal Level Small Area Estimates of
  Poverty.* https://www.psa.gov.ph/system/files/phdsd/Highlights%20of%20the%202021%20SAE.pdf
- **[R4b]** Provincial Government of Bohol (16 Feb 2026), reporting PSA's 2023 city and municipal poverty estimates.
  https://bohol.gov.ph/2026/02/16/more-bohol-towns-record-lower-poverty-incidence-in-2023-psa/
- **[R5]** FAO, IFAD, UNICEF, WFP and WHO (2023). *The State of Food Security and Nutrition in the World 2023:
  Urbanization, agrifood systems transformation and healthy diets across the rural–urban continuum.*
  doi:10.4060/cc3017en. Summary: https://sdg.iisd.org/news/sofi-2023-explores-rural-urban-continuum-in-agrifood-systems/
- **[R6]** Grimmer, J., and Stewart, B. M. (2013). Text as Data: The Promise and Pitfalls of Automatic Content Analysis
  Methods for Political Texts. *Political Analysis* 21(3), 267–297. https://bstewart.scholar.princeton.edu/document/41
- **[R7]** Yin, W., Hay, J., and Roth, D. (2019). Benchmarking Zero-shot Text Classification: Datasets, Evaluation and
  Entailment Approach. *EMNLP-IJCNLP 2019*, 3914–3923. https://aclanthology.org/D19-1404/
- **[R8]** Conneau, A., et al. (2020). Unsupervised Cross-lingual Representation Learning at Scale (XLM-R). *ACL 2020*.
  arXiv:1911.02116.
- **[R9]** Conneau, A., et al. (2018). XNLI: Evaluating Cross-lingual Sentence Representations. *EMNLP 2018*.
  https://arxiv.org/abs/1809.05053
- **[R10]** Balashankar, A., Subramanian, L., and Fraiberger, S. P. (2023). Predicting food crises using news streams.
  *Science Advances* 9, eabm3449. https://pmc.ncbi.nlm.nih.gov/articles/PMC9984173
- **[R11]** Hoyle, A., et al. (2021). Is Automated Topic Model Evaluation Broken? The Incoherence of Coherence.
  *NeurIPS 2021*. https://arxiv.org/abs/2107.02173
- **[R12]** Qiang, J., et al. (2020). Short Text Topic Modeling Techniques, Applications, and Performance: A Survey.
  *IEEE TKDE.* doi:10.1109/TKDE.2020.2992485. https://arxiv.org/abs/1904.07695
- **[R13]** Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure.
  arXiv:2203.05794.

**Verification note:** the facts quoted from [R1], [R2], [R3], [R5] and [R10] were read from the publishers' pages or
summaries on 2026-11-04. Exact page numbers should be checked against the full texts before final submission.
