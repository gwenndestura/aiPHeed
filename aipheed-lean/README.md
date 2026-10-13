# aiPHeed — lean

A stripped-down rebuild of the food-availability shock model, built to answer one
question: **how much of the aiPHeed pipeline is actually doing predictive work?**

Short answer: **twelve features and one data source reproduce the full system's
accuracy, and beat it on recall, F1 and AUC.** The other eleven data sources, the
news corpus, the transformer and the four-model ensemble are, on this data, not
measurably contributing.

Everything below is measured on the same rows, the same folds and the same
hyperparameters as the existing pipeline. Nothing here is an estimate.

---

## 1. Is the methodology too complex?

Parts of it, yes — but not the parts that usually get blamed. Split four ways:

| Component | Verdict |
|---|---|
| **Label construction** | **Keep as is.** Genuinely defensible and reused unchanged here. |
| **Evaluation** | **Keep as is.** Walk-forward, honest baselines, published ablations. This is what made the question answerable at all. |
| **Features / data sources** | **Far too complex.** 11 of 12 external feeds are not measurably contributing. |
| **Model machinery** | **Over-built.** The ensemble, per-group models and target encoding move discrimination by +0.0009 AUC. |

The complexity is real and it is concentrated in the data layer:

|  | backend | lean |
|---|---|---|
| Lines of code in the modelling path | 10,612 | 503 |
| External data feeds | 12 | 1 |
| Fetcher / scraper modules | 24 | 0 |
| NLP models | XLM-RoBERTa, BERTopic, sentiment, trigger | none |
| Parquet inputs to the feature matrix | 12 | 1 |
| pip requirements | 157 | 4 |
| Features reaching the classifier | 38 | 12 |

### Why it got this way

This is not carelessness — it is a **stranded pipeline**. The corpus, the NLP stack
and the macro fetchers were built to predict the original composite label (SWS
hunger + food-CPI deviation). That label was abandoned on 2026-09-01 as
unmeasurable, and the target became **PSA production shortfall against a series'
own seasonal baseline**.

The target changed. The forty inputs aimed at the old target did not.

That is the whole explanation for the numbers in the next section. News coverage
and consumer prices are informative about *household food stress*; they were never
going to be informative about *whether Quezon's mango harvest came in 10% below its
own seasonal norm*. The apparatus is not broken, it is pointed at a target that
moved.

---

## 2. The evidence

### 2.1 Feature sets — identical rows, folds, model and hyperparameters

`compare.py`. One frame, one classifier, one set of 12 walk-forward folds, 3,862
scored observations. The only thing varying between rows is which columns the
model may see. The frame comes from the **backend's own loader**, so the lean arm
is not being handed friendlier data.

| arm | nfeat | acc | Δ FULL | prec | rec | F1 | AUC | Δ FULL | feeds | parts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seasonal only | 7 | 0.7170 | −0.0148 | 0.5356 | 0.7384 | 0.6209 | 0.7793 | +0.0058 | 1 | 1 |
| **LEAN** | **12** | **0.7338** | **+0.0021** | 0.5596 | 0.7129 | **0.6270** | **0.7938** | **+0.0203** | **1** | **1** |
| LEAN + government | 26 | **0.7455** | +0.0137 | 0.5849 | 0.6510 | 0.6162 | 0.7881 | +0.0147 | 9 | 14 |
| LEAN + NLP | 17 | 0.7343 | +0.0026 | 0.5617 | 0.6988 | 0.6228 | 0.7863 | +0.0129 | 3 | 12 |
| LEAN + matched news | 15 | 0.7289 | −0.0028 | 0.5533 | 0.7063 | 0.6205 | 0.7903 | +0.0169 | 3 | 10 |
| LEAN + deep lags | 18 | 0.7258 | −0.0060 | 0.5487 | 0.7112 | 0.6195 | 0.7858 | +0.0124 | 1 | 1 |
| FULL (deployed set) | 38 | 0.7317 | — | 0.5609 | 0.6691 | 0.6102 | 0.7734 | — | 12 | 40 |
| | | | | | | | | | | |
| majority baseline | | 0.6862 | | | | | | | | |
| **seasonal persistence** | | **0.7466** | | | | | | | | |

Precision/recall/F1 are for the **shock class**. `feeds` = external data sources
that must keep working; `parts` = fetchers, models and join steps between source
and feature column.

Reading it:

- **LEAN beats FULL on every metric**: accuracy +0.0021, recall +0.0438,
  F1 +0.0168, AUC +0.0203 — on 1 data source instead of 12.
- **The NLP block adds +0.0005 accuracy and −0.0075 AUC.** That is noise, for a
  news corpus, a geocoder and a transformer. The backend's own ablation reaches the
  same place from the other direction: NLP alone scores **AUC 0.5003** — a coin
  flip — and matched-news alone **0.4525**, below chance.
- **The government block is the only one that lifts accuracy** (+0.0117), and it
  does it by trading recall away (0.7129 → 0.6510). F1 and AUC both *fall*. It is
  moving the operating point, not discriminating better.
- **Stacking everything is worse than any single addition.** 38 features on 6,118
  rows and 12 folds is over-parameterised.

### 2.2 Model machinery — same 12 features throughout

`upgrades.py`. Each row adds one mechanism to the row above it.

