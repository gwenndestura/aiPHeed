"""
scripts/build_results_docs.py

Builds docs/METRICS.md and docs/CHAPTER_4_RESULTS.md from the approved
pipeline's own artifacts, so no figure in either document is typed by hand:

    data/processed/training_results.json   Algorithms 3 and 4, holdout
    data/processed/eval_results.json       baselines (Objective 4)
    data/processed/shap_attribution.json   Research Question 1
    data/processed/face_validity.json      Objective 5 anchor
    data/processed/fssi_quarterly.parquet  FSSI coverage
    data/processed/topic_proportions.parquet, models/bertopic_model/topics.json  BERTopic
    data/processed/labels.parquet          Equation 3 label

Only the five metrics named in Specific Objective 2 are reported. Objective
statuses follow the evidence, and anything that awaits people (the ISO/IEC
25010 evaluation, DA review of the municipal rankings) or a methodology
decision is reported as such.

    python -m scripts.shap_attribution
    python -m scripts.face_validity
    python -m scripts.build_results_docs
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.inference.disaggregator import Disaggregator
from app.ml.inference.feature_display import FEATURE_DISPLAY_MAP
from app.ml.inference.predictor import Predictor

P = Path("data/processed")
DOCS = Path("docs")

BASELINES = {
    "aipheed_lgbm_combined": "aiPHeed LightGBM (NLP + government)",
    "naive_persistence": "Naive persistence",
    "psa_only_logistic": "Logistic regression, government indicators only",
    "nlp_only_logistic": "Logistic regression, NLP features only",
    "full_feature_logistic": "Logistic regression, combined features",
    "lgbm_psa_only": "LightGBM, government indicators only",
    "lgbm_nlp_only": "LightGBM, NLP features only",
}


def f4(v) -> str:
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.4f}"


def pct(v) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def name(feature: str) -> str:
    return FEATURE_DISPLAY_MAP.get(feature, {}).get("display_name", feature)


def load() -> dict:
    d = {
        "tr": json.loads((P / "training_results.json").read_text()),
        "ev": json.loads((P / "eval_results.json").read_text()),
        "sh": json.loads((P / "shap_attribution.json").read_text()),
        "fv": json.loads((P / "face_validity.json").read_text()),
        "labels": pd.read_parquet(P / "labels.parquet"),
        "fssi": pd.read_parquet(P / "fssi_quarterly.parquet"),
    }
    corpus = pd.read_parquet(P / "corpus_geocoded.parquet")
    inwin = corpus[corpus["quarter"].between("2020-Q1", "2025-Q4")]
    d["corpus"] = {"collected": len(corpus), "in_window": len(inwin),
                   "geocoded": int(inwin["province_code"].notna().sum())}
    topics = None
    tj = Path("models/bertopic_model/topics.json")
    tp = P / "topic_proportions.parquet"
    if tj.exists() and tp.exists():
        raw = json.loads(tj.read_text(encoding="utf-8"))
        sizes = {int(k): v for k, v in raw.get("topic_sizes", {}).items()}
        terms = {int(k): [w for w, _ in v[:5]] for k, v in raw.get("topic_representations", {}).items()}
        topics = {"sizes": sizes, "terms": terms,
                  "n_topics": len([k for k in sizes if k >= 0]),
                  "n_articles": sum(sizes.values()), "n_outliers": sizes.get(-1, 0),
                  "n_cells": len(pd.read_parquet(tp))}
    d["topics"] = topics
    return d


def baseline_table(ev: dict) -> str:
    rows = ["| Approach | Accuracy | Precision | Recall | F1 | AUC-ROC |",
            "|---|---:|---:|---:|---:|---:|"]
    for key, label in BASELINES.items():
        b = ev["baselines"].get(key)
        if not b:
            continue
        o = b["overall"]
        bold = "**" if key == "aipheed_lgbm_combined" else ""
        rows.append(f"| {bold}{label}{bold} | {f4(o['accuracy'])} | {f4(o['precision'])} | "
                    f"{f4(o['recall'])} | {f4(o['weighted_f1'])} | {f4(o['roc_auc'])} |")
    return "\n".join(rows)


def shap_table(sh: dict) -> str:
    rows = ["| Rank | Feature | Share of total attribution |", "|---:|---|---:|"]
    rows += [f"| {f['rank']} | {name(f['feature'])} | {pct(f['share_of_total'])} |" for f in sh["features"]]
    return "\n".join(rows)


def lead_table(tr: dict) -> str:
    rows = ["| k (quarters ahead) | Folds | Accuracy | Precision | Recall | F1 | AUC-ROC | Meets 75%? |",
            "|---:|---:|---:|---:|---:|---:|---:|---|"]
    rows += [f"| {r['k']} | {r['n_folds']} | {f4(r['accuracy'])} | {f4(r['precision'])} | {f4(r['recall'])} | "
             f"{f4(r['f1'])} | {f4(r['roc_auc'])} | {'Yes' if r['passed'] else 'No'} |" for r in tr["lead_time_scan"]]
    return "\n".join(rows)


def holdout_table(tr: dict) -> str:
    return "\n".join([
        "| Metric | Value | Section 3.4.4 target |", "|---|---:|---|",
        f"| Accuracy | {f4(tr['holdout_accuracy'])} | |",
        f"| Precision | {f4(tr['holdout_precision'])} | |",
        f"| Recall | {f4(tr['holdout_recall'])} | |",
        f"| F1-Score | {f4(tr['holdout_f1'])} | 0.75, {'met' if tr['meets_f1_target'] else 'not met'} |",
        f"| AUC-ROC | {f4(tr['holdout_roc_auc'])} | 0.80, {'met' if tr['meets_roc_auc_target'] else 'not met'} |",
    ])


OPEN_DECISIONS = [
    ("Publishing at a Maximum Reliable Lead Time of 0",
     "Section 3.4.4 states that a lead time or configuration below the thresholds is not "
     "published, and Rule 3 requires features from before the forecast period. The system "
     "publishes same-quarter estimates, labelled as such. Publish them, or show no forecast?"),
    ("Section 3.3.2.7 is cited but absent from the manuscript",
     "The selection procedure retains a different set of features from Equation 5's list on "
     "this data. The model trains on Equation 5's list. Which is authoritative?"),
    ("Food-nexus validity guard in Algorithm 1",
     "Articles with no food, hunger or eating term are scored 0 before the 0.30 threshold. "
     "Chapter III names the threshold as the only gate. Keep the guard, or remove it and rescore?"),
    ("Likert interpretation scale for the ISO/IEC 25010 questionnaires",
     "Chapter III does not state the verbal interpretation bands; scripts/iso25010_summary.py "
     "reports means and standard deviations and applies a scale only when one is supplied."),
    ("NNS 2019 and 2023 CALABARZON prevalence figures",
     "Objective 5 names them as the face-validity anchor; no verified value is on file."),
]


def build(d: dict, n_lgu: int) -> tuple[str, str]:
    tr, ev, sh, fv, labels, fssi, cp, topics = (d[k] for k in
        ("tr", "ev", "sh", "fv", "labels", "fssi", "corpus", "topics"))
    k = tr["max_reliable_lead_time"]
    pos, n_lab = int(labels["label_stress"].sum()), len(labels)
    # Only the approved window counts: fssi_quarterly.parquet also holds rows
    # outside 2020-Q1..2025-Q4 (and a few with no parsable quarter), which never
    # enter the feature matrix.
    win = fssi[fssi["quarter"].astype(str).between("2020-Q1", "2025-Q4")]
    fssi_cells = int((win["article_count"] > 0).sum())
    fssi_articles = int(win["article_count"].sum())
    comb = ev["baselines"]["aipheed_lgbm_combined"]["overall"]
    better = [BASELINES[b] for b, v in ev["baselines"].items()
              if b != "aipheed_lgbm_combined"
              and v["overall"]["accuracy"] > comb["accuracy"]
              and (v["overall"]["roc_auc"] or 0) > (comb["roc_auc"] or 0)]
    fssi_share = sum(f["share_of_total"] for f in sh["features"] if f["feature"].startswith("FSSI"))
    cpi = next((f for f in sh["features"] if f["feature"] == "cpi_dev"), None)
    top_fssi = min((f for f in sh["features"] if f["feature"].startswith("FSSI")), key=lambda f: f["rank"])
    nns = fv["nns_anchors"]
    missing = ", ".join(m["cycle"].replace("_", " ") for m in fv["nns_cycles_missing"]) or "none"

    h1 = ("Supported" if cpi and cpi["rank"] <= 3 and top_fssi["rank"] <= 3 else
          "Partially supported" if (cpi and cpi["rank"] <= 3) or top_fssi["rank"] <= 3 else
          "Not supported")
    h3 = "Supported" if not better and all(
        comb["accuracy"] >= v["overall"]["accuracy"] for b, v in ev["baselines"].items()) else "Not supported"

    topic_rows = ""
    if topics:
        rows = ["| Topic | Articles | Top terms |", "|---:|---:|---|"]
        for t in sorted((t for t in topics["sizes"] if t >= 0), key=lambda t: -topics["sizes"][t])[:10]:
            rows.append(f"| {t} | {topics['sizes'][t]} | {', '.join(topics['terms'].get(t, []))} |")
        topic_rows = "\n".join(rows)

    status = [
        ("1. Design a two-tier pipeline (zero-shot XLM-RoBERTa + BERTopic) producing the bias-corrected FSSI and latent risk patterns per province-quarter",
         "Algorithm 1; Equations 1-2; BERTopic", "`nlp/classifier.py`, `features/fssi_builder.py`, `nlp/topic_model.py`",
         "FSSI, lags and acceleration per province-quarter; topic proportions per province-quarter",
         f"FSSI from {fssi_articles} retained articles in {fssi_cells} of 120 province-quarters; "
         + (f"BERTopic: {topics['n_topics']} topics over {topics['n_articles']} articles, proportions for {topics['n_cells']} province-quarters" if topics else "BERTopic outputs missing"),
         "ACHIEVED" if topics else "PARTIALLY ACHIEVED",
         f"News coverage: {120 - fssi_cells} province-quarters carry no news and are filled under Section 3.3.2.6 (Rule 5 flags them)"),
        ("2. Evaluate the LightGBM model with accuracy, precision, recall, F1 and AUC-ROC, and determine the furthest reliable lead time",
         "Algorithms 3 and 4; walk-forward CV; four-quarter holdout", "`training/trainer.py`",
         "Five metrics on the holdout; Maximum Reliable Lead Time",
         f"Accuracy {f4(tr['holdout_accuracy'])}, precision {f4(tr['holdout_precision'])}, recall {f4(tr['holdout_recall'])}, F1 {f4(tr['holdout_f1'])}, AUC-ROC {f4(tr['holdout_roc_auc'])}; lead time {k}",
         "ACHIEVED",
         "The evaluation is complete. Targets: F1 " + ("met" if tr['meets_f1_target'] else "not met")
         + ", AUC-ROC " + ("met" if tr['meets_roc_auc_target'] else "not met")
         + f"; no forward lead time is reliable. Publication at lead time {k} is an open decision (Section 4.9)"),
        ("3. Produce municipal and city risk rankings from validated province forecasts using poverty incidence and population density",
         "Algorithm 5; Equation 6", "`inference/disaggregator.py`",
         "Ranked list of 142 LGUs per quarter with disaggregation label and data sufficiency flag",
         f"{n_lgu} LGUs ranked per quarter, every row labelled (verify_consistency)",
         "PARTIALLY ACHIEVED",
         "The province forecasts do not meet the Section 3.4.4 targets, so they are not 'validated' in that sense; agreement with DA evaluators (H4) awaits the System Accuracy Questionnaire"),
        ("4. Compare the LightGBM model against the baseline approaches",
         "Same walk-forward folds, gap and hyperparameters for all", "`training/evaluator.py`",
         "Comparison table of the five metrics", "Table 4.5",
         "ACHIEVED", "The comparison is complete; whether the model is better is Hypothesis 3"),
        ("5. Deploy a public geospatial dashboard with forecast maps and early-warning alerts; evaluate it under ISO/IEC 25010; validate against NNS 2019 and 2023",
         "FastAPI + React; Rule 7 alerts with review; ISO/IEC 25010 questionnaires; NNS anchor",
         "`api/v1`, `frontend/`, `scripts/iso25010_summary.py`, `scripts/face_validity.py`",
         "Public dashboard; ISO/IEC 25010 ratings; NNS comparison",
         "Dashboard, province ranking, SHAP explanations, municipal rankings and confirmed alerts run locally",
         "PARTIALLY ACHIEVED",
         f"Public deployment of this version not done; ISO/IEC 25010 responses not yet collected; NNS cycles unverified: {missing}"),
    ]
    obj_table = "\n".join(
        ["| Objective | Approved Method | Backend Component | Required Output | Evidence | Status | Remaining Gap |",
         "|---|---|---|---|---|---|---|"]
        + [f"| {' | '.join(r)} |" for r in status])

    decisions = "\n".join(f"{i}. **{t}.** {x}" for i, (t, x) in enumerate(OPEN_DECISIONS, 1))

    metrics = f"""# Model Results

