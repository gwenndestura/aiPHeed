"""E60 step N3: seeded annotation sample (NEWS_ANNOTATION_PROTOCOL.md section 3). Classifier outputs are NOT written
into the annotation sheet (the annotator sees title, domain, date only); they are kept in a separate key file.

    backend/venv/Scripts/python.exe -B runner/n3_sample.py ACD   -> annotation/sample_ACD.csv (+ annotation/key_ACD.csv)
    backend/venv/Scripts/python.exe -B runner/n3_sample.py B     -> annotation/sample_B.csv   (+ annotation/key_B.csv)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.nlp.trigger_classifier import TRIGGER_KEYWORDS  # noqa: E402

E31 = EXP / "E31_Chapter1_Completion" / "backend_dev" / "data" / "news_e31" / "articles.jsonl"
E60S = E60 / "data" / "news_e60" / "articles.jsonl"
RX = {c: [re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in kws] for c, kws in TRIGGER_KEYWORDS.items()}
AMBIG = re.compile(r"quezon city|rizal park|jose rizal|dr\.? rizal", re.I)


def load(p):
    a = pd.DataFrame([json.loads(x) for x in p.open(encoding="utf-8")])
    return a[(a["ph_date"] >= "2021-01-01") & (a["ph_date"] <= "2026-09-30")].drop_duplicates("article_key")


def v1_hit(t):
    return int(any(r.search(t or "") for rx in RX.values() for r in rx))


def main(which):
    rng = np.random.default_rng(60 if which == "ACD" else 61)
    (E60 / "annotation").mkdir(exist_ok=True)
    if which == "ACD":
        a = load(E31)
        a["v1"] = a["title"].map(v1_hit)
        geo = a["geo_province_code"].notna()
        A = a[a["v1"] == 1].sample(60, random_state=int(rng.integers(1e9)))
        C = a[(a["v1"] == 0) & geo & ~a["article_key"].isin(A["article_key"])].sample(30, random_state=int(rng.integers(1e9)))
        rest = a[~a["article_key"].isin(pd.concat([A, C])["article_key"])]
        D = rest[(~rest["geo_province_code"].notna()) | rest["title"].str.contains(AMBIG)].sample(20, random_state=int(rng.integers(1e9)))
        S = pd.concat([A.assign(stratum="A"), C.assign(stratum="C"), D.assign(stratum="D")])
    else:
        a = load(E60S)
        e31keys = set(load(E31)["article_key"])
        a = a[~a["article_key"].isin(e31keys)]
        a["v1"] = a["title"].map(v1_hit)
        B = a[a["v1"] == 0].sample(40, random_state=int(rng.integers(1e9)))
        S = B.assign(stratum="B")
    S = S.sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True)
    S["split"] = np.where(rng.random(len(S)) < 0.5, "DEV", "EVAL")
    S["item"] = [f"{which}{i:03d}" for i in range(len(S))]
    sheet = S[["item", "split", "stratum", "ph_date", "source_domain", "title"]].assign(
        relevant="", trigger="", province_true="", kind="", event_in_title_date="", repeat="", annotator="claude-ai",
        human_verified="")
    key = S[["item", "article_key", "geo_province_code", "v1", "first_query_id", "first_query_province", "link"]]
    sheet.to_csv(E60 / "annotation" / f"sample_{which}.csv", index=False)
    key.to_csv(E60 / "annotation" / f"key_{which}.csv", index=False)
    print(sheet["split"].value_counts().to_dict(), sheet["stratum"].value_counts().to_dict())


if __name__ == "__main__":
    main(sys.argv[1])
