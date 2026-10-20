"""Objective 1 human-validation workflow (E71): the blind E70 sample, a second annotator's blank copy, and a scorer
that adds inter-annotator agreement (Cohen's kappa) and a consensus reference to the E70 weighted metrics.

    python -B runner/e71_annotation.py prepare     # writes annotation/HUMAN_ANNOTATION_SAMPLE_annotator2.csv (blank)
    python -B runner/e71_annotation.py score       # after both files are labelled -> annotation/annotation_score_e71.json

No label is ever filled in by this script. Until human labels exist, `score` reports NOT_ANNOTATED.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

E71 = Path(__file__).resolve().parents[1]
E70A = E71.parent / "E70_Objectives_Completion" / "annotation"
A1, KEY, META = E70A / "HUMAN_ANNOTATION_SAMPLE.csv", E70A / "model_key.csv", E70A / "sample_meta.json"
A2 = E71 / "annotation" / "HUMAN_ANNOTATION_SAMPLE_annotator2.csv"
LABELS = ["human_relevant", "human_trigger", "human_province", "human_food_stress", "annotator", "notes"]


def read(path):
    return {r["sample_id"]: r for r in csv.DictReader(path.open(encoding="utf-8"))}


def prepare():
    if A2.exists():
        raise SystemExit("annotator-2 file exists; it is written once")
    rows = list(csv.DictReader(A1.open(encoding="utf-8")))
    A2.parent.mkdir(exist_ok=True)
    with A2.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({**r, **{c: "" for c in LABELS}})
    print(A2, len(rows))


def kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def score(a1=A1, a2=A2, key=KEY, meta=META) -> dict:
    l1 = read(a1)
    l2 = read(a2) if Path(a2).exists() else {}
    keys = list(csv.DictReader(Path(key).open(encoding="utf-8")))
    m = json.loads(Path(meta).read_text())
    w = {s: m["population"][s] / m["sizes"][s] for s in m["sizes"] if m["sizes"][s]}
    ok = lambda r: r is not None and r["human_relevant"].strip() in ("0", "1")  # noqa: E731
    both = [k for k in keys if ok(l1.get(k["sample_id"])) and ok(l2.get(k["sample_id"]))]
    one = [k for k in keys if ok(l1.get(k["sample_id"]))]
    res = {"sample": len(keys), "labelled_annotator1": len(one), "labelled_both": len(both)}
    if not one:
        return res | {"status": "NOT_ANNOTATED"}
    if both:
        res["kappa_relevance"] = kappa([l1[k["sample_id"]]["human_relevant"].strip() for k in both],
                                       [l2[k["sample_id"]]["human_relevant"].strip() for k in both])
        rel = [k for k in both if l1[k["sample_id"]]["human_relevant"].strip() == "1" == l2[k["sample_id"]]["human_relevant"].strip()]
        res["kappa_trigger"] = kappa([l1[k["sample_id"]]["human_trigger"].strip() for k in rel],
                                     [l2[k["sample_id"]]["human_trigger"].strip() for k in rel])
        res["kappa_province"] = kappa([l1[k["sample_id"]]["human_province"].strip() for k in rel],
                                      [l2[k["sample_id"]]["human_province"].strip() for k in rel])
    # reference = consensus where both labelled and agree; annotator 1 alone otherwise (reported)
    ref = []
    for k in keys:
        r1, r2 = l1.get(k["sample_id"]), l2.get(k["sample_id"])
        if ok(r1) and ok(r2):
            if r1["human_relevant"].strip() == r2["human_relevant"].strip():
                ref.append((k, int(r1["human_relevant"]), r1, "consensus"))
        elif ok(r1):
            ref.append((k, int(r1["human_relevant"]), r1, "single"))
    tp = fp = fn = tn = 0.0
    by_stratum, trig, prov = {}, [0, 0], [0, 0]
    for k, h, r, _ in ref:
        mdl, wt = int(k["model_admitted"]), w[k["stratum"]]
        tp += wt * (mdl == 1 and h == 1)
        fp += wt * (mdl == 1 and h == 0)
        fn += wt * (mdl == 0 and h == 1)
        tn += wt * (mdl == 0 and h == 0)
        s = by_stratum.setdefault(k["stratum"], [0, 0])
        s[0] += int(mdl == h)
        s[1] += 1
        if mdl == 1 and h == 1:
            if r["human_trigger"].strip():
                trig[0] += r["human_trigger"].strip() == k["model_trigger"]
                trig[1] += 1
            if r["human_province"].strip():
                prov[0] += r["human_province"].strip() == (k["model_province"] or "national")
                prov[1] += 1
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    res |= {"status": "ANNOTATED" if len(one) == len(keys) else "PARTIAL",
            "reference_rows": len(ref), "consensus_rows": sum(1 for x in ref if x[3] == "consensus"),
            "weighted_precision": prec, "weighted_recall": rec,
            "weighted_f1": 2 * prec * rec / (prec + rec) if prec and rec else None,
            "agreement_by_stratum": by_stratum,
            "filipino_stratum_agreement": by_stratum.get("F"),
            "trigger_agreement": trig[0] / trig[1] if trig[1] else None,
            "province_attribution_agreement": prov[0] / prov[1] if prov[1] else None}
    return res


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare()
    else:
        r = score()
        (E71 / "annotation").mkdir(exist_ok=True)
        (E71 / "annotation" / "annotation_score_e71.json").write_text(json.dumps(r, indent=1))
        print(json.dumps(r, indent=1))