Every figure is read from the approved pipeline's artifacts by
`scripts/build_results_docs.py`; nothing is typed by hand. Only the five metrics
named in Specific Objective 2 are reported.

```bash
python -m scripts.run_quarterly_pipeline --skip-collect
python -m scripts.shap_attribution
python -m scripts.face_validity
python -m scripts.build_results_docs
python -m scripts.verify_consistency
```

Data: {n_lab} labelled province-quarters, {labels['quarter'].min()} to {labels['quarter'].max()},
class split {pos} HIGH / {n_lab - pos} LOW (Equation 3). Model: LightGBM on Equation 5's
twelve features, tuned by 100 Optuna TPE trials on mean weighted F1 (Algorithm 4).

## 1. Maximum Reliable Lead Time (Algorithm 3)

{lead_table(tr)}

Maximum Reliable Lead Time: **{k}**.

## 2. Holdout evaluation (Algorithm 4)

{holdout_table(tr)}

Cross-validation mean weighted F1 of the selected parameters: {f4(tr['best_cv_f1'])}.

## 3. Baselines (Objective 4)

{baseline_table(ev)}

## 4. SHAP attribution (Research Question 1)

{shap_table(sh)}

NLP features {pct(sh['nlp_share'])}; government indicators {pct(sh['gov_share'])};
{sh['n_features_used']} of {len(sh['features'])} features used by the model.
"""

    chapter = f"""# CHAPTER IV
