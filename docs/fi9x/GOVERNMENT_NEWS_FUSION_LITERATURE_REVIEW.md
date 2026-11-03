# Government data + news fusion for food-insecurity forecasting: focused literature review (FI9-X)

All 26 references with a DOI were resolved on Crossref on 2026-11-03. Titles, venues and years match
(`backend/data/fi9x/out/literature_crossref.json`). Two documents without a DOI are cited by their publisher:
* the HFIAS indicator guide (Coates, Swindale & Bilinsky, FANTA, 2007);
* the FNRI 2023 NNS overview (copy kept in `backend/data/fi_labels/raw/owner_supplied/`).

Claims below are limited to what each work shows. Where a claim is our inference for aiPHeed, it says so.

## 1. Text in economic forecasting

| Work | What it shows | Implication for aiPHeed |
|---|---|---|
| Kalamara, Turrell, Redl, Kapetanios & Kapadia (2022), *J. Applied Econometrics*, 10.1002/jae.2907 | UK newspaper text improves macroeconomic forecasts. Gains are largest in periods of stress, and supervised, regularised methods on many text terms beat simple dictionary counts. | News can carry information, mainly in turbulent periods. The text must be reduced and regularised. |
| Barbaglia, Consoli & Manzan (2023), *J. Business & Economic Statistics*, 10.1080/07350015.2022.2060988 | Aspect-based (topic-specific) economic sentiment from news improves short-horizon forecasts of US macro variables, more in the tails than on average. | Use mechanism-specific (aspect) measures, not generic sentiment, and expect gains at short horizons and in extreme quarters. |
| Larsen & Thorsrud (2019), *J. Econometrics*, 10.1016/j.jeconom.2018.11.013 | News topics predict future economic developments beyond standard indicators. | Topic shares are a defensible low-dimensional representation. |
| Thorsrud (2020), *J. Business & Economic Statistics*, 10.1080/07350015.2018.1506344 | Newspaper topics yield a coincident (nowcast) business-cycle index. | News is often coincident, which supports testing news by issue timing. |
| Shapiro, Sudhof & Wilson (2022), *J. Econometrics*, 10.1016/j.jeconom.2020.07.053 | A news-sentiment index predicts survey-based consumer sentiment and macro outcomes. | Sentiment built for the domain is informative. |
| Baker, Bloom & Davis (2016), *Quarterly J. Economics*, 10.1093/qje/qjw024 | Article-count indices must be scaled by the total number of articles to remove volume changes. | Normalise by coverage (as FI6-N does), and test whether volume alone (attention) predicts the outcome. |

## 2. Structured + unstructured data fusion

| Work | What it shows | Implication |
|---|---|---|
| Zhao et al. (2024), *ACM Computing Surveys*, 10.1145/3649447 | Taxonomy of early, intermediate and late fusion; deep fusion methods rely on large training sets. | With 62 labelled quarters, deep multimodal fusion is not supportable. Test early, intermediate (low-dimensional), late and residual fusion with simple models. |
| Teles et al. (2025), *Information Fusion*, 10.1016/j.inffus.2025.102981 | Systematic review of structured + text fusion in prediction modelling; no single fusion stage dominates; results depend on design and sample size. | Compare fusion stages empirically; do not assume intermediate or deep fusion wins. |
| Bates & Granger (1969), *J. Operational Research Society*, 10.1057/jors.1969.103 | Combining forecasts can reduce error relative to the components. | Late fusion by simple averaging is a credible baseline. |
| Wolpert (1992), *Neural Networks*, 10.1016/S0893-6080(05)80023-1 | Stacked generalisation: train the combiner on out-of-sample predictions of the base models. | The stacking meta-model uses only chronological out-of-fold predictions. |

## 3. Small samples, regularisation, imbalance, drift

| Work | Implication |
|---|---|
| Tibshirani (1996), 10.1111/j.2517-6161.1996.tb02080.x; Zou & Hastie (2005), 10.1111/j.1467-9868.2005.00503.x | Lasso and elastic net for p large relative to n. Used as ridge change models and elastic-net logistic, with penalties chosen inside training folds. |
| He & Garcia (2009), *IEEE TKDE*, 10.1109/TKDE.2008.239 | With 11 HIGH of 62, accuracy is misleading. Report balanced accuracy, recall, precision, PR-AUC, and choose thresholds on training data. Synthetic oversampling is not used (too few positives, serial dependence). |
| Gama et al. (2014), *ACM Computing Surveys*, 10.1145/2523813 | Concept drift: test early vs late periods and expanding windows. Dynamic weighting needs more data than we have. |

