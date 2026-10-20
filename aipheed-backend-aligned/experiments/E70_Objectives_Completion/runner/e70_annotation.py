"""E70 Objective 1 (ACTION_PLAN F13): a blind, stratified HUMAN annotation sample of the served news corpus, and the
scorer that turns the researcher's labels into precision / recall / F1, attribution accuracy and error lists.

Claude cannot produce human labels; the sample is written with empty label columns. Run with cwd = backend:

    python -B ../aipheed-backend-aligned/experiments/E70_Objectives_Completion/runner/e70_annotation.py sample
    python -B ../aipheed-backend-aligned/experiments/E70_Objectives_Completion/runner/e70_annotation.py score

Strata (seed 70): A = admitted & province-attributed, B = admitted & national, C = classified not relevant,
F = Filipino-looking headline by the audit keyword test (any model label). Estimates are weighted by the inverse
sampling fraction of each stratum, so they describe the whole in-window corpus, not the sample.
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
E70 = Path(__file__).resolve().parents[1]
DIR = E70 / "annotation"
SAMPLE, KEY = DIR / "HUMAN_ANNOTATION_SAMPLE.csv", DIR / "model_key.csv"
SIZES = {"A": 100, "B": 60, "C": 100, "F": 40}
FIL = set("ang mga sa ng na nang para presyo bigas gutom kagutuman tulong magsasaka mangingisda ayuda tumaas bumaba".split())
LABEL_COLS = ["human_relevant", "human_trigger", "human_province", "human_food_stress", "annotator", "notes"]


def lang(t: str) -> str:
    w = set(re.findall(r"[a-z]+", t.lower()))
    return "fil" if len(w & FIL) >= 2 else "eng_or_mixed"


def strata():
    from app.news import pipeline_v3 as P
    C = P.corpus()
    adm = {a["article_key"] for a in P.admitted()}
    S = {"A": [], "B": [], "C": [], "F": []}
    for a in C:
        if lang(a["title"]) == "fil":
            S["F"].append(a)
        elif a["article_key"] in adm:
            S["A" if a["province_code"] else "B"].append(a)
        elif a["relevant"] != 1:
            S["C"].append(a)
    return C, adm, S


def sample():
    if SAMPLE.exists():
        raise SystemExit("sample already drawn; it is drawn once")
    C, adm, S = strata()
    rng = random.Random(70)
    rows, keys, pop = [], [], {}
    for s, arts in S.items():
        pop[s] = len(arts)
        pick = rng.sample(arts, min(SIZES[s], len(arts)))
        for a in pick:
            keys.append({"stratum": s, "article_key": a["article_key"], "model_relevant": a["relevant"],
                         "model_admitted": int(a["article_key"] in adm), "model_trigger": a["trigger"] or "",
                         "model_province": a["province_code"] or "", "quarter": a["quarter"]})
    order = list(range(len(keys)))
    rng.shuffle(order)                                    # strata are not visible to the annotator
    keys = [keys[i] for i in order]
    by_key = {a["article_key"]: a for a in C}
    for i, k in enumerate(keys, 1):
        k["sample_id"] = f"S{i:03d}"
        a = by_key[k["article_key"]]
        rows.append({"sample_id": k["sample_id"], "date": a["ph_date"], "outlet": a["outlet"], "title": a["title"],
                     "link": a["link"], **{c: "" for c in LABEL_COLS}})
    DIR.mkdir(exist_ok=True)
    for path, data in ((SAMPLE, rows), (KEY, keys)):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    (DIR / "sample_meta.json").write_text(json.dumps({"population": pop, "sizes": {s: min(SIZES[s], pop[s]) for s in S},
                                                      "corpus_in_window": len(C), "seed": 70}, indent=1))
    print(json.dumps(pop), len(rows))


def score(sample_path: Path = SAMPLE, key_path: Path = KEY, meta_path: Path = DIR / "sample_meta.json") -> dict:
    """Weighted relevance precision/recall/F1 (model 'admitted' vs human_relevant), trigger and province agreement."""
    lab = {r["sample_id"]: r for r in csv.DictReader(sample_path.open(encoding="utf-8"))}
    key = list(csv.DictReader(key_path.open(encoding="utf-8")))
    meta = json.loads(meta_path.read_text())
    w = {s: meta["population"][s] / meta["sizes"][s] for s in meta["sizes"] if meta["sizes"][s]}
    done = [k for k in key if lab[k["sample_id"]]["human_relevant"].strip() in ("0", "1")]
    if not done:
        return {"status": "NOT_ANNOTATED", "labelled": 0, "sample": len(key)}
    tp = fp = fn = tn = 0.0
    errors, trig, prov = [], [0, 0], [0, 0]
    for k in done:
        h = int(lab[k["sample_id"]]["human_relevant"])
        m = int(k["model_admitted"])
        wt = w[k["stratum"]]
        tp += wt * (m == 1 and h == 1)
        fp += wt * (m == 1 and h == 0)
        fn += wt * (m == 0 and h == 1)
        tn += wt * (m == 0 and h == 0)
        if m != h:
            errors.append({"sample_id": k["sample_id"], "stratum": k["stratum"], "model": m, "human": h,
                           "title": lab[k["sample_id"]]["title"]})
        if m == 1 and h == 1:
            ht = lab[k["sample_id"]]["human_trigger"].strip()
            if ht:
                trig[0] += ht == k["model_trigger"]
                trig[1] += 1
            hp = lab[k["sample_id"]]["human_province"].strip()
            if hp:
                prov[0] += hp == (k["model_province"] or "national")
                prov[1] += 1
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else None
    return {"status": "ANNOTATED" if len(done) == len(key) else "PARTIAL", "labelled": len(done), "sample": len(key),
            "weighted": {"precision": prec, "recall": rec, "f1": f1, "TP": tp, "FP": fp, "FN": fn, "TN": tn},
            "trigger_agreement": trig[0] / trig[1] if trig[1] else None, "trigger_n": trig[1],
            "province_agreement": prov[0] / prov[1] if prov[1] else None, "province_n": prov[1],
            "errors": errors}


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample()
    else:
        r = score()
        (DIR / "annotation_score.json").write_text(json.dumps(r, indent=1))
        print(json.dumps({k: v for k, v in r.items() if k != "errors"}, indent=1))