## RESULTS AND DISCUSSION

This chapter reports the results of aiPHeed as implemented under the approved
methodology of Chapter III, organized by the Specific Objectives in Section
1.5.2. Every figure is generated from the pipeline's artifacts by
`scripts/build_results_docs.py`.

### 4.1 Summary of Objective Accomplishment

**Table 4.1** *Objective, Method, Component, Output, Evidence and Status*

{obj_table}

### 4.2 Data

The news corpus holds {cp['collected']:,} articles, {cp['in_window']:,} dated inside the
2020-Q1 to 2025-Q4 window, of which {cp['geocoded']:,} were geocoded to a CALABARZON
province. The Food Stress Sentiment Index rests on {fssi_articles} retained articles in
{fssi_cells} of the 120 province-quarters; the remaining province-quarters carry no news
and are forward-filled or zero-filled under Section 3.3.2.6, and Rule 5 flags them. The
model was trained on {n_lab} labelled province-quarters ({labels['quarter'].min()} to
{labels['quarter'].max()}), {pos} HIGH and {n_lab - pos} LOW under Equation 3. Five
quarters carry no label because no SWS survey round was fielded in them.

### 4.3 Specific Objective 1 and Research Question 1

**Table 4.2** *SHAP Feature Attribution of the Served Model*

