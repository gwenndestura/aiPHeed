"""Human validation kit for the zero-shot XLM-RoBERTa labels (Objective 1).

    python -m app.fi6.nlp_validation sample     # writes data/fi6/nlp_validation/annotation_sheet.csv (+ hidden key)
    python -m app.fi6.nlp_validation score      # after annotators fill the sheet(s): precision/recall/kappa

The sheet shows only the headline, date and outlet. Model labels are in a separate key file so annotators are not
anchored. 200 headlines are drawn with a fixed seed, stratified so every domain, every evidence type, the gate-rejected
pool and Filipino headlines are represented. A second annotator may copy the sheet to annotation_sheet_B.csv; Cohen's
kappa is then reported. Until a person fills the sheet, the zero-shot labels remain unverified.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from app.fi5.nlp import ARTICLES, DOMAINS
from app.fi6.paths import VALIDATION

SHEET = VALIDATION / "annotation_sheet.csv"
KEY = VALIDATION / "model_key.csv"
COLS = ["relevant(0/1)", *[f"{d}(0/1)" for d in DOMAINS], "actual_hunger_report(0/1)", "direction(worse/better/neutral)"]
INSTRUCTIONS = """Annotation instructions (one row per headline; judge the headline only)
relevant: 1 if the headline is about something that can affect families' access to enough food (prices or supply of
  food, weather or typhoon damage to farms/food, jobs or livelihoods, OFW income, poverty, hunger or food aid).
market / climate / employment / remittance / poverty: 1 for every domain the headline is about (several allowed).
actual_hunger_report: 1 only if it reports people actually going hungry or lacking food (not a programme, not a risk).
direction: worse if it reports conditions getting worse for people, better if improving, neutral otherwise.
Leave the model's opinion out of it: the model labels are not in this file.
"""


def sample(n: int = 200, seed: int = 20261102) -> pd.DataFrame:
    a = pd.read_parquet(ARTICLES).drop_duplicates("title")
    rng = np.random.default_rng(seed)
    picks = []
    strata = {f"domain:{d}": a[a[f"is_{d}"]] for d in DOMAINS}
    strata |= {f"type:{t}": a[a["evidence_type"] == t] for t in a["evidence_type"].unique() if t != "irrelevant"}
    strata["rejected/irrelevant"] = a[a["evidence_type"] == "irrelevant"]
    per = n // (len(strata) + 1)
    for name, s in strata.items():
        s = s[~s["article_key"].isin([p for x in picks for p in x["article_key"]])]
        picks.append(s.sample(min(per, len(s)), random_state=int(rng.integers(1e9))).assign(stratum=name))
    rest = a[~a["article_key"].isin(pd.concat(picks)["article_key"])]
    picks.append(rest.sample(n - sum(len(p) for p in picks), random_state=int(rng.integers(1e9))).assign(stratum="random"))
    s = pd.concat(picks).sample(frac=1, random_state=seed).reset_index(drop=True)
    s.insert(0, "item", np.arange(1, len(s) + 1))
    sheet = s[["item", "ph_date", "source_domain", "title"]].copy()
    for c in COLS:
        sheet[c] = ""
    key = s[["item", "article_key", "stratum", "relevant", "evidence_type", "stress", *[f"is_{d}" for d in DOMAINS],
             *[f"p_{d}" for d in DOMAINS], "p_hunger_report", "p_worse", "p_better"]]
    sheet.to_csv(SHEET, index=False, lineterminator="\n", encoding="utf-8-sig")
    key.to_csv(KEY, index=False, lineterminator="\n")
    (VALIDATION / "INSTRUCTIONS.txt").write_text(INSTRUCTIONS, encoding="utf-8")
    return sheet


def _prf(truth: np.ndarray, pred: np.ndarray) -> dict:
    tp, fp, fn = int((truth & pred).sum()), int((~truth & pred).sum()), int((truth & ~pred).sum())
    return {"n_true": int(truth.sum()), "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None}


def kappa(a: np.ndarray, b: np.ndarray) -> float | None:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return None if pe == 1 else (po - pe) / (1 - pe)


def score() -> dict:
    key = pd.read_csv(KEY)
    sheets = {p.stem: pd.read_csv(p, encoding="utf-8-sig") for p in sorted(VALIDATION.glob("annotation_sheet*.csv"))}
    out = {"annotators": list(sheets)}
    main = list(sheets.values())[0].merge(key, on="item")
    done = main[main["relevant(0/1)"].astype(str).str.strip().isin(["0", "1"])]
    out["n_annotated"] = int(len(done))
    if not len(done):
        out["status"] = "not yet annotated: zero-shot labels remain unverified"
    else:
        t = done["relevant(0/1)"].astype(int).astype(bool).to_numpy()
        out["relevance"] = _prf(t, done["relevant"].astype(bool).to_numpy())
        for d in DOMAINS:
            out[d] = _prf(done[f"{d}(0/1)"].astype(str).eq("1").to_numpy(), done[f"is_{d}"].astype(bool).to_numpy())
        out["actual_hunger_report"] = _prf(done["actual_hunger_report(0/1)"].astype(str).eq("1").to_numpy(),
                                           (done["evidence_type"] == "actual_food_insecurity").to_numpy())
        dirn = done["direction(worse/better/neutral)"].astype(str).str.lower().str.strip()
        model_dir = np.where(done["stress"] > 0.2, "worse", np.where(done["stress"] < -0.2, "better", "neutral"))
        out["direction_agreement"] = float((dirn.to_numpy() == model_dir).mean())
        if len(sheets) > 1:
            b = list(sheets.values())[1]
            both = done.merge(b[["item", "relevant(0/1)"]], on="item", suffixes=("", "_B"))
            both = both[both["relevant(0/1)_B"].astype(str).isin(["0", "1"])]
            out["inter_annotator_kappa_relevance"] = kappa(both["relevant(0/1)"].astype(int), both["relevant(0/1)_B"].astype(int))
    (VALIDATION / "validation_result.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "score"])
    a = ap.parse_args()
    print(sample().shape if a.cmd == "sample" else json.dumps(score(), indent=1))