## 4. Evaluating forecasts

| Work | Implication |
|---|---|
| Hewamalage, Ackermann & Bergmeir (2023), *Data Mining and Knowledge Discovery*, 10.1007/s10618-022-00894-5 | Pitfalls: leakage via preprocessing, wrong cross-validation, weak benchmarks, test-set reuse. Hence the as-of features, transforms fitted inside folds, naive/persistence benchmarks, and the disclosure that historical test quarters were already seen. |
| Cerqueira, Torgo & Mozetič (2020), *Machine Learning*, 10.1007/s10994-020-05910-7 | For non-stationary real-world series, out-of-sample (rolling-origin) estimation is the safer choice. Hence the expanding-window walk-forward. |
| Tashman (2000), *Int. J. Forecasting*, 10.1016/S0169-2070(00)00065-0 | Rolling-origin evaluation and benchmark comparisons. |
| Diebold & Mariano (1995), *JBES*, 10.1080/07350015.1995.10524599 | Paired comparison of predictive accuracy. Implemented as paired Brier differences with a moving-block bootstrap (serial dependence). |
| Brier (1950), *Monthly Weather Review*, 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2; Gneiting & Raftery (2007), *JASA*, 10.1198/016214506000001437 | Brier and log loss are proper scoring rules. Probability quality is judged with them, separately from accuracy. |
| Niculescu-Mizil & Caruana (2005), ICML, 10.1145/1102351.1102430 | Platt scaling suits small samples; isotonic regression overfits. Only Platt-type recalibration on out-of-fold training predictions is considered. |
| Barber et al. (2023), *Annals of Statistics*, 10.1214/23-AOS2276 | Conformal coverage guarantees weaken without exchangeability (drift, serial dependence). Empirical coverage is reported with exact CIs, and the interval is called a 'likely range'. |

## 5. Food-insecurity measurement and small areas

| Work | Implication |
|---|---|
| Cafiero, Viviani & Nord (2018), *Measurement*, 10.1016/j.measurement.2017.10.065 | FIES is a Rasch-scaled experience scale with global thresholds. It is not interchangeable with HFIAS (Coates et al. 2007, FANTA guide) or the SWS single hunger question. Each is kept separate. |
| Fay & Herriot (1979), *JASA*, 10.1080/01621459.1979.10482505; Rao & Molina (2015), *Small Area Estimation*, 10.1002/9781118735855 | Area-level SAE needs direct estimates with sampling variances for many areas plus auxiliary covariates. Five provinces from one wave cannot identify the model; unit-level SAE needs the household files with design variables. |
| Conneau et al. (2020), ACL, 10.18653/v1/2020.acl-main.747 | XLM-R cross-lingual encoder, the basis of the existing zero-shot event and aspect scoring (English/Filipino news). |

## 6. Methods carried into the experiments, and why

| Method | Why appropriate | Data need | Risk | How evaluated |
|---|---|---|---|---|
| Early fusion with ridge / elastic net, 10 news representations | Regularised, few parameters (Kalamara et al.; Zou & Hastie) | ~60 rows OK with strong penalties | Overfitting through many representations | Walk-forward Brier vs no-news counterpart; nested selection |
| Early fusion with constrained LightGBM (FI6-N features, index) | Comparison with the FI6-N result | Larger than linear | Overfit (FI9 audit) | Same |
| Intermediate fusion: 2 government + 2 news principal components | Low-dimensional representation | PCA fitted per fold | Unstable components | Same |
| Late fusion: stacking on out-of-fold predictions; simple average | Wolpert; Bates & Granger | Base models' out-of-fold predictions | Stacker overfit with few positives | Same, vs stack without news |
| Residual fusion: news explains persistence errors | Persistence is the strongest base | Out-of-fold residuals | Unstable residual relation | Same, vs damped persistence |
| Timing-aware nested selection of the news window and representation | Barbaglia et al. (horizon-specific value); FI9-N timing result | Per-origin selection on training only | Selection noise | Same |
| Seasonal damped persistence (statistical time-series model) | Sawtooth may be seasonal and design-related | Quarter-of-year effects from past readings | Spurious seasonality | Same |
| Deep multimodal fusion, transformers fine-tuned on 62 labels | **Not used.** Far more parameters than labelled quarters (Zhao et al.) | Thousands of labels | Certain overfit | Not run |