{shap_table(sh)}

{("Food CPI deviation ranked " + str(cpi['rank']) + " (" + pct(cpi['share_of_total']) + ")") if cpi else "Food CPI deviation was not among the model's features"},
and the Food Stress Sentiment Index family carried {pct(fssi_share)}, led by
{name(top_fssi['feature'])} at rank {top_fssi['rank']}. NLP features carried
{pct(sh['nlp_share'])} of the attribution in total.

{"**Table 4.3** *Largest BERTopic Topics*" if topics else ""}

{topic_rows}

{(f"BERTopic grouped {topics['n_articles']} articles into {topics['n_topics']} topics ({topics['n_outliers']} outliers) and expressed them as topic proportions for {topics['n_cells']} province-quarters, the latent risk patterns Objective 1 asks for.") if topics else ""}

### 4.4 Specific Objective 2

**Table 4.4** *Lead Time Discovery (Algorithm 3)*

{lead_table(tr)}

The Maximum Reliable Lead Time is {k}: walk-forward accuracy did not reach 75% at any
forward horizon tested.

**Table 4.5** *Holdout Evaluation (Algorithm 4)*

{holdout_table(tr)}

### 4.5 Specific Objective 3

Province probabilities were distributed to {n_lgu} cities and municipalities with
Algorithm 5 (0.6 x poverty incidence + 0.4 x population density, normalized within each
province). Every row carries the Rule 8 disaggregation label and the Rule 5 data
sufficiency flag. Agreement with DA Region IV-A evaluators' assessment (Hypothesis 4)
awaits the System Accuracy Questionnaire.