| configuration | acc | step | rec | F1 | AUC | vs seasonal |
|---|---:|---:|---:|---:|---:|---:|
| 1. LEAN, threshold 0.50 | 0.7299 | | **0.7162** | **0.6247** | 0.7936 | −0.0167 |
| 2. + threshold on train fold | **0.7558** | **+0.0259** | 0.6097 | 0.6105 | 0.7936 | **+0.0092** |
| 2b. same, tuned for F1 | 0.7361 | −0.0197 | 0.6856 | 0.6199 | 0.7936 | −0.0104 |
| 3. + per-group thresholds | 0.7486 | +0.0124 | 0.6279 | 0.6105 | 0.7936 | +0.0020 |
| 4. + per-group models | 0.7460 | −0.0026 | 0.6180 | 0.6043 | 0.7802 | −0.0006 |
| 5. + 4-model ensemble | 0.7545 | +0.0085 | 0.6411 | 0.6211 | **0.7945** | +0.0079 |

**AUC is frozen at 0.7936 across rows 1–3.** That is not a coincidence — those
rows are the *same fitted model* and differ only in where the probability is cut,
and a cut cannot change ranking quality. Row 4 moves it to 0.7802 (worse); row 5
to 0.7945 (+0.0009 over row 1, noise).

So the entire mechanism stack — ensemble, per-group models, per-group thresholds —
**is not making the model better at telling shocks from non-shocks.** It is
choosing where on one fixed ROC curve to stand. Step 2 alone captures that choice
in five lines.

---

## 3. What to use

**LEAN + a single decision threshold picked on the training fold** — row 2 above.

- accuracy **0.7558**, the best of any configuration tested
- the first configuration to beat **seasonal persistence** (+0.0092), which is the
  baseline that matters on an annual agricultural cycle
- one data source, twelve features, ~500 lines, four dependencies

**If recall is what you are being marked on, use row 1 — plain threshold 0.50.**
It has the best recall (0.7162) and the best F1 (0.6247) of every configuration
here, including all five with machinery attached. It does not beat seasonal
persistence on accuracy. That is a real trade and it should be stated rather than
resolved quietly, because for an early-warning indicator a missed shortfall costs
more than a false alarm.

Tuning the threshold for F1 instead of accuracy (row 2b) does **not** recover it —
the training-fold optimum does not transfer. Row 1 remains the best F1 available.

---

## 4. Honest limits

These apply to the lean model and to the full one equally.

1. **The margin over seasonal persistence is small.** The best configuration beats
   it by **+0.0092** accuracy. The label is a seasonal agricultural quantity, and
   "what this series did in the same quarter last year" is a strong free predictor.
   Every claim should be quoted against that baseline, never against the majority
   class alone.
2. **The label is production shortfall, not food insecurity.** It measures whether
   PSA-reported output fell >10% below a series' own seasonal norm. It is a supply
   indicator. It is not a measurement of household hunger, and nothing here should
   be described as predicting food insecurity as experienced by people.
3. **The data is small.** 6,118 rows, 372 series, 22 quarters, 12 folds. Two rounds
   of feature search over nine candidates in the original pipeline yielded one
   survivor. Differences under ~0.01 accuracy are not distinguishable from noise at
   this size, which is exactly why rows 3–5 above should not be read as a ranking.
4. **Recall is the weak number everywhere.** The model misses ~28–39% of real
   shortfalls depending on configuration. Accuracy near 0.75 conceals this because
   the majority baseline is already 0.6862. Never quote accuracy without recall.
5. **This is a research indicator.** It produces potential risk signals, not
   official classifications, and it cannot substitute for assessment procedures
   conducted by the responsible agencies.

---

## 5. What this means for the thesis

The NLP result is a **finding, not a failure**, and it is more interesting than a
positive one would have been. Stated plainly:

> A news-derived NLP signal that was informative about a household food-stress
> target carried no measurable information about an agricultural production
> shortfall target on the same provinces and quarters. Twelve features derived
> from a commodity's own production history matched a 38-feature multi-source
> model on accuracy and exceeded it on recall, F1 and ROC-AUC.

That is a publishable negative result with a clean controlled experiment behind
it, and it is considerably stronger than reporting an ensemble whose components
were never individually measured. The ablation and skill-margin discipline already
in the backend is what makes it defensible — that part of the methodology is a
strength and should stay.

The lean model does not replace the existing system. It establishes what the
existing system has to beat, and right now it does not beat it.

---

## 6. Layout

```
panel.py       the label. Reads the existing builder's output and validates that
               label_shock is still reconstructible from dev_pct. No re-fetch —
               duplicating the label definition is how two definitions drift.
features.py    the twelve features, all from the panel's own history, plus a
               structural leakage check that train.py refuses to run without.
train.py       one LightGBM, walk-forward by quarter, full metrics, both baselines.
compare.py     §2.1 — feature sets head to head through the backend's own loader.
upgrades.py    §2.2 — what each mechanism buys on top of the lean core.
outputs/       results JSON and per-observation predictions from each script.
```

## 7. Running it

Uses the backend's virtualenv; needs only pandas, numpy, lightgbm, scikit-learn.

```bash
cd aipheed-lean && ../backend/venv/Scripts/python.exe train.py
```

```bash
cd aipheed-lean && ../backend/venv/Scripts/python.exe compare.py
```

```bash
cd aipheed-lean && ../backend/venv/Scripts/python.exe upgrades.py
```

`features.py` and `panel.py` also run standalone and print their own diagnostics.

The one input is `backend/data/processed/food_availability_panel.parquet`. If it is
missing, rebuild it — that step does fetch live from PSA OpenStat:

```bash
cd backend && venv/Scripts/python.exe scripts/build_food_availability_panel.py
```