### 4.6 Specific Objective 4

**Table 4.6** *Comparison Against the Baseline Approaches*

{baseline_table(ev)}

{("Outperforming the combined model on both accuracy and AUC-ROC: " + "; ".join(better) + ".") if better else "No baseline outperformed the combined model on both accuracy and AUC-ROC."}

### 4.7 Specific Objective 5

The system runs as a FastAPI service and a React dashboard showing the provincial risk
map with each province's probability and rank, SHAP explanations including the features
that separate each province from the next one down, the municipal rankings, the news
evidence, and early-warning alerts. Alerts follow Rule 7 and appear only after an
administrator confirms them; forecasts move from STAGED to PUBLISHED only on review.

The ISO/IEC 25010 evaluation by 25 DA Region IV-A and 25 DEPDev Region IV-A evaluators
has not yet been conducted; `scripts/iso25010_summary.py` will summarise the two Google
Forms exports once collected. For the face-validity anchor, the verified NNS cycle on file is
{", ".join(a['cycle'].replace('_', ' ') + f" (CALABARZON {a['calabarzon_moderate_severe_pct']}%)" for a in nns) or "none"};
{missing} could not be verified and are not used.

### 4.8 Summary of Hypothesis Testing

| Hypothesis | Result | Basis |
|---|---|---|
| H1: FSSI and food CPI deviation among the strongest predictors | {h1} | Table 4.2 |
| H2: reliable classification across multiple forward lead times | {"Supported" if k >= 2 else "Not supported"} | Maximum Reliable Lead Time {k} |
| H3: the combined LightGBM outperforms all six baselines | {h3} | Table 4.6 |
| H4: municipal rankings consistent with DA evaluators | Pending | System Accuracy Questionnaire |
| H5: favorable ISO/IEC 25010 ratings | Pending | ISO/IEC 25010 questionnaires |

### 4.9 Methodology Decisions Awaiting the Adviser

{decisions}

The outputs are potential risk indicators: they are indicative and not absolute, and
they are not to be construed as official food insecurity classifications or policy
recommendations.
"""
    return metrics, chapter


def main() -> None:
    d = load()
    pred = Predictor()
    q = pred.available_quarters()[-1]
    n_lgu = len(Disaggregator().disaggregate(pred.forecast_quarter(q), q))
    metrics, chapter = build(d, n_lgu)
    (DOCS / "METRICS.md").write_text(metrics, encoding="utf-8")
    (DOCS / "CHAPTER_4_RESULTS.md").write_text(chapter, encoding="utf-8")
    print("wrote docs/METRICS.md and docs/CHAPTER_4_RESULTS.md")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
